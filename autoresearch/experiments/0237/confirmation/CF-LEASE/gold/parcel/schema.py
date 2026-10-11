SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL UNIQUE,
    payload TEXT NOT NULL,
    state TEXT NOT NULL CHECK(state IN ('ready', 'leased', 'done')),
    available_at REAL NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    owner TEXT,
    token TEXT,
    lease_until REAL,
    last_error TEXT
);
CREATE INDEX IF NOT EXISTS jobs_pending ON jobs(state, available_at, seq);
"""
