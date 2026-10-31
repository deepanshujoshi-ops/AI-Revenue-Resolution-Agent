# AI Revenue Resolution Agent

An AI-assisted payment investigation and revenue-recovery prototype for Razorpay merchants, built with Python and FastAPI.

> **Project status:** Prototype / hackathon project. This repository is not a production payment platform. Use Razorpay Test Mode credentials for demonstrations. Do not expose development or `/test/*` endpoints to the public internet.

## The problem

A payment provider and a merchant's order system can temporarily disagree. For example, Razorpay may report a payment as `captured` while the merchant's order remains `PENDING` because the corresponding webhook was delayed, dropped, or not processed.

Treating every mismatch as a failed payment can cause unnecessary repeat-payment attempts. Treating every payment as successful without verification can create incorrect order records. The project explores a safer resolution workflow that checks provider state against the merchant-side order record before taking action.

## What it does

- **Payment investigation:** Fetches payment information from Razorpay and compares it with the merchant-side order record.
- **AI-assisted diagnosis:** Uses Google's Gemini API to produce a human-readable explanation of a payment/order situation.
- **Payment reconciliation:** Applies deterministic checks before updating an eligible pending order. Financial mismatches should be blocked from automatic reconciliation.
- **Failed-payment recovery:** Evaluates eligible failed payments and can create a Razorpay Payment Link for a recovery attempt.
- **Recovery tracking:** Records recovery cases and resolution outcomes for the dashboard.
- **Dashboard:** Displays revenue at risk, recovered revenue, resolved cases, escalations, case details, and recent activity using the `/dashboard-data` endpoint.

## Safety principle

The language model is used for investigation and explanation; it should not be treated as the authority for financial state. Payment status and amount checks must be enforced in ordinary application code before a financial side effect is performed.

Example: if Razorpay reports ₹100 while the merchant's order expects ₹1,000, the application should stop the automated action and surface the case for review. It must not silently mark the order as paid or generate a recovery link from the mismatch.

## Technology

- Python
- FastAPI and Uvicorn
- Razorpay Python SDK
- Google Gemini (`google-genai`)
- `python-dotenv`
- HTML, CSS, and JavaScript for the dashboard (served by the FastAPI app)

Dependencies are listed in [`requirements.txt`](requirements.txt).

## Architecture

The application is organized around a FastAPI entry point and separate modules for provider access, data storage, AI diagnosis, reconciliation, and recovery decisions. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the component responsibilities and request flow.

## Run locally

### 1. Prerequisites

- Python 3.10 or newer (use the version tested by the project environment)
- A Razorpay **Test Mode** key ID and key secret
- A Google Gemini API key

### 2. Clone and create a virtual environment

```bash
git clone https://github.com/deepanshujoshi-ops/AI-Revenue-Resolution-Agent.git
cd AI-Revenue-Resolution-Agent
python -m venv .venv
```

Activate it:

**Windows PowerShell**

```powershell
.venv\Scripts\Activate.ps1
```

**macOS / Linux**

```bash
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure credentials

Create a local `.env` file in the repository root. Use the exact environment-variable names read by `app/razorpay_client.py` and `app/ai_agent.py` in the current source. Do not commit `.env`, paste secrets into issues, or place credentials in screenshots.

The checked-in `requirements.txt` includes `python-dotenv`; the exact variable names need to stay synchronized with the source modules. A safe `.env.example` should be added only after those names have been verified in the current code.

### 5. Start the API

From the repository root:

```bash
uvicorn app.main:app --reload
```

Open:

- Dashboard: http://127.0.0.1:8000/dashboard
- API documentation: http://127.0.0.1:8000/docs
- Health/status response: http://127.0.0.1:8000/

If the entry-point filename or import path has changed in your checked-out branch, use the module path that contains `FastAPI()` and the `app` object.

## Main API routes

The following routes are present in the implementation shared during project development. Confirm the current `app/main.py` before relying on them if the code has since changed.

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/` | Basic application status |
| `GET` | `/razorpay-test` | Check Razorpay API connectivity |
| `GET` | `/dashboard` | Serve the dashboard UI |
| `GET` | `/dashboard-data` | Return dashboard metrics and case data |
| `POST` | `/agent/analyze/{payment_id}` | Fetch payment and merchant order data, then request AI diagnosis |
| `POST` | `/test/create-order/{order_id}` | Create a local pending order for testing |
| `POST` | `/test/reconcile/{payment_id}` | Exercise the reconciliation flow for a Razorpay payment |
| `POST` | `/test/recover/{payment_id}` | Evaluate a payment for a recovery action |
| `POST` | `/test/simulate-failed` | Simulate a failed payment and create a Test Mode recovery link when eligible |
| `POST` | `/test/complete-recovery/{payment_id}` | Verify a captured recovery payment and record the outcome |
| `GET` | `/debug/order/{order_id}` | Inspect a local order record during development |

Interactive API documentation is available at `/docs` while the app is running. The `/test/*` and `/debug/*` routes are development utilities, not public production endpoints.

## Demo and verification

Use the [local demo guide](docs/DEMO_GUIDE.md) to walk through the dashboard, reconciliation, and failed-payment recovery. Run the application with Razorpay Test Mode credentials only.

Before describing this project as tested, run the demo steps yourself and record the actual outcomes. Do not publish made-up transaction counts, recovered-revenue totals, or performance metrics.

## Screenshots

Add genuine screenshots captured from a local run under `docs/images/` and embed them here after you have verified that they contain no API keys, customer data, payment IDs, phone numbers, or other sensitive information. A useful minimum is:

1. Dashboard overview with the four KPI cards.
2. A reconciliation case showing the before/after order state.
3. A mismatch case showing that the safety check blocks automated action.
4. A recovery case showing the generated Test Mode payment link and its recorded status.

Do not use fabricated dashboard data or screenshots from a different project.

## Current limitations and next steps

- This is a prototype, not a production-ready payment system.
- The local merchant-order store is a demonstration store, not an integration with an arbitrary merchant's production database.
- The test and debug routes need authentication or removal before any public deployment.
- The app needs automated tests for captured/pending reconciliation, amount mismatch, genuinely failed payments, recovery completion, and repeated requests.
- Recovery actions should be idempotent and linked to the exact original order and recovery-link ID; avoid relying on a global “open recovery case” when multiple cases can exist concurrently.
- Add a verified `.env.example`, a concise architecture diagram, and real screenshots after validating the current source.

## Security

- Keep all credentials in local environment variables.
- Use Razorpay Test Mode for development.
- Never commit `.env`, database files containing real customer data, logs with secrets, or payment/customer information.
- Do not deploy unauthenticated test or debug endpoints.
- Do not claim production readiness or real-money recovery unless that has been independently implemented and tested.

## Author

**Deepanshu Joshi**  
[GitHub](https://github.com/deepanshujoshi-ops)
