"""
backend/routers/notifications.py

In-app notification center for the currently authenticated user
(regardless of role — everyone gets notifications about their own
account/patients). The React app polls GET here.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.deps import get_current_user
from backend.pg_repository import PgRepository
from backend.schemas_api import NotificationOut

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
def list_notifications(
    unread_only: bool = False,
    limit: int = 50,
    offset: int = 0,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[NotificationOut]:
    return PgRepository(db).list_notifications_for_user(
        current_user.id, unread_only=unread_only, limit=limit, offset=offset
    )


@router.patch("/{notification_id}/read", response_model=NotificationOut)
def mark_read(notification_id: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)) -> NotificationOut:
    row = PgRepository(db).mark_notification_read(notification_id, current_user.id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notification not found.")
    return row


@router.post("/mark-all-read")
def mark_all_read(current_user=Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    count = PgRepository(db).mark_all_read(current_user.id)
    return {"marked_read": count}
