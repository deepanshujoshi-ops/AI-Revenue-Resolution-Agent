from app.ai_agent import diagnose_payment
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import uuid

from app.razorpay_client import client, create_recovery_link
from app.database import (
    init_db,
    get_order,
    create_order,
    create_recovery_case,
    get_recovery_case,
    get_recovery_case_by_link_id,
    mark_recovery_recovered,
    get_open_recovery_case,
    get_dashboard_data,
    add_resolution,
    recovery_resolution_exists,
    reset_database
)
from app.reconciliation import reconcile_payment
from app.recovery import decide_recovery
from app.policy_engine import PolicyEngine
from app.orchestrator import ResolutionOrchestrator
from app.landing import LANDING_PAGE_HTML



app = FastAPI(title="AI Revenue Resolution Agent")



@app.on_event("startup")
def startup():
    init_db()


@app.get("/", response_class=HTMLResponse)
def home():
    return LANDING_PAGE_HTML


@app.get("/razorpay-test")

def razorpay_test():
    try:
        payments = client.payment.all({"count": 1})

        return {
            "razorpay": "connected",
            "payments_found": len(payments.get("items", []))
        }

    except Exception as e:
        return {
            "razorpay": "connection_failed",
            "error": str(e)
        }


@app.post("/test/create-order/{order_id}")
def test_create_order(order_id: str, amount: int = 10000):

    create_order(
        order_id=order_id,
        amount=amount,
        status="PENDING"
    )

    return {
        "message": "Merchant order created",
        "order_id": order_id,
        "amount": amount,
        "status": "PENDING"
    }


@app.get("/debug/order/{order_id}")
def debug_order(order_id: str):

    return {
        "database_order": get_order(order_id)
    }


@app.post("/test/reconcile/{payment_id}")
def test_reconcile(payment_id: str):

    # Get authoritative state from Razorpay
    payment = client.payment.fetch(payment_id)

    razorpay_order_id = payment.get("order_id")
    amount = payment["amount"]

    # Get merchant order
    merchant_order = get_order(razorpay_order_id)

    # If merchant hasn't recorded the order yet,
    # create the simulated PENDING record.
    if merchant_order is None:
        create_order(
            order_id=razorpay_order_id,
            amount=amount,
            status="PENDING"
        )

        merchant_order = get_order(razorpay_order_id)

    # Run resolution
    result = reconcile_payment(
        payment,
        merchant_order
    )

    # Fetch again AFTER resolution
    updated_order = get_order(razorpay_order_id)

    return {
        "payment": {
            "id": payment["id"],
            "amount": payment["amount"],
            "status": payment["status"],
            "order_id": razorpay_order_id
        },
        "before_resolution": merchant_order,
        "after_resolution": updated_order,
        "resolution": result
    }
@app.post("/test/recover/{payment_id}")
def test_recover(payment_id: str):

    # Handle our simulated failed-payment test case
    if payment_id.startswith("pay_test_failed_"):

        recovery_case = get_recovery_case(payment_id)

        if recovery_case is None:
            return {
                "action": "ESCALATE",
                "reason": "No recovery case exists for this simulated payment."
            }

        merchant_order = get_order(
            recovery_case["order_id"]
        )

        payment = {
            "id": payment_id,
            "order_id": recovery_case["order_id"],
            "amount": recovery_case["amount"],
            "status": "failed"
        }

    else:
        # Real Razorpay payment
        payment = client.payment.fetch(payment_id)

        merchant_order = get_order(
            payment.get("order_id")
        )

    decision = decide_recovery(
        payment,
        merchant_order
    )

    return decision
@app.post("/test/simulate-failed")
def simulate_failed_payment(
    order_id: str,
    amount: int = 10000
):
    # Create merchant-side unpaid order
    create_order(
        order_id=order_id,
        amount=amount,
        status="PENDING"
    )

    # Simulated Razorpay failed payment
    payment = {
        "id": f"pay_test_failed_{uuid.uuid4().hex[:12]}",
        "order_id": order_id,
        "amount": amount,
        "status": "failed"
    }

    merchant_order = get_order(order_id)

    # Let the recovery decision engine decide
    decision = decide_recovery(
        payment,
        merchant_order
    )

    if decision["action"] != "CREATE_RECOVERY_LINK":
        return decision

    # Create a real Razorpay Test Mode recovery link
    reference_id = (
        f"rr-{uuid.uuid4().hex[:16]}"
    )

    recovery_link = create_recovery_link(
        amount=amount,
        reference_id=reference_id,
        description=f"Payment recovery for order {order_id}"
    )

    # Record recovery attempt
    create_recovery_case(
        order_id=order_id,
        failed_payment_id=payment["id"],
        amount=amount,
        recovery_link_id=recovery_link["id"],
        recovery_link_url=recovery_link["short_url"]
    )

    return {
        "payment": payment,

        "merchant_order": merchant_order,

        "decision": decision,

        "recovery": {
            "action": "CREATE_RECOVERY_LINK",
            "link_id": recovery_link["id"],
            "url": recovery_link["short_url"],
            "status": recovery_link["status"],
            "amount_at_risk": amount
        }
    }
