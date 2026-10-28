# Agentic AI Hello World

The smallest working agentic AI app, grown one feature at a time to cover each topic of the **Claude Certified Architect - Foundations (CCAF)** exam.

It runs on **Gemini Flash-Lite (free tier)**. The ideas are the same as on Claude; only some names differ (see [Claude vs Gemini names](#claude-vs-gemini-names)).

## Setup and run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export GEMINI_API_KEY=your-free-key
python main.py "Order 9931 arrived broken. Where is it and can I get a refund?"
```

Get a free key at [Google AI Studio](https://aistudio.google.com/apikey). To try another model, set `GEMINI_MODEL` (default `gemini-3.5-flash-lite`).

## Files

Tools and agents live in separate files, so you can always tell which is which:

| File | Kind | What's in it |
|---|---|---|
| [main.py](main.py) | entry point | Reads the question and starts the orchestrator. The only file you run. |
| [orchestrator.py](orchestrator.py) | **agent** | The coordinator agent, plus its delegation tools (`ask_order_agent`, `ask_refund_agent`) that start a subagent. |
| [subagents.py](subagents.py) | **agents** | The 2 worker agents: `order_agent` and `refund_agent` (prompt + description + their tools). |
| [tools.py](tools.py) | **tools** | The 4 plain tools (Python functions), their declarations, and fake order data. |
| [loop.py](loop.py) | engine | `run_agent()`: the agentic loop that **every** agent runs. |
| [logs.py](logs.py) | helper | `log()`: prints each trace line tagged with `file:function`. |

## Tool vs agent

| | Tool | Agent |
|---|---|---|
| What it is | A plain function that does one fixed job | A model + system prompt + its own tools, running a loop |
| Thinks? | No: same input, same output | Yes: decides what to do next |
| Steps | Runs once | Many turns, until it decides it's done |
| Examples here | `look_up_order`, `issue_refund` (in `tools.py`) | `orchestrator`, `order_agent`, `refund_agent` |

**How an agent can be started "by a tool call"**, step by step:

1. **A model can't run anything.** All it can do is write text. To get something done, it writes a tool request, such as "call `look_up_order` with `order_id=9931`". Our code reads that request and runs the matching Python function.
2. **So the model can't start another agent by itself either.** It has no "start agent" ability. It can only ask for a tool by name.
3. **So we give it a tool whose Python function starts an agent.** When the orchestrator's model asks for `ask_refund_agent`, our code runs that function, and the function's body calls `run_agent(...)` for the refund agent (see `ask_refund_agent()` and `start_subagent()` in [orchestrator.py](orchestrator.py)).
4. **The model can't tell the difference.** For both kinds of tool it sends a name and inputs, and gets one result back. What ran in between is hidden from it.

The only difference is what the Python function does when it runs:

```python
def look_up_order(order_id):          # plain tool: fixed code, returns at once
    return ORDERS[order_id]

def ask_refund_agent(task):           # delegation tool: its body starts a whole agent
    return start_subagent("refund_agent", task)   # runs run_agent(...) for the refund agent
```

**Analogy:** the manager sits in a closed room and can only pass notes through a slot. A note might say "look up order 9931", and the assistant outside checks the system and passes the answer back. Or it might say "ask Riya about a refund", and the assistant takes it to Riya, who works on it for a while using her own tools and then writes a reply that comes back through the slot. From inside the room both look the same: a note out, a reply in. Behind the slot, one was a quick lookup and the other was a person doing real work.

Claude's Task / Agent tool works the same way: the model asks for the Task tool, and the Agent SDK's code behind it starts a subagent.

## How it works

**3 agents, 4 plain tools, 2 delegation tools:**

```
orchestrator          tools: ask_order_agent, ask_refund_agent   (delegation tools - each starts a subagent)
 |-- order_agent      tools: look_up_order, track_shipment       (plain tools)
 |-- refund_agent     tools: check_refund_policy, issue_refund   (plain tools)
```

**The flow for one question:**

```
main.py
 └─ orchestrator.run_orchestrator(question)
     └─ loop.run_agent("orchestrator")                              ← agent 1
          model: "call ask_order_agent"
           └─ orchestrator.ask_order_agent() → loop.run_agent("order_agent")   ← agent 2
                model: "call look_up_order" → tools.look_up_order()
                model: "done" → answer goes back to the orchestrator
          model: "call ask_refund_agent"
           └─ orchestrator.ask_refund_agent() → loop.run_agent("refund_agent")  ← agent 3
                model: "call check_refund_policy" → tools.check_refund_policy()
                model: "call issue_refund"        → tools.issue_refund()
                model: "done" → answer goes back to the orchestrator
          model: "done" → final answer printed by main.py
```

`main.py` starts only the orchestrator. The orchestrator's **model** decides when to start the subagents, by calling its `ask_...` tools.

## Reading the log

Every line starts with **where** it was printed from, as `file:function`, and each tool call says exactly which Python function will run:

```
main.py:main                   | USER: Order 9931 arrived broken. Where is it and can I get a refund?
loop.py:run_agent              | [orchestrator] stop_reason=tool_use  (Gemini finish_reason=STOP)
loop.py:run_agent              | [orchestrator] why: The customer wants to know where the order is.
loop.py:run_agent              | [orchestrator] calls ask_order_agent({'task': '...'})  -> runs orchestrator.py:ask_order_agent
orchestrator.py:start_subagent |     starting a new agent loop for order_agent
loop.py:run_agent              |     [order_agent] task: ...
loop.py:run_agent              |     [order_agent] stop_reason=tool_use  (Gemini finish_reason=STOP)
loop.py:run_agent              |     [order_agent] calls look_up_order({'order_id': '9931'})  -> runs tools.py:look_up_order
loop.py:run_agent              |     [order_agent] stop_reason=end_turn  (Gemini finish_reason=STOP)
loop.py:run_agent              |     [order_agent] done: ...
main.py:main                   | FINAL ANSWER: ...
```

- **Left column** (`file:function`): the code running at that moment. All three agents show `loop.py:run_agent`, because they share one loop.
- **`-> runs tools.py:...`**: a plain tool. **`-> runs orchestrator.py:ask_...`**: a tool that starts an agent, so the next lines are that subagent working (indented).
- **`stop_reason`**: the signal that drives the loop, using the Claude names (`tool_use` = keep looping, `end_turn` = done, also `max_tokens`, `refusal`). It's worked out by `claude_stop_reason()` in [loop.py](loop.py), because Gemini's own `finish_reason` is `STOP` in both cases.
- **`why:`**: the delegation tools require a `reason` argument, so the model must state why it picked that agent. This is its stated reason, written as part of the tool call; it works on any model, unlike hidden "thinking", which `generateContent` on Flash-Lite doesn't return.

## CCAF topics covered

| CCAF | Topic | Where in the code |
|---|---|---|
| 1.1 | Agentic loop, stop signal, turn cap, feeding results back | [loop.py](loop.py) `run_agent()`, `claude_stop_reason()` |
| 1.2 | Coordinator + subagents, hub-and-spoke | [orchestrator.py](orchestrator.py) `run_orchestrator()`, `ORCHESTRATOR_PROMPT` |
| 1.3 | Spawning a subagent is a tool call; isolated context; scoped tools; description tells the coordinator when to use it | [orchestrator.py](orchestrator.py) `ask_order_agent()`, `ask_refund_agent()`, `start_subagent()`, [subagents.py](subagents.py) `SUBAGENTS` |
| 2.1 | Tool = function + description the model chooses from | [tools.py](tools.py) `TOOLS`, `declare()` |

## Roadmap

Next topics to add to the same app:

| Domain | Topics still to add |
|---|---|
| 1. Agentic architecture | 1.4 prerequisite gates and human handoff · 1.5 hooks (block refunds over $500) · 1.6 decomposition patterns · 1.7 sessions (resume, fork) |
| 2. Tool design & MCP | 2.2 structured errors (`isError`, `isRetryable`) · 2.3 forced tool choice · 2.4 an MCP server |
| 3. Claude Code config | Claude Code features (CLAUDE.md, skills, plan mode, CI); covered as repo config files rather than app code |
| 4. Prompting & structured output | 4.1 explicit criteria · 4.2 few-shot · 4.3 structured output via a schema · 4.4 validation + retry · 4.5 batch processing · 4.6 multi-pass review |
| 5. Context & reliability | 5.1 case-facts block · 5.2 escalation · 5.3 error propagation from subagents · 5.5 confidence routing · 5.6 provenance |

## Claude vs Gemini names

| Idea (CCAF) | Claude API | Gemini API (this repo) |
|---|---|---|
| Tool request from the model | `tool_use` content block | `function_call` part (`response.function_calls`) |
| Tool result sent back | `tool_result` block | `function_response` part (`Part.from_function_response`) |
| "Keep looping" signal | `stop_reason == "tool_use"` | the reply contains function calls |
| "Done" signal | `stop_reason == "end_turn"` | no function calls (`finish_reason` is `STOP` in both cases) |
| Tool schema | `input_schema` | `parameters_json_schema` |
| System prompt | `system` | `system_instruction` |
| Force a tool | `tool_choice` (`auto` / `any` / `tool` / `none`) | `tool_config` function-calling mode (`AUTO` / `ANY` / `NONE`, plus allowed names) |
| Spawn a subagent | Task / Agent tool (Agent SDK) | a delegation tool that starts another loop (`orchestrator.ask_refund_agent`) |
