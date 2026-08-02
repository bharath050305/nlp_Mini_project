"""
app.py

MediAgent Streamlit dashboard — v2.

Design system is deliberately grounded in real clinical UI conventions
rather than generic dark-chat styling: status colors follow the same
green/amber/red convention used on lab reports and vital-sign monitors,
and the persistent "agent pipeline" strip at the top of the page is the
one signature element — it's the literal answer to "why is this agentic
and not a chatbot," visible before a single message is sent.

Run with: streamlit run app.py
"""

from __future__ import annotations

import html

import streamlit as st

from agents.orchestrator import Orchestrator
from agents.reminder_agent import list_reminders_with_schedule
from llm import get_llm_provider
from tools.database import Repository
from tools.pdf_reader import extract_text_from_bytes
from utils.exceptions import MediAgentError
from utils.logger import get_logger

logger = get_logger(__name__)

st.set_page_config(
    page_title="MediAgent",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --------------------------------------------------------------------------
# Design tokens
# --------------------------------------------------------------------------
_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

:root {
    --bg: #0F1620;
    --surface: #161F2B;
    --surface-hi: #1C2836;
    --border: #2A3847;
    --text: #E7EDF3;
    --text-muted: #8DA0B5;
    --accent: #2DD4BF;
    --a0: #2DD4BF;
    --a1: #FBBF24;
    --a2: #FB923C;
    --ok: #4ADE80;
    --warn: #FBBF24;
    --bad: #F87171;
    --idle: #3A4A5C;
}

.stApp { background: var(--bg); font-family: 'Inter', sans-serif; }
h1, h2, h3, .ma-display { font-family: 'IBM Plex Sans', sans-serif !important; letter-spacing: -0.01em; }
code, .ma-mono { font-family: 'IBM Plex Mono', monospace !important; }

/* --- pipeline strip (signature element) -------------------------------- */
.ma-pipeline { display: flex; gap: 6px; flex-wrap: wrap; margin: 4px 0 14px 0; }
.ma-pill {
    display: inline-flex; align-items: center; gap: 5px;
    font-family: 'IBM Plex Mono', monospace; font-size: 11px; font-weight: 500;
    padding: 5px 10px; border-radius: 6px; border: 1px solid var(--border);
    background: var(--surface); color: var(--text-muted); white-space: nowrap;
}
.ma-pill.done   { border-color: var(--ok);   color: var(--ok);   background: rgba(74,222,128,0.08); }
.ma-pill.failed { border-color: var(--bad);  color: var(--bad);  background: rgba(248,113,113,0.08); }
.ma-pill.skipped{ border-color: var(--warn); color: var(--warn); background: rgba(251,191,36,0.08); }
.ma-pill .dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }

/* --- badges ------------------------------------------------------------- */
.ma-badge {
    display: inline-block; font-family: 'IBM Plex Mono', monospace; font-size: 10.5px;
    font-weight: 500; padding: 2px 7px; border-radius: 5px; border: 1px solid;
    margin-right: 5px; white-space: nowrap;
}

/* --- evidence / cards ----------------------------------------------------- */
.ma-card {
    background: var(--surface); border: 1px solid var(--border); border-radius: 10px;
    padding: 12px 14px; margin-bottom: 8px;
}
.ma-card .claim { color: var(--text); font-size: 13.5px; margin-bottom: 3px; }
.ma-card .evidence { color: var(--text-muted); font-size: 12px; font-family: 'IBM Plex Mono', monospace; }

/* --- onboarding ----------------------------------------------------------- */
.ma-step {
    display: flex; gap: 12px; align-items: flex-start; padding: 10px 0;
    border-bottom: 1px solid var(--border);
}
.ma-step:last-child { border-bottom: none; }
.ma-step-num {
    font-family: 'IBM Plex Mono', monospace; color: var(--accent); font-weight: 600;
    font-size: 13px; min-width: 22px;
}
.ma-step-text { color: var(--text-muted); font-size: 13.5px; }
.ma-step-text b { color: var(--text); }

