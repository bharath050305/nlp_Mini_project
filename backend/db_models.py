"""
backend/db_models.py

SQLAlchemy ORM models for the Postgres-backed v3 schema: multi-user auth,
role-based care assignments, structured reminder schedules with quantity
tracking, notifications, and the transcript-to-report pipeline.

This is a deliberate deviation from `tools/database.py`'s raw-sqlite3,
no-ORM pattern (see docs/RAG.md and the plan doc for the justification):
RBAC joins, recurring schedules, and quantity tracking are enough
relational complexity that an ORM + Alembic migrations pay for themselves
here, whereas they didn't for the original single-patient demo. The old
sqlite path is untouched, not replaced.
"""

from __future__ import annotations

from datetime import date, datetime, time

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db import Base

ROLES = ("doctor", "patient", "nurse", "staff")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint(f"role IN {ROLES}", name="ck_users_role"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    patient_profile: Mapped[Patient | None] = relationship(
        back_populates="user", uselist=False, foreign_keys="Patient.user_id"
    )


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), unique=True, nullable=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User | None] = relationship(back_populates="patient_profile", foreign_keys=[user_id])


class CareAssignment(Base):
    """One row per doctor-or-nurse <-> patient link. `role_at_assignment`
    discriminates instead of two near-identical tables."""

    __tablename__ = "care_assignments"
    __table_args__ = (
        CheckConstraint("role_at_assignment IN ('doctor', 'nurse')", name="ck_assignment_role"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False)
    staff_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    role_at_assignment: Mapped[str] = mapped_column(String, nullable=False)
    assigned_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    unassigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (
        CheckConstraint("source_type IN ('upload', 'consultation_audio')", name="ck_report_source"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False)
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    source_type: Mapped[str] = mapped_column(String, default="upload", nullable=False)
    transcript_id: Mapped[int | None] = mapped_column(ForeignKey("transcripts.id"), nullable=True)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    summary_json: Mapped[str] = mapped_column(Text, default="", nullable=False)
    entities_json: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Reminder(Base):
    __tablename__ = "reminders"
    __table_args__ = (
        CheckConstraint("schedule_type IN ('daily', 'monthly', 'unscheduled')", name="ck_reminder_schedule_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    medicine_name: Mapped[str] = mapped_column(String, nullable=False)
    dosage: Mapped[str] = mapped_column(String, default="", nullable=False)
    frequency: Mapped[str] = mapped_column(String, default="", nullable=False)  # legacy free-text
    schedule_type: Mapped[str] = mapped_column(String, default="unscheduled", nullable=False)
    quantity_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quantity_remaining: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quantity_per_dose: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    low_stock_threshold: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    refill_alert_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    slots: Mapped[list[ReminderScheduleSlot]] = relationship(
        back_populates="reminder", cascade="all, delete-orphan"
    )


class ReminderScheduleSlot(Base):
    """One concrete fire time per reminder: daily reminders may have several
    rows (e.g. 8am + 8pm); monthly reminders set day_of_month."""

    __tablename__ = "reminder_schedule_slots"
    __table_args__ = (
        CheckConstraint("day_of_month IS NULL OR (day_of_month BETWEEN 1 AND 28)", name="ck_slot_day_of_month"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reminder_id: Mapped[int] = mapped_column(ForeignKey("reminders.id"), nullable=False)
    time_of_day: Mapped[time] = mapped_column(Time, nullable=False)
    day_of_month: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    apscheduler_job_id: Mapped[str | None] = mapped_column(String, nullable=True)

    reminder: Mapped[Reminder] = relationship(back_populates="slots")


class DoseLog(Base):
    """Explicit "mark taken" audit trail — quantity_remaining only ever
    decrements from a row inserted here, never from the clock alone."""

    __tablename__ = "dose_logs"
    __table_args__ = (
        CheckConstraint("status IN ('taken', 'skipped', 'missed_auto')", name="ck_dose_log_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reminder_id: Mapped[int] = mapped_column(ForeignKey("reminders.id"), nullable=False)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False)
    slot_id: Mapped[int | None] = mapped_column(ForeignKey("reminder_schedule_slots.id"), nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False)
    logged_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    taken_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint(
            "type IN ('dose_reminder', 'refill_alert', 'missed_dose', 'assignment', 'system')",
            name="ck_notification_type",
        ),
        CheckConstraint("channel IN ('in_app', 'email', 'both')", name="ck_notification_channel"),
        CheckConstraint("status IN ('pending', 'sent', 'failed', 'read')", name="ck_notification_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    patient_id: Mapped[int | None] = mapped_column(ForeignKey("patients.id"), nullable=True)
    type: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[str] = mapped_column(String, default="in_app", nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    related_reminder_id: Mapped[int | None] = mapped_column(ForeignKey("reminders.id"), nullable=True)
    related_transcript_id: Mapped[int | None] = mapped_column(ForeignKey("transcripts.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Transcript(Base):
    __tablename__ = "transcripts"
    __table_args__ = (
        CheckConstraint(
            "status IN ('uploaded', 'transcribing', 'transcribed', 'structuring', 'draft_ready', 'finalized', 'failed')",
            name="ck_transcript_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    audio_filename: Mapped[str] = mapped_column(String, nullable=False)
    audio_path: Mapped[str] = mapped_column(String, nullable=False)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_transcript_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    stt_provider: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="uploaded", nullable=False)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SoapNote(Base):
    __tablename__ = "soap_notes"
    __table_args__ = (
        UniqueConstraint("transcript_id", name="uq_soap_note_transcript"),
        CheckConstraint("status IN ('draft', 'finalized')", name="ck_soap_note_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    transcript_id: Mapped[int] = mapped_column(ForeignKey("transcripts.id"), nullable=False)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    subjective: Mapped[str] = mapped_column(Text, default="", nullable=False)
    objective: Mapped[str] = mapped_column(Text, default="", nullable=False)
    assessment: Mapped[str] = mapped_column(Text, default="", nullable=False)
    plan: Mapped[str] = mapped_column(Text, default="", nullable=False)
    entities_json: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String, default="draft", nullable=False)
    linked_report_id: Mapped[int | None] = mapped_column(ForeignKey("reports.id"), nullable=True)
    finalized_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ConversationTurn(Base):
    __tablename__ = "conversation_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False)
    user_message: Mapped[str] = mapped_column(Text, nullable=False)
    assistant_response: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
