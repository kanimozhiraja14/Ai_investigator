import unittest

from fastapi.testclient import TestClient

from incident_investigator.app.main import app


class TestHTTPRoutes(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_dashboard_static_files_and_api_docs(self):
        for path in ("/", "/static/app.js", "/static/style.css", "/docs", "/redoc", "/openapi.json"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

        schema = self.client.get("/openapi.json").json()
        self.assertIn("/api/investigate/{incident_id}", schema["paths"])
        self.assertIn("BearerAuth", schema["components"]["securitySchemes"])
        self.assertEqual(
            schema["paths"]["/api/incidents"]["get"]["security"],
            [{"BearerAuth": []}],
        )

    def test_read_routes_and_response_shapes(self):
        cases = {
            "/api/health": "status",
            "/api/stats": "total_incidents",
            "/api/incidents": None,
            "/api/incidents/INC-001": "id",
            "/api/evidence?incident_id=INC-001": None,
            "/api/logs?incident_id=INC-001": None,
            "/api/metrics?incident_id=INC-001": None,
            "/api/deployments?incident_id=INC-001": None,
            "/api/runbooks?query=connection%20pool": None,
            "/api/runbooks/db_connection_pool": "id",
            "/api/trace/INC-001": "incident_id",
        }
        for path, required_key in cases.items():
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                if required_key:
                    self.assertIn(required_key, response.json())

    def test_unknown_incidents_return_404_and_correlation_evidence_is_filterable(self):
        for path in (
            "/api/incidents/NO-SUCH",
            "/api/evidence?incident_id=NO-SUCH",
            "/api/logs?incident_id=NO-SUCH",
            "/api/metrics?incident_id=NO-SUCH",
            "/api/deployments?incident_id=NO-SUCH",
            "/api/trace/NO-SUCH",
        ):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)

        self.assertEqual(self.client.post("/api/investigate/NO-SUCH").status_code, 404)
        self.assertEqual(self.client.get("/api/runbooks/not-a-runbook").status_code, 404)
        correlation_evidence = self.client.get(
            "/api/evidence?incident_id=INC-001&source_type=CORRELATION"
        )
        self.assertEqual(correlation_evidence.status_code, 200)
        self.assertEqual(len(correlation_evidence.json()), 1)
        self.assertEqual(correlation_evidence.json()[0]["source_type"], "CORRELATION")

    def test_required_parameters_and_query_validation(self):
        self.assertEqual(self.client.get("/api/logs").status_code, 422)
        self.assertEqual(self.client.get("/api/metrics").status_code, 422)
        self.assertEqual(self.client.get("/api/deployments").status_code, 422)
        self.assertEqual(self.client.get("/api/runbooks").status_code, 422)
        self.assertEqual(self.client.get("/api/logs?incident_id=INC-001&limit=0").status_code, 422)
        self.assertEqual(
            self.client.post("/api/investigate/INC-001?mode=invalid").status_code,
            422,
        )
        self.assertEqual(self.client.get("/api/investigate/INC-001").status_code, 405)
        self.assertEqual(self.client.post("/api/stats").status_code, 405)

    def test_cors_rejects_unconfigured_origins_and_credentials(self):
        response = self.client.options(
            "/api/incidents",
            headers={
                "Origin": "https://example.test",
                "Access-Control-Request-Method": "GET",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("access-control-allow-origin", response.headers)
        self.assertNotIn("access-control-allow-credentials", response.headers)

    def test_investigation_modes_and_benchmark_endpoints(self):
        for mode in ("ai", "baseline"):
            with self.subTest(mode=mode):
                response = self.client.post(f"/api/investigate/INC-001?mode={mode}")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["incident_id"], "INC-001")
                self.assertTrue(response.json()["evidence_chain"])

        benchmark = self.client.get("/api/benchmark")
        self.assertEqual(benchmark.status_code, 200)
        self.assertEqual(benchmark.json()["total_incidents"], 10)
        self.assertEqual(len(benchmark.json()["comparisons"]), 10)

        export = self.client.get("/api/benchmark/export")
        self.assertEqual(export.status_code, 200)
        self.assertIn("application/json", export.headers["content-type"])


if __name__ == "__main__":
    unittest.main()
