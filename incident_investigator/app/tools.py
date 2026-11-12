"""
Read-only investigation tools with evidence registration, security guard, and mutation blocking.
"""

import re
from functools import wraps
from threading import Lock
from typing import Dict, Any, List, Optional
from .models import EvidenceItem, LogEntry, MetricPoint, DeploymentEvent, RiskAnalysis
from .telemetry import query_logs, query_metrics, query_deployments, get_incident
from .runbook_retriever import retriever
from .correlation_engine import correlator


class ReadOnlyViolationError(Exception):
    """Raised when an agent attempts a mutating operation or passes mutation verbs in read-only mode."""
    pass


FORBIDDEN_MUTATION_REGEX = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|REPLACE|"
    r"EXEC|SYSTEM|SHUTDOWN|KILL|REBOOT|WRITE|RM|DEL|POST|PUT|PATCH)\b",
    re.IGNORECASE
)

_tool_failure_lock = Lock()
_tool_failure_count = 0


def get_tool_failure_count() -> int:
    with _tool_failure_lock:
        return _tool_failure_count


def _track_tool_failures(method):
    @wraps(method)
    def tracked(*args, **kwargs):
        try:
            return method(*args, **kwargs)
        except Exception:
            global _tool_failure_count
            with _tool_failure_lock:
                _tool_failure_count += 1
            raise

    return tracked


def _validate_read_only_args(**kwargs):
    """
    Inspects all input parameters for SQL/system/API mutation verbs.
    Throws ReadOnlyViolationError if any write or destructive action is detected.
    """
    for key, val in kwargs.items():
        if isinstance(val, str) and FORBIDDEN_MUTATION_REGEX.search(val):
            raise ReadOnlyViolationError(
                f"STRICT READ-ONLY VIOLATION: Parameter '{key}' contains prohibited mutation command '{val}'. "
                "Investigation tools are strictly prohibited from mutating or deleting system state."
            )


