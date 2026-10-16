"""SQLite persists immutable decisions, model metadata, and joined outcomes."""
from contextlib import contextmanager
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS state (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS models (
 version TEXT PRIMARY KEY, created_at TEXT NOT NULL, metadata TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS batches (
 id TEXT PRIMARY KEY, created_at TEXT NOT NULL, scenario TEXT NOT NULL,
 model_version TEXT NOT NULL, threshold REAL NOT NULL, count INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS predictions (
 id TEXT PRIMARY KEY, input_id TEXT NOT NULL UNIQUE, batch_id TEXT NOT NULL,
 timestamp TEXT NOT NULL, model_version TEXT NOT NULL, artifact_sha256 TEXT NOT NULL,
 input_json TEXT NOT NULL, score REAL, predicted_class TEXT, decision TEXT,
 threshold REAL NOT NULL, status TEXT NOT NULL, error TEXT, latency_ms REAL NOT NULL,
 FOREIGN KEY(batch_id) REFERENCES batches(id),
 FOREIGN KEY(model_version) REFERENCES models(version)
);
CREATE TABLE IF NOT EXISTS simulation_truth (
 prediction_id TEXT PRIMARY KEY, outcome TEXT NOT NULL, available_at TEXT NOT NULL,
 FOREIGN KEY(prediction_id) REFERENCES predictions(id)
);
CREATE TABLE IF NOT EXISTS outcomes (
 prediction_id TEXT PRIMARY KEY, outcome TEXT NOT NULL, available_at TEXT NOT NULL,
 joined_at TEXT NOT NULL, evidence TEXT NOT NULL,
 FOREIGN KEY(prediction_id) REFERENCES predictions(id)
);
CREATE TABLE IF NOT EXISTS monitoring_runs (
 id INTEGER PRIMARY KEY AUTOINCREMENT, batch_id TEXT NOT NULL,
 created_at TEXT NOT NULL, report TEXT NOT NULL
);
"""


class Store:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript(SCHEMA)
            db.execute("INSERT OR IGNORE INTO state VALUES ('clock', '2026-01-01T09:00:00+00:00')")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.directory / "observatory.sqlite3", timeout=30)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    def rows(self, sql, args=()):
        with self.connect() as db:
            return [dict(row) for row in db.execute(sql, args)]

    def clock(self):
        return self.rows("SELECT value FROM state WHERE key='clock'")[0]["value"]
