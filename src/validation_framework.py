from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
import time
from typing import Any, Dict, Iterable, List, Optional

from src.scoring_engines import TrustInput, TrustScorer


POSITIVE_DECISIONS = {"ALLOW", "MONITOR", "SAFE"}
NEGATIVE_DECISIONS = {"UNSAFE", "BLOCK", "RESTRICT", "REVIEW", "DEGRADED"}


@dataclass
class GroundTruthScenario:
    scenario_id: str
    name: str
    input_conditions: Dict[str, Any]
    ground_truth: str
    expected_decision: str
    notes: str = ""

    def to_trust_input(self, weights: Optional[Dict[str, float]] = None) -> TrustInput:
        return TrustInput(
            dqs=float(self.input_conditions["dqs"]),
            dhs=float(self.input_conditions["dhs"]),
            uss=float(self.input_conditions["uss"]),
            rs=float(self.input_conditions["rs"]),
            ps=float(self.input_conditions["ps"]),
            confidence=float(self.input_conditions.get("confidence", 80.0)),
            hard_safety_passed=bool(self.input_conditions.get("hard_safety_passed", True)),
            policy_approved=bool(self.input_conditions.get("policy_approved", True)),
            formula_version=self.input_conditions.get("formula_version", "initial-v1"),
            weights=weights,
            timestamp=float(self.input_conditions.get("timestamp", time.time())),
        )


@dataclass
class ExperimentRecord:
    scenario_id: str
    input_conditions: Dict[str, Any]
    ground_truth: str
    trust_score: float
    confidence: float
    hard_safety_result: str
    decision: str
    correct: bool
    expected_decision: str
    predicted_positive: bool
    ground_truth_positive: bool
    timestamp: float = field(default_factory=time.time)


@dataclass
class ValidationSummary:
    tp: int
    tn: int
    fp: int
    fn: int
    precision: float
    recall: float
    f1: float
    specificity: float
    balanced_accuracy: float
    fpr: float
    fnr: float
    total_experiments: int
    correct_count: int
    timestamp: float = field(default_factory=time.time)


def normalize_decision(value: str) -> str:
    normalized = str(value).strip().upper()
    if normalized == "ALLOW":
        return "ALLOW"
    if normalized == "MONITOR":
        return "MONITOR"
    if normalized == "REVIEW":
        return "REVIEW"
    if normalized == "BLOCK":
        return "BLOCK"
    if normalized in {"SAFE", "PASS"}:
        return "ALLOW"
    if normalized in {"UNSAFE", "FAIL"}:
        return "BLOCK"
    if normalized == "RESTRICT":
        return "RESTRICT"
    if normalized == "DEGRADED":
        return "RESTRICT"
    return normalized


def is_positive_decision(value: str) -> bool:
    return normalize_decision(value) in POSITIVE_DECISIONS


def generate_ground_truth_scenarios() -> List[GroundTruthScenario]:
    """Create independent ground-truth validation scenarios.

    These scenarios are defined independently from the Trust Score implementation.
    They represent expected operational outcomes based on external rules and
    policy assumptions rather than the model's own decisions.
    """
    return [
        GroundTruthScenario(
            scenario_id="V-001",
            name="healthy_participant",
            input_conditions={
                "dqs": 95,
                "dhs": 92,
                "uss": 96,
                "rs": 90,
                "ps": 88,
                "confidence": 90,
                "hard_safety_passed": True,
                "policy_approved": True,
            },
            ground_truth="SAFE",
            expected_decision="ALLOW",
            notes="Healthy participant with robust trust profile",
        ),
        GroundTruthScenario(
            scenario_id="V-002",
            name="nan_update",
            input_conditions={
                "dqs": 40,
                "dhs": 45,
                "uss": 0,
                "rs": 62,
                "ps": 70,
                "confidence": 58,
                "hard_safety_passed": False,
                "policy_approved": True,
            },
            ground_truth="UNSAFE",
            expected_decision="BLOCK",
            notes="NaN or invalid update must be rejected.",
        ),
        GroundTruthScenario(
            scenario_id="V-003",
            name="infinity_update",
            input_conditions={
                "dqs": 35,
                "dhs": 30,
                "uss": 0,
                "rs": 40,
                "ps": 55,
                "confidence": 50,
                "hard_safety_passed": False,
                "policy_approved": True,
            },
            ground_truth="UNSAFE",
            expected_decision="BLOCK",
            notes="Infinity indicates invalid model state.",
        ),
        GroundTruthScenario(
            scenario_id="V-004",
            name="wrong_shape",
            input_conditions={
                "dqs": 58,
                "dhs": 66,
                "uss": 10,
                "rs": 50,
                "ps": 60,
                "confidence": 70,
                "hard_safety_passed": False,
                "policy_approved": True,
            },
            ground_truth="UNSAFE",
            expected_decision="BLOCK",
            notes="Wrong shape is a hard safety failure.",
        ),
        GroundTruthScenario(
            scenario_id="V-005",
            name="stale_update",
            input_conditions={
                "dqs": 70,
                "dhs": 72,
                "uss": 64,
                "rs": 45,
                "ps": 62,
                "confidence": 68,
                "hard_safety_passed": True,
                "policy_approved": True,
            },
            ground_truth="RESTRICT",
            expected_decision="RESTRICT",
            notes="Stale update should be restricted, not fully allowed.",
        ),
        GroundTruthScenario(
            scenario_id="V-006",
            name="new_participant_little_evidence",
            input_conditions={
                "dqs": 70,
                "dhs": 68,
                "uss": 72,
                "rs": 55,
                "ps": 63,
                "confidence": 30,
                "hard_safety_passed": True,
                "policy_approved": True,
            },
            ground_truth="REVIEW",
            expected_decision="REVIEW",
            notes="New participant with limited evidence requires review.",
        ),
        GroundTruthScenario(
            scenario_id="V-007",
            name="severe_controlled_corruption",
            input_conditions={
                "dqs": 20,
                "dhs": 25,
                "uss": 12,
                "rs": 40,
                "ps": 30,
                "confidence": 40,
                "hard_safety_passed": True,
                "policy_approved": True,
            },
            ground_truth="DEGRADED",
            expected_decision="RESTRICT",
            notes="Corruption is controlled but system should degrade behavior.",
        ),
        GroundTruthScenario(
            scenario_id="V-008",
            name="large_abnormal_update",
            input_conditions={
                "dqs": 55,
                "dhs": 50,
                "uss": 35,
                "rs": 52,
                "ps": 45,
                "confidence": 64,
                "hard_safety_passed": True,
                "policy_approved": True,
            },
            ground_truth="SUSPICIOUS",
            expected_decision="RESTRICT",
            notes="Large abnormal update should trigger restricted handling.",
        ),
    ]


