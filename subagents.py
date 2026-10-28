"""
subagents.py - the 2 worker agents (CCAF 1.3).

An AGENT = a model + a system prompt + its own tools, running the loop in loop.py.
This file only DEFINES the agents. It doesn't start them; the orchestrator does that.

    order_agent    tools: look_up_order, track_shipment
    refund_agent   tools: check_refund_policy, issue_refund
"""

from tools import TOOLS

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
