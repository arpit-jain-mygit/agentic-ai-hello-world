"""
main.py - the only entry point. Runs one worker agent on a question.

Run:
    export GEMINI_API_KEY=your-free-key
    python main.py order_agent "Where is order 9931?"
    python main.py refund_agent "Refund order 9931, it arrived broken."
"""

import json
import sys
from pathlib import Path

from agents.agent_loop import run_agent
from logs import log
from tools import TOOLS

WORKER_AGENTS = json.loads((Path(__file__).parent / "agents" / "worker_agents.json").read_text())


def main() -> None:
    name = sys.argv[1] if len(sys.argv) > 1 else "order_agent"
    question = sys.argv[2] if len(sys.argv) > 2 else "Order 9931 arrived broken. Where is it?"
    if name not in WORKER_AGENTS:
        sys.exit(f"Unknown agent '{name}'. Choose one of: {', '.join(WORKER_AGENTS)}")

    agent = WORKER_AGENTS[name]
    tools = {tool: TOOLS[tool] for tool in agent["tools"]}  # tool names -> real Python functions
    log(f"USER: {question}")
    answer = run_agent(name, agent["prompt"], tools, question)
    log(f"FINAL ANSWER: {answer}")


if __name__ == "__main__":
    main()
