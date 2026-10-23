import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from models.schemas import Criterion


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "rfp_evaluator.sqlite3"
SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def get_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Open SQLite with row objects and foreign-key checks enabled.

    Args:
        db_path: Database file path, or None to use the project default.

    Returns:
        Initialized sqlite3 connection; parent directories are created if needed.
    """
    path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(connection: sqlite3.Connection) -> None:
    """Create database tables from the checked-in SQL schema.

    Args:
        connection: Open SQLite connection to initialize.

    Returns:
        None. Commits schema changes to the database.
    """
    connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    connection.commit()


def load_active_criteria(connection: sqlite3.Connection) -> list[Criterion]:
    """Load active criteria ordered by database ID.

    Args:
        connection: Open SQLite connection containing evaluation_criteria.

    Returns:
        Active rows converted to Criterion dataclasses.
    """
    rows = connection.execute(
        "SELECT criterion_id, name, description, weight, max_score, is_active "
        "FROM evaluation_criteria WHERE is_active = 1 ORDER BY criterion_id"
    ).fetchall()
    return [Criterion(row["criterion_id"], row["name"], row["description"], row["weight"], row["max_score"], True)
            for row in rows]


def create_run(
    connection: sqlite3.Connection,
    run_id: str,
    created_at: str,
    provider: str,
    model: str,
    pricing: dict[str, Any],
    criteria: list[Criterion],
) -> None:
    """Insert a RUNNING record with model, pricing, and criteria snapshots.

    Args:
        connection: Open SQLite connection.
        run_id: Unique run identifier.
        created_at: ISO-8601 creation timestamp.
        provider: LLM provider label.
        model: LLM model identifier.
        pricing: JSON-serializable pricing snapshot.
        criteria: Criteria used for this evaluation.

    Returns:
        None. Inserts and commits the run record.
    """
    connection.execute(
        "INSERT INTO rfp_runs (rfp_run_id, created_at, status, llm_provider, llm_model, "
        "llm_pricing_json, result_json) VALUES (?, ?, 'RUNNING', ?, ?, ?, ?)",
        (run_id, created_at, provider, model, json.dumps(pricing), json.dumps({"criteria_used": [
            {"criterion_id": item.criterion_id, "name": item.name, "description": item.description,
             "weight": item.weight, "max_score": item.max_score} for item in criteria
        ]})),
    )
    connection.commit()


def complete_run(
    connection: sqlite3.Connection,
    run_id: str,
    results: list[dict[str, Any]],
    full_result: dict[str, Any],
) -> None:
    """Persist ranked supplier rows and mark the run COMPLETED.

    Args:
        connection: Open SQLite connection.
        run_id: Run to complete.
        results: Full ranked supplier result dictionaries.
        full_result: Complete JSON-ready run payload.

    Returns:
        None. Writes results and commits the transaction.
    """
    connection.executemany(
        "INSERT INTO supplier_results (rfp_run_id, supplier_name, submission_date, experience_rating, "
        "absolute_score, ppi, final_rank, result_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [(run_id, result["supplier_name"], result["submission_date"], result["experience_rating"],
          result["absolute_score"], result["ppi"], result["final_rank"], json.dumps(result))
         for result in results],
    )
    connection.execute(
        "UPDATE rfp_runs SET status = 'COMPLETED', result_json = ? WHERE rfp_run_id = ?",
        (json.dumps(full_result), run_id),
    )
    connection.commit()


def fail_run(connection: sqlite3.Connection, run_id: str, result: dict[str, Any]) -> None:
    """Mark a run FAILED and store its diagnostic payload.

    Args:
        connection: Open SQLite connection.
        run_id: Run to mark failed.
        result: JSON-ready failure payload.

    Returns:
        None. Updates and commits the run record.
    """
    connection.execute(
        "UPDATE rfp_runs SET status = 'FAILED', result_json = ? WHERE rfp_run_id = ?",
        (json.dumps(result), run_id),
    )
    connection.commit()


def load_run(connection: sqlite3.Connection, run_id: str) -> dict[str, Any] | None:
    """Load run metadata, decoded result JSON, and supplier result rows.

    Args:
        connection: Open SQLite connection.
        run_id: Unique run identifier to load.

    Returns:
        Run dictionary with supplier results, or None when the run is absent.
    """
    row = connection.execute("SELECT * FROM rfp_runs WHERE rfp_run_id = ?", (run_id,)).fetchone()
    if row is None:
        return None
    result = dict(row)
    result["llm_pricing"] = json.loads(result.pop("llm_pricing_json"))
    result["result"] = json.loads(result.pop("result_json"))
    result["suppliers"] = [json.loads(item[0]) for item in connection.execute(
        "SELECT result_json FROM supplier_results WHERE rfp_run_id = ? ORDER BY final_rank", (run_id,)
    ).fetchall()]
    return result


def utc_now_iso() -> str:
    """Return current UTC time as a second-precision ISO-8601 string.

    Args:
        None.

    Returns:
        Timestamp formatted like 2026-10-23T12:34:56Z.
    """
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
