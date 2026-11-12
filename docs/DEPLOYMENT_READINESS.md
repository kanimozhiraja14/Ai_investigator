# Deployment Readiness

**Review update:** 2026-11-12
**Recommendation:** **NOT READY for public or production deployment.** The app is still appropriate for a local portfolio demonstration using bundled synthetic data. Production hardening added useful baseline controls, but it does not establish a secure multi-user service or a validated deployment.

## Status summary

| Area | Status | Verified evidence / remaining limitation |
|---|---|---|
| Local synthetic-data workflow | **PASS** | Prior audit verified the ten fixture investigations, API routes, and dashboard. The latest 54-test post-hardening suite passes. |
| API authentication | **PASS (single shared bearer token)** | `/api/*` requires a configured token except generic health probes. Automated tests cover missing, invalid, and valid credentials. Production startup validation requires a 32–4096 character ASCII token without whitespace. |
| Role-based authorization | **WARNING / NOT IMPLEMENTED** | The app has no user identities or mutation APIs; all token holders have the same read-only access. This is not sufficient for multi-user, tenant-separated, or sensitive real-data use. |
| CORS | **PASS (configured allowlist)** | No wildcard default; exact origins only, no credentialed CORS, production origins must use HTTPS. Allowed-origin browser deployment was not runtime-tested. |
| Rate limiting | **PASS (single-process baseline)** | Configurable fixed-window per-client API limit, 429/Retry-After, and regression tests. Not distributed; gateway limits are required for deployment. |
| Input/error handling | **PASS for implemented routes** | Existing Pydantic/query validation remains; unexpected errors return generic 500 with request ID and do not log exception messages. Bodyless investigation route has no meaningful payload-validation surface. |
| Request/operations monitoring | **WARNING** | Structured request records and aggregate authenticated `/api/ops/metrics` are implemented and tested. No external monitoring, alerting, log retention, or durable metrics backend. |
| Liveness/readiness | **PASS (local checks)** | Generic `/api/healthz` and `/api/readyz` are unauthenticated; detailed `/api/health` is protected. Docker health check targets `/api/healthz`. |
| Data protection | **FAIL for real data** | Only synthetic fixtures exist. No real-data redaction, data access integration, persistent evidence store, backup/restore, or formal retention/deletion workflow. |
| Benchmark writes | **PASS (fixed)** | Benchmark and export calculate in memory; regression test confirms the checked-in `benchmark_results.json` is unchanged. |
| CORS/HTTPS deployment | **FAIL / BLOCKER** | App itself serves HTTP. Compose binds to loopback; a separately configured HTTPS reverse proxy and gateway controls are still required. |
| Container configuration | **WARNING / NOT VERIFIED** | Non-root user, read-only root filesystem, dropped capabilities, no-new-privileges, bounded Uvicorn keep-alive/concurrency/shutdown settings, and health check are configured. |
| Docker build/runtime | **BLOCKED** | `docker` command is unavailable in this environment. No claim is made that the image builds or runs. |
| Dependency security | **NOT TESTED** | Requirement ranges are not locked; no dependency scanner or reproducible-build check was run. |
| Backup/recovery | **NOT APPLICABLE to volatile demo state; NOT TESTED for production** | Current data and metrics are process-local. No durable state or backup mechanism exists. |

## Implemented controls

- Production startup rejects a missing, out-of-range, non-ASCII, or whitespace-containing API token and invalid environment/rate-limit/CORS configuration.
- Bearer auth is checked with constant-time comparison. The dashboard prompts for the token and keeps it only in memory.
- Every `/api/*` endpoint except `/api/healthz` and `/api/readyz` is protected when a token is configured; production cannot start without one.
- CORS is disabled by default and can allow only explicit origins. Wildcards are rejected, and production origins must use HTTPS.
- An in-process rate limiter and bounded Uvicorn concurrency, keep-alive, and graceful-shutdown settings are configured.
- Request logs omit credentials, raw URLs, query parameters, bodies, and incident data. Unexpected errors return generic text; operational metrics contain aggregate values only.
- Dashboard rendering HTML-escapes dynamic telemetry and result strings.
- Benchmark evaluation and export no longer persist data. The application does not implement external remediation.
- Compose binds to `127.0.0.1`, requires a production token, and configures a read-only container filesystem with reduced Linux privileges.

## Remaining deployment blockers

1. **Identity and authorization:** replace the one shared bearer token with an approved identity provider, per-user identity, least-privilege roles, and credential revocation/rotation if multiple users or sensitive records are in scope.
2. **HTTPS and edge controls:** deploy only behind a managed HTTPS reverse proxy/load balancer. Add gateway rate limits, request-size limits, timeouts, and trusted-proxy configuration. Do not expose port 8000 directly.
3. **Data policy:** do not connect production telemetry until redaction/minimization, authorization, retention/deletion, audit, backup, and recovery have been designed and validated.
4. **Operations:** connect external error monitoring, log/metric retention, alerting, and service ownership/on-call procedures. `/api/ops/metrics` is process-local, not an external monitoring solution.
5. **Supply chain:** pin/lock dependencies, run a vulnerability scan, and validate a reproducible image build.
6. **Container proof:** execute the Docker validation below; current status remains **BLOCKED**.
7. **Security validation:** run a deployment-specific threat model, security review, and load/resilience checks before handling real data.