.ma-banner {
    border: 1px solid var(--border); border-left: 3px solid var(--accent);
    background: var(--surface); border-radius: 8px; padding: 10px 14px;
    font-size: 13px; color: var(--text-muted); margin-bottom: 12px;
}
</style>
"""
st.markdown(_CSS, unsafe_allow_html=True)

# --------------------------------------------------------------------------
# Static lookup tables for badge rendering
# --------------------------------------------------------------------------
_AUTONOMY_INFO = {
    "A0": ("#2DD4BF", "A0 suggest-only"),
    "A1": ("#FBBF24", "A1 draft-for-signoff"),
    "A2": ("#FB923C", "A2 gated-execution"),
}
_RISK_INFO = {
    "R0": ("#8DA0B5", "R0 administrative"),
    "R1": ("#8DA0B5", "R1 patient info"),
    "R2": ("#C4A5F0", "R2 decision support"),
}
_CONFIDENCE_INFO = {"high": "#4ADE80", "medium": "#FBBF24", "low": "#8DA0B5"}
_SEVERITY_INFO = {"moderate": "#FBBF24", "major": "#F87171"}

# Canonical pipeline order for the persistent strip. list_reminders folds
# into the same "Reminder" pill as set_reminder for display purposes.
_PIPELINE = [
    ("read_report", "📄", "Reader"),
    ("summarize", "📝", "Summarizer"),
    ("answer_question", "🔎", "QA/RAG"),
    ("set_reminder", "💊", "Reminder"),
    ("check_interactions", "⚠️", "Interactions"),
    ("view_timeline", "📈", "Timeline"),
    ("generate_report", "📋", "Report Gen"),
]


def _badge(text: str, color: str) -> str:
    return f'<span class="ma-badge" style="color:{color};border-color:{color}66;background:{color}18;">{html.escape(text)}</span>'


def _pipeline_html(execution_log=None) -> str:
    status_by_key: dict[str, str] = {}
    if execution_log:
        for step in execution_log:
            key = "set_reminder" if step.agent_name == "list_reminders" else step.agent_name
            status_by_key[key] = step.status.value

    pills = ['<div class="ma-pipeline">']
    for key, icon, label in _PIPELINE:
        status = status_by_key.get(key, "idle")
        pills.append(f'<span class="ma-pill {status}"><span class="dot"></span>{icon} {html.escape(label)}</span>')
    pills.append("</div>")
    return "".join(pills)


# --------------------------------------------------------------------------
# Session / orchestrator plumbing
# --------------------------------------------------------------------------
@st.cache_resource
def get_repository() -> Repository:
    """One shared SQLite repository per server process."""
    return Repository()


def get_orchestrator() -> Orchestrator:
    """One Orchestrator per browser session. Note: even if this is ever
    recreated fresh (a rerun that lost session_state), Orchestrator.__init__
    rehydrates the most recent report from the database on its own — see
    agents/orchestrator.py — so an upload can't silently vanish from the
    assistant's point of view."""
    if "orchestrator" not in st.session_state:
        repo = get_repository()
        patient = repo.get_or_create_default_patient()
        st.session_state.orchestrator = Orchestrator(repo, patient.id)
        st.session_state.chat_history = []
    return st.session_state.orchestrator


