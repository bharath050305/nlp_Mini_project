"""
prompts.py

Prompt templates used by the Summarizer and QA agents.

Each template embeds its inputs behind fixed, ALL-CAPS markers
(REPORT_EXCERPT:, DISEASES:, CONTEXT:, QUESTION:, etc). This isn't just
cosmetic — the mock LLM provider (`llm/mock_provider.py`) parses these
exact markers back out with regex to do its rule-based generation, so the
*same* template drives a real GPT/Claude call and the offline fallback.
Keep the markers in sync if you edit these.
"""

from __future__ import annotations

SUMMARIZER_SYSTEM_PROMPT = (
    "You are a careful medical-report summarizer. Write for a patient with "
    "no medical background: plain English, no jargon, no diagnosis, no "
    "treatment instructions — only what the report itself says. Always "
    "close by recommending they discuss findings with their doctor."
)


def build_summarizer_prompt(
    report_excerpt: str,
    diseases: list[str],
    medicines: list[str],
    symptoms: list[str],
    lab_values: list[str],
    abnormal_values: list[str],
) -> str:
    return (
        f"REPORT_EXCERPT:\n{report_excerpt}\n\n"
        f"DISEASES: {', '.join(diseases) or 'none detected'}\n"
        f"MEDICINES: {', '.join(medicines) or 'none detected'}\n"
        f"SYMPTOMS: {', '.join(symptoms) or 'none detected'}\n"
        f"LAB_VALUES: {', '.join(lab_values) or 'none detected'}\n"
        f"ABNORMAL_VALUES: {', '.join(abnormal_values) or 'none flagged'}\n\n"
        "TASK: Write a 3-4 sentence plain-English patient summary covering "
        "the diseases/medicines/symptoms above, then list 2-4 short, "
        "general recommendations (e.g. 'discuss X with your doctor'). "
        "Do not invent facts not present above."
    )


QA_SYSTEM_PROMPT = (
    "You are a medical-report question-answering agent. Answer ONLY using "
    "the CONTEXT provided below, which was retrieved from the patient's own "
    "report. If the context doesn't contain the answer, say so plainly — "
    "never guess or use outside medical knowledge for specific values."
)


def build_qa_prompt(context_chunks: list[str], question: str) -> str:
    context = "\n---\n".join(context_chunks)
    return f"CONTEXT:\n{context}\n\nQUESTION: {question}\n\nTASK: Answer the question using only the CONTEXT above."
