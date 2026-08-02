"""
tools/openai_embedding_provider.py

Optional alternative semantic-search backend: OpenAI's embeddings API,
reusing the same `openai_api_key` already used by `llm/openai_provider.py`
and `tools/whisper_api_provider.py`. No local model download, but needs a
key and a network call per batch of chunks embedded.
"""

from __future__ import annotations

from tools.embeddings import EmbeddingProvider
from utils.exceptions import MediAgentError
from utils.logger import get_logger

logger = get_logger(__name__)

_MODEL = "text-embedding-3-small"


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise MediAgentError(
                "EMBEDDING_PROVIDER=openai but OPENAI_API_KEY is empty. "
                "Set it in .env, or switch EMBEDDING_PROVIDER back to 'sentence_transformers'/'disabled'."
            )
        try:
            from openai import OpenAI  # local import: optional dependency
        except ImportError as exc:
            raise MediAgentError(
                "The 'openai' package isn't installed. Run: pip install -r requirements-llm.txt"
            ) from exc

        self._client = OpenAI(api_key=api_key)

    @property
    def name(self) -> str:
        return f"openai:{_MODEL}"

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            response = self._client.embeddings.create(model=_MODEL, input=texts)
        except Exception as exc:
            raise MediAgentError(f"OpenAI embeddings API call failed: {exc}") from exc
        return [item.embedding for item in response.data]
