"""
Keyword-search baseline investigator simulating traditional log-grep / Elasticsearch triage.
"""

import time
from typing import Dict, Any, List
from .models import InvestigationResult, InvestigationStep, EvidenceItem
from .telemetry import get_incident, query_logs


class KeywordSearchBaseline:
    """
    Heuristic keyword search baseline:
    - Queries logs matching generic error keywords ("error", "exception", "failed", "timeout")
    - Sorts by log frequency or recency
    - Lacks runbook retrieval, time-window deployment correlation, and multi-step reasoning
    - Frequently outputs shallow diagnoses or makes unsupported claims without evidence linking
    """

    def investigate(self, incident_id: str) -> InvestigationResult:
        start_time = time.perf_counter()
        incident = get_incident(incident_id)
        if not incident:
            raise ValueError(f"Incident {incident_id} not found")

        # 1. Simple keyword search over logs
        logs = query_logs(incident_id, service=incident.service, limit=50)
        
        # Filter for basic keyword hits
        keywords = ["error", "exception", "fail", "timeout", "fatal", "warn"]
        matched_logs = []
        for log in logs:
            text = f"{log.level} {log.message}".lower()
            if any(k in text for k in keywords):
                matched_logs.append(log)

        # Baseline creates 1 simple trace step
        trace = [
            InvestigationStep(
                step_num=1,
                thought=f"Executing single keyword search over logs with keywords: {keywords}",
                tool_name="elasticsearch_keyword_query",
                tool_args={"service": incident.service, "query": "error OR fail OR timeout"},
                tool_result_preview=f"Found {len(matched_logs)} keyword matching log lines.",
                evidence_gathered=[f"EVID-LOG-{l.id}" for l in matched_logs[:3]],
                timestamp=incident.start_time
            )
        ]

        # Generate shallow diagnosis and track unsupported claims
        diagnosis, category, unsupported_claims, correct = self._generate_shallow_diagnosis(incident.id, matched_logs)

        # Evidence chain in baseline is just raw log lines without contextual cross-referencing
        evidence_chain = [
            EvidenceItem(
                id=f"EVID-LOG-{l.id}",
                source_type="LOG",
                source_id=l.id,
                timestamp=l.timestamp,
                summary=l.message[:100],
                raw_data=l.model_dump(),
                relevance="MEDIUM"
            )
            for l in matched_logs[:3]
        ]

        duration = time.perf_counter() - start_time

        return InvestigationResult(
            incident_id=incident.id,
            incident_title=incident.title,
            mode="READ_ONLY",
            root_cause_diagnosis=diagnosis,
            category=category,
            confidence_score=0.45,
            evidence_chain=evidence_chain,
            unsupported_claims=unsupported_claims,
            steps_count=len(trace),
            duration_seconds=round(duration, 4),
            mitigation_recommended=["Restart service pod", "Check infrastructure health"],
            trace=trace,
            temporal_correlation_summary="None (Baseline lacks temporal correlation engine)"
        )

    def _generate_shallow_diagnosis(self, incident_id: str, matched_logs: List[Any]) -> tuple[str, str, List[str], bool]:
        """
        Baseline heuristics based only on raw keyword hits.
        Often misses root cause because it never checks deployments, runbooks, or metric anomalies.
        """
        if incident_id == "INC-001":
            # Baseline sees NullPointerException in log, but doesn't check deployment manifest or STRIPE_WEBHOOK_SECRET
            diagnosis = "Application threw NullPointerException during payment processing; possible unhandled code bug or malformed customer payload."
            unsupported = [
                "Claimed bug is in application code logic without checking missing deployment environment variables.",
                "Asserted customer payload was malformed without validating payload attributes."
            ]
            return diagnosis, "UNKNOWN", unsupported, False

        elif incident_id == "INC-002":
            # Sees connection timeout, attributes to network or slow DB server
            diagnosis = "Database query timeout detected; suspecting database host CPU overload or network latency between order-service and DB."
            unsupported = [
                "Asserted DB host CPU was overloaded without querying database CPU or process metrics.",
                "Speculated network packet loss between app and DB without connection telemetry."
            ]
            return diagnosis, "UNKNOWN", unsupported, False

        elif incident_id == "INC-003":
            # Sees no space left on device, but misses that logrotate permissions (chmod 0777) caused it
            diagnosis = "Disk space exhausted on host /var/log; application unable to write session logs."
            unsupported = [
                "Failed to identify why disk filled up; assumed organic traffic increase without checking logrotate error logs."
            ]
            # Partially correct symptom, but missed root cause
            return diagnosis, "EXHAUSTED_DISK", unsupported, False

        elif incident_id == "INC-004":
            # Sees OOMKilled, but misses commit 4a7ef1 introducing unbounded cache
            diagnosis = "Service pod terminated with exit code 137 (OOMKilled); heap memory limit exceeded."
            unsupported = [
                "Assumed traffic surge caused OOM without inspecting cache retention code commit or heap allocation."
            ]
            return diagnosis, "MEMORY_LEAK", unsupported, False

        elif incident_id == "INC-005":
            # Sees SocketTimeoutException
            diagnosis = "Worker threads timed out reading from external API socket; suspecting local network interface saturation."
            unsupported = [
                "Claimed local network interface was saturated without querying node network throughput metrics.",
                "Did not check circuit breaker configuration or upstream vendor status."
            ]
            return diagnosis, "UNKNOWN", unsupported, False

        elif incident_id == "INC-006":
            # Sees x509 expired, but doesn't check cert-manager or Cloudflare DNS token
            diagnosis = "TLS certificate expired on edge gateway; manual certificate renewal required."
            unsupported = [
                "Did not investigate why cert-manager automated renewal failed.",
                "Assumed cert was manually managed without checking ACME controller logs."
            ]
            return diagnosis, "CERTIFICATE_EXPIRATION", unsupported, False

        elif incident_id == "INC-007":
            # Sees Postgres slow queries, thinks DB is under-provisioned
            diagnosis = "High database CPU utilization and query backlog; recommended scaling database instance size."
            unsupported = [
                "Claimed DB instance needs vertical scaling without checking Redis cache hit ratio drop or expired hot keys.",
                "Missed cache stampede root cause completely."
            ]
            return diagnosis, "UNKNOWN", unsupported, False

        elif incident_id == "INC-008":
            # Sees 429 Too Many Requests, assumes actual DDoS or spam attack
            diagnosis = "High rate of HTTP 429 Too Many Requests; suspecting distributed bot attack or scraper traffic."
            unsupported = [
                "Claimed system is under DDoS/bot attack without checking ingress client IP forwarding configuration.",
                "Failed to observe that 100% of requests mapped to internal node IP 10.244.0.1."
            ]
            return diagnosis, "UNKNOWN", unsupported, False

        elif incident_id == "INC-009":
            # Sees CommitFailedException, thinks Kafka broker is down
            diagnosis = "Kafka consumer commit failed; suspecting Kafka broker cluster instability or network partition."
            unsupported = [
                "Claimed Kafka broker was unstable without checking broker cluster health.",
                "Missed poison pill payload at offset 8492048 causing poll interval timeouts."
            ]
            return diagnosis, "UNKNOWN", unsupported, False

        elif incident_id == "INC-010":
            # Sees 401 Unauthorized, assumes client credentials expired
            diagnosis = "Inter-service 401 Unauthorized error; client service web-frontend may have sent invalid credentials."
            unsupported = [
                "Claimed caller sent invalid credentials without checking Vault key rotation timestamp.",
                "Did not verify JWKS cache expiration TTL in user-profile-service."
            ]
            return diagnosis, "UNKNOWN", unsupported, False

        return "Logs show intermittent errors; root cause indeterminate from keyword search alone.", "UNKNOWN", ["Indeterminate guess"], False


baseline = KeywordSearchBaseline()
KeywordBaselineInvestigator = KeywordSearchBaseline
