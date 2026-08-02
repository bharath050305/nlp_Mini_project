"""
backend/main.py

FastAPI application entry point: `uvicorn backend.main:app --reload`.
Wires every router together and configures CORS for the React dev server
(settings.cors_allowed_origin). The scheduler runs in a separate process
(`python -m backend.worker`) — see that module's docstring for why.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from backend.db import engine
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
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection OK (%s)", settings.database_url.split("@")[-1])
    except Exception:
        logger.exception("Database connection failed at startup — check DATABASE_URL in .env")
    yield


app = FastAPI(title="MediAgent API", version="3.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.cors_allowed_origin],
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
    return {"status": "ok"}
