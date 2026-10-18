import json
from pathlib import Path

from agents.orchestrator import run_batch
from db.repository import get_connection, load_run
from llm.mock import MockLLMClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_PDFS = PROJECT_ROOT / "sampleRFPs"


def make_supplier(filename: str, name: str, submitted: str, experience: float) -> dict:
    return {
        "supplier_name": name,
        "submission_date": submitted,
        "experience_rating": experience,
        "filename": filename,
        "pdf_bytes": (SAMPLE_PDFS / filename).read_bytes(),
    }


def test_mock_batch_persists_complete_run_and_never_exports_key(tmp_path):
    suppliers = [
        make_supplier("01_Apex_Health_Systems_RFP_Response.pdf", "Apex Health Systems", "2026-09-12", 8),
        make_supplier("03_NexaWorks_Medical_RFP_Response.pdf", "NexaWorks Medical", "2026-09-12", 8),
    ]
    database = tmp_path / "run.sqlite3"
    result = run_batch(suppliers, MockLLMClient(), "Demo", "mock", {"api_key": "must-not-be-exported"}, database)
    assert result["status"] == "COMPLETED"
    assert len(result["leaderboard"]) == 2
    assert "must-not-be-exported" not in json.dumps(result)

    connection = get_connection(database)
    try:
        stored = load_run(connection, result["rfp_run_id"])
        assert stored is not None
        assert stored["status"] == "COMPLETED"
        assert len(stored["suppliers"]) == 2
        assert stored["result"]["criteria_used"]
    finally:
        connection.close()


def test_failed_supplier_does_not_abort_batch(tmp_path):
    suppliers = [
        make_supplier("01_Apex_Health_Systems_RFP_Response.pdf", "Apex Health Systems", "2026-09-12", 8),
        {"supplier_name": "Unreadable", "submission_date": "2026-09-13", "experience_rating": 5,
         "filename": "empty.pdf", "pdf_bytes": b"%PDF-invalid"},
    ]
    result = run_batch(suppliers, MockLLMClient(), "Demo", "mock", db_path=tmp_path / "run.sqlite3")
    assert result["status"] == "COMPLETED"
    assert len(result["leaderboard"]) == 1
    assert any(warning["supplier"] == "Unreadable" for warning in result["warnings"])
