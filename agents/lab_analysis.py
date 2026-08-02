"""
agents/lab_analysis.py

Reference-range lab-value analysis, extracted from
`agents/summarizer_agent.py` so the summarizer's abnormal-value flagging
and the doctor analytics dashboard (`backend/routers/analytics.py`, v4)
share one reference-range table instead of maintaining two independently.
"""

from __future__ import annotations

import re

from schemas import LabReading

# (regex to pull the number out of a LAB_VALUE string, low, high, unit label)
# Deliberately small and named-value based — a real system would key this
# off the LAB_TEST name too, but for a mini project a handful of the most
# common reference ranges is enough to make "abnormal value flagging"
# genuinely demonstrable rather than hand-waved.
_RANGE_CHECKS: list[tuple[re.Pattern, float, float, str]] = [
    (re.compile(r"(\d+(\.\d+)?)\s?%"), 4.0, 5.6, "HbA1c/percentage value"),
    (re.compile(r"(\d+(\.\d+)?)\s?mg/dl"), 70, 140, "mg/dL value"),
    (re.compile(r"(\d+(\.\d+)?)\s?mmhg"), 90, 120, "blood pressure value"),
    (re.compile(r"(\d+(\.\d+)?)\s?bpm"), 60, 100, "heart-rate value"),
]


def analyze_lab_values(lab_values: list[str]) -> list[LabReading]:
    """Match each raw lab-value string against the reference-range table,
    returning one `LabReading` per value that matches a known pattern.

    Values that don't match any known pattern are silently skipped —
    silence is safer than a guessed range (same principle as the
    original `_check_lab_values` this was extracted from).
    """
    readings: list[LabReading] = []
    for value in lab_values:
        for pattern, low, high, label in _RANGE_CHECKS:
            m = pattern.search(value.lower())
            if m:
                num = float(m.group(1))
                readings.append(
                    LabReading(
                        raw_value=value,
                        numeric_value=num,
                        label=label,
                        is_abnormal=num < low or num > high,
                        reference_range=f"{low}-{high}",
                    )
                )
                break
    return readings
