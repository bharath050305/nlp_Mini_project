"""
backend/deps.py

FastAPI dependencies for authentication and RBAC. `require_patient_access`
is the single choke point every clinical-data endpoint routes through —
see the permission matrix in the plan doc / README for the exact rules:
patients see only their own record, doctors/nurses only assigned patients
(via an active `care_assignments` row), staff never resolves through here
at all (staff is an administrative role, not a clinical-data role).
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend import db_models
from backend.db import get_db
from backend.security import decode_access_token
from config import settings


def get_current_user(request: Request, db: Session = Depends(get_db)) -> db_models.User:
    token = request.cookies.get(settings.auth_cookie_name)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated.")
    try:
        payload = decode_access_token(token)
    except Exception as exc:  # AuthError from an invalid/expired token
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired or invalid.") from exc

    user_id = payload.get("sub")
    user = db.get(db_models.User, int(user_id)) if user_id else None
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Account not found or inactive.")
    return user


def require_role(*roles: str):
    """Dependency factory: 403 unless current_user.role is one of `roles`."""

    def _check(current_user: db_models.User = Depends(get_current_user)) -> db_models.User:
        if current_user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Requires role: {', '.join(roles)}.")
        return current_user

    return _check


def require_patient_access(
    patient_id: int,
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> db_models.Patient:
    """Dependency: FastAPI matches the `patient_id` parameter to the
    `{patient_id}` path segment of whatever route uses this. Resolves the
    Patient row iff the current user is allowed to see it, else 403/404.
    """
    patient = db.get(db_models.Patient, patient_id)
    if patient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found.")

    if current_user.role == "patient":
        if patient.user_id != current_user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your patient record.")
        return patient

    if current_user.role in ("doctor", "nurse"):
        assignment = (
            db.query(db_models.CareAssignment)
            .filter_by(
                patient_id=patient_id,
                staff_user_id=current_user.id,
                role_at_assignment=current_user.role,
                active=True,
            )
            .first()
        )
        if assignment is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not assigned to this patient.")
        return patient

    # staff never resolves through here — staff routers use require_role("staff") only
    raise HTTPException(status.HTTP_403_FORBIDDEN, "Staff cannot access clinical patient data directly.")
