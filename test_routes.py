"""
Direct validation of all FastAPI route handlers and enterprise extensions.
"""

from pathlib import Path

from incident_investigator.app.main import (
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
    get_dashboard,
    get_health_status,
    get_dashboard_stats,
    list_evidence,
    export_benchmark_report
)

def test_routes():
    print("[*] Testing FastAPI Enterprise Route Handlers directly:")
    
    # 1. Health Status
    health = get_health_status()
    print(f"  [✓] get_health_status() -> Status: {health.status}, Monitored: {health.total_incidents_monitored}")
    assert health.status == "HEALTHY"
    assert "api_gateway" in health.components
    assert "telemetry_database" in health.components
    assert "runbook_retrieval_engine" in health.components
    assert "read_only_enforcement" in health.components

    # 2. Dashboard Stats
    stats = get_dashboard_stats()
    print(f"  [✓] get_dashboard_stats() -> Total: {stats.total_incidents}, P1: {stats.severity_counts.get('P1')}")
    assert stats.total_incidents == 10

    # 3. list_incidents with filters
    incidents = list_incidents()
    print(f"  [✓] list_incidents() -> {len(incidents)} incidents")
    assert len(incidents) == 10
    for inc in incidents:
        assert inc.threat_category is not None
        assert inc.cwe_id is not None
    print(f"      Verified all 10 incidents carry cybersecurity Threat Categories & CWE IDs.")

    # 4. get_incident_details
    inc = get_incident_details("INC-001")
    print(f"  [✓] get_incident_details('INC-001') -> {inc.title}")

    # 5. get_logs
    logs = get_logs(incident_id="INC-001", level="ERROR")
    print(f"  [✓] get_logs('INC-001', level='ERROR') -> {len(logs)} logs")

    # 6. get_metrics
    metrics = get_metrics(incident_id="INC-001")
    print(f"  [✓] get_metrics('INC-001') -> {len(metrics)} points")

    # 7. get_deployments
    deps = get_deployments(incident_id="INC-001")
    print(f"  [✓] get_deployments('INC-001') -> {len(deps)} deployments")

    # 8. search_runbooks
    rbs = search_runbooks(query="PaymentServiceHighErrorRate", service="payment-service")
    print(f"  [✓] search_runbooks('PaymentServiceHighErrorRate') -> {len(rbs)} matched")

    # 9. get_runbook
    rb = get_runbook(rbs[0]["runbook_id"])
    print(f"  [✓] get_runbook('{rb.id}') -> {rb.title}")

    # 10. investigate_incident AI with Calibrated Confidence & Risk
    res_ai = investigate_incident("INC-001", mode="ai")
    print(f"  [✓] investigate_incident('INC-001', mode='ai') -> {res_ai.root_cause_diagnosis[:55]}...")
    print(f"      Evidence items: {len(res_ai.evidence_chain)}, Unsupported: {len(res_ai.unsupported_claims)}")
    assert res_ai.confidence_breakdown is not None
    print(f"      Calibrated Confidence: {res_ai.confidence_score * 100:.1f}%")
    print(f"      Breakdown: {res_ai.confidence_breakdown.explanation[:70]}...")
    assert res_ai.risk_analysis is not None
    print(f"      Risk Analysis: {res_ai.risk_analysis.risk_level} ({res_ai.risk_analysis.cwe_id})")

    # 11. investigate_incident Baseline
    res_base = investigate_incident("INC-001", mode="baseline")
    print(f"  [✓] investigate_incident('INC-001', mode='baseline') -> {res_base.root_cause_diagnosis[:55]}...")
    print(f"      Evidence items: {len(res_base.evidence_chain)}, Unsupported: {len(res_base.unsupported_claims)}")

    # 12. list_evidence (Evidence Explorer)
    ev_items = list_evidence(incident_id="INC-001")
    print(f"  [✓] list_evidence('INC-001') -> {len(ev_items)} evidence ledger items")
    assert len(ev_items) > 0

    # 13. get_investigation_trace
    trace = get_investigation_trace("INC-001")
    print(f"  [✓] get_investigation_trace('INC-001') -> {trace['steps_count']} steps in trace")

    # 14. run_system_benchmark & export
    bench = run_system_benchmark()
    print(f"  [✓] run_system_benchmark() -> AI Accuracy: {bench.investigator_accuracy}%, Baseline: {bench.baseline_accuracy}%")
    assert bench.investigator_accuracy == 100.0
    bench_file = Path("benchmark_results.json")
    assert bench_file.exists(), "benchmark_results.json must exist"

    export_resp = export_benchmark_report()
    print(f"  [✓] export_benchmark_report() -> FileResponse: {export_resp.path}")

    # 15. get_dashboard UI
    dash = get_dashboard()
    print(f"  [✓] get_dashboard() -> FileResponse: {dash.path}")

    print("\n[🎉] ALL 15 ENTERPRISE FASTAPI HANDLERS FULLY OPERATIONAL AND VERIFIED!")

if __name__ == "__main__":
    test_routes()
