"""A tiny model registry. Preprocessing is fitted on training folds only."""
import hashlib
import json
from datetime import datetime, timezone
from functools import lru_cache
import joblib
import sklearn
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV, StratifiedKFold, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, brier_score_loss
from .data import FEATURES, applications, matrix, repayments


def checksum(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ensure_models(store):
    for version, count, seed in [("v1", 2400, 41), ("v2", 8000, 72)]:
        if store.rows("SELECT version FROM models WHERE version=?", (version,)):
            continue
        records = applications(count, seed)
        y = np.array([o == "defaulted" for o in repayments(records, seed + 100)])
        indices = np.arange(count)
        train, test = train_test_split(indices, test_size=.25, stratify=y, random_state=seed)
        x = matrix(records)
        pipeline = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, random_state=seed))
        search = GridSearchCV(pipeline, {"logisticregression__C": [.1, 1., 10.]},
                              cv=StratifiedKFold(3, shuffle=True, random_state=seed),
                              scoring="neg_log_loss", n_jobs=1)
        search.fit(x[train], y[train])
        model = search.best_estimator_
        scores = model.predict_proba(x[test])[:, 1]
        artifact = store.directory / f"{version}.joblib"
        joblib.dump(model, artifact)
        # Independent reference population: same snapshot, never a live batch.
        reference = applications(2000, seed + 200)
        meta = dict(version=version, algorithm="StandardScaler + LogisticRegression",
                    seed=seed, training_rows=len(train), test_rows=len(test),
                    snapshot=f"synthetic-history-{seed}", features=FEATURES,
                    sklearn_version=sklearn.__version__, artifact_sha256=checksum(artifact),
                    dataset_sha256=hashlib.sha256(json.dumps(records, sort_keys=True).encode()).hexdigest(),
                    selected_C=search.best_params_["logisticregression__C"],
                    validation_log_loss=float(-search.best_score_),
                    test_auc=float(roc_auc_score(y[test], scores)),
                    test_brier=float(brier_score_loss(y[test], scores)),
                    training_default_rate=float(y[train].mean()), reference=reference,
                    reference_scores=model.predict_proba(matrix(reference))[:, 1].tolist())
        with store.connect() as db:
            db.execute("INSERT INTO models VALUES (?,?,?)",
                       (version, datetime.now(timezone.utc).isoformat(), json.dumps(meta)))


def metadata(store, version):
    rows = store.rows("SELECT metadata FROM models WHERE version=?", (version,))
    if not rows:
        raise ValueError("Unknown model version")
    return json.loads(rows[0]["metadata"])


@lru_cache(maxsize=8)
def _load(path, expected_hash):
    # Only load artifacts created by this application, never uploaded pickle files.
    return joblib.load(path)


def load_model(store, version):
    meta = metadata(store, version)
    path = store.directory / f"{version}.joblib"
    if checksum(path) != meta["artifact_sha256"]:
        raise ValueError("Model artifact checksum mismatch")
    return _load(path, meta["artifact_sha256"]), meta
