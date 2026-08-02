"""
agents/orchestrator.py

The executor half of the plan -> act -> observe loop. Takes the Planner
Agent's `Plan`, runs each `Task` against the matching specialist agent in
order, threads shared state between them (the loaded report text, its
extracted entities, running Q&A history), and logs every step for the
UI's execution timeline — each step tagged with its autonomy level and
risk tier from `agents/governance.py`.

`Session` is this build's "Memory Agent": it holds the uploaded report,
extracted entities, generated summary, and Q&A history for the lifetime
of one Streamlit/CLI session. Critically, the *report itself* is also
persisted to SQLite the moment it's loaded (`load_report`), and
`Orchestrator.__init__` rehydrates the session from the database if it's
ever constructed empty — e.g. after a server restart, or a redeploy — so
an uploaded report can't silently "disappear" from the assistant's point
of view while the UI still shows it as active. That exact failure mode
(session state lost, active-report UI stale) is what the in-conversation
bug report traced back to; this fixes the root cause rather than papering
over the symptom.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field

from agents import (
    drug_interaction_agent,
    governance,
    qa_agent,
    reminder_agent,
    report_generator_agent,
    summarizer_agent,
    timeline_agent,
)
from agents.planner_agent import create_plan
from schemas import (
    AgentRunResult,
    AgentStepLog,
    AgentStepStatus,
    ConversationTurn,
    DrugInteractionWarning,
    ExtractedEntities,
    QAResult,
    Reminder,
    Report,
    ReportSummary,
    TaskType,
    TimelineEvent,
)
from tools.database import Repository
from tools.medical_ner import extract_entities
from utils.exceptions import MediAgentError
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Session:
    """In-memory state for one uploaded report + its conversation, per patient."""

    patient_id: int
    report_id: int | None = None
    report_text: str = ""
    report_filename: str = ""
    entities: ExtractedEntities | None = None
    summary: ReportSummary | None = None
    qa_history: list[QAResult] = field(default_factory=list)
    # Populated per-request by _execute_task, read back by handle_request.
    last_report_path: str | None = None
    last_interaction_warnings: list[DrugInteractionWarning] = field(default_factory=list)
    last_timeline: list[TimelineEvent] = field(default_factory=list)
    last_step_gated: bool = False

    @property
    def has_report(self) -> bool:
        return bool(self.report_text)


class Orchestrator:
    """Coordinates the Planner Agent and every specialist agent for one patient session."""

    def __init__(self, repo: Repository, patient_id: int) -> None:
        self.repo = repo
        self.session = Session(patient_id=patient_id)
        self._hydrate_from_db()

    # -- durability: recover session state from SQLite if it's missing ------
    def _hydrate_from_db(self) -> None:
        """If this Orchestrator was constructed with an empty session (e.g.
        the in-memory session was lost to a server restart), recover the
        most recently uploaded report from the database instead of leaving
        the assistant thinking nothing was ever uploaded.
        """
        if self.session.has_report:
            return
        latest = self.repo.get_latest_report(self.session.patient_id)
        if latest is None:
            return
        self.session.report_id = latest.id
        self.session.report_text = latest.raw_text
        self.session.report_filename = latest.filename
        if latest.entities_json:
            try:
                self.session.entities = ExtractedEntities(**json.loads(latest.entities_json))
            except (json.JSONDecodeError, TypeError):
                self.session.entities = None
        if latest.summary_json:
            try:
                self.session.summary = ReportSummary(**json.loads(latest.summary_json))
            except (json.JSONDecodeError, TypeError):
                self.session.summary = None
        logger.info("Rehydrated session for patient %s from database: %s", self.session.patient_id, latest.filename)

    # -- report ingestion -----------------------------------------------
    def load_report(self, report_text: str, filename: str) -> None:
        """Register newly-extracted report text with the session AND persist
        it to SQLite immediately — this is the fix: report state used to
        live only in server memory, which is why it could disappear from
        under a still-showing "active report" UI.
        """
        self.session.report_text = report_text
        self.session.report_filename = filename
        self.session.entities = None  # invalidate cache; recomputed on first SUMMARIZE/use
        self.session.summary = None
        saved = self.repo.save_report(Report(patient_id=self.session.patient_id, filename=filename, raw_text=report_text))
        self.session.report_id = saved.id

    # -- main entry point --------------------------------------------------
    def handle_request(self, user_request: str) -> AgentRunResult:
        """Plan and execute one user request, returning a full result for the UI."""
        plan = create_plan(user_request, has_report=self.session.has_report)
        log: list[AgentStepLog] = []
        response_parts: list[str] = []
        self.session.last_report_path = None
        self.session.last_interaction_warnings = []
        self.session.last_timeline = []

        for task in plan.tasks:
            step_start = time.perf_counter()
            agent_name = task.task_type.value
            autonomy, risk_tier = governance.get_governance(task.task_type)
            self.session.last_step_gated = False
            try:
                text = self._execute_task(task)
                status = AgentStepStatus.SKIPPED if self.session.last_step_gated else AgentStepStatus.DONE
                if text:
                    response_parts.append(text)
                log.append(
                    AgentStepLog(
                        agent_name=agent_name,
                        status=status,
                        detail=task.description,
                        duration_ms=int((time.perf_counter() - step_start) * 1000),
                        autonomy=autonomy,
                        risk_tier=risk_tier,
                    )
                )
            except MediAgentError as exc:
                logger.warning("Task %s failed: %s", agent_name, exc)
                log.append(
                    AgentStepLog(
                        agent_name=agent_name,
                        status=AgentStepStatus.FAILED,
                        detail=str(exc),
                        duration_ms=int((time.perf_counter() - step_start) * 1000),
                        autonomy=autonomy,
                        risk_tier=risk_tier,
                    )
                )
                response_parts.append(f"[{agent_name}] couldn't complete: {exc}")

        final_response = "\n\n".join(response_parts) or "I couldn't find an actionable task in that request."
        self.repo.add_conversation_turn(
            ConversationTurn(
                patient_id=self.session.patient_id,
                user_message=user_request,
                assistant_response=final_response,
            )
        )

        return AgentRunResult(
            final_response=final_response,
            plan=plan,
            execution_log=log,
            entities=self.session.entities,
            summary=self.session.summary,
            qa_results=self.session.qa_history[-1:],
            reminders=self.repo.list_reminders(self.session.patient_id),
            report_file_path=self.session.last_report_path,
            interaction_warnings=self.session.last_interaction_warnings,
            timeline=self.session.last_timeline,
        )

    # -- per-task dispatch ------------------------------------------------
    def _execute_task(self, task) -> str:
        if task.task_type == TaskType.READ_REPORT:
            if not self.session.has_report:
                raise MediAgentError("No report has been uploaded yet.")
            if self.session.entities is None:
                self.session.entities = extract_entities(self.session.report_text)
            return f"Loaded report '{self.session.report_filename}' ({len(self.session.report_text)} characters)."

        if task.task_type == TaskType.SUMMARIZE:
            if not self.session.has_report:
                raise MediAgentError("Upload a report before asking for a summary.")
            if self.session.entities is None:
                self.session.entities = extract_entities(self.session.report_text)
            self.session.summary = summarizer_agent.summarize_report(self.session.report_text, self.session.entities)
            self._cache_analysis_to_db()
            return self.session.summary.patient_summary

        if task.task_type == TaskType.ANSWER_QUESTION:
            if not self.session.has_report:
                raise MediAgentError("Upload a report before asking questions about it.")
            question = task.payload.get("question") or task.description
            # Recent turns were already persisted by the previous
            # handle_request() call (add_conversation_turn runs at the end
            # of that method) — fetching them here naturally excludes the
            # in-flight question, no special-casing needed.
            history = self.repo.get_conversation_history(self.session.patient_id, limit=5)
            result = qa_agent.answer_question(
                self.session.report_text,
                question,
                history=history,
                repo=self.repo,
                patient_id=self.session.patient_id,
            )
            self.session.qa_history.append(result)
            return result.answer

        if task.task_type == TaskType.SET_REMINDER:
            # Governance gate (A2: execute-with-gates — see governance.py):
            # a low-confidence extraction is not silently saved as a guess.
            # This is what makes the autonomy label a real behavior rather
            # than just a UI badge.
            name = (task.payload.get("medicine_name") or "").strip()
            freq = (task.payload.get("frequency") or "").strip()
            if not name:
                self.session.last_step_gated = True
                return (
                    "I couldn't confidently identify the medicine name, so I didn't save a reminder. "
                    "Try rephrasing, e.g. \"remind me to take Metformin every morning.\""
                )
            saved = reminder_agent.add_reminder(self.repo, self.session.patient_id, name, frequency=freq)
            return f"Reminder saved: {saved.medicine_name} ({saved.frequency or 'no schedule specified'})."

        if task.task_type == TaskType.LIST_REMINDERS:
            items = reminder_agent.list_reminders_with_schedule(self.repo, self.session.patient_id)
            if not items:
                return "You have no saved medicine reminders yet."
            lines = [f"- {i['medicine_name']} ({i['frequency'] or 'no schedule'}) — next: {i['next_dose']}" for i in items]
            return "Your reminders:\n" + "\n".join(lines)

        if task.task_type == TaskType.GENERATE_REPORT:
            reminders: list[Reminder] = self.repo.list_reminders(self.session.patient_id)
            path = report_generator_agent.generate_pdf_report(
                patient_name="Demo Patient",
                summary=self.session.summary,
                entities=self.session.entities,
                reminders=reminders,
                qa_history=self.session.qa_history,
            )
            self.session.last_report_path = path
            return f"Doctor-summary report generated: {path}"

        if task.task_type == TaskType.CHECK_INTERACTIONS:
            medicine_names = list(self.session.entities.medicines) if self.session.entities else []
            medicine_names += [r.medicine_name for r in self.repo.list_reminders(self.session.patient_id)]
            if not medicine_names:
                self.session.last_step_gated = True
                return "No medicines are known yet (from a report or saved reminders), so there's nothing to check."
            warnings = drug_interaction_agent.check_interactions(medicine_names)
            self.session.last_interaction_warnings = warnings
            if not warnings:
                return f"Checked {len({m.lower() for m in medicine_names})} known medicine(s) — no interactions found in the curated reference table."
            lines = [f"- {w.drug_a} + {w.drug_b} ({w.severity}): {w.note}" for w in warnings]
            return "Possible interactions found — confirm with your pharmacist or doctor:\n" + "\n".join(lines)

        if task.task_type == TaskType.VIEW_TIMELINE:
            timeline = timeline_agent.build_timeline(self.repo, self.session.patient_id)
            self.session.last_timeline = timeline
            if len(timeline) < 2:
                self.session.last_step_gated = True
                return "A timeline needs at least two uploaded reports to show what's changed — only one is on file so far."
            lines = [f"- {e.uploaded_at} ({e.report_filename}): {', '.join(e.new_since_previous) or 'no new findings'}" for e in timeline[1:]]
            return "Timeline across your uploaded reports:\n" + "\n".join(lines)

        raise MediAgentError(f"Unknown task type: {task.task_type}")

    def _cache_analysis_to_db(self) -> None:
        """Persist the current session's computed summary/entities back onto
        the report row, so the Timeline Agent (or a future session) can
        reuse them instead of recomputing NER from scratch."""
        if self.session.report_id is None:
            return
        self.repo.update_report_analysis(
            self.session.report_id,
            summary_json=self.session.summary.model_dump_json() if self.session.summary else "",
            entities_json=self.session.entities.model_dump_json() if self.session.entities else "",
        )
