import pytest

from tools.vector_store import TfidfVectorStore
from utils.exceptions import VectorStoreError

REPORT_TEXT = """
The patient's fasting blood sugar is 145 mg/dl which is elevated.
Blood pressure was recorded at 150 mmhg during the visit.
Current medications include Metformin 500mg twice daily and Lisinopril 10mg each morning.
The patient reports no chest pain or shortness of breath at this time.
""" * 5  # repeat so chunking has something to split


def test_index_and_query_returns_relevant_chunk():
    store = TfidfVectorStore()
    store.index(REPORT_TEXT, chunk_size=30, overlap=5)
    results = store.query("What is the blood pressure?", k=2)
    assert len(results) > 0
    assert any("blood pressure" in r.lower() for r in results)


def test_query_before_index_raises():
    store = TfidfVectorStore()
    with pytest.raises(VectorStoreError):
        store.query("anything")


def test_index_empty_text_raises():
    store = TfidfVectorStore()
    with pytest.raises(VectorStoreError):
        store.index("")
