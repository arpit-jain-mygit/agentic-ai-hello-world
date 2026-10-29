"""
agent_loop.py - the agentic loop (CCAF 1.1). Every agent in this app runs this one function.

    Perceive -> Reason -> Act -> Observe, repeated until the model stops asking for tools.
"""

import os

from google import genai
from google.genai import types

from tool_hooks import run_post_tool_use, run_pre_tool_use
from logs import log

# Model can be changed with an env var; default is the free Flash-Lite.
MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")

# Safety cap so a confused agent can't loop forever (CCAF 1.1 anti-pattern).
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
    log(f"{indent}[{name}] task: {task}")

    # The conversation. The model has no memory between calls, so we resend all of it each turn.
    contents = [types.Content(role="user", parts=[types.Part(text=task)])]
    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        tools=[types.Tool(function_declarations=[decl for _, decl in tools.values()])],
    )

    for turn in range(1, MAX_TURNS + 1):
        log(f"{indent}[{name}] --- turn {turn} ---")

        # 1. PERCEIVE: send the whole conversation + this agent's tool list to the LLM.
        log(f"{indent}[{name}] PERCEIVE  LLM reads {len(contents)} message(s) + {len(tools)} tool(s): {', '.join(tools)}")
        response = client.models.generate_content(model=MODEL, contents=contents, config=config)
        contents.append(response.candidates[0].content)

        # 2. REASON: the LLM has decided. stop_reason says what it decided:
        #    tool_use = "run these tools for me", end_turn = "here is my final answer".
        stop_reason = claude_stop_reason(response)
        finish = response.candidates[0].finish_reason
        log(f"{indent}[{name}] REASON    stop_reason={stop_reason}  (Gemini finish_reason={finish.name if finish else None})")

        # No tool requested -> finished.  (Claude: stop_reason == "end_turn")
        if stop_reason != "tool_use":
            answer = (response.text or "").strip() or f"(no text - stopped with {stop_reason})"
            log(f"{indent}[{name}] DONE      {answer}")
            return answer

        # 3. ACT: the LLM only ASKED for tools; our code runs them.  (Claude: stop_reason == "tool_use")
        result_parts = []
        for call in response.function_calls:
            func, _ = tools[call.name]
            args = dict(call.args)
            # If the tool asks for a "reason", show it: this is the LLM explaining its choice.
            if "reason" in args:
                log(f"{indent}[{name}] REASON    why: {args.pop('reason')}")
            # HOOK (CCAF 1.5): run every PreToolUse rule registered in tool_hooks.py for this tool.
            # If one blocks, the tool does NOT run, and the model gets the reason back instead.
            blocked = run_pre_tool_use(call.name, args)
            if blocked:
                log(f"{indent}[{name}] HOOK      blocked {call.name}({args}): {blocked}")
                result = {"error": blocked, "blocked_by": "PreToolUse hook"}
            else:
                # Show exactly which Python function will run, as file:function (tools.py or orchestrator.py).
                log(f"{indent}[{name}] ACT       calls {call.name}({args})  -> runs {func.__module__}.py:{func.__name__}")
                result = func(**args)

                # HOOK (CCAF 1.5): run every PostToolUse rule for this tool. It may change the result
                # (e.g. hide private data) BEFORE the model sees it.
                changed = run_post_tool_use(call.name, result)
                if changed != result:
                    log(f"{indent}[{name}] HOOK      changed {call.name} result: {result} -> {changed}")
                result = changed

            # 4. OBSERVE: collect the result; it goes back to the LLM at the start of the next turn.
            log(f"{indent}[{name}] OBSERVE   {call.name} returned {result}")
            result_parts.append(types.Part.from_function_response(name=call.name, response=result))

        # Add the results to the conversation, so the next PERCEIVE includes them.
        contents.append(types.Content(role="user", parts=result_parts))

    return f"{name} stopped: hit MAX_TURNS without a final answer"
