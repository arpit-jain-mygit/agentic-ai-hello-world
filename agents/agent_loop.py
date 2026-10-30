"""
agents/agent_loop.py - the agentic loop. Every agent in this app runs this one function.

    Perceive -> Reason -> Act -> Observe, repeated until the model stops asking for tools.
"""

import os

from google import genai
from google.genai import types

from logs import log

# Model can be changed with an env var; default is the free Flash-Lite.
MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")

# Safety cap so a confused agent can't loop forever.
MAX_TURNS = 5


def claude_stop_reason(response) -> str:
    """
    Translate Gemini's reply into the Claude stop_reason it would have.
    Gemini's own finish_reason is "STOP" both when it wants a tool and when it is done,
    so we look at whether the reply contains tool calls.
    """
    finish = response.candidates[0].finish_reason
    if response.function_calls:
        return "tool_use"      # wants tools -> keep looping
    if finish == types.FinishReason.MAX_TOKENS:
        return "max_tokens"    # cut off by the output limit
    if finish in (types.FinishReason.SAFETY, types.FinishReason.PROHIBITED_CONTENT):
        return "refusal"       # blocked for safety
    return "end_turn"          # finished normally -> stop


def run_agent(name: str, system_prompt: str, tools: dict, task: str) -> str:
    """
    Run one agent until it gives a final answer.

    name          - label used in the printed trace
    system_prompt - the agent's role and rules
    tools         - {tool_name: (python_function, declaration)} - ONLY this agent's tools
    task          - the request; the agent's whole context
    """
    client = genai.Client()  # reads GEMINI_API_KEY from the environment
    log(f"[{name}] task: {task}")

    # The conversation. The model has no memory between calls, so we resend all of it each turn.
    contents = [types.Content(role="user", parts=[types.Part(text=task)])]
    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        tools=[types.Tool(function_declarations=[decl for _, decl in tools.values()])],
    )

    for turn in range(1, MAX_TURNS + 1):
        log(f"[{name}] --- turn {turn} ---")

        # 1. PERCEIVE: send the whole conversation + this agent's tool list to the LLM.
        log(f"[{name}] PERCEIVE  LLM reads {len(contents)} message(s) + {len(tools)} tool(s): {', '.join(tools)}")
        response = client.models.generate_content(model=MODEL, contents=contents, config=config)
        contents.append(response.candidates[0].content)

        # 2. REASON: the LLM has decided. stop_reason says what it decided:
        #    tool_use = "run these tools for me", end_turn = "here is my final answer".
        stop_reason = claude_stop_reason(response)
        finish = response.candidates[0].finish_reason
        log(f"[{name}] REASON    stop_reason={stop_reason}  (Gemini finish_reason={finish.name if finish else None})")

        # No tool requested -> finished.
        if stop_reason != "tool_use":
            answer = (response.text or "").strip() or f"(no text - stopped with {stop_reason})"
            log(f"[{name}] DONE      {answer}")
            return answer

        # 3. ACT: the LLM only ASKED for tools; our code runs them.
        result_parts = []
        for call in response.function_calls:
            func, _ = tools[call.name]
            args = dict(call.args)
            log(f"[{name}] ACT       calls {call.name}({args})  -> runs tools/functions.py:{func.__name__}")
            result = func(**args)

            # 4. OBSERVE: collect the result; it goes back to the LLM at the start of the next turn.
            log(f"[{name}] OBSERVE   {call.name} returned {result}")
            result_parts.append(types.Part.from_function_response(name=call.name, response=result))

        # Add the results to the conversation, so the next PERCEIVE includes them.
        contents.append(types.Content(role="user", parts=result_parts))

    return f"{name} stopped: hit MAX_TURNS without a final answer"
