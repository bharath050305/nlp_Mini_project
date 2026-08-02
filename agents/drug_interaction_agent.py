"""
agents/drug_interaction_agent.py

Drug Interaction Agent — new in this build, not present in the original
project. Cross-checks the set of medicines the system knows about (from
NER on the uploaded report, plus anything the user has saved as a
reminder) against a small curated reference table
(`data/medical_vocab/drug_interactions.json`) of well-established,
textbook-level interaction pairs.

Scope, stated plainly: this is a bounded, curated reference (under 20
pairs), not a connection to a real drug-interaction database or a
substitute for a pharmacist. It is intentionally conservative — it only
ever flags a *known* pair from the table and always routes to "confirm
with your pharmacist/doctor" rather than telling the patient what to do
about it. That is also why this task is classified R2 (clinical decision
support) in `agents/governance.py` even though its autonomy stays A0
(suggest-only): the risk tier reflects potential consequence, not how the
agent behaves.
"""

from __future__ import annotations

import json
from functools import lru_cache
from itertools import combinations
from pathlib import Path

from schemas import DrugInteractionWarning
from utils.logger import get_logger

logger = get_logger(__name__)

_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "medical_vocab" / "drug_interactions.json"


@lru_cache(maxsize=1)
def _load_table() -> dict[frozenset[str], tuple[str, str]]:
    """Load the curated pairs into a {frozenset({a, b}): (severity, note)} map."""
    with open(_DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)
    table: dict[frozenset[str], tuple[str, str]] = {}
    for pair in data.get("pairs", []):
        key = frozenset({pair["a"].lower(), pair["b"].lower()})
        table[key] = (pair["severity"], pair["note"])
    return table


def check_interactions(medicine_names: list[str]) -> list[DrugInteractionWarning]:
    """Check every pair among `medicine_names` against the curated table.

    Matching is case-insensitive substring-aware: a NER hit like "Metformin
    500mg" still matches the table's "metformin" entry.
    """
    table = _load_table()
    normalized = sorted({name.lower().strip() for name in medicine_names if name.strip()})
    warnings: list[DrugInteractionWarning] = []

    for name_a, name_b in combinations(normalized, 2):
        for key, (severity, note) in table.items():
            drug_a, drug_b = tuple(key)
            names_match = (drug_a in name_a and drug_b in name_b) or (drug_b in name_a and drug_a in name_b)
            if names_match:
                warnings.append(
                    DrugInteractionWarning(drug_a=name_a, drug_b=name_b, severity=severity, note=note)
                )

    logger.info("Checked %d medicine(s) for interactions, found %d warning(s)", len(normalized), len(warnings))
    return warnings
