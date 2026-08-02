from agents.governance import GOVERNANCE_TABLE, get_governance, oversight_note
from schemas import AutonomyLevel, RiskTier, TaskType


def test_every_task_type_is_governed():
    """Every TaskType the planner can emit must have a governance entry —
    nothing should ship ungoverned."""
    for task_type in TaskType:
        assert task_type in GOVERNANCE_TABLE


def test_no_task_is_classified_fully_autonomous():
    """The survey found no fully-autonomous (A3) healthcare agent
    deployments in the reviewed literature; this build shouldn't claim
    A3 for anything either."""
    for autonomy, _risk in GOVERNANCE_TABLE.values():
        assert autonomy != "A3"


def test_check_interactions_is_higher_risk_than_summarize():
    """Drug interactions carry more potential consequence than a plain
    summary, even though both are suggest-only (A0)."""
    interaction_autonomy, interaction_risk = get_governance(TaskType.CHECK_INTERACTIONS)
    summarize_autonomy, summarize_risk = get_governance(TaskType.SUMMARIZE)
    assert interaction_autonomy == AutonomyLevel.A0_SUGGEST_ONLY
    assert summarize_autonomy == AutonomyLevel.A0_SUGGEST_ONLY
    assert interaction_risk == RiskTier.R2_CLINICAL_DECISION_SUPPORT
    assert summarize_risk == RiskTier.R1_PATIENT_INFORMATIONAL


def test_set_reminder_is_gated_execution():
    autonomy, _risk = get_governance(TaskType.SET_REMINDER)
    assert autonomy == AutonomyLevel.A2_EXECUTE_WITH_GATES


def test_oversight_note_defined_for_every_used_autonomy_level():
    used_levels = {autonomy for autonomy, _risk in GOVERNANCE_TABLE.values()}
    for level in used_levels:
        assert oversight_note(level)  # non-empty string, doesn't raise
