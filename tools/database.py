"""
tools/database.py

SQLite repository layer. Plain `sqlite3` with parameterized queries only
(no ORM) — every query is one line and defensible in a viva, which is the
trade-off called out in the README.

`Database` owns the connection and schema; `Repository` exposes typed
CRUD methods returning/accepting the pydantic models from `schemas.py`.
Both are safe to construct multiple times (e.g. once per Streamlit
rerun) since `_init_schema` uses `CREATE TABLE IF NOT EXISTS`.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from config import settings
from schemas import ConversationTurn, Patient, Reminder, Report
from utils.exceptions import DatabaseError
from utils.logger import get_logger

logger = get_logger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS patients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL DEFAULT 'Demo Patient',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    filename TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    summary_json TEXT NOT NULL DEFAULT '',
    entities_json TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    medicine_name TEXT NOT NULL,
    dosage TEXT NOT NULL DEFAULT '',
    frequency TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS conversation_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    user_message TEXT NOT NULL,
    assistant_response TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


class Database:
    """Owns the SQLite connection and schema for a given database file."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or settings.database_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self) -> None:
        try:
            with self.connect() as conn:
                conn.executescript(_SCHEMA)
        except sqlite3.Error as exc:
            raise DatabaseError(f"Failed to initialize schema: {exc}") from exc

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


class Repository:
    """Typed CRUD operations over a `Database`, in/out via pydantic models."""

    def __init__(self, db: Database | None = None) -> None:
        self.db = db or Database()

    # -- patients ---------------------------------------------------------
    def get_or_create_default_patient(self) -> Patient:
        """Return patient #1, creating it if this is a fresh database.

        Multi-patient support is out of scope for the mini project (see
        README "Skip These"), but modeling patients as a real table keeps
        the schema honest and makes multi-user support a small follow-up
        rather than a rewrite.
        """
        with self.db.connect() as conn:
            row = conn.execute("SELECT * FROM patients ORDER BY id LIMIT 1").fetchone()
            if row is None:
                cur = conn.execute("INSERT INTO patients (name) VALUES (?)", ("Demo Patient",))
                row = conn.execute(
                    "SELECT * FROM patients WHERE id = ?", (cur.lastrowid,)
                ).fetchone()
            return Patient(**dict(row))

    # -- reports ------------------------------------------------------------
    def save_report(self, report: Report) -> Report:
        try:
            with self.db.connect() as conn:
                cur = conn.execute(
                    """INSERT INTO reports
                       (patient_id, filename, raw_text, summary_json, entities_json)
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        report.patient_id,
                        report.filename,
                        report.raw_text,
                        report.summary_json,
                        report.entities_json,
                    ),
                )
                row = conn.execute(
                    "SELECT * FROM reports WHERE id = ?", (cur.lastrowid,)
                ).fetchone()
                return Report(**dict(row))
        except sqlite3.Error as exc:
            raise DatabaseError(f"Failed to save report: {exc}") from exc

    def get_latest_report(self, patient_id: int) -> Report | None:
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT * FROM reports WHERE patient_id = ? ORDER BY id DESC LIMIT 1",
                (patient_id,),
            ).fetchone()
            return Report(**dict(row)) if row else None

    def list_reports(self, patient_id: int) -> list[Report]:
        """All reports for a patient, oldest first — feeds the Clinical
        Timeline Agent, which needs the full upload history, not just the
        latest report."""
        with self.db.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM reports WHERE patient_id = ? ORDER BY id ASC", (patient_id,)
            ).fetchall()
            return [Report(**dict(r)) for r in rows]

    def update_report_analysis(self, report_id: int, summary_json: str, entities_json: str) -> None:
        """Cache computed summary/entities back onto a saved report row, so
        the Timeline Agent can reuse them without re-running NER on every
        historical report on every request."""
        try:
            with self.db.connect() as conn:
                conn.execute(
                    "UPDATE reports SET summary_json = ?, entities_json = ? WHERE id = ?",
                    (summary_json, entities_json, report_id),
                )
        except sqlite3.Error as exc:
            raise DatabaseError(f"Failed to update report analysis: {exc}") from exc

    # -- reminders ----------------------------------------------------------
    def add_reminder(self, reminder: Reminder) -> Reminder:
        try:
            with self.db.connect() as conn:
                cur = conn.execute(
                    """INSERT INTO reminders (patient_id, medicine_name, dosage, frequency)
                       VALUES (?, ?, ?, ?)""",
                    (
                        reminder.patient_id,
                        reminder.medicine_name,
                        reminder.dosage,
                        reminder.frequency,
                    ),
                )
                row = conn.execute(
                    "SELECT * FROM reminders WHERE id = ?", (cur.lastrowid,)
                ).fetchone()
                return Reminder(**dict(row))
        except sqlite3.Error as exc:
            raise DatabaseError(f"Failed to add reminder: {exc}") from exc

    def list_reminders(self, patient_id: int) -> list[Reminder]:
        with self.db.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM reminders WHERE patient_id = ? ORDER BY id", (patient_id,)
            ).fetchall()
            return [Reminder(**dict(r)) for r in rows]

    def delete_reminder(self, reminder_id: int) -> bool:
        with self.db.connect() as conn:
            cur = conn.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
            return cur.rowcount > 0

    # -- conversation history / memory --------------------------------------
    def add_conversation_turn(self, turn: ConversationTurn) -> ConversationTurn:
        try:
            with self.db.connect() as conn:
                cur = conn.execute(
                    """INSERT INTO conversation_history
                       (patient_id, user_message, assistant_response)
                       VALUES (?, ?, ?)""",
                    (turn.patient_id, turn.user_message, turn.assistant_response),
                )
                row = conn.execute(
                    "SELECT * FROM conversation_history WHERE id = ?", (cur.lastrowid,)
                ).fetchone()
                return ConversationTurn(**dict(row))
        except sqlite3.Error as exc:
            raise DatabaseError(f"Failed to save conversation turn: {exc}") from exc

    def get_conversation_history(
        self, patient_id: int, limit: int = 20
    ) -> list[ConversationTurn]:
        with self.db.connect() as conn:
            rows = conn.execute(
                """SELECT * FROM conversation_history WHERE patient_id = ?
                   ORDER BY id DESC LIMIT ?""",
                (patient_id, limit),
            ).fetchall()
            return [ConversationTurn(**dict(r)) for r in reversed(rows)]
