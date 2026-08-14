"""
agents/planner_agent.py

Planner Agent — the "brain" that makes this Agentic AI rather than a
chatbot. Takes one free-text user request and decomposes it into an
ordered `Plan` of typed `Task`s that the orchestrator then executes
against the specialist agents.

Intent detection is rule-based (keyword/regex), not an LLM call: for a
closed, well-known domain like "things you can ask a health-report
assistant to do", a transparent rule set is more reliable than an LLM
classifier, has zero latency/cost, and — same rationale as the mock LLM
provider — every decision is traceable in a viva ("it matched the word
'remind'"), which a black-box classifier can't offer.
"""

from __future__ import annotations

import re

from schemas import Plan, Task, TaskType
from utils.exceptions import PlannerError
from utils.logger import get_logger

logger = get_logger(__name__)

# Ordered so that, if several intents match, tasks come out in a sensible
# execution sequence (read -> summarize -> answer -> remind -> report).
_INTENT_PATTERNS: list[tuple[TaskType, re.Pattern]] = [
    (
        TaskType.SUMMARIZE,
        re.compile(r"\b(summar\w*|key finding|abnormal|overview|findings?)\b", re.IGNORECASE),
    ),
    (
        TaskType.ANSWER_QUESTION,
        re.compile(
            r"(\?\s*$|\bwhat\s+is\b|\bwhat('| i)?s\b|\bexplain\b|\bhow\s+(much|many|is)\b|"
            r"\bam\s+i\b|\bdo\s+i\b|\bshould\s+i\b|\bwhy\b|\btell\s+me\b)",
            re.IGNORECASE,
        ),
    ),
    (
        TaskType.LIST_REMINDERS,
        re.compile(r"\b(show|list|what are)\s+my\s+reminders?\b|\bwhat medic\w* am i taking\b", re.IGNORECASE),
    ),
    (
        TaskType.SET_REMINDER,
        re.compile(r"\bremind\s+me\b|\bset\s+a?\s*reminder\b|\btake\s+.*\b(daily|morning|night)\b", re.IGNORECASE),
    ),
    (
        TaskType.GENERATE_REPORT,
        re.compile(r"\b(generate|prepare|create|download|export)\b.*\breport\b|\bdoctor('s)? summary\b", re.IGNORECASE),
    ),
    (
        TaskType.CHECK_INTERACTIONS,
        re.compile(r"\binteract\w*\b|\bsafe\s+to\s+take\b|\bcan\s+i\s+take\b.*\band\b|\btogether\b", re.IGNORECASE),
    ),
    (
        TaskType.VIEW_TIMELINE,
        re.compile(
            r"\btimeline\b|\bover\s+time\b|\bhow\s+(has|have)\s+my\b.*\bchanged\b|"
            r"\b(previous|past|earlier|old)\s+reports?\b|\bhistory\s+of\s+my\b",
            re.IGNORECASE,
        ),
    ),
]


def _extract_medicine_reminder(request: str) -> dict:
    """Best-effort extraction of a medicine name + frequency from free text.

    Deliberately simple: this is for the reminder demo path, not a
    dosage-parsing NLP problem in its own right.
    """
    freq_match = re.search(r"\b(morning|night|daily|twice a day|thrice a day|evening)\b", request, re.IGNORECASE)
    # Medicine name heuristic: word right after "take"/"remind me to take"
    med_match = re.search(r"take\s+([A-Za-z][A-Za-z0-9\- ]{1,30}?)(?:\s+(?:in|at|every|daily|morning|night|evening)|$|\.|,)", request, re.IGNORECASE)
    return {
        "medicine_name": med_match.group(1).strip() if med_match else "",
        "frequency": freq_match.group(1).strip() if freq_match else "",
    }


