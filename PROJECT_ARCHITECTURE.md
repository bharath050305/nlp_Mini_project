# MediAgent — Project Architecture Guide (Placement Drive Reference)

This document is a standalone, self-contained explanation of the entire
MediAgent project — what it does, how every piece fits together, and why
each technical decision was made. It's written to be read top-to-bottom
before an interview, or used as a lookup reference during one. For the
day-to-day developer README (setup commands, etc.) see
[README.md](README.md); for the deep-dive on the RAG/retrieval system
specifically, see [docs/RAG.md](docs/RAG.md).

---

## 1. Elevator pitch (30 seconds)

> "MediAgent is a multi-agent healthcare platform. A user — patient,
> doctor, nurse, or admin staff — logs into a React app backed by a
> FastAPI + PostgreSQL API. Patients upload medical reports and chat in
> plain English ('summarize my report and flag anything abnormal'); a
> planner agent breaks that into sub-tasks and routes each one to a
> specialist agent — summarizer, RAG-based Q&A, drug-interaction checker,
> clinical timeline, medicine reminders. Doctors get role-scoped access
> to only their assigned patients, can review lab-trend analytics, and
> can turn a recorded consultation into a structured SOAP note via
> speech-to-text. A background scheduler fires medicine reminders and
> refill alerts. A Supervisor agent sits above all of this: after every
> chat turn it checks a deterministic risk-triage classification and an
> evidence-verification pass together, and if either looks concerning it
> queues the response into a real human-in-the-loop approval worklist for
> a doctor or nurse — not just a disclaimer. Every agent's autonomy and
> risk level is tagged and shown in the UI — the system is honest about
> what it can and can't be trusted to do on its own."

## 2. What problem this solves

A patient with a PDF lab report has three real problems: (1) the report
is written in language they don't understand, (2) they can't easily ask
follow-up questions about it, (3) their care team (doctor/nurse) has no
single place to see history, medicines, and adherence together. MediAgent
solves all three with one multi-agent system instead of three separate
tools, and does it with proper access control so a nurse can't read chat
transcripts and a doctor can't see a patient they're not assigned to.

## 3. High-level architecture

```
┌─────────────────────┐
│   React Frontend     │  Vite + TypeScript + Tailwind + TanStack Query
│   (role-based UI)     │  Patient / Doctor / Nurse / Staff dashboards
└──────────┬───────────┘
           │ HTTPS + httpOnly JWT cookie
           ▼
┌─────────────────────────────────────────────────────────┐
│                  FastAPI Backend (backend/)               │
│  ┌─────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │  Auth    │  │  RBAC deps    │  │  14 routers          │  │
│  │ (JWT +   │→ │ (deps.py:     │→ │ (auth, patients,     │  │
│  │  bcrypt) │  │ require_role, │  │ reports, chat,        │  │
│  │          │  │ require_      │  │ reminders, analytics, │  │
│  │          │  │ patient_      │  │ transcripts, ...)     │  │
│  │          │  │ access)       │  │                        │  │
│  └─────────┘  └──────────────┘  └───────────┬────────────┘  │
└────────────────────────────────────────────┼───────────────┘
                                               ▼
                          ┌────────────────────────────────────┐
                          │          Supervisor Agent             │
                          │      (agents/supervisor_agent.py)      │
                          │  runs Planner→Orchestrator, then       │
                          │  decides escalation from the result    │
                          └──────────────────┬─────────────────────┘
                                              ▼
                          ┌────────────────────────────────────┐
                          │       Planner → Orchestrator         │
                          │  (agents/planner_agent.py,           │
                          │   agents/orchestrator.py)             │
                          │  free text → ordered task list →      │
                          │  dispatches to specialist agents       │
                          └─┬────┬────┬────┬────┬────┬────┬──────┘
                            ▼    ▼    ▼    ▼    ▼    ▼    ▼
                        Summ. QA/RAG Rem. Drug Time. Triage Critic
                        Agent  +Critic Agent Int. Agent  Agent  (verifies
                                       Agent Agent               QA answers)
                            │    │    │    │    │    │    │
                            └────┴────┴────┴────┴────┴────┘
                                          │
                       ┌──────────────────┼──────────────────┐
                       ▼                  ▼                  ▼
                 PostgreSQL         LLM Provider        Tools
                 (15 tables,      (mock / OpenAI /   (PDF reader, OCR,
                  SQLAlchemy +      Anthropic,          Medical NER,
                  Alembic)          pluggable)          TF-IDF + embeddings,
                                                          Speech-to-text)
                       │
                       ▼
              agent_approvals table ──▶ doctor/nurse Approvals worklist
              (Supervisor writes here when triage=HIGH/CRITICAL, an
               answer fails verification, or a major drug interaction
               is flagged — a real approve/reject decision, audited)

  Separate process: backend/worker.py
  ── APScheduler (Postgres-backed job store) ──▶ fires daily/monthly
     reminder jobs → creates notifications → email/in-app dispatch
```

