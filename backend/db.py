"""
backend/db.py

SQLAlchemy engine/session setup for the Postgres-backed API. Separate from
`tools/database.py` (the legacy SQLite `Repository`, kept unmodified for
`cli.py --mode sqlite`) — this is the v3 multi-user persistence layer.
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    """Declarative base for every ORM model in `backend/db_models.py`."""


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one DB session per request, always closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
