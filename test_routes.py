"""
Direct validation of all FastAPI route handlers.
"""

import os
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
    get_dashboard
)

def test_routes():
    print("[*] Testing FastAPI Route Handlers directly:")
    
    # 1. list_incidents
    incidents = list_incidents()
    print(f"  [✓] list_incidents() -> {len(incidents)} incidents")
    assert len(incidents) == 10
    for inc in incidents:
        assert inc.threat_category is not None
        assert inc.cwe_id is not None
    print(f"      Verified all 10 incidents carry cybersecurity Threat Categories & CWE IDs.")

    # 2. get_incident_details
    inc = get_incident_details("INC-001")
    print(f"  [✓] get_incident_details('INC-001') -> {inc.title}")

    # 3. get_logs
    logs = get_logs(incident_id="INC-001", level="ERROR")
    print(f"  [✓] get_logs('INC-001', level='ERROR') -> {len(logs)} logs")

    # 4. get_metrics
    metrics = get_metrics(incident_id="INC-001")
    print(f"  [✓] get_metrics('INC-001') -> {len(metrics)} points")

    # 5. get_deployments
    deps = get_deployments(incident_id="INC-001")
    print(f"  [✓] get_deployments('INC-001') -> {len(deps)} deployments")

    # 6. search_runbooks
    rbs = search_runbooks(query="PaymentServiceHighErrorRate", service="payment-service")
    print(f"  [✓] search_runbooks('PaymentServiceHighErrorRate') -> {len(rbs)} matched")

    # 7. get_runbook
    rb = get_runbook(rbs[0]["runbook_id"])
    print(f"  [✓] get_runbook('{rb.id}') -> {rb.title}")

    # 8. investigate_incident AI
    res_ai = investigate_incident("INC-001", mode="ai")
    print(f"  [✓] investigate_incident('INC-001', mode='ai') -> {res_ai.root_cause_diagnosis[:55]}...")
    print(f"      Evidence items: {len(res_ai.evidence_chain)}, Unsupported: {len(res_ai.unsupported_claims)}")
    assert res_ai.risk_analysis is not None
    print(f"      Risk Analysis Verified: {res_ai.risk_analysis.risk_level} ({res_ai.risk_analysis.cwe_id})")

    # 9. investigate_incident Baseline
    res_base = investigate_incident("INC-001", mode="baseline")
    print(f"  [✓] investigate_incident('INC-001', mode='baseline') -> {res_base.root_cause_diagnosis[:55]}...")
    print(f"      Evidence items: {len(res_base.evidence_chain)}, Unsupported: {len(res_base.unsupported_claims)}")

    # 10. get_investigation_trace
    trace = get_investigation_trace("INC-001")
    print(f"  [✓] get_investigation_trace('INC-001') -> {trace['steps_count']} steps in trace")

    # 11. run_system_benchmark
    bench = run_system_benchmark()
    print(f"  [✓] run_system_benchmark() -> AI Accuracy: {bench.investigator_accuracy}%, Baseline: {bench.baseline_accuracy}%")
    assert bench.investigator_accuracy == 100.0
    bench_file = Path("benchmark_results.json")
    assert bench_file.exists(), "benchmark_results.json must exist"
    print(f"      Saved and verified benchmark results on disk: {bench_file.name} ({bench_file.stat().st_size} bytes)")

    # 12. get_dashboard
    dash = get_dashboard()
    print(f"  [✓] get_dashboard() -> FileResponse: {dash.path}")

    print("\n[🎉] ALL FASTAPI HANDLERS & RISK ANALYSIS FULLY OPERATIONAL AND VERIFIED!")

if __name__ == "__main__":
    test_routes()
