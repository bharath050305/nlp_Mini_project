"""
agents/summarizer_agent.py

Medical Summarizer Agent. Combines two layers deliberately:

1. Deterministic, rule-based "abnormal value" flagging straight off the
   NER output (regex-extracted lab values compared against a small
   reference-range table) — this part must never hallucinate.
2. An LLM call (mock by default) for the natural-language narrative and
   recommendations, using only the facts surfaced in step 1.
"""

from __future__ import annotations

import re

from llm import get_llm_provider
from prompts import SUMMARIZER_SYSTEM_PROMPT, build_summarizer_prompt
from schemas import EvidenceItem, ExtractedEntities, ReportSummary
from utils.logger import get_logger

logger = get_logger(__name__)

# (regex to pull the number out of a LAB_VALUE string, low, high, unit label)
# Deliberately small and named-value based — a real system would key this
# off the LAB_TEST name too, but for a mini project a handful of the most
# common reference ranges is enough to make "abnormal value flagging"
# genuinely demonstrable rather than hand-waved.
_RANGE_CHECKS: list[tuple[re.Pattern, float, float, str]] = [
    (re.compile(r"(\d+(\.\d+)?)\s?%"), 4.0, 5.6, "HbA1c/percentage value"),
    (re.compile(r"(\d+(\.\d+)?)\s?mg/dl"), 70, 140, "mg/dL value"),
    (re.compile(r"(\d+(\.\d+)?)\s?mmhg"), 90, 120, "blood pressure value"),
    (re.compile(r"(\d+(\.\d+)?)\s?bpm"), 60, 100, "heart-rate value"),
]


def _check_lab_values(lab_values: list[str]) -> tuple[list[str], list[EvidenceItem]]:
    """Check each lab value against a small reference-range table.

    Returns (abnormal_value_strings, full_evidence_trail). The evidence
    trail — new in this build — includes every value that was actually
    checked, not just the ones flagged abnormal, so a reader can see what
    the system *did* check rather than only what it's warning about
    (survey Sec. 9.5: explanations should reveal the reasoning process,
    not just the conclusion). Anything that doesn't match a known pattern
    is left uncommented on rather than guessed at — silence is safer than
    a false "abnormal" label.
    """
    abnormal: list[str] = []
    evidence: list[EvidenceItem] = []
    for value in lab_values:
        for pattern, low, high, label in _RANGE_CHECKS:
            m = pattern.search(value.lower())
            if m:
                num = float(m.group(1))
                is_abnormal = num < low or num > high
                range_str = f"{low}-{high}"
                if is_abnormal:
                    abnormal.append(f"{value} (outside typical {label} range {range_str})")
                    claim = f"{value} is outside the typical range for a {label}"
                else:
                    claim = f"{value} is within the typical range for a {label}"
                evidence.append(EvidenceItem(claim=claim, evidence=f"Detected value: {value}", reference_range=range_str))
                break
    return abnormal, evidence


def _parse_llm_summary(raw: str) -> tuple[str, list[str]]:
    """Split the LLM's free text into (narrative_paragraph, recommendation_lines)."""
    if "Recommendations:" not in raw:
        return raw.strip(), []
    narrative, _, rec_block = raw.partition("Recommendations:")
    recs = [ln.lstrip("- ").strip() for ln in rec_block.strip().splitlines() if ln.strip()]
    return narrative.strip(), recs


def _estimate_confidence(entities: ExtractedEntities, evidence: list[EvidenceItem]) -> str:
    """Honest confidence signal: 'high' only when at least one lab value was
    actually range-checked (concrete, verifiable evidence exists); 'medium'
    when we found clinical entities but nothing numeric to check; 'low' when
    the extractor found essentially nothing to go on.
    """
    if evidence:
        return "high"
    if entities.diseases or entities.medicines or entities.symptoms:
        return "medium"
    return "low"


def summarize_report(report_text: str, entities: ExtractedEntities) -> ReportSummary:
    """Produce a `ReportSummary` for one report, given its already-extracted entities."""
    abnormal, evidence = _check_lab_values(entities.lab_values)
    key_findings = (
        [f"Disease/condition mentioned: {d}" for d in entities.diseases]
        + [f"Symptom mentioned: {s}" for s in entities.symptoms]
        + [f"Lab test performed: {t}" for t in entities.lab_tests]
    )

    excerpt = report_text[:1500]
    prompt = build_summarizer_prompt(
        report_excerpt=excerpt,
        diseases=entities.diseases,
        medicines=entities.medicines,
        symptoms=entities.symptoms,
        lab_values=entities.lab_values,
        abnormal_values=abnormal,
    )

    llm = get_llm_provider()
    raw_response = llm.complete(SUMMARIZER_SYSTEM_PROMPT, prompt, max_tokens=400)
    narrative, recommendations = _parse_llm_summary(raw_response)
    confidence = _estimate_confidence(entities, evidence)

    logger.info(
        "Summary generated via %s provider (%d abnormal values flagged, confidence=%s)",
        llm.name, len(abnormal), confidence,
    )
    return ReportSummary(
        patient_summary=narrative,
        key_findings=key_findings,
        abnormal_values=abnormal,
        recommendations=recommendations,
        evidence=evidence,
        confidence=confidence,
    )
