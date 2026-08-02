"""
config.py

Central configuration for MediAgent.

All runtime settings are declared here as a single typed, validated
`Settings` object (pydantic-settings) and loaded from environment
variables / a local `.env` file. Nothing else in the codebase should read
`os.environ` directly — import `settings` from this module instead, so
there is exactly one source of truth for configuration.
"""

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

    # -- Filesystem paths -----------------------------------------------------
    database_path: Path = BASE_DIR / "database" / "mediagent.db"
    upload_dir: Path = BASE_DIR / "uploads"
    reports_dir: Path = BASE_DIR / "reports"
    data_dir: Path = BASE_DIR / "data"
    logs_dir: Path = BASE_DIR / "logs"

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
