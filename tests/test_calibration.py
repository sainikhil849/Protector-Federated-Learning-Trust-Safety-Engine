import os

from src.calibration import (
    DEFAULT_CANDIDATE_WEIGHTS,
    calibrate_thresholds,
    evaluate_weight_configuration,
    export_calibration_artifacts,
    generate_validation_scenarios,
    run_weight_validation,
    select_best_configuration,
)


class TestCalibration:
    def test_validation_calculates_expected_metrics(self):
        scenarios = generate_validation_scenarios()
        result = evaluate_weight_configuration(
            weights=DEFAULT_CANDIDATE_WEIGHTS[0],
            scenarios=scenarios,
            threshold=75.0,
            business_costs={"false_negative": 10.0, "false_positive": 2.0},
            experiment_name="test-validation",
            selection_reason="unit-test-check",
        )

        assert result.tp >= 0
        assert result.tn >= 0
        assert result.fp >= 0
        assert result.fn >= 0
        assert 0.0 <= result.precision <= 1.0
        assert 0.0 <= result.recall <= 1.0
        assert 0.0 <= result.f1 <= 1.0
        assert 0.0 <= result.false_positive_rate <= 1.0
        assert 0.0 <= result.false_negative_rate <= 1.0
        assert result.weighted_error >= 0.0
        assert result.selection_reason == "unit-test-check"

    def test_candidate_validation_and_selection(self):
        results = run_weight_validation(
            candidate_weights=DEFAULT_CANDIDATE_WEIGHTS,
            validation_scenarios=generate_validation_scenarios(),
            threshold=75.0,
            business_costs={"false_negative": 10.0, "false_positive": 2.0},
        )

        assert len(results) == 3
        selected = select_best_configuration(results)
        assert selected in results
        assert selected.weighted_error >= 0

    def test_threshold_calibration(self):
        results = calibrate_thresholds(
            weights=DEFAULT_CANDIDATE_WEIGHTS[0],
            validation_scenarios=generate_validation_scenarios(),
            candidate_thresholds=[60.0, 70.0, 75.0, 80.0],
            business_costs={"false_negative": 10.0, "false_positive": 2.0},
        )

        assert len(results) == 4
        assert all(result.experiment.startswith("threshold-") for result in results)

    def test_chart_generation(self):
        output_dir = "docs/charts"
        os.makedirs(output_dir, exist_ok=True)
        results = export_calibration_artifacts(
            output_dir=output_dir,
            candidate_weights=DEFAULT_CANDIDATE_WEIGHTS,
            validation_scenarios=generate_validation_scenarios(),
            threshold=75.0,
            business_costs={"false_negative": 10.0, "false_positive": 2.0},
        )

        assert len(results) == 3
        assert os.path.exists(os.path.join(output_dir, "calibration_results.svg"))
