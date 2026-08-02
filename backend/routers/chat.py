"""
backend/routers/chat.py

The planner/executor chat endpoint. Builds a fresh `Orchestrator` per
request — safe because `Orchestrator.__init__` already rehydrates all
session state from the DB (see agents/orchestrator.py's module docstring)
— so there is no server-side session to keep in sync across requests or
worker processes.

Nurses are excluded per the RBAC matrix: chat/QA is a patient+doctor
capability, not a nursing one (nurses get reminder/dose-log access only).

Voice input (v4): POST .../chat/voice reuses the exact same STT pipeline
built for transcript-to-report (tools/speech_to_text.py) to transcribe a
recorded message, then feeds the transcribed text through the identical
Orchestrator.handle_request() path as text chat — same RBAC, same
response shape. AgentRunResult.plan.user_request already carries the
transcribed text back to the caller, so no new response schema is needed
for the frontend to show "you said: ...". Spoken *output* is handled
entirely client-side via the browser's SpeechSynthesis API — no backend
TTS involved.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from agents.orchestrator import Orchestrator
from backend.db import get_db
from backend.deps import get_current_user, require_patient_access
from backend.pg_repository import PgRepository
from backend.schemas_api import ChatRequest
from config import settings
from schemas import AgentRunResult
from tools.speech_to_text import get_stt_provider
from utils.exceptions import MediAgentError

router = APIRouter(prefix="/api/patients/{patient_id}/chat", tags=["chat"])

_VOICE_CHAT_DIR = settings.upload_dir / "voice_chat"


def _forbid_nurse(current_user) -> None:
    if current_user.role == "nurse":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Nurses don't have chat/QA access.")


@router.post("", response_model=AgentRunResult)
def chat(
    payload: ChatRequest,
    patient=Depends(require_patient_access),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AgentRunResult:
    _forbid_nurse(current_user)
    repo = PgRepository(db)
    orch = Orchestrator(repo, patient.id)
    return orch.handle_request(payload.message)


@router.post("/voice", response_model=AgentRunResult)
async def chat_voice(
    file: UploadFile,
    patient=Depends(require_patient_access),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AgentRunResult:
    _forbid_nurse(current_user)

    _VOICE_CHAT_DIR.mkdir(parents=True, exist_ok=True)
    dest = _VOICE_CHAT_DIR / f"{uuid.uuid4().hex}_{file.filename}"
    dest.write_bytes(await file.read())

    try:
        transcribed_text = get_stt_provider().transcribe(dest)
    except MediAgentError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    repo = PgRepository(db)
    orch = Orchestrator(repo, patient.id)
    return orch.handle_request(transcribed_text)
