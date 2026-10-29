"""
main.py - the only entry point.

Run:
    export GEMINI_API_KEY=your-free-key
    python main.py "Order 9931 arrived broken. Where is it and can I get a refund?"
"""

import sys

from logs import log
from agents.orchestrator import run_orchestrator


def main() -> None:
    question = sys.argv[1] if len(sys.argv) > 1 else "Order 9931 arrived broken. Where is it and can I get a refund?"
    log(f"USER: {question}")
    answer = run_orchestrator(question)
    log(f"FINAL ANSWER: {answer}")


if __name__ == "__main__":
    main()
