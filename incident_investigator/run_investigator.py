"""
Command-line test runner and benchmark demonstration script.
"""

import sys
import json
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent))

from app.telemetry import get_all_incidents, get_incident
from app.runbook_retriever import retriever
from app.correlation_engine import correlator
from app.tools import tools, ReadOnlyViolationError
from app.investigator import investigator
from app.baseline import baseline
from app.benchmark import run_benchmark


def main():
    print("=" * 80)
    print("AI INCIDENT INVESTIGATOR - VERIFICATION & PROOF SUITE")
    print("=" * 80)

    # 1. Verify Incidents
    incidents = get_all_incidents()
    print(f"\n[1] Verified 10 Injected Production Incidents:")
    for inc in incidents:
        print(f"  • [{inc.id}] {inc.severity} | {inc.service:22} | {inc.title}")
    assert len(incidents) == 10, "Expected 10 incidents"

    # 2. Test Runbook Retrieval
    print(f"\n[2] Testing Runbook Retrieval (BM25):")
    query = "PaymentServiceHighErrorRate 5xx"
    results = retriever.search(query, service="payment-service", top_k=2)
    print(f"  Query: '{query}'")
    for r in results:
        print(f"  -> Matched Runbook: '{r['title']}' (Score: {r['score']}, Service: {r['service']})")
    assert len(results) > 0, "Expected runbook matches"

    # 3. Test Time-Window Correlation Engine
    print(f"\n[3] Testing Time-Window Correlation (INC-001):")
    corr = correlator.correlate("INC-001")
    print(f"  Finding: {corr['causality_finding']}")
    print(f"  Correlated Deployments: {corr['correlated_deployments_count']}")
    print(f"  Error Logs in Window:   {corr['error_logs_count']}")
    print(f"  Metric Anomalies:       {corr['metric_anomalies_count']}")

    # 4. Test Read-Only Mode Enforcement
    print(f"\n[4] Testing Read-Only Investigation Mode (Mutation Blocker):")
    try:
        tools.execute_remediation_action("restart_service", "payment-service")
        print("  ❌ ERROR: Mutation was NOT blocked!")
    except ReadOnlyViolationError as e:
        print(f"  ✅ SUCCESS: Mutation intercepted and blocked as expected:")
        print(f"     \"{e}\"")

    # 5. Complete Investigation Trace (INC-001)
    print(f"\n[5] COMPLETE INVESTIGATION TRACE (INC-001: Payment Service Outage):")
    print("-" * 80)
    res = investigator.investigate("INC-001")
    print(f"Incident:    {res.incident_id} - {res.incident_title}")
    print(f"Mode:        {res.mode}")
    print(f"Duration:    {res.duration_seconds}s | Steps: {res.steps_count}")
    print(f"Confidence:  {res.confidence_score * 100:.1f}%")
    print(f"\nPROPOSED ROOT CAUSE:")
    print(f"  >> {res.root_cause_diagnosis}")
    print(f"\nTEMPORAL CORRELATION:")
    print(f"  >> {res.temporal_correlation_summary}")
    if res.risk_analysis:
        ra = res.risk_analysis
        print(f"\nCYBERSECURITY RISK & THREAT ASSESSMENT:")
        print(f"  >> Risk Level:     {ra.risk_level}")
        print(f"  >> Threat Vector:  {ra.threat_vector}")
        print(f"  >> CWE Mapping:    {ra.cwe_id}")
        print(f"  >> CIA Impact:     {ra.cia_impact}")
        print(f"  >> Blast Radius:   {ra.blast_radius}")
        print(f"  >> Remediation SLA:{ra.remediation_sla}")
        print(f"  >> Advisory:       {ra.security_advisory}")
    print(f"\nUNSUPPORTED CLAIMS AUDIT:")
    if not res.unsupported_claims:
        print("  >> 0 unsupported claims. 100% of claims verified against registered telemetry.")
    else:
        for uc in res.unsupported_claims:
            print(f"  >> WARNING: {uc}")

    print(f"\nEXECUTION TRACE (Step-by-Step):")
    for s in res.trace:
        print(f"  Step {s.step_num} [{s.tool_name}]:")
        print(f"    Thought: {s.thought}")
        print(f"    Args:    {s.tool_args}")
        print(f"    Result:  {s.tool_result_preview}")
        if s.evidence_gathered:
            print(f"    Evidence Captured: {s.evidence_gathered}")
        print()

    print(f"LINKED EVIDENCE ITEMS ({len(res.evidence_chain)} total):")
    for ev in res.evidence_chain[:5]:
        print(f"  • [{ev.id}] {ev.summary}")
    if len(res.evidence_chain) > 5:
        print(f"  ... and {len(res.evidence_chain) - 5} more evidence items.")

    print(f"\nRECOMMENDED RUNBOOK MITIGATIONS:")
    for m in res.mitigation_recommended:
        print(f"  • {m}")
    print("-" * 80)

    # 6. Benchmark Evaluation Proof across all 10 incidents
    print(f"\n[6] BENCHMARK EVALUATION PROOF (AI Investigator vs Keyword Baseline across 10 Incidents):")
    report = run_benchmark()
    print("=" * 80)
    print(f"Metric                        | AI Investigator     | Keyword Baseline")
    print("-" * 80)
    print(f"Root-Cause Accuracy           | {report.investigator_accuracy:6.1f}%             | {report.baseline_accuracy:6.1f}%")
    print(f"Avg Time to Diagnosis         | {report.investigator_avg_time_sec:6.4f}s            | {report.baseline_avg_time_sec:6.4f}s")
    print(f"Unsupported Claims / Incident | {report.investigator_unsupported_rate:6.2f}               | {report.baseline_unsupported_rate:6.2f}")
    print("=" * 80)

    print("\nINCIDENT-BY-INCIDENT COMPARISON MATRIX:")
    print(f"{'ID':<9} | {'Category':<22} | {'AI Result':<11} | {'Baseline':<11} | {'AI Evidence':<11}")
    print("-" * 80)
    for c in report.comparisons:
        ai_tag = "✅ CORRECT" if c.investigator_correct else "❌ WRONG"
        base_tag = "✅ CORRECT" if c.baseline_correct else "❌ WRONG"
        print(f"{c.incident_id:<9} | {c.category:<22} | {ai_tag:<11} | {base_tag:<11} | {c.investigator_evidence_count} items")

    print("\n" + "=" * 80)
    print("ALL TESTS AND PROOF COMPLETE.")
    print("=" * 80)


if __name__ == "__main__":
    main()
