import json
import os

import anthropic

from logs import log

MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-5-5")
MAX_TURNS = 5
MAX_TOKENS = 16000
MAX_TOKENS_CAP = 32000


def run_agent(name: str, system_prompt: str, tools: dict, task: str, indent: str = "") -> str:
    client = anthropic.Anthropic()
    log(f"{indent}[{name}] task: {task}")
    messages = [{"role": "user", "content": task}]
    declarations = [decl for _, decl in tools.values()]

    # PRAO, each turn: Perceive (send the conversation to Claude), Reason (Claude decides),
    # Act (run the tools it asked for), Observe (add the results). Stop when Claude gives an answer.
    max_tokens = MAX_TOKENS
    for turn in range(1, MAX_TURNS + 1):
        log(f"{indent}[{name}] --- turn {turn} ---")

        # 1. PERCEIVE - send the conversation to Claude
        log(f"{indent}[{name}] PERCEIVE  LLM reads {len(messages)} message(s) + {len(tools)} tool(s): {', '.join(tools)}")
        request = {"model": MODEL, "max_tokens": max_tokens, "system": system_prompt, "messages": messages}
        if declarations:
            request["tools"] = declarations
        llm_response = client.messages.create(**request)  # blocks until Claude's whole reply is received and parsed

        # 2. REASON - Claude decides
        stop_reason = llm_response.stop_reason
        log(f"{indent}[{name}] REASON    stop_reason={stop_reason}")
        log(f"{indent}[{name}] REASON    content={llm_response.content}")

        if stop_reason == "max_tokens" and max_tokens < MAX_TOKENS_CAP:
            max_tokens = MAX_TOKENS_CAP
            log(f"{indent}[{name}] REASON    cut off at max_tokens, retrying with max_tokens={max_tokens}")
            continue

        if stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": llm_response.content})
            continue

        if stop_reason != "tool_use":  # end_turn = final answer; any other stop_reason stops with a note
            answer = "".join(b.text for b in llm_response.content if b.type == "text").strip()
            if stop_reason != "end_turn":
                answer = f"stopped: {stop_reason}. {answer}".strip()
            answer = answer or "(no text)"
            log(f"{indent}[{name}] DONE      {answer}")
            return answer

        # 3. ACT - run the tools it asked for
        tool_results = []
        for block in llm_response.content:  # one piece of Claude's reply: text, thinking or tool_use
            if block.type != "tool_use":  # one tool_use block = one tool request from Claude
                continue
            func, _ = tools[block.name]
            args = dict(block.input)
            if "reason" in args:
                log(f"{indent}[{name}] REASON    why: {args.pop('reason')}")
            log(f"{indent}[{name}] ACT       calls {block.name}({args})  -> runs {func.__module__.replace('.', '/')}.py:{func.__name__}")
            result = func(**args)

            # 4. OBSERVE - add the results
            log(f"{indent}[{name}] OBSERVE   {block.name} returned {result}")
            tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(result)})

        messages.append({"role": "assistant", "content": llm_response.content})
        messages.append({"role": "user", "content": tool_results})

    return f"{name} stopped: hit MAX_TURNS without a final answer"
