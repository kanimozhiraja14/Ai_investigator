"""
BM25 Runbook Retrieval Engine Unit Tests.
Validates indexing, scoring formula, query relevance, and service filtering.
"""

import unittest
from incident_investigator.app.runbook_retriever import retriever


class TestRunbookRetrieval(unittest.TestCase):
    def test_runbook_corpus_loaded(self):
        self.assertGreaterEqual(len(retriever.runbooks), 10)

    def test_bm25_query_payment_service(self):
        results = retriever.search("PaymentServiceHighErrorRate 5xx error canary", service="payment-service")
        self.assertTrue(len(results) > 0)
        top_match = results[0]
        self.assertIn("payment", top_match["title"].lower())
        self.assertGreater(top_match["score"], 0.0)

    def test_bm25_query_db_connection_pool(self):
        results = retriever.search("database connection pool exhausted waiting timeout", service="order-service")
        self.assertTrue(len(results) > 0)
        self.assertIn("connection", results[0]["title"].lower())

    def test_bm25_query_disk_space(self):
        results = retriever.search("disk space saturation 98% filesystem full", service="auth-service")
        self.assertTrue(len(results) > 0)
        self.assertIn("disk", results[0]["title"].lower())

    def test_get_runbook_by_id(self):
        rb = retriever.get_runbook("payment_service_5xx")
        self.assertIsNotNone(rb)
        self.assertEqual(rb.id, "payment_service_5xx")
        self.assertIn("payment", rb.title.lower())
        self.assertTrue(len(rb.mitigation_steps) > 0)


if __name__ == "__main__":
    unittest.main()
