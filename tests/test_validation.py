import json

from models.schemas import Criterion
from tools.validation_tool import validate_and_normalize


CRITERIA = [
    Criterion(1, "Technical", "Architecture evidence", 60, 10),
    Criterion(2, "Security", "Security evidence", 40, 5),
]


def test_validation_normalizes_scores_and_warns_for_corrections():
    """Verify malformed or out-of-range fields are normalized with warnings.

    Args:
        None.

    Returns:
        None. Assertions check name override, clipping, defaults, and warnings.
    """
    raw = json.dumps({
        "supplier_name": "wrong name",
        "criteria": [
            {"criterion_id": 1, "score": 12, "max_score": 9, "justification": "Strong", "evidence": "Quoted evidence"},
            {"criterion_id": 1, "score": 3},
            {"criterion_id": 999, "score": 4},
            {"criterion_id": 2, "score": "NaN", "justification": None, "evidence": None},
        ],
    })
    card = validate_and_normalize(raw, CRITERIA, "Supplier One")
    assert card.supplier_name == "Supplier One"
    assert [(entry.criterion_id, entry.score) for entry in card.criteria] == [(1, 10), (2, 0)]
    codes = {warning["code"] for warning in card.warnings}
    assert {"SUPPLIER_NAME_OVERRIDDEN", "DUPLICATE_CRITERION", "UNKNOWN_CRITERION",
            "SCORE_CLIPPED", "SCORE_DEFAULTED", "TEXT_MISSING", "TOP_LEVEL_DEFAULTED"} <= codes


def test_validation_strips_fences_and_inserts_missing_criterion():
    """Verify fenced JSON is parsed and omitted active criteria are inserted.

    Args:
        None.

    Returns:
        None. Assertions check scorecard entries and corresponding warnings.
    """
    raw = '''```json\n{"criteria":[{"criterion_id":1,"score":6,"justification":"Fits","evidence":"FHIR support"}],"risks":[],"overall_summary":"OK"}\n```'''
    card = validate_and_normalize(raw, CRITERIA, "Supplier One")
    assert [entry.score for entry in card.criteria] == [6, 0]
    assert any(warning["code"] == "JSON_FENCE_STRIPPED" for warning in card.warnings)
    assert any(warning["code"] == "CRITERION_MISSING" for warning in card.warnings)


def test_invalid_json_raises_controlled_error():
    """Verify invalid JSON is rejected with a controlled ValueError.

    Args:
        None.

    Returns:
        None. Raises AssertionError if invalid input is accepted.
    """
    try:
        validate_and_normalize("not json", CRITERIA, "Supplier One")
    except ValueError as error:
        assert "valid JSON" in str(error)
    else:
        raise AssertionError("Invalid JSON should not be accepted")