**Why a separate worker process?** If `uvicorn` ever runs with multiple
workers, an in-process scheduler would fire every job N times (once per
worker). A single standalone process avoids that entirely, and needs no
new infrastructure — it shares the same Postgres database as the API.

## 4. Tech stack, and the reasoning behind each choice

This table is the single most interview-relevant part of this document —
almost every "why did you use X" question maps to a row here.

| Layer | Choice | Why |
|---|---|---|
| Frontend | React + Vite + TypeScript + Tailwind | Fast dev server, type safety across a growing app with 4 different role-based UIs, utility-first CSS for consistent styling without a component library lock-in |
| Server state | TanStack Query | Caching, polling (notifications), and mutation state (loading/error) without hand-rolled `useEffect` fetch logic |
| Backend framework | FastAPI | Async-capable, automatic OpenAPI docs, Pydantic-native request/response validation, dependency-injection system that RBAC hooks into cleanly (`Depends(require_patient_access)`) |
| Database | PostgreSQL | The moment there's more than one user with roles and assignments, you need real relational joins (`care_assignments` linking doctors/nurses to patients) and multi-user concurrency — a single SQLite file doesn't support that safely |
| ORM / migrations | SQLAlchemy + Alembic | The relational complexity (11 tables, FKs, constraints) justified an ORM here, versus the project's earlier raw-SQL-only philosophy for a single-table SQLite demo |
| Auth | Self-issued JWT (httpOnly cookie) + bcrypt | No third-party identity provider needed for the project's own accounts; httpOnly cookie means the React app never touches the raw token (XSS-resistant) |
| Password hashing | `bcrypt` directly (not `passlib`) | `passlib` is unmaintained and breaks against `bcrypt>=4.1` (removed an internal attribute passlib probes for) — found this the hard way mid-build and swapped it out |
| LLM | Pluggable provider interface, **mock by default** | The mock provider is rule-based/extractive (real NLP logic, not a stub) — it lets the whole system run **offline with zero API keys**, which matters enormously for a live demo with no reliable wifi. One `.env` line switches to real OpenAI/Anthropic |
| Retrieval (RAG) | TF-IDF (scikit-learn) baseline, **optionally augmented** by sentence-transformer embeddings | Deterministic, zero-download baseline that always works; embeddings are opt-in for genuine semantic matching (see §7) |
| Vector storage | Plain Postgres `float8[]` column + Python/numpy cosine similarity — **not pgvector** | pgvector needs native compilation and has no official Windows binary; at this project's actual scale (one patient's report chunks, not millions of vectors), brute-force cosine similarity in Python is completely adequate and avoids loading unofficial native code into the database server |
| NER | spaCy + a custom `EntityRuler` with a curated medical vocabulary | Off-the-shelf spaCy mislabels drug names; a curated ruler is lighter than SciSpaCy and fully explainable — every match traces to a vocab file, not an opaque model |
| Scheduling | APScheduler + `SQLAlchemyJobStore` (own process) | Persists jobs across restarts using the database that's already required — no Redis/Celery broker needed for this scale |
| Speech-to-text | OpenAI's Whisper, run **locally** by default | No API key required; `openai-whisper` + a system `ffmpeg` binary, same "thin wrapper + system binary" pattern used for OCR |
| OCR | Tesseract via `pytesseract` | Lightweight wrapper around a well-established open-source OCR engine; avoided `EasyOCR` because it pulls in a second full PyTorch install |
| Charts | Recharts | Standard, well-documented React charting library, sufficient for line/bar charts without a heavier visualization framework |
| Rate limiting | `slowapi` | Lightweight FastAPI-native wrapper, applied specifically to login/register to blunt credential-stuffing |

