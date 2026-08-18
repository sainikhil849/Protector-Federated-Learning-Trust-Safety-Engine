"""Prototype multi-round trust simulation built on top of the frozen scoring engine."""

from __future__ import annotations

import csv
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from src.component_orchestrator import score_data_quality, score_drift_health
from src.dataset_loader import load_csv
from src.model_runner import ModelRunner
from src.participant_history import PROTOTYPE_HISTORY_SOURCE, simulate_participant_history
from src.participant_simulator import simulate_participants
from src.result_exporter import export_results_csv, export_results_json
from src.scenario_injector import apply_scenario_to_participant
from src.scoring_engines import (
    PerformanceScorer,
    ReliabilityScorer,
    TrustInput,
    TrustScorer,
    UpdateSafetyScorer,
)


RESULTS_DIR = Path("experiments/results")
DEFAULT_MULTI_ROUND_RESULTS_CSV = RESULTS_DIR / "multi_round_results.csv"
DEFAULT_MULTI_ROUND_RESULTS_JSON = RESULTS_DIR / "multi_round_results.json"


@dataclass
class ParticipantHistoryState:
    """Persisted prototype history for a participant across rounds."""

    participant_id: str
    round_history: List[int] = field(default_factory=list)
    decision_history: List[str] = field(default_factory=list)
    trust_history: List[float] = field(default_factory=list)
    confidence_history: List[float] = field(default_factory=list)
    performance_history: List[float] = field(default_factory=list)
    last_seen_round: int = 0
    success_count: int = 0
    total_count: int = 0
    consecutive_failures: int = 0
    last_seen_rounds_ago: int = 0
    consistency_score: float = 1.0


def _build_participant_history_state(participant_id: str) -> ParticipantHistoryState:
    return ParticipantHistoryState(participant_id=participant_id)


def _update_history_state(
    history_state: ParticipantHistoryState,
    *,
    round_number: int,
    decision: str,
    trust_score: float,
    confidence: float,
    performance_score: float,
) -> None:
    history_state.round_history.append(round_number)
    history_state.decision_history.append(decision)
    history_state.trust_history.append(float(trust_score))
    history_state.confidence_history.append(float(confidence))
    history_state.performance_history.append(float(performance_score))
    history_state.total_count += 1
    history_state.last_seen_round = round_number
    history_state.last_seen_rounds_ago = 0
    if decision == "ALLOW":
        history_state.success_count += 1
        history_state.consecutive_failures = 0
    else:
        history_state.consecutive_failures += 1
    if history_state.trust_history:
        history_state.consistency_score = float(np.clip(np.mean(history_state.trust_history) / 100.0, 0.0, 1.0))


def _history_for_reliability(
    participant_id: str,
    *,
    history_state: ParticipantHistoryState,
    scenario: str,
    seed: int,
    round_number: int,
) -> Dict[str, Any]:
    profile = simulate_participant_history(participant_id, scenario, seed=seed + round_number)
    reliability = profile.reliability_input

    success_count = max(1, history_state.success_count)
    total_count = max(1, history_state.total_count)
    last_seen_rounds_ago = max(0, round_number - history_state.last_seen_round)
    consistency_score = float(np.clip(history_state.consistency_score, 0.0, 1.0))

    return {
        "success_count": success_count,
        "total_count": total_count,
        "consecutive_failures": history_state.consecutive_failures,
        "last_seen_rounds_ago": last_seen_rounds_ago,
        "consistency_score": consistency_score,
        "simulated_profile": profile,
        "reliability_input": ReliabilityScorer().score(
            type(reliability)(
                last_seen_rounds_ago=last_seen_rounds_ago,
                success_count=success_count,
                total_count=total_count,
                consecutive_failures=history_state.consecutive_failures,
                consistency_score=consistency_score,
            )
        ),
    }


def _participant_reference_baseline(
    dataset: Any,
    participant: Any,
    *,
    seed: int,
    min_baseline_samples: int = 12,
) -> tuple[np.ndarray, Dict[str, Any]]:
    """Use the same participant-independent reference baseline pattern as the real-data runner."""
    from run_real_data import build_reference_baseline

    candidate_indices = np.asarray(participant.metadata.original_row_index, dtype=int)
    baseline_indices, validation = build_reference_baseline(
        dataset_X=dataset.X,
        dataset_y=dataset.y,
        participant_indices=candidate_indices,
        seed=seed,
        min_baseline_samples=min_baseline_samples,
    )

    if validation.status in {"ERROR", "INSUFFICIENT_DATA"}:
        baseline_features = np.asarray([], dtype=float).reshape(0, dataset.X.shape[1])
        return baseline_features, {"status": validation.status, "message": validation.message}

    baseline_features = np.asarray(dataset.X[baseline_indices], dtype=float)
    return baseline_features, {"status": validation.status, "message": validation.message}


