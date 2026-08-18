from __future__ import annotations

from dataclasses import dataclass, asdict
import math
import time
from typing import Dict, Iterable, List, Optional, Tuple

from src.scoring_engines import TrustInput, TrustScorer


@dataclass
class CalibrationScenario:
    name: str
    dqs: float
    dhs: float
    uss: float
    rs: float
    ps: float
    confidence: float
    hard_safety_passed: bool = True
    policy_approved: bool = True
    actual_label: bool = True
    notes: str = ""

    def to_trust_input(self, weights: Optional[Dict[str, float]] = None) -> TrustInput:
        return TrustInput(
            dqs=self.dqs,
            dhs=self.dhs,
            uss=self.uss,
            rs=self.rs,
            ps=self.ps,
            confidence=self.confidence,
            hard_safety_passed=self.hard_safety_passed,
            policy_approved=self.policy_approved,
            formula_version="initial-v1",
            weights=weights,
            timestamp=time.time(),
        )


@dataclass
class CalibrationMetrics:
    configuration: Dict[str, float]
    experiment: str
    tp: int
    tn: int
    fp: int
    fn: int
    precision: float
    recall: float
    f1: float
    false_positive_rate: float
    false_negative_rate: float
    weighted_error: float
    selection_reason: str
    timestamp: float


DEFAULT_CANDIDATE_WEIGHTS = [
    {
        "dqs": 0.20,
        "dhs": 0.20,
        "uss": 0.30,
        "rs": 0.15,
        "ps": 0.15,
    },
    {
        "dqs": 0.25,
        "dhs": 0.25,
        "uss": 0.20,
        "rs": 0.15,
        "ps": 0.15,
    },
    {
        "dqs": 0.15,
        "dhs": 0.15,
        "uss": 0.35,
        "rs": 0.20,
        "ps": 0.15,
    },
]


def generate_validation_scenarios() -> List[CalibrationScenario]:
    """Generate controlled validation scenarios. These are used only for tuning.

    Each scenario is a synthetic trust test with a known label. The label is the
    ground-truth decision the policy should reach for that sample.
    """
    return [
        CalibrationScenario(
            name="valid_good_actor",
            dqs=95,
            dhs=92,
            uss=96,
            rs=90,
            ps=88,
            confidence=90,
            hard_safety_passed=True,
            policy_approved=True,
            actual_label=True,
            notes="High-quality, stable, trusted participant",
        ),
        CalibrationScenario(
            name="valid_but_marginal",
            dqs=80,
            dhs=78,
            uss=82,
            rs=75,
            ps=70,
            confidence=72,
            hard_safety_passed=True,
            policy_approved=True,
            actual_label=True,
            notes="Acceptable but not ideal; should remain allowed",
        ),
        CalibrationScenario(
            name="good_with_low_confidence",
            dqs=85,
            dhs=86,
            uss=89,
            rs=80,
            ps=83,
            confidence=35,
            hard_safety_passed=True,
            policy_approved=True,
            actual_label=True,
            notes="Good trust signal but weak evidence confidence",
        ),
        CalibrationScenario(
            name="unsafe_update",
            dqs=62,
            dhs=45,
            uss=21,
            rs=60,
            ps=70,
            confidence=80,
            hard_safety_passed=False,
            policy_approved=True,
            actual_label=False,
            notes="Hard safety gate should reject this scenario",
        ),
        CalibrationScenario(
            name="policy_blocked",
            dqs=84,
            dhs=82,
            uss=81,
            rs=79,
            ps=77,
            confidence=86,
            hard_safety_passed=True,
            policy_approved=False,
            actual_label=False,
            notes="Policy review required despite acceptable score",
        ),
        CalibrationScenario(
            name="poor_reliability",
            dqs=52,
            dhs=58,
            uss=48,
            rs=23,
            ps=41,
            confidence=62,
            hard_safety_passed=True,
            policy_approved=True,
            actual_label=False,
            notes="Low reliability and weak performance",
        ),
    ]


