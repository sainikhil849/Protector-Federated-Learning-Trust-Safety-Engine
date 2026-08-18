import numpy as np

from src.model_runner import ModelRunner
from src.participant_simulator import ParticipantData, ParticipantMetadata


def test_model_runner_ignores_empty_baseline_without_crashing():
    X = np.array(
        [
            [1.0, 1.0],
            [1.2, 1.1],
            [2.0, 2.0],
            [2.2, 1.9],
        ],
        dtype=float,
    )
    y = np.array([0, 0, 1, 1], dtype=int)
    participant = ParticipantData(
        participant_id="ORG-TEST",
        X=X,
        y=y,
        row_count=len(X),
        timestamp=0.0,
        metadata=ParticipantMetadata(
            original_row_index=[0, 1, 2, 3],
            class_distribution={0: 2, 1: 2},
            feature_count=X.shape[1],
            missing_value_count=0,
            duplicate_row_count=0,
        ),
    )

    runner = ModelRunner(random_seed=7)
    result = runner.run_for_participant(
        participant,
        baseline_features=np.empty((0, X.shape[1]), dtype=float),
        baseline_labels=np.empty((0,), dtype=int),
    )

    assert result.participant_id == "ORG-TEST"
    assert result.performance_input.local_accuracy >= 0.0
    assert result.update_safety_input.gradient.size >= 1
