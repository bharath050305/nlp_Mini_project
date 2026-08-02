"""
agents/governance.py

Governance layer, new in this build. Every task the Planner can emit is
pinned to an (autonomy, risk) pair from Xu et al., "A comprehensive survey
of AI agents in healthcare," J. Biomed. Inform. 179 (2026) 105045 — Table 4
(autonomy scale A0-A3 + minimum oversight controls) and Table 5/6 (risk
tiers by application domain).

This isn't decoration. `GOVERNANCE_TABLE` is read by the orchestrator to (a)
label every execution-log step honestly, and (b) actually gate behavior —
see `SET_REMINDER`'s handling in `orchestrator.py`, which refuses to
silently save a low-confidence extraction rather than treating "A2:
execute-with-gates" as just a label with no enforcement behind it.
"""

from __future__ import annotations

from schemas import AutonomyLevel, RiskTier, TaskType

# Rationale for each mapping (kept here, next to the table, so the two never
# drift apart):
#
# READ_REPORT         -> A0/R0  Pure ingestion, no patient-facing claim yet.
# SUMMARIZE            -> A0/R1  Patient-facing informational narrative of
#                                 their own report; suggest-only, never
#                                 states a diagnosis (see prompts.py).
# ANSWER_QUESTION       -> A0/R1  Same reasoning: informational, grounded
#                                 only in the patient's own report text.
# SET_REMINDER          -> A2/R0  Writes one row to a private, fully
#                                 reversible table; gated on extraction
#                                 confidence (empty medicine name -> the
#                                 orchestrator asks for clarification
#                                 instead of saving a guess).
# LIST_REMINDERS        -> A0/R0  Read-only.
# GENERATE_REPORT       -> A1/R1  Produces a draft PDF *for the patient to
#                                 bring to a clinician* - a draft-for-
#                                 sign-off artifact, not a standalone
#                                 clinical output.
# CHECK_INTERACTIONS    -> A0/R2  Higher risk tier than summarization: a
#                                 wrong interaction call has real safety
#                                 stakes even though the action itself is
#                                 still suggest-only and always deflects to
#                                 "confirm with your pharmacist."
# VIEW_TIMELINE         -> A0/R1  Read-only synthesis across past reports.
GOVERNANCE_TABLE: dict[TaskType, tuple[AutonomyLevel, RiskTier]] = {
    TaskType.READ_REPORT: (AutonomyLevel.A0_SUGGEST_ONLY, RiskTier.R0_ADMINISTRATIVE),
    TaskType.SUMMARIZE: (AutonomyLevel.A0_SUGGEST_ONLY, RiskTier.R1_PATIENT_INFORMATIONAL),
    TaskType.ANSWER_QUESTION: (AutonomyLevel.A0_SUGGEST_ONLY, RiskTier.R1_PATIENT_INFORMATIONAL),
    TaskType.SET_REMINDER: (AutonomyLevel.A2_EXECUTE_WITH_GATES, RiskTier.R0_ADMINISTRATIVE),
    TaskType.LIST_REMINDERS: (AutonomyLevel.A0_SUGGEST_ONLY, RiskTier.R0_ADMINISTRATIVE),
    TaskType.GENERATE_REPORT: (AutonomyLevel.A1_DRAFT_FOR_SIGNOFF, RiskTier.R1_PATIENT_INFORMATIONAL),
    TaskType.CHECK_INTERACTIONS: (AutonomyLevel.A0_SUGGEST_ONLY, RiskTier.R2_CLINICAL_DECISION_SUPPORT),
    TaskType.VIEW_TIMELINE: (AutonomyLevel.A0_SUGGEST_ONLY, RiskTier.R1_PATIENT_INFORMATIONAL),
}

_OVERSIGHT_NOTES: dict[AutonomyLevel, str] = {
    AutonomyLevel.A0_SUGGEST_ONLY: "Suggestion only — no data is written or acted on.",
    AutonomyLevel.A1_DRAFT_FOR_SIGNOFF: "Produces a draft only; treat it as unsigned until you review it.",
    AutonomyLevel.A2_EXECUTE_WITH_GATES: "Writes data, but only after a confidence gate — low-confidence input is not saved silently.",
}


def get_governance(task_type: TaskType) -> tuple[AutonomyLevel, RiskTier]:
    """Return the (autonomy, risk) pair for a task type. Always defined —
    new task types must be added to GOVERNANCE_TABLE or this raises, by
    design, so nothing new ships silently ungoverned."""
    return GOVERNANCE_TABLE[task_type]


def oversight_note(autonomy: AutonomyLevel) -> str:
    return _OVERSIGHT_NOTES[autonomy]
