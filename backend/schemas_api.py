"""
backend/schemas_api.py

Pydantic request/response DTOs for the FastAPI wire format. Kept separate
from `schemas.py` (the shared agent/domain layer) on purpose: `schemas.py`
models are consumed by the agents and must stay auth-agnostic; these
models are HTTP-shape and mostly wrap SQLAlchemy ORM rows via
`from_attributes=True`. Where a `schemas.py` model already matches what an
endpoint needs to return (e.g. `AgentRunResult`, `TimelineEvent`,
`DrugInteractionWarning`), routers use it directly instead of duplicating
it here.
"""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

Role = Literal["doctor", "patient", "nurse", "staff"]
ProviderRole = Literal["doctor", "nurse"]
ScheduleType = Literal["daily", "monthly", "unscheduled"]
DoseStatus = Literal["taken", "skipped"]


# --------------------------------------------------------------------------
# Auth / users
# --------------------------------------------------------------------------
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserCreateRequest(BaseModel):
    """Staff-only: create a doctor/nurse/staff/patient account."""

    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str
    role: Role


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: Role
    is_active: bool
    created_at: datetime


# --------------------------------------------------------------------------
# Patients
# --------------------------------------------------------------------------
class PatientCreateRequest(BaseModel):
    """Staff-only: chart a new patient, optionally without a login (walk-in)."""

    name: str
    date_of_birth: date | None = None
    phone: str | None = None


class PatientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None
    name: str
    date_of_birth: date | None
    phone: str | None
    created_at: datetime


# --------------------------------------------------------------------------
# Care assignments (staff-only management)
# --------------------------------------------------------------------------
class AssignmentCreateRequest(BaseModel):
    patient_id: int
    staff_user_id: int
    role_at_assignment: ProviderRole


class AssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    staff_user_id: int
    role_at_assignment: ProviderRole
    assigned_at: datetime
    active: bool


# --------------------------------------------------------------------------
# Reports
# --------------------------------------------------------------------------
class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    filename: str
    source_type: str
    created_at: datetime


class ReportDetailOut(ReportOut):
    raw_text: str
    summary_json: str
    entities_json: str


# --------------------------------------------------------------------------
# Chat
# --------------------------------------------------------------------------
class ChatRequest(BaseModel):
    message: str = Field(min_length=1)


# --------------------------------------------------------------------------
# Reminders
# --------------------------------------------------------------------------
class ScheduleSlotIn(BaseModel):
    time_of_day: time
    day_of_month: int | None = Field(default=None, ge=1, le=28)


class ScheduleSlotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    time_of_day: time
    day_of_month: int | None


class ReminderCreateRequest(BaseModel):
    medicine_name: str
    dosage: str = ""
    schedule_type: ScheduleType = "unscheduled"
    quantity_total: int | None = None
    quantity_per_dose: int = 1
    low_stock_threshold: int = 5
    slots: list[ScheduleSlotIn] = Field(default_factory=list)


class ReminderUpdateRequest(BaseModel):
    medicine_name: str | None = None
    dosage: str | None = None
    schedule_type: ScheduleType | None = None
    quantity_total: int | None = None
    quantity_remaining: int | None = None
    quantity_per_dose: int | None = None
    low_stock_threshold: int | None = None
    active: bool | None = None


class ReminderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    medicine_name: str
    dosage: str
    schedule_type: ScheduleType
    quantity_total: int | None
    quantity_remaining: int | None
    quantity_per_dose: int
    low_stock_threshold: int
    refill_alert_sent: bool
    active: bool
    created_at: datetime
    slots: list[ScheduleSlotOut] = Field(default_factory=list)


class MarkDoseRequest(BaseModel):
    slot_id: int | None = None
    status: DoseStatus = "taken"


# --------------------------------------------------------------------------
# Notifications
# --------------------------------------------------------------------------
class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    title: str
    body: str
    channel: str
    status: str
    related_reminder_id: int | None
    related_transcript_id: int | None
    created_at: datetime
    sent_at: datetime | None
    read_at: datetime | None


# --------------------------------------------------------------------------
# Transcripts / SOAP notes
# --------------------------------------------------------------------------
class TranscriptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    doctor_id: int
    audio_filename: str
    status: str
    duration_seconds: float | None
    error_detail: str | None
    created_at: datetime
    updated_at: datetime


class SoapNoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    transcript_id: int
    patient_id: int
    subjective: str
    objective: str
    assessment: str
    plan: str
    status: str
    linked_report_id: int | None
    created_at: datetime
    finalized_at: datetime | None


class SoapNoteUpdateRequest(BaseModel):
    subjective: str | None = None
    objective: str | None = None
    assessment: str | None = None
    plan: str | None = None


# --------------------------------------------------------------------------
# Doctor/nurse analytics (v4)
# --------------------------------------------------------------------------
class LabTrendPoint(BaseModel):
    report_id: int
    report_date: datetime
    report_filename: str
    label: str
    raw_value: str
    numeric_value: float
    is_abnormal: bool
    reference_range: str


class ReminderAdherence(BaseModel):
    reminder_id: int
    medicine_name: str
    taken: int
    skipped: int
    missed: int
    adherence_pct: float  # taken / (taken + missed), skipped excluded from the denominator


AbnormalTrend = Literal["up", "down", "flat", "unknown"]


class AnalyticsSummary(BaseModel):
    total_reports: int
    total_abnormal_readings: int
    abnormal_trend: AbnormalTrend
    active_reminders: int
    doses_missed_this_week: int
