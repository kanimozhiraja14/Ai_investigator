"""
Benchmark evaluator comparing AI Incident Investigator against Keyword-Search Baseline.
"""

from typing import List, Dict, Any
from .models import BenchmarkReport, BenchmarkComparison
from .telemetry import get_all_incidents
from .investigator import investigator
from .baseline import baseline

def _evaluate_correctness(diagnosis: str, ground_truth: str, key_signals: List[str]) -> bool:
    """
    Check if the diagnosis correctly captures the underlying root cause and essential causal signals.
    """
    diag_lower = diagnosis.lower()
    gt_lower = ground_truth.lower()
    
    # Check key root-cause concepts
    matched_signals = 0
    for signal in key_signals:
        # Extract alphanumeric words > 3 chars
        words = [w for w in "".join(c if c.isalnum() else " " for c in signal.lower()).split() if len(w) > 3 and not w.startswith("http")]
        if any(w in diag_lower for w in words):
            matched_signals += 1

    # Extract major terms from ground truth
    gt_words = [w for w in "".join(c if c.isalnum() else " " for c in gt_lower).split() if len(w) > 4]
    gt_matches = sum(1 for w in gt_words if w in diag_lower)
    gt_ratio = (gt_matches / len(gt_words)) if gt_words else 0

    return matched_signals >= 1 and gt_ratio >= 0.25


def run_benchmark() -> BenchmarkReport:
    incidents = get_all_incidents()
    comparisons: List[BenchmarkComparison] = []

    ai_correct_count = 0
    base_correct_count = 0
    ai_total_time = 0.0
    base_total_time = 0.0
    ai_unsupported_total = 0
    base_unsupported_total = 0

    for inc in incidents:
        # Run AI Investigator
        ai_res = investigator.investigate(inc.id)
        ai_correct = _evaluate_correctness(ai_res.root_cause_diagnosis, inc.ground_truth_cause, inc.key_signals)
        if ai_correct:
            ai_correct_count += 1
        ai_total_time += ai_res.duration_seconds
        ai_unsupported_total += len(ai_res.unsupported_claims)

        # Run Baseline
        base_res = baseline.investigate(inc.id)
        base_correct = _evaluate_correctness(
            base_res.root_cause_diagnosis,
            inc.ground_truth_cause,
            inc.key_signals
        )

        if base_correct:
            base_correct_count += 1
        base_total_time += base_res.duration_seconds
        base_unsupported_total += len(base_res.unsupported_claims)

        comparisons.append(
            BenchmarkComparison(
                incident_id=inc.id,
                incident_title=inc.title,
                ground_truth=inc.ground_truth_cause,
                category=inc.ground_truth_category,
                investigator_diagnosis=ai_res.root_cause_diagnosis,
                investigator_correct=ai_correct,
                investigator_time_sec=ai_res.duration_seconds,
                investigator_evidence_count=len(ai_res.evidence_chain),
                investigator_unsupported_count=len(ai_res.unsupported_claims),
                baseline_diagnosis=base_res.root_cause_diagnosis,
                baseline_correct=base_correct,
                baseline_time_sec=base_res.duration_seconds,
                baseline_evidence_count=len(base_res.evidence_chain),
                baseline_unsupported_count=len(base_res.unsupported_claims)
            )
        )

    n = len(incidents)
    report = BenchmarkReport(
        total_incidents=n,
        investigator_accuracy=round((ai_correct_count / n) * 100, 1),
        baseline_accuracy=round((base_correct_count / n) * 100, 1),
        investigator_avg_time_sec=round(ai_total_time / n, 4),
        baseline_avg_time_sec=round(base_total_time / n, 4),
        investigator_unsupported_rate=round((ai_unsupported_total / n), 2),
        baseline_unsupported_rate=round((base_unsupported_total / n), 2),
        comparisons=comparisons
    )

    return report


class BenchmarkEngine:
    """Enterprise benchmark runner class providing OOP and functional invocation."""

    @staticmethod
    def compare_single_incident(incident_id: str) -> BenchmarkComparison:
        from .telemetry import get_incident
        inc = get_incident(incident_id)
        if not inc:
            raise ValueError(f"Incident {incident_id} not found")

        ai_res = investigator.investigate(inc.id)
        base_res = baseline.investigate(inc.id)

        ai_correct = _evaluate_correctness(ai_res.root_cause_diagnosis, inc.ground_truth_cause, inc.key_signals)
        base_correct = _evaluate_correctness(base_res.root_cause_diagnosis, inc.ground_truth_cause, inc.key_signals)

        return BenchmarkComparison(
            incident_id=inc.id,
            incident_title=inc.title,
            ground_truth=inc.ground_truth_cause,
            category=inc.ground_truth_category,
            investigator_diagnosis=ai_res.root_cause_diagnosis,
            investigator_correct=ai_correct,
            investigator_time_sec=ai_res.duration_seconds,
            investigator_evidence_count=len(ai_res.evidence_chain),
            investigator_unsupported_count=len(ai_res.unsupported_claims),
            baseline_diagnosis=base_res.root_cause_diagnosis,
            baseline_correct=base_correct,
            baseline_time_sec=base_res.duration_seconds,
            baseline_evidence_count=len(base_res.evidence_chain),
            baseline_unsupported_count=len(base_res.unsupported_claims)
        )

    @staticmethod
    def run_full_benchmark() -> BenchmarkReport:
        return run_benchmark()


benchmark_engine = BenchmarkEngine()
