from tools.functions import prepare_handoff

# CCAF objective 1.5 - Pre-execution hook: the cap is low so the demo prices ($40, $120) can trigger it.
REFUND_CAP = 100


# CCAF objective 1.5 - Pre-execution hook: block a rule-breaking call and redirect it to a human before it runs.
def pre_tool_hook(name: str, args: dict):
    if name == "issue_refund" and args.get("amount", 0) > REFUND_CAP:
        handoff = prepare_handoff(args["order_id"], f"refund of {args['amount']} is above the {REFUND_CAP} cap", "human agent to approve or decline")
        return {"error": f"Refund above ${REFUND_CAP} is not allowed. Sent to a human agent.", "handoff": handoff}
    return None


# CCAF objective 1.5 - PostToolUse hook: normalize the tool result before Claude reads it.
def post_tool_hook(name: str, result: dict) -> dict:
    if name == "look_up_order" and "price" in result:
        return {**result, "price": f"{result['price']:.2f} USD"}
    return result
