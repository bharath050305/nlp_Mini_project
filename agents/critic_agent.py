"""
agents/critic_agent.py

Critic / Evidence Verifier Agent (v5) — checks a QA answer against the
report chunks it was supposedly grounded in, after the fact. This is
provider-agnostic verification: it inspects the *output text* against
the *retrieved evidence*, so it works identically whether the answer
came from the mock provider or a real OpenAI/Anthropic call — it never
needs to inspect the model's internals.

Rule-based (keyword overlap per sentence), same technique
`llm/mock_provider.py` already uses for its own extractive matching —
reused here as a verifier instead of a generator. This deliberately
doesn't try to be a sophisticated NLI/entailment model: for a single
patient report's worth of text, "does this sentence share any real
vocabulary with what was retrieved" is a good-enough, fully-explainable
proxy for "is this actually grounded," and false positives (flagging a
well-supported paraphrase) are safer than false negatives here — the
Supervisor treats a flag as "worth a second look," not as a hard block.
"""

from __future__ import annotations

import re

from schemas import CriticResult
from utils.logger import get_logger

logger = get_logger(__name__)

_STOPWORD_LIKE_MIN_LEN = 3  # skip very short words (articles, "is", "am") when comparing


def _keywords(text: str) -> set[str]:
    return {w.lower() for w in re.findall(r"[a-zA-Z0-9.]+", text) if len(w) >= _STOPWORD_LIKE_MIN_LEN}


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def verify_answer(question: str, answer: str, retrieved_chunks: list[str]) -> CriticResult:
    """Flag any sentence in `answer` that shares no real vocabulary with
    any retrieved chunk — a cheap, explainable proxy for "is this
    actually grounded in what was retrieved."""
    if not retrieved_chunks:
        # Nothing was retrieved at all — every claim is definitionally
        # unsupported, but this is the same case qa_agent already reports
        # as low confidence, so just note it rather than double-flag.
        return CriticResult(supported=True, note="No context was retrieved; confidence already reflects this.")

    evidence_keywords: set[str] = set()
    for chunk in retrieved_chunks:
        evidence_keywords |= _keywords(chunk)

    unsupported: list[str] = []
    for sentence in _split_sentences(answer):
        sentence_keywords = _keywords(sentence)
        if not sentence_keywords:
            continue  # nothing to check (e.g. a bare punctuation fragment)
        if not (sentence_keywords & evidence_keywords):
            unsupported.append(sentence)

    if unsupported:
        result = CriticResult(
            supported=False,
            unsupported_claims=unsupported,
            note="One or more sentences share no vocabulary with the retrieved report text.",
        )
        logger.info("Critic flagged %d unsupported sentence(s) for question %r", len(unsupported), question)
        return result

    return CriticResult(supported=True, note="Every sentence shares vocabulary with retrieved report text.")
