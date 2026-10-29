"""
agents/orchestrator.py - the coordinator agent (CCAF 1.2, 1.3).

The orchestrator is an agent too, but it does no work itself. Its only tools are
"delegation tools" (ask_order_agent, ask_refund_agent): calling one starts a subagent.

    orchestrator   tools: ask_order_agent, ask_refund_agent
"""

import json
from pathlib import Path

from agents.agent_loop import run_agent
from logs import log
from tools import TOOLS, declare

# ---------------------------------------------------------------------------
# Worker agents - loaded from worker_agents.json (config, not code).
# Each entry: description (when to use it), prompt (how it behaves), tools (tool NAMES).
# Claude Code defines subagents the same way, as config files in .claude/agents/.
# ---------------------------------------------------------------------------
def load_worker_agents(path: Path = Path(__file__).with_name("worker_agents.json")) -> dict:
    """Read worker_agents.json and check every tool name in it exists in tools/functions.py."""
    agents = json.loads(path.read_text())
    for agent_name, agent in agents.items():
        unknown = [t for t in agent["tools"] if t not in TOOLS]
        if unknown:  # fail fast on a typo, instead of mid-run
            raise ValueError(f"worker_agents.json: {agent_name} lists unknown tool(s) {unknown}")
    return agents


WORKER_AGENTS = load_worker_agents()

# ---------------------------------------------------------------------------
# Delegation tools - the orchestrator's 2 tools.
# To the orchestrator's model these are ordinary tools (call in, answer out).
# The only difference from a plain tool: their body starts a whole subagent.
# (Claude's Task / Agent tool works the same way.)
# ---------------------------------------------------------------------------
def start_subagent(agent_name: str, task: str) -> dict:
    """Run a subagent's full loop on the task and return its final answer."""
    agent = WORKER_AGENTS[agent_name]
    log(f"    starting a new agent loop for {agent_name}")
    tools = {name: TOOLS[name] for name in agent["tools"]}  # tool names -> real Python functions
    answer = run_agent(agent_name, agent["prompt"], tools, task, indent="    ")
    return {"answer": answer}


def ask_order_agent(task: str) -> dict:  # this tool's body starts a whole agent
    """Delegation tool: hand a task to the order agent."""
    return start_subagent("order_agent", task)


def ask_refund_agent(task: str) -> dict:  # this tool's body starts a whole agent
    """Delegation tool: hand a task to the refund agent."""
    return start_subagent("refund_agent", task)


# What the orchestrator's model is told about these 2 tools.
# The description comes from the subagent's definition, so it knows WHEN to use each one.
# "reason" makes the model say WHY it picked that agent (printed as "why:" in the log).
HANDOFF_HINT = " Pass a complete task: the subagent knows nothing else."
ORCHESTRATOR_TOOLS = {
    "ask_order_agent": (
        ask_order_agent,
        declare("ask_order_agent", WORKER_AGENTS["order_agent"]["description"] + HANDOFF_HINT, task="string", reason="string"),
    ),
    "ask_refund_agent": (
        ask_refund_agent,
        declare("ask_refund_agent", WORKER_AGENTS["refund_agent"]["description"] + HANDOFF_HINT, task="string", reason="string"),
    ),
}


# ---------------------------------------------------------------------------
# The orchestrator agent itself
# ---------------------------------------------------------------------------
ORCHESTRATOR_PROMPT = (
    "You are a customer-support coordinator. You do not do the work yourself: "
    "delegate to your subagents, then combine their answers into one short reply for the customer."
)


def run_orchestrator(question: str) -> str:
    """Start the orchestrator. It starts the subagents itself when its model decides to."""
    return run_agent("orchestrator", ORCHESTRATOR_PROMPT, ORCHESTRATOR_TOOLS, question)
