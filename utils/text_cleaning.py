"""
utils/text_cleaning.py

Text-cleaning helpers shared by the PDF reader, NER, and vector store.
Kept dependency-free (pure `re`/`str`) so they're trivial to unit test.
"""

from __future__ import annotations

import re

_MULTI_SPACE = re.compile(r"[ \t]+")
_MULTI_NEWLINE = re.compile(r"\n{3,}")
_HYPHEN_LINEBREAK = re.compile(r"(\w)-\n(\w)")
_PAGE_ARTIFACT = re.compile(r"^\s*(page\s*\d+(\s*of\s*\d+)?|\d+)\s*$", re.IGNORECASE)


def clean_extracted_text(raw_text: str) -> str:
    """Normalize whitespace/line-break artifacts left by PDF text extraction.

    - Rejoins words split by a hyphen at a line break ("glu-\ncose" -> "glucose")
    - Collapses runs of spaces/tabs and of 3+ blank lines
    - Drops standalone page-number lines ("Page 3 of 10", "12")
    - Strips leading/trailing whitespace
    """
    if not raw_text:
        return ""

    text = _HYPHEN_LINEBREAK.sub(r"\1\2", raw_text)
    lines = [ln for ln in text.split("\n") if not _PAGE_ARTIFACT.match(ln)]
    text = "\n".join(lines)
    text = _MULTI_SPACE.sub(" ", text)
    text = _MULTI_NEWLINE.sub("\n\n", text)
    return text.strip()


def split_sentences(text: str) -> list[str]:
    """Lightweight sentence splitter used as a fallback when spaCy isn't needed.

    Splits on '.', '!', '?' followed by whitespace + a capital letter/digit,
    while trying not to break on common clinical abbreviations.
    """
    if not text:
        return []

    abbrev_guard = re.sub(
        r"\b(Dr|Mr|Mrs|Ms|vs|etc|approx|no|mg|ml|kg)\.\s",
        r"\1<DOT> ",
        text,
        flags=re.IGNORECASE,
    )
    raw_sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", abbrev_guard)
    return [s.replace("<DOT>", ".").strip() for s in raw_sentences if s.strip()]


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    """Split text into overlapping word-count chunks for retrieval.

    Chunking (rather than indexing whole pages) keeps each vector-store
    entry focused enough that TF-IDF similarity actually discriminates
    between, say, the "medications" section and the "lab values" section.
    """
    words = text.split()
    if not words:
        return []
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be greater than overlap")

    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunks.append(" ".join(words[start:end]))
        if end >= len(words):
            break
        start = end - overlap
    return chunks
