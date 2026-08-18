from pathlib import Path
import numpy as np

from src.dataset_loader import load_csv
from src.participant_simulator import ParticipantData, simulate_participants
from src.scoring_engines import DataQualityScorer, DriftHealthScorer
from src.component_orchestrator import (
    score_participant_components,
    score_data_quality,
    score_drift_health,
)


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "participant_component_fixture.csv"


def _load_fixture_dataset():
    return load_csv(str(FIXTURE_PATH), target_column="label", verbose=False)


def test_component_orchestrator_normal_participant(monkeypatch):
    calls = {"dqs": 0, "dhs": 0}
    original_dqs = DataQualityScorer.score
    original_dhs = DriftHealthScorer.score

    def wrapped_dqs(self, data):
        calls["dqs"] += 1
        return original_dqs(self, data)

    def wrapped_dhs(self, data):
        calls["dhs"] += 1
        return original_dhs(self, data)

    monkeypatch.setattr(DataQualityScorer, "score", wrapped_dqs)
    monkeypatch.setattr(DriftHealthScorer, "score", wrapped_dhs)

    dataset = _load_fixture_dataset()
    participants = simulate_participants(
        dataset,
        number_of_participants=3,
        distribution_mode="iid",
        random_seed=7,
        verbose=False,
    )

    results = score_participant_components(participants[0], baseline_features=dataset.X)

    assert {result.component_name for result in results} == {"data_quality", "drift_health"}
    assert calls == {"dqs": 1, "dhs": 1}

    dqs = next(r for r in results if r.component_name == "data_quality")
    dhs = next(r for r in results if r.component_name == "drift_health")

    assert 0.0 <= dqs.score <= 100.0
    assert 0.0 <= dhs.score <= 100.0
    assert dqs.status in {"healthy", "warning", "degraded", "critical"}
    assert dhs.status in {"healthy", "warning", "degraded", "critical"}
    assert dqs.input_summary["rows"] == participants[0].row_count
    assert dhs.input_summary["baseline_rows"] == dataset.X.shape[0]


def test_component_orchestrator_missing_value_degradation(monkeypatch):
    calls = {"dqs": 0, "dhs": 0}
    original_dqs = DataQualityScorer.score
    original_dhs = DriftHealthScorer.score

    def wrapped_dqs(self, data):
        calls["dqs"] += 1
        return original_dqs(self, data)

    def wrapped_dhs(self, data):
        calls["dhs"] += 1
        return original_dhs(self, data)

    monkeypatch.setattr(DataQualityScorer, "score", wrapped_dqs)
    monkeypatch.setattr(DriftHealthScorer, "score", wrapped_dhs)

    dataset = _load_fixture_dataset()
    participant = simulate_participants(
        dataset,
        number_of_participants=2,
        distribution_mode="iid",
        random_seed=11,
        verbose=False,
    )[0]

    degraded = ParticipantData(
        participant_id=participant.participant_id,
        X=participant.X.copy(),
        y=participant.y.copy(),
        row_count=participant.row_count,
        timestamp=participant.timestamp,
        metadata=participant.metadata,
    )
    degraded.X[:, 0] = np.nan
    degraded.X[:, 1] = 250000.0
    degraded.X[:, 2] = np.nan
    degraded.X[:, 3] = -10.0

    results = score_participant_components(degraded, baseline_features=dataset.X)
    dqs = next(r for r in results if r.component_name == "data_quality")

    assert calls == {"dqs": 1, "dhs": 1}
    assert dqs.input_summary["missing_values"] > 0
    assert dqs.score < 100.0
    assert dqs.status in {"warning", "degraded", "critical"}


def test_component_orchestrator_drifted_participant(monkeypatch):
    calls = {"dqs": 0, "dhs": 0}
    original_dqs = DataQualityScorer.score
    original_dhs = DriftHealthScorer.score

    def wrapped_dqs(self, data):
        calls["dqs"] += 1
        return original_dqs(self, data)

    def wrapped_dhs(self, data):
        calls["dhs"] += 1
        return original_dhs(self, data)

    monkeypatch.setattr(DataQualityScorer, "score", wrapped_dqs)
    monkeypatch.setattr(DriftHealthScorer, "score", wrapped_dhs)

    dataset = _load_fixture_dataset()
    participant = simulate_participants(
        dataset,
        number_of_participants=2,
        distribution_mode="iid",
        random_seed=3,
        verbose=False,
    )[0]

    drifted_X = participant.X.copy() * 2.5
    drifted_participant = ParticipantData(
        participant_id=participant.participant_id,
        X=drifted_X,
        y=participant.y.copy(),
        row_count=participant.row_count,
        timestamp=participant.timestamp,
        metadata=participant.metadata,
    )

    results = score_participant_components(drifted_participant, baseline_features=dataset.X)
    dhs = next(r for r in results if r.component_name == "drift_health")

    assert calls == {"dqs": 1, "dhs": 1}
    assert dhs.score < 100.0
    assert dhs.status in {"warning", "degraded", "critical"}
    assert dhs.details.lower().find("drift") >= 0 or dhs.details.lower().find("psi") >= 0

    quality = next(r for r in results if r.component_name == "data_quality")
    assert quality.score <= 100.0


def test_direct_component_helpers():
    dataset = _load_fixture_dataset()
    participant = simulate_participants(dataset, number_of_participants=2, distribution_mode="iid", random_seed=13, verbose=False)[0]

    dqs = score_data_quality(participant)
    dhs = score_drift_health(participant, baseline_features=dataset.X)

    assert dqs.component_name == "data_quality"
    assert dhs.component_name == "drift_health"
    assert isinstance(dqs.input_summary, dict)
    assert isinstance(dhs.input_summary, dict)
    assert 0.0 <= dqs.score <= 100.0
    assert 0.0 <= dhs.score <= 100.0
