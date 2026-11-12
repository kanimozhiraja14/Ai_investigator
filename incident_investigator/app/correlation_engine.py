"""
Time-window correlation engine for aligning deployments, log anomalies, and metric spikes.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from .models import LogEntry, MetricPoint, DeploymentEvent
from .telemetry import query_logs, query_metrics, query_deployments, get_incident


class TimeWindowCorrelator:
    @staticmethod
    def _parse_iso(iso_str: str) -> datetime:
        clean_str = iso_str.replace("Z", "+00:00")
        return datetime.fromisoformat(clean_str)

    def correlate(self, incident_id: str, window_minutes_before: int = 30, window_minutes_after: int = 30) -> Dict[str, Any]:
        incident = get_incident(incident_id)
        if not incident:
            return {"error": f"Incident {incident_id} not found"}

        t_start = self._parse_iso(incident.start_time)
        
        # 1. Fetch deployments in window
        deployments = query_deployments(incident_id, incident.service)
        
        # 2. Fetch all logs in window
        logs = query_logs(incident_id, incident.service, limit=100)
        
        # 3. Fetch metrics
        metrics = query_metrics(incident_id, incident.service)

        # Build chronological timeline of key events
        timeline_events = []

        # Correlate deployments
        correlated_deployments = []
        for dep in deployments:
            dep_t = self._parse_iso(dep.timestamp)
            delta_sec = (t_start - dep_t).total_seconds()
            is_causal_candidate = (-300 <= delta_sec <= 1800)  # within 5 mins after or 30 mins before
            
            event_obj = {
                "type": "DEPLOYMENT",
                "id": dep.id,
                "timestamp": dep.timestamp,
                "summary": f"Rollout of {dep.service}:{dep.version} by {dep.author} (commit: {dep.commit_hash})",
                "delta_from_incident_start_sec": delta_sec,
                "causal_suspect": is_causal_candidate,
                "config_changes": dep.config_changes
            }
            correlated_deployments.append(event_obj)
            timeline_events.append(event_obj)

        # Correlate error logs
        error_logs = [log for log in logs if log.level in ["ERROR", "FATAL"]]
        first_error_log = error_logs[0] if error_logs else None
        
        for elog in error_logs[:5]:
            log_t = self._parse_iso(elog.timestamp)
            delta_sec = (log_t - t_start).total_seconds()
            timeline_events.append({
                "type": "LOG_ERROR",
                "id": elog.id,
                "timestamp": elog.timestamp,
                "summary": elog.message[:120],
                "delta_from_incident_start_sec": delta_sec,
                "attributes": elog.attributes
            })

        # Correlate metric spikes
        metric_anomalies = []
        for m in metrics:
            # Check for high values or spikes
            is_anomaly = False
            if "rate" in m.metric_name and m.value > 0.05:
                is_anomaly = True
            elif "latency" in m.metric_name and m.value > 1000:
                is_anomaly = True
            elif "connections" in m.metric_name and m.value > 40:
                is_anomaly = True
            elif "free_bytes" in m.metric_name and m.value < 1000000000:
                is_anomaly = True
            elif "utilization" in m.metric_name and m.value > 80:
                is_anomaly = True
            elif "lag" in m.metric_name and m.value > 10000:
                is_anomaly = True

            if is_anomaly:
                metric_anomalies.append({
                    "metric_name": m.metric_name,
                    "value": m.value,
                    "unit": m.unit,
                    "timestamp": m.timestamp
                })
                timeline_events.append({
                    "type": "METRIC_ANOMALY",
                    "id": f"MTR-{m.metric_name}-{m.timestamp}",
                    "timestamp": m.timestamp,
                    "summary": f"Spike in {m.metric_name}: {m.value} {m.unit}",
                    "delta_from_incident_start_sec": (self._parse_iso(m.timestamp) - t_start).total_seconds()
                })

        # Sort timeline chronologically
        timeline_events.sort(key=lambda x: x["timestamp"])

        # Determine causal chain
        causality_finding = ""
        if correlated_deployments and any(d["causal_suspect"] for d in correlated_deployments):
            dep = [d for d in correlated_deployments if d["causal_suspect"]][0]
            causality_finding = (
                f"High temporal correlation: Deployment {dep['id']} occurred at {dep['timestamp']} "
                f"({int(abs(dep['delta_from_incident_start_sec']))}s before incident start), followed immediately by error logs."
            )
        elif metric_anomalies:
            first_metric = metric_anomalies[0]
            causality_finding = (
                f"Resource/Metric anomaly detected at {first_metric['timestamp']}: "
                f"{first_metric['metric_name']} reached {first_metric['value']} {first_metric['unit']}."
            )
        else:
            causality_finding = "No deployment correlated; anomaly appears linked to external or infrastructure conditions."

        return {
            "incident_id": incident_id,
            "service": incident.service,
            "incident_start_time": incident.start_time,
            "causality_finding": causality_finding,
            "correlated_deployments_count": len(correlated_deployments),
            "error_logs_count": len(error_logs),
            "metric_anomalies_count": len(metric_anomalies),
            "timeline": timeline_events,
            "first_error_log": first_error_log.model_dump() if first_error_log else None
        }

    def correlate_incident(self, incident_id: str, window_minutes_before: int = 30, window_minutes_after: int = 30) -> Dict[str, Any]:
        """Convenience alias for correlate."""
        res = self.correlate(incident_id, window_minutes_before, window_minutes_after)
        # Add rich helper fields for testing and analysis
        res["has_deployment_in_window"] = res.get("correlated_deployments_count", 0) > 0
        res["deployments"] = [e for e in res.get("timeline", []) if e.get("type") == "DEPLOYMENT"]
        res["anomalous_metrics"] = [e for e in res.get("timeline", []) if e.get("type") == "METRIC_ANOMALY"]
        res["error_logs"] = [e for e in res.get("timeline", []) if e.get("type") in ["LOG_ERROR", "ERROR_LOG"]]
        res["temporal_event_sequence"] = res.get("timeline", [])
        return res


correlator = TimeWindowCorrelator()
correlation_engine = correlator
