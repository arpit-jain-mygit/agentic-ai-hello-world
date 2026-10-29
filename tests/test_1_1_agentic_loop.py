"""
CCAF 1.1 - the agentic loop.
Checks: stop on end_turn, run the tool on tool_use and send the result back, MAX_TURNS cap.
"""

from google.genai import types

from agent_loop import MAX_TURNS, claude_stop_reason, run_agent
from fake_gemini import last_tool_results, make_response, tool_call
from tools import TOOLS


def test_stops_on_end_turn(gemini):
    # Model answers in text straight away -> end_turn -> loop stops after one call.
    gemini.script("Hello!")
    assert run_agent("agent", "prompt", {}, "Hi") == "Hello!"
    assert len(gemini.requests) == 1


def test_runs_tool_and_sends_result_back(gemini):
    # Turn 1: model asks for a tool. Turn 2: it must SEE the tool's result, then answers.
    gemini.script(tool_call("look_up_order", order_id="9931"), "Headphones, $120.")
    tools = {"look_up_order": TOOLS["look_up_order"]}

    answer = run_agent("agent", "prompt", tools, "What is order 9931?")

    assert answer == "Headphones, $120."
    results = last_tool_results(gemini.requests[1])        # what turn 2 was shown
    assert results["look_up_order"]["price"] == 120


def test_stops_at_max_turns(gemini):
    # A model that never stops asking for tools must not loop forever.
    gemini.script(*[tool_call("look_up_order", order_id="9931")] * MAX_TURNS)
    answer = run_agent("agent", "prompt", {"look_up_order": TOOLS["look_up_order"]}, "loop")

    assert "MAX_TURNS" in answer
    assert len(gemini.requests) == MAX_TURNS


def test_stop_reason_mapping():
    # Gemini says STOP in both cases; the tool calls decide tool_use vs end_turn.
    assert claude_stop_reason(make_response("done")) == "end_turn"
    assert claude_stop_reason(make_response(tool_call("x"))) == "tool_use"
    assert claude_stop_reason(make_response("cut", types.FinishReason.MAX_TOKENS)) == "max_tokens"
    assert claude_stop_reason(make_response("", types.FinishReason.SAFETY)) == "refusal"
