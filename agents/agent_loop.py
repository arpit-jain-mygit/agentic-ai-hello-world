import json
import os

import anthropic

from logs import log

MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-5-5")
MAX_TURNS = 5


def run_agent(name: str, system_prompt: str, tools: dict, task: str, indent: str = "") -> str:
    client = anthropic.Anthropic()
    log(f"{indent}[{name}] task: {task}")
    messages = [{"role": "user", "content": task}]
    declarations = [decl for _, decl in tools.values()]

    # PRAO, each turn: Perceive (send the conversation to Claude), Reason (Claude decides),
    # Act (run the tools it asked for), Observe (add the results). Stop when Claude gives an answer.
    for turn in range(1, MAX_TURNS + 1):
        log(f"{indent}[{name}] --- turn {turn} ---")

        # 1. PERCEIVE
        log(f"{indent}[{name}] PERCEIVE  LLM reads {len(messages)} message(s) + {len(tools)} tool(s): {', '.join(tools)}")
        request = {"model": MODEL, "max_tokens": 16000, "system": system_prompt, "messages": messages}
        if declarations:
            request["tools"] = declarations
        response = client.messages.create(**request)  # blocks until Claude's whole reply is received and parsed
        messages.append({"role": "assistant", "content": response.content})  # keep Claude's reply for the next turn's request

        # 2. REASON
        stop_reason = response.stop_reason
        log(f"{indent}[{name}] REASON    stop_reason={stop_reason}")
        log(f"{indent}[{name}] REASON    content={response.content}")

        if stop_reason != "tool_use":  # end_turn = final answer; max_tokens, refusal, etc. = stop without a tool call
            answer = "".join(b.text for b in response.content if b.type == "text").strip()
            answer = answer or f"(no text - stopped with {stop_reason})"
            log(f"{indent}[{name}] DONE      {answer}")
            return answer

        # 3. ACT
        result_blocks = []
        for block in response.content:
            if block.type != "tool_use":  # one tool_use block = one tool request from Claude
                continue
            func, _ = tools[block.name]
            args = dict(block.input)
            if "reason" in args:
                log(f"{indent}[{name}] REASON    why: {args.pop('reason')}")
            log(f"{indent}[{name}] ACT       calls {block.name}({args})  -> runs {func.__module__.replace('.', '/')}.py:{func.__name__}")
            result = func(**args)

            # 4. OBSERVE
            log(f"{indent}[{name}] OBSERVE   {block.name} returned {result}")
            result_blocks.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(result)})

        messages.append({"role": "user", "content": result_blocks})

    return f"{name} stopped: hit MAX_TURNS without a final answer"
