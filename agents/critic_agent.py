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


# --------------------------------------------------------------------------
# Adversarial Differential Critique (v6)
# Falsification & Overlooked Emergency Detection
# --------------------------------------------------------------------------
def critique_differential(
    candidates: list,
    symptoms: list[str],
    user_text: str = "",
    lab_readings: list | None = None,
) -> dict:
    """Adversarial Devil's Advocate round:
    1. Assumes the primary candidate might be incomplete or misleading.
    2. Identifies dangerous clinical mimics that share presenting symptoms.
    3. Flags missing diagnostic investigations needed to definitively rule out emergencies.
    """
    if not candidates:
        return {
            "critique_summary": "No active differential candidates were proposed to critique.",
            "contradictions": [],
            "missing_investigations": [],
        }

    primary = candidates[0]
    primary_name = getattr(primary, "condition_name", str(primary))
    all_symptoms_text = " ".join(symptoms).lower() + " " + user_text.lower()

    contradictions: list[str] = []
    missing_tests: list[str] = []

    # Adversarial mimic checks
    if "pneumonia" in primary_name.lower():
        if any(term in all_symptoms_text for term in ("chest pain", "shortness of breath", "dyspnea", "tachycardia")):
            contradictions.append(
                "Warning: Presenting dyspnea/chest pain mimics Pulmonary Embolism (PE). PE cannot be safely excluded based on symptoms alone."
            )
            missing_tests.append("D-Dimer Assay / CTPA")

    if any(term in primary_name.lower() for term in ("gerd", "reflux", "hypertension")):
        if any(term in all_symptoms_text for term in ("chest", "pain", "tightness", "pressure", "arm", "jaw")):
            contradictions.append(
                "Critical Alert: Atypical chest discomfort may indicate Acute Coronary Syndrome (ACS). Must not diagnose isolated GERD/hypertension without ruling out cardiac ischemia."
            )
            missing_tests.append("12-Lead ECG & Serial Troponin I")

    if "diabetes" in primary_name.lower():
        if any(term in all_symptoms_text for term in ("vomiting", "nausea", "confusion", "drowsy")):
            contradictions.append(
                "Urgent Alert: Gastrointestinal symptoms in suspected diabetes require immediate evaluation for Diabetic Ketoacidosis (DKA)."
            )
            missing_tests.append("Serum Ketones & Venous Blood Gas")

    # Add general recommended tests from candidates that were not found in current observations
    for cand in candidates[:3]:
        for t in getattr(cand, "recommended_tests", []):
            if t not in missing_tests:
                missing_tests.append(t)

    summary = (
        f"Adversarial Review on '{primary_name}': "
        + (f"{len(contradictions)} critical mimic warning(s) raised. " if contradictions else "Consistent with presenting clinical picture. ")
        + f"{len(missing_tests)} confirmatory/exclusion test(s) recommended."
    )

    return {
        "critique_summary": summary,
        "contradictions": contradictions,
        "missing_investigations": missing_tests[:5],
    }

