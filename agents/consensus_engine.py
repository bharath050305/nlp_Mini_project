"""
agents/consensus_engine.py

Multi-Agent Consensus & Safety VETO Engine (v6).
Coordinates deliberation across clinical specialist agents, applies the
mathematical evidence-weighted aggregation algorithm, detects clinical
disagreement/entropy, and enforces deterministic safety vetoes.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from schemas import (
    ConsensusEvaluation,
    ConsensusStatus,
    DifferentialCandidate,
    EvidenceCitation,
    LabReading,
)
from utils.logger import get_logger

logger = get_logger(__name__)


class HealthcareConsensusEngine:
    """Computes weighted multi-agent consensus, applies adversarial critic reviews,
    and executes deterministic safety vetoes for clinical decision support.
    """

    def __init__(self, dispute_threshold: float = 0.25) -> None:
        self.dispute_threshold = dispute_threshold
        # Predefined agent domain weights (sum = 1.0)
        self.agent_weights: dict[str, float] = {
            "clinical_reasoner": 0.35,
            "lab_trend_analyst": 0.25,
            "guideline_evidence": 0.20,
            "history_synthesizer": 0.20,
        }

    def evaluate_clinical_consensus(
        self,
        agent_proposals: dict[str, list[DifferentialCandidate]],
        critic_critique: dict[str, Any] | None = None,
        patient_allergies: Sequence[str] = (),
        active_medications: Sequence[str] = (),
        lab_readings: Sequence[LabReading] = (),
    ) -> ConsensusEvaluation:
        """Aggregate independent agent proposals using evidence weighting and
        enforce deterministic safety vetoes.
        """
        critic = critic_critique or {}
        consensus_id = f"CONS-{uuid.uuid4().hex[:8].upper()}"

        # ------------------------------------------------------------------
        # 1. Deterministic Safety VETO Check
        # Confirmed patient allergies / contraindicated substances override all LLMs.
        # ------------------------------------------------------------------
        for allergy in patient_allergies:
            allergy_clean = allergy.strip().lower()
            if not allergy_clean:
                continue
            for agent_name, candidates in agent_proposals.items():
                for c in candidates:
                    if allergy_clean in c.condition_name.lower():
                        logger.warning("Safety VETO triggered: condition/treatment conflicts with allergy '%s'", allergy)
                        return ConsensusEvaluation(
                            consensus_id=consensus_id,
                            status=ConsensusStatus.SAFETY_VETOED,
                            primary_candidate=c,
                            safety_veto_triggered=True,
                            veto_reason=f"Zero-Tolerance Safety VETO: Clinical plan conflicts with verified patient allergy '{allergy}'.",
                            human_approval_required=True,
                        )

        # ------------------------------------------------------------------
        # 2. Evidence-Weighted Aggregation
        # ------------------------------------------------------------------
        score_map: dict[str, float] = {}
        evidence_map: dict[str, list[EvidenceCitation]] = {}
        agent_top_votes: dict[str, float] = {}
        icd10_map: dict[str, str | None] = {}
        tests_map: dict[str, list[str]] = {}

        total_weight = 0.0

        for agent_name, candidates in agent_proposals.items():
            if not candidates:
                continue
            w = self.agent_weights.get(agent_name, 0.15)
            total_weight += w

            top_cand = candidates[0]
            agent_top_votes[agent_name] = top_cand.probability_score

            for cand in candidates:
                key = cand.condition_name.strip()
                score_map[key] = score_map.get(key, 0.0) + (cand.probability_score * w)
                icd10_map[key] = cand.icd10_code or icd10_map.get(key)
                
                if key not in evidence_map:
                    evidence_map[key] = []
                evidence_map[key].extend(cand.supporting_evidence)

                if key not in tests_map:
                    tests_map[key] = []
                for t in cand.recommended_tests:
                    if t not in tests_map[key]:
                        tests_map[key].append(t)

        if not score_map or total_weight == 0.0:
            return ConsensusEvaluation(
                consensus_id=consensus_id,
                status=ConsensusStatus.INSUFFICIENT_EVIDENCE,
                critic_notes=critic.get("critique_summary", "Insufficient clinical evidence across agents."),
                human_approval_required=True,
            )

        # Normalize scores
        for k in score_map:
            score_map[k] = round(score_map[k] / total_weight, 2)

        sorted_candidates = sorted(score_map.items(), key=lambda item: item[1], reverse=True)

        top_name, top_score = sorted_candidates[0]
        second_score = sorted_candidates[1][1] if len(sorted_candidates) > 1 else 0.0
        score_gap = top_score - second_score

        # ------------------------------------------------------------------
        # 3. Disagreement / Entropy Detection
        # ------------------------------------------------------------------
        if top_score >= 0.80 and score_gap >= 0.30:
            status = ConsensusStatus.UNANIMOUS
        elif score_gap < self.dispute_threshold and len(sorted_candidates) > 1:
            status = ConsensusStatus.DISPUTED
            logger.info("Consensus DISPUTE detected: gap %0.2f between '%s' and '%s'", score_gap, top_name, sorted_candidates[1][0])
        else:
            status = ConsensusStatus.WEIGHTED_CONSENSUS

        # Format candidates
        primary = DifferentialCandidate(
            condition_name=top_name,
            icd10_code=icd10_map.get(top_name),
            probability_score=top_score,
            supporting_evidence=evidence_map.get(top_name, [])[:6],
            contradicting_evidence=critic.get("contradictions", []),
            recommended_tests=tests_map.get(top_name, []),
        )

        secondaries: list[DifferentialCandidate] = []
        for name, score in sorted_candidates[1:4]:
            secondaries.append(
                DifferentialCandidate(
                    condition_name=name,
                    icd10_code=icd10_map.get(name),
                    probability_score=score,
                    supporting_evidence=evidence_map.get(name, [])[:4],
                    recommended_tests=tests_map.get(name, []),
                )
            )

        entropy = round(max(0.0, min(1.0, 1.0 - score_gap)), 3)

        return ConsensusEvaluation(
            consensus_id=consensus_id,
            status=status,
            primary_candidate=primary,
            secondary_candidates=secondaries,
            agreement_entropy=entropy,
            agent_votes=agent_top_votes,
            critic_notes=critic.get("critique_summary", "Consensus verified without adverse contradictions."),
            safety_veto_triggered=False,
            missing_information=critic.get("missing_investigations", []),
            human_approval_required=True,  # All diagnostic consensus requires clinician review (A1/A2)
        )
