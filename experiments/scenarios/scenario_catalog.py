"""Scenario catalog used by the scenario validation runner."""

from __future__ import annotations

import time
from typing import Any, Dict, List

BASELINE_INPUT = {
    "dqs": 92,
    "dhs": 90,
    "uss": 95,
    "rs": 88,
    "ps": 90,
    "confidence": 85,
    "hard_safety_passed": True,
    "policy_approved": True,
    "timestamp": time.time(),
}


def get_scenarios() -> List[Dict[str, Any]]:
    """Return the prototype scenario catalog.

    Each scenario starts from the same valid baseline and only modifies the
    necessary input(s) to simulate a real-world trust failure pattern.
    """
    now = time.time()
    return [
        {
            "name": "healthy_participant",
            "description": "Healthy participant with strong scores across all dimensions.",
            "input_overrides": {},
            "expected_decision": "ALLOW",
        },
        {
            "name": "poor_data_quality",
            "description": "Data quality collapse caused by incomplete or noisy data.",
            "input_overrides": {
                "dqs": 32,
                "rs": 42,
                "ps": 38,
                "confidence": 68,
            },
            "expected_decision": "MONITOR",
        },
        {
            "name": "high_data_drift",
            "description": "Strong distribution drift indicates the participant data has drifted far from expected distribution.",
            "input_overrides": {
                "dhs": 18,
                "dqs": 78,
                "uss": 72,
                "rs": 74,
                "confidence": 80,
            },
            "expected_decision": "MONITOR",
        },
        {
            "name": "unsafe_update",
            "description": "The model update fails the hard safety gate and should be blocked immediately.",
            "input_overrides": {
                "uss": 12,
                "dqs": 72,
                "dhs": 68,
                "rs": 66,
                "ps": 70,
                "hard_safety_passed": False,
                "policy_approved": True,
                "confidence": 64,
            },
            "expected_decision": "BLOCK",
        },
        {
            "name": "stale_update",
            "description": "The update is older than the configured staleness threshold and should be rejected as stale.",
            "input_overrides": {
                "timestamp": now - (200 * 24 * 3600),
            },
            "expected_decision": "BLOCK",
        },
        {
            "name": "high_trust_low_confidence",
            "description": "Trust is high but evidence is weak, so the system should require review due to low confidence.",
            "input_overrides": {
                "confidence": 28,
            },
            "expected_decision": "REVIEW",
        },
        {
            "name": "unreliable_participant",
            "description": "Reliability history is too poor to trust the participant consistently.",
            "input_overrides": {
                "dqs": 70,
                "dhs": 68,
                "uss": 70,
                "rs": 20,
                "ps": 66,
                "confidence": 71,
            },
            "expected_decision": "MONITOR",
        },
        {
            "name": "poor_model_performance",
            "description": "The model update performs poorly and fails to offer a meaningful net benefit.",
            "input_overrides": {
                "dqs": 76,
                "dhs": 74,
                "uss": 80,
                "rs": 72,
                "ps": 18,
                "confidence": 60,
            },
            "expected_decision": "MONITOR",
        },
    ]
