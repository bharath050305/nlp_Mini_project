from agents.critic_agent import verify_answer


def test_grounded_answer_is_supported():
    chunks = ["HbA1c: 7.2%. LDL Cholesterol: 165 mg/dl. The patient shows elevated cholesterol."]
    result = verify_answer("what is my LDL", "Your LDL cholesterol is 165 mg/dl.", chunks)
    assert result.supported is True
    assert result.unsupported_claims == []


def test_unsupported_claim_is_flagged():
    chunks = ["HbA1c: 7.2%. LDL Cholesterol: 165 mg/dl."]
    answer = "Your LDL cholesterol is 165 mg/dl. You have been diagnosed with lung cancer."
    result = verify_answer("what is my LDL", answer, chunks)
    assert result.supported is False
    assert any("lung cancer" in c for c in result.unsupported_claims)


def test_no_retrieved_context_is_not_double_flagged():
    """No context at all is already reflected by qa_agent's own low
    confidence score — the critic shouldn't pile on a second warning."""
    result = verify_answer("random question", "I don't know.", [])
    assert result.supported is True


def test_fully_unrelated_answer_is_flagged():
    chunks = ["HbA1c: 7.2%. LDL Cholesterol: 165 mg/dl."]
    result = verify_answer("what is my LDL", "The weather today is sunny and warm.", chunks)
    assert result.supported is False
