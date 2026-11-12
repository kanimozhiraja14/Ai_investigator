"""
Enterprise-Grade FastAPI application for AI Incident Investigator.
Provides REST APIs for incident telemetry, BM25 runbook RAG, time-window correlation,
evidence tracking, risk modeling, execution tracing, and comparative benchmarking.
"""

import json
import logging
import os
import secrets
import threading
import time
import uuid
from collections import defaultdict, deque
from pathlib import Path
from typing import Optional, List, Literal, Dict, Any

from contextlib import asynccontextmanager
from fastapi import FastAPI, Query, HTTPException, Request, Response, status
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from .config import get_allowed_origins, get_rate_limit, is_production, validate_environment
from .models import (
    Incident, InvestigationResult, BenchmarkReport,
    LogEntry, MetricPoint, DeploymentEvent,
    SystemHealthStatus, ComponentHealth, SystemStats, EvidenceItem
)
from .telemetry import (
    get_all_incidents, get_incident,
    query_logs, query_metrics, query_deployments, get_system_stats
)
from .runbook_retriever import retriever
from .investigator import investigator
from .baseline import baseline
from .benchmark import run_benchmark
from .tools import get_tool_failure_count

APP_START_TIME = time.time()
logger = logging.getLogger("incident_investigator")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())


class OperationalMetrics:
    def __init__(self):
        self._lock = threading.Lock()
        self._request_count = 0
        self._http_error_count = 0
        self._rate_limited_count = 0
        self._request_duration_total = 0.0
        self._request_duration_max = 0.0
        self._investigation_count = 0
        self._investigation_failure_count = 0
        self._investigation_duration_total = 0.0
        self._investigation_duration_max = 0.0

    def record_request(self, status_code: int, duration_seconds: float) -> None:
        with self._lock:
            self._request_count += 1
            self._http_error_count += status_code >= 500
            self._request_duration_total += duration_seconds
            self._request_duration_max = max(self._request_duration_max, duration_seconds)

    def record_rate_limited(self) -> None:
        with self._lock:
            self._rate_limited_count += 1

    def record_investigation(self, duration_seconds: float, failed: bool) -> None:
        with self._lock:
            self._investigation_count += 1
            self._investigation_failure_count += failed
            self._investigation_duration_total += duration_seconds
            self._investigation_duration_max = max(
                self._investigation_duration_max, duration_seconds
            )

    def snapshot(self) -> dict[str, int | float]:
        with self._lock:
            return {
                "request_count": self._request_count,
                "http_5xx_count": self._http_error_count,
                "rate_limited_count": self._rate_limited_count,
                "request_latency_avg_ms": round(
                    self._request_duration_total / max(self._request_count, 1) * 1000, 3
                ),
                "request_latency_max_ms": round(self._request_duration_max * 1000, 3),
                "investigation_count": self._investigation_count,
                "investigation_failure_count": self._investigation_failure_count,
                "investigation_duration_avg_ms": round(
                    self._investigation_duration_total
                    / max(self._investigation_count, 1)
                    * 1000,
                    3,
                ),
                "investigation_duration_max_ms": round(
                    self._investigation_duration_max * 1000, 3
                ),
                "tool_failure_count": get_tool_failure_count(),
            }


class RequestRateLimiter:
    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window_seconds = window_seconds
        self._lock = threading.Lock()
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._max_clients = 10000

    def allow(self, client: str, now: Optional[float] = None) -> bool:
        current = time.monotonic() if now is None else now
        cutoff = current - self.window_seconds
        with self._lock:
            requests = self._requests.get(client)
            if requests is None:
                if len(self._requests) >= self._max_clients:
                    expired_clients = [
                        key for key, values in self._requests.items()
                        if not values or values[-1] <= cutoff
                    ]
                    for key in expired_clients:
                        self._requests.pop(key, None)
                if len(self._requests) >= self._max_clients:
                    return False
                requests = self._requests[client]
            while requests and requests[0] <= cutoff:
                requests.popleft()
            if len(requests) >= self.limit:
                return False
            requests.append(current)
            return True


operational_metrics = OperationalMetrics()
rate_limit, rate_window_seconds = get_rate_limit()
request_rate_limiter = RequestRateLimiter(rate_limit, rate_window_seconds)


@asynccontextmanager
async def lifespan(_: FastAPI):
    validate_environment()
    if not os.getenv("AI_INVESTIGATOR_API_TOKEN"):
        logger.warning("API authentication is disabled; use only for local development")
    yield


