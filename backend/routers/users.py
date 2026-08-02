"""
backend/routers/users.py

Staff-only account management: create doctor/nurse/staff/patient accounts,
list users (for building care-assignment pickers in the React admin UI).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.deps import require_role
from backend.pg_repository import PgRepository
from backend.schemas_api import Role, UserCreateRequest, UserOut
from backend.security import hash_password

router = APIRouter(prefix="/api/users", tags=["users"], dependencies=[Depends(require_role("staff"))])


@router.get("", response_model=list[UserOut])
def list_users(role: Role | None = None, db: Session = Depends(get_db)) -> list[UserOut]:
    return PgRepository(db).list_users(role=role)


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreateRequest, db: Session = Depends(get_db)) -> UserOut:
    repo = PgRepository(db)
    if repo.get_user_by_email(payload.email) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists.")

    user = repo.create_user(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
    )
    if payload.role == "patient":
        repo.create_patient(name=payload.full_name, user_id=user.id)
    return user
