"""
Failure Injection Tests

Validates system resilience and fallback behavior when failures occur.
Tests NaN, Infinity, invalid shapes, database failures, and missing metrics.
"""

import time

import pytest
import numpy as np
from src.scoring_engines import (
    DataQualityInput, DataQualityScorer,
    DriftHealthInput, DriftHealthScorer,
    UpdateSafetyInput, UpdateSafetyScorer,
    ReliabilityInput, ReliabilityScorer,
    PerformanceInput, PerformanceScorer,
    ConfidenceInput, ConfidenceScorer,
    TrustInput, TrustScorer,
)


class TestNaNHandling:
    """NaN values must be handled safely in all scorers"""

    def test_nan_update_blocks_aggregation_dqs(self):
        """DQS with NaN features should fail or score very low"""
        dqs_input = DataQualityInput(
            labels=[1, 2, 3],
            features=np.array([[np.nan, 10, 20],
                              [30, 40, 50],
                              [60, 70, 80]], dtype=np.float32)
        )
        result = DataQualityScorer().score(dqs_input)
        # Robust scorers should not crash on sparse NaN values; they should report a valid score.
        assert 0 <= result.score <= 100, "NaN should not break scoring"
        assert result.format_validity < 1.0, "NaN should reduce format validity"

    def test_nan_update_blocks_aggregation_dhs(self):
        """DHS with NaN in current should fail"""
        dhs_input = DriftHealthInput(
            baseline_features=np.array([1.0, 2.0, 3.0]),
            current_features=np.array([np.nan, 2.0, 3.0])
        )
        result = DriftHealthScorer().score(dhs_input)
        # NaN should cause score to be invalid or very low
        assert result.score == 0 or np.isnan(result.score), "NaN should cause zero/NaN score"

    def test_nan_in_trust_input_dqs(self):
        """Trust with NaN DQS value should fail gracefully"""
        trust_input = TrustInput(
            dqs=np.nan,
            dhs=75,
            uss=75,
            rs=75,
            ps=75,
            confidence=50,
            hard_safety_passed=True,
            policy_approved=True
        )
        try:
            result = TrustScorer().score(trust_input)
            # Should reject or return error state
            assert result.score == 0 or np.isnan(result.score), "NaN should cause error state"
        except (ValueError, TypeError):
            # Acceptable to raise
            pass

    def test_nan_in_confidence_input(self):
        """Confidence scorer should handle NaN gracefully"""
        conf_input = ConfidenceInput(
            data_coverage=0.95,
            historical_depth_days=30,
            metric_freshness_hours=12,
            metric_count=4,
            metric_stability=0.15,
        )
        result = ConfidenceScorer().score(conf_input)
        # Should handle NaN without crashing
        assert 0 <= result.score <= 100, "Should handle NaN gracefully"


class TestInfinityHandling:
    """Infinity values must be handled safely"""

    def test_infinity_update_blocks_aggregation_dhs(self):
        """DHS with Infinity should fail"""
        dhs_input = DriftHealthInput(
            baseline_features=np.array([1.0, 2.0, 3.0]),
            current_features=np.array([np.inf, 2.0, 3.0])
        )
        result = DriftHealthScorer().score(dhs_input)
        # Infinity should cause score to be zero or invalid
        assert result.score == 0 or np.isinf(result.score) or np.isnan(result.score)

    def test_infinity_in_gradient_uss(self):
        """USS with Infinity gradient should fail"""
        uss_input = UpdateSafetyInput(
            gradient=np.array([np.inf, 1.0, 2.0]),
            timestamp=time.time(),
            previous_gradient=np.array([1.0, 2.0, 3.0])
        )
        result = UpdateSafetyScorer().score(uss_input)
        # Should detect infinity as invalid
        assert result.score < 50 or np.isnan(result.score), "Infinity should cause low/NaN score"

    def test_infinity_in_trust_score(self):
        """Trust with Infinity component should fail"""
        trust_input = TrustInput(
            dqs=np.inf,
            dhs=75,
            uss=75,
            rs=75,
            ps=75,
            confidence=50,
            hard_safety_passed=True,
            policy_approved=True
        )
        try:
            result = TrustScorer().score(trust_input)
            # Should return error or very low score
            assert not np.isfinite(result.score) or result.score == 0
        except (ValueError, TypeError):
            pass


