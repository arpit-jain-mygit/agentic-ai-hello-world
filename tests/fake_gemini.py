"""
fake_gemini.py - a stand-in for genai.Client, so tests run offline, free and the same every time.

A test SCRIPTS what the "model" says, turn by turn:

    gemini.script(
        tool_call("issue_refund", order_id="9931", amount=500),   # turn 1: model asks for a tool
        "Sorry, I can't refund that much.",                        # turn 2: model gives final text
    )

Every agent in a run (orchestrator and subagents) shares ONE script, used in call order.
Every request our code sends is saved in gemini.requests, so tests can check what the model was shown.
"""

from google.genai import types


def tool_call(name: str, **args) -> types.FunctionCall:
    """One tool request the fake model makes."""
    return types.FunctionCall(name=name, args=args)


def make_response(reply, finish=types.FinishReason.STOP) -> types.GenerateContentResponse:
    """
    Build a real Gemini response object from a scripted reply.
    reply = a string (final text) or a FunctionCall / list of FunctionCalls (tool requests).
    """
    if isinstance(reply, str):
        parts = [types.Part(text=reply)]
    else:
        calls = reply if isinstance(reply, list) else [reply]
        parts = [types.Part(function_call=c) for c in calls]
    content = types.Content(role="model", parts=parts)
    return types.GenerateContentResponse(candidates=[types.Candidate(content=content, finish_reason=finish)])


class FakeGemini:
    """Plays the role of genai.Client(). Our code calls client.models.generate_content(...)."""

    def __init__(self):
        self.replies = []   # what the model will say next, in order
        self.requests = []  # what our code sent: {"contents": [...], "config": ...} per call
        self.models = self  # so client.models.generate_content works

    def script(self, *replies) -> None:
        self.replies.extend(replies)

    def generate_content(self, model, contents, config):
        # Copy contents: agent_loop keeps appending to the same list after this call.
        self.requests.append({"contents": list(contents), "config": config})
        assert self.replies, "fake model ran out of scripted replies"
        return make_response(self.replies.pop(0))


# ---------------------------------------------------------------------------
# Small helpers to read what a request contained
# ---------------------------------------------------------------------------
def tool_names(request) -> set:
    """Names of the tools the model was offered in this request."""
    return {d.name for d in request["config"].tools[0].function_declarations}


def last_tool_results(request) -> dict:
    """The tool results our code sent back in this request: {tool_name: result_dict}."""
    last = request["contents"][-1]
    return {p.function_response.name: p.function_response.response for p in last.parts if p.function_response}
