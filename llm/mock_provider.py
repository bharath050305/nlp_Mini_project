"""
llm/mock_provider.py

Default, fully offline "LLM" provider. No API key, no internet, no
download — this is what makes MediAgent runnable during a viva with no
wifi (see `config.py` and README).

It isn't a language model at all: it's rule-based/extractive logic that
parses the ALL-CAPS markers written by `prompts.py` and produces
templated but genuinely report-specific output — a real summary of *this*
report's entities, a real extractive answer from *this* report's
retrieved chunks. Swapping to `openai`/`anthropic` in `.env` replaces this
with an actual model call using the exact same prompts.
"""

from __future__ import annotations

import re

from llm.base import LLMProvider
from utils.logger import get_logger

logger = get_logger(__name__)

_SECTION = re.compile(r"^([A-Z_]+):\s?(.*)$", re.MULTILINE)

# Small curated dictionary so canned explanations still feel "smart" for
# the handful of terms every sample blood report contains — used as a
# fallback when the question-answering path is really an explanation
# request ("what is HbA1c").
_TERM_EXPLANATIONS = {
    "hba1c": "HbA1c measures your average blood sugar level over the past 2-3 months.",
    "ldl": "LDL ('bad') cholesterol can build up in artery walls; lower is generally better.",
    "hdl": "HDL ('good') cholesterol helps clear excess cholesterol from the blood; higher is generally better.",
    "creatinine": "Creatinine is a waste product filtered by the kidneys; high levels can suggest reduced kidney function.",
    "tsh": "TSH is a hormone that tells your thyroid how much thyroid hormone to make.",
    "esr": "ESR is a general marker of inflammation somewhere in the body.",
    "crp": "CRP is a marker that rises when there's inflammation or infection in the body.",
    "egfr": "eGFR estimates how well your kidneys are filtering blood; lower values suggest reduced kidney function.",
}


def _parse_sections(prompt: str) -> dict[str, str]:
    """Pull out the ALL-CAPS `KEY: value` markers written by prompts.py."""
    sections: dict[str, str] = {}
    matches = list(_SECTION.finditer(prompt))
    for i, m in enumerate(matches):
        key = m.group(1)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(prompt)
        sections[key] = prompt[start:end].strip() if not m.group(2) else (m.group(2) + "\n" + prompt[start:end]).strip()
    return sections


