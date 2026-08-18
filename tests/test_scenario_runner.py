from pathlib import Path

import run_scenarios


EXPECTED_SCENARIOS = [
    "healthy_participant",
    "poor_data_quality",
    "high_data_drift",
    "unsafe_update",
    "stale_update",
    "high_trust_low_confidence",
    "unreliable_participant",
    "poor_model_performance",
]


def test_scenario_registry_contains_all_required_scenarios():
    scenarios = run_scenarios.get_scenarios()
    assert [scenario["name"] for scenario in scenarios] == EXPECTED_SCENARIOS


def test_run_all_scenarios_writes_outputs(tmp_path):
    results = run_scenarios.run_all_scenarios(output_dir=tmp_path)

    assert results["total_scenarios"] == 8
    assert len(results["results"]) == 8
    assert all(item["result"] in {"PASS", "FAIL"} for item in results["results"])
    assert (tmp_path / "scenario_results.json").exists()
    assert (tmp_path / "scenario_results.csv").exists()
    assert all(item["expected_decision"] in {"ALLOW", "MONITOR", "REVIEW", "BLOCK"} for item in results["results"])