## 5. The agent system — the actual "AI" architecture

This is the part that makes the project "agentic" rather than "a chatbot
with extra steps." The distinction matters and is worth stating plainly
in an interview: **a chatbot answers one message at a time; this system
decomposes a request into a typed plan, executes each step against a
dedicated specialist, and logs the whole decision trail.**

### 5.1 Planner Agent (`agents/planner_agent.py`)
Takes free text ("summarize my report and check drug interactions"),
returns a `Plan` — an ordered list of typed `Task` objects
(`TaskType.SUMMARIZE`, `TaskType.CHECK_INTERACTIONS`, etc.). Rule-based
intent detection, not an LLM call — deterministic and fast, and every
decision is traceable to a specific keyword/pattern match rather than an
opaque model judgment.

### 5.2 Orchestrator / Executor (`agents/orchestrator.py`)
The "memory agent." Holds a `Session` (uploaded report text, extracted
entities, Q&A history) for one patient, runs each `Task` from the plan
against the matching specialist agent, and logs every step — agent name,
status, duration, **autonomy level, risk tier**. Critically, it's stateless
across requests by design: `Orchestrator.__init__` rehydrates the entire
session from the database every time it's constructed, so a fresh
`Orchestrator` is built **per HTTP request** in the FastAPI backend with
zero risk of stale state. This is what let the Postgres migration happen
with **zero changes to the orchestrator itself** — a new `PgRepository`
just duck-types the same method names the old SQLite repository had.

### 5.3 Governance layer (`agents/governance.py`)
Every task is tagged with:
- **Autonomy level** (A0 suggest-only, A1 draft-for-signoff, A2
  execute-with-gates — **A3 fully autonomous is deliberately never used**)
- **Risk tier** (R0 administrative → R2 clinical-decision-support)

These aren't decorative badges — they're adapted directly from a
published taxonomy (Xu et al. 2026, *J. Biomed. Inform.*), and A2 tasks
have a real behavioral gate: e.g. a reminder isn't saved if the medicine
name extraction has low confidence, rather than silently guessing.

### 5.4 Specialist agents
| Agent | Job | Autonomy · Risk |
|---|---|---|
| Summarizer | Deterministic reference-range checking (`agents/lab_analysis.py`) + LLM narrative, evidence trail per claim | A0 · R1 |
| QA (RAG) | Retrieval-augmented Q&A — see §7 | A0 · R1 |
| Reminder | CRUD for medicine reminders, gated on extraction confidence | A2 · R0 |
| Drug Interaction | Curated ~18-pair reference table cross-check, always deflects to "confirm with your pharmacist" | A0 · R2 |
| Clinical Timeline | Diffs entities across every report on file — "what's new since last time" | A0 · R1 |
| Report Generator | Assembles a downloadable doctor-summary PDF | A1 · R1 |
| Transcript Agent | Structures a consultation transcript into a 4-field SOAP note (Subjective/Objective/Assessment/Plan) | A1 · R1 |
| Clinical Triage Agent | Rule-based LOW/MEDIUM/HIGH/CRITICAL risk classification — see §5.5 | A0 · R2 |
| Critic / Evidence Verifier | Checks a QA answer's sentences against its own retrieved chunks for support — see §5.5 | A0 · R1 |

### 5.5 The Supervisor pattern — what actually makes this "multi-agent," not just "many functions"

A fair challenge to push back on: doesn't every agentic-AI project just
mean "call several functions in a row"? The Planner → Orchestrator loop
already answers part of that (dynamic task decomposition, not a fixed
pipeline), but the **Supervisor** is what adds the second half —
cross-cutting judgment that no single specialist agent has visibility
into on its own:

