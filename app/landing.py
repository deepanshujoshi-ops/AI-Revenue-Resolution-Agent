"""
Introductory Landing Page for AI Revenue Resolution Agent
Razorpay Buildathon 2026
"""

LANDING_PAGE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Revenue Resolution Agent | Razorpay Buildathon</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #f8fafc;
            color: #0f172a;
            line-height: 1.6;
        }

        /* Top Banner */
        .top-banner {
            background: linear-gradient(90deg, #0284c7 0%, #0369a1 100%);
            color: white;
            text-align: center;
            padding: 9px 16px;
            font-size: 13px;
            font-weight: 600;
            letter-spacing: 0.2px;
        }

        .top-banner a {
            color: #bae6fd;
            text-decoration: underline;
            margin-left: 6px;
        }

        /* Navbar */
        .navbar {
            background: #ffffff;
            border-bottom: 1px solid #e2e8f0;
            padding: 18px 48px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .brand-logo {
            display: flex;
            align-items: center;
            gap: 12px;
            text-decoration: none;
            color: #0f172a;
        }

        .brand-icon {
            width: 38px;
            height: 38px;
            background: #0284c7;
            color: white;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            font-size: 18px;
        }

        .brand-title {
            font-size: 18px;
            font-weight: 700;
            letter-spacing: -0.3px;
        }

        .brand-tag {
            font-size: 11px;
            color: #64748b;
            font-weight: 500;
        }

        .nav-links {
            display: flex;
            align-items: center;
            gap: 24px;
        }

        .nav-link {
            text-decoration: none;
            color: #475569;
            font-size: 14px;
            font-weight: 600;
            transition: color 0.15s ease;
        }

        .nav-link:hover {
            color: #0284c7;
        }

        .btn-launch {
            background: #0284c7;
            color: white;
            text-decoration: none;
            padding: 10px 20px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            box-shadow: 0 2px 6px rgba(2, 132, 199, 0.25);
            transition: all 0.2s ease;
        }

        .btn-launch:hover {
            background: #0369a1;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(2, 132, 199, 0.35);
        }

        /* Hero */
        .hero {
            max-width: 1200px;
            margin: 60px auto 40px;
            padding: 0 24px;
            text-align: center;
        }

        .badge-pill {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: #e0f2fe;
            color: #0369a1;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.6px;
            margin-bottom: 22px;
            border: 1px solid #bae6fd;
        }

        .hero h1 {
            font-size: 46px;
            font-weight: 800;
            color: #0f172a;
            line-height: 1.18;
            letter-spacing: -1.2px;
            max-width: 920px;
            margin: 0 auto 20px;
        }

        .hero h1 span {
            color: #0284c7;
        }

        .hero p {
            font-size: 19px;
            color: #475569;
            max-width: 760px;
            margin: 0 auto 36px;
            line-height: 1.6;
        }

        .hero-ctas {
            display: flex;
            justify-content: center;
            gap: 14px;
            margin-bottom: 40px;
            flex-wrap: wrap;
        }

        .btn-hero-primary {
            background: #0284c7;
            color: white;
            text-decoration: none;
            padding: 14px 28px;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 700;
            display: inline-flex;
            align-items: center;
            gap: 10px;
            box-shadow: 0 4px 14px rgba(2, 132, 199, 0.35);
            transition: all 0.2s ease;
        }

        .btn-hero-primary:hover {
            background: #0369a1;
            transform: translateY(-2px);
        }

        .btn-hero-secondary {
            background: #ffffff;
            color: #334155;
            text-decoration: none;
            padding: 14px 26px;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 600;
            border: 1px solid #cbd5e1;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            transition: all 0.2s ease;
        }

        .btn-hero-secondary:hover {
            background: #f1f5f9;
            border-color: #94a3b8;
        }

        /* Pillars Bar */
        .pillars {
            display: flex;
            justify-content: center;
            gap: 28px;
            margin-bottom: 70px;
            flex-wrap: wrap;
        }

        .pillar-item {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
            font-weight: 600;
            color: #334155;
            background: white;
            padding: 8px 16px;
            border-radius: 20px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.03);
        }

        .pillar-item span {
            color: #059669;
            font-weight: bold;
        }

        /* Philosophy Callout */
        .philosophy-banner {
            max-width: 1080px;
            margin: 0 auto 70px;
            background: #0f172a;
            color: white;
            border-radius: 16px;
            padding: 36px 44px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 30px;
            box-shadow: 0 12px 30px rgba(15, 23, 42, 0.12);
        }

        .philosophy-text h3 {
            font-size: 24px;
            font-weight: 800;
            margin-bottom: 8px;
            letter-spacing: -0.3px;
            color: #38bdf8;
        }

        .philosophy-text p {
            color: #cbd5e1;
            font-size: 15px;
            line-height: 1.6;
        }

        .philosophy-badges {
            display: flex;
            flex-direction: column;
            gap: 10px;
            min-width: 240px;
        }

        .phi-pill {
            background: #1e293b;
            border: 1px solid #334155;
            padding: 8px 14px;
            border-radius: 8px;
            font-size: 13px;
            color: #f1f5f9;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .phi-pill strong {
            color: #38bdf8;
        }

        /* Section Container */
        .section-wrap {
            max-width: 1120px;
            margin: 0 auto 80px;
            padding: 0 24px;
        }

        .section-title-wrap {
            text-align: center;
            margin-bottom: 44px;
        }

        .section-tag {
            color: #0284c7;
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            margin-bottom: 8px;
        }

        .section-title {
            font-size: 32px;
            font-weight: 800;
            color: #0f172a;
            letter-spacing: -0.6px;
        }

        .section-subtitle {
            font-size: 16px;
            color: #64748b;
            margin-top: 6px;
        }

        /* Guide Steps */
        .steps-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            margin-bottom: 50px;
        }

        .step-box {
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 14px;
            padding: 26px 20px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.03);
            position: relative;
            display: flex;
            flex-direction: column;
        }

        .step-circle {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            background: #0284c7;
            color: white;
            font-weight: 800;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
            margin-bottom: 16px;
        }

        .step-box h4 {
            font-size: 16px;
            font-weight: 700;
            color: #0f172a;
            margin-bottom: 8px;
        }

        .step-box p {
            font-size: 13px;
            color: #64748b;
            line-height: 1.55;
        }

        /* Scenario Cards */
        .scenarios-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 24px;
        }

        .scenario-card {
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 14px;
            padding: 28px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
            display: flex;
            flex-direction: column;
            border-top: 4px solid #0284c7;
        }

        .scenario-card.green-top {
            border-top-color: #059669;
        }

        .scenario-card.orange-top {
            border-top-color: #d97706;
        }

        .scenario-card.red-top {
            border-top-color: #dc2626;
        }

        .scenario-badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 700;
            margin-bottom: 14px;
            width: fit-content;
        }

        .scenario-badge.green { background: #d1fae5; color: #065f46; }
        .scenario-badge.orange { background: #fef3c7; color: #92400e; }
        .scenario-badge.red { background: #fee2e2; color: #991b1b; }

        .scenario-card h3 {
            font-size: 18px;
            font-weight: 700;
            color: #0f172a;
            margin-bottom: 10px;
        }

        .scenario-card p {
            font-size: 14px;
            color: #64748b;
            line-height: 1.6;
            margin-bottom: 16px;
            flex: 1;
        }

        .scenario-outcome {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 12px 14px;
            font-size: 12px;
            color: #334155;
        }

        .scenario-outcome strong {
            color: #0f172a;
            display: block;
            margin-bottom: 4px;
        }

        /* Final CTA */
        .final-cta {
            background: linear-gradient(135deg, #0284c7 0%, #075985 100%);
            color: white;
            border-radius: 20px;
            padding: 60px 40px;
            text-align: center;
            max-width: 1080px;
            margin: 0 auto 80px;
            box-shadow: 0 16px 40px rgba(2, 132, 199, 0.2);
        }

        .final-cta h2 {
            font-size: 36px;
            font-weight: 800;
            margin-bottom: 14px;
            letter-spacing: -0.6px;
        }

        .final-cta p {
            font-size: 17px;
            color: #e0f2fe;
            max-width: 620px;
            margin: 0 auto 30px;
            line-height: 1.6;
        }

        .btn-white {
            background: #ffffff;
            color: #0369a1;
            text-decoration: none;
            padding: 15px 32px;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 700;
            display: inline-flex;
            align-items: center;
            gap: 10px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            transition: all 0.2s ease;
        }

        .btn-white:hover {
            background: #f8fafc;
            transform: translateY(-2px);
        }

        /* Footer */
        .footer {
            border-top: 1px solid #e2e8f0;
            padding: 28px 48px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: white;
            color: #64748b;
            font-size: 13px;
        }

        @media (max-width: 900px) {
            .steps-grid,
            .scenarios-grid {
                grid-template-columns: 1fr;
            }

            .philosophy-banner {
                flex-direction: column;
                text-align: center;
            }

            .navbar {
                padding: 16px 24px;
            }

            .hero h1 {
                font-size: 34px;
            }
        }
    </style>
</head>
<body>

    <div class="top-banner">
        ⚡ Built for <strong>Razorpay Buildathon 2026</strong> • Autonomous Payment Recovery & Reconciliation
    </div>

    <nav class="navbar">
        <a href="/" class="brand-logo">
            <div class="brand-icon">₹</div>
            <div>
                <div class="brand-title">Revenue Resolution Agent</div>
                <div class="brand-tag">Autonomous Razorpay AI Agent</div>
            </div>
        </a>

        <div class="nav-links">
            <a href="#how-it-works" class="nav-link">How It Works</a>
            <a href="#scenarios" class="nav-link">Demo Scenarios</a>
            <a href="#philosophy" class="nav-link">Safety Model</a>
            <a href="/dashboard" class="btn-launch">
                🚀 Launch Agent Dashboard →
            </a>
        </div>
    </nav>

    <!-- Hero Section -->
    <section class="hero">
        <div class="badge-pill">
            🛡️ Razorpay Test Mode Ready • Deterministic Financial Controls
        </div>

        <h1>
            Autonomous Revenue Recovery for <span>Razorpay Merchants</span>
        </h1>

        <p>
            When a customer pays but a webhook drops, your store still says "Pending". 
            Our agent detects the discrepancy, diagnoses the state with Gemini, verifies fiduciary safety with deterministic rules, and reconciles orders without charging twice.
        </p>

        <div class="hero-ctas">
            <a href="/dashboard" class="btn-hero-primary">
                🚀 Use Agent / Launch Dashboard →
            </a>
            <a href="#how-to-use" class="btn-hero-secondary">
                📖 How to Use This Agent ↓
            </a>
        </div>

        <div class="pillars">
            <div class="pillar-item"><span>✓</span> Zero Customer Double-Charges</div>
            <div class="pillar-item"><span>✓</span> Sub-Second Webhook Reconciliation</div>
            <div class="pillar-item"><span>✓</span> Automated Razorpay Payment Links</div>
            <div class="pillar-item"><span>✓</span> Deterministic Policy Gatekeeper</div>
        </div>
    </section>

    <!-- Core Philosophy Banner -->
    <div class="philosophy-banner" id="philosophy">
        <div class="philosophy-text">
            <h3>AI reasons. Policy controls. Agent executes.</h3>
            <p>
                In fintech, giving an LLM unconstrained access to your ledger is dangerous. 
                We use Gemini strictly as diagnostic intelligence, while a deterministic Policy Engine acts as the fiduciary gatekeeper—mathematically verifying amount integrity, capture status, and idempotency before executing.
            </p>
        </div>

        <div class="philosophy-badges">
            <div class="phi-pill"><strong>1. AI Diagnosis:</strong> Gemini Reasoning</div>
            <div class="phi-pill"><strong>2. Safety Guard:</strong> Deterministic Policy</div>
            <div class="phi-pill"><strong>3. Execution:</strong> Safe Mutation & Audit</div>
        </div>
    </div>

    <!-- How to Use Section -->
    <section class="section-wrap" id="how-to-use">
        <div class="section-title-wrap">
            <div class="section-tag">Quick Start Guide</div>
            <h2 class="section-title">How to Use This Agent</h2>
            <div class="section-subtitle">A simple 4-step walkthrough for judges and merchants</div>
        </div>

        <div class="steps-grid" id="how-it-works">
            <div class="step-box">
                <div class="step-circle">1</div>
                <h4>Launch Dashboard</h4>
                <p>Click <strong>"Launch Agent Dashboard"</strong> to access real-time metrics: Revenue at Risk, Revenue Recovered, and Resolution Cases.</p>
            </div>

            <div class="step-box">
                <div class="step-circle">2</div>
                <h4>Select a Demo Trigger</h4>
                <p>Use the 1-Click Interactive Sandbox bar to simulate real-world payment anomalies (Webhook Drops, Failed Checkouts, or Tamper Attacks).</p>
            </div>

            <div class="step-box">
                <div class="step-circle">3</div>
                <h4>Inspect Execution Trace</h4>
                <p>Watch the 4-Step Pipeline execute live: Gateway state ingestion, Gemini diagnosis, Policy Engine rule checks, and safe resolution.</p>
            </div>

            <div class="step-box">
                <div class="step-circle">4</div>
                <h4>Track Ledger & Links</h4>
                <p>See orders marked PAID or live Razorpay recovery links generated instantly, recorded in an immutable audit log.</p>
            </div>
        </div>
    </section>

    <!-- Demo Scenarios Section -->
    <section class="section-wrap" id="scenarios">
        <div class="section-title-wrap">
            <div class="section-tag">Interactive Scenarios</div>
            <h2 class="section-title">3 Interactive Scenarios </h2>
            <div class="section-subtitle">Click these buttons in the dashboard to demonstrate the agent live</div>
        </div>

        <div class="scenarios-grid">
            <div class="scenario-card green-top">
                <span class="scenario-badge green">SCENARIO 1 • RECONCILIATION</span>
                <h3>🟢 Webhook Drop Desync</h3>
                <p>
                    A customer paid ₹100. Razorpay marked payment as <strong>CAPTURED</strong>, but your store DB timed out and still says <strong>PENDING</strong>.
                </p>
                <div class="scenario-outcome">
                    <strong>Agent Resolution:</strong>
                    AI diagnoses `PAYMENT_STATE_MISMATCH`. Policy approves `MARK_ORDER_PAID`. Reconciled without recharging customer.
                </div>
            </div>

            <div class="scenario-card orange-top">
                <span class="scenario-badge orange">SCENARIO 2 • RECOVERY</span>
                <h3>⚡ Failed Payment Recovery</h3>
                <p>
                    Customer's card was declined or checkout was abandoned at Razorpay gateway. Revenue is stuck at risk.
                </p>
                <div class="scenario-outcome">
                    <strong>Agent Resolution:</strong>
                    AI diagnoses `PAYMENT_FAILED`. Policy approves `CREATE_RECOVERY_LINK`. Generates a real Razorpay payment link.
                </div>
            </div>

            <div class="scenario-card red-top">
                <span class="scenario-badge red">SCENARIO 3 • SAFETY VETO</span>
                <h3>🛡️ Tamper & Hallucination Guard</h3>
                <p>
                    Corrupted webhook or malicious request: Gateway captured ₹100, but merchant order expects ₹1,000.
                </p>
                <div class="scenario-outcome">
                    <strong>Agent Resolution:</strong>
                    Policy Engine issues hard <strong>SAFETY VETO</strong>: Amount mismatch detected. Order remains unpaid and escalates.
                </div>
            </div>
        </div>
    </section>

    <!-- Final Call to Action -->
    <div class="final-cta">
        <h2>Experience the Autonomous Agent Live</h2>
        <p>
            Ready to record your demo or test live payment scenarios? Launch the dashboard to see Gemini and our Policy Engine in action.
        </p>
        <a href="/dashboard" class="btn-white">
            🚀 Launch Agent Dashboard →
        </a>
    </div>

    <!-- Footer -->
    <footer class="footer">
        <div>AI Revenue Resolution Agent • Built for Razorpay Buildathon 2026</div>
        <div>FastAPI • Gemini 2.5 • Razorpay Test Mode • SQLite</div>
    </footer>

</body>
</html>
"""
