"""
CCAF 1.5 - PreToolUse hooks, registered in tool_hooks.py (HOOKS), run by the loop through run_pre_tool_use().
Rule enforced in CODE (not the prompt): a refund can never be more than the order's price.
Checks: over-price refund is blocked, the tool never runs, the model is told why; a valid refund still runs;
the loop runs ANY registered rule without knowing its name; matchers pick which tools a hook sees.
"""

import tool_hooks
from agent_loop import run_agent
from fake_gemini import last_tool_results, tool_call
from tools import TOOLS


def spy_tool(tool_name):
    """A tool's real declaration with a spy function, so the test knows if it really ran."""
    ran = []
    _, declaration = TOOLS[tool_name]
    return ran, {tool_name: (lambda **args: ran.append(args) or {"ok": True}, declaration)}


# ---------------------------------------------------------------------------
# The refund rule, through the real loop
# ---------------------------------------------------------------------------
def test_refund_over_price_is_blocked(gemini):
    gemini.script(tool_call("issue_refund", order_id="9931", amount=500), "Sorry, I can't refund $500.")
    ran, tools = spy_tool("issue_refund")

    run_agent("refund_agent", "prompt", tools, "Refund $500 for order 9931")

    assert ran == []                                      # the tool never ran
    result = last_tool_results(gemini.requests[1])["issue_refund"]
    assert result["blocked_by"] == "PreToolUse hook"      # the model is told it was blocked, and why
    assert "120" in result["error"]


def test_refund_within_price_runs(gemini):
    gemini.script(tool_call("issue_refund", order_id="9931", amount=120), "Refunded $120.")
    ran, tools = spy_tool("issue_refund")

    run_agent("refund_agent", "prompt", tools, "Refund order 9931")

    assert ran == [{"order_id": "9931", "amount": 120}]


def test_refund_rule():
    # A rule is a plain function named by WHAT it checks. It returns a reason to block, or None.
    assert "120" in tool_hooks.refund_not_above_price({"order_id": "9931", "amount": 500})
    assert tool_hooks.refund_not_above_price({"order_id": "9931", "amount": 120}) is None


# ---------------------------------------------------------------------------
# The registry: the loop runs whatever is registered
# ---------------------------------------------------------------------------
def test_loop_runs_any_registered_hook(gemini, monkeypatch):
    # Register a brand-new rule. agent_loop.py has never heard of it, yet it is enforced.
    monkeypatch.setattr(tool_hooks, "HOOKS", {"PreToolUse": [("look_up_order", lambda args: "lookups are closed")]})
    gemini.script(tool_call("look_up_order", order_id="9931"), "Sorry.")
    ran, tools = spy_tool("look_up_order")

    run_agent("agent", "prompt", tools, "Look up 9931")

    assert ran == []
    assert last_tool_results(gemini.requests[1])["look_up_order"]["error"] == "lookups are closed"


def test_matcher_only_sends_matching_tools_to_a_hook():
    # The refund rule is registered for issue_refund only, so other tools are never checked by it.
    assert tool_hooks.run_pre_tool_use("look_up_order", {"order_id": "9931"}) is None
    assert tool_hooks.run_pre_tool_use("issue_refund", {"order_id": "9931", "amount": 500}) is not None


def test_star_matcher_sees_every_tool(monkeypatch):
    monkeypatch.setattr(tool_hooks, "HOOKS", {"PreToolUse": [("*", lambda args: "maintenance window")]})
    assert tool_hooks.run_pre_tool_use("track_shipment", {}) == "maintenance window"


def test_first_block_wins(monkeypatch):
    monkeypatch.setattr(tool_hooks, "HOOKS", {"PreToolUse": [("*", lambda a: None), ("*", lambda a: "first"), ("*", lambda a: "second")]})
    assert tool_hooks.run_pre_tool_use("issue_refund", {}) == "first"
