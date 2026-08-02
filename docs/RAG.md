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

## Upgrade path now that Postgres is in play

Now that this project has a real relational database instead of one SQLite
file, the natural next step for the RAG system is
**[pgvector](https://github.com/pgvector/pgvector)** — a Postgres extension
that adds a vector column type and approximate-nearest-neighbor indexing
directly in the same database already storing reports, reminders, and
users. Two things it would unlock that the current per-request TF-IDF index
structurally can't:

1. **Cross-report retrieval.** Today, `answer_question()` indexes exactly
   one report per call — a question is answered from *the current report*,
   not the patient's full history. With embeddings stored in Postgres, a
   query could retrieve the most relevant chunks across *every* report a
   patient has ever uploaded, which is a meaningfully different (and more
   useful) capability, especially combined with the Clinical Timeline
   Agent's existing cross-report reasoning.
2. **No re-indexing per request.** Chunks would be embedded once at upload
   time (e.g. in the same place `Orchestrator.load_report` already persists
   the report) and queried directly via SQL, instead of rebuilding a TF-IDF
   matrix from scratch on every question.

This is flagged as a **follow-up, not built in this iteration** — the
scope here was the multi-role platform (auth, scheduling, transcripts), and
swapping the retrieval backend is a genuinely separable piece of work that
deserves its own evaluation (embedding model choice, migration of existing
report text, index tuning) rather than being bundled in.
