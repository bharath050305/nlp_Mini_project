"""
tools/pdf_reader.py

PDF text extraction using PyMuPDF (`fitz`). Handles the error cases the
master prompt calls out explicitly: invalid/corrupt PDFs, empty PDFs,
and oversized files.
"""

from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF

from config import settings
from utils.exceptions import PDFProcessingError
from utils.logger import get_logger
from utils.text_cleaning import clean_extracted_text

logger = get_logger(__name__)


def extract_text_from_pdf(file_path: str | Path) -> str:
    """Extract and clean all text from a PDF file.

    Raises:
        PDFProcessingError: if the file is missing, too large, unreadable,
            or contains no extractable text (e.g. a pure image scan with
            no OCR layer).
    """
    path = Path(file_path)
    if not path.exists():
        raise PDFProcessingError(f"File not found: {path}")

    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb > settings.max_pdf_size_mb:
        raise PDFProcessingError(
            f"PDF is {size_mb:.1f} MB, which exceeds the "
            f"{settings.max_pdf_size_mb} MB limit."
        )

    try:
        doc = fitz.open(path)
    except Exception as exc:  # PyMuPDF raises various low-level errors
        raise PDFProcessingError(f"Could not open PDF (is it corrupted?): {exc}") from exc

    try:
        if doc.page_count == 0:
            raise PDFProcessingError("PDF has zero pages.")

        page_count = doc.page_count
        pages_text = [page.get_text("text") for page in doc]
    finally:
        doc.close()

    raw_text = "\n".join(pages_text)
    cleaned = clean_extracted_text(raw_text)

    if not cleaned:
        raise PDFProcessingError(
            "No extractable text found. This looks like a scanned image "
            "PDF with no text layer — OCR is out of scope for this build."
        )

    logger.info("Extracted %d chars of text from %s (%d pages)", len(cleaned), path.name, page_count)
    return cleaned


def extract_text_from_bytes(data: bytes, filename: str = "upload.pdf") -> str:
    """Same as `extract_text_from_pdf` but for in-memory bytes (Streamlit uploads).

    Writes to a temp file under `settings.upload_dir` so the same
    extraction path (and its error handling) is reused, and so the raw
    upload is retained for the demo/viva if needed.
    """
    dest = settings.upload_dir / filename
    dest.write_bytes(data)
    return extract_text_from_pdf(dest)
