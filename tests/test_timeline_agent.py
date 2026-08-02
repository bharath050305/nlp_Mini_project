import pytest

from agents.timeline_agent import build_timeline
from schemas import Report
from tools.database import Database, Repository


@pytest.fixture
def repo(tmp_path):
    return Repository(db=Database(db_path=tmp_path / "test.db"))


def test_single_report_has_no_new_since_previous(repo):
    patient = repo.get_or_create_default_patient()
    repo.save_report(Report(patient_id=patient.id, filename="visit1.pdf", raw_text="Diagnosis: Hypertension."))

    timeline = build_timeline(repo, patient.id)
    assert len(timeline) == 1
    assert timeline[0].new_since_previous == []


def test_second_report_flags_new_findings(repo):
    patient = repo.get_or_create_default_patient()
    repo.save_report(Report(patient_id=patient.id, filename="visit1.pdf", raw_text="Diagnosis: Hypertension. Medications: Lisinopril 10mg morning."))
    repo.save_report(
        Report(
            patient_id=patient.id,
            filename="visit2.pdf",
            raw_text="Diagnosis: Hypertension, Type 2 Diabetes. Medications: Lisinopril 10mg morning, Metformin 500mg twice daily.",
        )
    )

    timeline = build_timeline(repo, patient.id)
    assert len(timeline) == 2
    assert timeline[0].new_since_previous == []
    assert any("diabetes" in item.lower() for item in timeline[1].new_since_previous)
    assert any("metformin" in item.lower() for item in timeline[1].new_since_previous)


def test_no_reports_gives_empty_timeline(repo):
    patient = repo.get_or_create_default_patient()
    assert build_timeline(repo, patient.id) == []


def test_timeline_is_chronological(repo):
    patient = repo.get_or_create_default_patient()
    repo.save_report(Report(patient_id=patient.id, filename="first.pdf", raw_text="Diagnosis: Anemia."))
    repo.save_report(Report(patient_id=patient.id, filename="second.pdf", raw_text="Diagnosis: Anemia, Asthma."))
    repo.save_report(Report(patient_id=patient.id, filename="third.pdf", raw_text="Diagnosis: Anemia, Asthma, Migraine."))

    timeline = build_timeline(repo, patient.id)
    assert [e.report_filename for e in timeline] == ["first.pdf", "second.pdf", "third.pdf"]
