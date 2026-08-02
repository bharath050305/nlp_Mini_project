"""
backend/routers/transcripts.py

Audio consultation -> SOAP note pipeline. Doctor-only end to end (see the
RBAC matrix — nurses/staff/patients never touch this router): upload
audio, poll processing status, review/edit the AI-drafted SOAP note, then
finalize it — finalizing also creates a `reports` row so the visit flows
into the existing `timeline_agent`/summarizer pipeline uniformly, which is
how it becomes visible as part of a patient's "previous conditions"
history.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from backend import db_models
from backend.db import get_db
from backend.deps import require_patient_access, require_role
from backend.pg_repository import PgRepository
from backend.schemas_api import SoapNoteOut, SoapNoteUpdateRequest, TranscriptOut
from backend.services.stt_service import process_transcript
from config import settings
from schemas import Report
from tools.medical_ner import extract_entities

router = APIRouter(tags=["transcripts"])

_AUDIO_DIR = settings.upload_dir / "audio"


def _get_transcript_for_doctor(transcript_id: int, current_user, db: Session) -> db_models.Transcript:
    if current_user.role != "doctor":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only doctors can access transcripts.")
    transcript = db.get(db_models.Transcript, transcript_id)
    if transcript is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Transcript not found.")
    assignment = (
        db.query(db_models.CareAssignment)
        .filter_by(patient_id=transcript.patient_id, staff_user_id=current_user.id, role_at_assignment="doctor", active=True)
        .first()
    )
    if assignment is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not assigned to this patient.")
    return transcript


@router.post(
    "/api/patients/{patient_id}/transcripts/upload",
    response_model=TranscriptOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_transcript_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile,
    patient=Depends(require_patient_access),
    current_user=Depends(require_role("doctor")),
    db: Session = Depends(get_db),
) -> TranscriptOut:
    _AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex}_{file.filename}"
    dest = _AUDIO_DIR / safe_name
    dest.write_bytes(await file.read())

    repo = PgRepository(db)
    transcript = repo.create_transcript(
        patient_id=patient.id, doctor_id=current_user.id, audio_filename=file.filename, audio_path=str(dest)
    )
    background_tasks.add_task(process_transcript, transcript.id)
    return transcript


@router.get("/api/patients/{patient_id}/transcripts", response_model=list[TranscriptOut])
def list_transcripts(
    patient=Depends(require_patient_access),
    current_user=Depends(require_role("doctor")),
    db: Session = Depends(get_db),
) -> list[TranscriptOut]:
    return (
        db.query(db_models.Transcript)
        .filter_by(patient_id=patient.id)
        .order_by(db_models.Transcript.id.desc())
        .all()
    )


@router.get("/api/transcripts/{transcript_id}", response_model=TranscriptOut)
def get_transcript(
    transcript_id: int, current_user=Depends(require_role("doctor")), db: Session = Depends(get_db)
) -> TranscriptOut:
    return _get_transcript_for_doctor(transcript_id, current_user, db)


@router.get("/api/transcripts/{transcript_id}/soap", response_model=SoapNoteOut)
def get_soap_note(
    transcript_id: int, current_user=Depends(require_role("doctor")), db: Session = Depends(get_db)
) -> SoapNoteOut:
    _get_transcript_for_doctor(transcript_id, current_user, db)
    repo = PgRepository(db)
    soap = repo.get_soap_note_by_transcript(transcript_id)
    if soap is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "SOAP note isn't ready yet — check the transcript's status.")
    return soap


@router.patch("/api/transcripts/{transcript_id}/soap", response_model=SoapNoteOut)
def update_soap_note(
    transcript_id: int,
    payload: SoapNoteUpdateRequest,
    current_user=Depends(require_role("doctor")),
    db: Session = Depends(get_db),
) -> SoapNoteOut:
    _get_transcript_for_doctor(transcript_id, current_user, db)
    repo = PgRepository(db)
    soap = repo.get_soap_note_by_transcript(transcript_id)
    if soap is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "SOAP note isn't ready yet.")
    if soap.status == "finalized":
        raise HTTPException(status.HTTP_409_CONFLICT, "This SOAP note is already finalized and can't be edited.")

    updates = payload.model_dump(exclude_unset=True)
    return repo.update_soap_note(soap.id, **updates)


@router.post("/api/transcripts/{transcript_id}/finalize", response_model=SoapNoteOut)
def finalize_soap_note(
    transcript_id: int, current_user=Depends(require_role("doctor")), db: Session = Depends(get_db)
) -> SoapNoteOut:
    transcript = _get_transcript_for_doctor(transcript_id, current_user, db)
    repo = PgRepository(db)
    soap = repo.get_soap_note_by_transcript(transcript_id)
    if soap is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "SOAP note isn't ready yet.")
    if soap.status == "finalized":
        return soap

    combined_text = (
        f"SUBJECTIVE: {soap.subjective}\n\nOBJECTIVE: {soap.objective}\n\n"
        f"ASSESSMENT: {soap.assessment}\n\nPLAN: {soap.plan}"
    )
    entities = extract_entities(combined_text)

    pg_repo_report = repo.save_report(
        Report(
            patient_id=transcript.patient_id,
            filename=f"consultation_{transcript_id}.txt",
            raw_text=combined_text,
            entities_json=entities.model_dump_json(),
        ),
        uploaded_by=current_user.id,
        source_type="consultation_audio",
        transcript_id=transcript_id,
    )

    finalized = repo.update_soap_note(
        soap.id,
        status="finalized",
        finalized_by=current_user.id,
        finalized_at=datetime.now(UTC),
        linked_report_id=pg_repo_report.id,
        entities_json=entities.model_dump_json(),
    )
    return finalized
