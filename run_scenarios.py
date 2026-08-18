#!/usr/bin/env python3
"""Prototype scenario validation layer for Protector Uttam.

This module intentionally uses the real scoring engine rather than reimplementing
or mocking formulas. Each scenario is built from a valid baseline input and only
modifies the necessary values to represent a realistic trust issue.
"""

from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.scoring_engines import TrustInput, TrustScorer
from experiments.scenarios.scenario_catalog import BASELINE_INPUT, get_scenarios as catalog_get_scenarios

RESULTS_DIR = Path(__file__).resolve().parent / "experiments" / "results"


def _build_scenario_input(scenario: Dict[str, Any]) -> Dict[str, Any]:
    scenario_input = dict(BASELINE_INPUT)
    scenario_input.update(scenario["input_overrides"])
    return scenario_input


def _hard_safety_result(value: bool) -> str:
    return "PASS" if value else "FAIL"


def _freshness_result(timestamp: float | None, decision: str) -> str:
    if timestamp is None:
        return "UNKNOWN"

    age_days = (time.time() - float(timestamp)) / (24 * 3600)
    thresholds = {
        "warning_days": 14.0,
        "restrict_days": 30.0,
        "block_days": 180.0,
    }

    if age_days >= thresholds["block_days"]:
        return "BLOCK"
    if age_days >= thresholds["restrict_days"]:
        return "RESTRICT"
    if age_days >= thresholds["warning_days"] and decision == "ALLOW":
        return "MONITOR"
    return "CURRENT"


def _scenario_decision_reason(actual_decision: str) -> str:
    if actual_decision == "BLOCK":
        return "Critical safety or policy violation"
    if actual_decision == "REVIEW":
        return "Insufficient evidence or confidence"
    if actual_decision == "MONITOR":
        return "Borderline trust but operationally acceptable"
    return "Healthy and within expected trust band"


def run_single_scenario(scenario: Dict[str, Any]) -> Dict[str, Any]:
    scorer = TrustScorer()
    raw_input = _build_scenario_input(scenario)
    input_data = TrustInput(**raw_input)
    result = scorer.score(input_data)

    actual_decision = result.decision
    expected_decision = scenario["expected_decision"]
    freshness_result = _freshness_result(input_data.timestamp, actual_decision)
    passed = actual_decision == expected_decision

    scenario_record = {
        "scenario": scenario["name"],
        "description": scenario["description"],
        "dqs": round(result.components["dqs"], 2),
        "dhs": round(result.components["dhs"], 2),
        "uss": round(result.components["uss"], 2),
        "rs": round(result.components["rs"], 2),
        "ps": round(result.components["ps"], 2),
        "trust_score": round(result.score, 2),
        "confidence": result.confidence_level.upper(),
        "hard_safety_result": _hard_safety_result(result.hard_safety_passed),
        "freshness_result": freshness_result,
        "expected_decision": expected_decision,
        "actual_decision": actual_decision,
        "decision_reason": _scenario_decision_reason(actual_decision),
        "result": "PASS" if passed else "FAIL",
    }
    return scenario_record


def get_scenarios() -> List[Dict[str, Any]]:
    return catalog_get_scenarios()


def run_all_scenarios(output_dir: str | Path | None = None) -> Dict[str, Any]:
    output_dir = Path(output_dir) if output_dir is not None else RESULTS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    scenarios = get_scenarios()
    results = [run_single_scenario(s) for s in scenarios]

    summary = {
        "total_scenarios": len(results),
        "passed": sum(1 for item in results if item["result"] == "PASS"),
        "failed": sum(1 for item in results if item["result"] == "FAIL"),
        "results": results,
    }

    json_path = output_dir / "scenario_results.json"
    csv_path = output_dir / "scenario_results.csv"

    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    with csv_path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(
            csvfile,
            fieldnames=[
                "scenario",
                "description",
                "dqs",
                "dhs",
                "uss",
                "rs",
                "ps",
                "trust_score",
                "confidence",
                "hard_safety_result",
                "freshness_result",
                "expected_decision",
                "actual_decision",
                "decision_reason",
                "result",
            ],
        )
        writer.writeheader()
        writer.writerows(results)

    return summary


def main() -> int:
    summary = run_all_scenarios()

    print("====================================")
    print("SCENARIO VALIDATION SUMMARY")
    print("====================================")

    for item in summary["results"]:
        print()
        print("====================================")
        print(f"SCENARIO: {item['scenario'].upper()}")
        print("====================================")
        print(f"DQS: {item['dqs']}")
        print(f"DHS: {item['dhs']}")
        print(f"USS: {item['uss']}")
        print(f"RS: {item['rs']}")
        print(f"PS: {item['ps']}")
        print()
        print(f"Trust Score: {item['trust_score']}")
        print(f"Confidence: {item['confidence']}")
        print(f"Hard Safety: {item['hard_safety_result']}")
        print(f"Freshness: {item['freshness_result']}")
        print(f"Expected: {item['expected_decision']}")
        print(f"Actual: {item['actual_decision']}")
        print(f"Decision reason: {item['decision_reason']}")
        print(f"RESULT: {item['result']}")

    print()
    print(f"TOTAL PASS: {summary['passed']}/{summary['total_scenarios']}")
    if summary["failed"]:
        print(f"TOTAL FAIL: {summary['failed']}")
        return 1
    print("ALL SCENARIOS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
