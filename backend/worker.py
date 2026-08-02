"""
backend/worker.py

Standalone scheduler process: `python -m backend.worker`. Runs alongside
`uvicorn backend.main:app`, not inside it, so a multi-worker API process
never double-fires a job (see scheduler_service.py's module docstring).

Two things run here:
1. Every reminder's cron jobs (dose reminders -> notifications), synced
   once at startup and kept live via reminders.py's direct
   schedule/unschedule calls on create/update/delete.
2. A recurring "dispatch pending email notifications" job — decoupled
   from notification creation so an SMTP hiccup never blocks a firing job.
"""

from __future__ import annotations

import signal
import time

from apscheduler.triggers.interval import IntervalTrigger

from backend.db import SessionLocal
from backend.pg_repository import PgRepository
from backend.services.notification_service import dispatch_pending
from backend.services.scheduler_service import get_scheduler, sync_all_jobs
from utils.logger import get_logger

logger = get_logger(__name__)

_shutdown = False


def _dispatch_pending_job() -> None:
    db = SessionLocal()
    try:
        sent = dispatch_pending(PgRepository(db))
        if sent:
            logger.info("Dispatched %d pending notification(s)", sent)
    finally:
        db.close()


def _handle_signal(signum, frame) -> None:
    global _shutdown
    _shutdown = True


def main() -> None:
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    scheduler = get_scheduler()
    scheduler.add_job(
        _dispatch_pending_job,
        trigger=IntervalTrigger(minutes=1),
        id="dispatch-pending-notifications",
        replace_existing=True,
    )
    scheduler.start()
    sync_all_jobs()
    logger.info("MediAgent scheduler worker started.")

    try:
        while not _shutdown:
            time.sleep(1)
    finally:
        scheduler.shutdown(wait=False)
        logger.info("MediAgent scheduler worker stopped.")


if __name__ == "__main__":
    main()
