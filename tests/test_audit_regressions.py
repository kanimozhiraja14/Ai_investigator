import unittest
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from types import SimpleNamespace
from unittest.mock import patch

from incident_investigator.app.benchmark import _evaluate_correctness, run_benchmark
from incident_investigator.app.correlation_engine import TimeWindowCorrelator
from incident_investigator.app.investigator import AIIncidentInvestigator
from incident_investigator.app.models import DeploymentEvent, LogEntry, MetricPoint
from incident_investigator.app.runbook_retriever import retriever
from incident_investigator.app.telemetry import get_all_incidents
from incident_investigator.app.tools import ReadOnlyViolationError, tools


class TestEvidenceAndToolContracts(unittest.TestCase):
    def setUp(self):
        tools.clear()

    def test_all_ten_scenarios_match_expected_categories_and_runbooks(self):
        expected_runbooks = {
            "INC-001": "payment_service_5xx",
            "INC-002": "db_connection_pool",
            "INC-003": "disk_space_exhaustion",
            "INC-004": "oom_memory_leak",
            "INC-005": "third_party_degradation",
            "INC-006": "ingress_ssl_expiry",
            "INC-007": "redis_cache_stampede",
            "INC-008": "rate_limiting_misconfig",
            "INC-009": "kafka_consumer_lag",
            "INC-010": "jwt_auth_rotation_failure",
        }
        investigator = AIIncidentInvestigator()

        for incident in get_all_incidents():
            with self.subTest(incident=incident.id):
                result = investigator.investigate(incident.id)
                matches = retriever.search(
                    incident.initial_alert,
                    service=incident.service,
                    top_k=1,
                )
                self.assertEqual(result.category, incident.ground_truth_category)
                self.assertTrue(matches)
                self.assertEqual(matches[0]["runbook_id"], expected_runbooks[incident.id])
                self.assertIsNotNone(result.risk_analysis)
                self.assertEqual(len(result.trace), result.steps_count)
                evidence_ids = {item.id for item in result.evidence_chain}
                trace_evidence_ids = {
                    evidence_id
                    for step in result.trace
                    for evidence_id in step.evidence_gathered
                }
                self.assertTrue(trace_evidence_ids.issubset(evidence_ids))
                self.assertTrue(result.trace[1].evidence_gathered)

    def test_metric_evidence_ids_preserve_each_sample(self):
        result = AIIncidentInvestigator().investigate("INC-001")
        metric_evidence = [
            item for item in result.evidence_chain
            if item.source_type == "METRIC"
        ]
        self.assertEqual(len(metric_evidence), 7)
        self.assertEqual(len({item.id for item in metric_evidence}), 7)

    def test_concurrent_investigations_do_not_mix_shared_evidence(self):
        state_lock = Lock()
        active = 0
        max_active = 0
        search_runbooks = tools.search_runbooks_tool

        def delayed_search(**kwargs):
            nonlocal active, max_active
            with state_lock:
                active += 1
                max_active = max(max_active, active)
            try:
                time.sleep(0.01)
                return search_runbooks(**kwargs)
            finally:
                with state_lock:
                    active -= 1

        incident_ids = ["INC-001", "INC-002", "INC-003", "INC-004", "INC-005"]
        with patch.object(tools, "search_runbooks_tool", side_effect=delayed_search):
            with ThreadPoolExecutor(max_workers=len(incident_ids)) as pool:
                results = list(pool.map(AIIncidentInvestigator().investigate, incident_ids))

        self.assertEqual(max_active, 1)
        for incident_id, result in zip(incident_ids, results):
            with self.subTest(incident=incident_id):
                correlation_evidence = [
                    item for item in result.evidence_chain
                    if item.source_type == "CORRELATION"
                ]
                self.assertEqual(len(correlation_evidence), 1)
                self.assertEqual(correlation_evidence[0].raw_data["incident_id"], incident_id)

    def test_six_investigation_tools_return_expected_shapes(self):
        cases = [
            (tools.search_runbooks_tool, {"query": "payment 500", "service": "payment-service"}, "matches"),
            (tools.correlate_signals_tool, {"incident_id": "INC-001"}, "correlation"),
            (tools.get_deployments_tool, {"incident_id": "INC-001"}, "deployments"),
            (tools.query_logs_tool, {"incident_id": "INC-001"}, "logs"),
            (tools.query_metrics_tool, {"incident_id": "INC-001"}, "metrics"),
            (
                tools.assess_risk_tool,
                {"incident_id": "INC-001", "proposed_cause": "test", "category": "BAD_DEPLOYMENT"},
                "risk_analysis",
            ),
        ]
        for tool, kwargs, expected_key in cases:
            with self.subTest(tool=tool.__name__):
                tools.clear()
                result = tool(**kwargs)
                self.assertEqual(result["status"], "SUCCESS")
                self.assertIn(expected_key, result)
                self.assertTrue(result["evidence_registered"])

    def test_invalid_incidents_fail_instead_of_returning_success_shaped_data(self):
        calls = [
            (tools.correlate_signals_tool, {"incident_id": "NO-SUCH"}),
            (tools.get_deployments_tool, {"incident_id": "NO-SUCH"}),
            (tools.query_logs_tool, {"incident_id": "NO-SUCH"}),
            (tools.query_metrics_tool, {"incident_id": "NO-SUCH"}),
            (
                tools.assess_risk_tool,
                {"incident_id": "NO-SUCH", "proposed_cause": "cause", "category": "UNKNOWN"},
            ),
        ]
        for tool, kwargs in calls:
            with self.subTest(tool=tool.__name__):
                with self.assertRaisesRegex(ValueError, "not found"):
                    tool(**kwargs)

    def test_mutation_words_are_blocked_by_each_relevant_tool(self):
        calls = [
            (tools.search_runbooks_tool, {"query": "DROP"}),
            (tools.correlate_signals_tool, {"incident_id": "INC-001; DROP"}),
            (tools.get_deployments_tool, {"incident_id": "INC-001", "service": "DELETE"}),
            (tools.query_logs_tool, {"incident_id": "INC-001", "search": "UPDATE"}),
            (tools.query_metrics_tool, {"incident_id": "INC-001", "metric_name": "INSERT"}),
            (
                tools.assess_risk_tool,
                {"incident_id": "INC-001", "proposed_cause": "WRITE", "category": "BAD_DEPLOYMENT"},
            ),
        ]
        for tool, kwargs in calls:
            with self.subTest(tool=tool.__name__):
                with self.assertRaises(ReadOnlyViolationError):
                    tool(**kwargs)

    def test_retrieval_handles_empty_irrelevant_and_missing_ids(self):
        self.assertEqual(retriever.search("  "), [])
        self.assertEqual(retriever.search("qzxvzz nonexisting ingredient"), [])
        self.assertIsNone(retriever.get_runbook("does-not-exist"))

    def test_benchmark_applies_the_same_correctness_heuristic(self):
        report = run_benchmark()
        incidents = {incident.id: incident for incident in get_all_incidents()}
        for comparison in report.comparisons:
            incident = incidents[comparison.incident_id]
            self.assertEqual(
                comparison.investigator_correct,
                _evaluate_correctness(
                    comparison.investigator_diagnosis,
                    incident.ground_truth_cause,
                    incident.key_signals,
                ),
            )
            self.assertEqual(
                comparison.baseline_correct,
                _evaluate_correctness(
                    comparison.baseline_diagnosis,
                    incident.ground_truth_cause,
                    incident.key_signals,
                ),
            )