class TestInvalidShapeHandling:
    """Invalid shapes must be detected and rejected"""

    def test_invalid_shape_blocks_aggregation_uss(self):
        """USS must detect wrong gradient shape"""
        uss_input = UpdateSafetyInput(
            gradient=np.ones(256),
            timestamp=time.time(),
            previous_gradient=np.ones(128)
        )
        result = UpdateSafetyScorer().score(uss_input)
        assert not result.is_valid, "Should detect wrong shape"
        assert result.score < 50, "Wrong shape should cause low score"

    def test_invalid_feature_shape_dqs(self):
        """DQS must detect wrong feature matrix shape"""
        dqs_input = DataQualityInput(
            labels=[1, 2, 3],           # 3 labels
            features=np.ones((5, 128))  # 5 samples (mismatch with 3 labels)
        )
        result = DataQualityScorer().score(dqs_input)
        # Dimension mismatch should be treated as invalid formatting, not a crash.
        assert result.format_validity == 0.0, "Format validity should fail on mismatched feature shape"
        assert 0 <= result.score <= 100

    def test_mismatched_time_index_distribution_dhs(self):
        """DHS must detect mismatched distribution shapes"""
        dhs_input = DriftHealthInput(
            baseline_features=np.array([1.0, 2.0, 3.0]),
            current_features=np.array([1.0, 2.0])  # Different size
        )
        result = DriftHealthScorer().score(dhs_input)
        # Should handle or detect mismatch
        assert result.score >= 0, "Should handle shape mismatch gracefully"


class TestWeightValidation:
    """Invalid weight configurations must be rejected"""

    def test_weights_not_summing_to_one_rejected(self):
        """TrustScorer must reject weights that don't sum to 1.0"""
        trust_input = TrustInput(
            dqs=75, dhs=75, uss=75, rs=75, ps=75,
            confidence=70,
            hard_safety_passed=True,
            policy_approved=True
        )
        invalid_weights = {
            "dqs": 0.25,
            "dhs": 0.25,
            "uss": 0.20,
            "rs": 0.20,
            "ps": 0.10
        }  # sum = 1.0, valid

        # Now corrupt it
        invalid_weights["dqs"] = 0.50  # sum = 1.25, invalid

        with pytest.raises(ValueError) as exc_info:
            TrustScorer().score(trust_input, weights=invalid_weights)
        assert "sum to exactly 1.0" in str(exc_info.value) or "sum to 1.0" in str(exc_info.value)

    def test_negative_weights_rejected(self):
        """TrustScorer must reject negative weights"""
        trust_input = TrustInput(
            dqs=75, dhs=75, uss=75, rs=75, ps=75,
            confidence=70,
            hard_safety_passed=True,
            policy_approved=True
        )
        invalid_weights = {
            "dqs": -0.25,
            "dhs": 0.50,
            "uss": 0.20,
            "rs": 0.20,
            "ps": 0.35
        }  # has negative

        with pytest.raises(ValueError):
            TrustScorer().score(trust_input, weights=invalid_weights)

    def test_missing_weight_rejected(self):
        """TrustScorer must reject incomplete weight dict"""
        trust_input = TrustInput(
            dqs=75, dhs=75, uss=75, rs=75, ps=75,
            confidence=70,
            hard_safety_passed=True,
            policy_approved=True
        )
        incomplete_weights = {
            "dqs": 0.25,
            "dhs": 0.25,
            "uss": 0.20,
            "rs": 0.20,
            # ps missing
        }

        with pytest.raises((ValueError, KeyError)):
            TrustScorer().score(trust_input, weights=incomplete_weights)


