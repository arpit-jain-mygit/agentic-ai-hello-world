"""
agents.py - the 3 agents: one orchestrator and two subagents (CCAF 1.2, 1.3).

    Orchestrator   tools: ask_order_agent, ask_refund_agent   (each one starts a subagent)
     |-- order_agent    tools: look_up_order, track_shipment
     |-- refund_agent   tools: check_refund_policy, issue_refund
"""

from loop import run_agent
from tools import TOOLS, declare

# ---------------------------------------------------------------------------
# Subagent definitions - written by YOU, the developer
#   description -> how the orchestrator decides WHEN to use this agent
#   prompt      -> how the agent behaves
#   tools       -> ONLY the tools this role needs (scoped, least privilege)
# ---------------------------------------------------------------------------
SUBAGENTS = {
    "order_agent": {
        "description": "Answers questions about an order's details and delivery status.",
        "prompt": "You are the order agent. Use your tools, then reply with the facts only.",
        "tools": {n: TOOLS[n] for n in ["look_up_order", "track_shipment"]},
    },
    "refund_agent": {
        "description": "Checks refund eligibility and issues refunds.",
        "prompt": "You are the refund agent. Always check the policy before issuing a refund. Reply with the outcome.",
        "tools": {n: TOOLS[n] for n in ["check_refund_policy", "issue_refund"]},
    },
}


# ---------------------------------------------------------------------------
# Spawn tools - how the orchestrator starts a subagent.
# To the orchestrator this is just a tool; inside, it runs a whole new agent loop
# and returns that agent's final answer as the tool result. (Like Claude's Task tool.)
# ---------------------------------------------------------------------------
def spawn_tool(agent_name: str):
    agent = SUBAGENTS[agent_name]

    def spawn(task: str) -> dict:
        answer = run_agent(agent_name, agent["prompt"], agent["tools"], task, indent="    ")
        return {"answer": answer}

    declaration = declare(
        f"ask_{agent_name}",
        agent["description"] + " Pass a complete task: the subagent knows nothing else.",
        task="string",
        reason="string",  # makes the model say WHY it picked this agent (printed as "why:" in the log)
    )
    return spawn, declaration


# ---------------------------------------------------------------------------
# The orchestrator - an agent whose only tools are the spawn tools
# ---------------------------------------------------------------------------
ORCHESTRATOR_PROMPT = (
    "You are a customer-support coordinator. You do not do the work yourself: "
    "delegate to your subagents, then combine their answers into one short reply for the customer."
)
ORCHESTRATOR_TOOLS = {f"ask_{name}": spawn_tool(name) for name in SUBAGENTS}


def run_orchestrator(question: str) -> str:
    """Start the orchestrator. It starts the subagents itself when its model decides to."""
    return run_agent("orchestrator", ORCHESTRATOR_PROMPT, ORCHESTRATOR_TOOLS, question)
