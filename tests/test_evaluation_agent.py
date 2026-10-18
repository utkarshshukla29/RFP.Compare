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


def test_fails_after_three_structurally_empty_responses():
    client = SequenceClient(['{"criteria":[]}', '{"error":"model unavailable"}', '{}'])
    with pytest.raises(ValueError, match="invalid evaluation output"):
        evaluate_supplier(client, CRITERIA, "Supplier", "Evidence text")
    assert client.calls == 3