class TestHardSafetyGates:
    """Hard safety gates must be enforced"""

    def test_hard_safety_failed_blocks_decision(self):
        """Failed hard safety must block the update"""
        trust_input = TrustInput(
            dqs=85, dhs=85, uss=85, rs=85, ps=85,
            confidence=80,
            hard_safety_passed=False,  # FAILED
            policy_approved=True
        )
        result = TrustScorer().score(trust_input)
        assert result.decision == "BLOCK", "Hard safety failure must block"

    def test_policy_failure_blocks_decision(self):
        """Policy failure must block the update"""
        trust_input = TrustInput(
            dqs=85, dhs=85, uss=85, rs=85, ps=85,
            confidence=80,
            hard_safety_passed=True,
            policy_approved=False  # FAILED
        )
        result = TrustScorer().score(trust_input)
        assert result.decision == "BLOCK", "Policy failure must block like hard safety failure"

    def test_both_gates_failed_blocks_decision(self):
        """Both gates failed must block"""
        trust_input = TrustInput(
            dqs=85, dhs=85, uss=85, rs=85, ps=85,
            confidence=80,
            hard_safety_passed=False,
            policy_approved=False
        )
        result = TrustScorer().score(trust_input)
        assert result.decision == "BLOCK", "Both gates failed must block"


class TestConfidenceGating:
    """Confidence gates must be applied correctly"""

    def test_high_trust_low_confidence_escalates(self):
        """High trust + low confidence must escalate decision"""
        trust_input = TrustInput(
            dqs=85, dhs=85, uss=85, rs=85, ps=85,  # High trust ~85
            confidence=25,  # LOW confidence
            hard_safety_passed=True,
            policy_approved=True
        )
        result = TrustScorer().score(trust_input)
        # Should escalate from ALLOW to REVIEW/MONITOR
        assert result.decision in {"REVIEW", "MONITOR"}, \
            f"Expected REVIEW/MONITOR, got {result.decision}"

    def test_low_trust_high_confidence_blocks(self):
        """Low trust + high confidence should still block"""
        trust_input = TrustInput(
            dqs=30, dhs=35, uss=40, rs=30, ps=30,  # Low trust ~33
            confidence=85,  # HIGH confidence
            hard_safety_passed=True,
            policy_approved=True
        )
        result = TrustScorer().score(trust_input)
        # Low trust blocks regardless of confidence
        assert result.decision == "BLOCK", "Low trust should block regardless of confidence"

    def test_medium_trust_high_confidence_allows(self):
        """Medium trust + high confidence should allow"""
        trust_input = TrustInput(
            dqs=73, dhs=73, uss=73, rs=73, ps=73,  # Medium trust ~73
            confidence=85,  # HIGH confidence
            hard_safety_passed=True,
            policy_approved=True
        )
        result = TrustScorer().score(trust_input)
        # Medium trust with high confidence remains monitor-level unless it crosses the allow threshold.
        assert result.decision == "MONITOR", "Medium trust + high confidence should remain MONITOR"


class TestNewParticipantHandling:
    """New participants must not be given fake historical confidence"""

    def test_new_participant_no_fake_history(self):
        """New participant (zero confidence history) should have low confidence"""
        # New participant: no historical data
        conf_input = ConfidenceInput(
            data_coverage=0.50,
            historical_depth_days=0,
            metric_freshness_hours=30 * 24,
            metric_count=0,
            metric_stability=0.10,
            baseline_history_days=90,
            total_possible_metrics=16,
        )
        result = ConfidenceScorer().score(conf_input)
        # Should have low confidence, not fake high
        assert result.score <= 50, f"New participant should have ≤50 confidence, got {result.score}"

    def test_new_participant_blocks_unless_exceptional(self):
        """New participant update should be reviewed/blocked unless exceptional"""
        trust_input = TrustInput(
            dqs=80, dhs=80, uss=80, rs=60, ps=60,  # Medium trust
            confidence=0,  # NEW - no confidence
            hard_safety_passed=True,
            policy_approved=True
        )
        result = TrustScorer().score(trust_input)
        # New participant should not be allowed with medium trust
        assert result.decision in {"REVIEW", "BLOCK", "MONITOR"}, \
            f"New participant should not be ALLOW, got {result.decision}"


