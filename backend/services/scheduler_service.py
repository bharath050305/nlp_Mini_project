"""
backend/services/scheduler_service.py

APScheduler + SQLAlchemyJobStore against the same Postgres database —
persists jobs across restarts with no new infra (no Redis/Celery broker)
beyond the Postgres instance this project already requires. Runs as its
own process (`python -m backend.worker`), not embedded in the API
process, so a multi-worker `uvicorn` deployment never double-fires a job.

Each `reminder_schedule_slots` row maps to one cron job:
  daily   -> CronTrigger(hour=, minute=)
  monthly -> CronTrigger(day=, hour=, minute=)
Job id is deterministic (`reminder:<id>:slot:<id>`) so re-registering an
already-scheduled slot is a no-op replace, not a duplicate.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from apscheduler.jobstores.base import JobLookupError
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

_scheduler: BackgroundScheduler | None = None

# How long after a dose-reminder fires we check whether it was logged as
# taken before treating it as missed. Approximate on purpose: there's no
# per-occurrence table, just a "was anything logged taken recently" check
# — sufficient for a missed-dose nudge, not a strict adherence audit.
_MISSED_DOSE_CHECK_DELAY = timedelta(hours=2)
_MISSED_DOSE_LOOKBACK = timedelta(hours=3)


def get_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is None:
        jobstores = {"default": SQLAlchemyJobStore(url=settings.database_url)}
        _scheduler = BackgroundScheduler(jobstores=jobstores, timezone="UTC")
    return _scheduler


def _slot_job_id(reminder_id: int, slot_id: int) -> str:
    return f"reminder:{reminder_id}:slot:{slot_id}"


def schedule_reminder_slot(slot) -> str:
    """(Re)register the cron job for one ReminderScheduleSlot ORM row."""
    scheduler = get_scheduler()
    job_id = _slot_job_id(slot.reminder_id, slot.id)

    if slot.day_of_month is not None:
        trigger = CronTrigger(day=slot.day_of_month, hour=slot.time_of_day.hour, minute=slot.time_of_day.minute)
    else:
        trigger = CronTrigger(hour=slot.time_of_day.hour, minute=slot.time_of_day.minute)

    scheduler.add_job(
        _fire_dose_reminder,
        trigger=trigger,
        id=job_id,
        args=[slot.reminder_id, slot.id],
        replace_existing=True,
        misfire_grace_time=3600,
    )
    return job_id


def unschedule_reminder_slot(reminder_id: int, slot_id: int) -> None:
    scheduler = get_scheduler()
    try:
        scheduler.remove_job(_slot_job_id(reminder_id, slot_id))
    except JobLookupError:
        pass


def sync_all_jobs() -> int:
    """Startup safety net: (re)register every active reminder's slots.
    Idempotent — job ids are deterministic, so this just replaces."""
    from backend.db import SessionLocal
    from backend.pg_repository import PgRepository

    db = SessionLocal()
    try:
        repo = PgRepository(db)
        slots = repo.list_all_active_schedule_slots()
        for slot in slots:
            schedule_reminder_slot(slot)
        logger.info("Synced %d reminder schedule job(s)", len(slots))
        return len(slots)
    finally:
        db.close()


def _fire_dose_reminder(reminder_id: int, slot_id: int) -> None:
    """APScheduler job callback (runs in the worker process). Opens its
    own DB session since job callbacks execute outside any HTTP request."""
    from backend.db import SessionLocal
    from backend.pg_repository import PgRepository
    from backend.services.notification_service import create_notification

    db = SessionLocal()
    try:
        repo = PgRepository(db)
        reminder = repo.get_reminder(reminder_id)
        if reminder is None or not reminder.active:
            return
        patient = repo.get_patient(reminder.patient_id)
        if patient is None or patient.user_id is None:
            return

        create_notification(
            repo,
            user_id=patient.user_id,
            patient_id=patient.id,
            type="dose_reminder",
            title=f"Time to take {reminder.medicine_name}",
            body=f"Reminder: take {reminder.medicine_name} ({reminder.dosage or 'dosage not set'}) now.",
            channel="both",
            related_reminder_id=reminder.id,
        )

        get_scheduler().add_job(
            _check_missed_dose,
            trigger=DateTrigger(run_date=datetime.now(timezone.utc) + _MISSED_DOSE_CHECK_DELAY),
            id=f"missed-check:{reminder_id}:{slot_id}:{int(datetime.now(timezone.utc).timestamp())}",
            args=[reminder_id, slot_id],
        )
    finally:
        db.close()


def _check_missed_dose(reminder_id: int, slot_id: int) -> None:
    from backend import db_models
    from backend.db import SessionLocal
    from backend.pg_repository import PgRepository
    from backend.services.notification_service import create_notification

    db = SessionLocal()
    try:
        repo = PgRepository(db)
        reminder = repo.get_reminder(reminder_id)
        if reminder is None or not reminder.active:
            return

        cutoff = datetime.now(timezone.utc) - _MISSED_DOSE_LOOKBACK
        recent_taken = (
            db.query(db_models.DoseLog)
            .filter(
                db_models.DoseLog.reminder_id == reminder_id,
                db_models.DoseLog.status == "taken",
                db_models.DoseLog.taken_at >= cutoff,
            )
            .first()
        )
        if recent_taken is not None:
            return  # already logged taken — nothing to flag

        repo.log_dose(reminder_id=reminder_id, patient_id=reminder.patient_id, slot_id=slot_id, status="missed_auto", logged_by=None)

        patient = repo.get_patient(reminder.patient_id)
        if patient is None or patient.user_id is None:
            return
        create_notification(
            repo,
            user_id=patient.user_id,
            patient_id=patient.id,
            type="missed_dose",
            title=f"Missed dose: {reminder.medicine_name}",
            body=f"It looks like the {reminder.medicine_name} dose wasn't marked as taken.",
            channel="in_app",
            related_reminder_id=reminder.id,
        )
    finally:
        db.close()
