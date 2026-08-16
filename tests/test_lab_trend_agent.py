"""
tests/test_lab_trend_agent.py

Tests for Lab Trajectory & Trend Analyst Agent.
"""

from __future__ import annotations

from agents.lab_trend_agent import analyze_trajectories
from schemas import LabReading


def test_trajectory_detects_critical_hemoglobin_drop():
    # Sequence of dropping hemoglobin: 12.0 -> 9.5 -> 7.0 (delta = -2.5 each, drop threshold = -1.5)
    r1 = [LabReading(raw_value="12.0 g/dL", numeric_value=12.0, label="hemoglobin value", is_abnormal=False, reference_range="12-16")]
    r2 = [LabReading(raw_value="9.5 g/dL", numeric_value=9.5, label="hemoglobin value", is_abnormal=True, reference_range="12-16")]
    r3 = [LabReading(raw_value="7.0 g/dL", numeric_value=7.0, label="hemoglobin value", is_abnormal=True, reference_range="12-16")]

    readings_by_report = [
        ("2026-01-01", r1),
        ("2026-02-01", r2),
        ("2026-03-01", r3),
    ]

    trajectories = analyze_trajectories(readings_by_report)
    assert len(trajectories) == 1
    hb_traj = trajectories[0]
    assert hb_traj.test_name == "Hemoglobin"
    assert hb_traj.trend_direction == "critical_drop"
    assert hb_traj.slope_per_interval < -2.0
    assert hb_traj.clinical_alert is not None
    assert "critical downward trajectory" in hb_traj.clinical_alert.lower()


def test_trajectory_detects_critical_glucose_spike():
    # Sequence of rising glucose: 100 -> 160 -> 230 (delta = +65)
    r1 = [LabReading(raw_value="100 mg/dL", numeric_value=100.0, label="mg/dL value", is_abnormal=False, reference_range="70-140")]
    r2 = [LabReading(raw_value="160 mg/dL", numeric_value=160.0, label="mg/dL value", is_abnormal=True, reference_range="70-140")]
    r3 = [LabReading(raw_value="230 mg/dL", numeric_value=230.0, label="mg/dL value", is_abnormal=True, reference_range="70-140")]

    readings_by_report = [
        ("Report 1", r1),
        ("Report 2", r2),
        ("Report 3", r3),
    ]

    trajectories = analyze_trajectories(readings_by_report)
    assert len(trajectories) == 1
    glu_traj = trajectories[0]
    assert glu_traj.trend_direction == "critical_spike"
    assert glu_traj.slope_per_interval >= 50.0
    assert glu_traj.clinical_alert is not None


def test_single_reading_is_stable():
    r1 = [LabReading(raw_value="5.4 %", numeric_value=5.4, label="HbA1c/percentage value", is_abnormal=False, reference_range="4.0-5.6")]
    trajectories = analyze_trajectories([("Report 1", r1)])
    assert len(trajectories) == 1
    assert trajectories[0].trend_direction == "stable"
    assert trajectories[0].slope_per_interval == 0.0
    assert trajectories[0].clinical_alert is None
