"""
tools/sentence_transformer_provider.py

Default semantic-search backend: the pip `sentence-transformers` package
running fully locally — one-time ~80MB model download (all-MiniLM-L6-v2
by default), no API key needed afterward. Lazy-loaded on first `.embed()`
call, same pattern as `tools/whisper_local_provider.py`.
"""

from __future__ import annotations

from tools.embeddings import EmbeddingProvider
from utils.exceptions import MediAgentError
from utils.logger import get_logger

logger = get_logger(__name__)


class SentenceTransformerProvider(EmbeddingProvider):
    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self._model_name = model_name
        self._model = None  # lazy-loaded

    @property
    def name(self) -> str:
        return f"sentence_transformers:{self._model_name}"

    def _load_model(self):
        if self._model is not None:
            return self._model
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise MediAgentError(
                "EMBEDDING_PROVIDER=sentence_transformers but the "
                "'sentence-transformers' package isn't installed. Run: "
                "pip install -r requirements-semantic-search.txt"
            ) from exc

        logger.info("Loading sentence-transformers model '%s' (first use, may take a while)...", self._model_name)
        self._model = SentenceTransformer(self._model_name)
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self._load_model()
        vectors = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
        return [v.tolist() for v in vectors]
