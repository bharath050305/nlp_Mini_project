"""
backend/pg_repository.py

Postgres-backed repository. Implements the same method names/signatures
`tools.database.Repository` exposes for reports/reminders/conversation
history (report/reminder duck-typed contract), so `agents/orchestrator.py`,
`agents/reminder_agent.py`, and `agents/timeline_agent.py` work completely
unmodified when handed a `PgRepository` instead of the legacy sqlite
`Repository`. Everything beyond that contract (users, patients, care
assignments, notifications, transcripts, SOAP notes, schedule slots, dose
logs) is new v3 surface used directly by the FastAPI routers.

Legacy-contract methods return `schemas.*` Pydantic models (what the
agents expect). New v3 methods return the SQLAlchemy ORM objects directly
— routers serialize them via `schemas_api.py` DTOs with
`model_config = ConfigDict(from_attributes=True)`.
"""

from __future__ import annotations

from datetime import UTC

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend import db_models
from schemas import ConversationTurn, Reminder, Report
from utils.exceptions import DatabaseError
from utils.logger import get_logger

logger = get_logger(__name__)


class PgRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ======================================================================
    # Legacy-contract methods (schemas.* in/out) — consumed by agents/*
    # ======================================================================

    # -- reports --------------------------------------------------------------
    def save_report(
        self,
        report: Report,
        *,
        uploaded_by: int | None = None,
        source_type: str = "upload",
        transcript_id: int | None = None,
    ) -> Report:
        try:
            row = db_models.Report(
                patient_id=report.patient_id,
                uploaded_by=uploaded_by,
                source_type=source_type,
                transcript_id=transcript_id,
                filename=report.filename,
                raw_text=report.raw_text,
                summary_json=report.summary_json,
                entities_json=report.entities_json,
            )
            self.db.add(row)
            self.db.commit()
            self.db.refresh(row)
            return self._report_to_schema(row)
        except Exception as exc:
            self.db.rollback()
            raise DatabaseError(f"Failed to save report: {exc}") from exc

    def get_latest_report(self, patient_id: int) -> Report | None:
        row = (
            self.db.query(db_models.Report)
            .filter_by(patient_id=patient_id)
            .order_by(db_models.Report.id.desc())
            .first()
        )
        return self._report_to_schema(row) if row else None

    def list_reports(self, patient_id: int) -> list[Report]:
        rows = (
            self.db.query(db_models.Report)
            .filter_by(patient_id=patient_id)
            .order_by(db_models.Report.id.asc())
            .all()
        )
        return [self._report_to_schema(r) for r in rows]

    def update_report_analysis(self, report_id: int, summary_json: str, entities_json: str) -> None:
        try:
            row = self.db.get(db_models.Report, report_id)
            if row is None:
                return
            row.summary_json = summary_json
            row.entities_json = entities_json
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            raise DatabaseError(f"Failed to update report analysis: {exc}") from exc

    @staticmethod
    def _report_to_schema(row: db_models.Report) -> Report:
        return Report(
            id=row.id,
            patient_id=row.patient_id,
            filename=row.filename,
            raw_text=row.raw_text,
            summary_json=row.summary_json,
            entities_json=row.entities_json,
            created_at=row.created_at,
        )

    # -- reminders (legacy shape, used by the conversational SET_REMINDER path) --
    def add_reminder(self, reminder: Reminder, *, created_by: int | None = None) -> Reminder:
        try:
            row = db_models.Reminder(
                patient_id=reminder.patient_id,
                created_by=created_by,
                medicine_name=reminder.medicine_name,
                dosage=reminder.dosage,
                frequency=reminder.frequency,
                schedule_type=reminder.schedule_type,
                quantity_total=reminder.quantity_total,
                quantity_remaining=reminder.quantity_remaining,
                quantity_per_dose=reminder.quantity_per_dose,
                low_stock_threshold=reminder.low_stock_threshold,
            )
            self.db.add(row)
            self.db.commit()
            self.db.refresh(row)
            return self._reminder_to_schema(row)
        except Exception as exc:
            self.db.rollback()
            raise DatabaseError(f"Failed to add reminder: {exc}") from exc

    def list_reminders(self, patient_id: int) -> list[Reminder]:
        rows = (
            self.db.query(db_models.Reminder)
            .filter_by(patient_id=patient_id, active=True)
            .order_by(db_models.Reminder.id)
            .all()
        )
        return [self._reminder_to_schema(r) for r in rows]

    def delete_reminder(self, reminder_id: int) -> bool:
        row = self.db.get(db_models.Reminder, reminder_id)
        if row is None:
            return False
        self.db.delete(row)
        self.db.commit()
        return True

    @staticmethod
    def _reminder_to_schema(row: db_models.Reminder) -> Reminder:
        return Reminder(
            id=row.id,
            patient_id=row.patient_id,
            medicine_name=row.medicine_name,
            dosage=row.dosage,
            frequency=row.frequency,
            created_at=row.created_at,
            schedule_type=row.schedule_type,
            quantity_total=row.quantity_total,
            quantity_remaining=row.quantity_remaining,
            quantity_per_dose=row.quantity_per_dose,
            low_stock_threshold=row.low_stock_threshold,
            refill_alert_sent=row.refill_alert_sent,
            active=row.active,
        )

    # -- conversation history ---------------------------------------------------
    def add_conversation_turn(self, turn: ConversationTurn) -> ConversationTurn:
        try:
            row = db_models.ConversationTurn(
                patient_id=turn.patient_id,
                user_message=turn.user_message,
                assistant_response=turn.assistant_response,
            )
            self.db.add(row)
            self.db.commit()
            self.db.refresh(row)
            return ConversationTurn(
                id=row.id,
                patient_id=row.patient_id,
                user_message=row.user_message,
                assistant_response=row.assistant_response,
                created_at=row.created_at,
            )
        except Exception as exc:
            self.db.rollback()
            raise DatabaseError(f"Failed to save conversation turn: {exc}") from exc

    def get_conversation_history(self, patient_id: int, limit: int = 20) -> list[ConversationTurn]:
        rows = (
            self.db.query(db_models.ConversationTurn)
            .filter_by(patient_id=patient_id)
            .order_by(db_models.ConversationTurn.id.desc())
            .limit(limit)
            .all()
        )
        return [
            ConversationTurn(
                id=r.id,
                patient_id=r.patient_id,
                user_message=r.user_message,
                assistant_response=r.assistant_response,
                created_at=r.created_at,
            )
            for r in reversed(rows)
        ]

    # ======================================================================
    # v3 methods (ORM objects in/out) — consumed directly by backend/routers
    # ======================================================================

    # -- users --------------------------------------------------------------
    def get_user_by_email(self, email: str) -> db_models.User | None:
        return self.db.execute(select(db_models.User).filter_by(email=email)).scalar_one_or_none()

    def get_user(self, user_id: int) -> db_models.User | None:
        return self.db.get(db_models.User, user_id)

    def create_user(self, *, email: str, hashed_password: str, full_name: str, role: str) -> db_models.User:
        user = db_models.User(email=email, hashed_password=hashed_password, full_name=full_name, role=role)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def list_users(self, role: str | None = None) -> list[db_models.User]:
        q = self.db.query(db_models.User)
        if role:
            q = q.filter_by(role=role)
        return q.order_by(db_models.User.id).all()

    # -- patients -----------------------------------------------------------
    def create_patient(
        self,
        *,
        name: str,
        user_id: int | None = None,
        date_of_birth=None,
        phone: str | None = None,
        created_by: int | None = None,
    ) -> db_models.Patient:
        patient = db_models.Patient(
            name=name, user_id=user_id, date_of_birth=date_of_birth, phone=phone, created_by=created_by
        )
        self.db.add(patient)
        self.db.commit()
        self.db.refresh(patient)
        return patient

    def get_patient(self, patient_id: int) -> db_models.Patient | None:
        return self.db.get(db_models.Patient, patient_id)

    def get_patient_by_user_id(self, user_id: int) -> db_models.Patient | None:
        return self.db.execute(select(db_models.Patient).filter_by(user_id=user_id)).scalar_one_or_none()

    def list_all_patients(self) -> list[db_models.Patient]:
        return self.db.query(db_models.Patient).order_by(db_models.Patient.id).all()

    def list_patients_for_provider(self, staff_user_id: int, role: str) -> list[db_models.Patient]:
        return (
            self.db.query(db_models.Patient)
            .join(db_models.CareAssignment, db_models.CareAssignment.patient_id == db_models.Patient.id)
            .filter(
                db_models.CareAssignment.staff_user_id == staff_user_id,
                db_models.CareAssignment.role_at_assignment == role,
                db_models.CareAssignment.active.is_(True),
            )
            .order_by(db_models.Patient.id)
            .all()
        )

    # -- care assignments -----------------------------------------------------
    def create_assignment(
        self, *, patient_id: int, staff_user_id: int, role_at_assignment: str, assigned_by: int | None
    ) -> db_models.CareAssignment:
        existing = (
            self.db.query(db_models.CareAssignment)
            .filter_by(
                patient_id=patient_id,
                staff_user_id=staff_user_id,
                role_at_assignment=role_at_assignment,
                active=True,
            )
            .first()
        )
        if existing:
            return existing
        assignment = db_models.CareAssignment(
            patient_id=patient_id,
            staff_user_id=staff_user_id,
            role_at_assignment=role_at_assignment,
            assigned_by=assigned_by,
        )
        self.db.add(assignment)
        self.db.commit()
        self.db.refresh(assignment)
        return assignment

    def list_assignments_for_patient(self, patient_id: int) -> list[db_models.CareAssignment]:
        return (
            self.db.query(db_models.CareAssignment)
            .filter_by(patient_id=patient_id, active=True)
            .order_by(db_models.CareAssignment.id)
            .all()
        )

    def deactivate_assignment(self, assignment_id: int) -> bool:
        from datetime import datetime

        row = self.db.get(db_models.CareAssignment, assignment_id)
        if row is None:
            return False
        row.active = False
        row.unassigned_at = datetime.now(UTC)
        self.db.commit()
        return True

    # -- reminder schedule slots ------------------------------------------------
    def get_reminder(self, reminder_id: int) -> db_models.Reminder | None:
        return self.db.get(db_models.Reminder, reminder_id)

    def add_schedule_slot(
        self, reminder_id: int, time_of_day, day_of_month: int | None = None
    ) -> db_models.ReminderScheduleSlot:
        slot = db_models.ReminderScheduleSlot(reminder_id=reminder_id, time_of_day=time_of_day, day_of_month=day_of_month)
        self.db.add(slot)
        self.db.commit()
        self.db.refresh(slot)
        return slot

    def list_schedule_slots(self, reminder_id: int) -> list[db_models.ReminderScheduleSlot]:
        return self.db.query(db_models.ReminderScheduleSlot).filter_by(reminder_id=reminder_id).all()

    def delete_schedule_slot(self, slot_id: int) -> bool:
        row = self.db.get(db_models.ReminderScheduleSlot, slot_id)
        if row is None:
            return False
        self.db.delete(row)
        self.db.commit()
        return True

    def set_slot_job_id(self, slot_id: int, job_id: str) -> None:
        row = self.db.get(db_models.ReminderScheduleSlot, slot_id)
        if row is not None:
            row.apscheduler_job_id = job_id
            self.db.commit()

    def list_all_active_schedule_slots(self) -> list[db_models.ReminderScheduleSlot]:
        return (
            self.db.query(db_models.ReminderScheduleSlot)
            .join(db_models.Reminder)
            .filter(db_models.Reminder.active.is_(True))
            .all()
        )

    def deactivate_reminder(self, reminder_id: int) -> bool:
        row = self.db.get(db_models.Reminder, reminder_id)
        if row is None:
            return False
        row.active = False
        self.db.commit()
        return True

    def update_reminder_fields(self, reminder_id: int, **fields) -> db_models.Reminder | None:
        row = self.db.get(db_models.Reminder, reminder_id)
        if row is None:
            return None
        for key, value in fields.items():
            setattr(row, key, value)
        self.db.commit()
        self.db.refresh(row)
        return row

    # -- dose logs / refill logic -------------------------------------------
    def log_dose(
        self, *, reminder_id: int, patient_id: int, slot_id: int | None, status: str, logged_by: int | None
    ) -> db_models.DoseLog:
        log = db_models.DoseLog(
            reminder_id=reminder_id, patient_id=patient_id, slot_id=slot_id, status=status, logged_by=logged_by
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def decrement_reminder_quantity(self, reminder_id: int, amount: int) -> db_models.Reminder | None:
        row = self.db.get(db_models.Reminder, reminder_id)
        if row is None or row.quantity_remaining is None:
            return row
        row.quantity_remaining = max(0, row.quantity_remaining - amount)
        self.db.commit()
        self.db.refresh(row)
        return row

    def set_refill_alert_sent(self, reminder_id: int, sent: bool) -> None:
        row = self.db.get(db_models.Reminder, reminder_id)
        if row is not None:
            row.refill_alert_sent = sent
            self.db.commit()

    # -- notifications --------------------------------------------------------
    def create_notification(
        self,
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
        note = db_models.Notification(
            user_id=user_id,
            patient_id=patient_id,
            type=type,
            title=title,
            body=body,
            channel=channel,
            related_reminder_id=related_reminder_id,
            related_transcript_id=related_transcript_id,
        )
        self.db.add(note)
        self.db.commit()
        self.db.refresh(note)
        return note

    def list_notifications_for_user(
        self, user_id: int, *, unread_only: bool = False, limit: int = 50, offset: int = 0
    ) -> list[db_models.Notification]:
        q = self.db.query(db_models.Notification).filter_by(user_id=user_id)
        if unread_only:
            q = q.filter(db_models.Notification.status != "read")
        return q.order_by(db_models.Notification.created_at.desc()).offset(offset).limit(limit).all()

    def mark_notification_read(self, notification_id: int, user_id: int) -> db_models.Notification | None:
        from datetime import datetime

        row = self.db.query(db_models.Notification).filter_by(id=notification_id, user_id=user_id).first()
        if row is None:
            return None
        row.status = "read"
        row.read_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(row)
        return row

    def mark_all_read(self, user_id: int) -> int:
        from datetime import datetime

        rows = (
            self.db.query(db_models.Notification)
            .filter(db_models.Notification.user_id == user_id, db_models.Notification.status != "read")
            .all()
        )
        now = datetime.now(UTC)
        for row in rows:
            row.status = "read"
            row.read_at = now
        self.db.commit()
        return len(rows)

    def list_pending_notifications(self, *, channels: tuple[str, ...] = ("email", "both")) -> list[db_models.Notification]:
        return (
            self.db.query(db_models.Notification)
            .filter(db_models.Notification.status == "pending", db_models.Notification.channel.in_(channels))
            .all()
        )

    def mark_notification_dispatched(self, notification_id: int, *, success: bool) -> None:
        from datetime import datetime

        row = self.db.get(db_models.Notification, notification_id)
        if row is None:
            return
        row.status = "sent" if success else "failed"
        row.sent_at = datetime.now(UTC)
        self.db.commit()

    # -- transcripts / SOAP notes ----------------------------------------------
    def create_transcript(
        self, *, patient_id: int, doctor_id: int, audio_filename: str, audio_path: str
    ) -> db_models.Transcript:
        row = db_models.Transcript(
            patient_id=patient_id, doctor_id=doctor_id, audio_filename=audio_filename, audio_path=audio_path
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def get_transcript(self, transcript_id: int) -> db_models.Transcript | None:
        return self.db.get(db_models.Transcript, transcript_id)

    def update_transcript(self, transcript_id: int, **fields) -> db_models.Transcript | None:
        row = self.db.get(db_models.Transcript, transcript_id)
        if row is None:
            return None
        for key, value in fields.items():
            setattr(row, key, value)
        self.db.commit()
        self.db.refresh(row)
        return row

    def create_soap_note(
        self,
        *,
        transcript_id: int,
        patient_id: int,
        doctor_id: int,
        subjective: str,
        objective: str,
        assessment: str,
        plan: str,
        entities_json: str = "",
    ) -> db_models.SoapNote:
        row = db_models.SoapNote(
            transcript_id=transcript_id,
            patient_id=patient_id,
            doctor_id=doctor_id,
            subjective=subjective,
            objective=objective,
            assessment=assessment,
            plan=plan,
            entities_json=entities_json,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    # -- report chunk embeddings (semantic search, v4) --------------------------
    def replace_chunk_embeddings(self, report_id: int, chunks: list[tuple[str, list[float]]]) -> None:
        """Delete any existing embeddings for this report and insert the
        given (chunk_text, embedding) pairs — called once per report at
        upload/finalize time, not per question."""
        self.db.query(db_models.ReportChunkEmbedding).filter_by(report_id=report_id).delete()
        for index, (chunk_text_, embedding) in enumerate(chunks):
            self.db.add(
                db_models.ReportChunkEmbedding(
                    report_id=report_id, chunk_index=index, chunk_text=chunk_text_, embedding=embedding
                )
            )
        self.db.commit()

    def get_chunk_embeddings_for_patient(self, patient_id: int) -> list[tuple[str, list[float]]]:
        """All embedded chunks across every report this patient has on
        file — spans full history, not just the latest report (see
        docs/RAG.md's 'upgrade path' section)."""
        rows = (
            self.db.query(db_models.ReportChunkEmbedding)
            .join(db_models.Report, db_models.Report.id == db_models.ReportChunkEmbedding.report_id)
            .filter(db_models.Report.patient_id == patient_id)
            .all()
        )
        return [(row.chunk_text, row.embedding) for row in rows]

    def get_soap_note_by_transcript(self, transcript_id: int) -> db_models.SoapNote | None:
        return self.db.execute(
            select(db_models.SoapNote).filter_by(transcript_id=transcript_id)
        ).scalar_one_or_none()

    def update_soap_note(self, soap_note_id: int, **fields) -> db_models.SoapNote | None:
        row = self.db.get(db_models.SoapNote, soap_note_id)
        if row is None:
            return None
        for key, value in fields.items():
            setattr(row, key, value)
        self.db.commit()
        self.db.refresh(row)
        return row
