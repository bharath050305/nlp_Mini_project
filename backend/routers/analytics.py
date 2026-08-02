"""
backend/routers/analytics.py

Doctor/nurse analytics: lab-value trends over time, medicine-reminder
adherence, and an at-a-glance summary — the data behind the doctor
dashboard's charts. Doctor/nurse only (not patient, not staff): this is
clinical-monitoring tooling for the care team, distinct from the
patient's own report/reminder views.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from agents.lab_analysis import analyze_lab_values
from agents.timeline_agent import get_or_compute_entities
from backend import db_models
from backend.db import get_db
from backend.deps import get_current_user, require_patient_access
from backend.pg_repository import PgRepository
from backend.schemas_api import AnalyticsSummary, LabTrendPoint, ReminderAdherence

router = APIRouter(prefix="/api/patients/{patient_id}/analytics", tags=["analytics"])


def _require_clinical_staff(current_user) -> None:
    if current_user.role not in ("doctor", "nurse"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Analytics are available to doctors and nurses only.")


@router.get("/lab-trends", response_model=list[LabTrendPoint])
def lab_trends(
    patient=Depends(require_patient_access),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[LabTrendPoint]:
    _require_clinical_staff(current_user)
    repo = PgRepository(db)

    points: list[LabTrendPoint] = []
    for report in repo.list_reports(patient.id):
        entities = get_or_compute_entities(repo, report)
        for reading in analyze_lab_values(entities.lab_values):
            points.append(
                LabTrendPoint(
                    report_id=report.id,
                    report_date=report.created_at,
                    report_filename=report.filename,
                    label=reading.label,
                    raw_value=reading.raw_value,
                    numeric_value=reading.numeric_value,
                    is_abnormal=reading.is_abnormal,
                    reference_range=reading.reference_range,
                )
            )
    return points


@router.get("/adherence", response_model=list[ReminderAdherence])
def adherence(
    days: int = 30,
    patient=Depends(require_patient_access),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ReminderAdherence]:
    _require_clinical_staff(current_user)
    cutoff = datetime.now(UTC) - timedelta(days=days)

    reminders = db.query(db_models.Reminder).filter_by(patient_id=patient.id).all()
    results: list[ReminderAdherence] = []
    for reminder in reminders:
        logs = (
            db.query(db_models.DoseLog)
            .filter(db_models.DoseLog.reminder_id == reminder.id, db_models.DoseLog.taken_at >= cutoff)
            .all()
        )
        taken = sum(1 for log in logs if log.status == "taken")
        skipped = sum(1 for log in logs if log.status == "skipped")
        missed = sum(1 for log in logs if log.status == "missed_auto")
        denominator = taken + missed
        adherence_pct = (taken / denominator * 100) if denominator else 0.0
        results.append(
            ReminderAdherence(
                reminder_id=reminder.id,
                medicine_name=reminder.medicine_name,
                taken=taken,
                skipped=skipped,
                missed=missed,
                adherence_pct=round(adherence_pct, 1),
            )
        )
    return results


@router.get("/summary", response_model=AnalyticsSummary)
def summary(
    patient=Depends(require_patient_access),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnalyticsSummary:
    _require_clinical_staff(current_user)
    repo = PgRepository(db)

    reports = repo.list_reports(patient.id)
    abnormal_counts_by_report: list[int] = []
    total_abnormal = 0
    for report in reports:
        entities = get_or_compute_entities(repo, report)
        count = sum(1 for r in analyze_lab_values(entities.lab_values) if r.is_abnormal)
        abnormal_counts_by_report.append(count)
        total_abnormal += count

    trend: str = "unknown"
    if len(abnormal_counts_by_report) >= 2:
        latest, previous = abnormal_counts_by_report[-1], abnormal_counts_by_report[-2]
        trend = "up" if latest > previous else "down" if latest < previous else "flat"

    active_reminders = db.query(db_models.Reminder).filter_by(patient_id=patient.id, active=True).count()

    week_ago = datetime.now(UTC) - timedelta(days=7)
    doses_missed_this_week = (
        db.query(db_models.DoseLog)
        .join(db_models.Reminder, db_models.Reminder.id == db_models.DoseLog.reminder_id)
        .filter(
            db_models.Reminder.patient_id == patient.id,
            db_models.DoseLog.status == "missed_auto",
            db_models.DoseLog.taken_at >= week_ago,
        )
        .count()
    )

    return AnalyticsSummary(
        total_reports=len(reports),
        total_abnormal_readings=total_abnormal,
        abnormal_trend=trend,
        active_reminders=active_reminders,
        doses_missed_this_week=doses_missed_this_week,
    )
