# Agentic AI Hello World

The smallest working agentic AI app: a coordinator agent that hands work to two worker agents, each with its own tools, all running one loop.

It runs on **Claude**.

## Setup and run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your-key
python main.py "Order 9931 arrived broken. Where is it and can I get a refund?"
```

To try another model, set `CLAUDE_MODEL` (default `claude-opus-5-5`).

## Files

```
main.py                  entry point: starts the coordinator on a question
agents/                  everything that is an agent (LLM + loop)
  agent_loop.py          run_agent(): the loop every agent runs
  orchestrator.py        the coordinator agent + its delegation tools
  worker_agents.json     the worker agents, as config
tools/                   everything that is a tool (plain code)
  functions.py           the 4 plain tools, their declarations, fake order data
logs.py                  shared helper: prints each trace line with file:function
```

| Agent | Tools |
|---|---|
| `orchestrator` (coordinator) | `ask_order_agent`, `ask_refund_agent`: delegation tools that start a worker agent |
| `order_agent` | `look_up_order`, `track_shipment` |
| `refund_agent` | `check_refund_policy`, `issue_refund` |

**Agents are config, tools are code.** To change a worker agent's behaviour or tools, edit `agents/worker_agents.json`; no Python needed. `orchestrator.py` loads it at startup and stops with an error if a tool name doesn't exist.

## Tool vs agent

| | Tool | Agent |
|---|---|---|
| What it is | A plain function that does one fixed job | A model + system prompt + its own tools, running a loop |
| Thinks? | No: same input, same output | Yes: decides what to do next |
| Steps | Runs once | Many turns, until it decides it's done |

**A tool can start an agent.** The model can only ask for a tool by name. The coordinator's `ask_refund_agent` tool is a normal tool call from the model's side; its Python body runs `run_agent()` for the refund agent. The model can't tell the difference.

## How the loop works

Each turn of `run_agent()` has four steps, and they run in two loops:

- **Outer loop (once per turn):** Perceive, then Reason.
- **Inner loop (once per tool request):** Act, then Observe.

1. **Perceive:** send the whole conversation and the agent's tool list to Claude.
2. **Reason:** Claude replies with tool requests or a final answer. `stop_reason` says which.
3. **Act:** our code runs each tool Claude asked for.
4. **Observe:** each result is added to the conversation, and the next turn starts.

| `stop_reason` | What the loop does |
|---|---|
| `tool_use` | Runs the tools, then loops again |
| `end_turn` | Returns Claude's answer |
| `max_tokens` | Retries once with a higher limit, then stops with a note |
| `pause_turn` | Sends the reply back so Claude continues |
| `refusal`, `model_context_window_exceeded`, others | Stops with a note |

`MAX_TURNS` is only a safety cap.

A worker agent starts with only the task text, not the coordinator's conversation.

## Reading the log

Every line starts with where it was printed from (`file:function`). Indented lines belong to a worker agent started by the coordinator.

```
main.py:main                 | USER: Order 9931 arrived broken. Where is it and can I get a refund?
agent_loop.py:run_agent      | [orchestrator] --- turn 1 ---
agent_loop.py:run_agent      | [orchestrator] REASON    stop_reason=tool_use
agent_loop.py:run_agent      | [orchestrator] REASON    why: The customer wants to know where the order is.
agent_loop.py:run_agent      | [orchestrator] ACT       calls ask_order_agent({'task': '...'})  -> runs agents/orchestrator.py:ask_order_agent
orchestrator.py:start_subagent |     starting a new agent loop for order_agent
agent_loop.py:run_agent      |     [order_agent] ACT    calls look_up_order({'order_id': '9931'})  -> runs tools/functions.py:look_up_order
agent_loop.py:run_agent      |     [order_agent] DONE   Order 9931: headphones, delivered.
agent_loop.py:run_agent      | [orchestrator] OBSERVE   ask_order_agent returned {'answer': 'Order 9931: headphones, delivered.'}
main.py:main                 | FINAL ANSWER: ...
```

- **`-> runs tools/functions.py:...`**: a plain tool. **`-> runs agents/orchestrator.py:ask_...`**: a delegation tool that starts a worker agent.
- **`why:`**: the delegation tools take a `reason` argument, so the coordinator states why it picked a worker agent.
