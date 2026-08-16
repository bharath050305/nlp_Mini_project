"""
tests/test_consensus_engine.py

Tests for the Multi-Agent Consensus & Safety VETO Engine.
"""

from __future__ import annotations

from agents.consensus_engine import HealthcareConsensusEngine
from schemas import (
    ConsensusStatus,
    DifferentialCandidate,
    EvidenceCitation,
)


def _make_candidate(name: str, prob: float, source: str = "symptom_observation") -> DifferentialCandidate:
    return DifferentialCandidate(
        condition_name=name,
        probability_score=prob,
        supporting_evidence=[
            EvidenceCitation(
                source_type=source,
                resource_id="OBS-1",
                snippet=f"Documented finding for {name}",
                confidence_score=0.9,
            )
        ],
        recommended_tests=["Test A", "Test B"],
    )


def test_unanimous_consensus_when_strong_agreement():
    engine = HealthcareConsensusEngine(dispute_threshold=0.25)
    proposals = {
        "clinical_reasoner": [_make_candidate("Community-Acquired Pneumonia", 0.90), _make_candidate("Bronchitis", 0.30)],
        "lab_trend_analyst": [_make_candidate("Community-Acquired Pneumonia", 0.85), _make_candidate("Bronchitis", 0.25)],
        "guideline_evidence": [_make_candidate("Community-Acquired Pneumonia", 0.88)],
    }
    critic = {"critique_summary": "No adverse conflicts identified.", "contradictions": [], "missing_investigations": []}

    result = engine.evaluate_clinical_consensus(proposals, critic_critique=critic)

    assert result.status == ConsensusStatus.UNANIMOUS
    assert result.primary_candidate is not None
    assert result.primary_candidate.condition_name == "Community-Acquired Pneumonia"
    assert result.primary_candidate.probability_score >= 0.85
    assert not result.safety_veto_triggered


def test_disputed_consensus_when_agents_diverge():
    engine = HealthcareConsensusEngine(dispute_threshold=0.25)
    # Clinical reasoner leans PE, Lab Analyst leans Pneumonia with close scores
    proposals = {
        "clinical_reasoner": [_make_candidate("Pulmonary Embolism", 0.75), _make_candidate("Pneumonia", 0.70)],
        "lab_trend_analyst": [_make_candidate("Pneumonia", 0.74), _make_candidate("Pulmonary Embolism", 0.72)],
        "guideline_evidence": [_make_candidate("Pulmonary Embolism", 0.70), _make_candidate("Pneumonia", 0.70)],
    }
    critic = {
        "critique_summary": "Divergence between PE and Pneumonia.",
        "contradictions": ["PE cannot be ruled out without CTPA"],
        "missing_investigations": ["D-Dimer Assay / CTPA"],
    }

    result = engine.evaluate_clinical_consensus(proposals, critic_critique=critic)

    assert result.status == ConsensusStatus.DISPUTED
    assert result.agreement_entropy > 0.70  # High entropy indicates high disagreement
    assert len(result.missing_information) > 0


def test_deterministic_safety_veto_overrides_consensus():
    engine = HealthcareConsensusEngine()
    proposals = {
        "clinical_reasoner": [_make_candidate("Penicillin Allergy Rash", 0.85)],
        "guideline_evidence": [_make_candidate("Penicillin Allergy Rash", 0.80)],
    }

    result = engine.evaluate_clinical_consensus(
        proposals,
        patient_allergies=["penicillin"],
    )

    assert result.status == ConsensusStatus.SAFETY_VETOED
    assert result.safety_veto_triggered is True
    assert "penicillin" in result.veto_reason.lower()
    assert result.human_approval_required is True


def test_insufficient_evidence_when_proposals_empty():
    engine = HealthcareConsensusEngine()
    result = engine.evaluate_clinical_consensus({})
    assert result.status == ConsensusStatus.INSUFFICIENT_EVIDENCE
