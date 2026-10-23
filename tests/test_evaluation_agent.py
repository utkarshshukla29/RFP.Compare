import json

import pytest

from agents.evaluation_agent import evaluate_supplier
from models.schemas import Criterion


CRITERIA = [Criterion(1, "Technical", "Architecture evidence", 100, 10)]


class SequenceClient:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = 0

    def complete_json(self, system, user):
        self.calls += 1
        return next(self.responses)


def test_retries_structurally_empty_json_then_accepts_score():
    valid = json.dumps({"supplier_name": "Supplier", "criteria": [
        {"criterion_id": "1", "score": 7, "max_score": 10, "justification": "Reason", "evidence": "Quote"}
    ]})
    client = SequenceClient(['{"error":"temporary upstream issue"}', valid])
    assert evaluate_supplier(client, CRITERIA, "Supplier", "Evidence text") == valid
    assert client.calls == 2


@pytest.mark.parametrize("fence", ["```JSON\n", "```\n"])
def test_accepts_json_inside_markdown_fences(fence):
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
    response = {"criteria": [{**identity, "score": 7, "max_score": 10,
                              "justification": "Reason", "evidence": "Quote"}]}
    client = SequenceClient([json.dumps(response)])
    normalized = json.loads(evaluate_supplier(client, CRITERIA, "Supplier", "Evidence text"))
    assert normalized["criteria"][0]["criterion_id"] == 1
    assert client.calls == 1


def test_fails_after_three_structurally_empty_responses():
    client = SequenceClient(['{"criteria":[]}', '{"error":"model unavailable"}', '{}'])
    with pytest.raises(ValueError, match="invalid evaluation output"):
        evaluate_supplier(client, CRITERIA, "Supplier", "Evidence text")
    assert client.calls == 3


def test_reports_final_parse_reason():
    client = SequenceClient(["not json", "still not json", "nope"])
    with pytest.raises(ValueError, match="Expecting value"):
        evaluate_supplier(client, CRITERIA, "Supplier", "Evidence text")