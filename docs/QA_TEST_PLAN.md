# QA Test Plan and Execution Results

## Objective

Exercise the implemented local demo workflow and its failure boundaries without connecting to real infrastructure. This plan distinguishes deterministic fixture checks from claims that would require human evaluation or production services.

## Automated suite

Run from the repository root with the project interpreter:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

**Latest complete post-hardening execution: 54 tests passed, 0 failed.** The 10 focused hardening tests cover authentication/configuration, CORS validation, rate limiting, error/log redaction, operational metrics, tool-failure counters, and benchmark non-mutation. `TestClient` emits a Starlette deprecation warning for its HTTPX integration; tests still pass.

## Test matrix

| Area | Test method | Expected result | Status |
|---|---|---|---|
| Startup/import | Import FastAPI app; validate development and production configuration | Production rejects missing/short token and invalid settings | **PASS** (config tests and production-configured Uvicorn smoke) |
| API contract | FastAPI `TestClient` plus OpenAPI/static route checks | Correct success shapes; required-query 422; unknown incident/runbook 404; wrong method 405 | **PASS** (prior audit and targeted API rerun) |
| Authentication | Missing, invalid, and valid bearer token; generic probes while token configured | Protected routes return 401 without a correct token; liveness remains generic and public | **PASS** |
| CORS | Parse exact-origin allowlist, reject wildcard, send unapproved preflight | No wildcard or credentialed CORS; production origin validation requires HTTPS | **PASS** for configuration and unapproved preflight; approved-origin browser test **NOT TESTED** |
| Rate limiting | Configure one request per test window and exceed it | API returns 429 with `Retry-After` | **PASS** |
| Error/log redaction | Inject an exception containing a secret-like string; inspect response and app logs | Generic 500 with request ID; exception message, credentials, query values absent from app logs | **PASS** |
| Operational metrics | Query aggregate counters and tool-failure tracking | Latency/investigation/failure aggregates contain no incident labels or payloads | **PASS** |
| Benchmark persistence | Compare checked-in snapshot bytes before/after benchmark export | GET operations return in-memory results without changing the file | **PASS** |
| Dashboard HTML escaping | Inject hostile log text into the browser API response | Payload renders as text; no injected image/element is created | **PASS** |
| Investigator | Run all 10 fixture investigations; compare category to fixture category | All 10 categories match; trace/evidence IDs resolve | **PASS** |
| Retrieval | Query each fixture alert with its service; empty/irrelevant/missing-ID cases | Expected runbook ranks first in all 10 curated queries; empty cases return no match | **PASS** |
| Correlation | Synthetic events around before/after boundaries, timezone offsets, and invalid timestamps | Out-of-window events excluded; normalized chronological order; invalid/naive/missing timestamps and negative windows rejected | **PASS** |
| Six tools | Call valid tool contracts, unknown incident cases, mutation-pattern inputs, and output/evidence checks | Expected response keys and evidence records; invalid IDs fail; guarded writes reject | **PASS** |
| Evidence | Check distinct metric IDs and every trace evidence reference | No overwritten INC-001 metric sample; trace references resolve | **PASS** |
| Concurrency | Five concurrent investigations with delayed runbook search | Shared evidence registry is serialized; each result retains its own correlation evidence | **PASS** |
| Benchmark | Compare both modes against the same helper and bundled ground truth | Reproducible project-defined comparison; not independent accuracy certification | **PASS** |
| Browser | Previous audit covered all sections; post-hardening run connects through the token dialog and loads authenticated data | Dashboard connects, displays 10 fixture rows, and clears the password field | **PASS** |
| Browser failure/empty states | Inject a 503 for investigation; search for no incidents | Error is readable, stale diagnosis/evidence cleared, controls re-enabled; empty roster message shown | **PASS** |
| Responsive layout | Browser viewport 390 × 844 | Document width remains 390px; no horizontal overflow | **PASS** |
| Dependency vulnerability scan | No dedicated scanner available in project environment | No vulnerability verdict | **NOT TESTED** |
| Docker build/container runtime | `Get-Command docker` found no Docker CLI | Cannot verify image build, health check, API/dashboard connectivity, env injection, or shutdown | **BLOCKED** |

## API route sweep

The automated API test covers dashboard, health, statistics, incident list/detail, evidence, log/metric/deployment queries, runbook search/detail, investigation modes, trace, benchmark, benchmark export, OpenAPI, Swagger, ReDoc, and static assets. It also checks missing parameters, invalid limits/modes, unknown IDs, and wrong methods.

All application API routes are protected when a token is configured, except the generic `/api/healthz` and `/api/readyz` probes. `/api/health` and `/api/ops/metrics` require authentication. `GET /api/benchmark` and `/api/benchmark/export` now compute their results in memory; a regression test verifies the checked-in snapshot is unchanged.

## Tool-specific cases

Each of the six registered tools is invoked with a valid fixture input, checked for expected result fields and evidence where applicable, and given mutation-like input to verify the lexical read-only guard. Unknown incident checks cover correlation, deployments, logs, metrics, and risk assessment. Tool exceptions increment an aggregate counter and still propagate to the API's generic error boundary. These tests do not establish that the guard is a security sandbox.

Timeouts, network partitions, and malformed responses from an external data source cannot be exercised because there are no external integrations. Missing/invalid/valid token checks are covered in-process; the dashboard token dialog was also exercised in the browser.

## Browser observations

- All 8 navigation sections became active and API data rendered.
- The incident filter selected one matching row; a no-match filter showed the empty state.
- Selecting INC-002 updated the investigation to `DATABASE_SLOWDOWN`; both investigator and baseline returned 200.
- A runbook summary containing apostrophes opened in the evidence modal without malformed inline JavaScript.
- The trace showed six steps, including the correlation evidence reference.
- A deliberately intercepted HTTP 503 produced an explicit error and cleared stale diagnosis, evidence, risk, and trace output. Chromium logs the expected failed-resource 503; no uncaught JavaScript exception occurred.
- The production-configured dashboard was reloaded, showed the API access form after 401 responses, accepted a test bearer token, loaded the roster, and cleared the password input. No uncaught page errors occurred.
- A hostile `<img src=x onerror=...>` message returned by a stubbed logs endpoint appeared literally as text; the rendered logs container contained no `img` element. Initial unauthenticated 401 resource errors were expected.
- The older broad navigation, filter, investigation-mode, evidence-modal, error-state, and mobile-viewport checks remain from the previous audit; they were not repeated.

## Performance method

The following are pre-hardening in-process FastAPI `TestClient` samples from the previous audit. Added auth, logging, metrics, and rate-limit middleware make them stale; they are retained only as historical baseline values, not current measurements:

| Route | Client-side median | Client-side p95 | Server middleware median |
|---|---:|---:|---:|
| `GET /api/health` | 9.912 ms | 12.692 ms | 2.362 ms |
| `GET /api/incidents` | 8.665 ms | 10.797 ms | 2.079 ms |
| `POST /api/investigate/INC-001` | 8.258 ms | 11.596 ms | 2.636 ms |

No post-hardening stress, endurance, concurrent user load, or external network latency benchmark was run. The separate concurrency regression validates evidence isolation by serialization, not throughput.

## Reproducibility caveats

The suite uses standard-library `unittest`; it does not certify external dependencies, human-reviewed diagnostic accuracy, telemetry freshness, production security, or container deployment. Benchmark and audit reports should be regenerated after material code or fixture changes.