# --------------------------------------------------------------------------
# Sidebar
# --------------------------------------------------------------------------
def render_sidebar(orch: Orchestrator) -> None:
    with st.sidebar:
        st.markdown("### 🩺 MediAgent")
        st.caption("Agentic AI for multi-step healthcare task automation")

        try:
            provider_name = get_llm_provider().name
        except MediAgentError as exc:
            provider_name = "unavailable"
            st.error(f"LLM provider error: {exc}")
        st.markdown(_badge(f"LLM: {provider_name}", "#2DD4BF"), unsafe_allow_html=True)

        st.divider()
        st.markdown("**📄 Medical report**")
        uploaded = st.file_uploader("Upload a PDF report", type=["pdf"], label_visibility="collapsed")
        upload_signature = f"{uploaded.name}:{uploaded.size}" if uploaded is not None else None
        if uploaded is not None and upload_signature != st.session_state.get("last_upload_signature"):
            with st.spinner("Reading and indexing PDF..."):
                try:
                    text = extract_text_from_bytes(uploaded.getvalue(), uploaded.name)
                    orch.load_report(text, uploaded.name)
                    st.session_state.last_upload_signature = upload_signature
                    st.success(f"Loaded — {len(text):,} characters extracted.")
                except MediAgentError as exc:
                    st.error(f"Couldn't process this PDF: {exc}")

        if orch.session.has_report:
            st.markdown(
                f'<div class="ma-banner">📎 Active report: <b>{html.escape(orch.session.report_filename)}</b><br>'
                f'Saved to the database — safe across refreshes and restarts.</div>',
                unsafe_allow_html=True,
            )
        else:
            st.caption("No report yet. You can still set reminders or ask general questions.")

        st.divider()
        st.markdown("**💊 Reminders**")
        reminders = list_reminders_with_schedule(orch.repo, orch.session.patient_id)
        if reminders:
            for r in reminders:
                st.markdown(f"**{html.escape(r['medicine_name'])}** — {html.escape(r['frequency'] or 'no schedule')}")
                st.caption(f"Next dose: {r['next_dose']}")
        else:
            st.caption('Try: "remind me to take Metformin every morning"')

        st.divider()
        with st.expander("⚙️ How autonomy & risk labels work"):
            st.caption(
                "Every agent step is tagged with an autonomy level (how much it "
                "acts on its own) and a risk tier (how much it matters if it's "
                "wrong), adapted from a 2026 survey of 223 healthcare-agent "
                "studies (Xu et al., *J. Biomed. Inform.*). MediAgent never "
                "operates above A2 (gated execution) — no task in this build "
                "runs fully autonomously."
            )
            for color, label in _AUTONOMY_INFO.values():
                st.markdown(_badge(label, color), unsafe_allow_html=True)


# --------------------------------------------------------------------------
# Result rendering
# --------------------------------------------------------------------------
def render_execution_timeline(execution_log) -> None:
    for step in execution_log:
        a_color, a_label = _AUTONOMY_INFO.get(step.autonomy.value if step.autonomy else "", ("#8DA0B5", ""))
        r_color, r_label = _RISK_INFO.get(step.risk_tier.value if step.risk_tier else "", ("#8DA0B5", ""))
        icon = {"done": "✅", "failed": "❌", "skipped": "⏭️", "pending": "…", "running": "…"}[step.status.value]
        line = f"{icon} **{step.agent_name}** — {html.escape(step.detail)} · `{step.duration_ms}ms`"
        st.markdown(line)
        if a_label:
            st.markdown(_badge(a_label, a_color) + _badge(r_label, r_color), unsafe_allow_html=True)


def render_entities(entities) -> None:
    if entities is None:
        return
    cols = st.columns(3)
    fields = [
        ("Diseases", entities.diseases), ("Medicines", entities.medicines), ("Symptoms", entities.symptoms),
        ("Lab tests", entities.lab_tests), ("Lab values", entities.lab_values), ("Dosages", entities.dosages),
    ]
    for i, (label, values) in enumerate(fields):
        with cols[i % 3]:
            st.markdown(f"**{label}**")
            st.caption(", ".join(values) if values else "—")


def render_evidence(summary) -> None:
    if summary is None or not summary.evidence:
        return
    st.markdown(f"**Evidence trail** {_badge(summary.confidence, _CONFIDENCE_INFO.get(summary.confidence, '#8DA0B5'))}", unsafe_allow_html=True)
    for item in summary.evidence:
        st.markdown(
            f'<div class="ma-card"><div class="claim">{html.escape(item.claim)}</div>'
            f'<div class="evidence">{html.escape(item.evidence)}'
            + (f" · reference range {html.escape(item.reference_range)}" if item.reference_range else "")
            + "</div></div>",
            unsafe_allow_html=True,
        )


def render_interaction_warnings(warnings) -> None:
    if not warnings:
        return
    st.markdown("**Interaction warnings** — confirm with a pharmacist or doctor")
    for w in warnings:
        color = _SEVERITY_INFO.get(w.severity, "#8DA0B5")
        st.markdown(
            f'<div class="ma-card">{_badge(w.severity, color)} '
            f'<b>{html.escape(w.drug_a)} + {html.escape(w.drug_b)}</b><br>'
            f'<span class="evidence">{html.escape(w.note)}</span></div>',
            unsafe_allow_html=True,
        )


