from utils.text_cleaning import chunk_text, clean_extracted_text, split_sentences


def test_clean_extracted_text_rejoins_hyphenated_linebreak():
    raw = "The patient has dia-\nbetes and takes medication."
    assert "dia-\nbetes" not in clean_extracted_text(raw)
    assert "diabetes" in clean_extracted_text(raw)


def test_clean_extracted_text_drops_page_artifacts():
    raw = "Report line one.\nPage 2 of 5\nReport line two."
    cleaned = clean_extracted_text(raw)
    assert "Page 2 of 5" not in cleaned


def test_clean_extracted_text_collapses_whitespace():
    raw = "Line one.\n\n\n\n\nLine two.    Extra   spaces."
    cleaned = clean_extracted_text(raw)
    assert "\n\n\n" not in cleaned
    assert "   " not in cleaned


def test_split_sentences_basic():
    text = "Patient has fever. Blood pressure is high. HbA1c is 8.2%."
    sentences = split_sentences(text)
    assert len(sentences) == 3


def test_split_sentences_handles_abbreviations():
    text = "Dr. Smith prescribed 500 mg. of Metformin daily."
    sentences = split_sentences(text)
    assert len(sentences) == 1


def test_chunk_text_respects_overlap():
    words = " ".join(f"word{i}" for i in range(1000))
    chunks = chunk_text(words, chunk_size=200, overlap=50)
    assert len(chunks) > 1
    # consecutive chunks should share the overlap region
    first_tail = chunks[0].split()[-50:]
    second_head = chunks[1].split()[:50]
    assert first_tail == second_head


def test_chunk_text_empty_input():
    assert chunk_text("") == []