def evaluate_experiment(
    scenario: GroundTruthScenario,
    weights: Optional[Dict[str, float]] = None,
) -> ExperimentRecord:
    trust_result = TrustScorer().score(scenario.to_trust_input(weights=weights))
    decision = normalize_decision(trust_result.decision)
    ground_truth_positive = is_positive_decision(scenario.ground_truth)
    predicted_positive = is_positive_decision(decision)
    correct = normalize_decision(scenario.expected_decision) == decision

    return ExperimentRecord(
        scenario_id=scenario.scenario_id,
        input_conditions=scenario.input_conditions,
        ground_truth=scenario.ground_truth,
        trust_score=trust_result.score,
        confidence=trust_result.confidence_level,
        hard_safety_result="PASS" if scenario.input_conditions.get("hard_safety_passed", True) else "FAIL",
        decision=decision,
        correct=correct,
        expected_decision=normalize_decision(scenario.expected_decision),
        predicted_positive=predicted_positive,
        ground_truth_positive=ground_truth_positive,
        timestamp=time.time(),
    )


def calculate_validation_summary(results: Iterable[ExperimentRecord]) -> ValidationSummary:
    results = list(results)
    tp = sum(1 for r in results if r.ground_truth_positive and r.predicted_positive)
    tn = sum(1 for r in results if (not r.ground_truth_positive) and (not r.predicted_positive))
    fp = sum(1 for r in results if (not r.ground_truth_positive) and r.predicted_positive)
    fn = sum(1 for r in results if r.ground_truth_positive and (not r.predicted_positive))

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

    specificity = tn / (tn + fp) if (tn + fp) else 0.0
    balanced_accuracy = (recall + specificity) / 2.0 if (recall + specificity) else 0.0
    fpr = fp / (fp + tn) if (fp + tn) else 0.0
    fnr = fn / (fn + tp) if (fn + tp) else 0.0

    return ValidationSummary(
        tp=tp,
        tn=tn,
        fp=fp,
        fn=fn,
        precision=precision,
        recall=recall,
        f1=f1,
        specificity=specificity,
        balanced_accuracy=balanced_accuracy,
        fpr=fpr,
        fnr=fnr,
        total_experiments=len(results),
        correct_count=sum(1 for r in results if r.correct),
        timestamp=time.time(),
    )


def export_results_to_json(results: Iterable[ExperimentRecord], output_path: str) -> Dict[str, Any]:
    output = {
        "results": [asdict(r) for r in results],
        "summary": calculate_validation_summary(results).__dict__,
    }
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(output, handle, indent=2, sort_keys=True)
    return output


def export_results_to_csv(results: Iterable[ExperimentRecord], output_path: str) -> None:
    rows = [asdict(r) for r in results]
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "scenario_id",
                "input_conditions",
                "ground_truth",
                "trust_score",
                "confidence",
                "hard_safety_result",
                "decision",
                "correct",
                "expected_decision",
                "predicted_positive",
                "ground_truth_positive",
                "timestamp",
            ],
        )
        writer.writeheader()
        for row in rows:
            row["input_conditions"] = json.dumps(row["input_conditions"], sort_keys=True)
            writer.writerow(row)


def run_validation_experiments(
    scenarios: Optional[Iterable[GroundTruthScenario]] = None,
    weights: Optional[Dict[str, float]] = None,
    output_dir: str = "experiments/results",
) -> Dict[str, Any]:
    scenarios = list(scenarios or generate_ground_truth_scenarios())
    records = [evaluate_experiment(scenario, weights=weights) for scenario in scenarios]
    summary = calculate_validation_summary(records)

    export_results_to_json(records, f"{output_dir}/validation_results.json")
    export_results_to_csv(records, f"{output_dir}/validation_results.csv")

    return {
        "records": [asdict(r) for r in records],
        "summary": asdict(summary),
        "output_dir": output_dir,
    }
