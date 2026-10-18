import requests

from llm.base import LLMClient
from llm.mock import MockLLMClient


class ProviderClient:
    def __init__(self, provider: str, api_key: str, model: str):
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.session = requests.Session()

    def complete_json(self, system: str, user: str) -> str:
        try:
            return self._complete_json(system, user)
        except requests.RequestException as error:
            raise RuntimeError("Could not reach the LLM provider. Check the connection and try again.") from error

    def _complete_json(self, system: str, user: str) -> str:
        if self.provider in {"OpenAI", "OpenRouter"}:
            return self._openai_compatible(system, user)
        if self.provider == "Anthropic":
            response = self.session.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": self.api_key, "anthropic-version": "2023-06-01"},
                json={"model": self.model, "max_tokens": 4096, "temperature": 0,
                      "system": system, "messages": [{"role": "user", "content": user}]},
                timeout=90,
            )
            self._raise_for_status(response)
            return "\n".join(block.get("text", "") for block in response.json().get("content", []))
        if self.provider == "Cohere":
            response = self.session.post(
                "https://api.cohere.com/v2/chat",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.model, "temperature": 0, "response_format": {"type": "json_object"},
                      "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]},
                timeout=90,
            )
            self._raise_for_status(response)
            return response.json()["message"]["content"][0]["text"]
        if self.provider == "Google Gemini":
            response = self.session.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
                headers={"x-goog-api-key": self.api_key},
                json={"systemInstruction": {"parts": [{"text": system}]},
                      "contents": [{"role": "user", "parts": [{"text": user}]}],
                      "generationConfig": {"temperature": 0, "responseMimeType": "application/json"}},
                timeout=90,
            )
            self._raise_for_status(response)
            return response.json()["candidates"][0]["content"]["parts"][0]["text"]
        raise ValueError("Unsupported LLM provider.")

    def _openai_compatible(self, system: str, user: str) -> str:
        base_url = "https://openrouter.ai/api/v1" if self.provider == "OpenRouter" else "https://api.openai.com/v1"
        response = self.session.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": self.model, "temperature": 0, "response_format": {"type": "json_object"},
                  "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]},
            timeout=90,
        )
        self._raise_for_status(response)
        return response.json()["choices"][0]["message"]["content"]

    @staticmethod
    def _raise_for_status(response: requests.Response) -> None:
        try:
            response.raise_for_status()
        except requests.HTTPError as error:
            raise RuntimeError(f"LLM provider request failed (HTTP {response.status_code}). Check the key, model, and quota.") from error


def create_llm_client(provider: str, api_key: str, model: str, mock: bool = False) -> LLMClient:
    if mock:
        return MockLLMClient()
    if not api_key:
        raise ValueError("Enter a provider API key or select Demo mode.")
    return ProviderClient(provider, api_key, model)
