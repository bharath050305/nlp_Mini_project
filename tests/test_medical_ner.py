import pytest

from tools.medical_ner import extract_entities
from utils.exceptions import NERError

SAMPLE_TEXT = (
    "Patient diagnosed with Type 2 Diabetes and Hypertension. "
    "Reports fatigue and headache. HbA1c: 8.2%. Blood Pressure: 150 mmhg. "
    "Prescribed Metformin 500mg twice daily."
)


def test_extract_entities_finds_diseases():
    result = extract_entities(SAMPLE_TEXT)
    assert any("diabetes" in d.lower() for d in result.diseases)
    assert any("hypertension" in d.lower() for d in result.diseases)


def test_extract_entities_finds_medicines():
    result = extract_entities(SAMPLE_TEXT)
    assert any("metformin" in m.lower() for m in result.medicines)


def test_extract_entities_finds_symptoms():
    result = extract_entities(SAMPLE_TEXT)
    assert any("fatigue" in s.lower() for s in result.symptoms)


def test_extract_entities_finds_lab_values():
    result = extract_entities(SAMPLE_TEXT)
    assert any("8.2%" in v for v in result.lab_values)


def test_extract_entities_finds_dosage():
    result = extract_entities(SAMPLE_TEXT)
    assert any("500mg" in d.lower() for d in result.dosages)


def test_extract_entities_empty_text_raises():
    with pytest.raises(NERError):
        extract_entities("")
