"""
Data models for AI Incident Investigator system.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class LogEntry(BaseModel):
    id: str
    timestamp: str
    service: str
    level: str  # INFO, WARN, ERROR, FATAL, DEBUG
    message: str
    trace_id: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)


class MetricPoint(BaseModel):
    timestamp: str
    metric_name: str
    service: str
    value: float
    unit: str
    labels: Dict[str, str] = Field(default_factory=dict)


class DeploymentEvent(BaseModel):
    id: str
    timestamp: str
    service: str
    version: str
    previous_version: str
    author: str
    commit_hash: str
    commit_message: str
    config_changes: Dict[str, Any] = Field(default_factory=dict)
    status: str = "SUCCESS"  # SUCCESS, FAILED, ROLLED_BACK


class RunbookSection(BaseModel):
    title: str
    content: str


class Runbook(BaseModel):
    id: str
    title: str
    service: str
    description: str
    symptoms: List[str]
    diagnostic_steps: List[str]
    mitigation_steps: List[str]
    raw_markdown: str


class Incident(BaseModel):
    id: str
    title: str
    service: str
    start_time: str
    end_time: str
    initial_alert: str
    severity: str  # P1, P2, P3
    status: str = "OPEN"  # OPEN, INVESTIGATING, RESOLVED
    ground_truth_cause: str
    ground_truth_category: str
    threat_category: Optional[str] = None
    cwe_id: Optional[str] = None
    key_signals: List[str]
    impact_summary: Optional[str] = None


class RiskAnalysis(BaseModel):
    threat_vector: str
    cwe_id: str
    cia_impact: Dict[str, str] = Field(default_factory=dict)
    risk_level: str  # CRITICAL, HIGH, MEDIUM, LOW
    blast_radius: str
    remediation_sla: str
    security_advisory: str


class EvidenceItem(BaseModel):
    id: str
    source_type: str  # "LOG", "METRIC", "DEPLOYMENT", "RUNBOOK", "RISK"
    source_id: str
    timestamp: Optional[str] = None
    summary: str
    raw_data: Any
    relevance: str


class InvestigationStep(BaseModel):
    step_num: int
    thought: str
    tool_name: str
    tool_args: Dict[str, Any]
    tool_result_preview: str
    evidence_gathered: List[str] = Field(default_factory=list)
    timestamp: str


class ConfidenceBreakdown(BaseModel):
    overall_score: float
    log_signal_weight: float
    metric_anomaly_weight: float
    temporal_proximity_weight: float
    runbook_alignment_weight: float
    explanation: str


class InvestigationResult(BaseModel):
    incident_id: str
    incident_title: str
    mode: str = "READ_ONLY"
    root_cause_diagnosis: str
    category: str
    confidence_score: float  # 0.0 to 1.0
    confidence_breakdown: Optional[ConfidenceBreakdown] = None
    evidence_chain: List[EvidenceItem]
    unsupported_claims: List[str]
    steps_count: int
    duration_seconds: float
    mitigation_recommended: List[str]
    risk_analysis: Optional[RiskAnalysis] = None
    trace: List[InvestigationStep] = Field(default_factory=list)
    temporal_correlation_summary: Optional[str] = None


class BenchmarkComparison(BaseModel):
    incident_id: str
    incident_title: str
    ground_truth: str
    category: str
    investigator_diagnosis: str
    investigator_correct: bool
    investigator_time_sec: float
    investigator_evidence_count: int
    investigator_unsupported_count: int
    baseline_diagnosis: str
    baseline_correct: bool
    baseline_time_sec: float
    baseline_evidence_count: int
    baseline_unsupported_count: int


class BenchmarkReport(BaseModel):
    total_incidents: int
    investigator_accuracy: float
    baseline_accuracy: float
    investigator_avg_time_sec: float
    baseline_avg_time_sec: float
    investigator_unsupported_rate: float
    baseline_unsupported_rate: float
    comparisons: List[BenchmarkComparison]


class ComponentHealth(BaseModel):
    status: str  # OPERATIONAL, DEGRADED, DOWN
    details: str
    latency_ms: Optional[float] = None


class SystemHealthStatus(BaseModel):
    status: str  # HEALTHY, DEGRADED
    version: str = "2.0.0"
    uptime_seconds: float
    components: Dict[str, ComponentHealth]
    read_only_mode: bool = True
    total_incidents_monitored: int


class SystemStats(BaseModel):
    total_incidents: int
    severity_counts: Dict[str, int]
    status_counts: Dict[str, int]
    category_counts: Dict[str, int]
    recent_incidents: List[Incident]
    avg_mttr_seconds: float
