import json
import math
import re
from typing import Any

from models.schemas import Criterion, ScoreEntry, ValidatedScorecard


def validate_and_normalize(raw: str, criteria: list[Criterion], supplier_name: str) -> ValidatedScorecard:
    """Parse model JSON and normalize its scores against active criteria.

    Args:
        raw: Raw model JSON response, optionally wrapped in Markdown fences.
        criteria: Active criteria defining valid IDs and authoritative score maxima.
        supplier_name: User-entered supplier name, preferred over model output.

    Returns:
        ValidatedScorecard with one normalized entry per criterion and warnings.

    Raises:
        ValueError: If the response is invalid JSON or not a JSON object.
    """
    warnings: list[dict[str, Any]] = []
    cleaned = raw.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", cleaned, flags=re.IGNORECASE | re.DOTALL)
    if fenced:
        cleaned = fenced.group(1)
        warnings.append(_warning(supplier_name, None, "JSON_FENCE_STRIPPED", "Removed markdown JSON fences from the model response."))

    try:
        payload = json.loads(cleaned)
    except (json.JSONDecodeError, TypeError) as error:
        raise ValueError("The model did not return valid JSON after retries.") from error
    if not isinstance(payload, dict):
        raise ValueError("The model JSON response must be an object.")

    for key, default in (("criteria", []), ("risks", []), ("overall_summary", "")):
        if key not in payload:
            payload[key] = default
            warnings.append(_warning(supplier_name, None, "TOP_LEVEL_DEFAULTED", f"Missing '{key}' was defaulted."))

    returned_name = payload.get("supplier_name")
    if returned_name is not None and str(returned_name).strip() != supplier_name:
        warnings.append(_warning(supplier_name, None, "SUPPLIER_NAME_OVERRIDDEN", "User-entered supplier name replaced the model-returned name."))

    raw_entries = payload.get("criteria")
    if not isinstance(raw_entries, list):
        raw_entries = []
        warnings.append(_warning(supplier_name, None, "CRITERIA_NOT_LIST", "Criteria output was not a list; treated as empty."))

    active = {criterion.criterion_id: criterion for criterion in criteria}
    entries: dict[int, dict[str, Any]] = {}
    for item in raw_entries:
        if not isinstance(item, dict):
            warnings.append(_warning(supplier_name, None, "INVALID_CRITERION_ENTRY", "Ignored a criterion entry that was not an object."))
            continue
        try:
            criterion_id = int(item.get("criterion_id"))
        except (TypeError, ValueError, OverflowError):
            warnings.append(_warning(supplier_name, None, "INVALID_CRITERION_ID", "Ignored an entry with an invalid criterion_id."))
            continue
        if criterion_id not in active:
            warnings.append(_warning(supplier_name, criterion_id, "UNKNOWN_CRITERION", "Ignored a criterion that is not active."))
            continue
        if criterion_id in entries:
            warnings.append(_warning(supplier_name, criterion_id, "DUPLICATE_CRITERION", "Kept the first result and ignored a duplicate criterion_id."))
            continue
        entries[criterion_id] = item

    normalized = []
    for criterion in criteria:
        item = entries.get(criterion.criterion_id)
        if item is None:
            score = 0.0
            justification = "Not returned by model"
            evidence = ""
            warnings.append(_warning(supplier_name, criterion.criterion_id, "CRITERION_MISSING", "Active criterion was missing; score set to zero."))
        else:
            score = _number(item.get("score"), supplier_name, criterion, warnings)
            returned_max = _number_or_none(item.get("max_score"))
            if returned_max is not None and not math.isclose(returned_max, criterion.max_score):
                warnings.append(_warning(supplier_name, criterion.criterion_id, "MAX_SCORE_OVERRIDDEN", "Database max_score replaced the model-returned max_score."))
            justification = _text(item.get("justification"), supplier_name, criterion, "justification", warnings)
            evidence = _text(item.get("evidence"), supplier_name, criterion, "evidence", warnings)
            if score < 0:
                score = 0.0
                warnings.append(_warning(supplier_name, criterion.criterion_id, "SCORE_CLIPPED", "Score below zero was clipped to zero."))
            if score > criterion.max_score:
                score = criterion.max_score
                warnings.append(_warning(supplier_name, criterion.criterion_id, "SCORE_CLIPPED", f"Score above max_score was clipped to {criterion.max_score:g}."))
        normalized.append(ScoreEntry(criterion.criterion_id, criterion.name, criterion.weight, score,
                                     criterion.max_score, justification, evidence))

    risks_value = payload.get("risks")
    if not isinstance(risks_value, list):
        risks_value = [str(risks_value)] if risks_value else []
        warnings.append(_warning(supplier_name, None, "RISKS_NORMALIZED", "Risks were normalized to a list."))
    risks = [str(risk) for risk in risks_value if str(risk).strip()]
    return ValidatedScorecard(supplier_name, normalized, risks, str(payload.get("overall_summary") or ""), warnings)


def _number(value: Any, supplier_name: str, criterion: Criterion, warnings: list[dict[str, Any]]) -> float:
    """Parse a finite numeric score or default it to zero with a warning.

    Args:
        value: Model-returned score.
        supplier_name: Supplier associated with any warning.
        criterion: Criterion associated with this score.
        warnings: Mutable list receiving a warning for invalid values.

    Returns:
        Finite float score, or 0.0 when parsing fails.
    """
    number = _number_or_none(value)
    if number is None:
        warnings.append(_warning(supplier_name, criterion.criterion_id, "SCORE_DEFAULTED", "Non-numeric, null, or non-finite score was set to zero."))
        return 0.0
    return number


def _number_or_none(value: Any) -> float | None:
    """Convert a non-boolean finite numeric value to float when possible.

    Args:
        value: Value to parse.

    Returns:
        Finite float, or None for booleans, invalid, or non-finite values.
    """
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def _text(value: Any, supplier_name: str, criterion: Criterion, field_name: str,
          warnings: list[dict[str, Any]]) -> str:
    """Normalize model-provided text and warn when the value is missing.

    Args:
        value: Model-returned text value.
        supplier_name: Supplier associated with any warning.
        criterion: Criterion associated with this text.
        field_name: Field label included in a missing-value warning.
        warnings: Mutable list receiving a warning when value is None.

    Returns:
        Stripped text, or an empty string when the value is None.
    """
    if value is None:
        warnings.append(_warning(supplier_name, criterion.criterion_id, "TEXT_MISSING", f"Missing {field_name}; no evidence provided."))
        return ""
    return str(value).strip()


def _warning(supplier: str, criterion_id: int | None, code: str, message: str) -> dict[str, Any]:
    """Create a standardized scorecard validation warning dictionary.

    Args:
        supplier: Supplier associated with the warning.
        criterion_id: Related criterion ID, or None for a scorecard warning.
        code: Stable machine-readable warning code.
        message: Human-readable explanation.

    Returns:
        Dictionary containing supplier, criterion_id, code, and message.
    """
    return {"supplier": supplier, "criterion_id": criterion_id, "code": code, "message": message}