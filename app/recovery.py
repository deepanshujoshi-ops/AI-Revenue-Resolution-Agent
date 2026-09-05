from app.database import get_recovery_case


def decide_recovery(payment, merchant_order):
    payment_id = payment["id"]
    order_id = payment.get("order_id")
    amount = payment["amount"]
    status = payment["status"]

    if not order_id:
        return {
            "action": "ESCALATE",
            "reason": "Failed payment has no associated order ID."
        }

    if merchant_order is None:
        return {
            "action": "ESCALATE",
            "reason": f"Order {order_id} does not exist in merchant database."
        }

    if merchant_order["amount"] != amount:
        return {
            "action": "ESCALATE",
            "reason": (
                f"Amount mismatch: merchant expects "
                f"{merchant_order['amount']} but Razorpay reports {amount}."
            )
        }

    if merchant_order["status"] == "PAID":
        return {
            "action": "NO_ACTION",
            "reason": "Order is already marked as PAID."
        }

    if status != "failed":
        return {
            "action": "NO_ACTION",
            "reason": f"Payment status is {status}, not failed."
        }

    existing_case = get_recovery_case(payment_id)

    if existing_case is not None:
        return {
            "action": "NO_ACTION",
            "reason": "Recovery has already been attempted for this failed payment.",
            "recovery_case": existing_case
        }

    if amount <= 0:
        return {
            "action": "ESCALATE",
            "reason": "Invalid recovery amount."
        }

    return {
        "action": "CREATE_RECOVERY_LINK",
        "reason": "Payment failed and the order is still unpaid.",
        "amount_at_risk": amount
    }