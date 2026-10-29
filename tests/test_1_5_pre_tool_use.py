"""
CCAF 1.5 - PreToolUse hook.
Rule enforced in CODE (not the prompt): a refund can never be more than the order's price.
Checks: over-price refund is blocked, the tool never runs, the model is told why; a valid refund still runs.
"""

from agent_loop import run_agent
from fake_gemini import last_tool_results, tool_call
from tools import TOOLS


def spy_refund_tool():
    """issue_refund's declaration with a spy function, so the test knows if it really ran."""
    ran = []
    _, declaration = TOOLS["issue_refund"]
    return ran, {"issue_refund": (lambda **args: ran.append(args) or {"refunded": True}, declaration)}


def test_refund_over_price_is_blocked(gemini):
    gemini.script(tool_call("issue_refund", order_id="9931", amount=500), "Sorry, I can't refund $500.")
    ran, tools = spy_refund_tool()

    run_agent("refund_agent", "prompt", tools, "Refund $500 for order 9931")

    assert ran == []                                      # the tool never ran
    result = last_tool_results(gemini.requests[1])["issue_refund"]
    assert result["blocked_by"] == "pre_tool_use hook"    # the model is told it was blocked, and why
    assert "120" in result["error"]


def test_refund_within_price_runs(gemini):
    gemini.script(tool_call("issue_refund", order_id="9931", amount=120), "Refunded $120.")
    ran, tools = spy_refund_tool()

    run_agent("refund_agent", "prompt", tools, "Refund order 9931")

    assert ran == [{"order_id": "9931", "amount": 120}]


def test_hook_rule():
    from hooks import pre_tool_use

    assert "120" in pre_tool_use("issue_refund", {"order_id": "9931", "amount": 500})  # blocked, says why
    assert pre_tool_use("issue_refund", {"order_id": "9931", "amount": 120}) is None   # allowed
    assert pre_tool_use("look_up_order", {"order_id": "9931"}) is None                 # other tools untouched