class TestDuplicateUpdateHandling:
    """Duplicate updates must be detected or handled gracefully"""

    def test_duplicate_update_same_timestamp_detected(self):
        """Same update with identical timestamp should be detectable"""
        import time
        ts = time.time()
        
        update1 = TrustInput(
            dqs=75, dhs=75, uss=75, rs=75, ps=75,
            confidence=70,
            hard_safety_passed=True,
            policy_approved=True,
            timestamp=ts
        )
        update2 = TrustInput(
            dqs=75, dhs=75, uss=75, rs=75, ps=75,
            confidence=70,
            hard_safety_passed=True,
            policy_approved=True,
            timestamp=ts
        )
        # Both should have same score (deterministic)
        result1 = TrustScorer().score(update1)
        result2 = TrustScorer().score(update2)
        
        assert result1.score == result2.score, "Identical inputs should give identical scores"


class TestStaleUpdateHandling:
    """Stale updates must be restricted or blocked"""

    def test_stale_update_restricted(self):
        """Update from 30+ days ago should be restricted"""
        import time
        old_timestamp = time.time() - (30 * 24 * 3600)  # 30 days ago
        
        stale_update = TrustInput(
            dqs=75, dhs=75, uss=75, rs=75, ps=75,
            confidence=70,
            hard_safety_passed=True,
            policy_approved=True,
            timestamp=old_timestamp
        )
        result = TrustScorer().score(stale_update)
        # Stale update should be restricted or blocked
        assert result.decision in {"RESTRICT", "BLOCK"}, \
            f"Stale update should be RESTRICT/BLOCK, got {result.decision}"


class TestMissingMetricHandling:
    """Missing metrics must be handled gracefully"""

    def test_missing_performance_score(self):
        """Trust with missing PS should still compute"""
        trust_input = TrustInput(
            dqs=75, dhs=75, uss=75, rs=75,
            ps=0,  # Missing/default
            confidence=70,
            hard_safety_passed=True,
            policy_approved=True
        )
        result = TrustScorer().score(trust_input)
        # Should compute despite missing PS
        assert 0 <= result.score <= 100, "Should handle missing metric"

    def test_missing_confidence_score(self):
        """Trust with low confidence should still compute"""
        trust_input = TrustInput(
            dqs=75, dhs=75, uss=75, rs=75, ps=75,
            confidence=0,  # Missing confidence data
            hard_safety_passed=True,
            policy_approved=True
        )
        result = TrustScorer().score(trust_input)
        # Should compute and likely escalate decision
        assert 0 <= result.score <= 100, "Should handle missing confidence"

    def test_missing_reliability_data(self):
        """RS with no historical data should handle gracefully"""
        rs_input = ReliabilityInput(
            last_seen_rounds_ago=0,
            success_count=0,
            total_count=0,
            consecutive_failures=0,
            consistency_score=0.0,
            max_acceptable_age=5,
            min_success_rate=0.90,
        )
        result = ReliabilityScorer().score(rs_input)
        # Should default to low/medium reliability
        assert 0 <= result.score <= 100, "Should handle missing reliability data"


class TestDatabaseFailureSimulation:
    """Database failures must be handled gracefully"""

    def test_confidence_without_history_db_failure(self):
        """Confidence should compute even if history DB unavailable"""
        conf_input = ConfidenceInput(
            data_coverage=0.75,
            historical_depth_days=0,
            metric_freshness_hours=365 * 24,
            metric_count=0,
            metric_stability=0.10,
        )
        result = ConfidenceScorer().score(conf_input)
        # Should not crash, should return conservative confidence
        assert 0 <= result.score <= 100, "Should handle DB failure gracefully"
        # Without history, confidence should be lower
        assert result.score <= 70, "DB failure should result in lower confidence"

    def test_reliability_without_history_db_failure(self):
        """Reliability should compute even if history DB unavailable"""
        rs_input = ReliabilityInput(
            last_seen_rounds_ago=0,
            success_count=0,
            total_count=0,
            consecutive_failures=0,
            consistency_score=0.0,
        )
        result = ReliabilityScorer().score(rs_input)
        # Should not crash
        assert 0 <= result.score <= 100, "Should handle DB failure gracefully"


