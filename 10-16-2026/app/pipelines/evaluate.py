"""Pipeline 3: join matured outcomes by prediction ID, then evaluate cohorts."""
import json
from datetime import datetime, timedelta
import numpy as np
from sklearn.metrics import roc_auc_score


def advance(store, days):
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        now = db.execute("SELECT value FROM state WHERE key='clock'").fetchone()[0]
        future = (datetime.fromisoformat(now) + timedelta(days=days)).isoformat()
        db.execute("UPDATE state SET value=? WHERE key='clock'", (future,))
    return future


def run(store):
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        now = db.execute("SELECT value FROM state WHERE key='clock'").fetchone()[0]
        cursor = db.execute("""INSERT OR IGNORE INTO outcomes
            SELECT t.prediction_id,t.outcome,t.available_at,?,
                   CASE WHEN p.decision='approved' THEN 'funded' ELSE 'hypothetical' END
            FROM simulation_truth t JOIN predictions p ON p.id=t.prediction_id
            WHERE t.available_at <= ?""", (now, now))
        inserted = cursor.rowcount
    return dict(joined=inserted, clock=now)


def rate(numerator, denominator):
    return numerator / denominator if denominator else None


def metrics(rows):
    if not rows:
        return dict(n=0, precision=None, recall=None, brier=None, auc=None,
                    tp=0, fp=0, fn=0, tn=0, default_rate=None, late_rate=None)
    y = np.array([r["outcome"] == "defaulted" for r in rows])
    flagged = np.array([r["predicted_class"] == "default_risk" for r in rows])
    scores = np.array([r["score"] for r in rows])
    tp, fp = int(np.sum(y & flagged)), int(np.sum(~y & flagged))
    fn, tn = int(np.sum(y & ~flagged)), int(np.sum(~y & ~flagged))
    return dict(n=len(rows), precision=rate(tp, tp+fp), recall=rate(tp, tp+fn),
                brier=float(np.mean((scores-y)**2)),
                auc=float(roc_auc_score(y, scores)) if len(set(y)) == 2 else None,
                tp=tp, fp=fp, fn=fn, tn=tn, default_rate=float(y.mean()),
                late_rate=sum(r["outcome"] == "late" for r in rows)/len(rows))


def report(store, version="all"):
    where, args = ("", ()) if version == "all" else (" WHERE p.model_version=?", (version,))
    rows = store.rows("""SELECT p.*,o.outcome,o.evidence,o.available_at,b.scenario
        FROM predictions p JOIN outcomes o ON o.prediction_id=p.id
        JOIN batches b ON b.id=p.batch_id""" + where + " ORDER BY p.timestamp,p.rowid", args)
    funded = [r for r in rows if r["evidence"] == "funded"]
    trend = []
    for batch_id in dict.fromkeys(r["batch_id"] for r in rows):
        cohort = [r for r in rows if r["batch_id"] == batch_id]
        approved = [r for r in cohort if r["evidence"] == "funded"]
        trend.append(dict(batch_id=batch_id, timestamp=cohort[0]["timestamp"],
                          version=cohort[0]["model_version"], scenario=cohort[0]["scenario"],
                          **metrics(cohort), funded=metrics(approved)))
    segments = []
    for name, predicate in [("Credit under 650", lambda x: x["credit_score"] < 650),
                            ("Credit 650–719", lambda x: 650 <= x["credit_score"] < 720),
                            ("Credit 720+", lambda x: x["credit_score"] >= 720)]:
        segment = [r for r in funded if predicate(json.loads(r["input_json"]))]
        all_segment = [r for r in rows if predicate(json.loads(r["input_json"]))]
        segments.append(dict(name=name, **metrics(segment), oracle=metrics(all_segment)))
    return dict(oracle=metrics(rows), funded=metrics(funded), trend=trend, segments=segments,
                funded_outcomes={k: sum(r["outcome"] == k for r in funded)
                                 for k in ("on_time", "late", "defaulted")},
                by_model=[dict(version=v, **metrics([r for r in rows if r["model_version"] == v]))
                          for v in sorted(set(r["model_version"] for r in rows))])
