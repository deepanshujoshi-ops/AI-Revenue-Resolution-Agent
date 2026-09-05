from app.database import update_order, add_resolution


def reconcile_payment(payment, merchant_order):
    payment_id = payment["id"]
    order_id = payment.get("order_id")
    amount = payment["amount"]
    status = payment["status"]

    if not order_id:
        return {
            "action": "ESCALATE",
            "reason": "Payment has no associated order ID."
        }

    if merchant_order is None:
        return {
            "action": "ESCALATE",
            "reason": f"Order {order_id} does not exist in merchant database."
        }

    # Safety check: amounts must match
    if merchant_order["amount"] != amount:
        return {
            "action": "ESCALATE",
            "reason": (
                f"Amount mismatch: merchant expects "
                f"{merchant_order['amount']} but Razorpay reports {amount}."
            )
        }

    # Already resolved
    if merchant_order["status"] == "PAID":
        return {
            "action": "NO_ACTION",
            "reason": "Order is already marked as PAID."
        }

    # Main reconciliation case
    if status == "captured" and merchant_order["status"] == "PENDING":

        rows_updated = update_order(
        order_id=order_id,
        status="PAID",
        payment_id=payment_id
        )

        if rows_updated != 1:
            return {
            "action": "ESCALATE",
            "reason": "Failed to persist PAID status in merchant database."
        }



        add_resolution(
            order_id=order_id,
            payment_id=payment_id,
            issue_type="PAYMENT_STATE_MISMATCH",
            action="MARK_ORDER_PAID",
            amount_at_risk=amount,
            amount_recovered=amount,
            reason=(
                "Razorpay confirmed the payment was captured, "
                "but the merchant database showed PENDING. "
                "The order was safely reconciled without charging again."
            )
        )

        updated_order = {
            "order_id": order_id,
            "status": "PAID",
            "payment_id": payment_id
        }

        return {
            "action": "MARK_ORDER_PAID",
            "reason": "Captured payment reconciled with merchant order.",
            "amount_recovered": amount,
            "updated_order": updated_order
        }

    if status == "failed":
        return {
            "action": "RECOVERY_REQUIRED",
            "reason": "Payment failed and may require a recovery action.",
            "amount_at_risk": amount
        }

    return {
        "action": "NO_ACTION",
        "reason": f"No resolution required for payment status: {status}"
    }