@app.post("/test/complete-recovery/{payment_id}")
def complete_recovery(payment_id: str):

    payment = client.payment.fetch(payment_id)

    if payment["status"] != "captured":
        return {
            "action": "NO_ACTION",
            "reason": (
                f"Payment has not been captured. "
                f"Current status: {payment['status']}"
            )
        }

    recovery_case = get_open_recovery_case()

    if recovery_case is None:
        return {
            "action": "NO_ACTION",
            "reason": "No recovery case was found."
        }

    # Recovery was already completed earlier.
    # Make sure the audit record exists.
    if recovery_case["status"] == "RECOVERED":

        if recovery_resolution_exists(
            recovery_case["order_id"]
        ):
            return {
                "action": "NO_ACTION",
                "reason": "Revenue has already been marked as recovered."
            }

        add_resolution(
            order_id=recovery_case["order_id"],
            payment_id=payment_id,
            issue_type="PAYMENT_RECOVERY",
            action="RECOVERED",
            amount_at_risk=recovery_case["amount"],
            amount_recovered=payment["amount"],
            reason=(
                "Customer successfully completed the recovery payment "
                "after the original payment failure."
            )
        )

        return {
            "action": "RECOVERY_COMPLETED",
            "status": "RECOVERED",
            "payment_id": payment_id,
            "amount_recovered": payment["amount"],
            "order_id": recovery_case["order_id"],
            "message": "Recovery audit record completed."
        }

    # Normal first-time recovery completion
    rows_updated = mark_recovery_recovered(
        recovery_link_id=recovery_case["recovery_link_id"],
        payment_id=payment_id
    )

    if rows_updated != 1:
        return {
            "action": "ESCALATE",
            "reason": "Failed to update recovery case."
        }

    add_resolution(
        order_id=recovery_case["order_id"],
        payment_id=payment_id,
        issue_type="PAYMENT_RECOVERY",
        action="RECOVERED",
        amount_at_risk=recovery_case["amount"],
        amount_recovered=payment["amount"],
        reason=(
            "Customer successfully completed the recovery payment "
            "after the original payment failure."
        )
    )

    return {
        "action": "RECOVERY_COMPLETED",
        "status": "RECOVERED",
        "payment_id": payment_id,
        "amount_recovered": payment["amount"],
        "order_id": recovery_case["order_id"],
        "message": "Revenue successfully recovered."
    }

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():

    return """
<!DOCTYPE html>
<html>
<head>

    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <title>AI Revenue Resolution Agent</title>

    <style>

        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            font-family: Arial, sans-serif;
            background: #f5f7fb;
            color: #172033;
        }

        .header {
            background: #ffffff;
            border-bottom: 1px solid #e5e7eb;
            padding: 22px 40px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .brand h1 {
            margin: 0;
            font-size: 25px;
            letter-spacing: -0.3px;
        }

        .brand p {
            margin: 6px 0 0;
            color: #697386;
            font-size: 14px;
        }

        .status {
            background: #ecfdf3;
            color: #087443;
            padding: 8px 14px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: bold;
        }

        .container {
            max-width: 1280px;
            margin: 30px auto;
            padding: 0 25px;
        }

        /* ---------- STATS ---------- */

        .stats {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 18px;
            margin-bottom: 25px;
        }

        .stat-card {
            background: white;
            border: 1px solid #e6e8ee;
            border-radius: 12px;
            padding: 22px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.03);
        }

        .stat-title {
            color: #697386;
            font-size: 13px;
            margin-bottom: 10px;
        }

        .stat-value {
            font-size: 29px;
            font-weight: bold;
            letter-spacing: -0.5px;
        }

        .stat-description {
            margin-top: 8px;
            color: #98a2b3;
            font-size: 11px;
        }

        /* ---------- MAIN GRID ---------- */

        .main-grid {
            display: grid;
            grid-template-columns: 1.55fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }

        .card {
            background: white;
            border: 1px solid #e6e8ee;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.03);
        }

        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 18px;
        }

        .section-title {
            font-size: 17px;
            font-weight: bold;
        }

        .section-subtitle {
            color: #98a2b3;
            font-size: 12px;
        }

        /* ---------- CASES ---------- */

        .case {
            border: 1px solid #e6e8ee;
            border-radius: 10px;
            padding: 17px;
            margin-bottom: 12px;
        }

        .case:last-child {
            margin-bottom: 0;
        }

        .case-top {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 15px;
        }

        .case-left {
            display: flex;
            gap: 12px;
            min-width: 0;
        }

        .case-icon {
            width: 36px;
            height: 36px;
            min-width: 36px;
            border-radius: 50%;
            background: #ecfdf3;
            color: #087443;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
        }

        .case-icon.warning {
            background: #fff7ed;
            color: #c2410c;
        }

        .case-icon.error {
            background: #fef2f2;
            color: #b42318;
        }

        .case-title {
            font-size: 14px;
            font-weight: bold;
        }

        .case-order {
            margin-top: 4px;
            color: #697386;
            font-size: 12px;
            word-break: break-all;
        }

        .case-amount {
            font-size: 15px;
            font-weight: bold;
            white-space: nowrap;
        }

        .case-details {
            margin-top: 13px;
            padding-top: 13px;
            border-top: 1px solid #edf0f4;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 10px;
        }

        .case-description {
            color: #697386;
            font-size: 12px;
            line-height: 1.5;
        }

        .badge {
            display: inline-block;
            padding: 5px 9px;
            border-radius: 6px;
            font-size: 10px;
            font-weight: bold;
            white-space: nowrap;
        }

        .badge-success {
            background: #ecfdf3;
            color: #087443;
        }

        .badge-warning {
            background: #fff7ed;
            color: #c2410c;
        }

        .badge-error {
            background: #fef2f2;
            color: #b42318;
        }

        /* ---------- AGENT ---------- */

        .agent-card {
            background: #101828;
            color: white;
            border-color: #101828;
        }

        .agent-card .section-title {
            color: white;
        }

        .agent-status {
            display: flex;
            align-items: center;
            gap: 9px;
            margin-bottom: 20px;
            padding: 11px 13px;
            background: #182230;
            border-radius: 8px;
        }

        .agent-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #32d583;
        }

        .agent-status-text {
            font-size: 12px;
            color: #d0d5dd;
        }

        .decision {
            padding: 15px 0;
            border-bottom: 1px solid #344054;
        }

        .decision:last-child {
            border-bottom: none;
        }

        .decision-label {
            color: #98a2b3;
            font-size: 11px;
            margin-bottom: 6px;
            letter-spacing: 0.3px;
        }

        .decision-value {
            font-size: 14px;
            line-height: 1.5;
        }

        .decision-highlight {
            color: #6ce9a6;
            font-weight: bold;
        }

        /* ---------- BOTTOM GRID ---------- */

        .bottom-grid {
            display: grid;
            grid-template-columns: 1.1fr 1fr;
            gap: 20px;
        }

        /* ---------- ACTIVITY ---------- */

        .activity {
            display: flex;
            gap: 12px;
            padding: 14px 0;
            border-bottom: 1px solid #edf0f4;
        }

        .activity:last-child {
            border-bottom: none;
        }

        .activity-icon {
            width: 32px;
            height: 32px;
            min-width: 32px;
            border-radius: 50%;
            background: #ecfdf3;
            color: #087443;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
        }

        .activity-content {
            flex: 1;
            min-width: 0;
        }

        .activity-title {
            font-size: 13px;
            font-weight: bold;
        }

        .activity-subtitle {
            margin-top: 4px;
            color: #697386;
            font-size: 11px;
        }

        .activity-amount {
            font-weight: bold;
            font-size: 13px;
            white-space: nowrap;
        }

        /* ---------- BREAKDOWN ---------- */

        .breakdown-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 14px 0;
            border-bottom: 1px solid #edf0f4;
        }

        .breakdown-row:last-child {
            border-bottom: none;
        }

        .breakdown-label {
            color: #697386;
            font-size: 13px;
        }

        .breakdown-value {
            font-weight: bold;
            font-size: 14px;
        }

        .breakdown-left {
            display: flex;
            align-items: center;
            gap: 9px;
        }

        .mini-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #32d583;
        }

        .mini-dot.blue {
            background: #667085;
        }

        .mini-dot.orange {
            background: #f79009;
        }

        .empty {
            color: #697386;
            font-size: 13px;
            padding: 20px 0;
        }

        .footer-note {
            margin-top: 20px;
            text-align: center;
            color: #98a2b3;
            font-size: 11px;
        }

        @media (max-width: 900px) {

            .stats {
                grid-template-columns: repeat(2, 1fr);
            }

            .main-grid,
            .bottom-grid {
                grid-template-columns: 1fr;
            }

            .header {
                padding: 20px;
            }

        }

        @media (max-width: 550px) {

            .stats {
                grid-template-columns: 1fr;
            }

            .container {
                padding: 0 15px;
            }

            .case-top {
                flex-direction: column;
            }

        }

        /* ---------- DEMO SANDBOX ---------- */
        .demo-panel {
            background: #ffffff;
            border: 1px solid #d0d5dd;
            border-radius: 12px;
            padding: 18px 22px;
            margin-bottom: 24px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        }
        .demo-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
            flex-wrap: wrap;
            gap: 10px;
        }
        .demo-title {
            font-size: 15px;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 8px;
            color: #101828;
        }
        .demo-desc {
            color: #697386;
            font-size: 12px;
            margin-top: 2px;
        }
        .demo-buttons {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            align-items: center;
        }
        .btn {
            border: none;
            padding: 8px 14px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s ease;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }
        .btn:hover {
            opacity: 0.92;
            transform: translateY(-1px);
        }
        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        .btn-success { background: #087443; color: white; }
        .btn-warning { background: #b54708; color: white; }
        .btn-danger { background: #b42318; color: white; }
        .btn-dark { background: #101828; color: white; }
        .btn-light { background: #f2f4f7; color: #344054; border: 1px solid #d0d5dd; }

        .demo-input-group {
            display: flex;
            gap: 8px;
            margin-top: 14px;
            padding-top: 12px;
            border-top: 1px dashed #eaecf0;
            align-items: center;
            flex-wrap: wrap;
        }
        .demo-input {
            flex: 1;
            min-width: 250px;
            padding: 8px 12px;
            border: 1px solid #d0d5dd;
            border-radius: 8px;
            font-size: 12px;
        }
        /* New Visual Execution Pipeline */
        .trace-panel {
            display: none;
            margin-top: 18px;
            background: #f8fafc;
            border: 1px solid #cbd5e1;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 14px rgba(0,0,0,0.04);
        }
        .trace-header-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 12px;
            border-bottom: 1px solid #e2e8f0;
            margin-bottom: 14px;
            flex-wrap: wrap;
            gap: 8px;
        }
        .trace-title-text {
            font-size: 14px;
            font-weight: 700;
            color: #0f172a;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .trace-pipeline-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
        }
        @media (max-width: 900px) {
            .trace-pipeline-grid {
                grid-template-columns: repeat(2, 1fr);
            }
        }
        @media (max-width: 550px) {
            .trace-pipeline-grid {
                grid-template-columns: 1fr;
            }
        }
        .step-card {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 14px;
            display: flex;
            flex-direction: column;
            position: relative;
        }
        .step-card.active-success {
            border-color: #86efac;
            background: #f0fdf4;
        }
        .step-card.active-veto {
            border-color: #fca5a5;
            background: #fef2f2;
        }
        .step-header {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 11px;
            font-weight: 700;
            color: #475569;
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .step-num {
            width: 20px;
            height: 20px;
            border-radius: 50%;
            background: #e2e8f0;
            color: #334155;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 10px;
            font-weight: 800;
        }
        .step-card.active-success .step-num {
            background: #059669;
            color: white;
        }
        .step-card.active-veto .step-num {
            background: #dc2626;
            color: white;
        }
        .step-body {
            font-size: 12px;
            color: #334155;
            flex: 1;
            line-height: 1.5;
        }
        .step-meta-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 4px;
            font-size: 11px;
        }
        .step-meta-label {
            color: #64748b;
        }
        .step-meta-val {
            font-weight: 600;
            color: #0f172a;
        }
        .step-badge {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 700;
            margin-bottom: 6px;
        }
        .step-badge.green { background: #dcfce7; color: #166534; border: 1px solid #86efac; }
        .step-badge.red { background: #fee2e2; color: #991b1b; border: 1px solid #fca5a5; }
        .step-badge.blue { background: #e0f2fe; color: #075985; border: 1px solid #7dd3fc; }
        .step-badge.orange { background: #fef3c7; color: #92400e; border: 1px solid #fcd34d; }
        .step-rule-list {
            margin: 6px 0 0;
            padding-left: 14px;
            font-size: 11px;
            color: #475569;
        }
        .step-rule-list li {
            margin-bottom: 2px;
        }
        .link-btn {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 7px 12px;
            background: #0284c7;
            color: white;
            text-decoration: none;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            margin-top: 8px;
            box-shadow: 0 2px 4px rgba(2, 132, 199, 0.2);
            transition: background 0.15s ease;
        }
        .link-btn:hover {
            background: #0369a1;
        }

    </style>

</head>

<body>

    <div class="header">

        <div class="brand">
            <h1>AI Revenue Resolution Agent</h1>
            <p>Autonomous payment recovery & reconciliation</p>
        </div>

        <div style="display: flex; align-items: center; gap: 16px;">
            <a href="/" style="text-decoration: none; color: #0284c7; font-size: 13px; font-weight: 600; display: flex; align-items: center; gap: 5px; padding: 6px 12px; border-radius: 6px; background: #f0f9ff; border: 1px solid #bae6fd;">
                📖 Intro & How to Use Guide
            </a>
            <div class="status">
                ● Agent Online
            </div>
        </div>

    </div>


    <div class="container">

        <!-- ================= DEMO SANDBOX BAR ================= -->
        <div class="demo-panel">
            <div class="demo-header">
                <div>
                    <div class="demo-title">
                        <span>⚡</span>
                        <span>Interactive Demo Sandbox (Razorpay Buildathon)</span>
                    </div>
                    <div class="demo-desc">
                        Trigger autonomous resolution scenarios live. AI analyzes, Policy Engine enforces guardrails, and Agent settles without charging twice.
                    </div>
                </div>
                <div style="display: flex; gap: 6px;">
                    <button class="btn btn-light" id="btnReset" onclick="resetSandbox()">🔄 Reset Sandbox</button>
                </div>
            </div>

            <div class="demo-buttons">
                <button class="btn btn-success" id="btnDesync" onclick="runScenario('desync')">
                    🟢 1-Click: Reconcile Webhook Desync
                </button>
                <button class="btn btn-warning" id="btnRecovery" onclick="runScenario('recovery')">
                    ⚡ 1-Click: Recover Failed Payment
                </button>
                <button class="btn btn-danger" id="btnTamper" onclick="runScenario('tamper')">
                    🛡️ 1-Click: Policy Veto (Amount Tampering)
                </button>
            </div>

            <div class="demo-input-group">
                <span style="font-size: 12px; font-weight: 600; color: #475467;">Custom Payment:</span>
                <input type="text" class="demo-input" id="customPaymentId" placeholder="Enter Razorpay Payment ID (e.g. pay_TWsSMC66vUTobA)">
                <button class="btn btn-dark" id="btnCustom" onclick="runCustomPayment()">Run Autonomous Agent</button>
            </div>

            <div class="trace-panel" id="traceBox"></div>
        </div>

        <!-- ================= STATS ================= -->



        <div class="stats">

            <div class="stat-card">
                <div class="stat-title">
                    Revenue at Risk
                </div>

                <div class="stat-value" id="atRisk">
                    ₹0
                </div>

                <div class="stat-description">
                    Revenue requiring intervention
                </div>
            </div>


            <div class="stat-card">
                <div class="stat-title">
                    Revenue Recovered
                </div>

                <div class="stat-value" id="recovered">
                    ₹0
                </div>

                <div class="stat-description">
                    Successfully recovered through agent actions
                </div>
            </div>


            <div class="stat-card">
                <div class="stat-title">
                    Issues Resolved
                </div>

                <div class="stat-value" id="resolved">
                    0
                </div>

                <div class="stat-description">
                    Recovery and reconciliation actions
                </div>
            </div>


            <div class="stat-card">
                <div class="stat-title">
                    Escalated
                </div>

                <div class="stat-value" id="escalated">
                    0
                </div>

                <div class="stat-description">
                    Cases requiring human review
                </div>
            </div>

        </div>


        <!-- ================= CASES + AGENT ================= -->

        <div class="main-grid">

            <div class="card">

                <div class="section-header">

                    <div>
                        <div class="section-title">
                            Resolution Cases
                        </div>

                        <div class="section-subtitle">
                            Latest payment issues handled by the agent
                        </div>
                    </div>

                    <span class="badge badge-success">
                        LIVE
                    </span>

                </div>

                <div id="cases">
                    Loading cases...
                </div>

            </div>


            <div class="card agent-card">

                <div class="section-header">

                    <div>
                        <div class="section-title">
                            Agent Decision
                        </div>

                        <div class="section-subtitle" style="color:#98a2b3;">
                            Current reasoning state
                        </div>
                    </div>

                </div>


                <div class="agent-status">

                    <div class="agent-dot"></div>

                    <div class="agent-status-text" id="agentStatus">
                        Monitoring payment activity
                    </div>

                </div>


                <div class="decision">

                    <div class="decision-label">
                        LATEST ACTION
                    </div>

                    <div class="decision-value decision-highlight" id="latestAction">
                        Monitoring
                    </div>

                </div>


                <div class="decision">

                    <div class="decision-label">
                        WHY
                    </div>

                    <div class="decision-value" id="latestReason">
                        Waiting for a payment issue requiring resolution.
                    </div>

                </div>


                <div class="decision">

                    <div class="decision-label">
                        SAFETY MODE
                    </div>

                    <div class="decision-value">
                        Deterministic action controls enabled
                    </div>

                </div>


                <div class="decision">

                    <div class="decision-label">
                        DUPLICATE PREVENTION
                    </div>

                    <div class="decision-value">
                        ✓ Enabled
                    </div>

                </div>


                <div class="decision">

                    <div class="decision-label">
                        POLICY
                    </div>

                    <div class="decision-value">
                        Recover → Verify → Record
                    </div>

                </div>

            </div>

        </div>


        <!-- ================= ACTIVITY + BREAKDOWN ================= -->

        <div class="bottom-grid">

            <div class="card">

                <div class="section-header">

                    <div>
                        <div class="section-title">
                            Recent Activity
                        </div>

                        <div class="section-subtitle">
                            Agent resolution history
                        </div>
                    </div>

                </div>

                <div id="activity">
                    Loading activity...
                </div>

            </div>


            <div class="card">

                <div class="section-header">

                    <div>
                        <div class="section-title">
                            Resolution Breakdown
                        </div>

                        <div class="section-subtitle">
                            How the agent resolved issues
                        </div>
                    </div>

                </div>

                <div id="breakdown">
                    Loading...
                </div>

            </div>

        </div>


        <div class="footer-note">
            AI reasoning is advisory. Financial actions are controlled by deterministic safety policies.
        </div>

    </div>


<script>

function formatMoney(amount) {

    return "₹" + (amount / 100).toLocaleString("en-IN");

}


function escapeHtml(value) {

    if (value === null || value === undefined) {
        return "";
    }

    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");

}


function getActionTitle(item) {

    if (item.action === "RECOVERED") {
        return "Revenue successfully recovered";
    }

    if (item.action === "MARK_ORDER_PAID") {
        return "Payment state reconciled";
    }

    if (item.action === "ESCALATE") {
        return "Case escalated for review";
    }

    return "Payment issue resolved";

}


function getActionIcon(item) {

    if (item.action === "ESCALATE") {
        return "!";
    }

    return "✓";

}


function getCaseDescription(item) {

    if (item.status === "RECOVERED") {
        return "Failed payment recovered successfully.";
    }

    if (item.status === "LINK_CREATED") {
        return "Recovery link created. Awaiting customer payment.";
    }

    return "Payment issue is being monitored.";
}


function updateAgentDecision(data) {

    const resolutions = data.resolutions || [];

    if (resolutions.length === 0) {

        document.getElementById("agentStatus").textContent =
            "Monitoring payment activity";

        document.getElementById("latestAction").textContent =
            "Monitoring";

        document.getElementById("latestReason").textContent =
            "Waiting for a payment issue requiring resolution.";

        return;
    }


    const latest = resolutions[0];

    let action = "Issue resolved";

    if (latest.action === "RECOVERED") {
        action = "Revenue recovered";
    }

    if (latest.action === "MARK_ORDER_PAID") {
        action = "Payment reconciled";
    }

    if (latest.action === "ESCALATE") {
        action = "Human review required";
    }


    document.getElementById("agentStatus").textContent =
        action;

    document.getElementById("latestAction").textContent =
        action;

    document.getElementById("latestReason").textContent =
        latest.reason || "Resolution completed successfully.";

}


function renderCases(data) {

    const container = document.getElementById("cases");

    const cases = [];

    const recoveryCases = data.recovery_cases || [];
    const resolutions = data.resolutions || [];


    /*
     * Add recovery cases first.
     */
    recoveryCases.forEach(item => {

        cases.push({
            type: "RECOVERY",
            order_id: item.order_id,
            created_at: item.created_at || item.updated_at,
            amount: item.amount,
            status: item.status,
            title: item.status === "RECOVERED"
                ? "Payment recovery completed"
                : "Payment recovery in progress",
            description: item.status === "RECOVERED"
                ? "Failed payment recovered successfully."
                : "Recovery link created. Awaiting customer payment.",
            action: item.status === "RECOVERED"
                ? "RECOVERED"
                : "RECOVERY_PENDING"
        });

    });


    /*
     * Add reconciliation cases.
     *
     * Skip PAYMENT_RECOVERY because that case is already
     * represented by recovery_cases above.
     */
    resolutions.forEach(item => {

        if (item.issue_type === "PAYMENT_RECOVERY") {
            return;
        }

        cases.push({
            type: "RECONCILIATION",
            order_id: item.order_id,
            created_at: item.created_at,
            amount: item.amount_at_risk,
            status: "RESOLVED",
            title: item.action === "MARK_ORDER_PAID"
                ? "Payment state reconciled"
                : "Payment issue resolved",
            description: item.action === "MARK_ORDER_PAID"
                ? "Razorpay confirmed payment, but the merchant order was still pending."
                : item.reason,
            action: item.action
        });

    });


    /*
     * Sort newest cases first.
     */
    cases.sort((a, b) => {

        const aTime =
            a.created_at || "";

        const bTime =
            b.created_at || "";

        return bTime.localeCompare(aTime);

    });


    if (cases.length === 0) {

        container.innerHTML =
            '<div class="empty">No resolution cases yet.</div>';

        return;
    }


    container.innerHTML = cases.map(item => {

        let badgeClass = "badge-success";
        let badgeText = "RESOLVED";

        let iconClass = "";
        let icon = "✓";


        if (item.action === "RECOVERY_PENDING") {

            badgeClass = "badge-warning";
            badgeText = "ACTION REQUIRED";

            iconClass = "warning";
            icon = "!";

        }


        if (item.action === "ESCALATE") {

            badgeClass = "badge-error";
            badgeText = "ESCALATED";

            iconClass = "error";
            icon = "!";

        }


        return `
            <div class="case">

                <div class="case-top">

                    <div class="case-left">

                        <div class="case-icon ${iconClass}">
                            ${icon}
                        </div>

                        <div>

                            <div class="case-title">
                                ${escapeHtml(item.title)}
                            </div>

                            <div class="case-order">
                                Order ${escapeHtml(item.order_id)}
                            </div>

                        </div>

                    </div>


                    <div class="case-amount">
                        ${formatMoney(item.amount)}
                    </div>

                </div>


                <div class="case-details">

                    <div class="case-description">
                        ${escapeHtml(item.description)}
                    </div>

                    <span class="badge ${badgeClass}">
                        ${badgeText}
                    </span>

                </div>

            </div>
        `;

    }).join("");

}




function renderActivity(data) {

    const container = document.getElementById("activity");

    const resolutions = data.resolutions || [];

    if (resolutions.length === 0) {

        container.innerHTML =
            '<div class="empty">No resolution activity yet.</div>';

        return;
    }


    container.innerHTML = resolutions.slice(0, 6).map(item => {

        return `
            <div class="activity">

                <div class="activity-icon">
                    ${getActionIcon(item)}
                </div>

                <div class="activity-content">

                    <div class="activity-title">
                        ${escapeHtml(getActionTitle(item))}
                    </div>

                    <div class="activity-subtitle">
                        Order ${escapeHtml(item.order_id)}
                    </div>

                </div>

                <div class="activity-amount">
                    ${formatMoney(
                        item.amount_recovered || item.amount_at_risk || 0
                    )}
                </div>

            </div>
        `;

    }).join("");

}


function renderBreakdown(data) {

    const container = document.getElementById("breakdown");

    const resolutions = data.resolutions || [];

    let recovered = 0;
    let reconciled = 0;
    let escalated = 0;


    resolutions.forEach(item => {

        if (item.action === "RECOVERED") {
            recovered++;
        }

        if (item.action === "MARK_ORDER_PAID") {
            reconciled++;
        }

        if (item.action === "ESCALATE") {
            escalated++;
        }

    });


    container.innerHTML = `

        <div class="breakdown-row">

            <div class="breakdown-left">

                <div class="mini-dot"></div>

                <div class="breakdown-label">
                    Revenue recovered
                </div>

            </div>

            <div class="breakdown-value">
                ${recovered}
            </div>

        </div>


        <div class="breakdown-row">

            <div class="breakdown-left">

                <div class="mini-dot blue"></div>

                <div class="breakdown-label">
                    Payment reconciled
                </div>

            </div>

            <div class="breakdown-value">
                ${reconciled}
            </div>

        </div>


        <div class="breakdown-row">

            <div class="breakdown-left">

                <div class="mini-dot orange"></div>

                <div class="breakdown-label">
                    Escalated
                </div>

            </div>

            <div class="breakdown-value">
                ${escalated}
            </div>

        </div>

    `;

}


async function loadDashboard() {

    try {

        const response = await fetch("/dashboard-data");

        if (!response.ok) {
            throw new Error("Dashboard API unavailable");
        }

        const data = await response.json();

        const stats = data.stats;


        document.getElementById("atRisk").textContent =
            formatMoney(stats.at_risk);

        document.getElementById("recovered").textContent =
            formatMoney(stats.recovered);

        document.getElementById("resolved").textContent =
            stats.resolved;

        document.getElementById("escalated").textContent =
            stats.escalated;


        renderCases(data);

        renderActivity(data);

        renderBreakdown(data);

        updateAgentDecision(data);


    } catch (error) {

        document.getElementById("cases").innerHTML =
            '<div class="empty">Unable to load agent cases.</div>';

        console.error(error);

    }

}


function setButtonsDisabled(disabled) {
    document.querySelectorAll(".demo-panel button").forEach(b => b.disabled = disabled);
}

function showTrace(html) {
    const box = document.getElementById("traceBox");
    box.style.display = "block";
    box.innerHTML = html;
}

async function runScenario(scenario) {
    setButtonsDisabled(true);
    let endpoint = "/demo/simulate-desync";
    let label = "Webhook Desync Reconciliation";
    if (scenario === "recovery") {
        endpoint = "/demo/simulate-failed-recovery";
        label = "Failed Payment Recovery";
    } else if (scenario === "tamper") {
        endpoint = "/demo/simulate-tamper-veto";
        label = "Policy Veto (Tampering / Hallucination Guard)";
    }

    showTrace(`⏳ <b>Running Autonomous Agent Loop: ${label}...</b><br>Contacting Razorpay state -> Diagnosing with Gemini -> Verifying with Policy Engine...`);

    try {
        const res = await fetch(endpoint, { method: "POST" });
        const data = await res.json();
        renderTraceResult(data, label);
        await loadDashboard();
    } catch (err) {
        showTrace(`❌ Error executing scenario: ${err.message}`);
    } finally {
        setButtonsDisabled(false);
    }
}

async function runCustomPayment() {
    const input = document.getElementById("customPaymentId");
    const paymentId = (input.value || "").trim();
    if (!paymentId) {
        alert("Please enter a valid Razorpay Payment ID (e.g. pay_TWsSMC66vUTobA)");
        return;
    }

    setButtonsDisabled(true);
    showTrace(`⏳ <b>Running Autonomous Agent for ${paymentId}...</b><br>Fetching gateway payment state -> Evaluating...`);

    try {
        const res = await fetch(`/agent/resolve/${paymentId}`, { method: "POST" });
        const data = await res.json();
        renderTraceResult(data, `Custom Payment: ${paymentId}`);
        await loadDashboard();
    } catch (err) {
        showTrace(`❌ Error resolving payment: ${err.message}`);
    } finally {
        setButtonsDisabled(false);
    }
}

async function resetSandbox() {
    if (!confirm("Reset demo sandbox and wipe resolution activity?")) return;
    setButtonsDisabled(true);
    try {
        const res = await fetch("/demo/reset-sandbox", { method: "POST" });
        const data = await res.json();
        showTrace(`🔄 <b>Demo Sandbox Reset:</b> Clean state restored for new presentation take.`);
        await loadDashboard();
    } catch (err) {
        showTrace(`❌ Reset error: ${err.message}`);
    } finally {
        setButtonsDisabled(false);
    }
}

function renderTraceResult(data, title) {
    if (!data.success) {
        showTrace(`<div style="color:#b42318; font-weight:600; padding:10px;">❌ <b>Execution Error:</b> ${escapeHtml(data.error || "Unknown error")}</div>`);
        return;
    }

    const ai = data.ai_diagnosis || {};
    const pol = data.policy_decision || {};
    const exec = data.execution || {};
    const p = data.payment || {};
    const mBefore = data.merchant_order_before || {};
    const mAfter = data.merchant_order_after || {};

    const polBadge = pol.allowed 
        ? '<span class="step-badge green">✓ APPROVED</span>' 
        : '<span class="step-badge red">✕ VETOED</span>';

    const card3Class = pol.allowed ? 'active-success' : 'active-veto';
    const card4Class = exec.status === 'COMPLETED' ? 'active-success' : (exec.status === 'ESCALATED' ? 'active-veto' : '');

    const pStatusBadge = p.status === 'captured' 
        ? '<span class="step-badge green">CAPTURED</span>' 
        : (p.status === 'failed' ? '<span class="step-badge red">FAILED</span>' : `<span class="step-badge blue">${escapeHtml(p.status || 'UNKNOWN')}</span>`);

    const mStatusBadge = mBefore.status === 'PAID'
        ? '<span class="step-badge green">PAID</span>'
        : '<span class="step-badge orange">PENDING</span>';

    let ruleListHtml = (pol.checks_passed || []).slice(0, 3).map(r => `<li>✓ ${escapeHtml(r)}</li>`).join('');
    if (pol.violations && pol.violations.length > 0) {
        ruleListHtml += pol.violations.map(v => `<li style="color:#dc2626; font-weight:700;">✕ ${escapeHtml(v)}</li>`).join('');
    }

    let actionDetailHtml = '';
    if (exec.action === 'MARK_ORDER_PAID') {
        actionDetailHtml = `
            <div style="font-weight:700; color:#059669; font-size:13px; margin-bottom:4px;">Reconciled Order to PAID</div>
            <div style="font-size:11px; color:#475569;">Merchant ledger updated safely. Zero customer double charges.</div>
            <div style="margin-top:8px; font-size:11px;"><b>Recovered:</b> ₹${((p.amount||0)/100).toFixed(2)}</div>
        `;
    } else if (exec.action === 'CREATE_RECOVERY_LINK') {
        actionDetailHtml = `
            <div style="font-weight:700; color:#d97706; font-size:13px; margin-bottom:4px;">Recovery Link Dispatched</div>
            <div style="font-size:11px; color:#475569;">Real Razorpay payment link generated to recover abandoned checkout.</div>
            ${exec.recovery_link_url ? `<a href="${exec.recovery_link_url}" target="_blank" class="link-btn">🔗 Open Payment Link ↗</a>` : ''}
        `;
    } else if (exec.action === 'ESCALATE') {
        actionDetailHtml = `
            <div style="font-weight:700; color:#dc2626; font-size:13px; margin-bottom:4px;">Escalated for Human Review</div>
            <div style="font-size:11px; color:#475569;">Zero mutations executed. Ledger remains protected against fraudulent or mismatched states.</div>
        `;
    } else {
        actionDetailHtml = `
            <div style="font-weight:700; color:#475569; font-size:13px; margin-bottom:4px;">${escapeHtml(exec.action || 'NO_ACTION')}</div>
            <div style="font-size:11px; color:#64748b;">${escapeHtml(exec.message || pol.reason || '')}</div>
        `;
    }

    let html = `
        <div class="trace-header-bar">
            <div class="trace-title-text">
                <span>⚡</span>
                <span>Autonomous Execution Pipeline: <b>${escapeHtml(title)}</b></span>
            </div>
            <div>
                <span class="badge ${pol.allowed ? 'badge-success' : 'badge-error'}">
                    ${pol.allowed ? 'POLICY VERIFIED' : 'POLICY VETOED'}
                </span>
            </div>
        </div>

        <div class="trace-pipeline-grid">
            <!-- Step 1 -->
            <div class="step-card">
                <div class="step-header">
                    <div class="step-num">1</div>
                    <span>Gateway & Store State</span>
                </div>
                <div class="step-body">
                    <div class="step-meta-row"><span class="step-meta-label">Payment ID:</span><span class="step-meta-val">${escapeHtml(p.id || 'N/A')}</span></div>
                    <div class="step-meta-row"><span class="step-meta-label">Order ID:</span><span class="step-meta-val">${escapeHtml(p.order_id || mBefore.order_id || 'N/A')}</span></div>
                    <div class="step-meta-row"><span class="step-meta-label">Amount:</span><span class="step-meta-val">₹${((p.amount||0)/100).toFixed(2)}</span></div>
                    <div style="margin-top:8px; display:flex; gap:10px; flex-wrap:wrap;">
                        <div><span style="font-size:10px; color:#64748b; display:block;">Gateway:</span> ${pStatusBadge}</div>
                        <div><span style="font-size:10px; color:#64748b; display:block;">Store DB:</span> ${mStatusBadge}</div>
                    </div>
                </div>
            </div>

            <!-- Step 2 -->
            <div class="step-card">
                <div class="step-header">
                    <div class="step-num">2</div>
                    <span>Gemini AI Diagnosis</span>
                </div>
                <div class="step-body">
                    <div style="margin-bottom:6px;">
                        <span class="step-badge blue">${escapeHtml(ai.issue || 'UNKNOWN')}</span>
                        <span style="font-size:11px; color:#64748b; margin-left:4px;">${Math.round((ai.confidence||0)*100)}% Conf.</span>
                    </div>
                    <div style="font-size:11px; color:#334155; line-height:1.45; margin-bottom:6px;">
                        ${escapeHtml(ai.reasoning || 'Diagnostic analysis completed.')}
                    </div>
                    <div style="font-size:11px; color:#475569; border-top:1px solid #f1f5f9; padding-top:4px;">
                        <b>Rec. Action:</b> <code style="background:#f1f5f9; padding:1px 4px; border-radius:4px; font-size:10px;">${escapeHtml(ai.recommended_action || 'N/A')}</code>
                    </div>
                </div>
            </div>

            <!-- Step 3 -->
            <div class="step-card ${card3Class}">
                <div class="step-header">
                    <div class="step-num">3</div>
                    <span>Deterministic Policy</span>
                </div>
                <div class="step-body">
                    <div style="margin-bottom:6px;">${polBadge}</div>
                    <div style="font-size:11px; line-height:1.4; color:#334155; margin-bottom:6px;">
                        ${escapeHtml(pol.reason || '')}
                    </div>
                    <ul class="step-rule-list">
                        ${ruleListHtml}
                    </ul>
                </div>
            </div>

            <!-- Step 4 -->
            <div class="step-card ${card4Class}">
                <div class="step-header">
                    <div class="step-num">4</div>
                    <span>Execution & Audit</span>
                </div>
                <div class="step-body" style="display:flex; flex-direction:column; justify-content:space-between;">
                    <div>${actionDetailHtml}</div>
                    <div style="margin-top:10px; padding-top:6px; border-top:1px solid #f1f5f9; font-size:10px; color:#64748b;">
                        ✓ Immutable audit record written to SQLite
                    </div>
                </div>
            </div>
        </div>
    `;

    showTrace(html);
}



loadDashboard();

setInterval(loadDashboard, 10000);


</script>

</body>
</html>
    """
