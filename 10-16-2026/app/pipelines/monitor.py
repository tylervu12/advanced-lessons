"""Pipeline 2: compare a batch with its model's fixed reference population."""
import json
import numpy as np
from ..data import FEATURES
from ..model import metadata


def distribution(reference, current, edges):
    # Add a small pseudocount so empty bins don't produce infinite PSI.
    r_count, _ = np.histogram(reference, edges)
    c_count, _ = np.histogram(current, edges)
    r = (r_count + .5) / (len(reference) + .5 * len(r_count))
    c = (c_count + .5) / (len(current) + .5 * len(c_count))
    return dict(psi=float(np.sum((c-r) * np.log(c/r))),
                reference=(r_count / len(reference)).tolist(),
                current=(c_count / len(current)).tolist(),
                labels=[f"Bin {i+1}" for i in range(len(r_count))])


def run(store, batch_id):
    batches = store.rows("SELECT * FROM batches WHERE id=?", (batch_id,))
    if not batches:
        raise ValueError("Batch not found")
    batch = batches[0]
    rows = store.rows("SELECT * FROM predictions WHERE batch_id=? AND status='success'", (batch_id,))
    if not rows:
        raise ValueError("Batch has no successful predictions")
    meta = metadata(store, batch["model_version"])
    inputs = [json.loads(r["input_json"]) for r in rows]
    features = []
    for feature in FEATURES:
        reference = np.array([r[feature] for r in meta["reference"]])
        current = np.array([r[feature] for r in inputs])
        # Freeze boundaries from reference quantiles, with overflow bins.
        inner = np.unique(np.quantile(reference, np.linspace(0, 1, 11)[1:-1]))
        edges = np.r_[-np.inf, inner, np.inf]
        report = distribution(reference, current, edges)
        report.update(feature=feature, reference_mean=float(reference.mean()),
                      current_mean=float(current.mean()), boundaries=inner.tolist())
        features.append(report)
    scores = distribution(meta["reference_scores"], [r["score"] for r in rows], np.linspace(0, 1, 11))
    scores["labels"] = [f"{i*10}–{(i+1)*10}%" for i in range(10)]
    reference_flagged = float(np.mean(np.array(meta["reference_scores"]) >= batch["threshold"]))
    report = dict(batch_id=batch_id, model_version=batch["model_version"], threshold=batch["threshold"],
                  reference_count=len(meta["reference"]), current_count=len(rows),
                  excluded_errors=batch["count"]-len(rows), features=features, scores=scores,
                  reference_flagged=reference_flagged,
                  current_flagged=sum(r["decision"] == "declined" for r in rows)/len(rows),
                  small_sample=len(rows) < 100, alert_threshold=.2)
    with store.connect() as db:
        db.execute("INSERT INTO monitoring_runs (batch_id,created_at,report) VALUES (?,?,?)",
                   (batch_id, store.clock(), json.dumps(report)))
    return report
