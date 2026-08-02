"""
backend/main.py

FastAPI application entry point: `uvicorn backend.main:app --reload`.
Wires every router together and configures CORS for the React dev server
(settings.cors_allowed_origins). The scheduler runs in a separate process
(`python -m backend.worker`) — see that module's docstring for why.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from backend.db import engine
from backend.rate_limit import limiter
from backend.routers import (
    analytics,
    assignments,
    auth,
    chat,
    interactions,
    notifications,
    patients,
    reminders,
    reports,
    transcripts,
    users,
)
from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # The one config mistake that must never reach production silently:
    # config.py only warns about an insecure default JWT secret (so tests
    # and local sqlite/CLI usage don't crash on it) — the API server that
    # actually serves real users hard-fails instead.
    if settings.env == "production" and settings.jwt_secret_key == "dev-only-insecure-change-me":
        raise RuntimeError(
            "Refusing to start in production with the default insecure JWT_SECRET_KEY. "
            "Set a real random secret in .env before running the API server in production."
        )

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection OK (%s)", settings.database_url.split("@")[-1])
    except Exception:
        logger.exception("Database connection failed at startup — check DATABASE_URL in .env")
    yield


app = FastAPI(title="MediAgent API", version="4.0.0", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (
    auth.router,
    users.router,
    patients.router,
    assignments.router,
    reports.router,
    chat.router,
    interactions.router,
    reminders.router,
    notifications.router,
    transcripts.router,
    analytics.router,
):
    app.include_router(router)


@app.get("/api/health")
def health() -> dict:
    """Live liveness check — actually queries the DB on every call rather
    than only at startup, so a DB outage after boot is reflected here."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Database unreachable") from exc
    return {"status": "ok"}
