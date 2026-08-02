"""
agents/timeline_agent.py

Clinical Timeline Agent — new in this build. Reconstructs a chronological
view across every report a patient has uploaded in this system, the exact
capability the survey singles out for the "clinical notes" modality:
turning several time-stamped documents into one coherent timeline rather
than treating each upload as a fresh, disconnected conversation (survey
Sec. 4.1.3).

This is the most distinctly *NLP* of the new agents: it depends entirely
on named-entity extraction (already run per-report) plus simple set-diffing
across time, no new external tool or model.
"""

from __future__ import annotations

import json

from schemas import ExtractedEntities, TimelineEvent
from tools.database import Repository
from tools.medical_ner import extract_entities
from utils.logger import get_logger

logger = get_logger(__name__)


def _entities_for_report(repo: Repository, report) -> ExtractedEntities:
    """Reuse cached entities if this report was already analyzed; otherwise
    run NER once and cache the result back onto the row."""
    if report.entities_json:
        try:
            return ExtractedEntities(**json.loads(report.entities_json))
        except (json.JSONDecodeError, TypeError):
            pass  # fall through and recompute

    entities = extract_entities(report.raw_text)
    repo.update_report_analysis(report.id, summary_json=report.summary_json, entities_json=entities.model_dump_json())
    return entities


def build_timeline(repo: Repository, patient_id: int) -> list[TimelineEvent]:
    """Build a chronological timeline across every report this patient has uploaded.

    Each event lists what was found in that report, plus what's genuinely
    new compared to the previous one — the "what changed" view that makes
    a timeline useful rather than just a repeated dump of everything.
    """
    reports = repo.list_reports(patient_id)
    events: list[TimelineEvent] = []
    seen_diseases: set[str] = set()
    seen_medicines: set[str] = set()

    for report in reports:
        entities = _entities_for_report(repo, report)
        diseases = {d.lower() for d in entities.diseases}
        medicines = {m.lower() for m in entities.medicines}

        new_diseases = sorted(diseases - seen_diseases)
        new_medicines = sorted(medicines - seen_medicines)
        new_since_previous = (
            [f"New condition mentioned: {d}" for d in new_diseases]
            + [f"New medicine mentioned: {m}" for m in new_medicines]
        )

        events.append(
            TimelineEvent(
                report_filename=report.filename,
                uploaded_at=str(report.created_at) if report.created_at else "unknown date",
                diseases=sorted(entities.diseases),
                medicines=sorted(entities.medicines),
                lab_values=sorted(entities.lab_values),
                new_since_previous=new_since_previous if events else [],  # first report has no "previous"
            )
        )
        seen_diseases |= diseases
        seen_medicines |= medicines

    logger.info("Built timeline with %d event(s) for patient %s", len(events), patient_id)
    return events
