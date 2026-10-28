"""
Step 02 - Orchestrator + 2 subagents (CCAF 1.2 and 1.3)

  Orchestrator  (its tools = "spawn a subagent", like Claude's Task tool)
   |-- Order agent   -> look_up_order, track_shipment
   |-- Refund agent  -> check_refund_policy, issue_refund

Every agent runs the SAME loop from step 01. Subagents start with a blank,
isolated context: they only know the task text the orchestrator gives them.

Run:
    export GEMINI_API_KEY=your-free-key
    python steps/02-orchestrator-subagents/main.py "Order 9931 arrived broken. Where is it and can I get a refund?"
"""

import os
import sys

from google import genai
from google.genai import types

# ---------------------------------------------------------------------------
# 1. Settings
# ---------------------------------------------------------------------------
MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
MAX_TURNS = 5  # safety cap for every agent's loop

client = genai.Client()  # reads GEMINI_API_KEY from the environment

# ---------------------------------------------------------------------------
# 2. Fake data
# ---------------------------------------------------------------------------
ORDERS = {
    "9931": {"item": "Headphones", "price": 120, "status": "delivered", "days_since_delivery": 3},
    "4471": {"item": "Laptop stand", "price": 40, "status": "processing", "days_since_delivery": None},
}

# ---------------------------------------------------------------------------
# 3. The 4 worker tools (2 per subagent)
# ---------------------------------------------------------------------------
def look_up_order(order_id: str) -> dict:
    order = ORDERS.get(order_id)
    return {"found": False} if order is None else {"found": True, **order}


def track_shipment(order_id: str) -> dict:
    order = ORDERS.get(order_id)
    if order is None:
        return {"tracking": "Unknown order"}
    return {"tracking": f"Status: {order['status']}"}


def check_refund_policy(order_id: str) -> dict:
    order = ORDERS.get(order_id)
    if order is None or order["days_since_delivery"] is None:
        return {"eligible": False, "reason": "Not delivered yet"}
    return {"eligible": order["days_since_delivery"] <= 30, "rule": "Refunds allowed within 30 days of delivery"}


def issue_refund(order_id: str, amount: float) -> dict:
    return {"refunded": True, "order_id": order_id, "amount": amount}


# Small helper so tool declarations stay short: every tool here takes string/number args.
def declare(name: str, description: str, **params: str) -> types.FunctionDeclaration:
    """params maps arg name -> JSON type, e.g. order_id="string"."""
    return types.FunctionDeclaration(
        name=name,
        description=description,
        parameters_json_schema={
            "type": "object",
            "properties": {p: {"type": t} for p, t in params.items()},
            "required": list(params),
        },
    )


# ---------------------------------------------------------------------------
# 4. Subagent definitions - written by YOU, the developer (CCAF 1.3)
#    description -> how the orchestrator decides WHEN to use this agent
#    prompt      -> how the agent behaves
#    tools       -> ONLY the tools this role needs (scoped, least privilege)
# ---------------------------------------------------------------------------
SUBAGENTS = {
    "order_agent": {
        "description": "Answers questions about an order's details and delivery status.",
        "prompt": "You are the order agent. Use your tools, then reply with the facts only.",
        "tools": {
            "look_up_order": (look_up_order, declare("look_up_order", "Get an order's item, price and status.", order_id="string")),
            "track_shipment": (track_shipment, declare("track_shipment", "Get the delivery status of an order.", order_id="string")),
        },
    },
    "refund_agent": {
        "description": "Checks refund eligibility and issues refunds.",
        "prompt": "You are the refund agent. Always check the policy before issuing a refund. Reply with the outcome.",
        "tools": {
            "check_refund_policy": (check_refund_policy, declare("check_refund_policy", "Check if an order can be refunded.", order_id="string")),
            "issue_refund": (issue_refund, declare("issue_refund", "Refund an order. Only after the policy says eligible.", order_id="string", amount="number")),
        },
    },
}


# ---------------------------------------------------------------------------
# 5. ONE generic agentic loop, used by the orchestrator AND both subagents
#    tools = {name: (python_function, declaration)}
# ---------------------------------------------------------------------------
def run_agent(name: str, system_prompt: str, tools: dict, task: str, indent: str = "") -> str:
    print(f"{indent}[{name}] task: {task}")

    # Fresh, isolated context: this agent sees ONLY its own task.
    contents = [types.Content(role="user", parts=[types.Part(text=task)])]
    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        tools=[types.Tool(function_declarations=[decl for _, decl in tools.values()])],
    )

    for _ in range(MAX_TURNS):
        # PERCEIVE + REASON
        response = client.models.generate_content(model=MODEL, contents=contents, config=config)
        contents.append(response.candidates[0].content)

        # No tool requested = done (Claude: stop_reason == "end_turn")
        if not response.function_calls:
            print(f"{indent}[{name}] done: {response.text.strip()}")
            return response.text

        # ACT: run each requested tool (Claude: stop_reason == "tool_use")
        result_parts = []
        for call in response.function_calls:
            func, _ = tools[call.name]
            print(f"{indent}[{name}] calls {call.name}({dict(call.args)})")
            result = func(**call.args)
            result_parts.append(types.Part.from_function_response(name=call.name, response=result))

        # OBSERVE: feed results back for the next turn
        contents.append(types.Content(role="user", parts=result_parts))

    return f"{name} stopped: hit MAX_TURNS"


# ---------------------------------------------------------------------------
# 6. The orchestrator's tools: one "spawn" tool per subagent.
#    Calling it starts a whole new agent loop; that agent's final answer
#    comes back as this tool's result. (Claude's Task/Agent tool works the same way.)
# ---------------------------------------------------------------------------
def make_spawn_tool(agent_name: str):
    agent = SUBAGENTS[agent_name]

    def spawn(task: str) -> dict:
        answer = run_agent(agent_name, agent["prompt"], agent["tools"], task, indent="    ")
        return {"answer": answer}

    declaration = declare(
        f"ask_{agent_name}",
        agent["description"] + " Pass a complete task: the subagent knows nothing else.",
        task="string",
    )
    return spawn, declaration


ORCHESTRATOR_TOOLS = {f"ask_{n}": make_spawn_tool(n) for n in SUBAGENTS}

ORCHESTRATOR_PROMPT = (
    "You are a customer-support coordinator. You do not do the work yourself: "
    "delegate to your subagents, then combine their answers into one short reply for the customer."
)


# ---------------------------------------------------------------------------
# 7. Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    question = sys.argv[1] if len(sys.argv) > 1 else "Order 9931 arrived broken. Where is it and can I get a refund?"
    print(f"USER: {question}\n")
    # Only the orchestrator is started here. It starts the other 2 agents itself,
    # at runtime, when its model calls ask_order_agent / ask_refund_agent
    # (each of those calls run_agent() again, inside spawn()). Total: 3 agents.
    final = run_agent("orchestrator", ORCHESTRATOR_PROMPT, ORCHESTRATOR_TOOLS, question)
    print(f"\nFINAL ANSWER: {final}")
