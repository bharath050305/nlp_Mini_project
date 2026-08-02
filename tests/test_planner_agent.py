import pytest

from agents.planner_agent import create_plan
from schemas import TaskType
from utils.exceptions import PlannerError


def test_summarize_intent():
    plan = create_plan("Summarize my report and explain abnormal values", has_report=True)
    types = [t.task_type for t in plan.tasks]
    assert TaskType.READ_REPORT in types
    assert TaskType.SUMMARIZE in types


def test_reminder_intent_extracts_medicine_and_frequency():
    plan = create_plan("Remind me to take Metformin every morning", has_report=False)
    reminder_tasks = [t for t in plan.tasks if t.task_type == TaskType.SET_REMINDER]
    assert len(reminder_tasks) == 1
    assert reminder_tasks[0].payload["medicine_name"].lower() == "metformin"
    assert reminder_tasks[0].payload["frequency"].lower() == "morning"


def test_list_reminders_does_not_also_set_a_reminder():
    plan = create_plan("What are my reminders?", has_report=False)
    types = [t.task_type for t in plan.tasks]
    assert TaskType.LIST_REMINDERS in types
    assert TaskType.SET_REMINDER not in types


def test_generate_report_intent():
    plan = create_plan("Please generate a doctor report for me", has_report=True)
    types = [t.task_type for t in plan.tasks]
    assert TaskType.GENERATE_REPORT in types


def test_no_report_defaults_to_summarize():
    plan = create_plan("asdkjfh random gibberish text", has_report=False)
    assert plan.tasks[0].task_type == TaskType.SUMMARIZE


def test_empty_request_raises():
    with pytest.raises(PlannerError):
        create_plan("   ", has_report=True)
