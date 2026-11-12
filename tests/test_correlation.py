"""
Temporal Correlation Engine Unit Tests.
Validates time-window sequencing, deployment alignment, metric anomaly detection, and causality finding.
"""

import unittest
from incident_investigator.app.correlation_engine import correlation_engine
from incident_investigator.app.telemetry import get_incident


class TestTemporalCorrelation(unittest.TestCase):
    def test_correlate_inc_001_deployment_precedence(self):
        corr = correlation_engine.correlate_incident("INC-001")
        self.assertEqual(corr["incident_id"], "INC-001")
        self.assertTrue(corr["has_deployment_in_window"])
        self.assertGreater(len(corr["deployments"]), 0)
        self.assertGreater(len(corr["anomalous_metrics"]), 0)
        self.assertGreater(len(corr["error_logs"]), 0)
        self.assertIn("Deployment", corr["causality_finding"])

    def test_correlate_inc_002_resource_exhaustion(self):
        corr = correlation_engine.correlate_incident("INC-002")
        self.assertEqual(corr["incident_id"], "INC-002")
        self.assertGreater(len(corr["anomalous_metrics"]), 0)
        self.assertGreater(len(corr["error_logs"]), 0)

    def test_temporal_event_sequence_chronology(self):
        corr = correlation_engine.correlate_incident("INC-001")
        events = corr["temporal_event_sequence"]
        self.assertTrue(len(events) > 0)
        # Verify chronological ordering
        timestamps = [e["timestamp"] for e in events]
        sorted_timestamps = sorted(timestamps)
        self.assertEqual(timestamps, sorted_timestamps)


if __name__ == "__main__":
    unittest.main()
