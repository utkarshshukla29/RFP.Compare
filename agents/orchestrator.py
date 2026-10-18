import json
import uuid
from datetime import date
from pathlib import Path
from typing import Any, Callable

from agents.evaluation_agent import evaluate_supplier
from db.repository import (
    create_run,
    fail_run,
    get_connection,
    initialize_database,
    load_active_criteria,
    utc_now_iso,
    complete_run,
)
from db.seed import seed_database
from llm.base import LLMClient
from models.schemas import SupplierInput
from tools.document_tool import extract_text
from tools.ranking_tool import compute_ranking
from tools.validation_tool import validate_and_normalize


def run_batch(
    suppliers: list[SupplierInput | dict[str, Any]],
    llm_client: LLMClient,
    provider: str,
    model: str,
    pricing: dict[str, Any] | None = None,
    db_path: str | Path | None = None,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> dict[str, Any]:
    _validate_inputs(suppliers)
    pricing_snapshot = {
        key: pricing[key]
        for key in ("input_usd_per_1m", "output_usd_per_1m")
        if pricing is not None and key in pricing
    }
    seed_database(db_path)
    connection = get_connection(db_path)
    run_id = f"RFP-{date.today():%Y%m%d}-{uuid.uuid4().hex[:6].upper()}"
    created_at = utc_now_iso()
    initial_criteria = load_active_criteria(connection)
    create_run(connection, run_id, created_at, provider, model, pricing_snapshot, initial_criteria)
    criteria = load_active_criteria(connection)

    warnings: list[dict[str, Any]] = []
    if len(suppliers) == 1:
        warnings.append(_warning(None, "SINGLE_SUPPLIER", "Only one supplier was submitted; peer benchmarking is trivial."))

    scorecards = []
    metadata: dict[str, dict[str, Any]] = {}
    total = len(suppliers)
    try:
        for index, raw_supplier in enumerate(suppliers, start=1):
            supplier = _coerce_supplier(raw_supplier)
            if progress_callback:
                progress_callback(index, total, supplier.supplier_name)
            try:
                if not criteria:
                    raise ValueError("No active criteria are configured; activate at least one criterion.")
                if sum(item.weight for item in criteria) <= 0:
                    raise ValueError("Active criteria weights total zero; evaluation is blocked.")
                document = extract_text(supplier.pdf_bytes, supplier.supplier_name)
                warnings.extend(document.warnings)
                raw_result = evaluate_supplier(llm_client, criteria, supplier.supplier_name, document.text)
                scorecard = validate_and_normalize(raw_result, criteria, supplier.supplier_name)
                scorecards.append(scorecard)
                metadata[supplier.supplier_name] = {
                    "submission_date": supplier.submission_date,
                    "experience_rating": supplier.experience_rating,
                    "filename": supplier.filename,
                    "page_count": document.page_count,
                    "char_count": document.char_count,
                }
                warnings.extend(scorecard.warnings)
            except Exception as error:
                warnings.append(_warning(supplier.supplier_name, "SUPPLIER_FAILED", str(error)))

        if not scorecards:
            result = _run_payload(run_id, created_at, "FAILED", provider, model, pricing_snapshot, [], warnings, [], [])
            fail_run(connection, run_id, result)
            return result

        ranking = compute_ranking(scorecards, criteria, metadata)
        warnings.extend(ranking["warnings"])
        result = _run_payload(
            run_id, created_at, "COMPLETED", provider, model, pricing_snapshot, ranking["criteria_used"],
            warnings, ranking["tie_break_notes"], ranking["leaderboard"], ranking["suppliers"],
        )
        complete_run(connection, run_id, ranking["suppliers"], result)
        return result
    except Exception as error:
        result = _run_payload(run_id, created_at, "FAILED", provider, model, pricing_snapshot, [],
                              warnings + [_warning(None, "RUN_FAILED", str(error))], [], [])
        fail_run(connection, run_id, result)
        return result
    finally:
        connection.close()


def _validate_inputs(suppliers: list[SupplierInput | dict[str, Any]]) -> None:
    if not suppliers:
        raise ValueError("Upload at least one supplier PDF to evaluate.")
    names = set()
    for raw_supplier in suppliers:
        supplier = _coerce_supplier(raw_supplier)
        normalized_name = supplier.supplier_name.strip().casefold()
        if not normalized_name:
            raise ValueError("Every supplier must have a non-empty name.")
        if normalized_name in names:
            raise ValueError(f"Supplier name '{supplier.supplier_name}' is duplicated (names are case-insensitive).")
        names.add(normalized_name)
        try:
            date.fromisoformat(supplier.submission_date)
        except ValueError as error:
            raise ValueError(f"Invalid submission date for {supplier.supplier_name}; use YYYY-MM-DD.") from error
        if not 0 <= float(supplier.experience_rating) <= 10:
            raise ValueError(f"Experience rating for {supplier.supplier_name} must be between 0 and 10.")
        if not supplier.filename.lower().endswith(".pdf") or not supplier.pdf_bytes.startswith(b"%PDF"):
            raise ValueError(f"{supplier.supplier_name}: upload a readable PDF file.")


def _coerce_supplier(value: SupplierInput | dict[str, Any]) -> SupplierInput:
    if isinstance(value, SupplierInput):
        return value
    return SupplierInput(
        supplier_name=str(value.get("supplier_name", "")).strip(),
        submission_date=str(value.get("submission_date", "")),
        experience_rating=float(value.get("experience_rating", 0)),
        filename=str(value.get("filename", "")),
        pdf_bytes=bytes(value.get("pdf_bytes", b"")),
    )


def _run_payload(
    run_id: str,
    created_at: str,
    status: str,
    provider: str,
    model: str,
    pricing: dict[str, Any],
    criteria: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
    tie_break_notes: list[str],
    leaderboard: list[dict[str, Any]],
    suppliers: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "rfp_run_id": run_id,
        "created_at": created_at,
        "status": status,
        "llm": {"provider": provider, "model": model, **pricing},
        "criteria_used": criteria,
        "warnings": warnings,
        "tie_break_notes": tie_break_notes,
        "leaderboard": leaderboard,
        "suppliers": suppliers or [],
    }


def _warning(supplier: str | None, code: str, message: str) -> dict[str, Any]:
    return {"supplier": supplier, "criterion_id": None, "code": code, "message": message}
