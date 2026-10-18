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
    path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    connection.commit()


def load_active_criteria(connection: sqlite3.Connection) -> list[Criterion]:
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
    connection.execute(
        "UPDATE rfp_runs SET status = 'FAILED', result_json = ? WHERE rfp_run_id = ?",
        (json.dumps(result), run_id),
    )
    connection.commit()


def load_run(connection: sqlite3.Connection, run_id: str) -> dict[str, Any] | None:
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
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