@app.get("/dashboard-data")
def dashboard_data():
    return get_dashboard_data()

@app.post("/agent/analyze/{payment_id}")
def analyze_payment(payment_id: str):
    # 1. Fetch authoritative payment state from Razorpay
    payment = client.payment.fetch(payment_id)

    order_id = payment.get("order_id")

    if not order_id:
        return {
            "success": False,
            "error": "Payment has no associated order ID."
        }

    # 2. Fetch merchant's local state
    merchant_order = get_order(order_id)

    if merchant_order is None:
        return {
            "success": False,
            "error": f"Order {order_id} was not found in merchant database."
        }

    # 3. Ask AI to diagnose the situation
    diagnosis = diagnose_payment(payment, merchant_order)

    # 4. Return human-readable AI analysis
    return {
        "success": True,
        "payment": {
            "id": payment["id"],
            "status": payment["status"],
            "amount": payment["amount"],
            "order_id": order_id,
            "method": payment.get("method")
        },
        "merchant_order": merchant_order,
        "ai_analysis": diagnosis
    }
@app.post("/agent/test-mismatch/{payment_id}")
def test_ai_mismatch(payment_id: str):

    # Get authoritative Razorpay state
    payment = client.payment.fetch(payment_id)

    order_id = payment.get("order_id")

    if not order_id:
        return {
            "success": False,
            "error": "Payment has no associated order ID."
        }

    # Force merchant-side state to PENDING for this AI test
    create_order(
        order_id=order_id,
        amount=payment["amount"],
        status="PENDING"
    )

    # Immediately read the freshly-created merchant state
    merchant_order = get_order(order_id)

    # Ask Gemini to diagnose the mismatch
    diagnosis = diagnose_payment(
        payment,
        merchant_order
    )

    return {
        "success": True,

        "payment": {
            "id": payment["id"],
            "status": payment["status"],
            "amount": payment["amount"],
            "order_id": order_id,
            "method": payment.get("method")
        },

        "merchant_order": merchant_order,

        "ai_analysis": diagnosis
    }


