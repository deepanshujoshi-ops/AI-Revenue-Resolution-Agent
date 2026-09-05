"""
Autonomous Resolution Orchestrator
Connects: Ingestion -> Authoritative Fetch -> AI Diagnosis -> Policy Engine -> Execution -> Audit
"""

import uuid
from typing import Dict, Any, Optional

from app.razorpay_client import client, create_recovery_link
from app.ai_agent import diagnose_payment
from app.policy_engine import PolicyEngine
from app.database import (
    get_order,
    create_order,
    update_order,
    add_resolution,
    create_recovery_case,
    get_recovery_case
)


class ResolutionOrchestrator:
    """
    Coordinates the end-to-end lifecycle of payment investigation and resolution.
    Strictly adheres to: "AI reasons. Policy controls. Agent executes."
    """

    @classmethod
    def resolve_payment(
        cls,
        payment_id: str,
        override_payment: Optional[Dict[str, Any]] = None,
        auto_init_merchant_order: bool = True
    ) -> Dict[str, Any]:
        """
        Runs the full autonomous resolution loop for a given payment.
        """
        # Step 1: Fetch Authoritative Payment State
        payment = None
        if override_payment:
            payment = override_payment
        elif payment_id.startswith("pay_test_"):
            # Check if this is a registered simulated recovery case
            rec_case = get_recovery_case(payment_id)
            if rec_case:
                payment = {
                    "id": payment_id,
                    "order_id": rec_case["order_id"],
                    "amount": rec_case["amount"],
                    "status": "failed",
                    "method": "card"
                }
            else:
                # Default fallback for test simulation
                payment = {
                    "id": payment_id,
                    "order_id": f"order_sim_{payment_id[-8:]}",
                    "amount": 10000,
                    "status": "failed",
                    "method": "upi"
                }
        else:
            try:
                payment = client.payment.fetch(payment_id)
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Failed to fetch payment from Razorpay: {str(e)}",
                    "step": "RAZORPAY_FETCH"
                }

        order_id = payment.get("order_id")
        if not order_id:
            return {
                "success": False,
                "error": "Payment record has no associated order ID.",
                "step": "ORDER_IDENTIFICATION"
            }

        # Step 2: Fetch Merchant Order State
        merchant_order = get_order(order_id)
        if merchant_order is None and auto_init_merchant_order:
            # Simulate initial pending checkout state in merchant system
            create_order(
                order_id=order_id,
                amount=payment.get("amount", 10000),
                status="PENDING"
            )
            merchant_order = get_order(order_id)

        # Snapshot of merchant state before resolution
        before_state = dict(merchant_order) if merchant_order else None

        # Step 3: AI Diagnostic Reasoning (Gemini)
        ai_diagnosis = diagnose_payment(payment, merchant_order or {})

        # Step 4: Deterministic Policy Engine Evaluation (Financial Guardrails)
        existing_rec = get_recovery_case(payment.get("id"))
        policy_decision = PolicyEngine.evaluate(
            ai_diagnosis=ai_diagnosis,
            payment=payment,
            merchant_order=merchant_order,
            existing_recovery_case=existing_rec
        )

        # Step 5: Execute Authorized Action within Strict Boundaries
        action_to_take = policy_decision.get("action")
        execution_result = {}

        if action_to_take == "MARK_ORDER_PAID" and policy_decision.get("allowed"):
            rows_updated = update_order(
                order_id=order_id,
                status="PAID",
                payment_id=payment["id"]
            )
            
            if rows_updated == 1:
                add_resolution(
                    order_id=order_id,
                    payment_id=payment["id"],
                    issue_type=ai_diagnosis.get("issue", "PAYMENT_STATE_MISMATCH"),
                    action="MARK_ORDER_PAID",
                    amount_at_risk=payment.get("amount", 0),
                    amount_recovered=payment.get("amount", 0),
                    reason=(
                        f"[AI]: {ai_diagnosis.get('reasoning', '')} "
                        f"[Policy Approved]: {policy_decision.get('reason', '')}"
                    )
                )
                execution_result = {
                    "status": "COMPLETED",
                    "action": "MARK_ORDER_PAID",
                    "amount_recovered": payment.get("amount", 0),
                    "message": "Order successfully reconciled and marked PAID."
                }
            else:
                execution_result = {
                    "status": "FAILED",
                    "action": "ESCALATE",
                    "message": "Database write failure during reconciliation."
                }

        elif action_to_take == "CREATE_RECOVERY_LINK" and policy_decision.get("allowed"):
            amount = payment.get("amount", 10000)
            reference_id = f"rr-{uuid.uuid4().hex[:14]}"
            
            try:
                recovery_link = create_recovery_link(
                    amount=amount,
                    reference_id=reference_id,
                    description=f"Payment recovery for order {order_id}"
                )
                
                create_recovery_case(
                    order_id=order_id,
                    failed_payment_id=payment["id"],
                    amount=amount,
                    recovery_link_id=recovery_link.get("id"),
                    recovery_link_url=recovery_link.get("short_url")
                )
                
                add_resolution(
                    order_id=order_id,
                    payment_id=payment["id"],
                    issue_type=ai_diagnosis.get("issue", "PAYMENT_FAILED"),
                    action="LINK_CREATED",
                    amount_at_risk=amount,
                    amount_recovered=0,
                    reason=(
                        f"[AI]: {ai_diagnosis.get('reasoning', '')} "
                        f"[Policy Approved]: Recovery link {recovery_link.get('short_url')} dispatched."
                    )
                )

                execution_result = {
                    "status": "COMPLETED",
                    "action": "CREATE_RECOVERY_LINK",
                    "amount_at_risk": amount,
                    "recovery_link_id": recovery_link.get("id"),
                    "recovery_link_url": recovery_link.get("short_url"),
                    "message": "Razorpay payment recovery link generated successfully."
                }
            except Exception as e:
                execution_result = {
                    "status": "FAILED",
                    "action": "ESCALATE",
                    "message": f"Razorpay link creation failed: {str(e)}"
                }

        elif action_to_take == "NO_ACTION":
            execution_result = {
                "status": "SKIPPED",
                "action": "NO_ACTION",
                "message": policy_decision.get("reason", "No action needed.")
            }

        else:
            # Policy Veto or Escalation
            at_risk = merchant_order.get("amount", payment.get("amount", 0)) if merchant_order else payment.get("amount", 0)
            add_resolution(
                order_id=order_id,
                payment_id=payment.get("id"),
                issue_type=ai_diagnosis.get("issue", "SECURITY_ESCALATION"),
                action="ESCALATE",
                amount_at_risk=at_risk,
                amount_recovered=0,
                reason=(
                    f"[POLICY VETO / ESCALATION]: {policy_decision.get('reason')} "
                    f"| AI Recommended: '{ai_diagnosis.get('recommended_action')}'"
                )
            )
            execution_result = {
                "status": "ESCALATED",
                "action": "ESCALATE",
                "policy_status": policy_decision.get("policy_status"),
                "reason": policy_decision.get("reason"),
                "violations": policy_decision.get("violations", [])
            }

        # Step 6: Fetch After State
        after_state = get_order(order_id)

        # Step 7: Complete Audit Trace Response
        return {
            "success": True,
            "payment": {
                "id": payment.get("id"),
                "status": payment.get("status"),
                "amount": payment.get("amount"),
                "order_id": order_id,
                "method": payment.get("method")
            },
            "merchant_order_before": before_state,
            "merchant_order_after": after_state,
            "ai_diagnosis": ai_diagnosis,
            "policy_decision": policy_decision,
            "execution": execution_result
        }
