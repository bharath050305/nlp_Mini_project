"""
schemas.py

Pydantic domain models shared by every layer of MediAgent: the database
repository returns/accepts these, agents consume/produce these, and the
UI renders these directly. Keeping one definition here (instead of ad-hoc
dicts) is what makes the multi-agent handoff type-safe.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------
# Planner / execution
# --------------------------------------------------------------------------
class TaskType(str, Enum):
    """The finite set of sub-tasks the Planner Agent can emit.

    Every agent in `agents/` corresponds to exactly one of these, which is
    what keeps the orchestrator's dispatch table a simple 1:1 mapping.
    """

    READ_REPORT = "read_report"
    SUMMARIZE = "summarize"
    ANSWER_QUESTION = "answer_question"
    SET_REMINDER = "set_reminder"
    LIST_REMINDERS = "list_reminders"
    GENERATE_REPORT = "generate_report"
    CHECK_INTERACTIONS = "check_interactions"
    VIEW_TIMELINE = "view_timeline"
    ASSESS_RISK = "assess_risk"


class AutonomyLevel(str, Enum):
    """Agent autonomy scale (A0-A3), adapted from Xu et al., "A comprehensive
    survey of AI agents in healthcare," J. Biomed. Inform. 179 (2026) 105045,
    Table 4. Every task in MediAgent is pinned to one of these levels so the
    UI can show, honestly, how much independence the system actually has —
    rather than implying more autonomy than is really there.
    """

    A0_SUGGEST_ONLY = "A0"
    A1_DRAFT_FOR_SIGNOFF = "A1"
    A2_EXECUTE_WITH_GATES = "A2"
    # A3 (fully autonomous execution) is deliberately unused: the survey's
    # own review of 223 healthcare-agent studies found no fully autonomous
    # (A3) deployments in clinical contexts (Sec. 8.3) — MediAgent doesn't
    # claim a level of autonomy the published literature doesn't support.


class RiskTier(str, Enum):
    """Risk tier scale (R0-R3), adapted from the same survey's Table 4/6.

    Reflects escalating potential for harm if the agent is wrong, not how
    "important" a feature feels — e.g. a drug-interaction flag is R2
    (clinical decision support) even though it's just one line of text,
    because being wrong about it has real safety consequences.
    """

    R0_ADMINISTRATIVE = "R0"
    R1_PATIENT_INFORMATIONAL = "R1"
    R2_CLINICAL_DECISION_SUPPORT = "R2"
    R3_DIRECT_INTERVENTION = "R3"  # not used by any task in this build


class Task(BaseModel):
    """A single unit of work in an execution plan."""

    task_type: TaskType
    description: str
    payload: dict = Field(default_factory=dict)


class Plan(BaseModel):
    """The Planner Agent's decomposition of one user request."""

    user_request: str
    tasks: list[Task]


class AgentStepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


class AgentStepLog(BaseModel):
    """One row of the execution timeline shown in the UI."""

    agent_name: str
    status: AgentStepStatus
    detail: str = ""
    duration_ms: int | None = None
    autonomy: AutonomyLevel | None = None
    risk_tier: RiskTier | None = None


# --------------------------------------------------------------------------
# Medical NER
# --------------------------------------------------------------------------
class MedicalEntity(BaseModel):
    text: str
    label: str  # DISEASE | MEDICINE | SYMPTOM | LAB_TEST | LAB_VALUE | DOSAGE | DATE
    start_char: int
    end_char: int


class ExtractedEntities(BaseModel):
    diseases: list[str] = Field(default_factory=list)
    medicines: list[str] = Field(default_factory=list)
    symptoms: list[str] = Field(default_factory=list)
    lab_tests: list[str] = Field(default_factory=list)
    lab_values: list[str] = Field(default_factory=list)
    dosages: list[str] = Field(default_factory=list)
    dates: list[str] = Field(default_factory=list)
    raw_entities: list[MedicalEntity] = Field(default_factory=list)


# --------------------------------------------------------------------------
# Explainability (survey Sec. 9.5 "Explainability for trustworthy AI";
# Table 3's "Knowledge Retrieval" capability — grounding a claim in the
# specific evidence that produced it, not just asserting it)
# --------------------------------------------------------------------------
class EvidenceItem(BaseModel):
    """One claim, traced back to the exact evidence that supports it.

    This is what separates "your HbA1c is high" (an assertion) from a
    system a clinician can actually audit: claim + the literal value found
    + the reference range it was checked against.
    """

    claim: str
    evidence: str
    reference_range: str = ""


# --------------------------------------------------------------------------
# Lab value reference-range analysis (agents/lab_analysis.py) — shared by
# the summarizer's abnormal-value flagging and the doctor analytics
# dashboard (v4), so both use one reference-range table, not two.
# --------------------------------------------------------------------------
class LabReading(BaseModel):
    raw_value: str
    numeric_value: float
    label: str  # e.g. "HbA1c/percentage value"
    is_abnormal: bool
    reference_range: str


