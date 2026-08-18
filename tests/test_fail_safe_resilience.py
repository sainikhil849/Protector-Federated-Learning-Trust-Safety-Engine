import numpy as np

from src.scoring_engines import TrustInput, TrustScorer


def test_trust_engine_exception_blocks_safely():
    scorer = TrustScorer()
    data = TrustInput(
        dqs=85,
        dhs=90,
        uss=88,
        rs=82,
        ps=80,
        confidence=80,
        hard_safety_passed=True,
        policy_approved=True,
    )

    result = scorer.safe_score(
        data,
        failure_component="trust_engine",
        failure_type="exception",
        failure_details="RuntimeError: Trust engine crashed",
        independent_evidence=0,
    )

    assert result.system_mode == "SAFE_MODE"
    assert result.fallback_activated is True
    assert result.decision == "BLOCK"
    assert result.decision != "ALLOW"


def test_database_failure_with_enough_evidence_degrades():
    scorer = TrustScorer()
    data = TrustInput(
        dqs=85,
        dhs=90,
        uss=88,
        rs=80,
        ps=75,
        confidence=60,
        hard_safety_passed=True,
        policy_approved=True,
    )

    result = scorer.safe_score(
        data,
        failure_component="database",
        failure_type="database_unavailable",
        failure_details="History database unavailable",
        independent_evidence=4,
    )

    assert result.system_mode == "DEGRADED"
    assert result.fallback_activated is True
    assert result.decision in {"REVIEW", "RESTRICT"}
    assert result.decision != "ALLOW"


def test_drift_failure_without_sufficient_evidence_blocks():
    scorer = TrustScorer()
    data = TrustInput(
        dqs=40,
        dhs=np.nan,
        uss=45,
        rs=50,
        ps=55,
        confidence=35,
        hard_safety_passed=True,
        policy_approved=True,
    )

    result = scorer.safe_score(
        data,
        failure_component="drift_engine",
        failure_type="NaN",
        failure_details="DHS produced NaN",
        independent_evidence=2,
    )

    assert result.system_mode == "SAFE_MODE"
    assert result.fallback_activated is True
    assert result.decision == "BLOCK"


def test_performance_failure_with_sufficient_evidence_reduces_to_review():
    scorer = TrustScorer()
    data = TrustInput(
        dqs=75,
        dhs=78,
        uss=70,
        rs=72,
        ps=np.inf,
        confidence=68,
        hard_safety_passed=True,
        policy_approved=True,
    )

    result = scorer.safe_score(
        data,
        failure_component="performance_engine",
        failure_type="Infinity",
        failure_details="PS became Infinity",
        independent_evidence=3,
    )

    assert result.system_mode in {"DEGRADED", "SAFE_MODE"}
    assert result.decision in {"REVIEW", "RESTRICT", "BLOCK"}
    assert result.decision != "ALLOW"


def test_missing_historical_data_does_not_allow():
    scorer = TrustScorer()
    data = TrustInput(
        dqs=70,
        dhs=72,
        uss=68,
        rs=0,
        ps=65,
        confidence=50,
        hard_safety_passed=True,
        policy_approved=True,
    )

    result = scorer.safe_score(
        data,
        failure_component="history",
        failure_type="missing_historical_data",
        failure_details="No historical reliability data",
        independent_evidence=2,
    )

    assert result.system_mode == "SAFE_MODE"
    assert result.decision in {"RESTRICT", "BLOCK", "REVIEW"}
    assert result.decision != "ALLOW"


def test_unknown_state_uses_review_fallback():
    scorer = TrustScorer()
    data = TrustInput(
        dqs=78,
        dhs=82,
        uss=76,
        rs=74,
        ps=73,
        confidence=72,
        hard_safety_passed=True,
        policy_approved=True,
    )

    result = scorer.safe_score(
        data,
        failure_component="state_machine",
        failure_type="unknown_state",
        failure_details="State machine is in unknown state",
        independent_evidence=1,
    )

    assert result.system_mode == "SAFE_MODE"
    assert result.decision == "REVIEW"
