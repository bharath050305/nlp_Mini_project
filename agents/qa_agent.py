"""
agents/qa_agent.py

Retrieval-Augmented question answering over the uploaded report:
retrieve the most relevant chunks (`tools/vector_store.py`), then ask the
configured LLM to answer strictly from that retrieved context. This is
the RAG loop the brief asked for, with TF-IDF standing in for
FAISS + Sentence-Transformers (see `tools/vector_store.py` docstring).
"""

from __future__ import annotations

from llm import get_llm_provider
from prompts import QA_SYSTEM_PROMPT, build_qa_prompt
from schemas import QAResult
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


def answer_question(report_text: str, question: str, k: int = 3) -> QAResult:
    """Answer `question` using only content retrieved from `report_text`."""
    store = TfidfVectorStore()
    store.index(report_text)
    scored = store.query_with_scores(question, k=k)
    retrieved = [chunk for chunk, _score in scored]
    top_score = max((score for _chunk, score in scored), default=0.0)

    prompt = build_qa_prompt(retrieved, question)
    llm = get_llm_provider()
    answer = llm.complete(QA_SYSTEM_PROMPT, prompt, max_tokens=300)
    confidence = _confidence_from_score(top_score)

    logger.info(
        "QA answered via %s provider using %d retrieved chunk(s), confidence=%s (top_score=%.3f)",
        llm.name, len(retrieved), confidence, top_score,
    )
    return QAResult(question=question, answer=answer, retrieved_chunks=retrieved, confidence=confidence)
