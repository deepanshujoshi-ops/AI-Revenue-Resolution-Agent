# Security Review Before Sharing or Deploying

The repository is currently presented as a prototype. The following checks are required before treating it as production software.

- [ ] Confirm `.env` is ignored by Git and is not present in commit history.
- [ ] Rotate any credential that was ever committed or shared publicly.
- [ ] Confirm Razorpay credentials are Test Mode for demos.
- [ ] Add authentication and authorization to mutating routes.
- [ ] Disable or protect `/test/*` and `/debug/*` routes outside local development.
- [ ] Validate captured status, amount, currency, and order association before changing order state.
- [ ] Make reconciliation and recovery idempotent.
- [ ] Ensure recovery completion maps to the exact recovery link and order, not merely the first/open recovery case.
- [ ] Avoid logging secrets or unnecessary customer/payment data.
- [ ] Add tests for amount mismatch, duplicate requests, API failures, and recovery completion.

This list is a review checklist, not a claim that these controls have already been implemented.
