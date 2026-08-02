"""
backend/services/stt_service.py

Orchestrates one transcript's status transitions:
uploaded -> transcribing -> transcribed -> structuring -> draft_ready | failed

Runs as a FastAPI `BackgroundTask` (see backend/routers/transcripts.py),
so it opens its own DB session rather than reusing the request's (which
is closed by the time this runs).
"""

from __future__ import annotations

from agents.transcript_agent import structure_soap_note
from backend.db import SessionLocal
from backend.pg_repository import PgRepository
from tools.speech_to_text import get_stt_provider
from utils.exceptions import MediAgentError
from utils.logger import get_logger

logger = get_logger(__name__)


def process_transcript(transcript_id: int) -> None:
    db = SessionLocal()
    try:
        repo = PgRepository(db)
        transcript = repo.get_transcript(transcript_id)
        if transcript is None:
            logger.error("process_transcript: transcript %s not found", transcript_id)
            return

        try:
            repo.update_transcript(transcript_id, status="transcribing")
            text = get_stt_provider().transcribe(transcript.audio_path)
            repo.update_transcript(transcript_id, raw_transcript_text=text, status="transcribed")

            repo.update_transcript(transcript_id, status="structuring")
            note = structure_soap_note(text)
            soap = repo.create_soap_note(
                transcript_id=transcript_id,
                patient_id=transcript.patient_id,
                doctor_id=transcript.doctor_id,
                subjective=note.subjective,
                objective=note.objective,
                assessment=note.assessment,
                plan=note.plan,
            )
            repo.update_transcript(transcript_id, status="draft_ready")
            logger.info("Transcript %s -> draft SOAP note %s ready for review", transcript_id, soap.id)
        except MediAgentError as exc:
            logger.warning("Transcript %s processing failed: %s", transcript_id, exc)
            repo.update_transcript(transcript_id, status="failed", error_detail=str(exc))
    finally:
        db.close()