@app.post("/agent/resolve/{payment_id}")
def resolve_payment_endpoint(payment_id: str):
    """
    Autonomous resolution loop:
    Razorpay & Merchant State -> AI Diagnosis -> Policy Engine -> Execution -> Audit
    """
    result = ResolutionOrchestrator.resolve_payment(payment_id)
    return result


@app.post("/webhook/razorpay")
async def razorpay_webhook(request: Request):
    """
    Ingests live webhooks from Razorpay (e.g. payment.captured, payment.failed).
    Triggers autonomous resolution to prevent dropped order synchronization.
    """
    try:
        payload = await request.json()
    except Exception:
        return {"status": "error", "message": "Invalid JSON payload"}

    event = payload.get("event")
    payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
    payment_id = payment_entity.get("id")

    if not payment_id:
        return {"status": "ignored", "reason": "No payment ID in webhook payload"}

    resolution = ResolutionOrchestrator.resolve_payment(payment_id)
    return {
        "status": "processed",
        "event": event,
        "payment_id": payment_id,
        "resolution": resolution
    }


@app.post("/demo/simulate-desync")
def demo_simulate_desync():
    """
    Scenario 1: Silent Webhook Drop
    Razorpay captured payment of ₹100, but merchant DB still has order as PENDING.
    Autonomous loop diagnoses mismatch, Policy Engine verifies capture and amount,
    and reconciles order to PAID with zero customer double charges.
    """
    sim_order_id = f"ord_demo_{uuid.uuid4().hex[:8]}"
    sim_payment_id = f"pay_captured_{uuid.uuid4().hex[:10]}"
    amount = 10000  # ₹100

    create_order(order_id=sim_order_id, amount=amount, status="PENDING")

    sim_payment = {
        "id": sim_payment_id,
        "order_id": sim_order_id,
        "amount": amount,
        "status": "captured",
        "method": "upi"
    }

    result = ResolutionOrchestrator.resolve_payment(
        payment_id=sim_payment_id,
        override_payment=sim_payment
    )
    return result


