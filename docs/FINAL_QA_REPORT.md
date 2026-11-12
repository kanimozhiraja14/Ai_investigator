# Final QA Report

## Current release decision (2026-11-12)

**Local synthetic-data demo: PASS. Public/production deployment: FAIL.** The previous audit's 44-test baseline now has 10 focused hardening tests; the complete post-change suite passes **54 tests**. A production-configured Uvicorn smoke test verified generic probes, unauthenticated 401, authenticated fixture access, and operational metrics. Browser validation verified the in-app bearer-token dialog and confirmed hostile log text renders as text rather than an HTML element.

Implemented: production-required shared bearer token, environment validation, exact-origin CORS configuration, per-process API rate limiting, redacted structured request/error logs, generic liveness/readiness probes, aggregate operational metrics, dashboard HTML escaping, non-persistent benchmark export, and hardened-but-unverified container settings.

Remaining blockers: no per-user identity/RBAC or credential revocation, no TLS termination, no distributed gateway rate control, no external monitoring/alerting, no real-data redaction/retention/persistence/backup, no dependency scan/lock, and **Docker runtime validation BLOCKED** because Docker is unavailable. Do not expose publicly or connect real incident telemetry.

## 1. Executive summary

The application starts and its local synthetic incident workflow works for the 10 bundled scenarios. The complete post-hardening automated suite passed **54/54 tests**. Prior browser coverage exercised the eight navigation sections, filtering, both investigation modes, evidence, trace, error states, and a 390px viewport; current browser testing verified authenticated dashboard startup and hostile telemetry escaping.

The system is a deterministic Python demo, not an LLM-based investigator and not a production service. Baseline controls were added, but public deployment remains **not recommended**. Docker build and runtime are **BLOCKED**.

## 2. Architecture and modules tested

| Component | Status | Notes |
|---|---|---|
| FastAPI routes and Pydantic schemas | **PASS** | Route, method, response, invalid input, and unknown-ID tests. |
| `telemetry.py` fixture store | **PASS** | 10 synthetic incidents with fixture logs, metrics, and deployments. No live telemetry connector or database. |
| `runbook_retriever.py` | **PASS** | BM25-style lexical index over 10 Markdown runbooks, with service boost. No embeddings/vector search. |
| `correlation_engine.py` | **PASS** | UTC normalization, before/after filtering, ordering, and malformed timestamp handling tested. |
| `tools.py` | **PASS** | Six read-only query/assessment methods; keyword guard does not create an isolation boundary. |
| `investigator.py` | **PASS for fixture set** | Fixed signal-matching diagnosis rules; shared evidence registry serialized to avoid concurrent cross-contamination. |
| `baseline.py` / `benchmark.py` | **PASS** | Same heuristic helper evaluates both methods; output is not human-reviewed accuracy. |
| Static dashboard | **PASS** | Eight sections, filters, selection, evidence modal, trace, error and empty states, mobile width. |

No model API, SQL database, persistent evidence store, cloud telemetry connector, or executing remediation path is present.

## 3. API tests

All implemented API and documentation/static routes were exercised through FastAPI `TestClient`; the dashboard was also loaded through Uvicorn in a browser.

- **PASS:** success responses for health, stats, incident list/detail, evidence, logs, metrics, deployments, runbook search/detail, both investigation modes, trace, benchmark, and export.
- **PASS:** `/`, `/docs`, `/redoc`, `/openapi.json`, `/static/app.js`, and `/static/style.css`.
- **PASS:** unknown incident/runbook IDs return 404; missing required query parameters and invalid mode/limit return 422; wrong method returns 405.
- **PASS:** missing and invalid bearer tokens return 401; a valid token accesses protected API routes. OpenAPI now documents the bearer scheme.
- **PASS:** generic `/api/healthz` and `/api/readyz` remain unauthenticated; detailed `/api/health` and `/api/ops/metrics` are protected.
- **PASS:** an unapproved CORS preflight is rejected; wildcard origins are rejected by configuration.
- **PASS:** `/api/ops/metrics` returns aggregate-only values; benchmark and export do not modify `benchmark_results.json`.
- **PASS:** unexpected application exceptions return a generic 500 with request ID and omit the exception message from application logs.

## 4. Pipeline stage results

