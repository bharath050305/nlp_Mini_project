import pytest
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
