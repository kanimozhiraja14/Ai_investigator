# Runbook: Misconfigured Rate Limiter False Positive Throttling

**Service:** api-gateway  
**Severity:** P2  
**Category:** RATE_LIMIT_MISCONFIG  

## Symptoms
- Alert: `RateLimitExceededSurge` (HTTP 429 response rate > 15%).
- Widespread reports from regular authenticated users receiving "Too Many Requests".
- Total system RPS is normal or low, but rate limiter rejects requests.

## Diagnostic Steps
1. Query `http_requests_total{status="429"}` grouped by client IP or bucket key.
2. Inspect gateway access logs for client IP extracted by rate limit middleware.
3. Check reverse proxy header forwarding config (`X-Forwarded-For`, `X-Real-IP`).
4. Verify if rate limiter is evaluating the Kubernetes node IP rather than real client IP.

## Root Cause Patterns
- Gateway misconfiguration extracted ingress pod/node IP instead of real client IP from `X-Forwarded-For`.
- Rate limit bucket key collapsed all global traffic into a single shared bucket.

## Mitigation
1. Update ingress configmap: set `use-forwarded-headers: "true"` and `real-ip-header: "X-Forwarded-For"`.
2. Temporarily raise rate limit threshold while config updates propagate.
3. Reload API gateway deployment to apply corrected IP extraction rules.
