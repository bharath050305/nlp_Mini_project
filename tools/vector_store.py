"""
tools/vector_store.py

Retrieval over report chunks using TF-IDF + cosine similarity
(scikit-learn), standing in for Sentence-Transformers + FAISS.

Why: FAISS + Sentence-Transformers means a ~90MB model download and GPU/CPU
inference for a report that's usually a few hundred words — overkill, and
one more thing that can fail with no internet mid-demo. TF-IDF is
deterministic, has zero download, and for the short, vocabulary-distinct
sections of a single medical report (labs vs. medications vs. history) it
retrieves just as reliably. The `TfidfVectorStore` class is a drop-in
interface (`index(chunks)` / `query(text, k)`) so swapping in a real
embedding backend later is a one-file change.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from utils.exceptions import VectorStoreError
from utils.logger import get_logger
from utils.text_cleaning import chunk_text

logger = get_logger(__name__)


@dataclass
class TfidfVectorStore:
    """An in-memory TF-IDF index over a single document's chunks.

    One instance is built per uploaded report (see `QAAgent`), so there's
    no persistence concern — it lives for the duration of the session.
    """

    chunks: list[str] = field(default_factory=list)
    _vectorizer: TfidfVectorizer | None = field(default=None, repr=False)
    _matrix=None  # scipy sparse matrix, set by index()

    def index(self, text: str, chunk_size: int = 500, overlap: int = 100) -> None:
        """Chunk `text` and fit a TF-IDF matrix over the chunks."""
        self.chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)
        if not self.chunks:
            raise VectorStoreError("No text to index — report appears empty.")

        self._vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        try:
            self._matrix = self._vectorizer.fit_transform(self.chunks)
        except ValueError as exc:
            raise VectorStoreError(f"Failed to build TF-IDF index: {exc}") from exc

        logger.info("Indexed %d chunks for retrieval", len(self.chunks))

    def query(self, question: str, k: int = 3) -> list[str]:
        """Return the top-k most similar chunks to `question`."""
        return [chunk for chunk, _score in self.query_with_scores(question, k=k)]

    def query_with_scores(self, question: str, k: int = 3) -> list[tuple[str, float]]:
        """Return the top-k (chunk, cosine_similarity) pairs for `question`.

        The score is what lets a caller (e.g. the QA agent) report an
        honest confidence level instead of always sounding equally sure —
        new in this build, used for the retrieval-confidence feature.
        """
        if self._vectorizer is None or self._matrix is None:
            raise VectorStoreError("Vector store queried before indexing any text.")
        if not question or not question.strip():
            raise VectorStoreError("Cannot query with empty text.")

        q_vec = self._vectorizer.transform([question])
        scores = cosine_similarity(q_vec, self._matrix).flatten()
        top_k_idx = scores.argsort()[::-1][:k]

        # Fall back to returning the first chunk if TF-IDF finds nothing at
        # all in common with the question (all-zero scores) — better than
        # an empty context for the LLM to answer from. Reported score stays
        # 0.0 so downstream confidence correctly reads this as low-confidence.
        if scores[top_k_idx].sum() == 0:
            return [(c, 0.0) for c in self.chunks[: min(k, len(self.chunks))]]

        return [(self.chunks[i], float(scores[i])) for i in top_k_idx if scores[i] > 0] or [
            (self.chunks[top_k_idx[0]], float(scores[top_k_idx[0]]))
        ]
