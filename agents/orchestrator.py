import json
from pathlib import Path

from agents.agent_loop import MODEL, run_agent
from logs import log
from tools import TOOLS, declare


def load_worker_agents(path: Path = Path(__file__).with_name("worker_agents.json")) -> dict:
    agents = json.loads(path.read_text())
    for agent_name, agent in agents.items():
        unknown = [t for t in agent["tools"] if t not in TOOLS]
        if unknown:
            raise ValueError(f"worker_agents.json: {agent_name} lists unknown tool(s) {unknown}")
    return agents


# CCAF objective 1.3 - Configure subagent invocation, context passing, and spawning: agent definition, each worker in worker_agents.json has a description, prompt and tools.
WORKER_AGENTS = load_worker_agents()


# CCAF objective 1.3 - Configure subagent invocation, context passing, and spawning: spawning, a tool call starts a subagent, like the Task tool.
def start_subagent(agent_name: str, task: str) -> dict:
    agent = WORKER_AGENTS[agent_name]
    log(f"    starting a new agent loop for {agent_name}")
    # CCAF objective 1.3 - Configure subagent invocation, context passing, and spawning: scope tools tightly, each subagent gets only the tools listed for it.
    tools = {name: TOOLS[name] for name in agent["tools"]}
    # CCAF objective 1.2 - Orchestrate multi-agent systems with coordinator-subagent patterns: manages errors. A failed subagent returns an error, not a crash.
    try:
        # CCAF objective 1.3 - Configure subagent invocation, context passing, and spawning: passing context, the subagent gets only the task string, not the coordinator's history.
        # CCAF objective 1.3 - Configure subagent invocation, context passing, and spawning: model per agent (practice extra), a worker can name a cheaper model in worker_agents.json.
        answer = run_agent(agent_name, agent["prompt"], tools, task, indent="    ", model=agent.get("model", MODEL))
    except Exception as error:
        return {"error": f"{agent_name} failed: {error}"}
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

# CCAF objective 1.2 - Orchestrate multi-agent systems with coordinator-subagent patterns: manages errors. The prompt tells Claude what to do when a subagent fails.
ORCHESTRATOR_PROMPT = (
    "You are a customer-support coordinator. You do not do the work yourself: "
    "delegate to your subagents, then combine their answers into one short reply for the customer. "
    "If a subagent returns an error, do not guess its answer: retry once with a clearer task, "
    "or tell the customer which part could not be checked."
)


# CCAF objective 1.2 - Orchestrate multi-agent systems with coordinator-subagent patterns: iterative refinement. A reviewer checks the answer before it is returned.
REVIEWER_PROMPT = (
    "You check a customer-support reply. Reply PASS if it fully answers the question "
    "using only facts from the tool results. Otherwise reply FAIL and say in one line what is missing."
)
MAX_REFINEMENTS = 2
# CCAF objective 1.3 - Configure subagent invocation, context passing, and spawning: model per agent (practice extra), the coordinator and the reviewer each name their model too.
ORCHESTRATOR_MODEL = MODEL
REVIEWER_MODEL = MODEL


def run_orchestrator(question: str) -> str:
    answer = run_agent("orchestrator", ORCHESTRATOR_PROMPT, ORCHESTRATOR_TOOLS, question, model=ORCHESTRATOR_MODEL)
    for round_number in range(1, MAX_REFINEMENTS + 1):
        # CCAF objective 1.2 - Orchestrate multi-agent systems with coordinator-subagent patterns: iterative refinement. Check the answer. If it falls short, re-delegate with the gap.
        verdict = run_agent("reviewer", REVIEWER_PROMPT, {}, f"Question: {question}\nAnswer: {answer}", indent="  ", model=REVIEWER_MODEL)
        if verdict.startswith("PASS"):
            break
        log(f"refinement {round_number}: reviewer said {verdict}")
        answer = run_agent(
            "orchestrator",
            ORCHESTRATOR_PROMPT,
            ORCHESTRATOR_TOOLS,
            f"{question}\nYour previous answer: {answer}\nA reviewer found a gap: {verdict}\n"
            "Delegate again to fill the gap, then reply with the full corrected answer.",
            model=ORCHESTRATOR_MODEL,
        )
    return answer
