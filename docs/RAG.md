# How MediAgent's RAG system works

MediAgent's question-answering feature ("What is my HbA1c?", "Am I anemic?") is a
genuine retrieval-augmented generation (RAG) loop, not just an LLM call. This
document explains exactly how it works, end to end, and what would change if
it were scaled up beyond a single-report, single-request use case.

## The core idea

A language model answering directly from a medical report risks two failure
modes: it might answer from its own general medical knowledge instead of
*this patient's actual report* (a hallucination risk), or it might not fit
the whole report in context. RAG avoids both by **retrieving** the specific
passages relevant to the question first, then constraining the model to
answer only from those passages.

## The pipeline, step by step

**1. Chunking** — [`utils/text_cleaning.chunk_text`](../utils/text_cleaning.py)

The report's raw extracted text (from [`tools/pdf_reader.py`](../tools/pdf_reader.py))
is split into overlapping, word-count-bounded chunks — 500 words per chunk
with a 100-word overlap by default. The overlap matters: if a lab value and
its reference range straddle a chunk boundary, the overlap keeps them
together in at least one chunk instead of silently splitting them apart.

**2. Indexing** — [`tools/vector_store.TfidfVectorStore.index()`](../tools/vector_store.py)

Every chunk is vectorized with scikit-learn's `TfidfVectorizer`
(unigrams + bigrams, English stop words removed). This produces a sparse
term-frequency/inverse-document-frequency matrix — one row per chunk — built
fresh per request, since each query is scoped to one patient's one report.
There's no persistent vector database: the index lives only for the
duration of the retrieval call.

**3. Retrieval** — [`TfidfVectorStore.query_with_scores()`](../tools/vector_store.py)

The question is vectorized with the *same* fitted vectorizer, and cosine
similarity is computed between the question vector and every chunk vector.
The top-`k` (default 3) chunks by similarity score are returned, each
paired with its raw score. If every chunk scores exactly zero (no
vocabulary overlap at all), the store falls back to returning the first `k`
chunks rather than an empty context — but the score stays `0.0`, so nothing
downstream is fooled into treating that as a confident match.

**4. Grounded generation** — [`agents/qa_agent.answer_question()`](../agents/qa_agent.py)

The retrieved chunks are joined into a `CONTEXT:` block and passed to the
configured LLM provider ([`llm/`](../llm/)) with a system prompt
([`QA_SYSTEM_PROMPT`](../prompts.py)) that explicitly instructs it to
answer *only* from the given context and say so plainly if the context
doesn't contain the answer — never fall back to general medical knowledge
for a specific value. This is the same prompt structure for the mock
offline provider and a real OpenAI/Anthropic call, so swapping providers in
`.env` doesn't change the retrieval-grounding guarantee.

**5. Honest confidence, not a uniform tone** — `_confidence_from_score()`

The *top* cosine similarity score from step 3 is mapped to a `low` /
`medium` / `high` confidence label (`agents/qa_agent.py`'s
`_HIGH_CONFIDENCE_THRESHOLD = 0.35`, `_MEDIUM_CONFIDENCE_THRESHOLD = 0.12`).
This is deliberately a proxy signal from retrieval strength, not a
calibrated probability — the point is that the UI shows a genuinely
low-confidence badge when retrieval found nothing relevant, instead of the
model sounding equally sure regardless of whether it actually found
anything. The `QAResult` returned to the caller carries `answer`,
`retrieved_chunks` (so a user/doctor can see exactly what was retrieved),
and `confidence` together — nothing is asserted without its evidence
being inspectable.

## Why TF-IDF instead of embeddings + a vector DB

The original design brief called for Sentence-Transformers + FAISS. This
build uses TF-IDF + cosine similarity instead, on purpose:

