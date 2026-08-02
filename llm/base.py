"""
llm/base.py

Abstract interface every LLM backend implements. Agents depend only on
this interface (via `get_llm_provider()` in `llm/__init__.py`), never on
a concrete provider — swapping mock/OpenAI/Anthropic is a `.env` change,
not a code change.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Minimal chat-completion interface used across all agents."""

    @abstractmethod
    def complete(self, system_prompt: str, user_prompt: str, max_tokens: int = 500) -> str:
        """Return a single completion for the given system/user prompt pair."""
        raise NotImplementedError

    @property
    @abstractmethod
    def name(self) -> str:
        """Short identifier shown in logs/UI, e.g. 'mock', 'openai:gpt-4o-mini'."""
        raise NotImplementedError