class MockLLMProvider(LLMProvider):
    @property
    def name(self) -> str:
        return "mock"

    def complete(self, system_prompt: str, user_prompt: str, max_tokens: int = 500) -> str:
        sections = _parse_sections(user_prompt)

        if "REPORT_EXCERPT" in sections and "DISEASES" in sections:
            return self._summarize(sections)
        if "CONTEXT" in sections and "QUESTION" in sections:
            return self._answer(sections)
        if "TRANSCRIPT" in sections and "DISEASES_MENTIONED" in sections:
            return self._structure_soap(sections)

        # Generic fallback: no recognized markers, just echo a safe stub.
        logger.warning("MockLLMProvider received an unrecognized prompt shape; returning stub.")
        return "I don't have enough information to respond to that."

    # -- task-specific rule-based generation --------------------------------
    def _summarize(self, s: dict[str, str]) -> str:
        diseases = self._list(s.get("DISEASES", ""))
        medicines = self._list(s.get("MEDICINES", ""))
        symptoms = self._list(s.get("SYMPTOMS", ""))
        abnormal = self._list(s.get("ABNORMAL_VALUES", ""))

        parts = []
        if diseases:
            parts.append(f"Your report references {self._join(diseases)}.")
        if medicines:
            parts.append(f"It lists {self._join(medicines)} as current medication(s).")
        if symptoms:
            parts.append(f"Reported symptoms include {self._join(symptoms)}.")
        if abnormal:
            parts.append(
                f"{self._join(abnormal).capitalize()} fall outside the typical reference range "
                "and are worth discussing with your doctor."
            )
        if not parts:
            parts.append(
                "No specific diseases, medicines, or abnormal values were confidently "
                "detected in this report — it may be a general check-up or a report "
                "format the entity extractor doesn't recognize well."
            )
        summary = " ".join(parts)

        recs = ["Recommendations:"]
        if abnormal:
            recs.append(f"- Discuss {self._join(abnormal)} with your doctor at your next visit.")
        if medicines:
            recs.append("- Continue medications as prescribed; don't adjust dosage without medical advice.")
        recs.append("- Bring this report to your next appointment for a full clinical interpretation.")
        recs.append("- This summary is informational only and is not a diagnosis.")

        return summary + "\n\n" + "\n".join(recs)

    def _answer(self, s: dict[str, str]) -> str:
        question = s.get("QUESTION", "").strip()
        context = s.get("CONTEXT", "")
        history_block = s.get("RECENT_CONVERSATION", "")

        # "what is X" / "explain X" -> canned term dictionary first
        m = re.match(r"(what\s+is|explain)\s+(.*)", question.strip(), re.IGNORECASE)
        if m:
            term = m.group(2).strip(" ?").lower()
            for key, explanation in _TERM_EXPLANATIONS.items():
                if key in term:
                    return explanation

        chunks = [c.strip() for c in context.split("---") if c.strip()]
        if not chunks:
            return "The report doesn't contain enough information to answer that."

        # Extractive answer: the sentence (within the retrieved chunks)
        # with the most keyword overlap with the question.
        q_words = {w.lower() for w in re.findall(r"[a-zA-Z0-9.]+", question) if len(w) > 2}
        best_sentence, best_score = self._best_matching_sentence(chunks, q_words)

        # Follow-up fallback: a topic-less question ("what about that?")
        # has no keywords of its own to match on — broaden the pool with
        # the recent conversation's words before giving up.
        if best_score <= 0 and history_block:
            history_words = {w.lower() for w in re.findall(r"[a-zA-Z0-9.]+", history_block) if len(w) > 2}
            best_sentence, best_score = self._best_matching_sentence(chunks, q_words | history_words)

        if best_score <= 0 or not best_sentence:
            return (
                "I couldn't find a specific answer to that in the report. "
                "Try rephrasing, or ask about a value that appears in the document."
            )
        return best_sentence

    @staticmethod
    def _best_matching_sentence(chunks: list[str], keywords: set[str]) -> tuple[str, int]:
        best_sentence, best_score = "", -1
        for chunk in chunks:
            for sentence in re.split(r"(?<=[.!?])\s+", chunk):
                words = {w.lower() for w in re.findall(r"[a-zA-Z0-9.]+", sentence)}
                score = len(keywords & words)
                if score > best_score and sentence.strip():
                    best_score, best_sentence = score, sentence.strip()
        return best_sentence, best_score

    def _structure_soap(self, s: dict[str, str]) -> str:
        """Rule-based SOAP structuring: no real language understanding, so
        this deliberately stays close to what was actually mentioned
        (diseases/medicines/symptoms already extracted by NER) rather than
        attempting to paraphrase the transcript — same "don't invent facts"
        principle as `_summarize`."""
        transcript = s.get("TRANSCRIPT", "").strip()
        diseases = self._list(s.get("DISEASES_MENTIONED", ""))
        medicines = self._list(s.get("MEDICINES_MENTIONED", ""))
        symptoms = self._list(s.get("SYMPTOMS_MENTIONED", ""))

        subjective = f"Patient reported: {self._join(symptoms)}." if symptoms else "Not discussed."
        objective = (
            f"Consultation transcript on file ({len(transcript)} characters); "
            "no structured vitals were extracted from the transcript text."
            if transcript
            else "Not discussed."
        )
        assessment = f"Condition(s) discussed: {self._join(diseases)}." if diseases else "Not discussed."
        plan = (
            f"Medication(s) discussed: {self._join(medicines)}. Follow up as advised during the visit."
            if medicines
            else "Not discussed."
        )

        return (
            f"SUBJECTIVE: {subjective}\n"
            f"OBJECTIVE: {objective}\n"
            f"ASSESSMENT: {assessment}\n"
            f"PLAN: {plan}"
        )

    @staticmethod
    def _list(raw: str) -> list[str]:
        raw = raw.strip()
        if not raw or raw.lower() in {"none detected", "none flagged"}:
            return []
        return [x.strip() for x in raw.split(",") if x.strip()]

    @staticmethod
    def _join(items: list[str]) -> str:
        if len(items) == 1:
            return items[0]
        return ", ".join(items[:-1]) + f" and {items[-1]}"
