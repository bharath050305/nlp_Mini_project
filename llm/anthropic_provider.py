"""
llm/anthropic_provider.py

Optional real LLM backend using Claude. Only imported/instantiated if
`LLM_PROVIDER=anthropic` in `.env` (see `llm/openai_provider.py` for why
this stays out of the default install).
"""

from __future__ import annotations

from llm.base import LLMProvider
from utils.exceptions import LLMProviderError
from utils.logger import get_logger

logger = get_logger(__name__)


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str, model: str) -> None:
        if not api_key:
            raise LLMProviderError(
                "LLM_PROVIDER=anthropic but ANTHROPIC_API_KEY is empty. "
                "Set it in .env, or switch LLM_PROVIDER back to 'mock'."
            )
        try:
            import anthropic  # local import: optional dependency
        except ImportError as exc:
            raise LLMProviderError(
                "The 'anthropic' package isn't installed. Run: "
                "pip install -r requirements-llm.txt"
            ) from exc

        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    @property
    def name(self) -> str:
        return f"anthropic:{self._model}"

    def complete(self, system_prompt: str, user_prompt: str, max_tokens: int = 500) -> str:
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return "".join(block.text for block in response.content if block.type == "text")
        except Exception as exc:
            logger.error("Anthropic API call failed: %s", exc)
            raise LLMProviderError(f"Anthropic API call failed: {exc}") from exc
