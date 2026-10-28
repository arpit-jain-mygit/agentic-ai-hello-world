"""
main.py - the only entry point.

Run:
    export GEMINI_API_KEY=your-free-key
    python main.py "Order 9931 arrived broken. Where is it and can I get a refund?"
"""

import sys

from agents import run_orchestrator

if __name__ == "__main__":
    question = sys.argv[1] if len(sys.argv) > 1 else "Order 9931 arrived broken. Where is it and can I get a refund?"
    print(f"main.py   | USER: {question}")
    answer = run_orchestrator(question)
    print(f"main.py   | FINAL ANSWER: {answer}")
