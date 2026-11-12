# AI Incident Investigator - REST API Reference Specification

## Base URL
```
http://localhost:8000
```
Interactive Swagger UI documentation is accessible at `http://localhost:8000/docs` and ReDoc at `http://localhost:8000/redoc`.

---

## 1. System Health & Observability Endpoints

### `GET /health`
Returns health status for all system subsystems, memory counters, and read-only mode verification.

#### Response `200 OK`:
```json
{
  "status": "HEALTHY",
  "version": "2.0.0",
  "uptime_seconds": 124.5,
  "read_only_mode": true,
  "total_incidents_monitored": 10,
  "components": {
    "api_gateway": {
      "status": "OPERATIONAL",
      "details": "FastAPI ASGI engine running on Uvicorn",
      "latency_ms": 0.4
    },
    "telemetry_database": {
      "status": "OPERATIONAL",
      "details": "10 incident scenarios loaded with structured logs and metrics",
      "latency_ms": 0.2
    },
    "runbook_retrieval_engine": {
      "status": "OPERATIONAL",
      "details": "BM25 vector scoring over 10 Markdown runbooks active",
      "latency_ms": 0.5
    },
    "read_only_enforcement": {
      "status": "OPERATIONAL",
      "details": "Strict ReadOnlyGuard active. Mutating operations blocked.",
      "latency_ms": 0.1
    }
  }
}
```

---

### `GET /api/v1/stats`
Aggregated incident statistics across all monitored services.

#### Response `200 OK`:
```json
{
  "total_incidents": 10,
  "severity_counts": {
    "P1": 7,
    "P2": 3
  },
  "status_counts": {
    "OPEN": 10,
    "INVESTIGATING": 0,
    "RESOLVED": 0
  },
  "category_counts": {
    "BAD_DEPLOYMENT": 1,
    "DATABASE_SLOWDOWN": 1,
    "EXHAUSTED_DISK": 1,
    "MEMORY_LEAK": 1,
    "UPSTREAM_DEPENDENCY": 1,
    "CERTIFICATE_EXPIRATION": 1,
    "CACHE_STAMPEDE": 1,
    "RATE_LIMIT_MISCONFIG": 1,
    "CONSUMER_REBALANCE_LOOP": 1,
    "AUTH_SECRET_ROTATION": 1
  },
  "recent_incidents": [...],
  "avg_mttr_seconds": 0.0004
}
```

---

## 2. Incident Management Endpoints

### `GET /incidents`
Lists all injected incidents with optional filtering.

#### Query Parameters:
| Parameter | Type | Required | Description |
|:----------|:-----|:---------|:------------|
| `severity` | `string` | No | Filter by severity (`P1`, `P2`) |
| `service` | `string` | No | Filter by target microservice |
| `status` | `string` | No | Filter by status (`OPEN`, `RESOLVED`) |

#### Response `200 OK`:
```json
[
  {
    "id": "INC-001",
    "title": "Payment Service 500 Spike after Canary Rollout",
    "service": "payment-service",
    "start_time": "2026-11-12T14:02:00Z",
    "end_time": "2026-11-12T14:25:00Z",
    "initial_alert": "PaymentServiceHighErrorRate: 5xx error rate exceeded 12% in us-east-1",
    "severity": "P1",
    "status": "OPEN",
    "ground_truth_cause": "Missing STRIPE_WEBHOOK_SECRET environment variable in v2.4.1 deployment manifest...",
    "ground_truth_category": "BAD_DEPLOYMENT",
    "threat_category": "CONFIGURATION_DRIFT_AND_SECRET_HYGIENE",
    "cwe_id": "CWE-312 / CWE-347",
    "key_signals": ["StripeSignatureVerificationException", "STRIPE_WEBHOOK_SECRET", "DEP-101", "v2.4.1"]
  }
]
```

---

### `GET /incidents/{incident_id}`
Retrieves detailed metadata for a specific incident.

---

## 3. Autonomous Investigation Endpoints

### `POST /investigate/{incident_id}`
Executes root cause investigation for an incident.

#### Query Parameters:
| Parameter | Type | Default | Description |
|:----------|:-----|:--------|:------------|
| `mode` | `string` | `"ai"` | Investigation mode (`"ai"` or `"baseline"`) |

#### Response `200 OK`:
```json
{
  "incident_id": "INC-001",
  "incident_title": "Payment Service 500 Spike after Canary Rollout",
  "mode": "READ_ONLY",
  "root_cause_diagnosis": "Missing environment secret 'STRIPE_WEBHOOK_SECRET' introduced in deployment DEP-101 (v2.4.1)...",
  "category": "BAD_DEPLOYMENT",
  "confidence_score": 0.967,
  "confidence_breakdown": {
    "overall_score": 0.967,
    "log_signal_weight": 0.98,
    "metric_anomaly_weight": 0.96,
    "temporal_proximity_weight": 0.95,
    "runbook_alignment_weight": 0.97,
    "explanation": "Calibrated across 4 independent telemetry vectors..."
  },
  "evidence_chain": [
    {
      "id": "EVID-RUNBOOK-payment_service_5xx",
      "source_type": "RUNBOOK",
      "source_id": "payment_service_5xx",
      "timestamp": null,
      "summary": "Matched runbook 'Payment Service HTTP 500 Spike' for payment-service (BM25 score: 3.42)",
      "raw_data": {...},
      "relevance": "HIGH"
    }
  ],
  "unsupported_claims": [],
  "steps_count": 6,
  "duration_seconds": 0.0006,
  "mitigation_recommended": [
    "Verify STRIPE_WEBHOOK_SECRET environment variable injection",
    "Rollback canary deployment to v2.4.0 immediately"
  ],
  "risk_analysis": {
    "threat_vector": "CONFIGURATION_DRIFT_AND_SECRET_HYGIENE",
    "cwe_id": "CWE-312 / CWE-347",
    "cia_impact": {
      "confidentiality": "MEDIUM",
      "integrity": "HIGH",
      "availability": "CRITICAL"
    },
    "risk_level": "CRITICAL",
    "blast_radius": "Service 'payment-service' and connected tier-1 dependency mesh",
    "remediation_sla": "< 30 minutes (Immediate Action Required)",
    "security_advisory": "Security Advisory for payment-service..."
  }
}
```

---

### `GET /investigate/{incident_id}/trace`
Retrieves the execution audit trace (tool calls, arguments, timestamps, and findings) for an incident investigation.

---

## 4. Telemetry & Knowledge Endpoints

### `GET /telemetry/logs`
Filter logs by `incident_id`, `service`, `level`, `search`, and `limit`.

### `GET /telemetry/metrics`
Query metric timeseries by `incident_id`, `service`, or `metric_name`.

### `GET /telemetry/deployments`
Query deployment events by `incident_id` or `service`.

### `GET /runbooks/search`
Query runbook knowledge base with BM25 term weighting (`query`, `service`).

### `GET /runbooks/{runbook_id}`
Retrieve raw Markdown and structured symptom/mitigation steps of a runbook.

---

## 5. Benchmark Endpoints

### `GET /benchmark/run`
Executes head-to-head comparison across all 10 scenarios between the AI Investigator and Keyword Baseline. Returns accuracy, diagnosis time, unsupported claims rate, and individual scenario comparisons.

### `GET /benchmark/export`
Downloads the official serialized `benchmark_results.json` artifact.
