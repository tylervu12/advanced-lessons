"""Local dashboard API. Run from this lesson: python -m uvicorn app.main:app."""
from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
from typing import Literal
import numpy as np
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from .store import Store
from .model import ensure_models
from .pipelines import predict, monitor, evaluate

ROOT = Path(__file__).resolve().parent


class BatchRequest(BaseModel):
    model_version: Literal["v1", "v2"] = "v1"
    threshold: float = Field(default=.25, ge=.05, le=.8)
    count: int = Field(default=200, ge=20, le=1000)
    scenario: Literal["baseline", "input_shift", "concept_shift"] = "baseline"
    inject_errors: bool = False


class AdvanceRequest(BaseModel):
    days: int = Field(default=90, ge=1, le=365)


def seed_demo(store):
    if store.rows("SELECT id FROM batches LIMIT 1"):
        return
    for scenario in ["baseline", "baseline", "baseline", "input_shift", "concept_shift", "concept_shift"]:
        batch = predict.run(store, count=160, scenario=scenario)
        monitor.run(store, batch)
        evaluate.advance(store, 6)
    evaluate.advance(store, 90)
    evaluate.run(store)
    batch = predict.run(store, model_version="v2", count=120, inject_errors=True)
    monitor.run(store, batch)


def create_app(directory=None, seed=True):
    @asynccontextmanager
    async def lifespan(app):
        store = Store(directory or os.environ.get("MLOPS_DATA_DIR", ROOT.parent / "runtime"))
        ensure_models(store)
        if seed:
            seed_demo(store)
        app.state.store = store
        yield

    app = FastAPI(title="Loan Risk Observatory", lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(ROOT / "static" / "index.html")

    @app.get("/api/dashboard")
    def dashboard(version: Literal["all", "v1", "v2"] = "all"):
        store = app.state.store
        args = () if version == "all" else (version,)
        clause = "" if version == "all" else " WHERE model_version=?"
        predictions = store.rows("SELECT * FROM predictions" + clause + " ORDER BY timestamp,id", args)
        good = [p for p in predictions if p["status"] == "success"]
        models = []
        for row in store.rows("SELECT * FROM models ORDER BY version"):
            meta = json.loads(row["metadata"])
            meta.pop("reference"); meta.pop("reference_scores")
            models.append(dict(**meta, created_at=row["created_at"]))
        batches = store.rows("SELECT * FROM batches" + clause + " ORDER BY created_at,id", args)
        for b in batches:
            items = [p for p in predictions if p["batch_id"] == b["id"]]
            valid = [p for p in items if p["status"] == "success"]
            b.update(approved=sum(p["decision"] == "approved" for p in valid),
                     declined=sum(p["decision"] == "declined" for p in valid),
                     errors=len(items)-len(valid), latency_p95=float(np.percentile([p["latency_ms"] for p in items],95)))
        result = evaluate.report(store, version)
        return dict(clock=store.clock(), models=models, batches=batches,
                    summary=dict(total=len(predictions), success=len(good), errors=len(predictions)-len(good),
                                 approved=sum(p["decision"] == "approved" for p in good),
                                 declined=sum(p["decision"] == "declined" for p in good),
                                 pending=len(good)-result["oracle"]["n"],
                                 latency_p95=float(np.percentile([p["latency_ms"] for p in predictions],95)) if predictions else None),
                    evaluation=result)

    @app.get("/api/predictions")
    def predictions(version: Literal["all", "v1", "v2"] = "all", decision: Literal["all", "approved", "declined", "error"] = "all",
                    outcome: Literal["all", "pending", "on_time", "late", "defaulted"] = "all",
                    limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
        filters, args = [], []
        if version != "all": filters.append("p.model_version=?"); args.append(version)
        if decision == "error": filters.append("p.status='error'")
        elif decision != "all": filters.append("p.decision=?"); args.append(decision)
        if outcome == "pending": filters.append("o.outcome IS NULL AND p.status='success'")
        elif outcome != "all": filters.append("o.outcome=?"); args.append(outcome)
        where = " WHERE " + " AND ".join(filters) if filters else ""
        base = " FROM predictions p LEFT JOIN outcomes o ON p.id=o.prediction_id"
        total = app.state.store.rows("SELECT COUNT(*) AS n"+base+where, args)[0]["n"]
        rows = app.state.store.rows("SELECT p.*,o.outcome,o.evidence"+base+where+
                                   " ORDER BY p.timestamp DESC,p.rowid DESC LIMIT ? OFFSET ?", [*args,limit,offset])
        for row in rows: row["input"] = json.loads(row.pop("input_json"))
        return dict(total=total, rows=rows)

    @app.post("/api/pipelines/predict")
    def score(request: BatchRequest):
        try:
            batch_id = predict.run(app.state.store, **request.model_dump())
            return dict(batch_id=batch_id)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.post("/api/pipelines/monitor/{batch_id}")
    def monitor_batch(batch_id: str):
        try:
            return monitor.run(app.state.store, batch_id)
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc

    @app.get("/api/monitoring/{batch_id}")
    def monitoring(batch_id: str):
        rows = app.state.store.rows("SELECT report FROM monitoring_runs WHERE batch_id=? ORDER BY id DESC LIMIT 1", (batch_id,))
        return json.loads(rows[0]["report"]) if rows else None

    @app.post("/api/clock/advance")
    def advance(request: AdvanceRequest):
        return dict(clock=evaluate.advance(app.state.store, request.days))

    @app.post("/api/pipelines/evaluate")
    def join():
        return evaluate.run(app.state.store)

    @app.post("/api/predictions/{prediction_id}/reproduce")
    def reproduce(prediction_id: str):
        try:
            return predict.reproduce(app.state.store, prediction_id)
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc

    return app


app = create_app()
