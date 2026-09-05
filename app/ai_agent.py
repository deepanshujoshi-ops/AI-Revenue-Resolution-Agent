import json
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError("GEMINI_API_KEY is missing from .env")

client = genai.Client(api_key=api_key)


SYSTEM_PROMPT = """
You are the diagnostic intelligence of an AI Revenue Resolution Agent.

Your job is to analyze payment state from Razorpay and the merchant's
local order state.

You are a diagnostic AI only.
You MUST NOT execute financial actions.
You only analyze the situation and recommend an action.

Use ONLY the information provided to you.
Never invent missing payment or order information.

Decision rules:

1. If Razorpay payment status is "captured" AND the merchant order
   status is "PENDING" AND the amounts match:
   - issue = PAYMENT_STATE_MISMATCH
   - recommended_action = MARK_ORDER_PAID

2. If Razorpay payment status is "failed" AND the merchant order
   status is not "PAID" AND the amounts match:
   - issue = PAYMENT_FAILED
   - recommended_action = CREATE_RECOVERY_LINK

3. If the Razorpay amount and merchant amount do not match:
   - issue = AMOUNT_MISMATCH
   - recommended_action = ESCALATE

4. If the merchant order is already "PAID":
   - issue = ALREADY_RESOLVED
   - recommended_action = NO_ACTION

5. If the situation cannot be safely determined:
   - issue = UNKNOWN
   - recommended_action = ESCALATE

Confidence must be between 0.0 and 1.0.

The reasoning must clearly explain why the recommendation was made.

Evidence must contain specific facts from the supplied payment
and merchant order data.
"""


RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "issue": {
            "type": "STRING",
            "enum": [
                "PAYMENT_STATE_MISMATCH",
                "PAYMENT_FAILED",
                "ALREADY_RESOLVED",
                "AMOUNT_MISMATCH",
                "UNKNOWN"
            ]
        },
        "risk": {
            "type": "STRING"
        },
        "recommended_action": {
            "type": "STRING",
            "enum": [
                "MARK_ORDER_PAID",
                "CREATE_RECOVERY_LINK",
                "NO_ACTION",
                "ESCALATE"
            ]
        },
        "confidence": {
            "type": "NUMBER"
        },
        "reasoning": {
            "type": "STRING"
        },
        "evidence": {
            "type": "ARRAY",
            "items": {
                "type": "STRING"
            }
        }
    },
    "required": [
        "issue",
        "risk",
        "recommended_action",
        "confidence",
        "reasoning",
        "evidence"
    ]
}


def diagnose_payment(payment, merchant_order):

    input_data = {
        "payment": {
            "id": payment.get("id"),
            "status": payment.get("status"),
            "amount": payment.get("amount"),
            "order_id": payment.get("order_id"),
            "method": payment.get("method")
        },
        "merchant_order": {
            "order_id": merchant_order.get("order_id"),
            "amount": merchant_order.get("amount"),
            "status": merchant_order.get("status"),
            "payment_id": merchant_order.get("payment_id")
        }
    }

    prompt = f"""
{SYSTEM_PROMPT}

Analyze this payment:

{json.dumps(input_data, indent=2)}
"""

    models = [
        "gemini-2.5-flash",
        "gemini-3.5-flash-lite"
    ]


    last_error = None

    for model in models:
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=RESPONSE_SCHEMA,
                    max_output_tokens=500
                )
            )

            return json.loads(response.text)

        except Exception as e:
            last_error = e

    # Graceful degradation fallback if external API is temporarily down/congested
    p_status = payment.get("status")
    p_amount = payment.get("amount")
    m_status = merchant_order.get("status") if merchant_order else None
    m_amount = merchant_order.get("amount") if merchant_order else None

    if merchant_order and p_amount != m_amount:
        return {
            "issue": "AMOUNT_MISMATCH",
            "risk": "Discrepancy between gateway amount and merchant expected amount.",
            "recommended_action": "ESCALATE",
            "confidence": 1.0,
            "reasoning": f"Gateway amount ({p_amount}) does not match merchant expected amount ({m_amount}).",
            "evidence": [
                f"Razorpay amount: {p_amount}",
                f"Merchant amount: {m_amount}"
            ]
        }

    if m_status == "PAID":
        return {
            "issue": "ALREADY_RESOLVED",
            "risk": "None",
            "recommended_action": "NO_ACTION",
            "confidence": 1.0,
            "reasoning": "Merchant order is already settled as PAID.",
            "evidence": ["Merchant order status is PAID"]
        }

    if p_status == "captured" and m_status == "PENDING" and p_amount == m_amount:
        return {
            "issue": "PAYMENT_STATE_MISMATCH",
            "risk": "Customer paid but order is still marked pending in merchant database.",
            "recommended_action": "MARK_ORDER_PAID",
            "confidence": 0.99,
            "reasoning": (
                "Authoritative Razorpay state is CAPTURED and amounts match, "
                "but merchant database is out of sync (PENDING)."
            ),
            "evidence": [
                "Razorpay status is captured",
                "Merchant status is PENDING",
                f"Amounts match: {p_amount}"
            ]
        }

    if p_status == "failed" and m_status != "PAID" and p_amount == m_amount:
        return {
            "issue": "PAYMENT_FAILED",
            "risk": "Unrecovered abandoned checkout revenue.",
            "recommended_action": "CREATE_RECOVERY_LINK",
            "confidence": 0.99,
            "reasoning": "Payment failed at gateway and order is currently unpaid. Safe to initiate recovery link.",
            "evidence": [
                "Razorpay status is failed",
                f"Merchant order status is {m_status}",
                f"Amounts match: {p_amount}"
            ]
        }

    return {
        "issue": "UNKNOWN",
        "risk": "AI diagnosis could not be completed.",
        "recommended_action": "ESCALATE",
        "confidence": 0.0,
        "reasoning": (
            f"AI service unavailable and situation could not be determined safely. "
            f"Last error: {str(last_error)}"
        ),
        "evidence": []
    }