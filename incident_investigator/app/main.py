"""
FastAPI application for AI Incident Investigator.
"""

from fastapi import FastAPI, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import Optional, List
from pathlib import Path

from .models import (
    Incident, InvestigationResult, BenchmarkReport,
    LogEntry, MetricPoint, DeploymentEvent
)
from .telemetry import (
    get_all_incidents, get_incident,
    query_logs, query_metrics, query_deployments
)
from .runbook_retriever import retriever
from .investigator import investigator
from .baseline import baseline
from .benchmark import run_benchmark

app = FastAPI(
    title="AI Incident Investigator API",
    description="Automated service outage investigator correlating logs, metrics, deployments, and runbooks with evidence tracking.",
    version="1.0.0"
)

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def get_dashboard():
    """Serve web investigation dashboard."""
    index_file = STATIC_DIR / "index.html"
    return FileResponse(index_file)


# --- Incident Management ---

@app.get("/api/incidents", response_model=List[Incident])
def list_incidents():
    """List the 10 injected incident scenarios."""
    return get_all_incidents()


@app.get("/api/incidents/{incident_id}", response_model=Incident)
def get_incident_details(incident_id: str):
    """Retrieve details for a specific incident."""
    inc = get_incident(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    return inc


# --- Telemetry Query Endpoints ---

@app.get("/api/logs", response_model=List[LogEntry])
def get_logs(
    incident_id: str,
    service: Optional[str] = None,
    level: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 50
):
    """Query structured logs with multi-attribute filtering."""
    return query_logs(incident_id, service=service, level=level, search=search, limit=limit)


@app.get("/api/metrics", response_model=List[MetricPoint])
def get_metrics(
    incident_id: str,
    service: Optional[str] = None,
    metric_name: Optional[str] = None
):
    """Query time-series telemetry metrics."""
    return query_metrics(incident_id, service=service, metric_name=metric_name)


@app.get("/api/deployments", response_model=List[DeploymentEvent])
def get_deployments(
    incident_id: str,
    service: Optional[str] = None
):
    """Query deployment history and configuration changes within incident window."""
    return query_deployments(incident_id, service=service)


# --- Runbooks ---

@app.get("/api/runbooks")
def search_runbooks(
    query: str = Query(..., description="Query terms or alert description"),
    service: Optional[str] = None
):
    """BM25 search over runbooks."""
    return retriever.search(query=query, service=service)


@app.get("/api/runbooks/{runbook_id}")
def get_runbook(runbook_id: str):
    """Get full content of a runbook."""
    rb = retriever.get_runbook(runbook_id)
    if not rb:
        raise HTTPException(status_code=404, detail="Runbook not found")
    return rb


# --- Investigation & Proof Endpoints ---

from typing import Optional, List, Literal

@app.post("/api/investigate/{incident_id}", response_model=InvestigationResult)
def investigate_incident(
    incident_id: str,
    mode: Literal["ai", "baseline"] = Query("ai", description="'ai' for multi-step AI investigator, 'baseline' for keyword search")
):
    """
    Run an automated investigation on an incident.
    Returns proposed root cause, evidence chain, and execution trace.
    """
    inc = get_incident(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")

    if mode == "baseline":
        return baseline.investigate(incident_id)
    return investigator.investigate(incident_id)


@app.get("/api/trace/{incident_id}")
def get_investigation_trace(incident_id: str):
    """Get complete step-by-step investigation trace for an incident."""
    res = investigator.investigate(incident_id)
    return {
        "incident_id": res.incident_id,
        "title": res.incident_title,
        "root_cause_diagnosis": res.root_cause_diagnosis,
        "category": res.category,
        "confidence_score": res.confidence_score,
        "steps_count": res.steps_count,
        "duration_seconds": res.duration_seconds,
        "temporal_correlation_summary": res.temporal_correlation_summary,
        "unsupported_claims": res.unsupported_claims,
        "mitigation_recommended": res.mitigation_recommended,
        "trace": res.trace,
        "evidence_chain": res.evidence_chain
    }


@app.get("/api/benchmark", response_model=BenchmarkReport)
def run_system_benchmark():
    """
    Evaluate AI Investigator vs Keyword-Search Baseline across all 10 injected incidents.
    Calculates root-cause accuracy, time to diagnosis, and unsupported claims rate.
    """
    return run_benchmark()
