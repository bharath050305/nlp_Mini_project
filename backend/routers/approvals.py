"""
backend/routers/approvals.py

Human-in-the-loop approval worklist (v5) — doctor/nurse only. Lists
every pending item the Supervisor agent flagged (agents/supervisor_agent.py)
across all of the current provider's assigned patients, and lets them
approve/reject with an optional note. This is the "human gate" the
project's governance philosophy has always pointed toward: A2+ actions
get a real approve/reject decision, not just a UI badge.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.deps import require_role
from backend.pg_repository import PgRepository
from backend.schemas_api import ApprovalDecisionRequest, ApprovalOut

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


@router.get("", response_model=list[ApprovalOut])
def list_pending_approvals(
    current_user=Depends(require_role("doctor", "nurse")),
    db: Session = Depends(get_db),
) -> list[ApprovalOut]:
    repo = PgRepository(db)
    return repo.list_pending_approvals_for_provider(current_user.id, current_user.role)


@router.post("/{approval_id}/decision", response_model=ApprovalOut)
def decide_approval(
    approval_id: int,
    payload: ApprovalDecisionRequest,
    current_user=Depends(require_role("doctor", "nurse")),
    db: Session = Depends(get_db),
) -> ApprovalOut:
    repo = PgRepository(db)

    # Only resolve approvals for patients this provider is actually
    # assigned to — same scoping as the worklist itself, so a doctor
    # can't approve/reject items for a patient they don't have access to.
    pending_ids = {a.id for a in repo.list_pending_approvals_for_provider(current_user.id, current_user.role)}
    if approval_id not in pending_ids:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Approval not found or already resolved.")

    resolved = repo.resolve_approval(
        approval_id, reviewer_id=current_user.id, decision=payload.decision, note=payload.note
    )
    if resolved is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Approval not found.")
    return resolved
