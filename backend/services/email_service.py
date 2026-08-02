"""
backend/services/email_service.py

Mirrors the `llm/` pluggable-provider pattern: "mock" (default) just logs
the email instead of sending it, so a fresh install still runs fully
offline with zero SMTP setup — matching the same rationale as
`llm/mock_provider.py`. "smtp" sends via stdlib `smtplib`.
"""

from __future__ import annotations

import smtplib
from email.message import EmailMessage

from config import settings
from utils.exceptions import NotificationError
from utils.logger import get_logger

logger = get_logger(__name__)


def send_email(*, to_address: str, subject: str, body: str) -> None:
    if settings.email_provider == "mock":
        logger.info("[mock email] to=%s subject=%r body=%r", to_address, subject, body)
        return

    if not settings.smtp_host:
        raise NotificationError("EMAIL_PROVIDER=smtp but SMTP_HOST is not configured.")

    message = EmailMessage()
    message["From"] = settings.smtp_from_address
    message["To"] = to_address
    message["Subject"] = subject
    message.set_content(body)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
            if settings.smtp_use_tls:
                server.starttls()
            if settings.smtp_username and settings.smtp_password:
                server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(message)
    except (smtplib.SMTPException, OSError) as exc:
        raise NotificationError(f"Failed to send email to {to_address}: {exc}") from exc
