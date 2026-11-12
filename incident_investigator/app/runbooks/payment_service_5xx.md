# Runbook: Payment Service HTTP 500 Spike

**Service:** payment-service  
**Severity:** P1  
**Category:** BAD_DEPLOYMENT  

## Symptoms
- Alert: `PaymentServiceHighErrorRate` firing (5xx rate > 5%).
- Customers seeing "Payment Gateway Failure" at checkout.
- Sudden spike in HTTP 500 internal server errors.

## Diagnostic Steps
1. Query deployment events for `payment-service` within 30 minutes before incident start.
2. Inspect application error logs filtering for `level=ERROR` and `level=FATAL`.
3. Check for stack traces mentioning `NullPointerException` or missing configuration variables.
4. Verify environment variable declarations against the deployment commit diff.
5. Check `http_requests_total{status=~"5.."}` metric vs previous baseline.

## Root Cause Patterns
- Recent rollout introduced unhandled null references or missing environment secrets (e.g. `STRIPE_WEBHOOK_SECRET`, `PAYMENT_API_KEY`).
- Code changes in request validation logic failing on specific payload fields.

## Mitigation
1. Execute immediate canary rollback: `kubectl rollout undo deployment/payment-service`.
2. Verify rollback completion and check error rate drops below 0.1%.
3. Re-inject missing environment variables in Helm chart before redeploying.
