# Security Review

**Review update:** 2026-11-12
**Scope:** Production-hardening changes to the existing synthetic-data FastAPI demo. This is a code and regression-test review, not an external penetration test or production certification.

## Executive summary

Authentication, narrow CORS, basic per-client rate limiting, structured request logging, aggregate operational metrics, generic health probes, production configuration validation, and non-persistent benchmark export are implemented. The API remains read-only with respect to external infrastructure; its deterministic tools only query bundled fixtures and hold evidence in process memory.

**Recommendation: do not expose this service publicly or connect it to real incident data yet.** The bearer credential is a single shared secret without user identity, authorization roles, expiry, or revocation. HTTPS termination and external monitoring are not configured. The in-memory limiter is not a distributed abuse control. Docker build and runtime validation remain blocked because Docker is unavailable.

## Findings and controls

| Area | Current control | Status and limitation |
|---|---|---|
| API authentication | `AI_INVESTIGATOR_API_TOKEN` bearer token is required for every `/api/*` route except generic liveness/readiness probes. Production startup rejects a missing token, tokens outside 32–4096 characters, non-ASCII tokens, and whitespace. Comparisons use `secrets.compare_digest`. | **IMPLEMENTED / TESTED**. One shared, non-expiring credential; no identity, issuance, rotation, or revocation service. |
| Authorization / least privilege | No infrastructure mutation endpoints are exposed. Investigation is a read-only synthetic-data operation; benchmark evaluation no longer writes a file. | **LIMITED**. All authenticated users have the same read access. Fine-grained RBAC is not meaningful for the current single-role demo; per-user authorization is required before multi-tenant or sensitive-data use. The lexical mutation guard is not a sandbox. |
| Health and readiness | `/api/healthz` and `/api/readyz` return only generic process/readiness status. Detailed `/api/health` is authenticated. | **IMPLEMENTED / TESTED**. External service readiness does not apply because there are no external integrations. |
| CORS | Empty by default; exact origins are configured through `CORS_ALLOWED_ORIGINS`; wildcard origins are rejected; production origins must use HTTPS; credentials are disabled. | **IMPLEMENTED / CONFIG-TESTED**. Browser preflight was tested for an unapproved origin; a live approved-origin deployment was not tested. |
| Rate limiting | Fixed-window, per-remote-address API limit; defaults to 120 requests per 60 seconds; environment values are validated; rate-limited responses return 429 and `Retry-After`. | **IMPLEMENTED / TESTED**. State is in-memory and per worker, with no distributed coordination. A reverse proxy may collapse client addresses; enforce limits at the gateway as well. |
| Request/latency monitoring | JSON-line application request logs include request ID, method, route template, status, and duration. They deliberately omit raw URL, query string, request body, headers, credentials, and incident payload. Responses include request IDs and security headers. | **IMPLEMENTED / TESTED** for log redaction. No external log sink, retention controls, dashboard, alerting, or error-monitoring provider is configured. |
| Error handling | Unexpected application exceptions return a generic 500 response with request ID. Application error logs record only request ID and exception class, not exception messages or incident payloads. | **IMPLEMENTED / TESTED**. Infrastructure and proxy logs still require an equivalent redaction policy. |
| Operational metrics | Authenticated `/api/ops/metrics` exposes aggregate request/error/rate-limit counts, latency summaries, investigation duration/failure counts, and tool-failure count. No incident identifiers or payloads are included. | **IMPLEMENTED / TESTED**. In-memory counters reset on restart and are not a replacement for an external metrics/alerting system. |
| Browser data handling | The dashboard holds the bearer token only in JavaScript memory and requests it interactively after an API 401. Dynamic telemetry and diagnosis text is HTML-escaped before template rendering. | **IMPLEMENTED**. Token is lost on reload. Browser/XSS testing against hostile telemetry is not a separate certified assessment. |
| Data protection | This repository uses bundled synthetic fixtures only. Evidence and operational counters are in memory. Benchmark requests now return generated data without modifying `benchmark_results.json`. | **LIMITED**. No real-data redaction pipeline, persistent storage, backup, retention, or deletion service exists. Do not connect real telemetry. |
| Docker hardening | Non-root user, read-only root filesystem in Compose, dropped Linux capabilities, no-new-privileges, loopback-only host binding, health check, and bounded Uvicorn concurrency/keep-alive/shutdown settings are configured. | **CONFIGURED / NOT RUNTIME-VERIFIED**. Docker CLI is unavailable; image build, health check, and shutdown are **BLOCKED**. |
| TLS | The app serves HTTP. Compose binds to loopback to avoid direct network exposure. | **NOT CONFIGURED**. A separately managed HTTPS reverse proxy/load balancer is required before any network access. |
| Dependencies | Existing requirements remain minimum-version ranges without a lock file. | **WARNING**. Dependency vulnerability scanning and reproducible-build verification were not run. |

## Production environment variables

| Variable | Required behavior |
|---|---|
| `APP_ENV` | `development`, `test`, or `production`; production requires authentication. |
| `AI_INVESTIGATOR_API_TOKEN` | Production-only deployment secret; 32–4096 non-whitespace ASCII characters, supplied by a secret manager or protected process environment. Never commit it or put it in logs. |
| `CORS_ALLOWED_ORIGINS` | Optional comma-separated exact origins; production origins must be HTTPS. Same-origin dashboard/API use needs no CORS entry. |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | Integer from `1` to `100000`; default `120`. |
| `RATE_LIMIT_WINDOW_SECONDS` | Integer from `1` to `86400`; default `60`. |
| `LOG_LEVEL` | Standard Python logging level; default `INFO`. |

`.env.example` contains placeholders only. The Python process does not load `.env` itself; Docker Compose uses `.env` for interpolation, while local shell runs must receive variables through the shell or process manager.

## Data retention and deletion

The current app has no durable incident/evidence database. Synthetic fixtures are loaded from code and runbooks at startup. Evidence is process-local and may be replaced by a later investigation; process memory is lost at shutdown. Operational counters are also process-local. No backup is required for this demo's transient state. If real data is introduced, define data minimization, access, retention, deletion, backup, restore, and audit requirements before ingestion.

## Remaining high-priority risks

1. **High — shared-token authorization:** no individual identity, roles, credential expiry, or revocation. Store and rotate the secret externally; migrate to an identity provider before multi-user exposure.
2. **High — transport security:** HTTPS is not provided by the app. Require TLS at a controlled reverse proxy and do not expose the container port directly.
3. **High — operational controls:** no external alerting/error monitoring, durable audit trail, or centralized metrics.
4. **Medium — rate-limit scope:** limiter is process-local and depends on the socket peer address. Apply gateway-level quotas and load-test the deployed topology.
5. **High — real-data readiness:** no live connector, data redaction, persistence, retention, backup, or restore controls.
6. **Medium — dependency supply chain:** lock dependencies, scan them, and validate a reproducible image before release.
7. **Blocked — container evidence:** Docker build/runtime has not been exercised. See [`DEPLOYMENT_READINESS.md`](./DEPLOYMENT_READINESS.md) for exact validation steps.

## Verification

The latest focused tests cover missing/invalid/valid bearer tokens, production configuration validation, CORS allowlist validation, generic probes, rate limiting, aggregate metrics, tool-failure counters, benchmark file non-mutation, request-log redaction, and generic exception responses. See [`QA_TEST_PLAN.md`](./QA_TEST_PLAN.md) and [`FINAL_QA_REPORT.md`](./FINAL_QA_REPORT.md) for the complete test status and remaining blockers.
