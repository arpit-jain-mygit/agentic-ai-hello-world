"""
loop.py - the agentic loop (CCAF 1.1). Every agent in this app runs this one function.

    Perceive -> Reason -> Act -> Observe, repeated until the model stops asking for tools.
"""

import os

from google import genai
from google.genai import types

# Model can be changed with an env var; default is the free Flash-Lite.
MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")

# Safety cap so a confused agent can't loop forever (CCAF 1.1 anti-pattern).
MAX_TURNS = 5

# Set SHOW_THINKING=1 to also print a summary of WHY the model chose each step.
SHOW_THINKING = os.environ.get("SHOW_THINKING") == "1"


def run_agent(name: str, system_prompt: str, tools: dict, task: str, indent: str = "") -> str:
    """
    Run one agent until it gives a final answer.

    name          - label used in the printed trace
    system_prompt - the agent's role and rules
    tools         - {tool_name: (python_function, declaration)} - ONLY this agent's tools
    task          - the request; for a subagent this is ALL it knows (isolated context)
    indent        - extra spaces so subagent output prints nested under its parent
    """
    client = genai.Client()  # reads GEMINI_API_KEY from the environment
    print(f"{indent}[{name}] task: {task}")

    # The conversation. The model has no memory between calls, so we resend all of it each turn.
    contents = [types.Content(role="user", parts=[types.Part(text=task)])]
    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        tools=[types.Tool(function_declarations=[decl for _, decl in tools.values()])],
        # Ask the model to think a bit more and return a short summary of that thinking.
        thinking_config=types.ThinkingConfig(include_thoughts=True, thinking_level="low") if SHOW_THINKING else None,
    )

    for _ in range(MAX_TURNS):
        # PERCEIVE + REASON: the model reads everything so far and decides what to do.
        response = client.models.generate_content(model=MODEL, contents=contents, config=config)
        contents.append(response.candidates[0].content)

        # The REASON step, made visible: print the model's thought summary, if any.
        for part in response.candidates[0].content.parts or []:
            if part.thought and part.text:
                print(f"{indent}[{name}] thinks: {part.text.strip()}")

        # No tool requested -> finished.  (Claude: stop_reason == "end_turn")
        if not response.function_calls:
            print(f"{indent}[{name}] done: {response.text.strip()}")
            return response.text

        # ACT: the model only ASKED for tools; our code runs them.  (Claude: stop_reason == "tool_use")
        result_parts = []
        for call in response.function_calls:
            func, _ = tools[call.name]
            print(f"{indent}[{name}] calls {call.name}({dict(call.args)})")
            result = func(**call.args)
            result_parts.append(types.Part.from_function_response(name=call.name, response=result))

        # OBSERVE: send results back so the model sees them next turn.
        contents.append(types.Content(role="user", parts=result_parts))

    return f"{name} stopped: hit MAX_TURNS without a final answer"
