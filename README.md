# Agentic AI Hello World

The smallest working agentic AI app: two agents, each with its own tools, running one loop.

It runs on **Gemini Flash-Lite (free tier)**.

## Setup and run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export GEMINI_API_KEY=your-free-key
python main.py order_agent "Where is order 9931?"
python main.py refund_agent 'Refund order 9931, it arrived broken.'
```

Get a free key at [Google AI Studio](https://aistudio.google.com/apikey). To try another model, set `GEMINI_MODEL` (default `gemini-3.5-flash-lite`).

## Files

```
main.py                  entry point: runs one worker agent on a question
agents/                  everything that is an agent (LLM + loop)
  agent_loop.py          run_agent(): the loop every agent runs
  worker_agents.json     the worker agents, as config
tools/                   everything that is a tool (plain code)
  functions.py           the 4 plain tools, their declarations, fake order data
logs.py                  shared helper: prints each trace line with file:function
```

| Agent | Tools |
|---|---|
| `order_agent` | `look_up_order`, `track_shipment` |
| `refund_agent` | `check_refund_policy`, `issue_refund` |

**Agents are config, tools are code.** To change an agent's behaviour or tools, edit `agents/worker_agents.json`; no Python needed. `main.py` turns each tool name into the real function from `tools/functions.py`.

## Tool vs agent

| | Tool | Agent |
|---|---|---|
| What it is | A plain function that does one fixed job | A model + system prompt + its own tools, running a loop |
| Thinks? | No: same input, same output | Yes: decides what to do next |
| Steps | Runs once | Many turns, until it decides it's done |

## How the loop works

Each turn of `run_agent()` has four steps:

1. **Perceive:** send the whole conversation and the agent's tool list to the model.
2. **Reason:** the model replies either with tool requests or with a final answer. `stop_reason` says which (`tool_use` or `end_turn`).
3. **Act:** if it asked for tools, our code runs them.
4. **Observe:** the results are added to the conversation, and the next turn starts.

The loop stops on `end_turn`. `MAX_TURNS` is only a safety cap.

## Reading the log

Every line starts with where it was printed from (`file:function`):

```
main.py:main                | USER: Order 9931 arrived broken. Where is it?
agent_loop.py:run_agent     | [order_agent] --- turn 1 ---
agent_loop.py:run_agent     | [order_agent] PERCEIVE  LLM reads 1 message(s) + 2 tool(s): look_up_order, track_shipment
agent_loop.py:run_agent     | [order_agent] REASON    stop_reason=tool_use  (Gemini finish_reason=STOP)
agent_loop.py:run_agent     | [order_agent] ACT       calls look_up_order({'order_id': '9931'})  -> runs tools/functions.py:look_up_order
agent_loop.py:run_agent     | [order_agent] OBSERVE   look_up_order returned {'found': True, 'item': 'Headphones', 'price': 120, ...}
agent_loop.py:run_agent     | [order_agent] --- turn 2 ---
agent_loop.py:run_agent     | [order_agent] REASON    stop_reason=end_turn  (Gemini finish_reason=STOP)
agent_loop.py:run_agent     | [order_agent] DONE      Order 9931: headphones, delivered.
main.py:main                | FINAL ANSWER: Order 9931: headphones, delivered.
```

**`stop_reason`** uses the Claude names. It's worked out by `claude_stop_reason()` in [agents/agent_loop.py](agents/agent_loop.py), because Gemini's own `finish_reason` is `STOP` in both cases.

## Claude vs Gemini names

| Idea | Claude API | Gemini API (this repo) |
|---|---|---|
| Tool request from the model | `tool_use` content block | `function_call` part (`response.function_calls`) |
| Tool result sent back | `tool_result` block | `function_response` part (`Part.from_function_response`) |
| "Keep looping" signal | `stop_reason == "tool_use"` | the reply contains function calls |
| "Done" signal | `stop_reason == "end_turn"` | no function calls (`finish_reason` is `STOP` in both cases) |
| Tool schema | `input_schema` | `parameters_json_schema` |
| System prompt | `system` | `system_instruction` |
