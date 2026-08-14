"""
agents/supervisor_agent.py

Supervisor Agent (v5) — the top-level entry point `backend/routers/chat.py`
calls, sitting above the existing Planner/Orchestrator rather than
replacing them:

    User -> Supervisor -> Planner -> Orchestrator -> specialist agents
                              |                            |
                              +------- Triage / Critic -----+
                              |
                        Supervisor inspects the combined result
                              |
                    escalation needed? -> approval queue (Postgres)

Concretely: it constructs an `Orchestrator` exactly as the router did
before v5, calls `handle_request()`, then looks at the *combined* result
— the triage level, the critic's verification, any major drug
interaction — and decides whether a human needs to see this before the
patient just walks away with an AI answer. This is the genuine
value-add over the Orchestrator alone: no single specialist agent has
visibility across all three signals at once.

Escalation writes an `agent_approvals` row (Postgres-only — gracefully
absent for the legacy sqlite path via `hasattr`, the same duck-typing
pattern already used for semantic search in agents/qa_agent.py) rather
than blocking the response: the patient still gets their answer
immediately (A0/A1 suggest-and-draft, never a silent A2+ clinical
action), and a doctor/nurse picks up the flagged item from their
Approvals worklist.
"""

from __future__ import annotations

import json

from agents.orchestrator import Orchestrator
from schemas import AgentRunResult
from utils.logger import get_logger

logger = get_logger(__name__)

_MAJOR_INTERACTION_SEVERITY = "major"


def _decide_escalation(result: AgentRunResult) -> str | None:
    """Return a human-readable escalation reason, or None if nothing in
    this result warrants a human look."""
    if result.triage and result.triage.level in ("high", "critical"):
        return f"Triage classified this as {result.triage.level.upper()}: {'; '.join(result.triage.reasons)}"

    if result.verification and not result.verification.supported:
        return f"Answer verification flagged unsupported claim(s): {'; '.join(result.verification.unsupported_claims)}"

    major_interactions = [w for w in result.interaction_warnings if w.severity == _MAJOR_INTERACTION_SEVERITY]
    if major_interactions:
        names = ", ".join(f"{w.drug_a}+{w.drug_b}" for w in major_interactions)
        return f"Major drug interaction flagged: {names}"

    return None


def handle_request(
    repo,
    patient_id: int,
    user_request: str,
    *,
    requested_by_user_id: int | None = None,
) -> AgentRunResult:
    """Run the existing Planner/Orchestrator pipeline, then decide
    whether the combined result needs human review."""
    orchestrator = Orchestrator(repo, patient_id)
    result = orchestrator.handle_request(user_request)

    escalation_reason = _decide_escalation(result)
    if escalation_reason is None:
        return result

    result.requires_human_review = True
    result.escalation_reason = escalation_reason
    logger.warning("Supervisor escalating patient %s: %s", patient_id, escalation_reason)

    if hasattr(repo, "create_approval"):
        approval_type = "triage" if result.triage and result.triage.level in ("high", "critical") else (
            "verification" if result.verification and not result.verification.supported else "interaction"
        )
        detail = {
            "user_request": user_request,
            "final_response": result.final_response,
            "triage": result.triage.model_dump() if result.triage else None,
            "verification": result.verification.model_dump() if result.verification else None,
            "interaction_warnings": [w.model_dump() for w in result.interaction_warnings],
        }
        repo.create_approval(
            patient_id=patient_id,
            requested_by_user_id=requested_by_user_id,
            type=approval_type,
            summary=escalation_reason,
            detail_json=json.dumps(detail),
        )

    return result
