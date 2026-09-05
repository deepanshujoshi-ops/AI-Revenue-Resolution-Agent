"""
Policy Engine: Deterministic Safety & Financial Guardrails
Philosophy: "AI reasons. Policy controls. Agent executes."
"""

from typing import Dict, Any, Optional


class PolicyEngine:
    """
    Deterministic rule-based policy engine.
    Independently verifies every AI diagnostic recommendation against
    immutable business rules and financial safety invariants.
    """

    @classmethod
    def evaluate(
        cls,
        ai_diagnosis: Dict[str, Any],
        payment: Dict[str, Any],
        merchant_order: Optional[Dict[str, Any]],
        existing_recovery_case: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Evaluates the AI diagnosis against deterministic policies.

        Returns a structured decision:
        {
            "allowed": bool,
            "action": str,
            "policy_status": "APPROVED" | "VETOED" | "ESCALATED",
            "reason": str,
            "checks_passed": list[str],
            "violations": list[str]
        }
        """
        recommended_action = ai_diagnosis.get("recommended_action")
        checks_passed = []
        violations = []

        # Guard 1: Existence of merchant order
        if merchant_order is None:
            violations.append("Merchant order does not exist in local database")
            return {
                "allowed": False,
                "action": "ESCALATE",
                "policy_status": "VETOED",
                "reason": "Policy Veto: Order missing from merchant database.",
                "checks_passed": checks_passed,
                "violations": violations
            }
        checks_passed.append("Merchant order exists in database")

        # Guard 2: Order ID reference consistency
        payment_order_id = payment.get("order_id")
        merchant_order_id = merchant_order.get("order_id")
        if payment_order_id and merchant_order_id and payment_order_id != merchant_order_id:
            violations.append(f"Order ID mismatch ({payment_order_id} vs {merchant_order_id})")
            return {
                "allowed": False,
                "action": "ESCALATE",
                "policy_status": "VETOED",
                "reason": f"Policy Veto: Payment order ID '{payment_order_id}' does not match merchant order ID '{merchant_order_id}'.",
                "checks_passed": checks_passed,
                "violations": violations
            }
        checks_passed.append("Order reference ID matches")

        # Guard 3: Amount integrity (paise match)
        payment_amount = payment.get("amount")
        order_amount = merchant_order.get("amount")
        if payment_amount is None or order_amount is None or payment_amount != order_amount:
            violations.append(
                f"Amount mismatch: Razorpay reported {payment_amount} paise, "
                f"merchant expects {order_amount} paise"
            )
            return {
                "allowed": False,
                "action": "ESCALATE",
                "policy_status": "VETOED",
                "reason": (
                    f"Policy Veto: Financial integrity violation! "
                    f"Gateway amount ({payment_amount}) does not match merchant expected amount ({order_amount})."
                ),
                "checks_passed": checks_passed,
                "violations": violations
            }
        checks_passed.append(f"Amount integrity verified: {payment_amount} paise matches")

        # Guard 4: Idempotency / Already Settled
        if merchant_order.get("status") == "PAID":
            checks_passed.append("Order is already settled as PAID")
            return {
                "allowed": True,
                "action": "NO_ACTION",
                "policy_status": "APPROVED",
                "reason": "Policy Guard: Order is already marked PAID. No additional mutations permitted.",
                "checks_passed": checks_passed,
                "violations": []
            }

        # Guard 5: Reconciliation Action (MARK_ORDER_PAID)
        if recommended_action == "MARK_ORDER_PAID":
            gateway_status = payment.get("status")
            if gateway_status != "captured":
                violations.append(f"Gateway status is '{gateway_status}', expected 'captured'")
                return {
                    "allowed": False,
                    "action": "ESCALATE",
                    "policy_status": "VETOED",
                    "reason": (
                        f"Policy Veto: AI recommended MARK_ORDER_PAID, but Razorpay status is '{gateway_status}' "
                        f"(must be 'captured' to safely reconcile)."
                    ),
                    "checks_passed": checks_passed,
                    "violations": violations
                }

            checks_passed.append("Authoritative gateway status is 'captured'")
            checks_passed.append("Merchant order status is pending reconciliation")

            return {
                "allowed": True,
                "action": "MARK_ORDER_PAID",
                "policy_status": "APPROVED",
                "reason": (
                    "Policy Approved: Payment captured by Razorpay and amounts match. "
                    "Safe to mark merchant order as PAID without double-charging."
                ),
                "checks_passed": checks_passed,
                "violations": []
            }

        # Guard 6: Recovery Action (CREATE_RECOVERY_LINK)
        if recommended_action == "CREATE_RECOVERY_LINK":
            gateway_status = payment.get("status")
            if gateway_status != "failed":
                violations.append(f"Gateway status is '{gateway_status}', expected 'failed'")
                return {
                    "allowed": False,
                    "action": "ESCALATE",
                    "policy_status": "VETOED",
                    "reason": (
                        f"Policy Veto: AI recommended CREATE_RECOVERY_LINK, but payment status is '{gateway_status}' "
                        f"(must be 'failed')."
                    ),
                    "checks_passed": checks_passed,
                    "violations": violations
                }

            # Check if active recovery link was already created
            if existing_recovery_case is not None:
                checks_passed.append("Recovery link already exists for this payment")
                return {
                    "allowed": True,
                    "action": "NO_ACTION",
                    "policy_status": "APPROVED",
                    "reason": "Policy Guard: Recovery link already generated for this failed transaction.",
                    "checks_passed": checks_passed,
                    "violations": []
                }

            checks_passed.append("Gateway status confirmed failed")
            checks_passed.append("Order remains unpaid")
            checks_passed.append("No active duplicate recovery case found")

            return {
                "allowed": True,
                "action": "CREATE_RECOVERY_LINK",
                "policy_status": "APPROVED",
                "reason": (
                    "Policy Approved: Payment failure confirmed and order unpaid. "
                    "Authorized to generate a recovery payment link."
                ),
                "checks_passed": checks_passed,
                "violations": []
            }

        # Guard 7: AI recommended NO_ACTION
        if recommended_action == "NO_ACTION":
            checks_passed.append("AI recommended NO_ACTION")
            return {
                "allowed": True,
                "action": "NO_ACTION",
                "policy_status": "APPROVED",
                "reason": "Policy Approved: No intervention needed.",
                "checks_passed": checks_passed,
                "violations": []
            }

        # Guard 8: Explicit ESCALATE or unrecognized action
        violations.append(f"Action requires escalation or is unrecognized: {recommended_action}")
        return {
            "allowed": False,
            "action": "ESCALATE",
            "policy_status": "ESCALATED",
            "reason": (
                f"Policy Escalation: AI flagged case as '{recommended_action}' "
                f"or situation requires manual merchant verification."
            ),
            "checks_passed": checks_passed,
            "violations": violations
        }
