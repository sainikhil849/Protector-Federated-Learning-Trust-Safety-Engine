#!/usr/bin/env python3
"""Run the real CSV-to-trust pipeline end-to-end.

This script intentionally keeps the frozen scoring logic unchanged while wrapping
real dataset loading, participant splitting, model training, and scorer integration
around it.

Important:
- Real data values come from the CSV dataset and all materialized participant data.
- Participant history values are simulated prototype metadata and are clearly labeled
  as such in both console output and exported result files.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

from src.component_orchestrator import score_data_quality, score_drift_health
from src.dataset_loader import load_csv
from src.model_runner import ModelRunner
from src.participant_history import simulate_participant_history
from src.participant_simulator import simulate_participants
from src.scoring_engines import (
    PerformanceScorer,
    ReliabilityScorer,
    TrustInput,
    TrustScorer,
    UpdateSafetyScorer,
)


RESULTS_DIR = Path("experiments/results")
RESULTS_CSV = RESULTS_DIR / "real_data_results.csv"
RESULTS_JSON = RESULTS_DIR / "real_data_results.json"
DEFAULT_MIN_BASELINE_SAMPLES = 12


@dataclass
class BaselineValidationResult:
    """Explicit validation outcome for a drift-estimation baseline."""
    status: str
    message: str
    baseline_size: int = 0
    participant_size: int = 0
    minimum_required: int = 0
    feature_count: int = 0


def validate_reference_baseline(
    current_features: np.ndarray,
    baseline_features: np.ndarray,
    min_baseline_samples: int = DEFAULT_MIN_BASELINE_SAMPLES,
) -> BaselineValidationResult:
    """Validate baseline suitability without modifying the frozen scoring engine."""
    if current_features is None or baseline_features is None:
        return BaselineValidationResult(
            status="ERROR",
            message="Missing current or baseline feature arrays.",
            baseline_size=0,
            participant_size=0,
            minimum_required=min_baseline_samples,
        )

    current_arr = np.asarray(current_features, dtype=float)
    baseline_arr = np.asarray(baseline_features, dtype=float)

    if current_arr.ndim != 2 or baseline_arr.ndim != 2:
        return BaselineValidationResult(
            status="ERROR",
            message="Current and baseline data must both be 2D arrays.",
            baseline_size=int(baseline_arr.size > 0 and baseline_arr.shape[0]),
            participant_size=int(current_arr.size > 0 and current_arr.shape[0]),
            minimum_required=min_baseline_samples,
            feature_count=int(current_arr.shape[1] if current_arr.ndim == 2 else 0),
        )

    if current_arr.shape[0] == 0 or baseline_arr.shape[0] == 0:
        return BaselineValidationResult(
            status="ERROR",
            message="Empty baseline or participant feature matrix detected.",
            baseline_size=int(baseline_arr.shape[0]),
            participant_size=int(current_arr.shape[0]),
            minimum_required=min_baseline_samples,
            feature_count=int(current_arr.shape[1]),
        )

    if current_arr.shape[1] != baseline_arr.shape[1]:
        return BaselineValidationResult(
            status="ERROR",
            message=(
                f"Feature count mismatch: participant has {current_arr.shape[1]} features but "
                f"baseline has {baseline_arr.shape[1]} features."
            ),
            baseline_size=int(baseline_arr.shape[0]),
            participant_size=int(current_arr.shape[0]),
            minimum_required=min_baseline_samples,
            feature_count=int(current_arr.shape[1]),
        )

    if current_arr.shape[0] < 2:
        return BaselineValidationResult(
            status="INSUFFICIENT_DATA",
            message="Participant is too small for a stable PSI comparison.",
            baseline_size=int(baseline_arr.shape[0]),
            participant_size=int(current_arr.shape[0]),
            minimum_required=min_baseline_samples,
            feature_count=int(current_arr.shape[1]),
        )

    if baseline_arr.shape[0] < min_baseline_samples:
        return BaselineValidationResult(
            status="INSUFFICIENT_DATA",
            message=(
                f"Baseline contains {baseline_arr.shape[0]} rows, below the prototype minimum of "
                f"{min_baseline_samples}. INSUFFICIENT DATA FOR RELIABLE DRIFT ESTIMATION."
            ),
            baseline_size=int(baseline_arr.shape[0]),
            participant_size=int(current_arr.shape[0]),
            minimum_required=min_baseline_samples,
            feature_count=int(current_arr.shape[1]),
        )

    if not np.isfinite(current_arr).all() or not np.isfinite(baseline_arr).all():
        return BaselineValidationResult(
            status="ERROR",
            message="Baseline or participant data contains NaN or infinite values.",
            baseline_size=int(baseline_arr.shape[0]),
            participant_size=int(current_arr.shape[0]),
            minimum_required=min_baseline_samples,
            feature_count=int(current_arr.shape[1]),
        )

    constant_columns = np.where(np.all(baseline_arr == baseline_arr[0], axis=0))[0]
    if constant_columns.size > 0:
        return BaselineValidationResult(
            status="WARNING",
            message=(
                f"Baseline contains constant columns that may reduce PSI informativeness: "
                f"{constant_columns.tolist()}."
            ),
            baseline_size=int(baseline_arr.shape[0]),
            participant_size=int(current_arr.shape[0]),
            minimum_required=min_baseline_samples,
            feature_count=int(current_arr.shape[1]),
        )

    return BaselineValidationResult(
        status="VALID",
        message="Baseline is large enough and structurally valid for PSI-based drift estimation.",
        baseline_size=int(baseline_arr.shape[0]),
        participant_size=int(current_arr.shape[0]),
        minimum_required=min_baseline_samples,
        feature_count=int(current_arr.shape[1]),
    )


def build_reference_baseline(
    dataset_X: np.ndarray,
    dataset_y: np.ndarray,
    participant_indices: np.ndarray,
    seed: int,
    min_baseline_samples: int = DEFAULT_MIN_BASELINE_SAMPLES,
) -> Tuple[np.ndarray, BaselineValidationResult]:
    """Construct a deterministic, participant-independent reference baseline."""
    if dataset_X is None or dataset_y is None:
        return (
            np.asarray([], dtype=int),
            BaselineValidationResult(
                status="ERROR",
                message="Missing dataset contents.",
                minimum_required=min_baseline_samples,
            ),
        )

    X = np.asarray(dataset_X, dtype=float)
    y = np.asarray(dataset_y)

    if X.ndim != 2 or y.ndim != 1:
        return (
            np.asarray([], dtype=int),
            BaselineValidationResult(
                status="ERROR",
                message="Dataset must be a 2D feature matrix with a 1D label vector.",
                minimum_required=min_baseline_samples,
            ),
        )

    if X.shape[0] != y.shape[0]:
        return (
            np.asarray([], dtype=int),
            BaselineValidationResult(
                status="ERROR",
                message="Dataset rows and labels are not aligned.",
                minimum_required=min_baseline_samples,
            ),
        )

    if X.shape[0] == 0:
        return (
            np.asarray([], dtype=int),
            BaselineValidationResult(
                status="ERROR",
                message="Dataset is empty.",
                minimum_required=min_baseline_samples,
            ),
        )

    participant_set = set(int(i) for i in np.asarray(participant_indices, dtype=int).tolist())
    candidate_indices = np.asarray(
        [idx for idx in range(len(X)) if idx not in participant_set],
        dtype=int,
    )

    if candidate_indices.size == 0:
        return (
            np.asarray([], dtype=int),
            BaselineValidationResult(
                status="INSUFFICIENT_DATA",
                message="No eligible global rows remain outside the evaluated participant.",
                baseline_size=0,
                participant_size=int(len(participant_indices)),
                minimum_required=min_baseline_samples,
                feature_count=int(X.shape[1]),
            ),
        )

    if candidate_indices.size < min_baseline_samples:
        return (
            np.asarray([], dtype=int),
            BaselineValidationResult(
                status="INSUFFICIENT_DATA",
                message=(
                    f"Reference baseline candidates are too few ({candidate_indices.size}) for the prototype "
                    f"minimum of {min_baseline_samples}. INSUFFICIENT DATA FOR RELIABLE DRIFT ESTIMATION."
                ),
                baseline_size=int(candidate_indices.size),
                participant_size=int(len(participant_indices)),
                minimum_required=min_baseline_samples,
                feature_count=int(X.shape[1]),
            ),
        )

    rng = np.random.RandomState(seed)
    class_labels = np.unique(y)
    desired_per_class = max(1, int(np.ceil(min_baseline_samples / max(1, len(class_labels)))))
    baseline_indices: List[int] = []

    for label in np.unique(y):
        class_candidates = np.asarray([idx for idx in candidate_indices if int(y[idx]) == int(label)], dtype=int)
        if class_candidates.size == 0:
            continue
        rng.shuffle(class_candidates)
        selected = class_candidates[:desired_per_class]
        baseline_indices.extend(selected.tolist())

    if len(baseline_indices) == 0:
        rng.shuffle(candidate_indices)
        baseline_indices = candidate_indices[:min_baseline_samples].tolist()

    baseline_indices = np.asarray(sorted(set(baseline_indices)), dtype=int)
    if baseline_indices.size < min_baseline_samples:
        rng.shuffle(candidate_indices)
        extra = candidate_indices[: max(0, min_baseline_samples - baseline_indices.size)]
        baseline_indices = np.asarray(sorted(set(baseline_indices.tolist() + extra.tolist())), dtype=int)

    baseline_indices = baseline_indices[: min(len(baseline_indices), len(candidate_indices))]
    baseline_indices = np.asarray(baseline_indices, dtype=int)

    reference_features = X[baseline_indices]
    validation = validate_reference_baseline(
        current_features=X[np.asarray(list(participant_indices), dtype=int)],
        baseline_features=reference_features,
        min_baseline_samples=min_baseline_samples,
    )
    return baseline_indices, validation


def _deterministic_baseline_indices(participant: Any, seed: int) -> np.ndarray:
    """Backward-compatible wrapper; direct participant baselines are deprecated in favor of global reference baselines."""
    rng = np.random.RandomState(seed)
    idx = np.arange(len(participant.X))
    rng.shuffle(idx)

    baseline_indices: List[int] = []
    for label in np.unique(participant.y):
        class_indices = np.where(participant.y == label)[0]
        if class_indices.size == 0:
            continue
        baseline_indices.extend(class_indices[:1].tolist())

    baseline_indices = np.asarray(sorted(set(baseline_indices)), dtype=int)
    if baseline_indices.size == 0:
        baseline_indices = idx[: max(2, len(idx) // 2)]
    if baseline_indices.size < 2:
        baseline_indices = idx[: max(2, len(idx) // 2)]
    return baseline_indices


def _scenario_for_participant(index: int, total: int) -> str:
    options = [
        "reliable_participant",
        "unreliable_participant",
        "new_participant_limited_history",
        "repeated_failures",
        "stale_participant",
    ]
    if total <= 0:
        return options[0]
    return options[index % len(options)]


def run_real_data_pipeline(
    csv_path: str,
    target_column: str,
    participants: int,
    seed: int = 42,
    output_dir: str | Path = RESULTS_DIR,
    min_baseline_samples: int = DEFAULT_MIN_BASELINE_SAMPLES,
) -> List[Dict[str, Any]]:
    """Execute the end-to-end real-data pipeline and save CSV/JSON outputs."""
    csv_path = str(csv_path)
    try:
        dataset = load_csv(csv_path, target_column=target_column, verbose=False)
    except (FileNotFoundError, ValueError, OSError) as exc:
        raise ValueError(f"Dataset invalid or not readable: {csv_path}") from exc

    if participants <= 0:
        raise ValueError("participants must be > 0")
    if participants > len(dataset.X):
        raise ValueError(
            f"Cannot create {participants} participants from a dataset with only {len(dataset.X)} rows"
        )

    participant_sets = simulate_participants(
        dataset,
        number_of_participants=participants,
        distribution_mode="iid",
        random_seed=seed,
        verbose=False,
    )

    model_runner = ModelRunner(random_seed=seed)
    results: List[Dict[str, Any]] = []

    for index, participant in enumerate(participant_sets):
        participant_row_indices = np.asarray(participant.metadata.original_row_index, dtype=int)
        baseline_indices, baseline_validation = build_reference_baseline(
            dataset_X=dataset.X,
            dataset_y=dataset.y,
            participant_indices=participant_row_indices,
            seed=seed + index + 10,
            min_baseline_samples=min_baseline_samples,
        )

        if baseline_validation.status in {"ERROR", "INSUFFICIENT_DATA"}:
            baseline_features = np.asarray([], dtype=float).reshape(0, dataset.X.shape[1])
            baseline_labels = np.asarray([], dtype=int)
            dhs_score = 0.0
            dhs_detail = baseline_validation.message
        else:
            baseline_features = np.asarray(dataset.X[baseline_indices], dtype=float)
            baseline_labels = np.asarray(dataset.y[baseline_indices], dtype=int)
            dhs_score = score_drift_health(participant, baseline_features=baseline_features).score
            dhs_detail = f"baseline_status={baseline_validation.status}; {baseline_validation.message}"

        model_run = model_runner.run_for_participant(
            participant,
            baseline_features=baseline_features,
            baseline_labels=baseline_labels,
        )

        dqs = score_data_quality(participant)
        dhs = score_drift_health(participant, baseline_features=baseline_features)
        if baseline_validation.status in {"ERROR", "INSUFFICIENT_DATA"}:
            dhs = type(dhs)(
                component_name="drift_health",
                score=float(dhs_score),
                status="critical",
                details=dhs_detail,
                input_summary={
                    "current_rows": int(participant.X.shape[0]),
                    "baseline_rows": int(baseline_features.shape[0]),
                    "current_features": int(participant.X.shape[1]),
                    "baseline_features": int(baseline_features.shape[1]) if baseline_features.size else 0,
                    "baseline_status": baseline_validation.status,
                    "baseline_message": baseline_validation.message,
                },
            )
        uss = UpdateSafetyScorer().score(model_run.update_safety_input)
        history_profile = simulate_participant_history(
            participant.participant_id,
            _scenario_for_participant(index, len(participant_sets)),
            seed=seed + index + 17,
        )
        rs = ReliabilityScorer().score(history_profile.reliability_input)
        ps = PerformanceScorer().score(model_run.performance_input)

        confidence = float(np.clip(model_run.performance_input.local_accuracy * 100.0, 0.0, 100.0))
        trust_input = TrustInput(
            dqs=float(dqs.score),
            dhs=float(dhs.score),
            uss=float(uss.score),
            rs=float(rs.score),
            ps=float(ps.score),
            confidence=confidence,
            hard_safety_passed=bool(uss.is_valid),
            policy_approved=True,
            formula_version="initial-v1",
            timestamp=time.time(),
        )
        trust_output = TrustScorer().score(trust_input)

        row = {
            "participant_id": participant.participant_id,
            "data_origin": "real_csv_dataset",
            "history_source": history_profile.source,
            "history_scenario": history_profile.scenario,
            "dqs": round(float(dqs.score), 6),
            "dhs": round(float(dhs.score), 6),
            "uss": round(float(uss.score), 6),
            "rs": round(float(rs.score), 6),
            "ps": round(float(ps.score), 6),
            "trust_score": round(float(trust_output.score), 6),
            "confidence": round(float(confidence), 6),
            "decision": trust_output.decision,
            "decision_reason": trust_output.recommendation,
            "baseline_sample_count": int(baseline_features.shape[0]) if baseline_features is not None else 0,
            "baseline_validation_status": baseline_validation.status,
            "baseline_validation_message": baseline_validation.message,
            "psi_average": round(float(getattr(dhs, 'psi_average', 0.0)), 6),
            "drift_level": getattr(dhs, 'drift_level', 'unknown'),
            "real_data": True,
            "simulated_history_metadata": True,
            "simulated_history_values": {
                "success_count": history_profile.reliability_input.success_count,
                "total_count": history_profile.reliability_input.total_count,
                "consecutive_failures": history_profile.reliability_input.consecutive_failures,
                "last_seen_rounds_ago": history_profile.reliability_input.last_seen_rounds_ago,
                "consistency_score": history_profile.reliability_input.consistency_score,
            },
        }
        results.append(row)

        print(
            f"Participant {participant.participant_id}: "
            f"DQS={row['dqs']:.2f} DHS={row['dhs']:.2f} USS={row['uss']:.2f} "
            f"RS={row['rs']:.2f} PS={row['ps']:.2f} Trust={row['trust_score']:.2f} "
            f"Confidence={row['confidence']:.2f} Decision={row['decision']} "
            f"Reason={row['decision_reason']} "
            f"HistorySource={row['history_source']}"
        )

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_output_path = output_dir / "real_data_results.csv"
    json_output_path = output_dir / "real_data_results.json"

    csv_columns = [
        "participant_id",
        "data_origin",
        "history_source",
        "history_scenario",
        "dqs",
        "dhs",
        "uss",
        "rs",
        "ps",
        "trust_score",
        "confidence",
        "decision",
        "decision_reason",
        "baseline_sample_count",
        "baseline_validation_status",
        "baseline_validation_message",
        "psi_average",
        "drift_level",
        "real_data",
        "simulated_history_metadata",
    ]
    with csv_output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=csv_columns)
        writer.writeheader()
        for row in results:
            out = {key: row.get(key, "") for key in csv_columns}
            writer.writerow(out)

    with json_output_path.open("w", encoding="utf-8") as handle:
        json.dump(results, handle, indent=2)

    return results


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the real-data trust pipeline end-to-end.")
    parser.add_argument("--csv", required=True, help="Path to the CSV dataset to load.")
    parser.add_argument("--target", required=True, help="Target column name in the CSV file.")
    parser.add_argument("--participants", type=int, default=5, help="Number of simulated participants to create.")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic seed for splitting and model training.")
    parser.add_argument("--min-baseline-samples", type=int, default=DEFAULT_MIN_BASELINE_SAMPLES, help="Prototype minimum global reference baseline size for PSI drift estimation.")
    parser.add_argument("--output-dir", default=str(RESULTS_DIR), help="Directory where results CSV and JSON are saved.")
    return parser


def main(argv: List[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        rows = run_real_data_pipeline(
            csv_path=args.csv,
            target_column=args.target,
            participants=args.participants,
            seed=args.seed,
            output_dir=args.output_dir,
            min_baseline_samples=args.min_baseline_samples,
        )
    except Exception as exc:  # fail safely for invalid datasets or unsupported inputs
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    csv_output_path = Path(args.output_dir) / "real_data_results.csv"
    json_output_path = Path(args.output_dir) / "real_data_results.json"
    print(f"Saved {len(rows)} participant result rows to {csv_output_path}")
    print(f"Saved {len(rows)} participant result rows to {json_output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