class InvestigationToolRegistry:
    def __init__(self):
        self.evidence_store: Dict[str, EvidenceItem] = {}
        self.mutation_attempts: List[str] = []

    def clear(self):
        self.evidence_store.clear()
        self.mutation_attempts.clear()

    def register_evidence(self, source_type: str, source_id: str, summary: str, raw_data: Any, timestamp: Optional[str] = None, relevance: str = "HIGH") -> str:
        evid_id = f"EVID-{source_type}-{source_id}"
        item = EvidenceItem(
            id=evid_id,
            source_type=source_type,
            source_id=source_id,
            timestamp=timestamp,
            summary=summary,
            raw_data=raw_data,
            relevance=relevance
        )
        self.evidence_store[evid_id] = item
        return evid_id

    # --- Read-Only Tools ---

    @_track_tool_failures
    def query_logs_tool(self, incident_id: str, service: Optional[str] = None, level: Optional[str] = None, search: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
        """Query structured logs and capture discovered records as verified evidence."""
        _validate_read_only_args(incident_id=incident_id, service=service, level=level, search=search)
        if not get_incident(incident_id):
            raise ValueError(f"Incident {incident_id} not found")
        logs = query_logs(incident_id, service=service, level=level, search=search, limit=limit)
        captured_ids = []
        for log in logs:
            evid_id = self.register_evidence(
                source_type="LOG",
                source_id=log.id,
                summary=f"[{log.level}] {log.service} at {log.timestamp}: {log.message[:140]}",
                raw_data=log.model_dump(),
                timestamp=log.timestamp,
                relevance="HIGH" if log.level in ["ERROR", "FATAL"] else "MEDIUM"
            )
            captured_ids.append(evid_id)

        return {
            "status": "SUCCESS",
            "total_found": len(logs),
            "logs": [l.model_dump() for l in logs],
            "evidence_registered": captured_ids
        }

    @_track_tool_failures
    def query_metrics_tool(self, incident_id: str, service: Optional[str] = None, metric_name: Optional[str] = None) -> Dict[str, Any]:
        """Query metric timeseries to identify saturation, error rate spikes, or latency anomalies."""
        _validate_read_only_args(incident_id=incident_id, service=service, metric_name=metric_name)
        if not get_incident(incident_id):
            raise ValueError(f"Incident {incident_id} not found")
        metrics = query_metrics(incident_id, service=service, metric_name=metric_name)
        captured_ids = []
        for m in metrics:
            evid_id = self.register_evidence(
                source_type="METRIC",
                source_id=f"{m.service}_{m.metric_name}_{m.timestamp}",
                summary=f"Metric {m.metric_name} for {m.service} recorded {m.value}{m.unit} at {m.timestamp}",
                raw_data=m.model_dump(),
                timestamp=m.timestamp,
                relevance="HIGH"
            )
            captured_ids.append(evid_id)

        return {
            "status": "SUCCESS",
            "total_points": len(metrics),
            "metrics": [m.model_dump() for m in metrics],
            "evidence_registered": captured_ids
        }

    @_track_tool_failures
    def get_deployments_tool(self, incident_id: str, service: Optional[str] = None) -> Dict[str, Any]:
        """Query deployment history to determine if a software release or configuration change triggered the incident."""
        _validate_read_only_args(incident_id=incident_id, service=service)
        if not get_incident(incident_id):
            raise ValueError(f"Incident {incident_id} not found")
        deployments = query_deployments(incident_id, service=service)
        captured_ids = []
        for dep in deployments:
            evid_id = self.register_evidence(
                source_type="DEPLOYMENT",
                source_id=dep.id,
                summary=f"Deployment of {dep.service} ({dep.version}) by {dep.author} with commit {dep.commit_hash[:8]}",
                raw_data=dep.model_dump(),
                timestamp=dep.timestamp,
                relevance="HIGH"
            )
            captured_ids.append(evid_id)

        return {
            "status": "SUCCESS",
            "deployments": [d.model_dump() for d in deployments],
            "evidence_registered": captured_ids
        }

    @_track_tool_failures
    def search_runbooks_tool(self, query: str, service: Optional[str] = None) -> Dict[str, Any]:
        """Search runbook knowledge base using BM25 relevance scoring."""
        _validate_read_only_args(query=query, service=service)
        matches = retriever.search(query=query, service=service)
        captured_ids = []
        for match in matches[:2]:
            evid_id = self.register_evidence(
                source_type="RUNBOOK",
                source_id=match["runbook_id"],
                summary=f"Matched runbook '{match['title']}' for {match['service']} (BM25 score: {match['score']:.2f})",
                raw_data=match,
                relevance="HIGH"
            )
            captured_ids.append(evid_id)

        return {
            "status": "SUCCESS",
            "matches": matches,
            "evidence_registered": captured_ids
        }

    def get_runbook_detail_tool(self, runbook_id: str) -> Dict[str, Any]:
        """Retrieve full structured runbook markdown, symptoms, and mitigation steps."""
        _validate_read_only_args(runbook_id=runbook_id)
        rb = retriever.get_runbook(runbook_id)
        if not rb:
            return {"status": "ERROR", "message": f"Runbook {runbook_id} not found"}
        
        return {
            "status": "SUCCESS",
            "runbook": rb.model_dump()
        }

    @_track_tool_failures
    def correlate_signals_tool(self, incident_id: str) -> Dict[str, Any]:
        """Correlate temporal signals across deployments, error logs, and metric spikes."""
        _validate_read_only_args(incident_id=incident_id)
        if not get_incident(incident_id):
            raise ValueError(f"Incident {incident_id} not found")
        result = correlator.correlate(incident_id)
        evidence_id = self.register_evidence(
            source_type="CORRELATION",
            source_id=f"CORRELATION-{incident_id}",
            summary=result["causality_finding"],
            raw_data=result,
            timestamp=result["incident_start_time"],
            relevance="HIGH"
        )
        return {
            "status": "SUCCESS",
            "correlation": result,
            "evidence_registered": [evidence_id]
        }

    @_track_tool_failures
    def assess_risk_tool(self, incident_id: str, proposed_cause: str, category: str) -> Dict[str, Any]:
        """
        Perform cybersecurity risk analysis and impact assessment on the identified root cause.
        Evaluates CIA triad impact, CWE mapping, blast radius, and mitigation urgency.
        """
        _validate_read_only_args(incident_id=incident_id, proposed_cause=proposed_cause, category=category)
        incident = get_incident(incident_id)
        if not incident:
            raise ValueError(f"Incident {incident_id} not found")
        threat_vector = incident.threat_category or "UNCLASSIFIED_SYSTEM_FAULT"
        cwe = incident.cwe_id or "CWE-693"
        severity = incident.severity

        # Determine CIA Impact profile based on incident category
        cia_profile = {
            "BAD_DEPLOYMENT": {"confidentiality": "MEDIUM", "integrity": "HIGH", "availability": "CRITICAL"},
            "DATABASE_SLOWDOWN": {"confidentiality": "LOW", "integrity": "MEDIUM", "availability": "CRITICAL"},
            "EXHAUSTED_DISK": {"confidentiality": "LOW", "integrity": "HIGH", "availability": "CRITICAL"},
            "MEMORY_LEAK": {"confidentiality": "LOW", "integrity": "LOW", "availability": "CRITICAL"},
            "UPSTREAM_DEPENDENCY": {"confidentiality": "LOW", "integrity": "MEDIUM", "availability": "HIGH"},
            "CERTIFICATE_EXPIRATION": {"confidentiality": "CRITICAL", "integrity": "CRITICAL", "availability": "CRITICAL"},
            "CACHE_STAMPEDE": {"confidentiality": "LOW", "integrity": "LOW", "availability": "CRITICAL"},
            "RATE_LIMIT_MISCONFIG": {"confidentiality": "LOW", "integrity": "LOW", "availability": "CRITICAL"},
            "CONSUMER_REBALANCE_LOOP": {"confidentiality": "LOW", "integrity": "HIGH", "availability": "CRITICAL"},
            "AUTH_SECRET_ROTATION": {"confidentiality": "HIGH", "integrity": "CRITICAL", "availability": "CRITICAL"}
        }.get(category, {"confidentiality": "MEDIUM", "integrity": "MEDIUM", "availability": "HIGH"})

        risk_level = "CRITICAL" if severity == "P1" else "HIGH"
        sla = "< 30 minutes (Immediate Action Required)" if severity == "P1" else "< 2 hours (High Priority)"
        service_name = incident.service

        advisory = (
            f"Security Advisory for {service_name}: Root cause '{category}' mapped to {cwe}. "
            f"Threat vector '{threat_vector}'. Ensure mitigation actions are vetted and verified in staging before rollout."
        )

        risk_analysis = RiskAnalysis(
            threat_vector=threat_vector,
            cwe_id=cwe,
            cia_impact=cia_profile,
            risk_level=risk_level,
            blast_radius=f"Service '{service_name}' and connected tier-1 dependency mesh",
            remediation_sla=sla,
            security_advisory=advisory
        )

        evid_id = self.register_evidence(
            source_type="RISK",
            source_id=f"RISK-{incident_id}",
            summary=f"Risk Assessment for {incident_id}: {risk_level} ({threat_vector}, {cwe})",
            raw_data=risk_analysis.model_dump(),
            relevance="CRITICAL"
        )

        return {
            "status": "SUCCESS",
            "risk_analysis": risk_analysis.model_dump(),
            "evidence_registered": [evid_id]
        }

    # --- Mutating Action Blocker (Read-Only Enforcement) ---

    def execute_remediation_action(self, action_name: str, target: str) -> Dict[str, Any]:
        """Blocked in read-only mode to prevent unintended production state changes."""
        self.mutation_attempts.append(f"{action_name} on {target}")
        raise ReadOnlyViolationError(
            f"MUTATION BLOCKED: '{action_name}' on '{target}' is rejected. "
            "AI Incident Investigator is running in STRICT READ-ONLY MODE."
        )


tools = InvestigationToolRegistry()
