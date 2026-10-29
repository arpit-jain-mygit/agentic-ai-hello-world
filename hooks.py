"""
hooks.py - code that runs automatically around every tool call (CCAF 1.5).

A prompt rule is followed most of the time. A hook is followed every time,
because our code runs it - the model cannot skip it.

How it is organized (same shape as Claude's Agent SDK hooks):
    rule functions  - one small function per business rule, named by WHAT it checks
    HOOKS           - the registry: WHEN to run each rule (event) and for WHICH tool (matcher)
    run_hooks()     - the generic runner agent_loop.py calls; it knows no rule by name

To add a rule: write one function, add one line to HOOKS. agent_loop.py never changes.
"""

from tools import ORDERS


# ---------------------------------------------------------------------------
# Rules - each gets the tool's arguments and returns a reason to block, or None to allow
# ---------------------------------------------------------------------------
def refund_not_above_price(args: dict) -> str | None:
    """A refund can never be more than what the customer paid."""
    order = ORDERS.get(args.get("order_id"))
    if order is None:
        return f"unknown order {args.get('order_id')}"
    if args.get("amount", 0) > order["price"]:
        return f"amount {args['amount']} is more than the order price {order['price']}"
    return None


# ---------------------------------------------------------------------------
# Registry - event -> list of (matcher, rule). Matcher = a tool name, or "*" for every tool.
#   PreToolUse = just before a tool runs (can block it)
# ---------------------------------------------------------------------------
HOOKS = {
    "PreToolUse": [
        ("issue_refund", refund_not_above_price),
    ],
}


# ---------------------------------------------------------------------------
# Runner - called by agent_loop.py for every tool call
# ---------------------------------------------------------------------------
def run_hooks(event: str, tool_name: str, args: dict) -> str | None:
    """Run every rule registered for this event and tool. The first one that blocks wins."""
    for matcher, rule in HOOKS.get(event, []):
        if matcher in (tool_name, "*"):     # is this rule meant for this tool?
            blocked = rule(args)
            if blocked:
                return blocked              # stop here: the tool will not run
    return None                             # no rule objected: allow
