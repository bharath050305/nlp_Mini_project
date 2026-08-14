"""
backend/routers/digital_twin.py

Patient Digital Twin (v5) — explicitly a consolidated read-model, not new
reasoning. Every field here is computed by an existing agent/helper
(entity extraction, lab analysis, triage, dose-log adherence math); this
endpoint just assembles them into one response instead of the frontend
making five separate calls and stitching them together itself.

Doctor/nurse only, same as analytics — this is care-team monitoring
tooling, not a patient-facing view.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from agents.lab_analysis import analyze_lab_values
from agents.timeline_agent import build_timeline, get_or_compute_entities
from agents.triage_agent import assess_risk
from backend import db_models
from backend.db import get_db
from backend.deps import get_current_user, require_patient_access
from backend.pg_repository import PgRepository
from backend.schemas_api import DigitalTwin

router = APIRouter(prefix="/api/patients/{patient_id}/digital-twin", tags=["digital-twin"])


def _require_clinical_staff(current_user) -> None:
    if current_user.role not in ("doctor", "nurse"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "The Digital Twin view is available to doctors and nurses only.")


@router.get("", response_model=DigitalTwin)
def get_digital_twin(
    patient=Depends(require_patient_access),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DigitalTwin:
    _require_clinical_staff(current_user)
    repo = PgRepository(db)

    reports = repo.list_reports(patient.id)
    latest_report = reports[-1] if reports else None
    latest_entities = get_or_compute_entities(repo, latest_report) if latest_report else None

    # Reuse the exact same lab-value analysis + triage rules the chat
    # pipeline uses (agents/lab_analysis.py, agents/triage_agent.py) —
    # the Digital Twin's risk level is the same computation, not a
    # second, drifting implementation of it.
    latest_lab_readings = analyze_lab_values(latest_entities.lab_values) if latest_entities else []
    triage = assess_risk(latest_entities, latest_lab_readings, user_text="")

    active_reminders = db.query(db_models.Reminder).filter_by(patient_id=patient.id, active=True).all()

    thirty_days_ago = datetime.now(UTC) - timedelta(days=30)
    all_logs = (
        db.query(db_models.DoseLog)
        .join(db_models.Reminder, db_models.Reminder.id == db_models.DoseLog.reminder_id)
        .filter(db_models.Reminder.patient_id == patient.id, db_models.DoseLog.taken_at >= thirty_days_ago)
        .all()
    )
    taken = sum(1 for log in all_logs if log.status == "taken")
    missed = sum(1 for log in all_logs if log.status == "missed_auto")
    denominator = taken + missed
    overall_adherence_pct = round((taken / denominator * 100), 1) if denominator else 0.0

    week_ago = datetime.now(UTC) - timedelta(days=7)
    doses_missed_this_week = sum(1 for log in all_logs if log.status == "missed_auto" and log.taken_at >= week_ago)

    timeline = build_timeline(repo, patient.id)

    return DigitalTwin(
        patient_id=patient.id,
        patient_name=patient.name,
        latest_report_filename=latest_report.filename if latest_report else None,
        latest_report_date=latest_report.created_at if latest_report else None,
        total_reports=len(reports),
        diseases=sorted(latest_entities.diseases) if latest_entities else [],
        medicines=sorted(latest_entities.medicines) if latest_entities else [],
        symptoms=sorted(latest_entities.symptoms) if latest_entities else [],
        triage_level=triage.level,
        triage_reasons=triage.reasons,
        active_reminders=len(active_reminders),
        overall_adherence_pct=overall_adherence_pct,
        doses_missed_this_week=doses_missed_this_week,
        timeline_event_count=len(timeline),
    )