| Stage | Status | Result |
|---|---|---|
| Incident input and validation | **PASS** | Known fixture accepted; unknown IDs rejected with 404 at API boundary. |
| BM25 runbook retrieval | **PASS** | Expected runbook ranked first for all 10 curated alert/service queries. |
| Tool selection and execution | **PASS** | Six implemented tool methods exercised; trace records six orchestration calls. |
| Temporal correlation | **PASS** | Window boundaries, offset timestamps, ordering, and invalid values covered. |
| Evidence capture | **PASS** | Every trace evidence reference resolves; correlation result now has its own evidence item. Evidence remains mutable and in memory. |
| Root-cause diagnosis | **PASS for known fixtures** | Category matched documented fixture category for 10/10. No generalization claim. |
| Risk assessment | **PASS for fixtures** | Fixed category/severity mapping returns risk, CWE/CIA, blast radius, and SLA values. External validity **NOT TESTED**. |
| Final report and dashboard | **PASS** | Successful responses render; failures clear stale results and show an explicit error. |
| Claim-level support audit | **WARNING** | `unsupported_claims` is empty for investigator cases, but no independent claim-to-evidence validator exists. |

## 5. Six tool results

| Tool | Status | Result |
|---|---|---|
| `search_runbooks` | **PASS** | Valid, empty, irrelevant, and guarded mutation-like query cases. |
| `correlate_signals` | **PASS** | Known/unknown IDs, windows, timezone ordering, invalid/missing timestamps; correlation evidence linked into trace. |
| `get_deployments` | **PASS** | Valid and unknown incident inputs, read-only guard, evidence output. |
| `query_logs` | **PASS** | Valid and unknown incident inputs, read-only guard, evidence output. |
| `query_metrics` | **PASS** | Valid and unknown incident inputs; unique evidence IDs preserve all INC-001 samples. |
| `assess_security_risk` | **PASS** | Valid and unknown incident inputs; risk values are fixed rules, not an independently validated model. |

**Timeout handling: NOT TESTED.** These tools use local in-memory data and have no external operations with configurable timeouts.

## 6. Ten-scenario end-to-end results

All ten categories match their fixture ground-truth categories. Retrieval result is the top-1 runbook for the fixture's initial alert/service. The unsupported count is the investigator's reported field, not an independent audit result. Durations are the investigator's rounded in-process measurements and are too small to treat as service-level performance.

| ID | Expected root cause (fixture) | Actual investigator hypothesis | Top runbook | Correlation D/L/M | Evidence | Risk | Unsupported flags | Duration | Status |
|---|---|---|---|---:|---:|---|---:|---:|---|
| INC-001 | Missing `STRIPE_WEBHOOK_SECRET` in v2.4.1 caused payment webhook failure. | Missing secret in DEP-101 caused `NullPointerException` in `WebhookHandler`. | `payment_service_5xx` | 1/4/3 | 16 | CRITICAL | 0* | 0.0007 s | **PASS** |
| INC-002 | Unindexed analytics query occupied all 50 connection-pool slots. | Long-running unindexed orders query exhausted the 50-slot pool. | `db_connection_pool` | 0/3/2 | 13 | CRITICAL | 0* | 0.0004 s | **PASS** |
| INC-003 | Logrotate permission failure plus debug logs filled the 50GB partition. | Logrotate permission failure and unrotated debug logs exhausted disk. | `disk_space_exhaustion` | 0/3/1 | 11 | HIGH | 0* | 0.0003 s | **PASS** |
| INC-004 | Unbounded reservation cache without TTL/eviction caused OOM. | Unbounded reservation cache caused OOM and pod restarts. | `oom_memory_leak` | 0/3/0 | 12 | CRITICAL | 0* | 0.0003 s | **PASS** |
| INC-005 | SendGrid packet drops without timeout/circuit breaker blocked workers. | 30-second upstream socket timeouts without circuit breaker exhausted workers. | `third_party_degradation` | 0/3/1 | 11 | HIGH | 0* | 0.0003 s | **PASS** |
| INC-006 | Expired Cloudflare token stopped certificate renewal before expiry. | Failed cert-manager renewal after Cloudflare token expiry caused TLS outage. | `ingress_ssl_expiry` | 0/3/1 | 10 | CRITICAL | 0* | 0.0003 s | **PASS** |
| INC-007 | Hot cache key expired without locking/jitter and stampeded Postgres. | 12,000 requests hit Postgres after hot-key expiration. | `redis_cache_stampede` | 0/2/2 | 10 | CRITICAL | 0* | 0.0003 s | **PASS** |
| INC-008 | Missing `real_ip_header` grouped users under an internal node IP. | Proxy configuration collapsed traffic into the node-IP rate-limit bucket. | `rate_limiting_misconfig` | 1/2/2 | 10 | HIGH | 0* | 0.0004 s | **PASS** |
| INC-009 | Poison-pill decimal caused regex hang and consumer rebalance loop. | Poison pill at offset 8492048 hung validation past `max.poll.interval.ms`. | `kafka_consumer_lag` | 0/2/2 | 10 | CRITICAL | 0* | 0.0003 s | **PASS** |
| INC-010 | Vault key rotation left a stale 24-hour JWKS cache. | Rotated key with stale JWKS cache caused inter-service 401s. | `jwt_auth_rotation_failure` | 0/3/2 | 10 | CRITICAL | 0* | 0.0005 s | **PASS** |

