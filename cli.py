"""
cli.py

Headless CLI demo path — zero-dependency fallback if a live Streamlit
demo ever misbehaves mid-viva. Same Orchestrator, same agents, same
database; just a terminal loop instead of a browser.

Usage:
    python cli.py                      # interactive chat loop
    python cli.py --pdf report.pdf     # load a report first, then chat
"""

from __future__ import annotations

import argparse
import sys

from agents.orchestrator import Orchestrator
from llm import get_llm_provider
from tools.database import Repository
from tools.pdf_reader import extract_text_from_pdf
from utils.exceptions import MediAgentError
from utils.logger import get_logger

logger = get_logger(__name__)


def print_execution_log(execution_log) -> None:
    print("  Execution timeline:")
    for step in execution_log:
        marker = {"done": "✔", "failed": "✘", "pending": "…", "running": "…", "skipped": "-"}[step.status.value]
        gov = f" [{step.autonomy.value}/{step.risk_tier.value}]" if step.autonomy and step.risk_tier else ""
        print(f"    [{marker}] {step.agent_name}{gov}: {step.detail} ({step.duration_ms} ms)")


def main() -> None:
    parser = argparse.ArgumentParser(description="MediAgent CLI")
    parser.add_argument("--pdf", help="Path to a medical report PDF to load at startup")
    args = parser.parse_args()

    repo = Repository()
    patient = repo.get_or_create_default_patient()
    orch = Orchestrator(repo, patient.id)

    print("=" * 70)
    print(" MediAgent — Agentic AI for Multi-Step Healthcare Task Automation")
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