```
Supervisor.handle_request()
  1. Runs the existing Orchestrator exactly as before (zero changes to it)
  2. Reads the COMBINED result: triage level + critic verification +
     drug-interaction severity — three signals, one decision
  3. Escalation needed if: triage is HIGH/CRITICAL, OR the Critic
     flagged an unsupported claim, OR a MAJOR drug interaction was found
  4. If yes: writes an `agent_approvals` row (Postgres) and sets
     requires_human_review=True on the response — the patient still
     gets their answer immediately (never silently blocked), but a
     doctor/nurse now has a real approve/reject decision to make
```

Two things worth stating explicitly if asked:
- **The Triage Agent is deliberately not the LLM.** It's a rule-based
  ladder (curated critical-symptom keywords → beat everything else;
  then lab readings more than 2x outside their reference range → HIGH;
  any abnormal reading → MEDIUM). Handing "is this an emergency" to a
  language model's judgment would be the one place in this whole system
  where a hallucination could actually hurt someone — so it isn't.
- **The Critic is provider-agnostic.** It doesn't matter whether the
  answer came from the mock provider or a real GPT-4/Claude call — it
  checks the *output text* against the *retrieved evidence chunks* for
  vocabulary overlap, sentence by sentence. Verified live during
  development: it correctly flagged a deliberately-injected fabricated
  claim ("you have been diagnosed with lung cancer") while leaving a
  genuinely grounded sentence alone in the same answer.

### 5.6 Patient Digital Twin

`GET /api/patients/{id}/digital-twin` — explicitly **not** a new
reasoning layer, a consolidated read-model. It calls the same functions
everything else already calls (entity extraction, `lab_analysis.py`,
`triage_agent.py`, the dose-log adherence math from the analytics
router) and assembles them into one response instead of the frontend
making five separate calls and stitching the picture together itself.
Worth mentioning if asked "what would you add next" — this is the
natural foundation a more advanced longitudinal-reasoning feature would
build on, without needing a new data model.

### 5.7 Agent Registry

`GET /api/admin/agents` (staff-only) returns a declarative listing —
every agent's name, module, description, what it reads, what it writes,
its risk tier and autonomy level (`agents/registry.py`). Said plainly,
including in the code's own docstring: **this is not a runtime-enforced
permission sandbox.** Enforcing it for real would mean routing every
agent's data access through a generic permission-checked proxy —
disproportionate rework for what this project needs, and it would risk
destabilizing the RBAC that's already correctly enforced at the API
boundary regardless of which agent a router calls. What it *does* give
you: an honest, single-source answer to "what can this agent touch,"
generated by reading the actual code — the kind of thing a real system
audit would ask for, done at the scale this project can actually back up.

## 6. Role-based access control (RBAC)

Four roles, enforced **server-side on every request**, not just hidden in
the UI:

| | Patient (own) | Doctor (assigned) | Nurse (assigned) | Staff |
|---|---|---|---|---|
| Reports / timeline / "previous conditions" | ✔ | ✔ | ✔ | ✘ |
| Chat / RAG Q&A | ✔ | ✔ | ✘ | ✘ |
| Reminders (read/write) | ✔ | ✔ | ✔ | ✘ |
| Doctor PDF generation | ✘ | ✔ | ✘ | ✘ |
| Transcript upload/finalize | ✘ | ✔ | ✘ | ✘ |
| Analytics dashboard | ✘ | ✔ | ✔ | ✘ |
| Digital Twin view | ✘ | ✔ | ✔ | ✘ |
| Approvals worklist | ✘ | ✔ | ✔ | ✘ |
| Agent Registry | ✘ | ✘ | ✘ | ✔ |
| Manage accounts / assignments | ✘ | ✘ | ✘ | ✔ |

**Mechanism**: `backend/deps.py` has two FastAPI dependencies —
`require_role(*roles)` (simple role check) and `require_patient_access`
(resolves a `Patient` row only if the current user is that patient, OR a
doctor/nurse with an **active row in `care_assignments`** for that
specific patient). A doctor with zero assignments gets a 403 on every
patient endpoint, exactly like a stranger would. Staff is deliberately an
**administrative role, not a clinical-data role** — least privilege by
default: staff manages accounts and assignments but can never read report
content, even though they created the account.

