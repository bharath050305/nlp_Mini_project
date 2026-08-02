import fitz
import pytest
from PIL import Image, ImageDraw
from reportlab.pdfgen import canvas

from tools.pdf_reader import extract_text_from_pdf
from utils.exceptions import PDFProcessingError


def _make_pdf(path, lines):
    c = canvas.Canvas(str(path))
    text = c.beginText(50, 800)
    for line in lines:
        text.textLine(line)
    c.drawText(text)
    c.save()


def _make_image_only_pdf(path, lines):
    """Build a PDF with a page image (no text layer at all) — simulates a
    scanned report, the case OCR exists to handle."""
    img = Image.new("RGB", (900, 300), color="white")
    draw = ImageDraw.Draw(img)
    y = 20
    for line in lines:
        draw.text((20, y), line, fill="black")
        y += 40
    img_path = path.with_suffix(".png")
    img.save(img_path)

    doc = fitz.open()
    page = doc.new_page(width=900, height=300)
    page.insert_image(fitz.Rect(0, 0, 900, 300), filename=str(img_path))
    doc.save(path)
    doc.close()


def test_extract_text_from_pdf_happy_path(tmp_path):
    pdf_path = tmp_path / "report.pdf"
    _make_pdf(pdf_path, ["Patient has diabetes.", "HbA1c: 8.2%"])

    text = extract_text_from_pdf(pdf_path)
    assert "diabetes" in text
    assert "8.2%" in text


def test_extract_text_missing_file_raises(tmp_path):
    with pytest.raises(PDFProcessingError):
        extract_text_from_pdf(tmp_path / "does_not_exist.pdf")


def test_extract_text_empty_pdf_raises(tmp_path):
    pdf_path = tmp_path / "empty.pdf"
    c = canvas.Canvas(str(pdf_path))
    c.showPage()
    c.save()

    with pytest.raises(PDFProcessingError):
        extract_text_from_pdf(pdf_path)


def test_extract_text_oversized_raises(tmp_path, monkeypatch):
    import config

    pdf_path = tmp_path / "report.pdf"
    _make_pdf(pdf_path, ["Some text"])
    monkeypatch.setattr(config.settings, "max_pdf_size_mb", 0)

    with pytest.raises(PDFProcessingError):
        extract_text_from_pdf(pdf_path)


def test_scanned_pdf_falls_back_to_ocr(tmp_path):
    """A PDF with no text layer at all (a scanned report) should be
    readable via the OCR fallback — skipped if pytesseract/Tesseract
    aren't installed in this environment, since that's a system binary
    pip can't guarantee (see requirements-ocr.txt)."""
    pytest.importorskip("pytesseract")
    import shutil

    from config import settings

    if not settings.tesseract_cmd and not shutil.which("tesseract"):
        pytest.skip("Tesseract binary not found on PATH or TESSERACT_CMD")

    pdf_path = tmp_path / "scanned.pdf"
    _make_image_only_pdf(pdf_path, ["Diagnosis: Hypertension", "Medicine: Lisinopril"])

    text = extract_text_from_pdf(pdf_path)
    assert "Hypertension" in text or "hypertension" in text.lower()


def test_scanned_pdf_raises_when_ocr_disabled(tmp_path, monkeypatch):
    import config

    monkeypatch.setattr(config.settings, "ocr_enabled", False)
    pdf_path = tmp_path / "scanned.pdf"
    _make_image_only_pdf(pdf_path, ["Diagnosis: Hypertension"])

    with pytest.raises(PDFProcessingError, match="OCR is disabled"):
        extract_text_from_pdf(pdf_path)


def test_ocr_provider_raises_clear_error_when_pytesseract_missing(tmp_path, monkeypatch):
    """extract_text_via_ocr should fail with an install hint, not a bare
    ImportError, when pytesseract isn't installed."""
    import builtins

    from tools import ocr_provider

    pdf_path = tmp_path / "scanned.pdf"
    _make_image_only_pdf(pdf_path, ["Some scanned text"])

    real_import = builtins.__import__

    def _blocked_import(name, *args, **kwargs):
        if name == "pytesseract":
            raise ImportError("simulated missing dependency")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _blocked_import)

    with pytest.raises(PDFProcessingError, match="pytesseract"):
        ocr_provider.extract_text_via_ocr(pdf_path)
