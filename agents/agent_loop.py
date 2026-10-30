"""
agents/agent_loop.py - the agentic loop. Every agent in this app runs this one function.

    Perceive -> Reason -> Act -> Observe, repeated until Claude stops asking for tools.
"""

import json
import os

import anthropic

from logs import log

# Model can be changed with an env var; default is Claude Opus 5.5.
MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-5-5")

# Safety cap so a confused agent can't loop forever.
MAX_TURNS = 5


def run_agent(name: str, system_prompt: str, tools: dict, task: str, indent: str = "") -> str:
    """
    Run one agent until it gives a final answer.

    name          - label used in the printed trace
    system_prompt - the agent's role and rules
    tools         - {tool_name: (python_function, declaration)} - ONLY this agent's tools
    task          - the request; for a subagent this is ALL it knows
    indent        - extra spaces so subagent output prints nested under its parent
    """
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment
    log(f"{indent}[{name}] task: {task}")

    # The conversation. The model has no memory between calls, so we resend all of it each turn.
    messages = [{"role": "user", "content": task}]
    declarations = [decl for _, decl in tools.values()]

    for turn in range(1, MAX_TURNS + 1):
        log(f"{indent}[{name}] --- turn {turn} ---")

        # 1. PERCEIVE: send the whole conversation + this agent's tool list to the LLM.
        log(f"{indent}[{name}] PERCEIVE  LLM reads {len(messages)} message(s) + {len(tools)} tool(s): {', '.join(tools)}")
        request = {"model": MODEL, "max_tokens": 16000, "system": system_prompt, "messages": messages}
        if declarations:  # an agent with no tools simply isn't offered any
            request["tools"] = declarations
        response = client.messages.create(**request)
        # Keep the reply exactly as Claude sent it (text and tool_use blocks), so the next turn sees it.
        messages.append({"role": "assistant", "content": response.content})

        # 2. REASON: the LLM has decided. stop_reason says what it decided:
        #    tool_use = "run these tools for me", end_turn = "here is my final answer".
        stop_reason = response.stop_reason
        log(f"{indent}[{name}] REASON    stop_reason={stop_reason}")

        # Not a tool request -> finished. (end_turn, max_tokens, refusal, ...)
        if stop_reason != "tool_use":
            answer = "".join(b.text for b in response.content if b.type == "text").strip()
            answer = answer or f"(no text - stopped with {stop_reason})"
            log(f"{indent}[{name}] DONE      {answer}")
            return answer

        # 3. ACT: Claude only ASKED for tools; our code runs them.
        result_blocks = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            func, _ = tools[block.name]
            args = dict(block.input)
            # If the tool asks for a "reason", show it: this is the LLM explaining its choice.
            if "reason" in args:
                log(f"{indent}[{name}] REASON    why: {args.pop('reason')}")
            # Show exactly which Python function will run, as file:function.
            log(f"{indent}[{name}] ACT       calls {block.name}({args})  -> runs {func.__module__.replace('.', '/')}.py:{func.__name__}")
            result = func(**args)

            # 4. OBSERVE: collect the result; it goes back to the LLM at the start of the next turn.
            log(f"{indent}[{name}] OBSERVE   {block.name} returned {result}")
            result_blocks.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(result)})

        # Add the results to the conversation, so the next PERCEIVE includes them.
        messages.append({"role": "user", "content": result_blocks})

    return f"{name} stopped: hit MAX_TURNS without a final answer"
