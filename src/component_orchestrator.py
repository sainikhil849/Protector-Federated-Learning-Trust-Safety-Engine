from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np

from src.dataset_loader import DatasetData
from src.participant_simulator import ParticipantData
from src.scoring_engines import (
    DataQualityInput,
    DataQualityOutput,
    DataQualityScorer,
    DriftHealthInput,
    DriftHealthOutput,
    DriftHealthScorer,
)


@dataclass
class ComponentScoreResult:
    """Standardized result object for a component score."""
    component_name: str
    score: float
    status: str
    details: str
    input_summary: Dict[str, Any]


def _score_status(score: float) -> str:
    if score >= 80:
        return "healthy"
    if score >= 60:
        return "warning"
    if score >= 40:
        return "degraded"
    return "critical"


def _summarize_data_quality_input(participant: ParticipantData) -> Dict[str, Any]:
    row_count = int(participant.row_count)
    feature_count = int(participant.X.shape[1]) if getattr(participant.X, "ndim", 1) > 1 else 0
    missing_values = int(np.isnan(participant.X).sum()) if participant.X.size > 0 else 0
    unique_labels = np.unique(participant.y).tolist() if participant.y.size > 0 else []
    return {
        "rows": row_count,
        "feature_count": feature_count,
        "missing_values": missing_values,
        "label_values": [int(v) for v in unique_labels],
        "label_count": int(len(unique_labels)),
    }


def _summarize_drift_input(current_features: np.ndarray, baseline_features: np.ndarray) -> Dict[str, Any]:
    return {
        "current_rows": int(current_features.shape[0]) if current_features is not None and getattr(current_features, "ndim", 1) > 1 else 0,
        "baseline_rows": int(baseline_features.shape[0]) if baseline_features is not None and getattr(baseline_features, "ndim", 1) > 1 else 0,
        "current_features": int(current_features.shape[1]) if current_features is not None and getattr(current_features, "ndim", 1) > 1 else 0,
        "baseline_features": int(baseline_features.shape[1]) if baseline_features is not None and getattr(baseline_features, "ndim", 1) > 1 else 0,
    }


def score_data_quality(participant: ParticipantData, *, feature_min: float = 0.1, feature_max: float = 170000, outlier_threshold: float = 3.0) -> ComponentScoreResult:
    """Map a participant dataset to the existing DataQualityInput and score it."""
    if participant.X.size == 0 or len(participant.y) == 0:
        return ComponentScoreResult(
            component_name="data_quality",
            score=0.0,
            status="critical",
            details="empty participant data",
            input_summary={"rows": 0, "feature_count": 0, "missing_values": 0, "label_values": [], "label_count": 0},
        )

    data = DataQualityInput(
        labels=participant.y.astype(int).tolist(),
        features=np.asarray(participant.X, dtype=float),
        feature_min=feature_min,
        feature_max=feature_max,
        outlier_threshold=outlier_threshold,
        sparse_format=True,
    )

    scorer = DataQualityScorer(
        feature_min=feature_min,
        feature_max=feature_max,
        outlier_threshold=outlier_threshold,
    )
    output: DataQualityOutput = scorer.score(data)

    summary = _summarize_data_quality_input(participant)
    summary["feature_min"] = feature_min
    summary["feature_max"] = feature_max
    summary["outlier_threshold"] = outlier_threshold

    details = (
        f"schema_validity={output.schema_validity:.4f}; completeness={output.completeness:.4f}; "
        f"outlier_rate={output.outlier_rate:.4f}; invalid_features={int(output.invalid_features)}; "
        f"invalid_labels={int(output.invalid_labels)}"
    )

    return ComponentScoreResult(
        component_name="data_quality",
        score=float(output.score),
        status=_score_status(float(output.score)),
        details=details,
        input_summary=summary,
    )


def score_drift_health(
    participant: ParticipantData,
    *,
    baseline_features: np.ndarray,
    num_bins: int = 10,
    epsilon: float = 1e-10,
    feature_min: float = 0.1,
    feature_max: float = 170000,
) -> ComponentScoreResult:
    """Map participant and baseline data to the existing DriftHealthInput and score it."""
    current = np.asarray(participant.X, dtype=float)
    baseline = np.asarray(baseline_features, dtype=float)

    if current.size == 0 or baseline.size == 0:
        return ComponentScoreResult(
            component_name="drift_health",
            score=0.0,
            status="critical",
            details="missing baseline or current feature data",
            input_summary={"current_rows": 0, "baseline_rows": 0, "current_features": 0, "baseline_features": 0},
        )

    data = DriftHealthInput(
        current_features=current,
        baseline_features=baseline,
        num_bins=num_bins,
        epsilon=epsilon,
        feature_min=feature_min,
        feature_max=feature_max,
    )

    scorer = DriftHealthScorer(
        num_bins=num_bins,
        epsilon=epsilon,
        feature_min=feature_min,
        feature_max=feature_max,
    )
    output: DriftHealthOutput = scorer.score(data)

    summary = _summarize_drift_input(current, baseline)
    summary["num_bins"] = num_bins
    summary["drift_threshold"] = 0.25

    details = (
        f"drift_level={output.drift_level}; psi_average={output.psi_average:.4f}; "
        f"drift_count={output.drift_count}; features_with_drift={output.features_with_drift[:10]}"
    )

    return ComponentScoreResult(
        component_name="drift_health",
        score=float(output.score),
        status=_score_status(float(output.score)),
        details=details,
        input_summary=summary,
    )


def score_participant_components(
    participant: ParticipantData,
    *,
    baseline_features: Optional[np.ndarray] = None,
    use_global_baseline: bool = False,
    feature_min: float = 0.1,
    feature_max: float = 170000,
    outlier_threshold: float = 3.0,
) -> List[ComponentScoreResult]:
    """Score the given participant against the real data quality and drift health components."""
    if baseline_features is None:
        baseline_features = participant.X.copy()

    quality_result = score_data_quality(
        participant,
        feature_min=feature_min,
        feature_max=feature_max,
        outlier_threshold=outlier_threshold,
    )
    drift_result = score_drift_health(
        participant,
        baseline_features=baseline_features,
        feature_min=feature_min,
        feature_max=feature_max,
    )

    return [quality_result, drift_result]
