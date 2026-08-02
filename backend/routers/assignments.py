"""
backend/routers/assignments.py

Staff-only care-assignment management: link a doctor or nurse to a
patient (or unlink them). This is the table `require_patient_access`
checks against for every clinical-data endpoint.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.deps import require_role
from backend.pg_repository import PgRepository
from backend.schemas_api import AssignmentCreateRequest, AssignmentOut

router = APIRouter(prefix="/api/assignments", tags=["assignments"], dependencies=[Depends(require_role("staff"))])


@router.get("", response_model=list[AssignmentOut])
def list_assignments(patient_id: int, db: Session = Depends(get_db)) -> list[AssignmentOut]:
    return PgRepository(db).list_assignments_for_patient(patient_id)


@router.post("", response_model=AssignmentOut, status_code=status.HTTP_201_CREATED)
def create_assignment(
    payload: AssignmentCreateRequest,
    current_user=Depends(require_role("staff")),
    db: Session = Depends(get_db),
) -> AssignmentOut:
    repo = PgRepository(db)
    if repo.get_patient(payload.patient_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found.")
    staff_member = repo.get_user(payload.staff_user_id)
    if staff_member is None or staff_member.role != payload.role_at_assignment:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"staff_user_id must belong to an account with role={payload.role_at_assignment}.",
        )
    return repo.create_assignment(
        patient_id=payload.patient_id,
        staff_user_id=payload.staff_user_id,
        role_at_assignment=payload.role_at_assignment,
        assigned_by=current_user.id,
    )


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assignment(assignment_id: int, db: Session = Depends(get_db)) -> None:
    if not PgRepository(db).deactivate_assignment(assignment_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Assignment not found.")
