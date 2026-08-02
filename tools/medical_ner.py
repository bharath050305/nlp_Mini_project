"""
tools/medical_ner.py

Medical Named Entity Recognition.

Uses stock spaCy (`en_core_web_sm`) for DATE detection and general
tokenization/sentence boundaries, plus a custom `EntityRuler` seeded from
curated vocabulary files in `data/medical_vocab/` for the domain-specific
labels (DISEASE, MEDICINE, SYMPTOM, LAB_TEST). Lab values and dosages
(e.g. "8.2%", "500mg") are caught with regex since they're numeric
patterns, not vocabulary.

Why not SciSpaCy: its models are large (400MB+), narrow (trained on very
specific corpora), and stock spaCy alone mislabels drug names as PERSON/ORG
— confirmed while building this. A curated `EntityRuler` is lighter,
100% deterministic, and every match is traceable to a vocab file, which is
much easier to defend in a viva than a black-box model's mistakes.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import spacy
from spacy.matcher import PhraseMatcher

from config import settings
from schemas import ExtractedEntities, MedicalEntity
from utils.exceptions import NERError
from utils.logger import get_logger

logger = get_logger(__name__)

VOCAB_DIR = Path(__file__).resolve().parent.parent / "data" / "medical_vocab"

_LAB_VALUE_PATTERN = re.compile(
    r"\b\d+(\.\d+)?\s?(%|mg/dl|mmol/l|g/dl|mg/l|iu/l|meq/l|bpm|mmhg|/ul)(?=\W|$)",
    re.IGNORECASE,
)
_DOSAGE_PATTERN = re.compile(
    r"\b\d+(\.\d+)?\s?(mg|mcg|ml|g|iu|units?)\b(\s(once|twice|thrice|daily|nightly|"
    r"morning|evening|night|bd|od|tds|qid))?",
    re.IGNORECASE,
)


def _load_vocab(filename: str) -> list[str]:
    path = VOCAB_DIR / filename
    if not path.exists():
        logger.warning("Vocab file missing: %s", path)
        return []
    with open(path, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


@lru_cache(maxsize=1)
def _get_pipeline():
    """Build (once, cached) the spaCy pipeline + PhraseMatcher for medical vocab.

    Loading spaCy's full model takes ~1s; caching means every call to
    `extract_entities` after the first is effectively instant.
    """
    try:
        nlp = spacy.load(settings.spacy_model)
    except OSError as exc:
        raise NERError(
            f"spaCy model '{settings.spacy_model}' is not installed. "
            f"Run: python -m spacy download {settings.spacy_model}"
        ) from exc

    vocab_map = {
        "DISEASE": _load_vocab("diseases.txt"),
        "MEDICINE": _load_vocab("medicines.txt"),
        "SYMPTOM": _load_vocab("symptoms.txt"),
        "LAB_TEST": _load_vocab("lab_tests.txt"),
    }

    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    for label, terms in vocab_map.items():
        patterns = [nlp.make_doc(term) for term in terms]
        if patterns:
            matcher.add(label, patterns)

    return nlp, matcher


def extract_entities(text: str) -> ExtractedEntities:
    """Run the full medical NER pipeline over report text.

    Returns:
        An `ExtractedEntities` with both the structured, deduplicated
        lists (for the UI/summary) and the raw span-level matches (for
        anything that needs character offsets, e.g. highlighting).
    """
    if not text or not text.strip():
        raise NERError("Cannot run NER on empty text.")

    nlp, matcher = _get_pipeline()
    doc = nlp(text)

    raw: list[MedicalEntity] = []
    buckets: dict[str, set[str]] = {
        "DISEASE": set(),
        "MEDICINE": set(),
        "SYMPTOM": set(),
        "LAB_TEST": set(),
        "LAB_VALUE": set(),
        "DOSAGE": set(),
        "DATE": set(),
    }

    # Vocabulary-based matches
    for match_id, start, end in matcher(doc):
        label = nlp.vocab.strings[match_id]
        span = doc[start:end]
        buckets[label].add(span.text)
        raw.append(
            MedicalEntity(
                text=span.text, label=label, start_char=span.start_char, end_char=span.end_char
            )
        )

    # spaCy's built-in NER, kept only for DATE (everything else it tags
    # in a general-purpose way that doesn't match our clinical labels)
    for ent in doc.ents:
        if ent.label_ == "DATE":
            buckets["DATE"].add(ent.text)
            raw.append(
                MedicalEntity(
                    text=ent.text, label="DATE", start_char=ent.start_char, end_char=ent.end_char
                )
            )

    # Regex-based numeric patterns
    for m in _LAB_VALUE_PATTERN.finditer(text):
        buckets["LAB_VALUE"].add(m.group().strip())
        raw.append(
            MedicalEntity(text=m.group().strip(), label="LAB_VALUE", start_char=m.start(), end_char=m.end())
        )
    for m in _DOSAGE_PATTERN.finditer(text):
        buckets["DOSAGE"].add(m.group().strip())
        raw.append(
            MedicalEntity(text=m.group().strip(), label="DOSAGE", start_char=m.start(), end_char=m.end())
        )

    result = ExtractedEntities(
        diseases=sorted(buckets["DISEASE"]),
        medicines=sorted(buckets["MEDICINE"]),
        symptoms=sorted(buckets["SYMPTOM"]),
        lab_tests=sorted(buckets["LAB_TEST"]),
        lab_values=sorted(buckets["LAB_VALUE"]),
        dosages=sorted(buckets["DOSAGE"]),
        dates=sorted(buckets["DATE"]),
        raw_entities=raw,
    )
    logger.info(
        "NER found %d diseases, %d medicines, %d lab tests, %d lab values",
        len(result.diseases), len(result.medicines), len(result.lab_tests), len(result.lab_values),
    )
    return result
