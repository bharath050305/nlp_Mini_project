import pytest

from schemas import ConversationTurn, Reminder, Report
from tools.database import Database, Repository


@pytest.fixture
def repo(tmp_path):
    db = Database(db_path=tmp_path / "test.db")
    return Repository(db=db)


def test_get_or_create_default_patient_is_idempotent(repo):
    p1 = repo.get_or_create_default_patient()
    p2 = repo.get_or_create_default_patient()
    assert p1.id == p2.id


def test_save_and_get_latest_report(repo):
    patient = repo.get_or_create_default_patient()
    repo.save_report(Report(patient_id=patient.id, filename="a.pdf", raw_text="text A"))
    repo.save_report(Report(patient_id=patient.id, filename="b.pdf", raw_text="text B"))

    latest = repo.get_latest_report(patient.id)
    assert latest.filename == "b.pdf"


def test_reminder_crud(repo):
    patient = repo.get_or_create_default_patient()
    saved = repo.add_reminder(
        Reminder(patient_id=patient.id, medicine_name="Metformin", frequency="morning")
    )
    assert saved.id is not None

    reminders = repo.list_reminders(patient.id)
    assert len(reminders) == 1
    assert reminders[0].medicine_name == "Metformin"

    assert repo.delete_reminder(saved.id) is True
    assert repo.list_reminders(patient.id) == []


def test_conversation_history_ordering(repo):
    patient = repo.get_or_create_default_patient()
    repo.add_conversation_turn(
        ConversationTurn(patient_id=patient.id, user_message="hi", assistant_response="hello")
    )
    repo.add_conversation_turn(
        ConversationTurn(patient_id=patient.id, user_message="bye", assistant_response="goodbye")
    )
    history = repo.get_conversation_history(patient.id)
    assert [h.user_message for h in history] == ["hi", "bye"]
