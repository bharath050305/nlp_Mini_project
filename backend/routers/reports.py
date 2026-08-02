"""
backend/routers/reports.py

Report upload + list/detail + clinical timeline ("previous conditions"),
scoped via `require_patient_access` — patients see their own, doctors and
nurses see it for their assigned patients, staff never reaches this router.

Upload reuses the exact same `extract_text_from_bytes` -> `Orchestrator
.load_report` path the old Streamlit UI used, so report ingestion
behaves identically to before.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from agents.orchestrator import Orchestrator
from agents.timeline_agent import build_timeline
from backend import db_models
from backend.db import get_db
from backend.deps import require_patient_access
from backend.pg_repository import PgRepository
from backend.schemas_api import ReportDetailOut, ReportOut
from backend.services.embedding_service import embed_and_store_report
from schemas import TimelineEvent
from tools.pdf_reader import extract_text_from_bytes
from utils.exceptions import MediAgentError

router = APIRouter(prefix="/api/patients/{patient_id}", tags=["reports"])


@router.post("/reports/upload", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
async def upload_report(
    file: UploadFile,
    patient=Depends(require_patient_access),
    db: Session = Depends(get_db),
) -> ReportOut:
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only PDF files are supported.")

    data = await file.read()
    try:
        text = extract_text_from_bytes(data, file.filename)
    except MediAgentError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    repo = PgRepository(db)
    orch = Orchestrator(repo, patient.id)
    orch.load_report(text, file.filename)

    latest = repo.get_latest_report(patient.id)
    embed_and_store_report(repo, latest.id, text)

    return ReportOut(
        id=latest.id,
        patient_id=latest.patient_id,
        filename=latest.filename,
        source_type="upload",
        created_at=latest.created_at,
    )


@router.get("/reports", response_model=list[ReportOut])
def list_reports(patient=Depends(require_patient_access), db: Session = Depends(get_db)) -> list[ReportOut]:
    return db.query(db_models.Report).filter_by(patient_id=patient.id).order_by(db_models.Report.id).all()


@router.get("/reports/{report_id}", response_model=ReportDetailOut)
def get_report(
    report_id: int, patient=Depends(require_patient_access), db: Session = Depends(get_db)
) -> ReportDetailOut:
    row = db.get(db_models.Report, report_id)
    if row is None or row.patient_id != patient.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found.")
    return row


@router.get("/timeline", response_model=list[TimelineEvent])
def get_timeline(patient=Depends(require_patient_access), db: Session = Depends(get_db)) -> list[TimelineEvent]:
    """Chronological view across every report on file for this patient —
    what a doctor/nurse uses to see previous conditions at a glance."""
    repo = PgRepository(db)
    return build_timeline(repo, patient.id)
