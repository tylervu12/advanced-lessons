"""Checks for leakage, traceability, cohort math, and independent pipelines."""
import json
import shutil
import sqlite3
import numpy as np
import pytest
from fastapi.testclient import TestClient
from app.data import applications, repayments
from app.main import create_app
from app.model import ensure_models
from app.pipelines import predict, monitor, evaluate
from app.store import Store


@pytest.fixture(scope="session")
def trained_directory(tmp_path_factory):
    directory = tmp_path_factory.mktemp("trained")
    ensure_models(Store(directory))
    return directory


@pytest.fixture
def store(tmp_path, trained_directory):
    # Reuse training, but isolate each test's predictions and clock.
    shutil.copytree(trained_directory, tmp_path, dirs_exist_ok=True)
    return Store(tmp_path)


def test_prediction_can_be_reproduced_after_another_model_is_used(store):
    batch = predict.run(store, count=20, threshold=.33)
    row = store.rows("SELECT * FROM predictions WHERE batch_id=?", (batch,))[0]
    predict.run(store, model_version="v2", count=20, threshold=.1)
    replay = predict.reproduce(store, row["id"])
    assert replay["reproducible"]
    assert replay["threshold"] == .33
    assert replay["model_version"] == "v1"
    assert row["input_id"] and row["artifact_sha256"] and row["timestamp"]
    assert row["latency_ms"] > 0


def test_future_outcomes_are_hidden_and_join_is_idempotent(store):
    predict.run(store, count=20)
    assert evaluate.run(store)["joined"] == 0
    evaluate.advance(store, 88)  # The scoring batch already advanced one day.
    assert evaluate.run(store)["joined"] == 0
    evaluate.advance(store, 1)
    assert evaluate.run(store)["joined"] == 20
    assert evaluate.run(store)["joined"] == 0
    assert evaluate.report(store)["oracle"]["n"] == 20


def test_invalid_records_never_receive_decisions_or_labels(store):
    batch = predict.run(store, count=40, inject_errors=True)
    errors = store.rows("SELECT * FROM predictions WHERE status='error'")
    assert len(errors) == 2
    assert all(r["score"] is None and r["decision"] is None and r["error"] for r in errors)
    report = monitor.run(store, batch)
    assert report["current_count"] == 38 and report["excluded_errors"] == 2
    evaluate.advance(store, 90)
    assert evaluate.run(store)["joined"] == 38


def test_pipeline_stages_are_independent(store):
    batch = predict.run(store, count=20)
    assert store.rows("SELECT * FROM monitoring_runs") == []
    assert store.rows("SELECT * FROM outcomes") == []
    monitor.run(store, batch)
    assert store.rows("SELECT * FROM outcomes") == []
    evaluate.advance(store, 90)
    assert store.rows("SELECT * FROM outcomes") == []


def test_monitoring_uses_same_model_and_threshold_for_reference(store):
    batch = predict.run(store, model_version="v2", count=400, threshold=.45, scenario="input_shift")
    report = monitor.run(store, batch)
    meta = json.loads(store.rows("SELECT metadata FROM models WHERE version='v2'")[0]["metadata"])
    assert report["model_version"] == "v2"
    assert report["reference_flagged"] == np.mean(np.array(meta["reference_scores"]) >= .45)
    assert max(f["psi"] for f in report["features"]) > .2
    assert report["reference_count"] == 2000


def test_concept_shift_changes_outcomes_without_changing_inputs():
    baseline = applications(8000, 123, "baseline")
    changed = applications(8000, 123, "concept_shift")
    assert baseline == changed
    normal = repayments(baseline, 321, "baseline")
    shifted = repayments(changed, 321, "concept_shift")
    assert shifted.count("defaulted") > normal.count("defaulted") * 1.8


def test_psi_handles_identical_data_and_empty_bins():
    same = monitor.distribution([0, 0, 1], [0, 0, 1], [0, .5, .8, 1.1])
    assert same["psi"] == 0
    changed = monitor.distribution([0, 0, 0], [1, 1, 1], [0, .5, 1.1])
    assert np.isfinite(changed["psi"]) and changed["psi"] > 0


def test_metrics_match_known_confusion_matrix_and_undefined_cases():
    rows = [dict(outcome=o, predicted_class=c, score=s) for o,c,s in [
        ("defaulted", "default_risk", .8), ("late", "default_risk", .6),
        ("defaulted", "lower_risk", .1), ("on_time", "lower_risk", .1)]]
    result = evaluate.metrics(rows)
    assert (result["tp"],result["fp"],result["fn"],result["tn"]) == (1,1,1,1)
    assert result["precision"] == result["recall"] == .5
    assert result["late_rate"] == .25
    assert result["brier"] == pytest.approx(.305)
    assert evaluate.metrics([])["recall"] is None
    assert evaluate.metrics([rows[-1]])["precision"] is None
    assert evaluate.metrics([rows[-1]])["recall"] is None
    assert evaluate.metrics([rows[-1]])["auc"] is None


def test_funded_and_hypothetical_outcomes_are_kept_separate(store):
    predict.run(store, count=200)
    evaluate.advance(store, 90); evaluate.run(store)
    report = evaluate.report(store)
    funded = store.rows("SELECT p.id FROM predictions p JOIN outcomes o ON o.prediction_id=p.id WHERE p.decision='approved'")
    assert report["funded"]["n"] == len(funded)
    assert report["oracle"]["n"] == 200
    assert sum(report["funded_outcomes"].values()) == len(funded)
    assert sum(s["n"] for s in report["segments"]) == len(funded)
    assert store.rows("SELECT * FROM outcomes WHERE evidence='hypothetical'")
    assert evaluate.report(store,"v2")["oracle"]["n"] == 0


def test_artifact_tampering_blocks_reproduction(store):
    predict.run(store, count=20)
    record = store.rows("SELECT id FROM predictions LIMIT 1")[0]
    path = store.directory / "v1.joblib"
    path.write_bytes(path.read_bytes()+b"tampered")
    with pytest.raises(ValueError, match="checksum"):
        predict.reproduce(store, record["id"])


def test_unknown_outcomes_cannot_be_joined(store):
    with pytest.raises(sqlite3.IntegrityError):
        with store.connect() as db:
            db.execute("INSERT INTO outcomes VALUES ('missing','late','2026-01-01','2026-04-01','funded')")


def test_api_validation_filters_and_pending_outcomes(store):
    with TestClient(create_app(store.directory, seed=False)) as client:
        assert client.get('/').status_code == 200
        assert client.post('/api/pipelines/predict',json={'threshold':1.2}).status_code == 422
        assert client.post('/api/pipelines/predict',json={'model_version':'unknown'}).status_code == 422
        assert client.post('/api/clock/advance',json={'days':-1}).status_code == 422
        response = client.post('/api/pipelines/predict',json={'count':40,'inject_errors':True})
        assert response.status_code == 200
        dashboard = client.get('/api/dashboard').json()
        assert dashboard['summary']['pending'] == 38
        records = client.get('/api/predictions?outcome=pending&limit=5').json()
        assert records['total'] == 38 and len(records['rows']) == 5
        assert all(r['outcome'] is None for r in records['rows'])
        assert 'simulation_truth' not in json.dumps(records)
        errors = client.get('/api/predictions?decision=error').json()
        assert errors['total'] == 2
        client.post('/api/clock/advance',json={'days':90})
        assert client.post('/api/pipelines/evaluate',json={}).json()['joined'] == 38
        assert client.get('/api/dashboard?version=v2').json()['summary']['total'] == 0
        assert client.post('/api/pipelines/monitor/not-a-batch',json={}).status_code == 404
