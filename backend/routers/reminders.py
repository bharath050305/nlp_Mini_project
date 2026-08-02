"""
backend/routers/reminders.py

Reminder CRUD with structured daily/monthly schedules and quantity
tracking, plus the "mark dose taken" action that drives refill alerts
(backend/services/refill_service.py). Scheduling changes here call
scheduler_service directly so a running worker process picks them up
immediately, not just on its next startup sync.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend import db_models
from backend.db import get_db
from backend.deps import get_current_user, require_patient_access
from backend.pg_repository import PgRepository
from backend.schemas_api import MarkDoseRequest, ReminderCreateRequest, ReminderOut, ReminderUpdateRequest
from backend.services import refill_service
from backend.services.scheduler_service import schedule_reminder_slot, unschedule_reminder_slot

router = APIRouter(prefix="/api/patients/{patient_id}/reminders", tags=["reminders"])


def _forbid_staff(current_user) -> None:
    if current_user.role == "staff":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Staff don't have reminder access.")


@router.get("", response_model=list[ReminderOut])
def list_reminders(
    patient=Depends(require_patient_access),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ReminderOut]:
    _forbid_staff(current_user)
    return db.query(db_models.Reminder).filter_by(patient_id=patient.id, active=True).order_by(db_models.Reminder.id).all()


@router.post("", response_model=ReminderOut, status_code=status.HTTP_201_CREATED)
def create_reminder(
    payload: ReminderCreateRequest,
    patient=Depends(require_patient_access),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReminderOut:
    _forbid_staff(current_user)
    if payload.schedule_type in ("daily", "monthly") and not payload.slots:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "At least one schedule slot is required for daily/monthly reminders.")
    if payload.schedule_type == "monthly" and any(s.day_of_month is None for s in payload.slots):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Monthly slots require day_of_month.")

    row = db_models.Reminder(
        patient_id=patient.id,
        created_by=current_user.id,
        medicine_name=payload.medicine_name,
        dosage=payload.dosage,
        schedule_type=payload.schedule_type,
        quantity_total=payload.quantity_total,
        quantity_remaining=payload.quantity_total,
        quantity_per_dose=payload.quantity_per_dose,
        low_stock_threshold=payload.low_stock_threshold,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    for slot_in in payload.slots:
        slot = db_models.ReminderScheduleSlot(
            reminder_id=row.id, time_of_day=slot_in.time_of_day, day_of_month=slot_in.day_of_month
        )
        db.add(slot)
        db.commit()
        db.refresh(slot)
        if payload.schedule_type in ("daily", "monthly"):
            job_id = schedule_reminder_slot(slot)
            slot.apscheduler_job_id = job_id
            db.commit()

    db.refresh(row)
    return row


@router.patch("/{reminder_id}", response_model=ReminderOut)
def update_reminder(
    reminder_id: int,
    payload: ReminderUpdateRequest,
    patient=Depends(require_patient_access),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReminderOut:
    _forbid_staff(current_user)
    row = db.get(db_models.Reminder, reminder_id)
    if row is None or row.patient_id != patient.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reminder not found.")

    updates = payload.model_dump(exclude_unset=True)
    is_restock = "quantity_remaining" in updates and (updates["quantity_remaining"] or 0) > (row.quantity_remaining or 0)
    for key, value in updates.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)

    if is_restock:
        refill_service.reset_refill_alert_on_restock(PgRepository(db), reminder_id)
        db.refresh(row)

    return row


@router.delete("/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reminder(
    reminder_id: int,
    patient=Depends(require_patient_access),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    _forbid_staff(current_user)
    row = db.get(db_models.Reminder, reminder_id)
    if row is None or row.patient_id != patient.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reminder not found.")

    for slot in row.slots:
        unschedule_reminder_slot(reminder_id, slot.id)
    db.delete(row)
    db.commit()


@router.post("/{reminder_id}/mark-dose", status_code=status.HTTP_201_CREATED)
def mark_dose(
    reminder_id: int,
    payload: MarkDoseRequest,
    patient=Depends(require_patient_access),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    _forbid_staff(current_user)
    repo = PgRepository(db)
    reminder = repo.get_reminder(reminder_id)
    if reminder is None or reminder.patient_id != patient.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reminder not found.")

    refill_service.log_dose_taken(
        repo,
        reminder_id=reminder_id,
        patient_id=patient.id,
        slot_id=payload.slot_id,
        status=payload.status,
        logged_by=current_user.id,
    )
    updated = repo.get_reminder(reminder_id)
    return {"quantity_remaining": updated.quantity_remaining, "refill_alert_sent": updated.refill_alert_sent}
