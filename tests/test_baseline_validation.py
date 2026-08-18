import numpy as np

from run_real_data import (
    DEFAULT_MIN_BASELINE_SAMPLES,
    build_reference_baseline,
    validate_reference_baseline,
)


def test_reference_baseline_is_independent_and_deterministic():
    dataset_X = np.arange(192, dtype=float).reshape(48, 4)
    dataset_y = np.repeat(np.array([0, 1, 2, 3]), 12)
    participant_indices = np.array([0, 1, 3, 4, 6, 7, 9, 10, 12, 13, 15, 16], dtype=int)

    baseline_a, validation_a = build_reference_baseline(
        dataset_X=dataset_X,
        dataset_y=dataset_y,
        participant_indices=participant_indices,
        seed=42,
        min_baseline_samples=DEFAULT_MIN_BASELINE_SAMPLES,
    )
    baseline_b, validation_b = build_reference_baseline(
        dataset_X=dataset_X,
        dataset_y=dataset_y,
        participant_indices=participant_indices,
        seed=42,
        min_baseline_samples=DEFAULT_MIN_BASELINE_SAMPLES,
    )

    assert baseline_a.tolist() == baseline_b.tolist()
    assert validation_a.status == "VALID"
    assert validation_b.status == "VALID"
    assert not set(baseline_a).intersection(set(participant_indices))
    assert len(baseline_a) >= DEFAULT_MIN_BASELINE_SAMPLES


def test_reference_baseline_detects_insufficient_data():
    dataset_X = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]])
    dataset_y = np.array([0, 1, 0])

    result = build_reference_baseline(
        dataset_X=dataset_X,
        dataset_y=dataset_y,
        participant_indices=np.array([0, 1, 2], dtype=int),
        seed=7,
        min_baseline_samples=8,
    )

    assert isinstance(result, tuple)
    baseline_indices, validation = result
    assert validation.status == "INSUFFICIENT_DATA"
    assert len(baseline_indices) == 0


def test_feature_mismatch_fails_safely():
    current = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
    baseline = np.array([[1.0, 2.0, 3.0, 4.0], [5.0, 6.0, 7.0, 8.0]])

    validation = validate_reference_baseline(current, baseline, min_baseline_samples=2)
    assert validation.status == "ERROR"
    assert "feature count" in validation.message.lower()


def test_normal_distribution_has_lower_psi_than_severe_drift():
    rng = np.random.RandomState(0)
    reference = rng.normal(loc=50.0, scale=3.0, size=(500, 4))
    normal = rng.normal(loc=52.0, scale=3.2, size=(300, 4))
    moderate = rng.normal(loc=60.0, scale=6.0, size=(300, 4))
    severe = rng.normal(loc=90.0, scale=15.0, size=(300, 4))

    from src.scoring_engines import DriftHealthScorer, DriftHealthInput

    scorer = DriftHealthScorer()
    normal_out = scorer.score(DriftHealthInput(current_features=normal, baseline_features=reference))
    moderate_out = scorer.score(DriftHealthInput(current_features=moderate, baseline_features=reference))
    severe_out = scorer.score(DriftHealthInput(current_features=severe, baseline_features=reference))

    assert normal_out.psi_average < moderate_out.psi_average < severe_out.psi_average
    assert normal_out.score >= moderate_out.score >= severe_out.score


def test_baseline_validation_rejects_nan_and_constant_columns():
    current = np.array([[1.0, 2.0], [3.0, 4.0]])
    baseline = np.array([[np.nan, 5.0], [np.nan, 5.0]])

    validation = validate_reference_baseline(current, baseline, min_baseline_samples=2)
    assert validation.status == "ERROR"
    assert "nan" in validation.message.lower()

    constant = np.array([[1.0, 1.0], [1.0, 1.0]])
    validation = validate_reference_baseline(current, constant, min_baseline_samples=2)
    assert validation.status in {"WARNING", "VALID"}


def test_same_seed_reproduces_reference_baseline():
    x = np.arange(80, dtype=float).reshape(20, 4)
    y = np.repeat(np.array([0, 1, 2, 3]), 5)
    participant_indices = np.array([0, 1, 2, 3, 4, 5, 10, 11, 12, 13, 14, 15])

    first = build_reference_baseline(
        dataset_X=x,
        dataset_y=y,
        participant_indices=participant_indices,
        seed=123,
        min_baseline_samples=8,
    )
    second = build_reference_baseline(
        dataset_X=x,
        dataset_y=y,
        participant_indices=participant_indices,
        seed=123,
        min_baseline_samples=8,
    )

    assert first[0].tolist() == second[0].tolist()
