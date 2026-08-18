import numpy as np
import pytest

from src.dataset_loader import load_csv
from src.model_runner import ModelRunner
from src.participant_simulator import simulate_participants


FIXTURE_PATH = "tests/fixtures/participant_component_fixture.csv"


@pytest.fixture
def dataset():
    return load_csv(FIXTURE_PATH, target_column="label", verbose=False)


@pytest.fixture
def participant(dataset):
    return simulate_participants(
        dataset,
        number_of_participants=3,
        distribution_mode="iid",
        random_seed=7,
        verbose=False,
    )[0]


def test_model_runner_deterministic_training(participant):
    runner = ModelRunner(random_seed=11)
    result_1 = runner.run_for_participant(participant)
    result_2 = runner.run_for_participant(participant)

    assert result_1.metrics["local_accuracy"] == result_2.metrics["local_accuracy"]
    assert np.allclose(result_1.model.coef_, result_2.model.coef_)
    assert np.allclose(result_1.model.intercept_, result_2.model.intercept_)
    assert result_1.timestamp == result_2.timestamp or abs(result_1.timestamp - result_2.timestamp) < 1.0


def test_model_runner_valid_metrics(participant):
    runner = ModelRunner(random_seed=9)
    result = runner.run_for_participant(participant)

    required = {
        "local_accuracy",
        "baseline_accuracy",
        "class_fairness_score",
        "metric_variance",
        "update_impact",
        "f1_score",
    }

    assert required.issubset(result.metrics)
    for key in required:
        assert 0.0 <= float(result.metrics[key]) <= 1.0 or key in {"update_impact"}
    assert 0.0 <= result.performance_input.local_accuracy <= 1.0
    assert 0.0 <= result.performance_input.f1_score <= 1.0


def test_model_runner_valid_update_shape(participant):
    runner = ModelRunner(random_seed=4)
    result = runner.run_for_participant(participant)

    update = result.update_safety_input.gradient
    assert update.ndim == 1
    assert update.size in {5, 128}
    assert np.all(np.isfinite(update))


def test_model_runner_same_seed_reproducibility(participant):
    runner_a = ModelRunner(random_seed=123)
    runner_b = ModelRunner(random_seed=123)

    result_a = runner_a.run_for_participant(participant)
    result_b = runner_b.run_for_participant(participant)

    assert np.allclose(result_a.model.coef_, result_b.model.coef_)
    assert np.allclose(result_a.model.intercept_, result_b.model.intercept_)
    assert np.allclose(result_a.update_safety_input.gradient, result_b.update_safety_input.gradient)


def test_model_runner_invalid_update_handling(dataset):
    participant = simulate_participants(
        dataset,
        number_of_participants=3,
        distribution_mode="iid",
        random_seed=12,
        verbose=False,
    )[0]

    runner = ModelRunner(random_seed=42)

    with pytest.raises(ValueError):
        runner.run_for_participant(participant, baseline_model=None, baseline_features=np.ones((2, 2)), baseline_labels=np.array([0, 1]))

    with pytest.raises(ValueError):
        runner.run_for_participant(
            participant,
            baseline_model=None,
            baseline_features=np.ones((len(participant.X), participant.X.shape[1])),
            baseline_labels=np.array([1] * len(participant.X)),
        )
