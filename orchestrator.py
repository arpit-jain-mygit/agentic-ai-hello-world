"""
orchestrator.py - the coordinator agent (CCAF 1.2, 1.3).

The orchestrator is an agent too, but it does no work itself. Its only tools are
"delegation tools" (ask_order_agent, ask_refund_agent): calling one starts a subagent.

    orchestrator   tools: ask_order_agent, ask_refund_agent
"""

from loop import run_agent
from subagents import SUBAGENTS
from tools import declare

# ---------------------------------------------------------------------------
# Delegation tools - the bridge between the orchestrator and the subagents.
# To the orchestrator's model, ask_<agent> is just a tool (call in, answer out).
# Inside, it runs that subagent's whole loop and returns its final answer.
# (Claude's Task / Agent tool works the same way.)
# ---------------------------------------------------------------------------
def delegation_tool(agent_name: str):
    agent = SUBAGENTS[agent_name]

    def ask_agent(task: str) -> dict:
        print(f"{'orchestrator.py':<15} |     ask_{agent_name}: starting a new agent loop for {agent_name}")
        answer = run_agent(agent_name, agent["prompt"], agent["tools"], task, indent="    ")
        return {"answer": answer}

    declaration = declare(
        f"ask_{agent_name}",
        agent["description"] + " Pass a complete task: the subagent knows nothing else.",
        task="string",
        reason="string",  # makes the model say WHY it picked this agent (printed as "why:" in the log)
    )
    return ask_agent, declaration


# ---------------------------------------------------------------------------
# The orchestrator agent itself
# ---------------------------------------------------------------------------
ORCHESTRATOR_PROMPT = (
    "You are a customer-support coordinator. You do not do the work yourself: "
    "delegate to your subagents, then combine their answers into one short reply for the customer."
)
ORCHESTRATOR_TOOLS = {f"ask_{name}": delegation_tool(name) for name in SUBAGENTS}


def run_orchestrator(question: str) -> str:
    """Start the orchestrator. It starts the subagents itself when its model decides to."""
    return run_agent("orchestrator", ORCHESTRATOR_PROMPT, ORCHESTRATOR_TOOLS, question)