class TestCorrelationBoundaries(unittest.TestCase):
    def setUp(self):
        self.correlator = TimeWindowCorrelator()
        self.incident = SimpleNamespace(
            id="TEST-001",
            service="test-service",
            start_time="2026-01-01T12:00:00+02:00",
        )

    @staticmethod
    def _log(log_id, timestamp):
        return LogEntry(
            id=log_id,
            timestamp=timestamp,
            service="test-service",
            level="ERROR",
            message="test error",
        )

    def test_window_filters_events_and_orders_equivalent_timezones(self):
        deployment_in = DeploymentEvent(
            id="DEP-IN",
            timestamp="2026-01-01T09:55:00Z",
            service="test-service",
            version="v2",
            previous_version="v1",
            author="test",
            commit_hash="abc",
            commit_message="test",
        )
        deployment_out = deployment_in.model_copy(
            update={"id": "DEP-OUT", "timestamp": "2026-01-01T09:54:59Z"}
        )
        log_before = self._log("LOG-BEFORE", "2026-01-01T11:59:30+02:00")
        log_after = self._log("LOG-AFTER", "2026-01-01T10:05:00Z")
        log_out = self._log("LOG-OUT", "2026-01-01T10:10:01Z")
        metric = MetricPoint(
            timestamp="2026-01-01T10:00:00Z",
            metric_name="request_latency",
            service="test-service",
            value=2000,
            unit="ms",
        )

        with (
            patch("incident_investigator.app.correlation_engine.get_incident", return_value=self.incident),
            patch(
                "incident_investigator.app.correlation_engine.query_deployments",
                return_value=[deployment_out, deployment_in],
            ),
            patch(
                "incident_investigator.app.correlation_engine.query_logs",
                return_value=[log_after, log_out, log_before],
            ),
            patch("incident_investigator.app.correlation_engine.query_metrics", return_value=[metric]),
        ):
            result = self.correlator.correlate(
                "TEST-001",
                window_minutes_before=5,
                window_minutes_after=10,
            )

        self.assertEqual(result["correlated_deployments_count"], 1)
        self.assertEqual(result["error_logs_count"], 2)
        self.assertEqual(
            [event["id"] for event in result["timeline"]],
            ["DEP-IN", "LOG-BEFORE", "MTR-request_latency-2026-01-01T10:00:00Z", "LOG-AFTER"],
        )
        self.assertEqual(result["first_error_log"]["id"], "LOG-BEFORE")

    def test_invalid_or_naive_timestamps_are_rejected(self):
        for timestamp in (None, "not-a-time", "2026-01-01T10:00:00"):
            with self.subTest(timestamp=timestamp):
                with self.assertRaises(ValueError):
                    self.correlator._parse_iso(timestamp)

    def test_negative_window_is_rejected(self):
        with patch("incident_investigator.app.correlation_engine.get_incident", return_value=self.incident):
            with self.assertRaisesRegex(ValueError, "non-negative"):
                self.correlator.correlate("TEST-001", window_minutes_before=-1)


if __name__ == "__main__":
    unittest.main()
