from typing import Protocol


class LLMClient(Protocol):
    def complete_json(self, system: str, user: str) -> str:
        """Request a completion expected to contain one JSON object.

        Args:
            system: System instruction sent to the model.
            user: User prompt sent to the model.

        Returns:
            Raw model response text for downstream JSON validation.
        """