**Why this design, if asked**: hidden UI elements are not access
control — anyone with browser devtools can call the API directly. Every
permission check happens in the FastAPI dependency layer, before a
handler function even runs.

## 7. The RAG (Retrieval-Augmented Generation) system

This is very likely to come up directly in an interview — it's the
clearest "real NLP/AI engineering" story in the project. Full detail in
[docs/RAG.md](docs/RAG.md); summary:

**The loop**: chunk the report text (overlapping word windows) →
vectorize each chunk → retrieve the top-k chunks most similar to the
question → hand *only those chunks* to the LLM with an explicit
instruction to answer strictly from that context → report a confidence
level derived from the retrieval score, not a uniformly confident tone.

**Two retrieval backends, used together**:
1. **TF-IDF + cosine similarity** (scikit-learn) — the always-on
   baseline. Deterministic, zero download, rebuilt fresh per request.
2. **Sentence-transformer embeddings** (opt-in via `.env`) — computed
   once at upload time and stored in Postgres (a plain `float8[]`
   column, no pgvector — see §4), spanning a patient's **entire report
   history**, not just the current report. Retrieval **augments**
   TF-IDF (union of both result sets) rather than replacing it, so a
   lexical match and a semantic match are both caught.

**Why this is defensible under questioning**: it's not "call an LLM and
hope" — the LLM only ever sees retrieved, real report text, the
confidence score is computed from an actual similarity number (not
invented), and the two-backend design was a genuine engineering
trade-off made explicit (a proper vector-database extension wasn't
available on this Windows Postgres install, so a scale-appropriate
alternative was built instead of blocking on it).

**Verified during development** (a good concrete detail to mention): a
report that only ever said "renal function" correctly answered a
"kidney function" question — TF-IDF alone (zero shared vocabulary) would
have failed; the semantic layer's similarity score (0.53) correctly beat
TF-IDF's (0.28) and the combined confidence was reported as "high."

## 8. Database schema (PostgreSQL, 15 tables)

```
users ──┬── patients (user_id nullable — a chart can exist with no login)
        │       │
        │       ├── care_assignments (doctor/nurse ↔ patient, role_at_assignment)
        │       ├── reports ──── report_chunk_embeddings (semantic search)
        │       ├── reminders ── reminder_schedule_slots
        │       │                    └── dose_logs (explicit "mark taken", audit trail)
        │       ├── transcripts ── soap_notes (→ finalizes into a linked report)
        │       ├── conversation_history
        │       └── agent_approvals (Supervisor's human-in-the-loop queue —
        │                            reviewed_by/reviewed_at/review_note = audit trail)
        └── notifications (recipient = any user)

  + apscheduler_jobs (owned by APScheduler at runtime, not a SQLAlchemy model — see §11)
```

Two design decisions worth being able to explain:
- **`quantity_remaining` only ever decrements from an explicit "mark dose
  taken" action** (a `dose_logs` insert), never assumed from the clock.
  This is auditable — a doctor can see exactly which doses were logged,
  by whom, and when — and matches the project's broader philosophy of
  not silently acting on unconfirmed input.
- **`care_assignments` uses one table with a `role_at_assignment` column**
  instead of separate `doctor_patient_assignments`/`nurse_patient_assignments`
  tables — same shape, one less duplicated schema to maintain, and the
  RBAC dependency checks it with one query pattern regardless of role.

## 9. Frontend structure

```
frontend/src/
  api/            One typed client file per backend resource (axios + TanStack Query)
  context/        AuthContext — hydrates from GET /api/auth/me on load
  components/
    layout/       AppShell, Sidebar, TopBar, RoleGuard (blocks cross-role routes)
    chat/         ChatWindow, VoiceRecorderButton (MediaRecorder API), SpeakButton (SpeechSynthesis API)
    reminders/    ReminderForm, ScheduleBuilder (daily/monthly slot builder)
    analytics/    LabTrendChart, AdherenceChart, StatTile (Recharts)
    transcripts/  AudioUploader, SoapNoteEditor, TranscriptStatus (polls processing state)
  pages/          One directory per role: patient/, doctor/, nurse/, staff/, shared/
```

