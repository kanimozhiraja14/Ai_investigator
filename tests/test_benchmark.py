"""
Benchmark Engine Unit Tests.
Validates comparative evaluation between AI Incident Investigator and Keyword Baseline.
"""

import unittest
from incident_investigator.app.benchmark import benchmark_engine


class TestBenchmarkEngine(unittest.TestCase):
    def test_run_single_incident_benchmark(self):
        comparison = benchmark_engine.compare_single_incident("INC-001")
        self.assertEqual(comparison.incident_id, "INC-001")
        self.assertTrue(comparison.investigator_correct)
        self.assertEqual(comparison.investigator_unsupported_count, 0)
        self.assertGreater(comparison.investigator_evidence_count, 0)

    def test_run_full_system_benchmark(self):
        report = benchmark_engine.run_full_benchmark()
        self.assertEqual(report.total_incidents, 10)
        self.assertEqual(report.investigator_accuracy, 100.0)
        self.assertEqual(report.investigator_unsupported_rate, 0.0)
        self.assertLess(report.investigator_unsupported_rate, report.baseline_unsupported_rate)
        self.assertEqual(len(report.comparisons), 10)


if __name__ == "__main__":
    unittest.main()
