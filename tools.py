"""
tools.py - the 4 tools the subagents can use, plus fake data.

A tool = a plain Python function + a declaration (name, description, inputs).
The model only ever sees the declaration; our code runs the function. (CCAF 2.1)
"""

from google.genai import types

# ---------------------------------------------------------------------------
# Fake data - a tiny in-memory "database", so no real system is needed
# ---------------------------------------------------------------------------
ORDERS = {
    "9931": {"item": "Headphones", "price": 120, "status": "delivered", "days_since_delivery": 3, "customer_email": "riya@example.com"},
    "4471": {"item": "Laptop stand", "price": 40, "status": "processing", "days_since_delivery": None, "customer_email": "sam@example.com"},
}


# ---------------------------------------------------------------------------
# Order tools (used by the order agent)
# ---------------------------------------------------------------------------
def look_up_order(order_id: str) -> dict:  # plain tool: fixed code, returns at once
    """Return the order record, or say it was not found."""
    order = ORDERS.get(order_id)
    return {"found": False} if order is None else {"found": True, **order}


def track_shipment(order_id: str) -> dict:  # plain tool: fixed code, returns at once
    """Return the delivery status of an order."""
    order = ORDERS.get(order_id)
    return {"tracking": "Unknown order"} if order is None else {"tracking": f"Status: {order['status']}"}


# ---------------------------------------------------------------------------
# Refund tools (used by the refund agent)
# ---------------------------------------------------------------------------
def check_refund_policy(order_id: str) -> dict:  # plain tool: fixed code, returns at once
    """Refunds are allowed within 30 days of delivery."""
    order = ORDERS.get(order_id)
    if order is None or order["days_since_delivery"] is None:
        return {"eligible": False, "reason": "Not delivered yet"}
    return {"eligible": order["days_since_delivery"] <= 30, "rule": "Refunds allowed within 30 days of delivery"}


def issue_refund(order_id: str, amount: float) -> dict:  # plain tool: fixed code, returns at once
    """Pretend to refund the customer."""
    return {"refunded": True, "order_id": order_id, "amount": amount}


# ---------------------------------------------------------------------------
# Declarations - what the model is told about each tool
# ---------------------------------------------------------------------------
def declare(name: str, description: str, **params: str) -> types.FunctionDeclaration:
    """Build a tool declaration. params maps arg name -> JSON type, e.g. order_id="string"."""
    return types.FunctionDeclaration(
        name=name,
        description=description,
        parameters_json_schema={
            "type": "object",
            "properties": {p: {"type": t} for p, t in params.items()},
            "required": list(params),
        },
    )


# Every tool in one place: name -> (python function, declaration for the model)
TOOLS = {
    "look_up_order": (look_up_order, declare("look_up_order", "Get an order's item, price and status.", order_id="string")),
    "track_shipment": (track_shipment, declare("track_shipment", "Get the delivery status of an order.", order_id="string")),
    "check_refund_policy": (check_refund_policy, declare("check_refund_policy", "Check if an order can be refunded.", order_id="string")),
    "issue_refund": (issue_refund, declare("issue_refund", "Refund an order. Only after the policy says eligible.", order_id="string", amount="number")),
}
