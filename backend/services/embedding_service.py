"""
backend/services/embedding_service.py

Computes and persists chunk embeddings for a report, once, at
upload/finalize time — rather than re-embedding a report's text on every
question asked (the exact inefficiency `docs/RAG.md` flagged as today's
per-request TF-IDF limitation). No-ops cleanly when embeddings are
disabled (the default), so callers never need an `if enabled` check.
"""

from __future__ import annotations

from backend.pg_repository import PgRepository
from tools.embeddings import get_embedding_provider, is_enabled
from utils.logger import get_logger
from utils.text_cleaning import chunk_text

logger = get_logger(__name__)


def embed_and_store_report(repo: PgRepository, report_id: int, text: str) -> int:
    """Chunk + embed `text` and store the vectors against `report_id`.
    Returns the number of chunks stored (0 if embeddings are disabled)."""
    if not is_enabled():
        return 0

    chunks = chunk_text(text)
    if not chunks:
        return 0

    provider = get_embedding_provider()
    vectors = provider.embed(chunks)
    repo.replace_chunk_embeddings(report_id, list(zip(chunks, vectors, strict=True)))

    logger.info("Embedded %d chunk(s) for report %s via %s", len(chunks), report_id, provider.name)
    return len(chunks)
