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

| File | What's in it |
|---|---|
| [main.py](main.py) | The only entry point. Reads the question and starts the orchestrator. |
| [agents.py](agents.py) | The 3 agents: the orchestrator and its 2 subagents, plus the "spawn" tools that start a subagent. |
| [loop.py](loop.py) | `run_agent()`: the agentic loop that **every** agent runs. |
| [tools.py](tools.py) | The 4 tools (plain Python functions), their declarations, and fake order data. |

## How it works

**3 agents, 6 tools:**

```
Orchestrator          tools: ask_order_agent, ask_refund_agent   (each starts a subagent)
 |-- order_agent      tools: look_up_order, track_shipment
 |-- refund_agent     tools: check_refund_policy, issue_refund
```

**The flow for one question:**

```
main.py
 └─ agents.run_orchestrator(question)
     └─ loop.run_agent("orchestrator")                     ← agent 1
          model: "call ask_order_agent"
           └─ agents.spawn() → loop.run_agent("order_agent")    ← agent 2
                model: "call look_up_order" → tools.look_up_order()
                model: "done" → answer goes back to the orchestrator
          model: "call ask_refund_agent"
           └─ agents.spawn() → loop.run_agent("refund_agent")   ← agent 3
                model: "call check_refund_policy" → tools.check_refund_policy()
                model: "call issue_refund"        → tools.issue_refund()
                model: "done" → answer goes back to the orchestrator
          model: "done" → final answer printed by main.py
```

`main.py` starts only the orchestrator. The orchestrator's **model** decides when to start the subagents, by calling its `ask_...` tools.

**Subagent vs plain tool:** to the orchestrator, `ask_refund_agent` looks like any tool (call in, answer out). Inside, it's a full agent with its own model loop, system prompt, tools and fresh context. A plain tool like `look_up_order` is fixed code that runs one step.

## CCAF topics covered

| CCAF | Topic | Where in the code |
|---|---|---|
| 1.1 | Agentic loop, stop signal, turn cap, feeding results back | [loop.py](loop.py) `run_agent()` |
| 1.2 | Coordinator + subagents, hub-and-spoke | [agents.py](agents.py) `run_orchestrator()`, `ORCHESTRATOR_PROMPT` |
| 1.3 | Spawning a subagent is a tool call; isolated context; scoped tools; description tells the coordinator when to use it | [agents.py](agents.py) `spawn_tool()`, `SUBAGENTS` |
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
| Spawn a subagent | Task / Agent tool (Agent SDK) | a normal function that starts another loop (`agents.spawn_tool`) |
