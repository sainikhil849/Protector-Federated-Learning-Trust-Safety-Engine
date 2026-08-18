"""Prototype participant history metadata for federated trust experiments.

This module intentionally simulates historical participation metadata only.
The data values are not measured from a real federated system and must not be
presented as observed production history.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
import numpy as np

from src.scoring_engines import ReliabilityInput


PROTOTYPE_HISTORY_SOURCE = "simulated prototype metadata"

SCENARIO_LIBRARY = {
    "reliable_participant": {
        "success_count": 18,
        "total_count": 20,
        "consecutive_failures": 0,
        "last_seen_rounds_ago": 1,
        "consistency_score": 0.95,
    },
    "unreliable_participant": {
        "success_count": 7,
        "total_count": 12,
        "consecutive_failures": 2,
        "last_seen_rounds_ago": 3,
        "consistency_score": 0.72,
    },
    "new_participant_limited_history": {
        "success_count": 1,
        "total_count": 2,
        "consecutive_failures": 0,
        "last_seen_rounds_ago": 0,
        "consistency_score": 0.65,
    },
    "repeated_failures": {
        "success_count": 2,
        "total_count": 9,
        "consecutive_failures": 6,
        "last_seen_rounds_ago": 7,
        "consistency_score": 0.35,
    },
    "stale_participant": {
        "success_count": 4,
        "total_count": 9,
        "consecutive_failures": 3,
        "last_seen_rounds_ago": 8,
        "consistency_score": 0.55,
    },
}


@dataclass
class ParticipantHistoryProfile:
    """Deterministic prototype metadata profile for a participant."""

    participant_id: str
    scenario: str
    source: str
    reliability_input: ReliabilityInput
    seed: int


def _validate_history_config(config: Dict[str, Any]) -> Dict[str, Any]:
    required = {
        "success_count",
        "total_count",
        "consecutive_failures",
        "last_seen_rounds_ago",
        "consistency_score",
    }
    missing = sorted(required - set(config.keys()))
    if missing:
        raise ValueError(f"Missing required history fields: {missing}")

    cleaned = dict(config)
    cleaned["success_count"] = int(cleaned["success_count"])
    cleaned["total_count"] = int(cleaned["total_count"])
    cleaned["consecutive_failures"] = int(cleaned["consecutive_failures"])
    cleaned["last_seen_rounds_ago"] = int(cleaned["last_seen_rounds_ago"])
    cleaned["consistency_score"] = float(cleaned["consistency_score"])

    if cleaned["total_count"] < 0:
        raise ValueError("total_count must be >= 0")
    if cleaned["success_count"] < 0:
        raise ValueError("success_count must be >= 0")
    if cleaned["success_count"] > cleaned["total_count"]:
        raise ValueError("success_count cannot exceed total_count")
    if cleaned["consecutive_failures"] < 0:
        raise ValueError("consecutive_failures must be >= 0")
    if not 0.0 <= cleaned["consistency_score"] <= 1.0:
        raise ValueError("consistency_score must be in [0, 1]")

    return cleaned


def build_history_from_config(
    participant_id: str,
    scenario: str,
    config: Dict[str, Any],
    *,
    seed: int = 42,
) -> ReliabilityInput:
    """Create a ReliabilityInput from deterministic prototype metadata.

    This converter intentionally maps prototype metadata into the exact existing
    ReliabilityInput schema without implying it was measured from live telemetry.
    """

    validated = _validate_history_config(config)
    return ReliabilityInput(
        last_seen_rounds_ago=validated["last_seen_rounds_ago"],
        success_count=validated["success_count"],
        total_count=validated["total_count"],
        consecutive_failures=validated["consecutive_failures"],
        consistency_score=validated["consistency_score"],
    )


def simulate_participant_history(
    participant_id: str,
    scenario: str,
    *,
    seed: int = 42,
    custom_config: Optional[Dict[str, Any]] = None,
) -> ParticipantHistoryProfile:
    """Return deterministic metadata representing a prototype federated history.

    Important: these values are explicitly simulated metadata for prototype-only
    experimentation. They are not raw, real-world measurements from production.
    """

    scenario_key = scenario if scenario in SCENARIO_LIBRARY else "reliable_participant"
    base_config = dict(SCENARIO_LIBRARY[scenario_key])
    if custom_config is not None:
        base_config.update(custom_config)

    rng = np.random.RandomState(seed)
    jitter = float(rng.uniform(-0.05, 0.05, size=1)[0])
    config = dict(base_config)
    config["consistency_score"] = float(np.clip(
        config["consistency_score"] + jitter,
        0.0,
        1.0,
    ))

    reliability_input = build_history_from_config(
        participant_id,
        scenario_key,
        config,
        seed=seed,
    )
    return ParticipantHistoryProfile(
        participant_id=participant_id,
        scenario=scenario_key,
        source=PROTOTYPE_HISTORY_SOURCE,
        reliability_input=reliability_input,
        seed=seed,
    )
