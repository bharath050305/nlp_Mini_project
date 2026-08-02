from agents.drug_interaction_agent import check_interactions


def test_known_pair_is_flagged():
    warnings = check_interactions(["Warfarin", "Ibuprofen 400mg"])
    assert len(warnings) == 1
    assert warnings[0].severity in {"moderate", "major"}


def test_unrelated_medicines_are_not_flagged():
    warnings = check_interactions(["Cetirizine", "Loratadine"])
    assert warnings == []


def test_case_and_dosage_text_do_not_prevent_matching():
    warnings = check_interactions(["WARFARIN", "ibuprofen 400 mg tablet"])
    assert len(warnings) == 1


def test_single_medicine_produces_no_warnings():
    assert check_interactions(["Metformin"]) == []


def test_empty_list_produces_no_warnings():
    assert check_interactions([]) == []


def test_three_medicines_checks_all_pairs():
    # Warfarin+Ibuprofen and Warfarin+Aspirin are both in the curated table.
    warnings = check_interactions(["Warfarin", "Ibuprofen", "Aspirin"])
    pairs_found = {frozenset({w.drug_a, w.drug_b}) for w in warnings}
    assert len(pairs_found) == 2
