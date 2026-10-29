"""
CCAF 1.2 - coordinator + subagents (hub-and-spoke).
Checks: the coordinator only delegates, starts the agent the model picked, and gets its answer back.
"""

from fake_gemini import last_tool_results, tool_call, tool_names
from orchestrator import WORKER_AGENTS, run_orchestrator


def script_order_question(gemini):
    gemini.script(
        tool_call("ask_order_agent", task="Status of order 9931?", reason="order question"),  # orchestrator turn 1
        "Order 9931: headphones, delivered.",                                                  # order agent turn 1
        "Your headphones were delivered.",                                                     # orchestrator turn 2
    )


def test_orchestrator_only_has_delegation_tools(gemini):
    # The coordinator manages; it has no plain tools of its own.
    script_order_question(gemini)
    run_orchestrator("Where is order 9931?")
    assert tool_names(gemini.requests[0]) == {"ask_order_agent", "ask_refund_agent"}


def test_starts_the_agent_the_model_picked(gemini):
    script_order_question(gemini)
    run_orchestrator("Where is order 9931?")
    # Request 2 is the order agent's loop: it runs with the order agent's prompt.
    assert gemini.requests[1]["config"].system_instruction == WORKER_AGENTS["order_agent"]["prompt"]


def test_subagent_answer_goes_back_to_orchestrator(gemini):
    script_order_question(gemini)
    final = run_orchestrator("Where is order 9931?")
    # The orchestrator's 2nd turn sees the subagent's answer as a tool result, then synthesizes.
    results = last_tool_results(gemini.requests[2])
    assert results["ask_order_agent"]["answer"] == "Order 9931: headphones, delivered."
    assert final == "Your headphones were delivered."
