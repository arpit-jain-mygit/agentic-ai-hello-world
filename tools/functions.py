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


def check_refund_policy(order_id: str) -> dict:
    order = ORDERS.get(order_id)
    if order is None or order["days_since_delivery"] is None:
        return {"eligible": False, "reason": "Not delivered yet"}
    return {"eligible": order["days_since_delivery"] <= 30, "rule": "Refunds allowed within 30 days of delivery"}


def issue_refund(order_id: str, amount: float) -> dict:
    return {"refunded": True, "order_id": order_id, "amount": amount}


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
}
