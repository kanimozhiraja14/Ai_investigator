"""
AI Investigation Engine Unit Tests.
Tests investigation reasoning, evidence registration, confidence breakdown, and CWE risk mapping.
"""

import unittest
from incident_investigator.app.investigator import AIIncidentInvestigator
from incident_investigator.app.baseline import KeywordBaselineInvestigator
from incident_investigator.app.telemetry import get_incident, get_all_incidents


class TestInvestigationEngine(unittest.TestCase):
    def setUp(self):
        self.investigator = AIIncidentInvestigator()
        self.baseline = KeywordBaselineInvestigator()

    def test_investigate_all_10_scenarios(self):
        incidents = get_all_incidents()
        for inc in incidents:
            res = self.investigator.investigate(inc.id)
            self.assertEqual(res.incident_id, inc.id)
            self.assertEqual(res.mode, "READ_ONLY")
            self.assertGreater(len(res.root_cause_diagnosis), 10)
            self.assertGreater(len(res.evidence_chain), 0)
            self.assertIsNotNone(res.confidence_breakdown)
            self.assertGreaterEqual(res.confidence_score, 0.70)
            self.assertIsNotNone(res.risk_analysis)
            self.assertTrue(len(res.mitigation_recommended) > 0)
            self.assertTrue(len(res.trace) >= 5)

    def test_evidence_trace_integrity(self):
        res = self.investigator.investigate("INC-001")
        # Ensure every evidence item has a valid EVID ID
        for ev in res.evidence_chain:
            self.assertTrue(ev.id.startswith("EVID-"))
            self.assertIn(ev.source_type, ["RUNBOOK", "DEPLOYMENT", "LOG", "METRIC", "RISK"])
            self.assertTrue(len(ev.summary) > 5)

    def test_unsupported_claims_rate_is_zero(self):
        # AI engine must ground all findings in evidence
        incidents = get_all_incidents()
        for inc in incidents[:3]:
            res = self.investigator.investigate(inc.id)
            self.assertEqual(len(res.unsupported_claims), 0, f"Unsupported claims found for {inc.id}")

    def test_baseline_investigator_fallback(self):
        res = self.baseline.investigate("INC-001")
        self.assertEqual(res.incident_id, "INC-001")
        self.assertEqual(res.mode, "READ_ONLY")
        self.assertTrue(len(res.root_cause_diagnosis) > 5)


if __name__ == "__main__":
    unittest.main()