# --------------------------------------------------------------------------
# Summarization
# --------------------------------------------------------------------------
class ReportSummary(BaseModel):
    patient_summary: str
    key_findings: list[str] = Field(default_factory=list)
    abnormal_values: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    confidence: str = "medium"  # low | medium | high — see agents/confidence.py


# --------------------------------------------------------------------------
# QA
# --------------------------------------------------------------------------
class QAResult(BaseModel):
    question: str
    answer: str
    retrieved_chunks: list[str] = Field(default_factory=list)
    confidence: str = "low"  # low | medium | high, from retrieval similarity


# --------------------------------------------------------------------------
# Reminders
# --------------------------------------------------------------------------
class Reminder(BaseModel):
    id: int | None = None
    patient_id: int
    medicine_name: str
    dosage: str = ""
    frequency: str = ""  # legacy free-text, e.g. "morning, night" (conversational path)
    created_at: datetime | None = None
    # -- structured scheduling (v3, optional/backward-compatible) --------------
    schedule_type: str = "unscheduled"  # "daily" | "monthly" | "unscheduled"
    quantity_total: int | None = None
    quantity_remaining: int | None = None
    quantity_per_dose: int = 1
    low_stock_threshold: int = 5
    refill_alert_sent: bool = False
    active: bool = True


# --------------------------------------------------------------------------
# Drug Interaction Agent
# --------------------------------------------------------------------------
class DrugInteractionWarning(BaseModel):
    drug_a: str
    drug_b: str
    severity: str  # "moderate" | "major"
    note: str


# --------------------------------------------------------------------------
# Clinical Timeline Agent (survey Sec. 4.1.3 "Clinical notes" — reconstructing
# a coherent timeline from multiple time-stamped documents)
# --------------------------------------------------------------------------
class TimelineEvent(BaseModel):
    report_filename: str
    uploaded_at: str  # formatted timestamp, kept as str for simple display
    diseases: list[str] = Field(default_factory=list)
    medicines: list[str] = Field(default_factory=list)
    lab_values: list[str] = Field(default_factory=list)
    new_since_previous: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------
# Clinical Triage Agent (v5) — deterministic LOW/MEDIUM/HIGH/CRITICAL risk
# classification. Rule-based by design: the LLM never decides emergency
# care (see agents/triage_agent.py) — same philosophy as the mock LLM
# provider and the curated drug-interaction table.
# --------------------------------------------------------------------------
class TriageResult(BaseModel):
    level: str = "low"  # low | medium | high | critical
    reasons: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------
# Critic / Evidence Verifier Agent (v5) — checks a QA answer against the
# retrieved chunks it was supposedly grounded in. Rule-based (keyword
# overlap), provider-agnostic — verifies the *output*, not the model.
# --------------------------------------------------------------------------
class CriticResult(BaseModel):
    supported: bool = True
    unsupported_claims: list[str] = Field(default_factory=list)
    note: str = ""


# --------------------------------------------------------------------------
# Transcript-to-report agent (v3) — structures a consultation-audio
# transcript into a SOAP note, the same way summarizer_agent structures
# an uploaded PDF report. Kept here (not in backend/db_models.py) because
# it's agent input/output shared across the pipeline, not a persistence
# concern — the same "domain layer" reasoning as ReportSummary/QAResult.
# --------------------------------------------------------------------------
class SOAPNote(BaseModel):
    subjective: str = ""
    objective: str = ""
    assessment: str = ""
    plan: str = ""
    confidence: str = "medium"  # low | medium | high


# --------------------------------------------------------------------------
# Persistence models
# --------------------------------------------------------------------------
class Patient(BaseModel):
    id: int | None = None
    name: str = "Demo Patient"
    created_at: datetime | None = None


class Report(BaseModel):
    id: int | None = None
    patient_id: int
    filename: str
    raw_text: str
    summary_json: str = ""  # serialized ReportSummary
    entities_json: str = ""  # serialized ExtractedEntities
    created_at: datetime | None = None


class ConversationTurn(BaseModel):
    id: int | None = None
    patient_id: int
    user_message: str
    assistant_response: str
    created_at: datetime | None = None


# --------------------------------------------------------------------------
# Orchestrator I/O
# --------------------------------------------------------------------------
class AgentRunResult(BaseModel):
    """Everything the orchestrator hands back to the UI/CLI after one request."""

    final_response: str
    plan: Plan
    execution_log: list[AgentStepLog] = Field(default_factory=list)
    entities: ExtractedEntities | None = None
    summary: ReportSummary | None = None
    qa_results: list[QAResult] = Field(default_factory=list)
    reminders: list[Reminder] = Field(default_factory=list)
    report_file_path: str | None = None
    interaction_warnings: list[DrugInteractionWarning] = Field(default_factory=list)
    timeline: list[TimelineEvent] = Field(default_factory=list)
    # v5: Supervisor / Triage / Critic layer (agents/supervisor_agent.py)
    triage: TriageResult | None = None
    verification: CriticResult | None = None
    requires_human_review: bool = False
    escalation_reason: str | None = None
