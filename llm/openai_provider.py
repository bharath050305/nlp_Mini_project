"""
llm/openai_provider.py

Optional real LLM backend. Only imported/instantiated if
`LLM_PROVIDER=openai` in `.env` — the `openai` package is intentionally
kept out of `requirements.txt` (see `requirements-llm.txt`) so the app
installs and runs with zero paid dependencies by default.
"""

from __future__ import annotations

from llm.base import LLMProvider
from utils.exceptions import LLMProviderError
from utils.logger import get_logger

logger = get_logger(__name__)


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str) -> None:
        if not api_key:
            raise LLMProviderError(
                "LLM_PROVIDER=openai but OPENAI_API_KEY is empty. "
                "Set it in .env, or switch LLM_PROVIDER back to 'mock'."
            )
        try:
            from openai import OpenAI  # local import: optional dependency
        except ImportError as exc:
            raise LLMProviderError(
                "The 'openai' package isn't installed. Run: "
                "pip install -r requirements-llm.txt"
            ) from exc

        self._client = OpenAI(api_key=api_key)
        self._model = model

    @property
    def name(self) -> str:
        return f"openai:{self._model}"

    def complete(self, system_prompt: str, user_prompt: str, max_tokens: int = 500) -> str:
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            logger.error("OpenAI API call failed: %s", exc)
            raise LLMProviderError(f"OpenAI API call failed: {exc}") from exc
