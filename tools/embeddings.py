"""
tools/embeddings.py

Abstract embedding-provider interface + factory, mirroring
`llm/base.py` + `llm/__init__.py`'s pluggable-provider pattern exactly:
`agents/qa_agent.py` and `backend/services/embedding_service.py` depend
only on `EmbeddingProvider`, never a concrete backend, so swapping local
sentence-transformers for the OpenAI embeddings API is a `.env` change.

Default is "disabled" — TF-IDF retrieval works with zero setup, and
embeddings are an opt-in augmentation (see docs/RAG.md), not a
replacement, so a fresh install never silently requires a model download.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from functools import lru_cache

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class EmbeddingProvider(ABC):
    """Minimal text-embedding interface used for semantic retrieval."""

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text, same order."""
        raise NotImplementedError

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError


class NullEmbeddingProvider(EmbeddingProvider):
    """Used when embedding_provider=disabled — callers check `is_enabled`
    (or just catch the NotImplementedError) rather than calling embed()."""

    @property
    def name(self) -> str:
        return "disabled"

    def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError("Embeddings are disabled (EMBEDDING_PROVIDER=disabled in .env).")


def is_enabled() -> bool:
    return settings.embedding_provider != "disabled"


@lru_cache(maxsize=1)
def get_embedding_provider() -> EmbeddingProvider:
    provider = settings.embedding_provider

    if provider == "disabled":
        instance: EmbeddingProvider = NullEmbeddingProvider()
    elif provider == "sentence_transformers":
        from tools.sentence_transformer_provider import SentenceTransformerProvider

        instance = SentenceTransformerProvider(settings.embedding_model_name)
    elif provider == "openai":
        from tools.openai_embedding_provider import OpenAIEmbeddingProvider

        instance = OpenAIEmbeddingProvider(settings.openai_api_key or "")
    else:  # pragma: no cover - pydantic Literal already restricts this
        raise ValueError(f"Unknown EMBEDDING_PROVIDER: {provider}")

    logger.info("Embedding provider initialized: %s", instance.name)
    return instance
