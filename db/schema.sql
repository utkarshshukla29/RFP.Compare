PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS evaluation_criteria (
    criterion_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL,
    weight REAL NOT NULL CHECK (weight >= 0),
    max_score REAL NOT NULL DEFAULT 10 CHECK (max_score > 0),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
);

CREATE TABLE IF NOT EXISTS rfp_runs (
    rfp_run_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('RUNNING', 'COMPLETED', 'FAILED')),
    llm_provider TEXT NOT NULL,
    llm_model TEXT NOT NULL,
    llm_pricing_json TEXT NOT NULL,
    result_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS supplier_results (
    rfp_run_id TEXT NOT NULL REFERENCES rfp_runs(rfp_run_id) ON DELETE CASCADE,
    supplier_name TEXT NOT NULL,
    submission_date TEXT NOT NULL,
    experience_rating REAL NOT NULL CHECK (experience_rating BETWEEN 0 AND 10),
    absolute_score REAL NOT NULL,
    ppi REAL NOT NULL,
    final_rank INTEGER NOT NULL,
    result_json TEXT NOT NULL,
    PRIMARY KEY (rfp_run_id, supplier_name)
);
