"""
backend/routers/chat.py

The planner/executor chat endpoint. Builds a fresh `Orchestrator` per
request — safe because `Orchestrator.__init__` already rehydrates all
session state from the DB (see agents/orchestrator.py's module docstring)
— so there is no server-side session to keep in sync across requests or
worker processes.

Nurses are excluded per the RBAC matrix: chat/QA is a patient+doctor
capability, not a nursing one (nurses get reminder/dose-log access only).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from agents.orchestrator import Orchestrator
from backend.db import get_db
from backend.deps import get_current_user, require_patient_access
from backend.pg_repository import PgRepository
from backend.schemas_api import ChatRequest
from schemas import AgentRunResult

router = APIRouter(prefix="/api/patients/{patient_id}/chat", tags=["chat"])


@router.post("", response_model=AgentRunResult)
def chat(
    payload: ChatRequest,
    patient=Depends(require_patient_access),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AgentRunResult:
    if current_user.role == "nurse":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Nurses don't have chat/QA access.")

    repo = PgRepository(db)
    orch = Orchestrator(repo, patient.id)
    return orch.handle_request(payload.message)
