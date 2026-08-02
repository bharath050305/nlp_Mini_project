"""
config.py

Central configuration for MediAgent.

All runtime settings are declared here as a single typed, validated
`Settings` object (pydantic-settings) and loaded from environment
variables / a local `.env` file. Nothing else in the codebase should read
`os.environ` directly — import `settings` from this module instead, so
there is exactly one source of truth for configuration.
"""

import logging
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    """Typed application settings, populated from `.env` (see `.env.example`)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # -- LLM provider -------------------------------------------------------
    # "mock" needs no API key and no internet access — it's the default so
    # the app always runs, e.g. during a viva or placement demo with no wifi.
    llm_provider: Literal["mock", "openai", "anthropic"] = "mock"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-6"

    # -- App behaviour --------------------------------------------------------
    debug: bool = False
    log_level: str = "INFO"

    # -- NLP --------------------------------------------------------------------
    spacy_model: str = "en_core_web_sm"
    max_pdf_size_mb: int = 15

    # -- OCR fallback for scanned/image-only PDFs (v4) --------------------------
    # Tesseract via pytesseract — a thin wrapper + a system Tesseract binary,
    # the same pattern as ffmpeg-for-Whisper. Only invoked when the normal
    # text-layer extraction finds nothing.
    ocr_enabled: bool = True
    tesseract_cmd: str | None = None  # override if tesseract.exe isn't on PATH

    # -- Filesystem paths -----------------------------------------------------
    database_path: Path = BASE_DIR / "database" / "mediagent.db"
    upload_dir: Path = BASE_DIR / "uploads"
    reports_dir: Path = BASE_DIR / "reports"
    data_dir: Path = BASE_DIR / "data"
    logs_dir: Path = BASE_DIR / "logs"

    # -- Deployment environment -------------------------------------------------
    # Drives cookie Secure flag and whether an insecure default JWT secret
    # is merely warned about (dev) or should be treated as a hard error by
    # ops tooling (production).
    env: Literal["development", "production"] = "development"

    # -- Backend API / Postgres (v3) --------------------------------------------
    # The FastAPI backend + React frontend replace the old single-process
    # Streamlit UI. Postgres is required for multi-user/RBAC; the legacy
    # SQLite `Repository` (tools/database.py) is kept, unmodified, for the
    # offline `cli.py --mode sqlite` fallback only.
    database_url: str = "postgresql+psycopg2://mediagent:mediagent@localhost:5432/mediagent"
    cors_allowed_origin: str = "http://localhost:5173"

    # -- Auth (JWT via httpOnly cookie) -----------------------------------------
    # NOTE: the default secret below is intentionally insecure so the app
    # still boots with zero setup; a warning is logged at import time if
    # it's still in use outside development (see bottom of this file).
    jwt_secret_key: str = "dev-only-insecure-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 720
    auth_cookie_name: str = "mediagent_session"

    # -- Email notifications (v3) ------------------------------------------------
    # Mirrors the llm_provider pattern: "mock" (default) just logs the
    # email instead of sending it, so a fresh install still runs offline
    # with no SMTP credentials configured.
    email_provider: Literal["mock", "smtp"] = "mock"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_address: str = "noreply@mediagent.local"
    smtp_use_tls: bool = True

    # -- Speech-to-text (transcript-to-report agent, v3) ------------------------
    # "whisper_local" (default) uses the pip `openai-whisper` package —
    # no API key needed, but pulls in torch and requires a system ffmpeg
    # binary. "openai_whisper_api" reuses openai_api_key above instead.
    stt_provider: Literal["whisper_local", "openai_whisper_api"] = "whisper_local"
    whisper_model_size: str = "base"

    # -- Semantic search / embeddings (v4) ---------------------------------------
    # "disabled" (default) — TF-IDF only, zero setup, matching this
    # project's usual offline-first-by-default pattern. "sentence_transformers"
    # downloads a small local embedding model once (~80MB), no API key,
    # augments (not replaces) TF-IDF retrieval with semantic matches — see
    # docs/RAG.md. "openai" reuses openai_api_key instead of a local model.
    embedding_provider: Literal["disabled", "sentence_transformers", "openai"] = "disabled"
    embedding_model_name: str = "all-MiniLM-L6-v2"

    def ensure_directories(self) -> None:
        """Create any runtime directories that don't exist yet.

        Called once at import time below. Also handy to call directly in
        tests after overriding paths to a temp directory.
        """
        for directory in (
            self.upload_dir,
            self.reports_dir,
            self.data_dir,
            self.logs_dir,
            self.database_path.parent,
        ):
            directory.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_directories()

if settings.env != "development" and settings.jwt_secret_key == "dev-only-insecure-change-me":
    logging.getLogger("mediagent.config").warning(
        "jwt_secret_key is still the insecure development default outside "
        "a development environment — set JWT_SECRET_KEY in .env before "
        "deploying anywhere real users can reach this."
    )
