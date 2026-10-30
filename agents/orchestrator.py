import json
from pathlib import Path

from agents.agent_loop import run_agent
from logs import log
from tools import TOOLS, declare


def load_worker_agents(path: Path = Path(__file__).with_name("worker_agents.json")) -> dict:
    agents = json.loads(path.read_text())
    for agent_name, agent in agents.items():
        unknown = [t for t in agent["tools"] if t not in TOOLS]
        if unknown:
            raise ValueError(f"worker_agents.json: {agent_name} lists unknown tool(s) {unknown}")
    return agents


WORKER_AGENTS = load_worker_agents()


def start_subagent(agent_name: str, task: str) -> dict:
    agent = WORKER_AGENTS[agent_name]
    log(f"    starting a new agent loop for {agent_name}")
    tools = {name: TOOLS[name] for name in agent["tools"]}
    answer = run_agent(agent_name, agent["prompt"], tools, task, indent="    ")
    return {"answer": answer}


def ask_order_agent(task: str) -> dict:
    return start_subagent("order_agent", task)


def ask_refund_agent(task: str) -> dict:
    return start_subagent("refund_agent", task)


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

ORCHESTRATOR_PROMPT = (
    "You are a customer-support coordinator. You do not do the work yourself: "
    "delegate to your subagents, then combine their answers into one short reply for the customer."
)


def run_orchestrator(question: str) -> str:
    return run_agent("orchestrator", ORCHESTRATOR_PROMPT, ORCHESTRATOR_TOOLS, question)
