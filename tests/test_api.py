"""
API and Endpoint Unit Tests for AI Incident Investigator.
Tests all FastAPI endpoint contracts, status responses, and data models.
"""

import unittest
from incident_investigator.app.main import (
    app,
    get_health_status,
    get_dashboard_stats,
    list_incidents,
    get_incident_details,
    get_logs,
    get_metrics,
    get_deployments,
    search_runbooks,
    get_runbook,
    investigate_incident,
    get_investigation_trace,
    run_system_benchmark,
    list_evidence,
    export_benchmark_report
)


class TestAPIEndpoints(unittest.TestCase):
    def test_health_check(self):
        health = get_health_status()
        self.assertEqual(health.status, "HEALTHY")
        self.assertTrue(health.read_only_mode)
        self.assertIn("api_gateway", health.components)
        self.assertIn("telemetry_database", health.components)
        self.assertIn("runbook_retrieval_engine", health.components)
        self.assertIn("read_only_enforcement", health.components)
        self.assertEqual(health.total_incidents_monitored, 10)

    def test_dashboard_stats(self):
        stats = get_dashboard_stats()
        self.assertEqual(stats.total_incidents, 10)
        self.assertGreaterEqual(stats.severity_counts.get("P1", 0), 1)
        self.assertGreaterEqual(len(stats.recent_incidents), 1)

    def test_list_incidents(self):
        incidents = list_incidents()
        self.assertEqual(len(incidents), 10)
        # Verify cybersecurity metadata
        for inc in incidents:
            self.assertTrue(hasattr(inc, "id"))
            self.assertTrue(hasattr(inc, "threat_category"))
            self.assertTrue(hasattr(inc, "cwe_id"))
            self.assertIsNotNone(inc.threat_category)
            self.assertIsNotNone(inc.cwe_id)

    def test_list_incidents_filtered_by_severity(self):
        p1_incidents = list_incidents(severity="P1")
        self.assertTrue(len(p1_incidents) > 0)
        for inc in p1_incidents:
            self.assertEqual(inc.severity, "P1")

    def test_get_incident_details(self):
        inc = get_incident_details("INC-001")
        self.assertEqual(inc.id, "INC-001")
        self.assertEqual(inc.service, "payment-service")

    def test_get_telemetry_endpoints(self):
        logs = get_logs(incident_id="INC-001", level="ERROR")
        self.assertTrue(len(logs) > 0)
        self.assertEqual(logs[0].service, "payment-service")

        metrics = get_metrics(incident_id="INC-001")
        self.assertTrue(len(metrics) > 0)

        deps = get_deployments(incident_id="INC-001")
        self.assertTrue(len(deps) > 0)

    def test_runbook_retrieval_endpoint(self):
        results = search_runbooks(query="connection pool exhausted", service="order-service")
        self.assertTrue(len(results) > 0)
        top_rb_id = results[0]["runbook_id"]
        rb = get_runbook(top_rb_id)
        self.assertEqual(rb.id, top_rb_id)
        self.assertTrue(len(rb.mitigation_steps) > 0)


if __name__ == "__main__":
    unittest.main()
