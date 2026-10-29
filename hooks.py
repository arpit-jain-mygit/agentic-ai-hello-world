"""
hooks.py - code that runs automatically around every tool call (CCAF 1.5).

A prompt rule is followed most of the time. A hook is followed every time,
because our code runs it - the model cannot skip it.

    PreToolUse: runs BEFORE a tool. It can allow the call or block it.
"""

from tools import ORDERS


def pre_tool_use(tool_name: str, args: dict) -> str | None:
    """
    Check a tool call before it runs.
    Returns None to allow it, or a reason string to block it.
    """
    # Rule: a refund can never be more than what the customer paid.
    if tool_name == "issue_refund":
        order = ORDERS.get(args.get("order_id"))
        if order is None:
            return f"unknown order {args.get('order_id')}"
        if args.get("amount", 0) > order["price"]:
            return f"amount {args['amount']} is more than the order price {order['price']}"
    return None  # every other call is allowed
