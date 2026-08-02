import pytest

from agents.orchestrator import Orchestrator
from schemas import AgentStepStatus
from tools.database import Database, Repository

SAMPLE_REPORT = (
    "Diagnosis: Type 2 Diabetes, Hypertension. "
    "Symptoms: fatigue, headache. "
    "Lab Results: HbA1c 8.2%, Blood Pressure 150 mmhg. "
    "Current Medications: Metformin 500mg twice daily."
)


@pytest.fixture
def orchestrator(tmp_path):
    repo = Repository(db=Database(db_path=tmp_path / "test.db"))
    patient = repo.get_or_create_default_patient()
    orch = Orchestrator(repo, patient.id)
    orch.load_report(SAMPLE_REPORT, "sample.pdf")
    return orch


def test_summarize_request_produces_summary(orchestrator):
    result = orchestrator.handle_request("Summarize my report and flag abnormal values")
    assert result.summary is not None
    assert result.entities is not None
    assert all(step.status == AgentStepStatus.DONE for step in result.execution_log)


def test_question_answering_flow(orchestrator):
    result = orchestrator.handle_request("What is my HbA1c?")
    assert len(result.qa_results) == 1
    assert result.qa_results[0].answer


def test_reminder_then_list_flow(orchestrator):
    orchestrator.handle_request("Remind me to take Metformin every morning")
    result = orchestrator.handle_request("Show my reminders")
    assert len(result.reminders) == 1
    assert result.reminders[0].medicine_name.lower() == "metformin"


def test_generate_report_flow(orchestrator):
    orchestrator.handle_request("Summarize my report")
    result = orchestrator.handle_request("Generate a downloadable doctor report")
    assert result.report_file_path is not None
    from pathlib import Path

    assert Path(result.report_file_path).exists()


def test_question_without_report_fails_gracefully(tmp_path):
    repo = Repository(db=Database(db_path=tmp_path / "test2.db"))
    patient = repo.get_or_create_default_patient()
    orch = Orchestrator(repo, patient.id)  # no report loaded
    result = orch.handle_request("What is my HbA1c?")
    assert any(step.status == AgentStepStatus.FAILED for step in result.execution_log)


def test_session_rehydrates_from_db_after_simulated_restart(tmp_path):
    """Regression test for the reported bug: a report uploaded in one
    Orchestrator instance must still be there for a brand-new Orchestrator
    instance against the same patient/database — simulating a server
    restart, redeploy, or a new browser session reusing the same backend.
    """
    db = Database(db_path=tmp_path / "test.db")
    repo = Repository(db=db)
    patient = repo.get_or_create_default_patient()

    first = Orchestrator(repo, patient.id)
    first.load_report(SAMPLE_REPORT, "sample.pdf")

    second = Orchestrator(repo, patient.id)  # brand new instance, no load_report call
    assert second.session.has_report is True
    assert second.session.report_filename == "sample.pdf"

    result = second.handle_request("Summarize my report")
    assert all(step.status != AgentStepStatus.FAILED for step in result.execution_log)


def test_reminder_gate_does_not_save_low_confidence_extraction(orchestrator):
    result = orchestrator.handle_request("remind me every morning")  # no parseable medicine name
    assert result.reminders == []
    assert any(step.status == AgentStepStatus.SKIPPED for step in result.execution_log)


def test_interaction_check_flags_known_pair(orchestrator):
    orchestrator.handle_request("Summarize my report")  # populates entities (Metformin)
    orchestrator.handle_request("Remind me to take Ibuprofen every night")
    result = orchestrator.handle_request("Could taking my medicines together cause any interactions?")
    assert isinstance(result.interaction_warnings, list)  # ran without error either way


def test_timeline_needs_at_least_two_reports(orchestrator):
    result = orchestrator.handle_request("Show me the timeline of my reports")
    assert any(step.status == AgentStepStatus.SKIPPED for step in result.execution_log)


def test_timeline_across_two_reports(tmp_path):
    repo = Repository(db=Database(db_path=tmp_path / "test.db"))
    patient = repo.get_or_create_default_patient()
    orch = Orchestrator(repo, patient.id)
    orch.load_report("Diagnosis: Hypertension.", "visit1.pdf")
    orch.load_report("Diagnosis: Hypertension, Type 2 Diabetes. Medications: Metformin 500mg.", "visit2.pdf")

    result = orch.handle_request("How has my health changed over time?")
    assert len(result.timeline) == 2
    assert result.timeline[0].report_filename == "visit1.pdf"
    assert result.timeline[1].report_filename == "visit2.pdf"
