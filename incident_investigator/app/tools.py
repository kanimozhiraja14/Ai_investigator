"""
Read-only investigation tools with evidence registration and mutation blocking.
"""

from typing import Dict, Any, List, Optional
from .models import EvidenceItem, LogEntry, MetricPoint, DeploymentEvent, RiskAnalysis
from .telemetry import query_logs, query_metrics, query_deployments, get_incident
from .runbook_retriever import retriever
from .correlation_engine import correlator


class ReadOnlyViolationError(Exception):
    """Raised when an agent attempts a mutating operation in read-only mode."""
    pass


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

    def query_logs_tool(self, incident_id: str, service: Optional[str] = None, level: Optional[str] = None, search: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
        """Query structured logs and capture discovered records as verified evidence."""
        logs = query_logs(incident_id, service=service, level=level, search=search, limit=limit)
        captured_ids = []
        for log in logs:
            evid_id = self.register_evidence(
                source_type="LOG",
                source_id=log.id,
                summary=f"[{log.level}] {log.service} at {log.timestamp}: {log.message[:140]}",
                raw_data=log.dict(),
                timestamp=log.timestamp,
                relevance="HIGH" if log.level in ["ERROR", "FATAL"] else "MEDIUM"
            )
            captured_ids.append(evid_id)

        return {
            "status": "SUCCESS",
            "count": len(logs),
            "logs": [l.dict() for l in logs],
            "evidence_registered": captured_ids
        }

    def query_metrics_tool(self, incident_id: str, service: Optional[str] = None, metric_name: Optional[str] = None) -> Dict[str, Any]:
        """Query time-series metrics and register anomalies as evidence."""
        metrics = query_metrics(incident_id, service=service, metric_name=metric_name)
        captured_ids = []
        for m in metrics:
            evid_id = self.register_evidence(
                source_type="METRIC",
                source_id=f"{m.metric_name}-{m.timestamp}",
                summary=f"{m.service} metric {m.metric_name} = {m.value} {m.unit} at {m.timestamp}",
                raw_data=m.dict(),
                timestamp=m.timestamp,
                relevance="HIGH"
            )
            captured_ids.append(evid_id)

        return {
            "status": "SUCCESS",
            "count": len(metrics),
            "metrics": [m.dict() for m in metrics],
            "evidence_registered": captured_ids
        }

    def get_deployments_tool(self, incident_id: str, service: Optional[str] = None) -> Dict[str, Any]:
        """Query deployment history and commit diffs within the incident window."""
        deployments = query_deployments(incident_id, service=service)
        captured_ids = []
        for dep in deployments:
            evid_id = self.register_evidence(
                source_type="DEPLOYMENT",
                source_id=dep.id,
                summary=f"Deployment {dep.id} ({dep.service}:{dep.version}) by {dep.author} at {dep.timestamp} - commit {dep.commit_hash}",
                raw_data=dep.dict(),
                timestamp=dep.timestamp,
                relevance="HIGH"
            )
            captured_ids.append(evid_id)

        return {
            "status": "SUCCESS",
            "count": len(deployments),
            "deployments": [d.dict() for d in deployments],
            "evidence_registered": captured_ids
        }

    def search_runbooks_tool(self, query: str, service: Optional[str] = None) -> Dict[str, Any]:
        """Retrieve relevant runbooks using BM25 ranking based on symptoms and service."""
        matches = retriever.search(query, service=service, top_k=3)
        captured_ids = []
        for m in matches:
            evid_id = self.register_evidence(
                source_type="RUNBOOK",
                source_id=m["runbook_id"],
                summary=f"Runbook '{m['title']}' for {m['service']} (score={m['score']})",
                raw_data=m,
                relevance="HIGH"
            )
            captured_ids.append(evid_id)

        return {
            "status": "SUCCESS",
            "matches": matches,
            "evidence_registered": captured_ids
        }

    def get_runbook_detail_tool(self, runbook_id: str) -> Dict[str, Any]:
        """Fetch full markdown content and checklist of a specific runbook."""
        rb = retriever.get_runbook(runbook_id)
        if not rb:
            return {"status": "ERROR", "message": f"Runbook {runbook_id} not found"}

        evid_id = self.register_evidence(
            source_type="RUNBOOK",
            source_id=rb.id,
            summary=f"Full runbook guidance for {rb.title}",
            raw_data={"symptoms": rb.symptoms, "diagnostic_steps": rb.diagnostic_steps, "mitigation": rb.mitigation_steps},
            relevance="HIGH"
        )
        return {
            "status": "SUCCESS",
            "runbook": rb.dict(),
            "evidence_registered": [evid_id]
        }

    def correlate_signals_tool(self, incident_id: str) -> Dict[str, Any]:
        """Perform cross-telemetry time-window correlation over deployments, logs, and metrics."""
        result = correlator.correlate(incident_id)
        return {
            "status": "SUCCESS",
            "correlation": result
        }

    def assess_risk_tool(self, incident_id: str, proposed_cause: str, category: str) -> Dict[str, Any]:
        """
        Perform cybersecurity risk analysis and impact assessment on the identified root cause.
        Evaluates CIA triad impact, CWE mapping, blast radius, and mitigation urgency.
        """
        incident = get_incident(incident_id)
        threat_vector = incident.threat_category if incident and incident.threat_category else "UNCLASSIFIED_SYSTEM_FAULT"
        cwe = incident.cwe_id if incident and incident.cwe_id else "CWE-693"
        severity = incident.severity if incident else "P1"

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
        service_name = incident.service if incident else "unknown"

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
            raw_data=risk_analysis.dict(),
            relevance="CRITICAL"
        )

        return {
            "status": "SUCCESS",
            "risk_analysis": risk_analysis.dict(),
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
