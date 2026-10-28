"""
Step 01 - The agentic loop (CCAF 1.1)

ONE agent, TWO tools, ONE hand-written loop.
Watch the four steps repeat:  Perceive -> Reason -> Act -> Observe

Run:
    export GEMINI_API_KEY=your-free-key
    python steps/01-agentic-loop/main.py "Where is my order 9931?"
"""

import os
import sys

from google import genai
from google.genai import types

# ---------------------------------------------------------------------------
# 1. Settings
# ---------------------------------------------------------------------------
# Model name can be changed with an env var; default is the free Flash-Lite.
MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")

# Safety cap: stop after this many loop turns even if the model never finishes.
# (CCAF anti-pattern: a loop with no end condition.)
MAX_TURNS = 5

# ---------------------------------------------------------------------------
# 2. Fake data - a tiny in-memory "database" so no real system is needed
# ---------------------------------------------------------------------------
ORDERS = {
    "9931": {"item": "Headphones", "status": "shipped", "carrier": "BlueDart"},
    "4471": {"item": "Laptop stand", "status": "processing", "carrier": None},
}

# ---------------------------------------------------------------------------
# 3. The two tools - plain Python functions the agent can ask us to run
# ---------------------------------------------------------------------------
def look_up_order(order_id: str) -> dict:
    """Return the order record, or a 'not found' answer."""
    order = ORDERS.get(order_id)
    if order is None:
        return {"found": False}
    return {"found": True, **order}


def track_shipment(order_id: str) -> dict:
    """Return where a shipped parcel is right now."""
    order = ORDERS.get(order_id)
    if order is None or order["status"] != "shipped":
        return {"tracking": "No shipment yet"}
    return {"tracking": f"With {order['carrier']}, out for delivery today"}


# Map tool name -> Python function, so the loop can run whatever the model asks for.
TOOL_FUNCTIONS = {
    "look_up_order": look_up_order,
    "track_shipment": track_shipment,
}

# ---------------------------------------------------------------------------
# 4. Tool descriptions - this is ALL the model sees about our tools (CCAF 2.1)
# ---------------------------------------------------------------------------
TOOL_DECLARATIONS = [
    types.FunctionDeclaration(
        name="look_up_order",
        description="Get an order's item and status by order id. Use this first for any order question.",
        parameters_json_schema={
            "type": "object",
            "properties": {"order_id": {"type": "string", "description": "e.g. '9931'"}},
            "required": ["order_id"],
        },
    ),
    types.FunctionDeclaration(
        name="track_shipment",
        description="Get the live delivery location of an order. Use only when the order status is 'shipped'.",
        parameters_json_schema={
            "type": "object",
            "properties": {"order_id": {"type": "string", "description": "e.g. '9931'"}},
            "required": ["order_id"],
        },
    ),
]

SYSTEM_PROMPT = "You are an order-support agent. Use the tools to answer. Be brief."


# ---------------------------------------------------------------------------
# 5. The agentic loop
# ---------------------------------------------------------------------------
def run_agent(user_request: str) -> str:
    client = genai.Client()  # reads GEMINI_API_KEY from the environment

    # The conversation so far. The model has NO memory between calls,
    # so we resend this whole list every turn.
    contents = [types.Content(role="user", parts=[types.Part(text=user_request)])]

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=[types.Tool(function_declarations=TOOL_DECLARATIONS)],
    )

    for turn in range(1, MAX_TURNS + 1):
        print(f"\n--- turn {turn} ---")

        # PERCEIVE + REASON: the model reads the whole conversation and decides.
        response = client.models.generate_content(model=MODEL, contents=contents, config=config)

        # Keep the model's reply in the history (includes any tool requests).
        contents.append(response.candidates[0].content)

        # Gemini's version of Claude's stop_reason check:
        #   tool requested  -> keep looping   (Claude: stop_reason == "tool_use")
        #   no tool request -> we're done     (Claude: stop_reason == "end_turn")
        if not response.function_calls:
            print("Model finished (Claude would say stop_reason = end_turn)")
            return response.text

        print("Model wants tools (Claude would say stop_reason = tool_use)")

        # ACT: the model only ASKED for tools. Our code actually runs them.
        result_parts = []
        for call in response.function_calls:
            result = TOOL_FUNCTIONS[call.name](**call.args)
            print(f"  ACT     {call.name}({dict(call.args)})")
            print(f"  OBSERVE {result}")
            result_parts.append(types.Part.from_function_response(name=call.name, response=result))

        # OBSERVE: send the results back so the model sees them next turn.
        # (CCAF anti-pattern: forgetting this step - the model never learns the result.)
        contents.append(types.Content(role="user", parts=result_parts))

    return "Stopped: hit MAX_TURNS without a final answer."


# ---------------------------------------------------------------------------
# 6. Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    question = sys.argv[1] if len(sys.argv) > 1 else "Where is my order 9931?"
    print(f"USER: {question}")
    print(f"\nFINAL ANSWER: {run_agent(question)}")
