# Runbook: Upstream Third-Party Dependency Degradation & Network Timeouts

**Service:** notification-service  
**Severity:** P2  
**Category:** UPSTREAM_DEPENDENCY  

## Symptoms
- Alert: `NotificationQueueLagHigh` firing (> 20,000 pending items).
- Downstream delivery latencies exceeding SLA (> 60s).
- Worker threads blocking on HTTP socket read operations.

## Diagnostic Steps
1. Query external outbound request latency metrics: `external_http_request_duration_seconds`.
2. Inspect worker logs for `ConnectTimeoutException` or `Read timed out` against third-party hosts.
3. Check status page or DNS resolution for third-party provider (e.g. `api.sendgrid.com`).
4. Verify circuit breaker state metrics (`resilience4j_circuitbreaker_state`).

## Root Cause Patterns
- External SaaS vendor undergoing outage or throttling API clients.
- Missing circuit breaker or socket read timeout allowing hung connections to starve worker threadpool.

## Mitigation
1. Trip circuit breaker manually to activate fallback queue or secondary provider (e.g. AWS SES).
2. Reduce socket read timeout from 60s to 5s to fail-fast.
3. Scale out notification consumer workers once upstream connectivity stabilizes.