Auth flow: login sets an httpOnly cookie server-side → `AuthContext`
calls `GET /api/auth/me` to learn who's logged in → `/` redirects to
`/patient`, `/doctor`, `/nurse`, or `/staff` based on role →
`RoleGuard` wraps each subtree and redirects anyone in the wrong area
back to their own landing page.

## 10. Notification / scheduling pipeline

```
Reminder created with a daily/monthly schedule
        │
        ▼
backend/services/scheduler_service.py registers a CronTrigger job
(APScheduler, persisted in Postgres via SQLAlchemyJobStore)
        │
        ▼ (fires at the scheduled time, in the standalone worker process)
Creates a `notifications` row (type=dose_reminder, channel=both)
        │
        ├──▶ In-app: read directly by GET /api/notifications (polled every 30s)
        │
        └──▶ Email: a SEPARATE recurring job (every 1 min) dispatches
             pending email notifications — decoupled from the firing job
             so an SMTP hiccup never blocks the reminder itself from firing

Separately: a one-shot job ~2h after each dose reminder checks whether a
"taken" dose_log exists; if not, logs "missed_auto" and notifies.

Separately: whenever quantity_remaining crosses the low-stock threshold
(only on an explicit dose-taken action), a refill_alert notification fires once.
```

## 11. Interesting engineering problems actually hit (good STAR-format talking points)

- **`passlib` vs. modern `bcrypt`**: passlib (used for password hashing)
  turned out to be unmaintained and incompatible with `bcrypt>=4.1` — it
  probes for an internal attribute that newer bcrypt removed. Diagnosed
  from a live traceback, swapped to using the `bcrypt` library directly.
- **pgvector unavailable on Windows**: the "obvious" choice for storing
  embeddings in Postgres has no official Windows binary. Rather than
  block on installing an unofficial third-party compiled binary into a
  production-adjacent database server, redesigned semantic search to use
  a plain array column + application-level cosine similarity —
  appropriate at the actual data scale involved.
- **APScheduler + Alembic autogenerate conflict**: APScheduler creates
  its own `apscheduler_jobs` table at runtime (not part of the
  SQLAlchemy models), so Alembic's `--autogenerate` kept proposing to
  *drop* it — which would have destroyed every scheduled reminder job on
  the next migration. Fixed with an `include_object` filter in
  `alembic/env.py` that excludes that table from schema diffing.
  permanently.
- **Whisper needs `ffmpeg` as a real system binary**, not a pip package —
  installed via `winget`, then discovered it wasn't on `PATH` for new
  processes (the installer doesn't register it), so it had to be added
  to the persistent user `PATH` explicitly.
- **Multi-tenancy without rewriting the agent layer**: the original
  single-patient SQLite `Repository` and Postgres `PgRepository` share no
  inheritance — they just implement the same method names. Because the
  agents only ever call `repo.<method>(...)`, swapping the whole
  persistence backend required **zero changes** to any agent. This is a
  duck-typing/dependency-inversion story worth telling explicitly if
  asked "how did you handle scaling to multiple users."
- **Turning down 34 of 40 requested features, on purpose**: a later
  request asked for a full "production-scale agentic platform" — 40
  numbered features including Kubernetes, Kafka, multi-tenant hospital
  isolation, FHIR/EHR integration, a trained ML risk-prediction model,
  a knowledge graph, and chaos/load testing at 100K synthetic patients.
  None of that infrastructure exists here — no cluster, no broker, no
  second hospital, no labeled training data. Building stub versions of
  any of it would have been strictly worse than not having them: an
  unverifiable claim is a bigger liability under interview questioning
  than a smaller, fully-defensible system. What shipped instead was the
  6 items genuinely buildable on the *existing* architecture with zero
  new infrastructure — Supervisor, Triage, Critic, human-in-the-loop
  approvals, Digital Twin, Agent Registry (§5.5–5.7) — each one real,
  tested, and demonstrable end-to-end. This is worth having ready as an
  answer to "how do you handle scope": recognizing when a request
  exceeds what can be honestly delivered, and saying so, rather than
  producing something that only looks finished.

## 12. Likely interview questions and how to answer them

**Q: Why not just use LangGraph/LangChain for the agent orchestration?**
A: The planner→task-list→executor pattern *is* the same plan-act-observe
loop those frameworks formalize — built from first principles here so
every line is explainable, with no opaque framework internals to defend
under questioning about internals I didn't write.

**Q: Why does the LLM default to a "mock" provider — isn't that fake?**
A: It's genuinely rule-based/extractive logic (regex + keyword matching
over the actual report text), not a hardcoded stub — it produces
report-specific output. It exists so the whole system runs with zero API
cost and zero internet dependency, and swapping to a real OpenAI/Anthropic
model is a one-line `.env` change using the exact same prompts.