def create_plan(user_request: str, has_report: bool) -> Plan:
    """Decompose one free-text request into an ordered, executable `Plan`.

    Args:
        user_request: the raw text the user typed.
        has_report: whether a report has already been uploaded/parsed in
            this session — used to auto-prepend READ_REPORT and to decide
            whether SUMMARIZE/ANSWER_QUESTION are even runnable.

    Raises:
        PlannerError: if the request is empty or matches no known intent.
    """
    if not user_request or not user_request.strip():
        raise PlannerError("Cannot plan an empty request.")

    matched_types: list[TaskType] = []
    for task_type, pattern in _INTENT_PATTERNS:
        if pattern.search(user_request):
            matched_types.append(task_type)

    if not matched_types:
        # No explicit intent keyword matched. If a report exists, the most
        # useful default is to treat it as a question; otherwise ask for
        # a summary so the user always gets *something* useful back.
        matched_types = [TaskType.ANSWER_QUESTION] if has_report else [TaskType.SUMMARIZE]

    # Generic wh-words ("what", "why") can co-match ANSWER_QUESTION even on
    # requests that are clearly list/generate intents ("what are my
    # reminders?"). Only keep ANSWER_QUESTION alongside another matched
    # intent if the request looks like a genuine question (has "?" or
    # explicitly says "explain"/"what is").
    other_intents = [t for t in matched_types if t != TaskType.ANSWER_QUESTION]
    looks_like_real_question = bool(
        re.search(r"\bexplain\b|\bwhat\s+is\b|\bwhat('| i)?s\b|\bwhy\b", user_request, re.IGNORECASE)
    )
    if TaskType.ANSWER_QUESTION in matched_types and other_intents and not looks_like_real_question:
        matched_types = other_intents

    tasks: list[Task] = []
    # VIEW_TIMELINE deliberately excluded: it reads the *full* report history
    # from the database (agents/timeline_agent.py), not the current session's
    # active report, so it shouldn't require one to be loaded right now.
    needs_report = {TaskType.SUMMARIZE, TaskType.ANSWER_QUESTION, TaskType.GENERATE_REPORT, TaskType.CHECK_INTERACTIONS}
    if has_report and any(t in needs_report for t in matched_types):
        tasks.append(Task(task_type=TaskType.READ_REPORT, description="Load the uploaded report into working memory"))

    for task_type in matched_types:
        if task_type == TaskType.SUMMARIZE:
            tasks.append(Task(task_type=task_type, description="Summarize the report and flag abnormal values"))
        elif task_type == TaskType.ANSWER_QUESTION:
            tasks.append(Task(task_type=task_type, description="Answer the user's question from the report", payload={"question": user_request}))
        elif task_type == TaskType.SET_REMINDER:
            tasks.append(Task(task_type=task_type, description="Store a medicine reminder", payload=_extract_medicine_reminder(user_request)))
        elif task_type == TaskType.LIST_REMINDERS:
            tasks.append(Task(task_type=task_type, description="List saved medicine reminders"))
        elif task_type == TaskType.GENERATE_REPORT:
            tasks.append(Task(task_type=task_type, description="Generate a downloadable doctor-summary PDF"))
        elif task_type == TaskType.CHECK_INTERACTIONS:
            tasks.append(Task(task_type=task_type, description="Check known medicines for interaction warnings"))
        elif task_type == TaskType.VIEW_TIMELINE:
            tasks.append(Task(task_type=task_type, description="Build a timeline across all uploaded reports"))

    # ASSESS_RISK (v5) is never keyword-triggered — a triage classification
    # shouldn't depend on the patient happening to ask for one. It runs
    # automatically any turn where a report is actually being read, right
    # after READ_REPORT/SUMMARIZE so entities are already populated.
    if any(t.task_type in (TaskType.READ_REPORT, TaskType.SUMMARIZE) for t in tasks):
        tasks.append(Task(task_type=TaskType.ASSESS_RISK, description="Classify current clinical risk level"))

    logger.info("Planner produced %d task(s) for request: %r", len(tasks), user_request)
    return Plan(user_request=user_request, tasks=tasks)
