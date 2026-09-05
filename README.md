@'
# AI Revenue Resolution Agent

AI-powered autonomous revenue recovery and payment reconciliation agent for Razorpay merchants.

## Problem

Payment systems can enter inconsistent states.

For example, a customer may successfully pay and Razorpay may report the payment as `CAPTURED`, while the merchant's own order database still shows `PENDING` because a webhook was delayed, dropped, or failed.

This creates operational problems and can put legitimate revenue at risk.

The AI Revenue Resolution Agent investigates these payment-state problems and determines the safest resolution.

## What It Does

### 1. Payment State Reconciliation

When Razorpay reports a payment as `CAPTURED` while the merchant order is `PENDING` and the amounts match, the agent identifies the mismatch and safely reconciles the order as `PAID` without charging the customer again.

### 2. Failed Payment Recovery

When a payment genuinely fails and the order remains unpaid, the agent can identify the revenue at risk and create a Razorpay Payment Link so the customer can complete the payment.

The recovery result is then recorded in the system.

### 3. Safety Veto

If important financial information does not match, such as:

```text
Razorpay amount:   ₹100
Merchant amount:   ₹1,000