| | Sentence-Transformers + FAISS | TF-IDF (what's built) |
|---|---|---|
| Setup | ~90MB model download, first-run latency | Zero download, pure scikit-learn |
| Determinism | Model-version-dependent | Fully deterministic |
| Offline capability | Needs the model cached locally first | Works with zero network access, always |
| Retrieval quality here | Better for paraphrased/semantic matches | Adequate — medical report sections (labs vs. medications vs. history) are vocabulary-distinct enough that lexical overlap retrieves reliably |

For the actual scale this system operates at right now — one report,
typically a few hundred to a few thousand words, queried a handful of times
per session — TF-IDF's weakness (it can't match semantically similar but
lexically different phrasing, e.g. "kidney function" vs. "renal function")
matters less than its offline-by-default reliability. `TfidfVectorStore`
exposes the same `index()`/`query()` shape a real embedding backend would,
so swapping the implementation later is a one-file change, not a rewrite of
`qa_agent.py`.

## v4: semantic search (embeddings), built as an augmentation

The section above described this as a future upgrade; it's now built.
`agents/qa_agent.answer_question()` runs TF-IDF retrieval exactly as
before, **and**, when enabled, also runs semantic retrieval over
embeddings stored in Postgres — the two result sets are unioned before
being handed to the LLM, and the reported confidence takes the stronger
of the two scores. This is deliberately an **augmentation, not a
replacement**: TF-IDF still runs unconditionally (zero setup, always
available), and semantic search only adds to it when configured.

**Why not pgvector.** The obvious Postgres-native choice for storing and
querying embeddings is [pgvector](https://github.com/pgvector/pgvector) —
but it isn't installed on this project's Postgres instance, and has no
official Windows binary (only an unofficial, third-party-compiled one).
Rather than load unofficial native code into the database server, chunk
embeddings are stored in a plain `report_chunk_embeddings` table
(`backend/db_models.py`) with the vector as a native Postgres `float8[]`
column (SQLAlchemy `ARRAY(Float)`) — no extension required. Retrieval
(`agents/qa_agent._semantic_retrieve`) fetches a patient's stored
embeddings and computes cosine similarity in Python/numpy. At this
project's actual scale — one patient's chunks, at most a few hundred, not
millions of vectors across a whole product — brute-force similarity is
fully adequate; pgvector's real advantage (fast approximate search over
huge datasets) doesn't apply here.

**What this unlocks that per-request TF-IDF structurally couldn't:**

1. **Cross-report retrieval.** `PgRepository.get_chunk_embeddings_for_patient()`
   returns embeddings across *every* report a patient has on file, not
   just the one currently loaded into session — so a question can now be
   answered by pulling context from an older report, not only the most
   recent upload.
2. **No re-indexing per request.** Chunks are embedded once, at upload
   time (`backend/routers/reports.py`'s upload endpoint) or transcript
   finalize time (`backend/routers/transcripts.py`), via
   `backend/services/embedding_service.embed_and_store_report()` — not
   rebuilt from scratch on every question the way the TF-IDF index still
   is (TF-IDF is cheap enough per-request that this wasn't worth
   optimizing away for it specifically).
3. **Genuine synonym/vocabulary matching.** TF-IDF is lexical: a report
   that says "renal function" won't match a question about "kidney
   function" — zero shared words, zero score. Embeddings capture meaning,
   not just vocabulary; verified live during development (`renal function`
   vs. `kidney function`: cosine similarity 0.96 via the raw model, and
   the full pipeline correctly answered a "kidney function" question from
   a report that only ever said "renal").

**Backend**: `tools/embeddings.py` (`EmbeddingProvider` ABC + factory,
mirroring `llm/base.py`'s pattern exactly) — default
`sentence-transformers` running the small `all-MiniLM-L6-v2` model fully
locally (one-time ~80MB download, no API key), or `openai` (reuses
`openai_api_key`) as an alternative. Default is `disabled`: a fresh
install still runs on TF-IDF alone with zero setup, matching this
project's consistent "offline by default, opt into heavier backends"
pattern for the LLM and speech-to-text layers too.
