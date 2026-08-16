from agents.qa_agent import _NO_ANSWER_MESSAGE, answer_question

_REPORT_TEXT = (
    "HbA1c: 7.2%. LDL Cholesterol: 165 mg/dl. Patient reports mild fatigue. "
    "Prescribed Metformin 500mg twice daily. Follow-up in 3 months."
)


def test_on_topic_question_is_answered():
    result = answer_question(_REPORT_TEXT, "what is my LDL cholesterol")
    assert result.answer != _NO_ANSWER_MESSAGE
    assert result.retrieved_chunks


def test_unrelated_question_is_declined():
    result = answer_question(_REPORT_TEXT, "what is the capital of france")
    assert result.answer == _NO_ANSWER_MESSAGE
    assert result.retrieved_chunks == []
    assert result.confidence == "low"
