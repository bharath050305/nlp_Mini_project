"""
tools/ocr_provider.py

OCR fallback for scanned/image-only PDFs — Tesseract via `pytesseract`,
a thin Python wrapper around a system `tesseract` binary (the same
"thin wrapper + system binary" pattern as `tools/whisper_local_provider.py`
+ ffmpeg). Only ever invoked by `tools/pdf_reader.py` when the normal
text-layer extraction finds nothing to extract.
"""

from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF — already a dependency, used here to rasterize pages

from config import settings
from utils.exceptions import PDFProcessingError
from utils.logger import get_logger
from utils.text_cleaning import clean_extracted_text

logger = get_logger(__name__)

# Common install locations on Windows when tesseract.exe isn't on PATH
# (e.g. the UB-Mannheim installer's default location) — checked only if
# settings.tesseract_cmd isn't explicitly set and PATH lookup fails.
_COMMON_WINDOWS_PATHS = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
)


def _configure_tesseract_cmd(pytesseract) -> None:
    if settings.tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd
        return
    import shutil

    if shutil.which("tesseract"):
        return  # already resolvable on PATH, nothing to configure
    for candidate in _COMMON_WINDOWS_PATHS:
        if Path(candidate).exists():
            pytesseract.pytesseract.tesseract_cmd = candidate
            return


def extract_text_via_ocr(pdf_path: str | Path) -> str:
    """Rasterize every page of `pdf_path` and run Tesseract OCR over each.

    Raises:
        PDFProcessingError: if `pytesseract` isn't installed, the
            Tesseract binary can't be found, or OCR finds no text either
            (a genuinely blank/corrupt scan).
    """
    try:
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        raise PDFProcessingError(
            "OCR fallback needs the 'pytesseract' and 'Pillow' packages. Run: "
            "pip install -r requirements-ocr.txt (also requires the system "
            "Tesseract binary — see that file)."
        ) from exc

    _configure_tesseract_cmd(pytesseract)

    path = Path(pdf_path)
    try:
        doc = fitz.open(path)
    except Exception as exc:
        raise PDFProcessingError(f"Could not open PDF for OCR (is it corrupted?): {exc}") from exc

    try:
        page_texts = []
        for page in doc:
            # 2x zoom noticeably improves OCR accuracy on typical scan
            # resolutions without being slow enough to matter here.
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            try:
                page_texts.append(pytesseract.image_to_string(image))
            except pytesseract.TesseractNotFoundError as exc:
                raise PDFProcessingError(
                    "The Tesseract binary wasn't found. Install it (e.g. the "
                    "UB-Mannheim build on Windows) and set TESSERACT_CMD in "
                    ".env if it isn't on your system PATH."
                ) from exc
    finally:
        doc.close()

    raw_text = "\n".join(page_texts)
    cleaned = clean_extracted_text(raw_text)
    if not cleaned:
        raise PDFProcessingError("OCR ran but found no readable text — the scan may be blank or too low quality.")

    logger.info("OCR extracted %d chars from %s (%d page(s))", len(cleaned), path.name, len(page_texts))
    return cleaned
