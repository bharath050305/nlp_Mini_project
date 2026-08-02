"""
agents/transcript_agent.py

Transcript-to-report agent. Takes an already-transcribed consultation
(tools/speech_to_text.py did the audio -> text step) and structures it
into a SOAP note (Subjective/Objective/Assessment/Plan), the same
"deterministic extraction + LLM narrative" split `summarizer_agent.py`
uses: NER runs first on the transcript text (same tool, same vocab), then
the LLM only ever narrates facts already surfaced by NER — it never
free-associates a diagnosis from nothing.

The result is always a *draft* — the doctor reviews/edits every field via
PATCH /api/transcripts/{id}/soap before finalizing (backend/routers
/transcripts.py), the same review-before-signoff pattern the governance
layer already uses for reminders (A2: execute-with-gates).
"""

from __future__ import annotations

import re

from llm import get_llm_provider
from prompts import SOAP_SYSTEM_PROMPT, build_soap_prompt
from schemas import ExtractedEntities, SOAPNote
from tools.medical_ner import extract_entities
from utils.logger import get_logger

logger = get_logger(__name__)

_SECTION_PATTERN = re.compile(
    r"SUBJECTIVE:\s*(?P<subjective>.*?)\s*OBJECTIVE:\s*(?P<objective>.*?)\s*"
    r"ASSESSMENT:\s*(?P<assessment>.*?)\s*PLAN:\s*(?P<plan>.*)",
    re.IGNORECASE | re.DOTALL,
)


def _parse_soap_sections(raw: str) -> tuple[str, str, str, str]:
    match = _SECTION_PATTERN.search(raw)
    if not match:
        # Fallback: couldn't find the expected markers — surface the whole
        # response under Subjective rather than silently dropping content.
        logger.warning("Could not parse SOAP markers from LLM output; returning raw text under Subjective.")
        return raw.strip(), "Not discussed.", "Not discussed.", "Not discussed."
    return (
        match.group("subjective").strip() or "Not discussed.",
        match.group("objective").strip() or "Not discussed.",
        match.group("assessment").strip() or "Not discussed.",
        match.group("plan").strip() or "Not discussed.",
    )


def _estimate_confidence(entities: ExtractedEntities) -> str:
    """Same honest-confidence philosophy as summarizer_agent: 'high' only
    when the transcript actually contained recognizable clinical entities
    to ground the note in, not a flat default."""
    if entities.diseases and (entities.medicines or entities.symptoms):
        return "high"
    if entities.diseases or entities.medicines or entities.symptoms:
        return "medium"
    return "low"


def structure_soap_note(transcript_text: str) -> SOAPNote:
    """Extract entities from the raw transcript, then structure a draft
    SOAP note via the configured LLM provider (mock by default)."""
    entities = extract_entities(transcript_text)

    prompt = build_soap_prompt(
        transcript_text=transcript_text[:4000],
        diseases=entities.diseases,
        medicines=entities.medicines,
        symptoms=entities.symptoms,
    )

    llm = get_llm_provider()
    raw_response = llm.complete(SOAP_SYSTEM_PROMPT, prompt, max_tokens=600)
    subjective, objective, assessment, plan = _parse_soap_sections(raw_response)
    confidence = _estimate_confidence(entities)

    logger.info("SOAP note drafted via %s provider (confidence=%s)", llm.name, confidence)
    return SOAPNote(subjective=subjective, objective=objective, assessment=assessment, plan=plan, confidence=confidence)
