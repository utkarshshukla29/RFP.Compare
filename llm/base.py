from typing import Protocol


class LLMClient(Protocol):
    def complete_json(self, system: str, user: str) -> str:
        """Return a model response expected to contain one JSON object."""
