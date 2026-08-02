"""
backend/services/notification_service.py

Creates notification rows and dispatches the ones that need email
delivery. Decoupled on purpose: "decide to notify" (create_notification,
called synchronously from request handlers and scheduler jobs) is
separate from "actually deliver" (dispatch_pending, run on a recurring
APScheduler job in backend/worker.py) so an SMTP hiccup can't block the
thing that decided a notification was needed.
"""

from __future__ import annotations

from backend import db_models
from backend.pg_repository import PgRepository
from backend.services.email_service import send_email
from utils.logger import get_logger

logger = get_logger(__name__)


def create_notification(
    repo: PgRepository,
    *,
    user_id: int,
    type: str,
    title: str,
    body: str,
    patient_id: int | None = None,
    channel: str = "in_app",
    related_reminder_id: int | None = None,
    related_transcript_id: int | None = None,
) -> db_models.Notification:
    notification = repo.create_notification(
        user_id=user_id,
        type=type,
        title=title,
        body=body,
        patient_id=patient_id,
        channel=channel,
        related_reminder_id=related_reminder_id,
        related_transcript_id=related_transcript_id,
    )
    if channel == "in_app":
        # nothing to dispatch — the in-app center reads notifications
        # rows directly, so a purely in-app notification is "sent" already.
        repo.mark_notification_dispatched(notification.id, success=True)
    return notification


def dispatch_pending(repo: PgRepository) -> int:
    """Send every pending email/both notification. Returns count sent.

    Registered as its own recurring job (see backend/worker.py) rather
    than being called inline from create_notification, so a transient
    SMTP failure never blocks the request/job that raised the
    notification in the first place.
    """
    pending = repo.list_pending_notifications(channels=("email", "both"))
    sent_count = 0
    for note in pending:
        user = repo.get_user(note.user_id)
        if user is None or not user.email:
            repo.mark_notification_dispatched(note.id, success=False)
            continue
        try:
            send_email(to_address=user.email, subject=note.title, body=note.body)
            repo.mark_notification_dispatched(note.id, success=True)
            sent_count += 1
        except Exception:
            logger.exception("Failed to dispatch notification %s to %s", note.id, user.email)
            repo.mark_notification_dispatched(note.id, success=False)
    return sent_count
