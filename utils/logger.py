"""
utils/logger.py

Centralized logging for MediAgent.

Call `get_logger(__name__)` from any module. Configuration (level, file
location) is read once from `config.settings` so behaviour is consistent
everywhere and controlled entirely by `.env`.
"""

from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler

from config import settings

_CONFIGURED = False


class _JsonFormatter(logging.Formatter):
    """One JSON object per line — for production, where logs are piped
    into a real aggregator rather than read directly off a terminal.
    Not a general-purpose structured-logging library: just enough fields
    (timestamp, level, logger name, message, exception) to be useful."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def _configure_root() -> None:
    """Attach a console handler and a rotating file handler to the root logger.

    Idempotent — safe to call from every module's import time via
    `get_logger` without creating duplicate handlers.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    root = logging.getLogger()
    root.setLevel(settings.log_level.upper())

    fmt: logging.Formatter
    if settings.log_format == "json":
        fmt = _JsonFormatter()
    else:
        fmt = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)

    log_file = settings.logs_dir / "mediagent.log"
    file_handler = RotatingFileHandler(
        log_file, maxBytes=2_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a module-scoped logger, configuring root handlers on first use."""
    _configure_root()
    return logging.getLogger(name)
