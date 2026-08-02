"""
backend/routers/auth.py

Register/login/logout + /me. Public registration only ever creates a
`patient` account (with a linked `patients` row created in the same
request) — doctor/nurse/staff accounts are provisioned by an existing
staff user via POST /api/users (backend/routers/users.py).

Token transport is an httpOnly cookie, not a JSON body field — the React
app never touches the raw JWT (XSS resistance), it just relies on the
browser sending the cookie automatically on every request.
"""

from __future__ import annotations

from datetime import UTC

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.deps import get_current_user
from backend.pg_repository import PgRepository
from backend.schemas_api import LoginRequest, RegisterRequest, UserOut
from backend.security import create_access_token, hash_password, verify_password
from config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.env == "production",
        max_age=settings.jwt_expires_minutes * 60,
        path="/",
    )


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, response: Response, db: Session = Depends(get_db)) -> UserOut:
    repo = PgRepository(db)
    if repo.get_user_by_email(payload.email) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists.")

    user = repo.create_user(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role="patient",
    )
    repo.create_patient(name=payload.full_name, user_id=user.id, created_by=user.id)

    token = create_access_token(user.id, user.role)
    _set_auth_cookie(response, token)
    return user


@router.post("/login", response_model=UserOut)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> UserOut:
    from datetime import datetime

    repo = PgRepository(db)
    user = repo.get_user_by_email(payload.email)
    if user is None or not user.is_active or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password.")

    user.last_login_at = datetime.now(UTC)
    db.commit()

    token = create_access_token(user.id, user.role)
    _set_auth_cookie(response, token)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    response.delete_cookie(settings.auth_cookie_name, path="/")


@router.get("/me", response_model=UserOut)
def me(current_user=Depends(get_current_user)) -> UserOut:
    return current_user
