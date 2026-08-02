"""
agents/qa_agent.py

Retrieval-Augmented question answering over the uploaded report:
retrieve the most relevant chunks (`tools/vector_store.py`), then ask the
configured LLM to answer strictly from that retrieved context. This is
the RAG loop the brief asked for, with TF-IDF standing in for
FAISS + Sentence-Transformers (see `tools/vector_store.py` docstring and
`docs/RAG.md` for the full writeup).

Conversation memory: recent turns (fetched by the orchestrator from
`Repository.get_conversation_history`, which already persisted them —
this was a pure wiring gap) are folded into both the retrieval query
(so a follow-up like "what about my LDL?" still retrieves the right
chunk even though it names no topic of its own) and the LLM prompt (so
the answer can maintain conversational continuity). History is never a
source of facts by itself — only the retrieved report CONTEXT is.
"""

from __future__ import annotations

import numpy as np

from llm import get_llm_provider
from prompts import QA_SYSTEM_PROMPT, build_qa_prompt
from schemas import ConversationTurn, QAResult
from tools.embeddings import get_embedding_provider
from tools.embeddings import is_enabled as embeddings_enabled
from tools.vector_store import TfidfVectorStore
from utils.logger import get_logger

logger = get_logger(__name__)

# Thresholds on TF-IDF cosine similarity. These are deliberately simple and
# named as what they are — a proxy signal from retrieval strength, not a
# calibrated probability — because overstating confidence is worse than a
# rough-but-honest signal (survey Sec. 9.5, "explainable uncertainty").
_HIGH_CONFIDENCE_THRESHOLD = 0.35
_MEDIUM_CONFIDENCE_THRESHOLD = 0.12


def _confidence_from_score(top_score: float) -> str:
    if top_score >= _HIGH_CONFIDENCE_THRESHOLD:
        return "high"
    if top_score >= _MEDIUM_CONFIDENCE_THRESHOLD:
        return "medium"
    return "low"


def _build_history_block(history: list[ConversationTurn] | None) -> str:
    """Render the last few conversation turns as short 'asked/answered'
    lines for the prompt — keep it short, this is context, not the answer."""
    if not history:
        return ""
    lines = []
    for turn in history[-3:]:
        lines.append(f"Patient asked: {turn.user_message}")
        lines.append(f"Assistant answered: {turn.assistant_response}")
    return "\n".join(lines)


def _semantic_retrieve(repo, patient_id: int, query: str, k: int) -> list[tuple[str, float]]:
    """Cosine-similarity retrieval over embeddings stored in Postgres,
    spanning the patient's *entire* report history (not just the current
    one — see `docs/RAG.md`'s upgrade-path note, which this implements).

    Plain numpy over a plain Postgres array column, no pgvector: at this
    project's scale (one patient's chunks, not millions of vectors)
    brute-force cosine similarity is fully adequate, and pgvector has no
    official Windows binary to depend on.
    """
    candidates = repo.get_chunk_embeddings_for_patient(patient_id)
    if not candidates:
        return []

    query_vec = np.array(get_embedding_provider().embed([query])[0])
    query_norm = np.linalg.norm(query_vec)
    if query_norm == 0:
        return []

    texts = [c[0] for c in candidates]
    matrix = np.array([c[1] for c in candidates])
    sims = matrix @ query_vec / (np.linalg.norm(matrix, axis=1) * query_norm + 1e-10)

    top_idx = np.argsort(sims)[::-1][:k]
    return [(texts[i], float(sims[i])) for i in top_idx if sims[i] > 0]


def answer_question(
    report_text: str,
    question: str,
    k: int = 3,
    history: list[ConversationTurn] | None = None,
    repo=None,
    patient_id: int | None = None,
) -> QAResult:
    """Answer `question` using only content retrieved from `report_text`.

    `history` (recent conversation turns) broadens the *retrieval* query
    so a topic-less follow-up ("what about my LDL?") still pulls the
    right chunk, and is passed to the LLM as conversational context —
    but the answer is still grounded only in retrieved report text.

    `repo`/`patient_id` are optional: when given, and embeddings are
    enabled and the repo supports `get_chunk_embeddings_for_patient`
    (duck-typed — the legacy sqlite Repository simply doesn't, and this
    gracefully no-ops), semantic retrieval *augments* TF-IDF rather than
    replacing it — catching both lexical and semantic matches, degrading
    cleanly to TF-IDF-only otherwise.
    """
    store = TfidfVectorStore()
    store.index(report_text)

    retrieval_query = question
    if history:
        retrieval_query = f"{history[-1].user_message} {question}"

    scored = store.query_with_scores(retrieval_query, k=k)
    retrieved = [chunk for chunk, _score in scored]
    tfidf_top_score = max((score for _chunk, score in scored), default=0.0)

    semantic_top_score = 0.0
    if repo is not None and patient_id is not None and embeddings_enabled() and hasattr(
        repo, "get_chunk_embeddings_for_patient"
    ):
        semantic_matches = _semantic_retrieve(repo, patient_id, retrieval_query, k=k)
        if semantic_matches:
            semantic_top_score = semantic_matches[0][1]
            seen = set(retrieved)
            for chunk, _score in semantic_matches:
                if chunk not in seen:
                    retrieved.append(chunk)
                    seen.add(chunk)

    history_block = _build_history_block(history)
    prompt = build_qa_prompt(retrieved, question, history_block=history_block)
    llm = get_llm_provider()
    answer = llm.complete(QA_SYSTEM_PROMPT, prompt, max_tokens=300)
    confidence = _confidence_from_score(max(tfidf_top_score, semantic_top_score))

    logger.info(
        "QA answered via %s provider using %d retrieved chunk(s) (tfidf=%.3f, semantic=%.3f), "
        "confidence=%s, history=%d turn(s)",
        llm.name, len(retrieved), tfidf_top_score, semantic_top_score, confidence, len(history or []),
    )
    return QAResult(question=question, answer=answer, retrieved_chunks=retrieved, confidence=confidence)
