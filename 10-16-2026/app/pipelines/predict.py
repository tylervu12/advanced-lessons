"""Pipeline 1: score applications and log each decision, including failures."""
import json
import time
from datetime import datetime, timedelta
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from ..data import applications, matrix, repayments
from ..model import load_model


class Loan(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    income: float = Field(ge=1000, le=1_000_000)
    credit_score: int = Field(ge=300, le=850)
    debt_ratio: float = Field(ge=0, le=1)
    loan_amount: float = Field(gt=0, le=1_000_000)
    employment_years: float = Field(ge=0, le=60)


def run(store, model_version="v1", threshold=.25, count=200, scenario="baseline", inject_errors=False):
    model, meta = load_model(store, model_version)
    batch_id = "batch-" + uuid4().hex[:10]
    # A fresh seed per batch is persisted through the exact input snapshots.
    seed = int(uuid4().hex[:8], 16)
    records = applications(count, seed, scenario)
    truth = repayments(records, seed + 1, scenario)
    if inject_errors:
        for i in range(0, count, 20):
            records[i] = {**records[i], "income": -100}
    with store.connect() as db:
        # Serialize the virtual clock update and the entire batch as one transaction.
        db.execute("BEGIN IMMEDIATE")
        timestamp = db.execute("SELECT value FROM state WHERE key='clock'").fetchone()[0]
        db.execute("INSERT INTO batches VALUES (?,?,?,?,?,?)",
                   (batch_id, timestamp, scenario, model_version, threshold, count))
        for i, record in enumerate(records):
            prediction_id = "pred-" + uuid4().hex
            input_id = "loan-" + uuid4().hex[:12]
            start = time.perf_counter()
            score = predicted_class = decision = error = None
            status = "success"
            try:
                loan = Loan.model_validate(record)
                score = float(model.predict_proba(matrix([loan.model_dump()]))[0, 1])
                predicted_class = "default_risk" if score >= threshold else "lower_risk"
                decision = "declined" if score >= threshold else "approved"
            except ValidationError:
                status, error = "error", "Invalid input: application failed feature validation"
            except Exception as exc:
                status, error = "error", f"Scoring failed: {type(exc).__name__}"
            elapsed = (time.perf_counter() - start) * 1000
            db.execute("INSERT INTO predictions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                prediction_id, input_id, batch_id, timestamp, model_version,
                meta["artifact_sha256"], json.dumps(record), score, predicted_class,
                decision, threshold, status, error, elapsed))
            if status == "success":
                # Only the outcome pipeline can expose this future ground truth.
                available = (datetime.fromisoformat(timestamp) + timedelta(days=90)).isoformat()
                db.execute("INSERT INTO simulation_truth VALUES (?,?,?)",
                           (prediction_id, truth[i], available))
        tomorrow = (datetime.fromisoformat(timestamp) + timedelta(days=1)).isoformat()
        db.execute("UPDATE state SET value=? WHERE key='clock'", (tomorrow,))
    return batch_id


def reproduce(store, prediction_id):
    rows = store.rows("SELECT * FROM predictions WHERE id=?", (prediction_id,))
    if not rows:
        raise ValueError("Prediction not found")
    row = rows[0]
    if row["status"] != "success":
        return dict(reproducible=False, reason=row["error"])
    model, meta = load_model(store, row["model_version"])
    score = float(model.predict_proba(matrix([json.loads(row["input_json"])]))[0, 1])
    return dict(reproducible=abs(score-row["score"]) < 1e-12 and
                row["artifact_sha256"] == meta["artifact_sha256"],
                recorded_score=row["score"], replayed_score=score,
                threshold=row["threshold"], model_version=row["model_version"],
                decision="declined" if score >= row["threshold"] else "approved")
