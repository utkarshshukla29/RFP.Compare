from models.schemas import Criterion, ScoreEntry, ValidatedScorecard
from tools.ranking_tool import compute_ranking


def make_criterion(criterion_id: int, name: str, weight: float) -> Criterion:
    """Create a criterion fixture with a fixed description and score maximum.

    Args:
        criterion_id: Criterion identifier used by score entries.
        name: Criterion display name.
        weight: Criterion weight in percentage points.

    Returns:
        Criterion fixture with max_score 10.
    """
    return Criterion(criterion_id, name, "Description", weight, 10)


def make_card(name: str, scores: list[float]) -> ValidatedScorecard:
    """Create a supplier scorecard fixture for a list of scores.

    Args:
        name: Supplier name.
        scores: Scores assigned to sequential criterion IDs starting at one.

    Returns:
        ValidatedScorecard containing generated entries and sample text.
    """
    return ValidatedScorecard(name, [
        ScoreEntry(index, f"Criterion {index}", 1, score, 10, "Reason", "Evidence")
        for index, score in enumerate(scores, start=1)
    ])


def metadata(name: str, date: str, experience: float) -> dict[str, dict[str, object]]:
    """Create one supplier's ranking metadata mapping.

    Args:
        name: Supplier name used as the mapping key.
        date: ISO-format submission date.
        experience: Historical experience rating.

    Returns:
        Mapping from supplier name to submission date and experience rating.
    """
    return {name: {"submission_date": date, "experience_rating": experience}}


def test_formula_benchmarks_and_weighted_ranking():
    """Verify absolute scores, PPI calculations, and descending leaderboard order.

    Args:
        None.

    Returns:
        None. Assertions compare computed rankings with hand-calculated values.
    """
    criteria = [make_criterion(1, "Quality", 60), make_criterion(2, "Value", 40)]
    cards = [make_card("A", [8, 6]), make_card("B", [10, 4]), make_card("C", [5, 10])]
    supplier_metadata = {
        "A": {"submission_date": "2026-09-12", "experience_rating": 8},
        "B": {"submission_date": "2026-09-13", "experience_rating": 7},
        "C": {"submission_date": "2026-09-10", "experience_rating": 9},
    }
    result = compute_ranking(cards, criteria, supplier_metadata)
    by_name = {supplier["supplier_name"]: supplier for supplier in result["suppliers"]}
    assert by_name["A"]["absolute_score"] == 72
    assert by_name["A"]["ppi"] == 72
    assert by_name["B"]["absolute_score"] == 76
    assert by_name["B"]["ppi"] == 76
    assert by_name["C"]["absolute_score"] == 70
    assert [row["supplier_name"] for row in result["leaderboard"]] == ["B", "A", "C"]


def test_zero_benchmark_is_safe_and_warned():
    """Verify all-zero criterion benchmarks produce safe relative scores and warnings.

    Args:
        None.

    Returns:
        None. Assertions check 100 percent relative values and a warning record.
    """
    criteria = [make_criterion(1, "Only", 100)]
    result = compute_ranking([make_card("A", [0]), make_card("B", [0])], criteria, {
        "A": {"submission_date": "2026-01-01", "experience_rating": 5},
        "B": {"submission_date": "2026-01-02", "experience_rating": 5},
    })
    assert all(item["criteria"][0]["relative_pct"] == 100 for item in result["suppliers"])
    assert any(warning["code"] == "ZERO_BENCHMARK" for warning in result["warnings"])


def test_tie_break_order_and_stable_across_input_order():
    """Verify deterministic tie-break ordering for multiple input permutations.

    Args:
        None.

    Returns:
        None. Assertions check supplier order and tie-break explanations.
    """
    criteria = [make_criterion(1, "Only", 100)]
    cards = [make_card("alpha", [10]), make_card("Beta", [10]), make_card("Apex", [10])]
    supplier_metadata = {
        "alpha": {"submission_date": "2026-01-01", "experience_rating": 8},
        "Beta": {"submission_date": "2026-01-01", "experience_rating": 8},
        "Apex": {"submission_date": "2026-01-01", "experience_rating": 9},
    }
    expected = ["Apex", "alpha", "Beta"]
    for shuffled in (cards, list(reversed(cards)), [cards[1], cards[2], cards[0]]):
        result = compute_ranking(shuffled, criteria, supplier_metadata)
        assert [row["supplier_name"] for row in result["leaderboard"]] == expected
        assert len(result["tie_break_notes"]) == 2