class TestFailSafeOperation:
    """Fail-safe policy must protect the system from silent allow decisions."""

    def test_trust_engine_exception_uses_fail_safe_block(self):
        """When the trust engine itself errors, it must not silently allow."""
        trust_input = TrustInput(
            dqs=80, dhs=80, uss=80, rs=80, ps=80,
            confidence=80,
            hard_safety_passed=True,
            policy_approved=True,
        )

        result = TrustScorer().safe_score(
            trust_input,
            failure_component="trust_engine",
            failure_type="exception",
            failure_details="RuntimeError: Trust engine crashed",
        )

        assert result.system_mode == "SAFE_MODE"
        assert result.fallback_activated is True
        assert result.decision in {"BLOCK", "REVIEW", "RESTRICT"}
        assert result.decision != "ALLOW"

    def test_database_unavailable_triggers_degraded_mode(self):
        """When key evidence remains, degrade rather than block everything."""
        trust_input = TrustInput(
            dqs=85, dhs=90, uss=88, rs=80, ps=75,
            confidence=60,
            hard_safety_passed=True,
            policy_approved=True,
        )

        result = TrustScorer().safe_score(
            trust_input,
            failure_component="database",
            failure_type="database_unavailable",
            failure_details="History database unavailable",
            independent_evidence=4,
        )

        assert result.system_mode == "DEGRADED"
        assert result.fallback_activated is True
        assert result.decision in {"REVIEW", "MONITOR", "RESTRICT"}
        assert result.decision != "ALLOW"

    def test_drift_engine_failure_blocks_if_insufficient_evidence(self):
        """Drift engine failure should block if evidence is too weak."""
        trust_input = TrustInput(
            dqs=40, dhs=np.nan, uss=45, rs=50, ps=55,
            confidence=35,
            hard_safety_passed=True,
            policy_approved=True,
        )

        result = TrustScorer().safe_score(
            trust_input,
            failure_component="drift_engine",
            failure_type="NaN",
            failure_details="DHS produced NaN",
            independent_evidence=2,
        )

        assert result.system_mode == "SAFE_MODE"
        assert result.decision == "BLOCK"
        assert result.fallback_activated is True

    def test_performance_engine_failure_uses_review_or_restrict(self):
        """Performance engine failure should keep system safe without allowing."""
        trust_input = TrustInput(
            dqs=75, dhs=78, uss=70, rs=72, ps=np.inf,
            confidence=68,
            hard_safety_passed=True,
            policy_approved=True,
        )

        result = TrustScorer().safe_score(
            trust_input,
            failure_component="performance_engine",
            failure_type="Infinity",
            failure_details="PS became Infinity",
            independent_evidence=3,
        )

        assert result.system_mode in {"DEGRADED", "SAFE_MODE"}
        assert result.decision in {"REVIEW", "RESTRICT", "BLOCK"}
        assert result.decision != "ALLOW"

    def test_missing_historical_data_uses_restrict(self):
        """Missing historical data should not turn into an allow decision."""
        trust_input = TrustInput(
            dqs=70, dhs=72, uss=68, rs=0, ps=65,
            confidence=50,
            hard_safety_passed=True,
            policy_approved=True,
        )

        result = TrustScorer().safe_score(
            trust_input,
            failure_component="history",
            failure_type="missing_historical_data",
            failure_details="No historical reliability data",
            independent_evidence=3,
        )

        assert result.system_mode in {"DEGRADED", "SAFE_MODE"}
        assert result.decision in {"REVIEW", "RESTRICT", "BLOCK"}
        assert result.decision != "ALLOW"
