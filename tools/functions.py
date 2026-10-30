ORDERS = {
    "9931": {"item": "Headphones", "price": 120, "status": "delivered", "days_since_delivery": 3, "customer_email": "riya@example.com"},
    "4471": {"item": "Laptop stand", "price": 40, "status": "processing", "days_since_delivery": None, "customer_email": "sam@example.com"},
}


def look_up_order(order_id: str) -> dict:
    order = ORDERS.get(order_id)
    return {"found": False} if order is None else {"found": True, **order}


def track_shipment(order_id: str) -> dict:
    order = ORDERS.get(order_id)
    return {"tracking": "Unknown order"} if order is None else {"tracking": f"Status: {order['status']}"}


# CCAF objective 1.4 - Enforcement: orders that passed the policy check in this process. issue_refund needs one.
ELIGIBLE_ORDERS = set()


def check_refund_policy(order_id: str) -> dict:
    order = ORDERS.get(order_id)
    if order is None or order["days_since_delivery"] is None:
        return {"eligible": False, "reason": "Not delivered yet"}
    eligible = order["days_since_delivery"] <= 30
    if eligible:
        ELIGIBLE_ORDERS.add(order_id)
    return {"eligible": eligible, "rule": "Refunds allowed within 30 days of delivery"}


# CCAF objective 1.4 - Enforcement: a prerequisite gate. Refund is blocked until the policy check passed.
def issue_refund(order_id: str, amount: float) -> dict:
    if order_id not in ELIGIBLE_ORDERS:
        return {"refunded": False, "error": "Refund blocked: check_refund_policy must say eligible first."}
    return {"refunded": True, "order_id": order_id, "amount": amount}


# CCAF objective 1.4 - Handoff: a structured summary for a human agent who cannot see the transcript.
def prepare_handoff(order_id: str, root_cause: str, recommended_action: str) -> dict:
    order = ORDERS.get(order_id)
    if order is None:
        return {"error": f"Unknown order {order_id}"}
    return {
        "order_id": order_id,
        "customer_email": order["customer_email"],
        "item": order["item"],
        "price": order["price"],
        "root_cause": root_cause,
        "recommended_action": recommended_action,
    }


def declare(name: str, description: str, **params: str) -> dict:
    return {
        "name": name,
        "description": description,
        "input_schema": {
            "type": "object",
            "properties": {p: {"type": t} for p, t in params.items()},
            "required": list(params),
        },
    }


TOOLS = {
    "look_up_order": (look_up_order, declare("look_up_order", "Get an order's item, price and status.", order_id="string")),
    "track_shipment": (track_shipment, declare("track_shipment", "Get the delivery status of an order.", order_id="string")),
    "check_refund_policy": (check_refund_policy, declare("check_refund_policy", "Check if an order can be refunded.", order_id="string")),
    "issue_refund": (issue_refund, declare("issue_refund", "Refund an order. Only after the policy says eligible.", order_id="string", amount="number")),
    "prepare_handoff": (prepare_handoff, declare("prepare_handoff", "Write a handoff summary for a human agent when a refund cannot be issued.", order_id="string", root_cause="string", recommended_action="string")),
}
