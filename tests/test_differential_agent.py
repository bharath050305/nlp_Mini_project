"""
tests/test_differential_agent.py

Tests for Independent Differential Diagnosis Agent.
"""

from __future__ import annotations

from agents.differential_agent import generate_differential
from schemas import ExtractedEntities, LabReading


def test_differential_identifies_pneumonia_from_symptoms():
    entities = ExtractedEntities(
        symptoms=["fever", "cough", "sputum"],
        diseases=[],
        medicines=[],
        lab_tests=[],
        lab_values=[],
    )

    candidates = generate_differential(entities, user_text="Patient has productive cough and fever")
    assert len(candidates) > 0
    top = candidates[0]
    assert "Pneumonia" in top.condition_name
    assert top.probability_score > 0.70
    assert top.icd10_code == "J13"
    assert len(top.supporting_evidence) > 0
    assert any("fever" in ev.snippet.lower() or "cough" in ev.snippet.lower() for ev in top.supporting_evidence)


def test_differential_identifies_acute_coronary_syndrome_from_chest_pain():
    entities = ExtractedEntities(
        symptoms=["chest pain", "shortness of breath", "sweating"],
        diseases=[],
        medicines=[],
        lab_tests=[],
        lab_values=[],
    )

    candidates = generate_differential(entities, user_text="Severe crushing chest pain radiating to jaw")
    assert len(candidates) > 0
    condition_names = [c.condition_name for c in candidates]
    assert any("Coronary" in name or "Myocardial" in name for name in condition_names)


def test_differential_incorporates_abnormal_lab_values():
    entities = ExtractedEntities(
        symptoms=["thirst", "frequent urination"],
        diseases=[],
        medicines=[],
        lab_tests=["HbA1c"],
        lab_values=["8.5%"],
    )
    readings = [
        LabReading(
            raw_value="8.5%",
            numeric_value=8.5,
            label="HbA1c/percentage value",
            is_abnormal=True,
            reference_range="4.0-5.6",
        )
    ]

    candidates = generate_differential(entities, user_text="High sugar reading", lab_readings=readings)
    assert len(candidates) > 0
    top = candidates[0]
    assert "Diabetes" in top.condition_name
    assert top.probability_score >= 0.80
    assert any("abnormal" in ev.snippet.lower() for ev in top.supporting_evidence)
