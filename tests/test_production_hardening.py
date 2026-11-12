import os
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from incident_investigator.app.config import (
    get_allowed_origins,
    get_rate_limit,
    validate_environment,
)
from incident_investigator.app.main import app, request_rate_limiter
from incident_investigator.app.tools import get_tool_failure_count, tools


class TestProductionHardening(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_api_requires_configured_bearer_token_and_rejects_invalid_tokens(self):
        token = "t" * 40
        with patch.dict(
            os.environ,
            {"APP_ENV": "production", "AI_INVESTIGATOR_API_TOKEN": token},
        ):
            self.assertEqual(self.client.get("/api/incidents").status_code, 401)
            invalid = self.client.get(
                "/api/incidents",
                headers={"Authorization": f"Bearer {'x' * 40}"},
            )
            self.assertEqual(invalid.status_code, 401)
            self.assertEqual(
                self.client.get(
                    "/api/incidents",
                    headers={"Authorization": f"Bearer {token}"},
                ).status_code,
                200,
            )
            self.assertEqual(self.client.get("/api/healthz").status_code, 200)
            self.assertEqual(self.client.get("/api/health").status_code, 401)

    def test_request_logs_do_not_include_credentials_or_query_values(self):
        token = "s" * 40
        private_value = "do-not-log-this-query"
        with patch.dict(
            os.environ,
            {"APP_ENV": "production", "AI_INVESTIGATOR_API_TOKEN": token},
        ):
            with self.assertLogs("incident_investigator", level="INFO") as captured:
                self.client.get(f"/api/incidents?search={private_value}")
        logged = "\n".join(captured.output)
        self.assertNotIn(token, logged)
        self.assertNotIn(private_value, logged)

    def test_unexpected_api_errors_are_redacted_and_correlated(self):
        private_value = "synthetic-secret-error-detail"
        with patch("incident_investigator.app.main.investigator.investigate") as run:
            run.side_effect = RuntimeError(private_value)
            with self.assertLogs("incident_investigator", level="ERROR") as captured:
                response = self.client.post("/api/investigate/INC-001")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["detail"], "Internal server error")
        self.assertEqual(
            response.headers["X-Request-ID"],
            response.json()["request_id"],
        )
        self.assertNotIn(private_value, "\n".join(captured.output))

    def test_production_configuration_rejects_missing_or_short_tokens(self):
        with patch.dict(os.environ, {"APP_ENV": "production"}, clear=True):
            with self.assertRaisesRegex(ValueError, "required in production"):
                validate_environment()
        with patch.dict(
            os.environ,
            {"APP_ENV": "production", "AI_INVESTIGATOR_API_TOKEN": "short"},
            clear=True,
        ):
            with self.assertRaisesRegex(ValueError, "32 to 4096 characters"):
                validate_environment()
        with patch.dict(
            os.environ,
            {
                "APP_ENV": "production",
                "AI_INVESTIGATOR_API_TOKEN": "t" * 40,
                "CORS_ALLOWED_ORIGINS": "http://console.example.test",
            },
            clear=True,
        ):
            with self.assertRaisesRegex(ValueError, "must use HTTPS"):
                validate_environment()
        with patch.dict(os.environ, {"APP_ENV": "production"}, clear=True):
            with self.assertRaisesRegex(ValueError, "required in production"):
                with TestClient(app):
                    pass

    def test_cors_configuration_requires_exact_origins(self):
        with patch.dict(
            os.environ,
            {"CORS_ALLOWED_ORIGINS": "https://console.example.test, https://ops.example.test"},
            clear=True,
        ):
            self.assertEqual(
                get_allowed_origins(),
                ["https://console.example.test", "https://ops.example.test"],
            )
        with patch.dict(os.environ, {"CORS_ALLOWED_ORIGINS": "*"}, clear=True):
            with self.assertRaisesRegex(ValueError, "wildcard"):
                get_allowed_origins()

    def test_health_probes_are_generic_and_operational_metrics_are_aggregate(self):
        self.assertEqual(self.client.get("/api/healthz").json(), {"status": "ok"})
        self.assertEqual(self.client.get("/api/readyz").json(), {"status": "ready"})

        metrics = self.client.get("/api/ops/metrics").json()
        self.assertIn("request_latency_avg_ms", metrics)
        self.assertIn("investigation_duration_avg_ms", metrics)
        self.assertIn("tool_failure_count", metrics)
        self.assertNotIn("INC-001", str(metrics))

    def test_rate_limiter_returns_429_and_can_be_reconfigured(self):
        original_limit = request_rate_limiter.limit
        try:
            request_rate_limiter._requests.clear()
            request_rate_limiter.limit = 1
            self.assertEqual(self.client.get("/api/stats").status_code, 200)
            limited = self.client.get("/api/stats")
            self.assertEqual(limited.status_code, 429)
            self.assertEqual(limited.headers["Retry-After"], "60")
        finally:
            request_rate_limiter.limit = original_limit
            request_rate_limiter._requests.clear()

    def test_benchmark_export_does_not_change_the_checked_in_snapshot(self):
        snapshot = Path("benchmark_results.json")
        original = snapshot.read_bytes()
        response = self.client.get("/api/benchmark/export")
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment;", response.headers["content-disposition"])
        self.assertEqual(snapshot.read_bytes(), original)

    def test_failed_tool_calls_are_counted_and_still_raise(self):
        before = get_tool_failure_count()
        with self.assertRaisesRegex(ValueError, "not found"):
            tools.query_logs_tool("NO-SUCH")
        self.assertEqual(get_tool_failure_count(), before + 1)

    def test_rate_limit_environment_values_are_validated(self):
        with patch.dict(
            os.environ,
            {
                "RATE_LIMIT_REQUESTS_PER_MINUTE": "25",
                "RATE_LIMIT_WINDOW_SECONDS": "30",
            },
            clear=True,
        ):
            self.assertEqual(get_rate_limit(), (25, 30))
        with patch.dict(
            os.environ,
            {"RATE_LIMIT_REQUESTS_PER_MINUTE": "0"},
            clear=True,
        ):
            with self.assertRaisesRegex(ValueError, "outside the supported bounds"):
                get_rate_limit()


if __name__ == "__main__":
    unittest.main()
