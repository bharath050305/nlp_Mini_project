"""
agents/lab_trend_agent.py

Lab Trajectory & Mathematical Trend Analyst Agent (v6).
Computes rates of change (ΔValue/Δt), trend direction, and detects critical
escalation/plummeting trajectories across time-series laboratory readings.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from schemas import LabReading, LabTrajectory, LabTrajectoryPoint
from utils.logger import get_logger

logger = get_logger(__name__)

# Patterns for extracting test name and units
_TEST_PATTERNS: list[tuple[re.Pattern, str, str, float, float]] = [
    # (regex_matcher, test_name, unit, critical_drop_rate, critical_spike_rate)
    (re.compile(r"(?:hba1c|percentage|%)", re.IGNORECASE), "HbA1c", "%", -1.0, 1.2),
    (re.compile(r"(?:glucose|sugar|fbs|rbs|mg/dl)", re.IGNORECASE), "Blood Glucose", "mg/dL", -40.0, 45.0),
    (re.compile(r"(?:bp|blood pressure|mmhg)", re.IGNORECASE), "Blood Pressure (Systolic)", "mmHg", -25.0, 30.0),
    (re.compile(r"(?:bpm|heart\s?rate|pulse)", re.IGNORECASE), "Heart Rate", "bpm", -20.0, 25.0),
    (re.compile(r"(?:hemoglobin|hb|hgb)", re.IGNORECASE), "Hemoglobin", "g/dL", -1.5, 2.0),
    (re.compile(r"(?:creatinine|cr)", re.IGNORECASE), "Serum Creatinine", "mg/dL", -0.5, 0.4),
]


def extract_test_identity(label_or_val: str) -> tuple[str, str, float, float]:
    for pattern, name, unit, crit_drop, crit_spike in _TEST_PATTERNS:
        if pattern.search(label_or_val):
            return name, unit, crit_drop, crit_spike
    return "General Clinical Reading", "", -100.0, 100.0


def analyze_trajectories(
    readings_by_report: Sequence[tuple[str, Sequence[LabReading]]],
) -> list[LabTrajectory]:
    """Given a sequence of (report_label, list_of_readings), reconstruct
    chronological trajectories for each distinct lab test and compute slope & alerts.
    """
    trajectories_map: dict[str, list[LabTrajectoryPoint]] = {}

    for report_date, readings in readings_by_report:
        for r in readings:
            test_name, unit, _, _ = extract_test_identity(r.label + " " + r.raw_value)
            if test_name not in trajectories_map:
                trajectories_map[test_name] = []

            trajectories_map[test_name].append(
                LabTrajectoryPoint(
                    test_name=test_name,
                    date_or_seq=report_date,
                    value=r.numeric_value,
                    unit=unit,
                    is_abnormal=r.is_abnormal,
                )
            )

    results: list[LabTrajectory] = []

    for test_name, points in trajectories_map.items():
        if not points:
            continue

        _, _, crit_drop, crit_spike = extract_test_identity(test_name)

        if len(points) == 1:
            results.append(
                LabTrajectory(
                    test_name=test_name,
                    readings=points,
                    slope_per_interval=0.0,
                    trend_direction="stable",
                    clinical_alert=None,
                )
            )
            continue

        # Compute average slope between successive readings
        deltas = [points[i].value - points[i - 1].value for i in range(1, len(points))]
        avg_slope = sum(deltas) / len(deltas)

        trend_dir = "stable"
        alert = None

        if avg_slope <= crit_drop:
            trend_dir = "critical_drop"
            alert = f"Critical downward trajectory detected in {test_name} (avg delta: {avg_slope:+.1f}). Urgent clinical review advised."
        elif avg_slope >= crit_spike:
            trend_dir = "critical_spike"
            alert = f"Critical escalating trajectory detected in {test_name} (avg delta: {avg_slope:+.1f}). Urgent glycemic/hemodynamic evaluation advised."
        elif avg_slope > 0.05 * points[0].value:
            trend_dir = "rising"
        elif avg_slope < -0.05 * points[0].value:
            trend_dir = "falling"

        results.append(
            LabTrajectory(
                test_name=test_name,
                readings=points,
                slope_per_interval=round(avg_slope, 2),
                trend_direction=trend_dir,
                clinical_alert=alert,
            )
        )

    return results
