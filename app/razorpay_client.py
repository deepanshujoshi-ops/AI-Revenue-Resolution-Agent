import os
import time

import razorpay
from dotenv import load_dotenv


load_dotenv()

key_id = os.getenv("RAZORPAY_KEY_ID")
key_secret = os.getenv("RAZORPAY_KEY_SECRET")

if not key_id or not key_secret:
    raise RuntimeError("Razorpay API keys are missing from .env")


client = razorpay.Client(
    auth=(key_id, key_secret)
)


def get_payment(payment_id: str):
    return client.payment.fetch(payment_id)


def create_recovery_link(
    amount: int,
    reference_id: str,
    description: str
):
    return client.payment_link.create({
        "amount": amount,
        "currency": "INR",
        "accept_partial": False,
        "reference_id": reference_id,
        "description": description,
        "expire_by": int(time.time()) + (24 * 60 * 60),
        "reminder_enable": False
    })