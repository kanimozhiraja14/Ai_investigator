"""
Read-Only Security Guard Unit Tests.
Verifies that all tool operations are strictly read-only and mutation verbs are intercepted.
"""

import unittest
from incident_investigator.app.tools import tools, ReadOnlyViolationError


class TestReadOnlySecurity(unittest.TestCase):
    def test_safe_read_queries(self):
        # Normal safe read operations must succeed
        res = tools.query_logs_tool(incident_id="INC-001", level="ERROR")
        self.assertIn("logs", res)

        metrics = tools.query_metrics_tool(incident_id="INC-001")
        self.assertIn("metrics", metrics)

        deps = tools.get_deployments_tool(incident_id="INC-001")
        self.assertIn("deployments", deps)

    def test_sql_drop_table_rejection(self):
        with self.assertRaises(ReadOnlyViolationError):
            tools.query_logs_tool(incident_id="INC-001; DROP TABLE logs; --")

    def test_sql_delete_rejection(self):
        with self.assertRaises(ReadOnlyViolationError):
            tools.query_logs_tool(incident_id="INC-001", service="payment-service; DELETE FROM services")

    def test_sql_insert_rejection(self):
        with self.assertRaises(ReadOnlyViolationError):
            tools.query_metrics_tool(incident_id="INC-001", metric_name="INSERT INTO metrics VALUES (1)")

    def test_cli_exec_rejection(self):
        with self.assertRaises(ReadOnlyViolationError):
            tools.search_runbooks_tool(query="EXEC xp_cmdshell('whoami')")

    def test_write_operation_rejection(self):
        with self.assertRaises(ReadOnlyViolationError):
            tools.search_runbooks_tool(query="WRITE /etc/passwd")


if __name__ == "__main__":
    unittest.main()
