"""
tool_hooks.py - code that runs automatically around every tool call (CCAF 1.5).

A prompt rule is followed most of the time. A hook is followed every time,
because our code runs it - the model cannot skip it.

Two events (moments in the loop), each with its own job:
    PreToolUse   - BEFORE a tool runs. Guards what goes out: can BLOCK the call.
    PostToolUse  - AFTER a tool runs, before the model sees the result. Shapes what comes back: can CHANGE it.

How it is organized (same shape as Claude's Agent SDK hooks):
    rule functions       - one small function per business rule, named by WHAT it checks or changes
    HOOKS                - the registry: WHEN to run each rule (event) and for WHICH tool (matcher)
    run_pre_tool_use()   - runner for PreToolUse rules, called by agent_loop.py before every tool
    run_post_tool_use()  - runner for PostToolUse rules, called by agent_loop.py after every tool

To add a rule: write one function, add one line to HOOKS. agent_loop.py never changes.
"""

from tools import ORDERS


# ---------------------------------------------------------------------------
# PreToolUse rules - get the tool's arguments; return a reason to block, or None to allow
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
# PostToolUse rules - get the tool's result; return a changed COPY, or None for "no change"
# ---------------------------------------------------------------------------
def hide_customer_email(result: dict) -> dict | None:
    """Private data never reaches the model: replace the email before the model reads the result."""
    if "customer_email" not in result:
        return None
    return {**result, "customer_email": "***"}


# ---------------------------------------------------------------------------
# Registry - event -> list of (matcher, rule). Matcher = a tool name, or "*" for every tool.
# ---------------------------------------------------------------------------
HOOKS = {
    "PreToolUse": [
        ("issue_refund", refund_not_above_price),
    ],
    "PostToolUse": [
        ("*", hide_customer_email),
    ],
}


def rules_for(event: str, tool_name: str) -> list:
    """The rules registered for this event whose matcher fits this tool, in registration order."""
    return [rule for matcher, rule in HOOKS.get(event, []) if matcher in (tool_name, "*")]


# ---------------------------------------------------------------------------
# Runners - called by agent_loop.py for every tool call
# ---------------------------------------------------------------------------
def run_pre_tool_use(tool_name: str, args: dict) -> str | None:
    """Run the PreToolUse rules. The first one that blocks wins; the tool will not run."""
    for rule in rules_for("PreToolUse", tool_name):
        blocked = rule(args)
        if blocked:
            return blocked
    return None  # no rule objected: allow


def run_post_tool_use(tool_name: str, result: dict) -> dict:
    """Run the PostToolUse rules in order. Each one gets the result the previous one left."""
    for rule in rules_for("PostToolUse", tool_name):
        result = rule(result) or result  # None means "no change": keep the result as it is
    return result
