"""
CCAF 1.5 - PostToolUse hooks: run AFTER a tool, BEFORE the model sees its result. They can change the result.
Example rule: hide the customer's email, so private data never reaches the model.
Checks: the model sees the changed result, the real data is untouched, rules run in order,
and a call blocked by PreToolUse never reaches PostToolUse.
"""

import hooks
from agent_loop import run_agent
from fake_gemini import last_tool_results, tool_call
from tools import ORDERS, TOOLS


def test_model_never_sees_the_email(gemini):
    gemini.script(tool_call("look_up_order", order_id="9931"), "Headphones, $120.")

    run_agent("order_agent", "prompt", {"look_up_order": TOOLS["look_up_order"]}, "Order 9931?")

    seen = last_tool_results(gemini.requests[1])["look_up_order"]
    assert seen["customer_email"] == "***"                   # the model got the hidden version
    assert seen["price"] == 120                               # everything else is unchanged
    assert ORDERS["9931"]["customer_email"] != "***"          # the real data is untouched


def test_hide_email_rule():
    # A PostToolUse rule gets the tool's result and returns a changed copy, or None for "no change".
    assert hooks.hide_customer_email({"item": "Headphones", "customer_email": "a@b.com"}) == {"item": "Headphones", "customer_email": "***"}
    assert hooks.hide_customer_email({"tracking": "Status: delivered"}) is None


def test_post_rules_run_in_order(monkeypatch):
    monkeypatch.setattr(hooks, "HOOKS", {"PostToolUse": [
        ("*", lambda r: {**r, "steps": r["steps"] + ["first"]}),
        ("*", lambda r: {**r, "steps": r["steps"] + ["second"]}),
        ("other_tool", lambda r: {**r, "steps": ["never"]}),     # matcher doesn't fit, so it is skipped
    ]})
    assert hooks.run_post_tool_use("look_up_order", {"steps": []}) == {"steps": ["first", "second"]}


def test_blocked_call_skips_post_hooks(gemini, monkeypatch):
    # PreToolUse blocked the call -> the tool never ran -> there is no result for PostToolUse to change.
    post_ran = []
    monkeypatch.setattr(hooks, "HOOKS", {
        "PreToolUse": [("look_up_order", lambda args: "blocked")],
        "PostToolUse": [("*", lambda r: post_ran.append(r))],
    })
    gemini.script(tool_call("look_up_order", order_id="9931"), "Sorry.")

    run_agent("agent", "prompt", {"look_up_order": TOOLS["look_up_order"]}, "Order 9931?")

    assert post_ran == []