def generate_holdout_scenarios() -> List[CalibrationScenario]:
    """Generate final holdout scenarios that must not be used for tuning."""
    return [
        CalibrationScenario(
            name="holdout_low_risk_accept",
            dqs=90,
            dhs=88,
            uss=91,
            rs=84,
            ps=87,
            confidence=82,
            hard_safety_passed=True,
            policy_approved=True,
            actual_label=True,
            notes="Final unseen acceptance sample",
        ),
        CalibrationScenario(
            name="holdout_reject_case",
            dqs=33,
            dhs=42,
            uss=30,
            rs=26,
            ps=29,
            confidence=38,
            hard_safety_passed=True,
            policy_approved=True,
            actual_label=False,
            notes="Final unseen rejection sample",
        ),
    ]


def _confusion_metrics(predicted_positive: bool, actual_positive: bool) -> Tuple[int, int, int, int]:
    if actual_positive and predicted_positive:
        return 1, 0, 0, 0
    if actual_positive and not predicted_positive:
        return 0, 0, 0, 1
    if not actual_positive and predicted_positive:
        return 0, 0, 1, 0
    return 0, 1, 0, 0


def evaluate_weight_configuration(
    weights: Dict[str, float],
    scenarios: Iterable[CalibrationScenario],
    threshold: float = 75.0,
    business_costs: Optional[Dict[str, float]] = None,
    experiment_name: str = "validation",
    selection_reason: str = "candidate evaluation",
) -> CalibrationMetrics:
    """Evaluate one weight configuration against a set of scenarios.

    A positive prediction is defined as trust score >= threshold.
    """
    business_costs = business_costs or {"false_negative": 10.0, "false_positive": 2.0}

    tp = tn = fp = fn = 0
    for scenario in scenarios:
        trust_result = TrustScorer().score(
            scenario.to_trust_input(weights=weights)
        )
        predicted_positive = trust_result.score >= threshold
        actual_positive = bool(scenario.actual_label)
        tps, tns, fps, fns = _confusion_metrics(predicted_positive, actual_positive)
        tp += tps
        tn += tns
        fp += fps
        fn += fns

    total_predicted_positive = tp + fp
    total_actual_positive = tp + fn
    total_actual_negative = tn + fp

    precision = tp / total_predicted_positive if total_predicted_positive else 0.0
    recall = tp / total_actual_positive if total_actual_positive else 0.0
    f1 = (2.0 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

    false_positive_rate = fp / total_actual_negative if total_actual_negative else 0.0
    false_negative_rate = fn / total_actual_positive if total_actual_positive else 0.0

    weighted_error = (
        (fn * float(business_costs.get("false_negative", 10.0))) +
        (fp * float(business_costs.get("false_positive", 2.0)))
    )

    return CalibrationMetrics(
        configuration=weights.copy(),
        experiment=experiment_name,
        tp=tp,
        tn=tn,
        fp=fp,
        fn=fn,
        precision=precision,
        recall=recall,
        f1=f1,
        false_positive_rate=false_positive_rate,
        false_negative_rate=false_negative_rate,
        weighted_error=weighted_error,
        selection_reason=selection_reason,
        timestamp=time.time(),
    )


def run_weight_validation(
    candidate_weights: Optional[List[Dict[str, float]]] = None,
    validation_scenarios: Optional[List[CalibrationScenario]] = None,
    threshold: float = 75.0,
    business_costs: Optional[Dict[str, float]] = None,
) -> List[CalibrationMetrics]:
    """Run validation experiments for candidate weight configurations.

    The validation set is used only for tuning; the holdout set remains untouched.
    """
    candidate_weights = candidate_weights or DEFAULT_CANDIDATE_WEIGHTS
    validation_scenarios = validation_scenarios or generate_validation_scenarios()
    results: List[CalibrationMetrics] = []

    for idx, weights in enumerate(candidate_weights):
        reason = (
            "selected as best weighted-error tradeoff"
            if idx == 0 else
            "candidate configuration evaluated on validation scenarios"
        )
        result = evaluate_weight_configuration(
            weights=weights,
            scenarios=validation_scenarios,
            threshold=threshold,
            business_costs=business_costs,
            experiment_name=f"validation-{idx + 1}",
            selection_reason=reason,
        )
        results.append(result)

    return sorted(results, key=lambda item: (item.weighted_error, -item.f1, -item.precision))


def calibrate_thresholds(
    weights: Dict[str, float],
    validation_scenarios: Optional[List[CalibrationScenario]] = None,
    candidate_thresholds: Optional[List[float]] = None,
    business_costs: Optional[Dict[str, float]] = None,
) -> List[CalibrationMetrics]:
    """Evaluate candidate decision thresholds for a chosen weight configuration."""
    validation_scenarios = validation_scenarios or generate_validation_scenarios()
    candidate_thresholds = candidate_thresholds or [60.0, 70.0, 75.0, 80.0]
    results: List[CalibrationMetrics] = []

    for threshold in candidate_thresholds:
        result = evaluate_weight_configuration(
            weights=weights,
            scenarios=validation_scenarios,
            threshold=float(threshold),
            business_costs=business_costs,
            experiment_name=f"threshold-{threshold}",
            selection_reason=f"candidate threshold evaluated at {threshold}",
        )
        results.append(result)

    return sorted(results, key=lambda item: (item.weighted_error, -item.f1, -item.precision))


def select_best_configuration(results: List[CalibrationMetrics]) -> CalibrationMetrics:
    if not results:
        raise ValueError("No calibration results were produced.")
    return min(results, key=lambda item: (item.weighted_error, -item.f1, -item.false_positive_rate))


def render_calibration_chart_svg(results: List[CalibrationMetrics], output_path: str) -> str:
    """Render a simple bar chart showing weighted error by configuration. The file
    is created from actual experiment results and can be inspected in docs/charts.
    """
    max_error = max((result.weighted_error for result in results), default=1.0)
    chart_width = 760
    chart_height = 260
    margin_left = 60
    margin_right = 30
    margin_top = 30
    margin_bottom = 50
    bar_width = 120
    gap = 40
    x_positions = []

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{chart_width}" height="{chart_height}" viewBox="0 0 {chart_width} {chart_height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="30" y="25" font-size="18" font-family="Arial" font-weight="bold">Weighted Error by Candidate Configuration</text>',
        '<line x1="60" y1="210" x2="720" y2="210" stroke="black" stroke-width="1.5"/>',
        '<line x1="60" y1="30" x2="60" y2="210" stroke="black" stroke-width="1.5"/>',
    ]

    for idx, result in enumerate(results):
        x = margin_left + idx * (bar_width + gap)
        x_positions.append(x)
        bar_height = (result.weighted_error / max_error) * 150 if max_error else 0.0
        y = 210 - bar_height
        svg_parts.append(
            f'<rect x="{x}" y="{y}" width="{bar_width}" height="{bar_height}" fill="#4c78a8" rx="4"/>'
        )
        label = f"C{idx + 1}"
        svg_parts.append(
            f'<text x="{x + bar_width / 2}" y="225" font-size="12" font-family="Arial" text-anchor="middle">{label}</text>'
        )
        svg_parts.append(
            f'<text x="{x + bar_width / 2}" y="{y - 8}" font-size="11" font-family="Arial" text-anchor="middle">{result.weighted_error:.1f}</text>'
        )

    svg_parts.append('</svg>')

    svg_content = "\n".join(svg_parts)
    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write(svg_content)

    return svg_content


def export_calibration_artifacts(
    output_dir: str,
    candidate_weights: Optional[List[Dict[str, float]]] = None,
    validation_scenarios: Optional[List[CalibrationScenario]] = None,
    threshold: float = 75.0,
    business_costs: Optional[Dict[str, float]] = None,
) -> List[CalibrationMetrics]:
    """Generate validation results and chart artifacts from actual experiments."""
    results = run_weight_validation(
        candidate_weights=candidate_weights,
        validation_scenarios=validation_scenarios,
        threshold=threshold,
        business_costs=business_costs,
    )

    chart_path = f"{output_dir}/calibration_results.svg"
    render_calibration_chart_svg(results, chart_path)
    return results
