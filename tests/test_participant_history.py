import pytest

from src.participant_history import (
    SCENARIO_LIBRARY,
    ParticipantHistoryProfile,
    build_history_from_config,
    simulate_participant_history,
)
from src.scoring_engines import ReliabilityInput, ReliabilityScorer


@pytest.mark.parametrize(
    "scenario",
    [
        "reliable_participant",
        "unreliable_participant",
        "new_participant_limited_history",
        "repeated_failures",
        "stale_participant",
    ],
)
def test_scenario_library_contains_all_requested_scenarios(scenario):
    assert scenario in SCENARIO_LIBRARY


def test_build_history_from_config_maps_to_reliability_input():
    config = {
        "success_count": 15,
        "total_count": 18,
        "consecutive_failures": 1,
        "last_seen_rounds_ago": 2,
        "consistency_score": 0.88,
    }

    history = build_history_from_config("ORG-099", "prototype_config", config)

    assert isinstance(history, ReliabilityInput)
    assert history.success_count == 15
    assert history.total_count == 18
    assert history.consecutive_failures == 1
    assert history.last_seen_rounds_ago == 2
    assert history.consistency_score == 0.88


def test_reliable_scenario_is_good_quality():
    history = simulate_participant_history("ORG-001", "reliable_participant", seed=11)

    assert isinstance(history, ParticipantHistoryProfile)
    assert history.source == "simulated prototype metadata"
    assert history.reliability_input.success_count >= history.reliability_input.total_count * 0.8
    assert history.reliability_input.consecutive_failures == 0
    assert history.reliability_input.last_seen_rounds_ago <= 2

    score = ReliabilityScorer().score(history.reliability_input)
    assert score.quarantine_level in {"ok", "warning"}


def test_unreliable_scenario_flags_warning():
    history = simulate_participant_history("ORG-002", "unreliable_participant", seed=11)
    score = ReliabilityScorer().score(history.reliability_input)

    assert history.reliability_input.total_count > history.reliability_input.success_count
    assert history.reliability_input.consecutive_failures >= 1
    assert score.quarantine_level in {"warning", "quarantine"}


def test_new_participant_limited_history_stays_small():
    history = simulate_participant_history("ORG-003", "new_participant_limited_history", seed=11)

    assert history.reliability_input.total_count <= 3
    assert history.reliability_input.last_seen_rounds_ago == 0
    assert history.reliability_input.success_count >= 0
    assert history.reliability_input.consistency_score >= 0.5


def test_repeated_failures_are_severe():
    history = simulate_participant_history("ORG-004", "repeated_failures", seed=11)

    assert history.reliability_input.consecutive_failures >= 4
    assert history.reliability_input.total_count >= history.reliability_input.success_count
    assert ReliabilityScorer().score(history.reliability_input).quarantine_level == "quarantine"


def test_stale_participant_is_old_and_inactive():
    history = simulate_participant_history("ORG-005", "stale_participant", seed=11)

    assert history.reliability_input.last_seen_rounds_ago >= 6
    assert history.reliability_input.success_count <= history.reliability_input.total_count
    assert ReliabilityScorer().score(history.reliability_input).quarantine_level in {"warning", "quarantine"}
