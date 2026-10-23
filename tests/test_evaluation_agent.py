import json

import pytest

from agents.evaluation_agent import evaluate_supplier
from models.schemas import Criterion


CRITERIA = [Criterion(1, "Technical", "Architecture evidence", 100, 10)]


class SequenceClient:
    def __init__(self, responses):
        """Initialize a client that returns supplied responses in sequence.

        Args:
            responses: Iterable of raw completion strings to return.

        Returns:
            None. Stores the response iterator and initializes the call counter.
        """
        self.responses = iter(responses)
        self.calls = 0

    def complete_json(self, system, user):
        """Return the next prepared response and count the request.

        Args:
            system: System prompt, unused by this deterministic test double.
            user: User prompt, unused by this deterministic test double.

        Returns:
            Next response string from the configured sequence.
        """
        self.calls += 1
        return next(self.responses)


def test_retries_structurally_empty_json_then_accepts_score():
    """Verify a structurally invalid response is retried before valid JSON.

    Args:
        None.

    Returns:
        None. Assertions check accepted output and exactly two client calls.
    """
    valid = json.dumps({"supplier_name": "Supplier", "criteria": [
        {"criterion_id": "1", "score": 7, "max_score": 10, "justification": "Reason", "evidence": "Quote"}
    ]})
    client = SequenceClient(['{"error":"temporary upstream issue"}', valid])
    assert evaluate_supplier(client, CRITERIA, "Supplier", "Evidence text") == valid
    assert client.calls == 2


@pytest.mark.parametrize("fence", ["```JSON\n", "```\n"])
def test_accepts_json_inside_markdown_fences(fence):
    """Verify labeled and unlabeled Markdown fences are accepted in one call.

    Args:
        fence: Opening Markdown fence variant supplied by pytest parametrization.

    Returns:
        None. Assertions check the response is accepted without retry.
    """
    valid = json.dumps({"criteria": [
        {"criterion_id": 1, "score": 7, "max_score": 10, "justification": "Reason", "evidence": "Quote"}
    ]})
    client = SequenceClient([f"{fence}{valid}\n```"])
    assert evaluate_supplier(client, CRITERIA, "Supplier", "Evidence text").strip() == f"{fence}{valid}\n```"
    assert client.calls == 1


@pytest.mark.parametrize("identity", [
    {"criterion_id": "Technical"},
    {"criterion_name": " technical "},
    {"criterion": "Technical"},
])
def test_maps_criterion_name_to_active_id(identity):
    """Verify criterion names in supported fields normalize to the active ID.

    Args:
        identity: Pytest-parameterized criterion identity field and value.

    Returns:
        None. Assertions check normalized ID and a single client call.
    """
    response = {"criteria": [{**identity, "score": 7, "max_score": 10,
                              "justification": "Reason", "evidence": "Quote"}]}
    client = SequenceClient([json.dumps(response)])
    normalized = json.loads(evaluate_supplier(client, CRITERIA, "Supplier", "Evidence text"))
    assert normalized["criteria"][0]["criterion_id"] == 1
    assert client.calls == 1


def test_fails_after_three_structurally_empty_responses():
    """Verify three responses without an active criterion produce ValueError.

    Args:
        None.

    Returns:
        None. Assertions check the controlled error and three attempts.
    """
    client = SequenceClient(['{"criteria":[]}', '{"error":"model unavailable"}', '{}'])
    with pytest.raises(ValueError, match="invalid evaluation output"):
        evaluate_supplier(client, CRITERIA, "Supplier", "Evidence text")
    assert client.calls == 3


def test_reports_final_parse_reason():
    """Verify the final JSON parsing reason is included in the error message.

    Args:
        None.

    Returns:
        None. The assertion checks the exposed JSON decoder error text.
    """
    client = SequenceClient(["not json", "still not json", "nope"])
    with pytest.raises(ValueError, match="Expecting value"):
        evaluate_supplier(client, CRITERIA, "Supplier", "Evidence text")