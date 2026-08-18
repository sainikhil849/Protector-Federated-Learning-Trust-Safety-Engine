"""Scenario injection helpers for prototype multi-round evaluation.

These helpers intentionally modify only the participant input conditions that are
used by the real scoring pipeline. They never rewrite the scoring formulas or
hardcode final trust scores.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np

from src.participant_simulator import ParticipantData

VALID_SCENARIOS = {
    "normal",
    "drift",
    "unreliable",
    "poor_performance",
    "unsafe_update",
    "mixed",
}


@dataclass
class ScenarioImpact:
    """Simple, prototype-only description of a scenario effect."""

    scenario: str
    round_number: int
    description: str
    feature_scale: float = 1.0
    noise_scale: float = 0.0
    feature_indices: Tuple[int, ...] = ()
    bias: float = 0.0


def _scenario_notes(scenario: str, round_number: int) -> str:
    if scenario == "normal":
        return "Regular participant behavior, no intentional drift or reliability issue."
    if scenario == "drift":
        return "Feature distribution shifted to simulate drift across rounds."
    if scenario == "unreliable":
        return "Participant reliability reduced through simulated missed participation and instability."
    if scenario == "poor_performance":
        return "Feature quality degraded to emulate weaker local model performance."
    if scenario == "unsafe_update":
        return "Update characteristics perturbed to stress the safety gate."
    if scenario == "mixed":
        return "Mixed participant conditions simulate a realistic but controlled operational scenario."
    return "Prototype scenario injection applied."


def apply_scenario_to_participant(
    participant: ParticipantData,
    *,
    scenario: str = "normal",
    round_number: int = 1,
    seed: int = 42,
) -> Tuple[ParticipantData, ScenarioImpact]:
    """Return a participant copy with scenario-conditioned feature changes.

    A scenario only influences the participant input conditions. The scoring engine
    and decision formulas remain unchanged.
    """
    scenario_name = scenario.lower() if isinstance(scenario, str) else "normal"
    if scenario_name not in VALID_SCENARIOS:
        scenario_name = "normal"

    rng = np.random.RandomState(seed + round_number * 13 + len(participant.participant_id))
    x = np.asarray(participant.X, dtype=float).copy()
    y = np.asarray(participant.y, dtype=int).copy()

    notes = _scenario_notes(scenario_name, round_number)

    if scenario_name == "normal":
        impact = ScenarioImpact(
            scenario=scenario_name,
            round_number=round_number,
            description=notes,
            feature_scale=1.0,
            noise_scale=0.0,
            feature_indices=tuple(range(min(x.shape[1], 4))),
            bias=0.0,
        )
        return participant, impact

    if scenario_name == "drift":
        feature_indices = tuple(range(min(x.shape[1], 4)))
        drift_pct = 0.08 + (round_number % 5) * 0.03
        x[:, feature_indices] = x[:, feature_indices] * (1.0 + drift_pct)
        impact = ScenarioImpact(
            scenario=scenario_name,
            round_number=round_number,
            description=notes,
            feature_scale=1.0 + drift_pct,
            noise_scale=0.02,
            feature_indices=feature_indices,
            bias=drift_pct,
        )
        return ParticipantData(
            participant_id=participant.participant_id,
            X=x,
            y=y,
            row_count=len(x),
            timestamp=participant.timestamp,
            metadata=participant.metadata,
        ), impact

    if scenario_name == "unreliable":
        x = x + rng.normal(0.0, 0.12, size=x.shape)
        feature_indices = tuple(range(min(x.shape[1], 3)))
        impact = ScenarioImpact(
            scenario=scenario_name,
            round_number=round_number,
            description=notes,
            feature_scale=1.0,
            noise_scale=0.12,
            feature_indices=feature_indices,
            bias=0.0,
        )
        return ParticipantData(
            participant_id=participant.participant_id,
            X=x,
            y=y,
            row_count=len(x),
            timestamp=participant.timestamp,
            metadata=participant.metadata,
        ), impact

    if scenario_name == "poor_performance":
        feature_indices = tuple(range(min(x.shape[1], 4)))
        x[:, feature_indices] = x[:, feature_indices] * 0.8
        x = x + rng.normal(0.0, 0.07, size=x.shape)
        impact = ScenarioImpact(
            scenario=scenario_name,
            round_number=round_number,
            description=notes,
            feature_scale=0.8,
            noise_scale=0.07,
            feature_indices=feature_indices,
            bias=-0.2,
        )
        return ParticipantData(
            participant_id=participant.participant_id,
            X=x,
            y=y,
            row_count=len(x),
            timestamp=participant.timestamp,
            metadata=participant.metadata,
        ), impact

    if scenario_name == "unsafe_update":
        x[:, : min(2, x.shape[1])] = x[:, : min(2, x.shape[1])] * 1.4
        x = x + rng.normal(0.0, 0.15, size=x.shape)
        impact = ScenarioImpact(
            scenario=scenario_name,
            round_number=round_number,
            description=notes,
            feature_scale=1.4,
            noise_scale=0.15,
            feature_indices=tuple(range(min(x.shape[1], 2))),
            bias=0.4,
        )
        return ParticipantData(
            participant_id=participant.participant_id,
            X=x,
            y=y,
            row_count=len(x),
            timestamp=participant.timestamp,
            metadata=participant.metadata,
        ), impact

    # mixed scenario combines two effects for a realistic but controlled stress case
    feature_indices = tuple(range(min(x.shape[1], 4)))
    x[:, feature_indices] = x[:, feature_indices] * (1.05 + 0.04 * (round_number % 3))
    x = x + rng.normal(0.0, 0.06, size=x.shape)
    impact = ScenarioImpact(
        scenario="mixed",
        round_number=round_number,
        description=notes,
        feature_scale=1.1,
        noise_scale=0.06,
        feature_indices=feature_indices,
        bias=0.1,
    )
    return ParticipantData(
        participant_id=participant.participant_id,
        X=x,
        y=y,
        row_count=len(x),
        timestamp=participant.timestamp,
        metadata=participant.metadata,
    ), impact


def apply_scenario_to_dataset(
    participant: ParticipantData,
    *,
    scenario: str = "normal",
    round_number: int = 1,
    seed: int = 42,
) -> Tuple[ParticipantData, ScenarioImpact]:
    """Compatibility wrapper for scenario injection semantics."""
    return apply_scenario_to_participant(
        participant,
        scenario=scenario,
        round_number=round_number,
        seed=seed,
    )
