"""
utils/exceptions.py

Custom exception hierarchy for MediAgent.

Every agent/tool raises one of these instead of a bare Exception so that
`app.py` / `cli.py` can catch a single `MediAgentError` at the top level
and show the user a clean message, while still being able to branch on
the specific subtype when useful (e.g. show a "re-upload PDF" hint only
for `PDFProcessingError`).
"""

from __future__ import annotations


class MediAgentError(Exception):
    """Base class for every error raised by MediAgent's own code."""


class PDFProcessingError(MediAgentError):
    """Raised when a PDF can't be opened, is empty, or exceeds size limits."""


class NERError(MediAgentError):
    """Raised when medical entity extraction fails (e.g. spaCy model missing)."""


class VectorStoreError(MediAgentError):
    """Raised when chunking, indexing, or retrieval over a report fails."""


class LLMProviderError(MediAgentError):
    """Raised when the configured LLM provider fails (bad/missing key, API error)."""


class PlannerError(MediAgentError):
    """Raised when the planner cannot decompose a user request into tasks."""


class DatabaseError(MediAgentError):
    """Raised on any SQLite read/write failure."""


class ReportGenerationError(MediAgentError):
    """Raised when the final PDF report fails to build."""