The read-only query guard is lexical input filtering, not process isolation. A shared bearer token authorizes every API operation; it is not user-level RBAC. The per-process limiter can be bypassed by scaling to multiple workers and may treat all clients behind a proxy as one peer. Keep gateway enforcement.

## Docker status and exact validation steps

**Current result: BLOCKED — Docker Desktop/CLI is not installed or available in this environment.** No image build, container startup, health check, API/dashboard connectivity, environment handling, persistent-volume behavior, or shutdown test has passed.

### Install on Windows

1. Install Docker Desktop for Windows using the [official Windows installation guide](https://docs.docker.com/desktop/setup/install/windows-install/). With WinGet, the install command is:

   ```powershell
   winget install --exact --id Docker.DockerDesktop
   ```

   On systems using the WSL 2 backend, install/enable WSL 2 using [Microsoft's WSL installation guide](https://learn.microsoft.com/windows/wsl/install), restart if prompted, and start Docker Desktop.
2. Verify from a new PowerShell window:

   ```powershell
   docker version
   docker compose version
   ```

3. From the repository root, create a token in the current PowerShell session without printing it:

   ```powershell
   $env:AI_INVESTIGATOR_API_TOKEN = python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```

   If a separate browser origin is required, set `CORS_ALLOWED_ORIGINS` to a comma-separated list of exact HTTPS origins, for example `$env:CORS_ALLOWED_ORIGINS = 'https://console.example.com'`. Leave it empty for the same-origin dashboard served by this container. Do not commit the generated token or store it in source control.

### Build, run, and verify

```powershell
docker compose config --quiet
docker compose up --build --detach
docker compose ps
$containerId = docker compose ps --quiet ai-incident-investigator
docker inspect --format='{{.State.Health.Status}}' $containerId
Invoke-RestMethod http://127.0.0.1:8000/api/healthz
$headers = @{ Authorization = "Bearer $env:AI_INVESTIGATOR_API_TOKEN" }
Invoke-RestMethod -Headers $headers http://127.0.0.1:8000/api/incidents
$unauthorizedStatus = 0
try { Invoke-WebRequest -ErrorAction Stop http://127.0.0.1:8000/api/incidents | Out-Null } catch { $unauthorizedStatus = [int]$_.Exception.Response.StatusCode }
if ($unauthorizedStatus -ne 401) { throw "Expected unauthenticated API status 401, got $unauthorizedStatus" }
```

Expected results: `docker compose ps` reports the service running, inspection reports `healthy`, the liveness endpoint returns `{"status":"ok"}`, and the authenticated incident query returns only the bundled synthetic fixtures.

Also verify that an unauthenticated request is rejected (HTTP 401), the dashboard at `http://127.0.0.1:8000/` prompts for the token and can load its data, and the token is not present in container logs. Verify configuration is present without displaying the value:

```powershell
docker compose exec --no-TTY ai-incident-investigator python -c "import os; assert os.getenv('APP_ENV') == 'production'; assert len(os.getenv('AI_INVESTIGATOR_API_TOKEN', '')) >= 32; print('production environment configured')"
docker inspect --format='{{.HostConfig.ReadonlyRootfs}}' $containerId
```

The expected read-only-root result is `true`. There is intentionally no persistent application-data volume: this demo has no durable evidence store. Then exercise graceful shutdown and inspect only redacted logs:

```powershell
docker compose stop
docker compose logs --tail 50 ai-incident-investigator
docker compose down
```

Repeat the API and dashboard checks after any Compose, Dockerfile, or app changes. Record the actual commands and outcomes in this document; do not mark Docker **PASS** until the full sequence succeeds.

## Retention and deletion

The application has no durable incident/evidence database. Synthetic fixture records are part of the application bundle. Investigation evidence, request counters, and aggregate metrics reside in process memory; evidence may be replaced during a subsequent investigation and all volatile state disappears when the process exits. No backup is needed for this demo state, but no production retention, deletion, backup, or restore policy is implemented.

## Release recommendation

- **Local portfolio demo with synthetic fixtures:** **PASS**, subject to using loopback/local access.
- **Network-exposed demo:** **WARNING / BLOCKED** until HTTPS termination, gateway controls, a secret-management process, and Docker validation are in place.
- **Public production use or real incident data:** **FAIL** until all blockers above are addressed and deployment-specific validation passes.

See [`SECURITY_REVIEW.md`](./SECURITY_REVIEW.md), [`QA_TEST_PLAN.md`](./QA_TEST_PLAN.md), and [`FINAL_QA_REPORT.md`](./FINAL_QA_REPORT.md) for security and test details.
