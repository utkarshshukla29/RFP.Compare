from __future__ import annotations

from typing import Any

from models.schemas import Criterion, ValidatedScorecard


def compute_ranking(
    scorecards: list[ValidatedScorecard],
    criteria: list[Criterion],
    supplier_metadata: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Calculate weighted scores, benchmarks, PPI, tie-breaks, and ranks.

    Args:
        scorecards: Validated criterion scorecards for successful suppliers.
        criteria: Active criteria defining score limits and original weights.
        supplier_metadata: Mapping from supplier name to date and experience rating.

    Returns:
        Dictionary with leaderboard, supplier details, warnings, tie-break notes,
        and the normalized criteria snapshot.

    Raises:
        ValueError: If criteria are empty or their total weight is not positive.
    """
    if not criteria:
        raise ValueError("There are no active evaluation criteria.")

    original_total = sum(criterion.weight for criterion in criteria)
    if original_total <= 0:
        raise ValueError("Active criterion weights must total more than zero.")

    normalized_weights = {criterion.criterion_id: criterion.weight * 100 / original_total for criterion in criteria}
    warnings: list[dict[str, Any]] = []
    if abs(original_total - 100) > 1e-9:
        warnings.append({"supplier": None, "criterion_id": None, "code": "WEIGHTS_NORMALIZED",
                         "message": f"Active weights totaled {original_total:g}; normalized proportionally to 100 for this run."})

    criterion_lookup = {criterion.criterion_id: criterion for criterion in criteria}
    score_index: dict[str, dict[int, dict[str, Any]]] = {}
    suppliers: list[dict[str, Any]] = []
    benchmarks: dict[int, float] = {}
    for criterion in criteria:
        benchmarks[criterion.criterion_id] = max(
            (entry.score for card in scorecards for entry in card.criteria if entry.criterion_id == criterion.criterion_id),
            default=0.0,
        )
        if benchmarks[criterion.criterion_id] == 0:
            warnings.append({"supplier": None, "criterion_id": criterion.criterion_id, "code": "ZERO_BENCHMARK",
                             "message": f"All suppliers scored zero for {criterion.name}; relative performance is set to 100% for all."})

    for card in scorecards:
        metadata = supplier_metadata[card.supplier_name]
        entries_by_id = {entry.criterion_id: entry for entry in card.criteria}
        criterion_results = []
        absolute_score = 0.0
        ppi_numerator = 0.0
        for criterion in criteria:
            entry = entries_by_id[criterion.criterion_id]
            benchmark = benchmarks[criterion.criterion_id]
            relative = 100.0 if benchmark == 0 else entry.score / benchmark * 100
            gap = entry.score - benchmark
            weight = normalized_weights[criterion.criterion_id]
            contribution = entry.score / criterion.max_score * weight
            absolute_score += contribution
            ppi_numerator += relative * weight
            criterion_results.append({
                "criterion_id": criterion.criterion_id,
                "name": criterion.name,
                "weight": weight,
                "original_weight": criterion.weight,
                "score": entry.score,
                "max_score": criterion.max_score,
                "benchmark": benchmark,
                "gap": gap,
                "relative_pct": relative,
                "weighted_contribution": contribution,
                "justification": entry.justification,
                "evidence": entry.evidence,
            })
        result = {
            "supplier_name": card.supplier_name,
            "submission_date": metadata["submission_date"],
            "experience_rating": float(metadata["experience_rating"]),
            "absolute_score": absolute_score,
            "ppi": ppi_numerator / 100,
            "criteria": criterion_results,
            "risks": card.risks,
            "overall_summary": card.overall_summary,
            "warnings": card.warnings,
        }
        score_index[card.supplier_name] = entries_by_id
        suppliers.append(result)

    suppliers.sort(key=lambda result: (
        -round(result["ppi"], 4), result["submission_date"],
        -result["experience_rating"], result["supplier_name"].casefold(),
    ))
    tie_break_notes = _explain_tie_breaks(suppliers)
    for rank, result in enumerate(suppliers, start=1):
        result["final_rank"] = rank

    leaderboard = [{key: result[key] for key in (
        "final_rank", "supplier_name", "submission_date", "experience_rating", "absolute_score", "ppi"
    )} for result in suppliers]
    return {"leaderboard": leaderboard, "suppliers": suppliers, "warnings": warnings,
            "tie_break_notes": tie_break_notes, "criteria_used": [
                {"criterion_id": criterion.criterion_id, "name": criterion.name,
                 "description": criterion.description, "weight": normalized_weights[criterion.criterion_id],
                 "original_weight": criterion.weight, "max_score": criterion.max_score}
                for criterion in criteria
            ]}


def _explain_tie_breaks(suppliers: list[dict[str, Any]]) -> list[str]:
    """Describe adjacent ranking pairs whose PPIs tie at four decimals.

    Args:
        suppliers: Supplier result dictionaries already sorted by final rank.

    Returns:
        Human-readable notes for ties resolved by date, experience, or name.
    """
    notes = []
    for higher, lower in zip(suppliers, suppliers[1:]):
        if round(higher["ppi"], 4) != round(lower["ppi"], 4):
            continue
        reasons = [f"equal PPI ({higher['ppi']:.2f})"]
        if higher["submission_date"] != lower["submission_date"]:
            reasons.append(f"earlier submission date ({higher['submission_date']} vs {lower['submission_date']})")
        elif higher["experience_rating"] != lower["experience_rating"]:
            reasons.append(f"higher experience rating ({higher['experience_rating']:g} vs {lower['experience_rating']:g})")
        elif higher["supplier_name"].casefold() != lower["supplier_name"].casefold():
            reasons.append("supplier name sorts first case-insensitively")
        else:
            continue
        notes.append(f"{higher['supplier_name']} ranked above {lower['supplier_name']}: " + ", ".join(reasons) + ".")
    return notes