**Q: How do you know the RAG answers aren't hallucinated?**
A: The LLM is only ever given retrieved chunks as context and explicitly
instructed to say so if the answer isn't in them — and the confidence
score reported alongside every answer comes from the actual retrieval
similarity score, not the model's tone.

**Q: How is this different from just calling ChatGPT with the PDF text?**
A: Four ways: (1) task decomposition — one request can trigger multiple
specialist agents in sequence; (2) RBAC — different users get
fundamentally different data access, enforced server-side; (3) retrieval
grounding — answers are constrained to retrieved report text, not free
generation; (4) governance — every action carries an explicit
autonomy/risk label instead of an undifferentiated "AI did something."

**Q: What would you do differently at real production scale?**
A: Swap TF-IDF + array-column cosine similarity for a proper vector
index (pgvector once available, or a managed vector DB) once report
volume per patient grows beyond a few hundred chunks; move the
notification center from polling to WebSocket/SSE push; add
Docker/CI (explicitly out of scope for this build by choice, not
oversight — the hardening pass that was done covered secrets, rate
limiting, and logging, and stopped there deliberately).

**Q: What's the single hardest bug you fixed?**
A: The APScheduler/Alembic autogenerate conflict (§11) — subtle because
it wouldn't have failed loudly, it would have silently deleted every
user's scheduled medicine reminders on the next routine migration.

**Q: What makes this "multi-agent" rather than just several functions
called in sequence?**
A: Two things, concretely. First, the Planner produces a *dynamic* task
list from free text, not a fixed pipeline — different requests genuinely
execute different agent sequences. Second, and more importantly, the
Supervisor (§5.5) makes a decision no single specialist agent has the
information to make on its own: it reads the triage result, the critic's
verification, and any drug-interaction warnings *together* and decides
whether a human needs to see this. That cross-cutting judgment, plus a
real approve/reject workflow with an audit trail, is what separates
"agentic" from "a chatbot that calls tools."

**Q: Why is risk triage rule-based instead of asking the LLM to judge
severity?**
A: Because that's the one place in the whole system where getting it
wrong has the highest cost, and LLMs are the least auditable component
available. A curated keyword ladder plus a numeric threshold on lab
deviation is slower to extend than "just ask GPT-4," but every
CRITICAL/HIGH classification traces to a specific rule you can point to
— which matters far more than coverage for a safety-classification step.

**Q: You said you deliberately didn't build 34 of 40 requested features
— how did you decide which 6 to keep?**
A: I only kept the ones buildable on infrastructure that actually
exists here, verified by actually building and testing them, not by how
impressive they'd sound. See §11 — this is worth leading with if the
interviewer pushes on scope, since it shows the judgment call was
explicit, not an oversight.

## 13. Quick facts for a rapid-fire round

- **36** API routes across **14** routers
- **15** PostgreSQL tables
- **74** automated backend tests passing, `ruff` lint clean
- **12** specialist/support agents (`agents/` directory), including a
  Supervisor, a rule-based Triage Agent, and a provider-agnostic Critic
- **4** user roles, enforced via 2 core FastAPI dependencies
- **2** retrieval backends for RAG (TF-IDF always-on, embeddings opt-in)
- **1** human-in-the-loop approval queue, with a full audit trail
  (who reviewed, when, what they decided, and why)
- Runs **fully offline** by default (mock LLM, no API keys required) —
  every "real" backend (OpenAI, Whisper, embeddings, SMTP) is an explicit
  opt-in via one `.env` line each
