"""
CCAF 1.3 - spawning subagents and passing context.
Checks: scoped tools, isolated context (the task is all it knows), description reaches the coordinator,
and a typo in worker_agents.json fails fast.
"""

import json

import pytest

from fake_gemini import tool_call, tool_names
from orchestrator import ORCHESTRATOR_TOOLS, WORKER_AGENTS, load_worker_agents, run_orchestrator


def script_refund_question(gemini):
    gemini.script(
        tool_call("ask_refund_agent", task="Can order 9931 be refunded?", reason="refund question"),
        "Yes, eligible.",
        "You can get a refund.",
    )


def test_subagent_gets_only_its_own_tools(gemini):
    script_refund_question(gemini)
    run_orchestrator("Order 9931 broke. Refund?")
    assert tool_names(gemini.requests[1]) == {"check_refund_policy", "issue_refund"}


def test_subagent_context_is_only_the_task(gemini):
    # The subagent starts blank: one message, the task text. Not the customer's original question.
    script_refund_question(gemini)
    run_orchestrator("Order 9931 broke. Refund?")
    contents = gemini.requests[1]["contents"]
    assert len(contents) == 1
    assert contents[0].parts[0].text == "Can order 9931 be refunded?"


def test_description_tells_the_coordinator_when_to_use_it():
    decl = ORCHESTRATOR_TOOLS["ask_refund_agent"][1]
    assert decl.description.startswith(WORKER_AGENTS["refund_agent"]["description"])


def test_unknown_tool_in_config_fails_fast(tmp_path):
    bad = tmp_path / "worker_agents.json"
    bad.write_text(json.dumps({"x_agent": {"description": "d", "prompt": "p", "tools": ["no_such_tool"]}}))
    with pytest.raises(ValueError, match="no_such_tool"):
        load_worker_agents(bad)
