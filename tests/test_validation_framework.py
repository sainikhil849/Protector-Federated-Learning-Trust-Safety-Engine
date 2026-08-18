from src.validation_framework import (
    calculate_validation_summary,
    evaluate_experiment,
    generate_ground_truth_scenarios,
    run_validation_experiments,
)


class TestValidationFramework:
    def test_ground_truth_scenarios_are_independent(self):
        scenarios = generate_ground_truth_scenarios()
        assert len(scenarios) == 8
        assert all(scenario.ground_truth in {"SAFE", "UNSAFE", "RESTRICT", "REVIEW", "DEGRADED", "SUSPICIOUS"} for scenario in scenarios)

    def test_experiment_evaluation_returns_metrics_and_correctness(self):
        scenario = generate_ground_truth_scenarios()[0]
        record = evaluate_experiment(scenario)

        assert record.scenario_id == "V-001"
        assert record.ground_truth == "SAFE"
        assert record.decision in {"ALLOW", "MONITOR", "REVIEW", "BLOCK", "RESTRICT"}
        assert isinstance(record.correct, bool)
        assert record.predicted_positive in {True, False}
        assert record.ground_truth_positive in {True, False}

    def test_validation_summary_calculates_all_metrics(self):
        scenarios = generate_ground_truth_scenarios()
        records = [evaluate_experiment(s) for s in scenarios]
        summary = calculate_validation_summary(records)

        assert summary.total_experiments == len(scenarios)
        assert summary.tp >= 0
        assert summary.tn >= 0
        assert summary.fp >= 0
        assert summary.fn >= 0
        assert 0.0 <= summary.precision <= 1.0
        assert 0.0 <= summary.recall <= 1.0
        assert 0.0 <= summary.f1 <= 1.0
        assert 0.0 <= summary.specificity <= 1.0
        assert 0.0 <= summary.balanced_accuracy <= 1.0
        assert 0.0 <= summary.fpr <= 1.0
        assert 0.0 <= summary.fnr <= 1.0

    def test_run_validation_experiments_exports_results(self):
        payload = run_validation_experiments(output_dir="experiments/results")
        assert payload["summary"]["total_experiments"] == 8
        assert payload["records"]
        assert len(payload["records"]) == 8
