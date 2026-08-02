"""
backend/routers/interactions.py

Standalone drug-interaction check endpoint (the same
`agents/drug_interaction_agent.py` the chat CHECK_INTERACTIONS task uses,
exposed directly so the React UI can show it without going through chat).
Checks medicines from the patient's latest report entities plus anything
saved as a reminder.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from agents.drug_interaction_agent import check_interactions
from backend.db import get_db
from backend.deps import require_patient_access
from backend.pg_repository import PgRepository
from schemas import DrugInteractionWarning
from tools.medical_ner import extract_entities

router = APIRouter(prefix="/api/patients/{patient_id}/interactions", tags=["interactions"])


@router.get("", response_model=list[DrugInteractionWarning])
def get_interactions(patient=Depends(require_patient_access), db: Session = Depends(get_db)) -> list[DrugInteractionWarning]:
    repo = PgRepository(db)
    medicine_names: list[str] = []

    latest = repo.get_latest_report(patient.id)
    if latest is not None:
        entities = extract_entities(latest.raw_text)
        medicine_names.extend(entities.medicines)

    medicine_names.extend(r.medicine_name for r in repo.list_reminders(patient.id))
    if not medicine_names:
        return []
    return check_interactions(medicine_names)
