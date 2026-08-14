"""
agents/triage_agent.py

Clinical Risk/Triage Agent (v5) — classifies the current situation into
LOW / MEDIUM / HIGH / CRITICAL. Deliberately rule-based, not an LLM call:
the LLM never independently decides emergency care. This is the same
"deterministic tool, not a model guess" pattern already used by
`agents/drug_interaction_agent.py` (curated table) and the mock LLM
provider (regex-driven, not generative) — extended here to the single
highest-stakes decision this system makes.

Escalation ladder, evaluated in order (first match wins):
1. A curated critical-symptom keyword appears in the patient's own words
   or NER-extracted symptoms -> CRITICAL, always. This never depends on
   lab values being present at all — a "chest pain" message should
   escalate even with no report loaded.
2. Any lab reading more than 2x outside its reference range -> HIGH.
3. Any abnormal reading at all -> MEDIUM.
4. Otherwise -> LOW.

This never diagnoses or prescribes — it only decides how urgently a
human (the patient, and via the Supervisor's escalation, a doctor/nurse)
should look at this. See agents/supervisor_agent.py for what happens
with a HIGH/CRITICAL result.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from schemas import ExtractedEntities, LabReading, TriageResult
from utils.logger import get_logger

logger = get_logger(__name__)

_VOCAB_PATH = Path(__file__).resolve().parent.parent / "data" / "medical_vocab" / "critical_symptoms.txt"

# How far outside the reference range counts as "severe" rather than just
# "abnormal" — 2x the boundary value, matching the plan's stated rule.
# Deliberately simple and named as what it is, same honesty-over-precision
# rationale as agents/qa_agent.py's confidence thresholds.
_SEVERE_MULTIPLIER = 2.0


@lru_cache(maxsize=1)
def _load_critical_symptoms() -> list[str]:
    with open(_VOCAB_PATH, encoding="utf-8") as f:
        return [line.strip().lower() for line in f if line.strip()]


def _matched_critical_symptoms(text: str) -> list[str]:
    text_lower = text.lower()
    return [phrase for phrase in _load_critical_symptoms() if re.search(re.escape(phrase), text_lower)]


def _is_severe(reading: LabReading) -> bool:
    try:
        low_str, high_str = reading.reference_range.split("-")
        low, high = float(low_str), float(high_str)
    except (ValueError, AttributeError):
        return False
    if reading.numeric_value > high:
        return reading.numeric_value > high * _SEVERE_MULTIPLIER
    if reading.numeric_value < low:
        return low > 0 and reading.numeric_value < low / _SEVERE_MULTIPLIER
    return False


def assess_risk(
    entities: ExtractedEntities | None,
    lab_readings: list[LabReading],
    user_text: str = "",
) -> TriageResult:
    """Classify current risk level from extracted entities, lab readings,
    and the patient's own message text (for symptom keywords not
    necessarily captured by NER)."""
    combined_symptom_text = " ".join(entities.symptoms if entities else []) + " " + user_text
    critical_matches = _matched_critical_symptoms(combined_symptom_text)
    if critical_matches:
        result = TriageResult(
            level="critical",
            reasons=[f"Critical symptom keyword detected: '{m}'" for m in critical_matches],
        )
        logger.warning("Triage CRITICAL: %s", result.reasons)
        return result

    severe_readings = [r for r in lab_readings if r.is_abnormal and _is_severe(r)]
    if severe_readings:
        result = TriageResult(
            level="high",
            reasons=[
                f"{r.raw_value} is more than {_SEVERE_MULTIPLIER:.0f}x outside the typical "
                f"{r.label} range ({r.reference_range})"
                for r in severe_readings
            ],
        )
        logger.info("Triage HIGH: %s", result.reasons)
        return result

    abnormal_readings = [r for r in lab_readings if r.is_abnormal]
    if abnormal_readings:
        result = TriageResult(
            level="medium",
            reasons=[
                f"{r.raw_value} is outside the typical {r.label} range ({r.reference_range})"
                for r in abnormal_readings
            ],
        )
        logger.info("Triage MEDIUM: %s", result.reasons)
        return result

    return TriageResult(level="low", reasons=["No abnormal lab values or critical symptoms detected."])