app = FastAPI(
    title="AI Incident Investigator API",
    description=(
        "Deterministic incident investigation demo using bundled synthetic telemetry, lexical runbook retrieval, "
        "time-window correlation, and an in-memory evidence chain."
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


def _custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    schema.setdefault("components", {}).setdefault("securitySchemes", {})[
        "BearerAuth"
    ] = {"type": "http", "scheme": "bearer"}
    for path, operations in schema.get("paths", {}).items():
        if path.startswith("/api/") and path not in {"/api/healthz", "/api/readyz"}:
            for operation in operations.values():
                operation["security"] = [{"BearerAuth": []}]
    app.openapi_schema = schema
    return schema


app.openapi = _custom_openapi

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def harden_requests(request: Request, call_next):
    start = time.perf_counter()
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    response: Optional[Response] = None
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    path = request.url.path
    requires_auth = (
        path.startswith("/api/")
        and path not in {"/api/healthz", "/api/readyz"}
        and request.method != "OPTIONS"
    )

    try:
        token = os.getenv("AI_INVESTIGATOR_API_TOKEN", "")
        provided_token = request.headers.get("authorization", "")
        valid_token = (
            provided_token[:7].lower() == "bearer "
            and bool(token)
            and provided_token[7:].isascii()
            and secrets.compare_digest(
                provided_token[7:].encode("ascii"),
                token.encode("ascii"),
            )
        )
        if requires_auth and is_production() and not token:
            response = JSONResponse(
                {"detail": "Service authentication is not configured"},
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        elif requires_auth and token and not valid_token:
            response = JSONResponse(
                {"detail": "Authentication required"},
                status_code=status.HTTP_401_UNAUTHORIZED,
                headers={"WWW-Authenticate": "Bearer"},
            )

        if response is None and request.method != "OPTIONS" and path.startswith("/api/") and path not in {
            "/api/healthz",
            "/api/readyz",
        }:
            client = request.client.host if request.client else "unknown"
            if not request_rate_limiter.allow(client):
                operational_metrics.record_rate_limited()
                response = JSONResponse(
                    {"detail": "Request rate limit exceeded"},
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    headers={"Retry-After": str(rate_window_seconds)},
                )

        if response is None:
            response = await call_next(request)
        status_code = response.status_code
        return response
    except Exception as exc:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        logger.error(json.dumps({
            "event": "unhandled_exception",
            "request_id": request_id,
            "error_type": type(exc).__name__,
        }, separators=(",", ":")))
        response = JSONResponse(
            {"detail": "Internal server error", "request_id": request_id},
            status_code=status_code,
        )
        return response
    finally:
        duration = time.perf_counter() - start
        operational_metrics.record_request(status_code, duration)
        route = request.scope.get("route")
        route_template = getattr(route, "path", "/unmatched")
        logger.info(json.dumps({
            "event": "http_request",
            "request_id": request_id,
            "method": request.method,
            "route": route_template,
            "status_code": status_code,
            "duration_ms": round(duration * 1000, 3),
        }, separators=(",", ":")))
        if response is not None:
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time-Sec"] = f"{duration:.6f}"
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Referrer-Policy"] = "no-referrer"
            if path.startswith("/api/"):
                response.headers["Cache-Control"] = "no-store"



STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _require_incident(incident_id: str) -> Incident:
    incident = get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found")
    return incident


@app.get("/", tags=["Dashboard UI"])
def get_dashboard():
    """Serve the incident-investigation demo dashboard."""
    index_file = STATIC_DIR / "index.html"
    return FileResponse(index_file)


@app.get("/api/healthz", include_in_schema=False)
def liveness_check():
    return {"status": "ok"}


@app.get("/api/readyz", include_in_schema=False)
def readiness_check():
    if not get_all_incidents() or not retriever.runbooks:
        raise HTTPException(status_code=503, detail="Service is not ready")
    return {"status": "ready"}


# --- System Health & Observability ---

@app.get("/api/health", response_model=SystemHealthStatus, tags=["System Health"])
def get_health_status():
    """Report process and bundled-demo component status."""
    uptime = time.time() - APP_START_TIME
    incidents = get_all_incidents()
    
    components = {
        "api_gateway": ComponentHealth(
            status="OPERATIONAL",
            details="FastAPI process is serving requests"
        ),
        "telemetry_database": ComponentHealth(
            status="OPERATIONAL",
            details=f"In-memory synthetic telemetry store loaded with {len(incidents)} incident scenarios"
        ),
        "runbook_retrieval_engine": ComponentHealth(
            status="OPERATIONAL",
            details=f"Lexical runbook retriever loaded with {len(retriever.runbooks)} bundled runbooks"
        ),
        "read_only_enforcement": ComponentHealth(
            status="OPERATIONAL",
            details="Investigation tools enforce read-only query checks"
        )
    }

    return SystemHealthStatus(
        status="HEALTHY",
        version="2.0.0",
        uptime_seconds=round(uptime, 2),
        components=components,
        read_only_mode=True,
        total_incidents_monitored=len(incidents)
    )


@app.get("/api/ops/metrics", tags=["System Health"])
def get_operational_metrics():
    """Return aggregate service counters only; no incident-level labels or payloads."""
    return operational_metrics.snapshot()


@app.get("/api/stats", response_model=SystemStats, tags=["System Health"])
def get_dashboard_stats():
    """High-level SRE / SOC metrics: total incidents, severity breakdown, categories, and MTTR."""
    return get_system_stats()


# --- Incident Management ---

@app.get("/api/incidents", response_model=List[Incident], tags=["Incident Management"])
def list_incidents(
    severity: Optional[str] = Query(None, description="Filter by severity: P1, P2, P3"),
    status: Optional[str] = Query(None, description="Filter by status: OPEN, INVESTIGATING, RESOLVED"),
    service: Optional[str] = Query(None, description="Filter by service name"),
    search: Optional[str] = Query(None, description="Text search over incident titles and alerts")
):
    """List incidents with multi-attribute filtering and search."""
    incidents = get_all_incidents()
    filtered = incidents

    if severity and isinstance(severity, str):
        filtered = [i for i in filtered if i.severity.upper() == severity.upper()]
    if status and isinstance(status, str):
        filtered = [i for i in filtered if i.status.upper() == status.upper()]
    if service and isinstance(service, str):
        filtered = [i for i in filtered if service.lower() in i.service.lower()]
    if search and isinstance(search, str):
        q = search.lower()
        filtered = [
            i for i in filtered 
            if q in i.title.lower() or q in i.initial_alert.lower() or q in i.service.lower()
        ]

    return filtered


@app.get("/api/incidents/{incident_id}", response_model=Incident, tags=["Incident Management"])
def get_incident_details(incident_id: str):
    """Retrieve details, detection time, and threat metadata for a specific incident."""
    return _require_incident(incident_id)


# --- Evidence Explorer ---

@app.get("/api/evidence", response_model=List[EvidenceItem], tags=["Evidence Explorer"])
def list_evidence(
    incident_id: Optional[str] = Query(None, description="Filter evidence for a specific incident"),
    source_type: Optional[str] = Query(None, description="Filter by source type: LOG, METRIC, DEPLOYMENT, RUNBOOK, RISK"),
    search: Optional[str] = Query(None, description="Search evidence summaries")
):
    """Global Evidence Explorer: Query evidence ledger items linked to investigations."""
    # Ensure investigator runs at least on requested incident or default incident to populate store
    target_id = incident_id if (incident_id and isinstance(incident_id, str)) else "INC-001"
    _require_incident(target_id)
    res = investigator.investigate(target_id)
    items = res.evidence_chain

    if source_type and isinstance(source_type, str):
        items = [e for e in items if e.source_type.upper() == source_type.upper()]
    if search and isinstance(search, str):
        q = search.lower()
        items = [e for e in items if q in e.summary.lower() or q in str(e.raw_data).lower()]

    return items


# --- Telemetry Query Endpoints ---

@app.get("/api/logs", response_model=List[LogEntry], tags=["Telemetry & Observability"])
def get_logs(
    incident_id: str = Query(..., description="Target incident ID"),
    service: Optional[str] = Query(None, description="Filter by service"),
    level: Optional[str] = Query(None, description="Log level: INFO, WARN, ERROR, FATAL"),
    search: Optional[str] = Query(None, description="Search log text and attributes"),
    limit: int = Query(50, ge=1, le=200, description="Max logs to return")
):
    """Query structured logs with multi-attribute filtering."""
    _require_incident(incident_id)
    svc = service if isinstance(service, str) else None
    lvl = level if isinstance(level, str) else None
    srch = search if isinstance(search, str) else None
    lmt = limit if isinstance(limit, int) else 50
    return query_logs(incident_id, service=svc, level=lvl, search=srch, limit=lmt)


@app.get("/api/metrics", response_model=List[MetricPoint], tags=["Telemetry & Observability"])
def get_metrics(
    incident_id: str = Query(..., description="Target incident ID"),
    service: Optional[str] = Query(None, description="Filter by service"),
    metric_name: Optional[str] = Query(None, description="Specific metric name")
):
    """Query time-series telemetry metrics."""
    _require_incident(incident_id)
    svc = service if isinstance(service, str) else None
    m_name = metric_name if isinstance(metric_name, str) else None
    return query_metrics(incident_id, service=svc, metric_name=m_name)


@app.get("/api/deployments", response_model=List[DeploymentEvent], tags=["Telemetry & Observability"])
def get_deployments(
    incident_id: str = Query(..., description="Target incident ID"),
    service: Optional[str] = Query(None, description="Filter by service")
):
    """Query deployment change events, commit hashes, and config diffs within incident window."""
    _require_incident(incident_id)
    svc = service if isinstance(service, str) else None
    return query_deployments(incident_id, service=svc)


# --- Runbooks ---

@app.get("/api/runbooks", tags=["Runbook Knowledge Base"])
def search_runbooks(
    query: str = Query(..., description="Query terms or alert description"),
    service: Optional[str] = Query(None, description="Filter/boost by service name")
):
    """BM25 search over markdown runbook repository."""
    q_str = query if isinstance(query, str) else str(query)
    svc = service if isinstance(service, str) else None
    return retriever.search(query=q_str, service=svc)


@app.get("/api/runbooks/{runbook_id}", tags=["Runbook Knowledge Base"])
def get_runbook(runbook_id: str):
    """Get full structured content and diagnostic checklist of a specific runbook."""
    rb = retriever.get_runbook(runbook_id)
    if not rb:
        raise HTTPException(status_code=404, detail=f"Runbook '{runbook_id}' not found")
    return rb


# --- Investigation & Proof Endpoints ---

@app.post("/api/investigate/{incident_id}", response_model=InvestigationResult, tags=["AI Investigation"])
def investigate_incident(
    incident_id: str,
    mode: Literal["ai", "baseline"] = Query(
        "ai",
        description="'ai' executes multi-step tool-calling investigator; 'baseline' executes keyword grep triage"
    )
):
    """
    Execute an automated incident investigation.
    Returns calibrated root cause diagnosis, confidence breakdown, evidence ledger, and risk analysis.
    """
    _require_incident(incident_id)
    started = time.perf_counter()
    failed = True
    try:
        result = (
            baseline.investigate(incident_id)
            if mode == "baseline"
            else investigator.investigate(incident_id)
        )
        failed = False
        return result
    finally:
        operational_metrics.record_investigation(
            time.perf_counter() - started,
            failed,
        )


@app.get("/api/trace/{incident_id}", tags=["AI Investigation"])
def get_investigation_trace(incident_id: str):
    """Retrieve auditable step-by-step execution trace including tool calls, arguments, and evidence IDs."""
    _require_incident(incident_id)

    res = investigator.investigate(incident_id)
    return {
        "incident_id": res.incident_id,
        "title": res.incident_title,
        "root_cause_diagnosis": res.root_cause_diagnosis,
        "category": res.category,
        "confidence_score": res.confidence_score,
        "confidence_breakdown": res.confidence_breakdown,
        "steps_count": res.steps_count,
        "duration_seconds": res.duration_seconds,
        "temporal_correlation_summary": res.temporal_correlation_summary,
        "risk_analysis": res.risk_analysis,
        "unsupported_claims": res.unsupported_claims,
        "mitigation_recommended": res.mitigation_recommended,
        "trace": res.trace,
        "evidence_chain": res.evidence_chain
    }


# --- Comparative Benchmark Center ---

@app.get("/api/benchmark", response_model=BenchmarkReport, tags=["Benchmark Center"])
def run_system_benchmark():
    """
    Evaluate AI Investigator vs Keyword-Search Baseline across all 10 injected incidents.
    Calculates root-cause accuracy, diagnosis duration, and unsupported claims rate.
    """
    return run_benchmark()


@app.get("/api/benchmark/export", tags=["Benchmark Center"])
def export_benchmark_report():
    """Generate an in-memory benchmark download without writing persistent state."""
    report = run_benchmark()
    return JSONResponse(
        content=report.model_dump(),
        headers={"Content-Disposition": 'attachment; filename="benchmark_report.json"'},
    )