def run_multi_round_pipeline(
    csv_path: str,
    target_column: str,
    participants: int,
    rounds: int,
    seed: int = 42,
    scenario: str = "normal",
    output_dir: str | Path = DEFAULT_MULTI_ROUND_RESULTS_CSV.parent,
    min_baseline_samples: int = 12,
) -> List[Dict[str, Any]]:
    """Run multi-round participant scoring while reusing the frozen scoring engine."""
    if rounds <= 0:
        raise ValueError("rounds must be > 0")
    if participants <= 0:
        raise ValueError("participants must be > 0")

    dataset = load_csv(csv_path, target_column=target_column, verbose=False)
    history_store: Dict[str, ParticipantHistoryState] = {}
    model_runner = ModelRunner(random_seed=seed)
    rows: List[Dict[str, Any]] = []

    for round_number in range(1, rounds + 1):
        participant_sets = simulate_participants(
            dataset,
            number_of_participants=participants,
            distribution_mode="iid",
            random_seed=seed + round_number,
            verbose=False,
        )

        for participant in participant_sets:
            history_state = history_store.setdefault(participant.participant_id, _build_participant_history_state(participant.participant_id))
            scenario_name = scenario.lower() if isinstance(scenario, str) else "normal"
            scenario_participant, _ = apply_scenario_to_participant(
                participant,
                scenario=scenario_name,
                round_number=round_number,
                seed=seed + round_number,
            )

            baseline_features, baseline_validation = _participant_reference_baseline(
                dataset,
                participant,
                seed=seed + round_number + 100,
                min_baseline_samples=min_baseline_samples,
            )
            if baseline_features.size == 0:
                baseline_labels = np.asarray([], dtype=int)
            else:
                baseline_labels = np.asarray(dataset.y[np.asarray(sorted(set(np.asarray(np.arange(len(dataset.X))))), dtype=int)[: baseline_features.shape[0]]], dtype=int) if False else np.asarray([], dtype=int)

            if baseline_features.size > 0:
                from run_real_data import build_reference_baseline

                candidate_indices = np.asarray(participant.metadata.original_row_index, dtype=int)
                base_idx, _ = build_reference_baseline(
                    dataset.X,
                    dataset.y,
                    candidate_indices,
                    seed=seed + round_number + 200,
                    min_baseline_samples=min_baseline_samples,
                )
                baseline_features = np.asarray(dataset.X[base_idx], dtype=float)
                baseline_labels = np.asarray(dataset.y[base_idx], dtype=int)
            else:
                baseline_features = np.asarray([], dtype=float).reshape(0, dataset.X.shape[1])
                baseline_labels = np.asarray([], dtype=int)

            model_run = model_runner.run_for_participant(
                scenario_participant,
                baseline_features=baseline_features,
                baseline_labels=baseline_labels,
            )
            dqs = score_data_quality(scenario_participant)
            if baseline_features.size == 0:
                dhs = type(dqs)(
                    component_name="drift_health",
                    score=0.0,
                    status="critical",
                    details="INSUFFICIENT DATA FOR RELIABLE DRIFT ESTIMATION",
                    input_summary={"current_rows": int(scenario_participant.row_count), "baseline_rows": 0},
                )
            else:
                dhs = score_drift_health(scenario_participant, baseline_features=baseline_features)
            uss = UpdateSafetyScorer().score(model_run.update_safety_input)

            profile_info = _history_for_reliability(
                participant.participant_id,
                history_state=history_state,
                scenario=scenario_name,
                seed=seed,
                round_number=round_number,
            )
            rs = profile_info["reliability_input"]
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

            _update_history_state(
                history_state,
                round_number=round_number,
                decision=trust_output.decision,
                trust_score=trust_output.score,
                confidence=confidence,
                performance_score=float(ps.score),
            )

            row = {
                "round": round_number,
                "participant_id": participant.participant_id,
                "participated": True,
                "DQS": round(float(dqs.score), 6),
                "DHS": round(float(dhs.score), 6),
                "USS": round(float(uss.score), 6),
                "RS": round(float(rs.score), 6),
                "PS": round(float(ps.score), 6),
                "confidence": round(float(confidence), 6),
                "trust_score": round(float(trust_output.score), 6),
                "decision": trust_output.decision,
                "data_origin": "real_csv_dataset",
                "history_source": PROTOTYPE_HISTORY_SOURCE,
                "real_data": True,
                "simulated_history_metadata": True,
                "scenario": scenario_name,
                "validation_message": baseline_validation["message"],
                "participant_history": {
                    "success_count": history_state.success_count,
                    "total_count": history_state.total_count,
                    "consecutive_failures": history_state.consecutive_failures,
                    "last_seen_rounds_ago": history_state.last_seen_rounds_ago,
                    "consistency_score": round(float(history_state.consistency_score), 6),
                    "trust_history": [round(float(v), 6) for v in history_state.trust_history],
                    "decision_history": list(history_state.decision_history),
                },
            }
            rows.append(row)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path_out = output_dir / "multi_round_results.csv"
    json_path_out = output_dir / "multi_round_results.json"
    export_results_csv(rows, csv_path_out)
    export_results_json(rows, json_path_out)
    return rows


def main(argv: Optional[List[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Run a prototype multi-round trust simulation.")
    parser.add_argument("--csv", required=True, help="Path to the CSV dataset.")
    parser.add_argument("--target", required=True, help="Target column name.")
    parser.add_argument("--participants", type=int, default=3, help="Number of participants per round.")
    parser.add_argument("--rounds", type=int, default=10, help="Number of federated rounds to simulate.")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic seed for reproducibility.")
    parser.add_argument("--scenario", default="mixed", choices=sorted({"normal", "drift", "unreliable", "poor_performance", "unsafe_update", "mixed"}), help="Prototype scenario to inject.")
    parser.add_argument("--output-dir", default=str(DEFAULT_MULTI_ROUND_RESULTS_CSV.parent), help="Directory for generated CSV and JSON results.")
    args = parser.parse_args(argv)

    rows = run_multi_round_pipeline(
        csv_path=args.csv,
        target_column=args.target,
        participants=args.participants,
        rounds=args.rounds,
        seed=args.seed,
        scenario=args.scenario,
        output_dir=args.output_dir,
    )

    print(f"Generated {len(rows)} multi-round rows in {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
