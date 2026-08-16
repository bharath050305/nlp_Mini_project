"""
agents/differential_agent.py

Independent Clinical Reasoning & Differential Diagnosis Agent (v6).
Generates an independent, evidence-grounded differential diagnosis list from
extracted clinical entities (symptoms, diseases, lab values), patient history,
and user query.

This agent adheres to the "Independent Reasoning" principle: it reasons over
unstructured symptoms and clinical observations *before* any deliberation with
other agents, preventing conversational anchoring or premature convergence.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from schemas import (
    DifferentialCandidate,
    EvidenceCitation,
    ExtractedEntities,
    LabReading,
)
from utils.logger import get_logger

logger = get_logger(__name__)

# Clinical pattern repository: maps symptom/finding combinations to candidate diagnoses,
# ICD-10 codes, base confidence, and required confirmatory tests.
_CLINICAL_PROFILES: list[dict] = [
    {
        "condition": "Community-Acquired Pneumonia",
        "icd10": "J13",
        "keywords": {"fever", "cough", "sputum", "chills", "chest pain", "crackles", "shortness of breath", "dyspnea"},
        "lab_markers": {"wbc", "crp", "procalcitonin", "temp"},
        "base_prob": 0.82,
        "recommended_tests": ["Chest X-ray (PA/Lateral)", "Complete Blood Count (CBC)", "Sputum Culture"],
    },
    {
        "condition": "Pulmonary Embolism",
        "icd10": "I26.9",
        "keywords": {"chest pain", "shortness of breath", "dyspnea", "tachycardia", "hemoptysis", "leg pain", "swelling"},
        "lab_markers": {"d-dimer", "troponin"},
        "base_prob": 0.70,
        "recommended_tests": ["D-Dimer Assay", "CT Pulmonary Angiography (CTPA)", "Lower Extremity Venous Duplex"],
    },
    {
        "condition": "Acute Coronary Syndrome / Myocardial Infarction",
        "icd10": "I21.9",
        "keywords": {"chest pain", "chest tightness", "angina", "radiating pain", "diaphoresis", "sweating", "nausea", "dyspnea"},
        "lab_markers": {"troponin", "ck-mb", "ecg", "bp"},
        "base_prob": 0.85,
        "recommended_tests": ["12-Lead ECG", "High-Sensitivity Troponin I/T", "Echocardiogram"],
    },
    {
        "condition": "Type 2 Diabetes Mellitus",
        "icd10": "E11.9",
        "keywords": {"polydipsia", "polyuria", "frequent urination", "thirst", "fatigue", "blurred vision", "weight loss", "hba1c"},
        "lab_markers": {"hba1c", "glucose", "fbs", "rbs"},
        "base_prob": 0.88,
        "recommended_tests": ["Fasting Plasma Glucose", "HbA1c Confirmation", "Urinary Albumin-to-Creatinine Ratio"],
    },
    {
        "condition": "Essential Hypertension",
        "icd10": "I10",
        "keywords": {"high blood pressure", "hypertension", "headache", "dizziness", "palpitations", "blurred vision", "bp"},
        "lab_markers": {"bp", "creatinine", "lipid"},
        "base_prob": 0.80,
        "recommended_tests": ["24-Hour Ambulatory BP Monitoring", "Serum Creatinine & eGFR", "Lipid Panel", "ECG"],
    },
    {
        "condition": "Iron Deficiency Anemia",
        "icd10": "D50.9",
        "keywords": {"fatigue", "weakness", "pallor", "pale", "dizziness", "brittle nails", "shortness of breath", "hemoglobin"},
        "lab_markers": {"hemoglobin", "ferritin", "iron", "mcv"},
        "base_prob": 0.80,
        "recommended_tests": ["Complete Blood Count (CBC)", "Serum Ferritin & Total Iron Binding Capacity", "Peripheral Blood Smear"],
    },
    {
        "condition": "Bronchial Asthma Exacerbation",
        "icd10": "J45.901",
        "keywords": {"wheezing", "cough", "shortness of breath", "dyspnea", "chest tightness", "night cough"},
        "lab_markers": {"peak flow", "ige", "eosinophil"},
        "base_prob": 0.78,
        "recommended_tests": ["Spirometry / Peak Expiratory Flow Rate", "Fractional Exhaled Nitric Oxide (FeNO)", "Chest Radiograph"],
    },
    {
        "condition": "Acute Gastroesophageal Reflux Disease (GERD)",
        "icd10": "K21.9",
        "keywords": {"heartburn", "acid reflux", "chest burning", "regurgitation", "dysphagia", "epigastric pain"},
        "lab_markers": set(),
        "base_prob": 0.65,
        "recommended_tests": ["Upper GI Endoscopy", "Esophageal pH Monitoring"],
    },
]


def _normalize(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9\s]", " ", text).lower()


def generate_differential(
    entities: ExtractedEntities | None,
    user_text: str = "",
    lab_readings: Sequence[LabReading] = (),
    report_text: str = "",
) -> list[DifferentialCandidate]:
    """Analyze symptoms, diseases, lab readings, and raw text to produce a ranked
    list of differential diagnosis candidates with explicit evidence grounding.
    """
    all_symptoms: set[str] = set()
    all_diseases: set[str] = set()

    if entities:
        for s in entities.symptoms:
            all_symptoms.update(_normalize(s).split())
        for d in entities.diseases:
            all_diseases.update(_normalize(d).split())

    # Include terms from user query and lab readings
    user_norm = _normalize(user_text)
    user_tokens = set(user_norm.split())
    combined_tokens = all_symptoms | all_diseases | user_tokens

    candidates: list[DifferentialCandidate] = []

    for profile in _CLINICAL_PROFILES:
        matched_keywords: list[str] = []
        for kw in profile["keywords"]:
            kw_norm = _normalize(kw)
            if kw_norm in user_norm or any(kw_norm in _normalize(s) for s in (entities.symptoms if entities else [])) or any(part in combined_tokens for part in kw_norm.split() if len(part) >= 4):
                matched_keywords.append(kw)

        # Check relevant abnormal lab readings
        matched_labs: list[str] = []
        for r in lab_readings:
            r_norm = _normalize(r.label + " " + r.raw_value)
            if any(marker in r_norm for marker in profile["lab_markers"]):
                if r.is_abnormal:
                    matched_labs.append(f"{r.raw_value} (abnormal, ref: {r.reference_range})")

        total_matches = len(matched_keywords) + len(matched_labs)
        if total_matches == 0:
            continue

        # Compute calculated support probability based on evidence strength
        evidence_ratio = min(1.0, total_matches / max(2, len(profile["keywords"]) // 2))
        prob = round(min(0.95, profile["base_prob"] * (0.7 + 0.3 * evidence_ratio)), 2)

        # Build formal evidence citations
        citations: list[EvidenceCitation] = []
        for kw in matched_keywords[:4]:
            citations.append(
                EvidenceCitation(
                    source_type="symptom_observation",
                    resource_id="OBS-SYM",
                    snippet=f"Documented symptom/finding: '{kw}'",
                    confidence_score=0.9,
                )
            )
        for lab_desc in matched_labs:
            citations.append(
                EvidenceCitation(
                    source_type="lab_observation",
                    resource_id="OBS-LAB",
                    snippet=f"Abnormal diagnostic marker: {lab_desc}",
                    confidence_score=0.95,
                )
            )

        candidates.append(
            DifferentialCandidate(
                condition_name=profile["condition"],
                icd10_code=profile["icd10"],
                probability_score=prob,
                supporting_evidence=citations,
                contradicting_evidence=[],
                recommended_tests=profile["recommended_tests"],
            )
        )

    # Sort descending by probability score
    candidates.sort(key=lambda c: c.probability_score, reverse=True)
    return candidates