def render_timeline(events) -> None:
    if not events:
        return
    st.markdown("**Clinical timeline**")
    for e in events:
        new_txt = "; ".join(e.new_since_previous) if e.new_since_previous else "no change from previous report"
        st.markdown(
            f'<div class="ma-card"><b>{html.escape(e.report_filename)}</b> '
            f'<span class="evidence">· {html.escape(str(e.uploaded_at))}</span><br>'
            f'<span class="evidence">{html.escape(new_txt)}</span></div>',
            unsafe_allow_html=True,
        )


def render_result_details(result) -> None:
    with st.expander("🔍 Details & evidence"):
        render_execution_timeline(result.execution_log)
        if result.entities:
            st.divider()
            render_entities(result.entities)
        if result.summary and result.summary.evidence:
            st.divider()
            render_evidence(result.summary)
        if result.interaction_warnings:
            st.divider()
            render_interaction_warnings(result.interaction_warnings)
        if result.timeline:
            st.divider()
            render_timeline(result.timeline)


def render_download_button(path: str, key: str) -> None:
    try:
        with open(path, "rb") as f:
            st.download_button("⬇️ Download report PDF", f.read(), file_name=path.split("/")[-1], mime="application/pdf", key=key)
    except FileNotFoundError:
        st.caption("(Report file no longer available on disk.)")


# --------------------------------------------------------------------------
# Onboarding empty state
# --------------------------------------------------------------------------
_EXAMPLE_PROMPTS = [
    "Summarize my report and explain abnormal values",
    "What is my HbA1c?",
    "Remind me to take Metformin every morning",
    "Are there any interactions between my medicines?",
]


def render_empty_state() -> None:
    st.markdown(
        '<div class="ma-step"><div class="ma-step-num">01</div>'
        '<div class="ma-step-text"><b>Upload a report</b> — PDF, in the sidebar. Extraction and entity '
        "recognition run automatically.</div></div>"
        '<div class="ma-step"><div class="ma-step-num">02</div>'
        '<div class="ma-step-text"><b>Ask in plain English</b> — the Planner Agent breaks your request into '
        "an ordered task list and runs the right specialist agents.</div></div>"
        '<div class="ma-step"><div class="ma-step-num">03</div>'
        '<div class="ma-step-text"><b>Review the evidence</b> — every claim traces back to the report text '
        "or a reference range, with an honest confidence level, not just a confident tone.</div></div>",
        unsafe_allow_html=True,
    )
    st.write("")
    st.caption("Try one of these:")
    cols = st.columns(2)
    for i, prompt_text in enumerate(_EXAMPLE_PROMPTS):
        with cols[i % 2]:
            if st.button(prompt_text, key=f"example_{i}", use_container_width=True):
                st.session_state.queued_prompt = prompt_text
                st.rerun()


def _last_execution_log():
    """Find the most recent assistant turn's execution log, if any — used to
    keep the top-of-page pipeline strip current between reruns."""
    for turn in reversed(st.session_state.get("chat_history", [])):
        if turn.get("result") is not None:
            return turn["result"].execution_log
    return None


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main() -> None:
    orch = get_orchestrator()
    render_sidebar(orch)

    st.markdown("## Ask MediAgent")
    st.markdown(_pipeline_html(_last_execution_log()), unsafe_allow_html=True)

    if not st.session_state.chat_history:
        render_empty_state()

    for turn in st.session_state.chat_history:
        with st.chat_message(turn["role"]):
            st.write(turn["content"])
            if turn["role"] == "assistant" and turn.get("result") is not None:
                render_result_details(turn["result"])
                if turn.get("result").report_file_path:
                    render_download_button(turn["result"].report_file_path, key=f"dl_{turn['content'][:20]}_{id(turn)}")

    queued = st.session_state.pop("queued_prompt", None)
    typed = st.chat_input("Ask about your report, set reminders, check interactions...")
    prompt = queued or typed

    if prompt:
        st.session_state.chat_history.append({"role": "user", "content": prompt, "result": None})

        with st.spinner("Planning and executing agents..."):
            try:
                result = orch.handle_request(prompt)
                st.session_state.chat_history.append({"role": "assistant", "content": result.final_response, "result": result})
            except MediAgentError as exc:
                st.session_state.chat_history.append({"role": "assistant", "content": f"Error: {exc}", "result": None})
        st.rerun()


if __name__ == "__main__":
    main()
