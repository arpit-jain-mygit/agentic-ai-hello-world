# Agentic AI Hello World

The smallest working agentic AI app, grown one step at a time to cover each topic of the **Claude Certified Architect - Foundations (CCAF)** exam.

It runs on **Gemini Flash-Lite (free tier)**. The ideas are the same as on Claude; only some names differ (see [Claude vs Gemini names](#claude-vs-gemini-names)).

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export GEMINI_API_KEY=your-free-key
```

Get a free key at [Google AI Studio](https://aistudio.google.com/apikey). To try another model, set `GEMINI_MODEL` (default `gemini-3.5-flash-lite`).

## Steps

Each step is a single runnable file that adds one CCAF idea on top of the previous one.

| Step | CCAF | What it shows | Run |
|---|---|---|---|
| [01-agentic-loop](steps/01-agentic-loop/main.py) | 1.1 | One agent, 2 tools, a hand-written Perceive → Reason → Act → Observe loop with a turn cap | `python steps/01-agentic-loop/main.py "Where is my order 9931?"` |
| [02-orchestrator-subagents](steps/02-orchestrator-subagents/main.py) | 1.2, 1.3 | An orchestrator + 2 subagents (4 tools). Spawning a subagent is a tool call; each subagent has an isolated context and scoped tools | `python steps/02-orchestrator-subagents/main.py "Order 9931 arrived broken. Where is it and can I get a refund?"` |

### How step 02 is wired

```
Orchestrator            tools: ask_order_agent, ask_refund_agent   (spawn a subagent)
 |-- Order agent        tools: look_up_order, track_shipment
 |-- Refund agent       tools: check_refund_policy, issue_refund
```

All three agents use the same `run_agent()` loop. When the orchestrator calls `ask_refund_agent(task)`, a brand-new loop starts for the refund agent with only that task text, and its final answer comes back as the tool result.

## Roadmap

Planned steps, one CCAF topic at a time:

| Domain | Topics still to add |
|---|---|
| 1. Agentic architecture | 1.4 prerequisite gates and human handoff · 1.5 hooks (block refunds over $500) · 1.6 decomposition patterns · 1.7 sessions (resume, fork) |
| 2. Tool design & MCP | 2.1 tool descriptions · 2.2 structured errors (`isError`, `isRetryable`) · 2.3 forced tool choice · 2.4 an MCP server |
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
| Spawn a subagent | Task / Agent tool (Agent SDK) | a normal function that starts another loop (step 02) |
