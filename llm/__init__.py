"""
llm/__init__.py

Factory for the configured LLM provider. Every agent calls
`get_llm_provider()` instead of importing a concrete provider class —
this is the one place `settings.llm_provider` is branched on.
"""

from __future__ import annotations

from functools import lru_cache

from config import settings
from llm.base import LLMProvider
from utils.logger import get_logger

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def get_llm_provider() -> LLMProvider:
    """Return the single, cached LLM provider instance for this process."""
    provider = settings.llm_provider

    if provider == "mock":
        from llm.mock_provider import MockLLMProvider

        instance: LLMProvider = MockLLMProvider()
    elif provider == "openai":
        from llm.openai_provider import OpenAIProvider

        instance = OpenAIProvider(settings.openai_api_key or "", settings.openai_model)
    elif provider == "anthropic":
        from llm.anthropic_provider import AnthropicProvider

        instance = AnthropicProvider(settings.anthropic_api_key or "", settings.anthropic_model)
    else:  # pragma: no cover - pydantic Literal already restricts this
        raise ValueError(f"Unknown LLM_PROVIDER: {provider}")

    logger.info("LLM provider initialized: %s", instance.name)
    return instance
