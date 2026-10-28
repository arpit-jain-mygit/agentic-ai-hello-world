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

## Tool vs agent

| | Tool | Agent |
|---|---|---|
| What it is | A plain function that does one fixed job | A model + system prompt + its own tools, running a loop |
| Thinks? | No: same input, same output | Yes: decides what to do next |
| Steps | Runs once | Many turns, until it decides it's done |
| Examples here | `look_up_order`, `issue_refund` (in `tools.py`) | `orchestrator`, `order_agent`, `refund_agent` |

**The one bridge between them:** the orchestrator's model can only call tools, so each subagent is wrapped in a *delegation tool* (`ask_order_agent`, `ask_refund_agent`, in `orchestrator.py`). From outside it looks like a tool; inside it starts a whole agent. That's how Claude's Task / Agent tool works too.

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
           └─ orchestrator.ask_agent() → loop.run_agent("order_agent")   ← agent 2
                model: "call look_up_order" → tools.look_up_order()
                model: "done" → answer goes back to the orchestrator
          model: "call ask_refund_agent"
           └─ orchestrator.ask_agent() → loop.run_agent("refund_agent")  ← agent 3
                model: "call check_refund_policy" → tools.check_refund_policy()
                model: "call issue_refund"        → tools.issue_refund()
                model: "done" → answer goes back to the orchestrator
          model: "done" → final answer printed by main.py
```

`main.py` starts only the orchestrator. The orchestrator's **model** decides when to start the subagents, by calling its `ask_...` tools.

## Reading the log

Every line starts with the file that printed it, and each tool call says which file the tool's code lives in:

```
loop.py         | [orchestrator] stop_reason=tool_use  (Gemini finish_reason=STOP)
loop.py         | [orchestrator] why: The customer wants to know where the order is.
loop.py         | [orchestrator] calls ask_order_agent({'task': '...'})  -> runs in orchestrator.py
orchestrator.py |     ask_order_agent: starting a new agent loop for order_agent
loop.py         |     [order_agent] task: ...
loop.py         |     [order_agent] stop_reason=tool_use  (Gemini finish_reason=STOP)
loop.py         |     [order_agent] calls look_up_order({'order_id': '9931'})  -> runs in tools.py
loop.py         |     [order_agent] stop_reason=end_turn  (Gemini finish_reason=STOP)
loop.py         |     [order_agent] done: ...
```

- **`-> runs in tools.py`**: a plain tool. **`-> runs in orchestrator.py`**: a delegation tool, so the next lines are a subagent working (indented).
- **`stop_reason`**: the signal that drives the loop, using the Claude names (`tool_use` = keep looping, `end_turn` = done, also `max_tokens`, `refusal`). It's worked out by `claude_stop_reason()` in [loop.py](loop.py), because Gemini's own `finish_reason` is `STOP` in both cases.
- **`why:`**: the delegation tools require a `reason` argument, so the model must state why it picked that agent. This is its stated reason, written as part of the tool call; it works on any model, unlike hidden "thinking", which `generateContent` on Flash-Lite doesn't return.

## CCAF topics covered

| CCAF | Topic | Where in the code |
|---|---|---|
| 1.1 | Agentic loop, stop signal, turn cap, feeding results back | [loop.py](loop.py) `run_agent()`, `claude_stop_reason()` |
| 1.2 | Coordinator + subagents, hub-and-spoke | [orchestrator.py](orchestrator.py) `run_orchestrator()`, `ORCHESTRATOR_PROMPT` |
| 1.3 | Spawning a subagent is a tool call; isolated context; scoped tools; description tells the coordinator when to use it | [orchestrator.py](orchestrator.py) `delegation_tool()`, [subagents.py](subagents.py) `SUBAGENTS` |
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
| Spawn a subagent | Task / Agent tool (Agent SDK) | a delegation tool that starts another loop (`orchestrator.delegation_tool`) |