`D/L/M` = correlated deployments / error-or-fatal logs / metric anomalies. `*` Zero is the returned field value; it is **not** evidence that each natural-language claim was independently verified.

## 7. Evidence validation

- INC-001 returned 16 evidence items, including all 7 metric samples; IDs are distinct after the metric-ID fix.
- The ten scenario results returned 10–16 evidence items each.
- Correlation is represented by a `CORRELATION` item; trace evidence references resolve in the response's evidence chain.
- A five-thread concurrency regression verifies that the shared global registry is serialized and each result retains its own correlation evidence.
- **WARNING:** evidence and raw payloads are process-local, mutable, and not cryptographically hashed or durable. Root-cause text has no per-claim citation structure. Re-running an investigation clears the prior shared registry.

## 8. Frontend results

- **PASS:** all eight sections (Overview, Incident Roster, Investigation Hub, Evidence Explorer, Risk/CWE, Benchmark, Execution Trace, System Health).
- **PASS:** incident search/filter, incident selection, AI-labeled multi-step mode, keyword baseline, evidence filtering and modal.
- **PASS:** apostrophe-containing runbook evidence opens in the modal; dynamic evidence rows no longer use inline JavaScript.
- **PASS:** empty roster state, investigation HTTP 503 error state, loading controls, and clearing stale diagnosis/evidence/risk/trace on failure.
- **PASS:** 390px viewport had no horizontal document overflow.
- **PASS:** production-configured dashboard token dialog connects and loads the 10 fixture rows; token input is cleared after submission and not persisted.
- **PASS:** hostile `<img onerror>` log content rendered as text; no image element was created.
- **PASS:** no uncaught JavaScript page errors in the authenticated browser run. Initial unauthorized requests generated expected HTTP 401 resource-error console entries before the token was submitted.
- **WARNING:** the “AI” branding is a project name; investigation is deterministic Python logic, not an LLM.

## 9. Security findings

| Finding | Severity | Status |
|---|---|---|
| Shared bearer token, no identity/role/expiry/revocation | High for multi-user exposure | **IMPLEMENTED baseline / BLOCKER remains** |
| HTTPS termination absent | High | **FAIL** for network exposure |
| CORS origin allowlist | Medium | **IMPLEMENTED**; live approved-origin deployment not tested |
| Read-only guard is lexical input filtering, not process isolation | High if treated as a sandbox | **WARNING**; explicitly not a production security boundary |
| Rate limiting | Medium | **IMPLEMENTED per process**; gateway limits still required |
| Request/error log redaction | High for sensitive data | **PASS** in application regression tests; infrastructure logs not assessed |
| Real-data redaction / retention | High | **FAIL**; real telemetry is unsupported |
| In-memory mutable evidence registry | Integrity / availability limitation | **WARNING**; concurrency serialized, not durable/tamper-evident |
| Benchmark GET route writes a JSON file | Unexpected state change for GET | **FIXED / TESTED**; export is in memory |
| External monitoring / alerting | High for operations | **NOT CONFIGURED**; aggregate local metrics only |
| Dependency vulnerability scan | Unknown | **NOT TESTED** |
| Docker build/runtime | Deployment evidence | **BLOCKED**; Docker CLI unavailable |

No destructive actions were run against real infrastructure.

## 10. Benchmark and performance

The benchmark compared 10 bundled scenarios and now applies the same `_evaluate_correctness()` text heuristic to investigator and baseline diagnoses:

