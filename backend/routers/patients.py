"""
backend/routers/patients.py

Patient roster + demographic detail, scoped by role:
- staff: full roster (names/DOB/phone only — no clinical data here)
- doctor/nurse: only their assigned patients
- patient: only their own linked record, via GET /api/patients/me
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.deps import get_current_user, require_patient_access, require_role
from backend.pg_repository import PgRepository
from backend.schemas_api import PatientCreateRequest, PatientOut

router = APIRouter(prefix="/api/patients", tags=["patients"])


@router.get("", response_model=list[PatientOut])
def list_patients(current_user=Depends(get_current_user), db: Session = Depends(get_db)) -> list[PatientOut]:
    repo = PgRepository(db)
    if current_user.role == "staff":
        return repo.list_all_patients()
    if current_user.role in ("doctor", "nurse"):
        return repo.list_patients_for_provider(current_user.id, current_user.role)
    raise HTTPException(status.HTTP_403_FORBIDDEN, "Patients should use GET /api/patients/me instead.")


@router.get("/me", response_model=PatientOut)
def get_my_patient_record(current_user=Depends(require_role("patient")), db: Session = Depends(get_db)) -> PatientOut:
    repo = PgRepository(db)
    patient = repo.get_patient_by_user_id(current_user.id)
    if patient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No patient record linked to this account.")
    return patient


@router.post("", response_model=PatientOut, status_code=status.HTTP_201_CREATED)
def create_patient(
    payload: PatientCreateRequest,
    current_user=Depends(require_role("staff")),
    db: Session = Depends(get_db),
) -> PatientOut:
    """Chart a new patient without a login (e.g. a walk-in clinic record)."""
    repo = PgRepository(db)
    return repo.create_patient(
        name=payload.name,
        date_of_birth=payload.date_of_birth,
        phone=payload.phone,
        created_by=current_user.id,
    )


@router.get("/{patient_id}", response_model=PatientOut)
def get_patient(patient=Depends(require_patient_access)) -> PatientOut:
    return patient
