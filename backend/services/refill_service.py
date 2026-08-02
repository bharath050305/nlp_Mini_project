"""
backend/services/refill_service.py

Quantity/refill logic. `quantity_remaining` decrements only from an
explicit "mark dose taken" action (a `dose_logs` insert) — never assumed
from the clock — matching the project's existing governance philosophy of
not silently acting on unconfirmed input (see agents/governance.py). This
also makes it auditable: a doctor/nurse can see exactly which doses were
logged, by whom, and when.
"""

from __future__ import annotations

from backend import db_models
from backend.pg_repository import PgRepository
from backend.services.notification_service import create_notification


def log_dose_taken(
    repo: PgRepository,
    *,
    reminder_id: int,
    patient_id: int,
    slot_id: int | None,
    status: str,
    logged_by: int | None,
) -> db_models.DoseLog:
    """Record a dose event. Only a `status="taken"` log decrements stock
    and can trigger a refill alert; `skipped`/`missed_auto` never touch
    quantity_remaining."""
    log = repo.log_dose(
        reminder_id=reminder_id, patient_id=patient_id, slot_id=slot_id, status=status, logged_by=logged_by
    )

    if status != "taken":
        return log

    reminder = repo.get_reminder(reminder_id)
    if reminder is None or reminder.quantity_remaining is None:
        return log  # quantity tracking not enabled for this reminder

    updated = repo.decrement_reminder_quantity(reminder_id, reminder.quantity_per_dose)
    _maybe_trigger_refill_alert(repo, updated)
    return log


def _maybe_trigger_refill_alert(repo: PgRepository, reminder: db_models.Reminder) -> None:
    if reminder.quantity_remaining is None:
        return
    if reminder.quantity_remaining > reminder.low_stock_threshold:
        return
    if reminder.refill_alert_sent:
        return

    patient = repo.get_patient(reminder.patient_id)
    if patient is None or patient.user_id is None:
        return  # no login linked to this patient — nothing to notify in-app/email

    create_notification(
        repo,
        user_id=patient.user_id,
        patient_id=patient.id,
        type="refill_alert",
        title=f"{reminder.medicine_name} is running low",
        body=(
            f"Only {reminder.quantity_remaining} dose(s) of {reminder.medicine_name} remain "
            f"(threshold: {reminder.low_stock_threshold}). Time to arrange a refill."
        ),
        channel="both",
        related_reminder_id=reminder.id,
    )
    repo.set_refill_alert_sent(reminder.id, True)


def reset_refill_alert_on_restock(repo: PgRepository, reminder_id: int) -> None:
    """Called when a reminder's quantity_total/quantity_remaining is
    increased (a refill) — re-arms the low-stock alert for next time."""
    repo.set_refill_alert_sent(reminder_id, False)
