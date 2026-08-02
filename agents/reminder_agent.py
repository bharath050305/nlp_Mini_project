"""
agents/reminder_agent.py

Medicine Reminder Agent. Thin, focused wrapper over the SQLite repository
(`tools/database.py`) plus the mock scheduling helper
(`tools/calendar_tool.py`) — CRUD for reminders, with a human-readable
"next dose" string for the UI.
"""

from __future__ import annotations

from schemas import Reminder
from tools.calendar_tool import format_next_dose
from tools.database import Repository
from utils.logger import get_logger

logger = get_logger(__name__)


def add_reminder(repo: Repository, patient_id: int, medicine_name: str, dosage: str = "", frequency: str = "") -> Reminder:
    """Persist a new reminder. Falls back to a generic name if extraction failed."""
    reminder = Reminder(
        patient_id=patient_id,
        medicine_name=medicine_name.strip() or "Unnamed medicine",
        dosage=dosage.strip(),
        frequency=frequency.strip(),
    )
    saved = repo.add_reminder(reminder)
    logger.info("Reminder saved: %s (%s)", saved.medicine_name, saved.frequency or "no frequency given")
    return saved


def list_reminders_with_schedule(repo: Repository, patient_id: int) -> list[dict]:
    """Return saved reminders enriched with a computed 'next dose' string."""
    reminders = repo.list_reminders(patient_id)
    return [
        {
            "id": r.id,
            "medicine_name": r.medicine_name,
            "dosage": r.dosage,
            "frequency": r.frequency,
            "next_dose": format_next_dose(r.frequency) if r.frequency else "Not scheduled",
        }
        for r in reminders
    ]


def delete_reminder(repo: Repository, reminder_id: int) -> bool:
    return repo.delete_reminder(reminder_id)