| Metric | Investigator | Keyword baseline | Qualification |
|---|---:|---:|---|
| Project heuristic correctness | 100% (10/10) | 0% (0/10) | Not human-reviewed; not independent model evaluation |
| Mean in-process diagnosis time | ~0.0007 s | ~0.0001 s | Rounded Python timings; below useful benchmark resolution |
| Mean evidence items | 11.3 | 3.0 | Evidence counts, not evidence quality |
| Unsupported-claim field | 0.0 | 1.8 per scenario | Investigator check is not independent; baseline figure is a mean count, not a validated rate |
| Retrieval top-1 | 10/10 curated queries | N/A | Fixture mapping only; no broad recall estimate |

The previous audit's 25-request `TestClient` samples measured median/p95 client-side times of 9.912/12.692 ms for health, 8.665/10.797 ms for incident listing, and 8.258/11.596 ms for INC-001 investigation. These are **pre-hardening historical values** and do not include the new authentication, rate-limit, and logging middleware; no post-hardening latency or load measurement was performed.

## 11. Bugs fixed

1. Unknown incident IDs for evidence, logs, metrics, and deployments previously returned misleading empty/success responses or 500; API and tools now reject unknown IDs.
2. Metric evidence IDs collided for same-service/same-metric records; timestamp-qualified IDs preserve samples.
3. Evidence inspection used inline JavaScript quoting and failed on apostrophes; DOM event listeners and text nodes now handle these values.
4. Overview KPIs and health cards used hard-coded or production-sounding values; the dashboard now derives counts and reports only synthetic in-memory component status.
5. Correlation ignored configured windows, string-sorted timestamps, and treated after-start deployment as causal; it now filters and UTC-sorts events and validates timestamps/windows.
6. Unknown risk assessment fabricated a critical fallback; it now raises an error for unknown incidents.
7. Benchmark previously evaluated investigator and baseline with different correctness logic; both now use the same helper.
8. Correlation results were absent from the evidence chain; they are now registered and referenced by the trace.
9. Concurrent investigations could clear/interleave a global evidence registry; the investigator now serializes access, with a concurrency regression.
10. UI failures retained stale results and the roster lacked a no-match state; both are corrected.
11. CORS allowed credentials with wildcard origins; credentialed CORS is disabled.
12. The CLI runner used Unicode output that failed under a Windows cp1252 console and did not fail when a mutation blocker failed; output is ASCII and failed guard checks raise.
13. Confidence and security UI/documentation overstated calibration, sandboxing, and claim auditing; language now reflects the implemented heuristic and guard limits.
14. Unauthenticated API access and wildcard CORS were replaced with production-validated bearer auth and an exact-origin allowlist.
15. Request handling gained per-process rate limiting, request IDs, redacted JSON-line access/error logs, generic error responses, security headers, and aggregate operational metrics.
16. The dashboard's browser `prompt()` token flow was replaced with an explicit password-field dialog after browser automation showed prompts were unsupported; dynamic telemetry strings are escaped before HTML rendering.
17. Benchmark HTTP calls no longer write the snapshot file; a regression test verifies the file remains unchanged.
18. Container startup/health/shutdown settings were hardened in Dockerfile/Compose, but runtime status remains blocked pending Docker validation.

## 12. Outstanding issues and blockers

- No per-user identity, roles, credential expiry/revocation, or real-data access control.
- HTTPS termination and gateway request limits are not configured.
- The in-memory rate limiter is process-local and cannot replace gateway controls.
- No external monitoring/alerting, real telemetry connector, redaction pipeline, persistent evidence store, or data retention/backup implementation.
- No independent claim-to-evidence verifier or human-reviewed diagnosis benchmark.
- No external dependency vulnerability scan; dependency ranges are not locked.
- Docker image build/runtime could not be validated because Docker CLI is unavailable.
- `.env.example` values are not automatically loaded by the Python process; deployment environment injection is required.
- No external service timeout, network outage, load, or resilience test applies to the current in-memory implementation.

## 13. Deployment recommendation

- **Local portfolio demo:** **PASS**, using only bundled synthetic data.
- **Network-exposed demo:** **BLOCKED** pending HTTPS termination, gateway controls, secret management, and Docker runtime validation.
- **Public deployment with real or sensitive data:** **FAIL** until the blockers in [`DEPLOYMENT_READINESS.md`](./DEPLOYMENT_READINESS.md) are closed and independently validated.

The older architecture, API, security, deployment, testing, and benchmark pages now carry audit-status warnings because they contain stale or unsupported implementation claims.
