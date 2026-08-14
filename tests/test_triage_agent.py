from agents.lab_analysis import analyze_lab_values
from agents.triage_agent import assess_risk
from schemas import ExtractedEntities


def test_critical_symptom_keyword_in_user_text_overrides_everything():
    entities = ExtractedEntities()
    result = assess_risk(entities, [], user_text="I have severe chest pain and can't breathe")
    assert result.level == "critical"
    assert any("chest pain" in r for r in result.reasons)


def test_critical_symptom_keyword_in_extracted_symptoms():
    entities = ExtractedEntities(symptoms=["loss of consciousness"])
    result = assess_risk(entities, [], user_text="")
    assert result.level == "critical"


def test_severely_abnormal_lab_value_is_high():
    entities = ExtractedEntities(lab_values=["31.9%"])
    readings = analyze_lab_values(entities.lab_values)
    result = assess_risk(entities, readings, user_text="what is my hba1c")
    assert result.level == "high"


def test_mildly_abnormal_lab_value_is_medium():
    entities = ExtractedEntities(lab_values=["150 mg/dl"])
    readings = analyze_lab_values(entities.lab_values)
    result = assess_risk(entities, readings, user_text="how is my sugar")
    assert result.level == "medium"


def test_no_findings_is_low():
    result = assess_risk(ExtractedEntities(), [], user_text="hello")
    assert result.level == "low"


def test_critical_symptom_takes_priority_over_abnormal_labs():
    """Even with abnormal labs present, a critical symptom keyword should
    still win — urgency of the symptom outranks a lab-value severity calc."""
    entities = ExtractedEntities(lab_values=["150 mg/dl"])
    readings = analyze_lab_values(entities.lab_values)
    result = assess_risk(entities, readings, user_text="I am having severe bleeding")
    assert result.level == "critical"


def test_no_entities_does_not_raise():
    result = assess_risk(None, [], user_text="hello")
    assert result.level == "low"