@app.post("/demo/simulate-failed-recovery")
def demo_simulate_failed_recovery():
    """
    Scenario 2: Failed Payment Recovery
    Customer attempted checkout of ₹100, but payment failed.
    Autonomous loop diagnoses failure, Policy Engine verifies order is unpaid,
    generates a real Razorpay payment link, and tracks revenue recovery.
    """
    sim_order_id = f"ord_fail_{uuid.uuid4().hex[:8]}"
    sim_payment_id = f"pay_test_failed_{uuid.uuid4().hex[:10]}"
    amount = 10000  # ₹100

    create_order(order_id=sim_order_id, amount=amount, status="PENDING")

    sim_payment = {
        "id": sim_payment_id,
        "order_id": sim_order_id,
        "amount": amount,
        "status": "failed",
        "method": "card"
    }

    result = ResolutionOrchestrator.resolve_payment(
        payment_id=sim_payment_id,
        override_payment=sim_payment
    )
    return result


@app.post("/demo/simulate-tamper-veto")
def demo_simulate_tamper_veto():
    """
    Scenario 3: Hallucination & Financial Tamper Guard
    Corrupted payment: Razorpay captures ₹100 (10000 paise),
    but merchant order was ₹1,000 (100000 paise).
    Policy Engine VETOES the AI execution, prevents marking the high-value order as paid,
    and safely logs an ESCALATION.
    """
    sim_order_id = f"ord_tamper_{uuid.uuid4().hex[:8]}"
    sim_payment_id = f"pay_tamper_{uuid.uuid4().hex[:10]}"

    create_order(order_id=sim_order_id, amount=100000, status="PENDING")

    tampered_payment = {
        "id": sim_payment_id,
        "order_id": sim_order_id,
        "amount": 10000,
        "status": "captured",
        "method": "card"
    }

    result = ResolutionOrchestrator.resolve_payment(
        payment_id=sim_payment_id,
        override_payment=tampered_payment
    )
    return result


@app.post("/demo/reset-sandbox")
def demo_reset_sandbox():
    """
    Resets the database so you can record clean pitch video takes anytime.
    """
    reset_database()
    return {
        "success": True,
        "message": "Demo database wiped clean for a fresh presentation take."
    }