# Local Demo Guide

This guide is for a local demonstration using Razorpay Test Mode. It is not a production runbook.

## Before starting

1. Start the FastAPI app as described in the root README.
2. Confirm that the configured Razorpay credentials are Test Mode credentials.
3. Open `http://127.0.0.1:8000/docs` to inspect the routes and their actual parameter names.
4. Use test transactions and synthetic merchant orders only. Never use real customer/payment data for screenshots.

## Demo A: inspect the dashboard

1. Open `http://127.0.0.1:8000/dashboard`.
2. Confirm that the dashboard loads.
3. Confirm that `/dashboard-data` returns the same metrics/cases rendered by the UI.
4. Capture a screenshot only after removing or masking payment IDs and any personal data.

## Demo B: captured payment vs pending merchant order

1. Create a payment in the Razorpay Test Mode dashboard and retain its payment ID and associated Razorpay order ID.
2. Ensure the merchant-side store contains a `PENDING` order for that exact order ID and expected amount.
3. Call `POST /test/reconcile/{payment_id}` from `/docs`.
4. Inspect the returned payment, order-before, order-after, and resolution fields.
5. Confirm that the order changes only when the authoritative payment is captured and the amount matches.

Amounts returned by Razorpay are commonly represented in the currency's smallest unit (for INR, paise). Check the endpoint's implementation and use consistent units when setting up a test order.

## Demo C: financial mismatch

1. Prepare a local pending order whose expected amount differs from the captured Razorpay payment amount.
2. Run the reconciliation endpoint for that payment.
3. Confirm that the system blocks the state-changing action and returns a review/escalation outcome.
4. Record the exact response. Do not describe this safeguard as working unless this test passes in the current version.

## Demo D: failed-payment recovery

1. Use `POST /test/simulate-failed` in `/docs` with a unique demo order ID and a small amount.
2. The implementation shared during development creates a Razorpay Test Mode Payment Link when the recovery decision is eligible.
3. Inspect the returned decision and recovery-link fields.
4. Complete the link only with Razorpay Test Mode payment details, then use the recovery-completion route if present in the current code.
5. Confirm that the recovery case and dashboard values update correctly.

## What to capture

- Dashboard overview.
- Successful reconciliation response (before and after state).
- Mismatch response showing the blocked action.
- Recovery response with the generated Test Mode payment-link status.

Mask payment IDs, order IDs, email addresses, phone numbers, and all credentials before adding screenshots to GitHub.
