"""
cli.py

Headless CLI demo path — zero-dependency fallback if the React/FastAPI
stack ever misbehaves mid-viva. Same Orchestrator, same agents, just a
terminal loop instead of a browser.

Usage:
    python cli.py                              # Postgres, a CLI demo patient
    python cli.py --mode sqlite                 # legacy offline SQLite path
    python cli.py --patient-id 3                # Postgres, a specific patient
    python cli.py --pdf report.pdf               # load a report first, then chat

`--mode sqlite` preserves the original zero-infra, zero-setup offline demo
exactly as it worked before v3 (tools/database.py, unmodified). `--mode
postgres` (the default) talks to the same database the FastAPI backend
uses — handy for debugging a specific patient's session without a browser.
"""

from __future__ import annotations

import argparse
import sys

if hasattr(sys.stdout, "reconfigure"):
    # Windows terminals often default to cp1252, which can't encode the
    # ✔/✘ markers below — force UTF-8 rather than picking ASCII fallbacks.
    sys.stdout.reconfigure(encoding="utf-8")

from agents.orchestrator import Orchestrator
from llm import get_llm_provider
from tools.pdf_reader import extract_text_from_pdf
from utils.exceptions import MediAgentError
from utils.logger import get_logger

logger = get_logger(__name__)


def _sqlite_repo_and_patient():
    from tools.database import Repository

    repo = Repository()
    patient = repo.get_or_create_default_patient()
    return repo, patient.id


def _postgres_repo_and_patient(patient_id: int | None):
    from backend.db import SessionLocal
    from backend.pg_repository import PgRepository

    db = SessionLocal()
    repo = PgRepository(db)

    if patient_id is not None:
        patient = repo.get_patient(patient_id)
        if patient is None:
            print(f"No patient with id={patient_id} found in Postgres.")
            sys.exit(1)
        return repo, patient.id

    demo = next((p for p in repo.list_all_patients() if p.name == "CLI Demo Patient"), None)
    if demo is None:
        demo = repo.create_patient(name="CLI Demo Patient")
        print(f"Created a CLI demo patient (id={demo.id}, unlinked to any login) for this session.")
    return repo, demo.id


def print_execution_log(execution_log) -> None:
    print("  Execution timeline:")
    for step in execution_log:
        marker = {"done": "✔", "failed": "✘", "pending": "…", "running": "…", "skipped": "-"}[step.status.value]
        gov = f" [{step.autonomy.value}/{step.risk_tier.value}]" if step.autonomy and step.risk_tier else ""
        print(f"    [{marker}] {step.agent_name}{gov}: {step.detail} ({step.duration_ms} ms)")


def main() -> None:
    parser = argparse.ArgumentParser(description="MediAgent CLI")
    parser.add_argument("--pdf", help="Path to a medical report PDF to load at startup")
    parser.add_argument(
        "--mode",
        choices=["postgres", "sqlite"],
        default="postgres",
        help="postgres (default): same DB as the FastAPI backend. sqlite: legacy offline-only path.",
    )
    parser.add_argument("--patient-id", type=int, default=None, help="Postgres mode only: use a specific patient id.")
    args = parser.parse_args()

    if args.mode == "sqlite":
        repo, patient_id = _sqlite_repo_and_patient()
    else:
        repo, patient_id = _postgres_repo_and_patient(args.patient_id)
    orch = Orchestrator(repo, patient_id)

    print("=" * 70)
    print(" MediAgent — Agentic AI for Multi-Step Healthcare Task Automation")
    print(f" mode: {args.mode}")
    print("=" * 70)
    try:
        print(f"LLM provider: {get_llm_provider().name}")
    except MediAgentError as exc:
        print(f"LLM provider error: {exc}")
        sys.exit(1)

    if args.pdf:
        try:
            text = extract_text_from_pdf(args.pdf)
            orch.load_report(text, args.pdf)
            print(f"Loaded report: {args.pdf} ({len(text)} characters)")
        except MediAgentError as exc:
            print(f"Failed to load PDF: {exc}")

    print("\nType a request (or 'quit' to exit). Examples:")
    print('  "Summarize my report and explain abnormal values"')
    print('  "What is my HbA1c?"')
    print('  "Remind me to take Metformin every morning"')
    print('  "Are there any interactions between my medicines?"')
    print('  "Show me the timeline of my reports" (needs 2+ uploads)')
    print('  "Generate a doctor report"\n')

    while True:
        try:
            user_input = input("You> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not user_input:
            continue
        if user_input.lower() in {"quit", "exit"}:
            print("Goodbye.")
            break

        try:
            result = orch.handle_request(user_input)
        except MediAgentError as exc:
            print(f"Error: {exc}")
            continue

        print(f"\nMediAgent> {result.final_response}\n")
        print_execution_log(result.execution_log)
        if result.report_file_path:
            print(f"  Report saved to: {result.report_file_path}")
        print()


if __name__ == "__main__":
    main()
