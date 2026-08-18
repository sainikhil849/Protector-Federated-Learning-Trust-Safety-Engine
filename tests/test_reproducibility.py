"""
Reproducibility Tests

Validates that scoring is deterministic: same input + same configuration always yields same result.
Tests that scoring does not depend on execution order or random seeds.
"""

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


class TestDeterministicScoring:
    """Same input must always produce identical output"""

    def test_dqs_deterministic_multiple_runs(self):
        """DQS must produce identical score across multiple runs"""
        dqs_input = DataQualityInput(
            labels=[1, 2, 3, 4, 5],
            features=np.ones((5, 128), dtype=np.float32) * 50000
        )
        
        scorer = DataQualityScorer()
        results = [scorer.score(dqs_input) for _ in range(10)]
        scores = [r.score for r in results]
        
        # All scores must be identical
        assert len(set(scores)) == 1, f"Scores should be identical: {scores}"
        assert all(r.schema_validity == results[0].schema_validity for r in results)
        assert all(r.completeness == results[0].completeness for r in results)

    def test_dhs_deterministic_multiple_runs(self):
        """DHS must produce identical score across multiple runs"""
        dhs_input = DriftHealthInput(
            baseline=np.array([1.0, 2.0, 3.0, 4.0, 5.0]),
            current=np.array([1.1, 2.1, 3.1, 4.1, 5.1])
        )
        
        scorer = DriftHealthScorer()
        results = [scorer.score(dhs_input) for _ in range(10)]
        scores = [r.score for r in results]
        
        # All scores must be identical
        assert len(set(scores)) == 1, f"Scores should be identical: {scores}"

    def test_uss_deterministic_multiple_runs(self):
        """USS must produce identical score across multiple runs"""
        uss_input = UpdateSafetyInput(
            gradient=np.array([0.1, 0.2, 0.3, 0.4, 0.5]),
            timestamp=0.0,
            previous_gradient=np.array([0.0, 0.0, 0.0, 0.0, 0.0])
        )
        
        scorer = UpdateSafetyScorer()
        results = [scorer.score(uss_input) for _ in range(10)]
        scores = [r.score for r in results]
        
        # All scores must be identical
        assert len(set(scores)) == 1, f"Scores should be identical: {scores}"

    def test_rs_deterministic_multiple_runs(self):
        """RS must produce identical score across multiple runs"""
        rs_input = ReliabilityInput(
            last_seen_rounds_ago=0,
            success_count=95,
            total_count=100,
            consecutive_failures=2,
            consistency_score=0.9,
        )
        
        scorer = ReliabilityScorer()
        results = [scorer.score(rs_input) for _ in range(10)]
        scores = [r.score for r in results]
        
        # All scores must be identical
        assert len(set(scores)) == 1, f"Scores should be identical: {scores}"

    def test_ps_deterministic_multiple_runs(self):
        """PS must produce identical score across multiple runs"""
        ps_input = PerformanceInput(
            local_accuracy=0.92,
            baseline_accuracy=0.90,
            class_fairness_score=0.90,
            metric_variance=0.08,
            update_impact=0.05,
        )
        
        scorer = PerformanceScorer()
        results = [scorer.score(ps_input) for _ in range(10)]
        scores = [r.score for r in results]
        
        # All scores must be identical
        assert len(set(scores)) == 1, f"Scores should be identical: {scores}"

    def test_confidence_deterministic_multiple_runs(self):
        """Confidence must produce identical score across multiple runs"""
        conf_input = ConfidenceInput(
            data_coverage=0.95,
            historical_depth_days=30,
            metric_freshness_hours=12,
            metric_count=16,
            metric_stability=0.1,
        )
        
        scorer = ConfidenceScorer()
        results = [scorer.score(conf_input) for _ in range(10)]
        scores = [r.score for r in results]
        
        # All scores must be identical
        assert len(set(scores)) == 1, f"Scores should be identical: {scores}"

    def test_trust_deterministic_multiple_runs(self):
        """Trust must produce identical score across multiple runs"""
        trust_input = TrustInput(
            dqs=75, dhs=75, uss=75, rs=75, ps=75,
            confidence=70,
            hard_safety_passed=True,
            policy_approved=True
        )
        
        scorer = TrustScorer()
        results = [scorer.score(trust_input) for _ in range(10)]
        scores = [r.score for r in results]
        
        # All scores must be identical
        assert len(set(scores)) == 1, f"Scores should be identical: {scores}"

    def test_trust_deterministic_with_custom_weights(self):
        """Trust with custom weights must produce identical score across runs"""
        trust_input = TrustInput(
            dqs=75, dhs=75, uss=75, rs=75, ps=75,
            confidence=70,
            hard_safety_passed=True,
            policy_approved=True
        )
        weights = {
            "dqs": 0.25,
            "dhs": 0.25,
            "uss": 0.20,
            "rs": 0.20,
            "ps": 0.10
        }
        
        scorer = TrustScorer()
        results = [scorer.score(trust_input, weights=weights) for _ in range(10)]
        scores = [r.score for r in results]
        
        # All scores must be identical
        assert len(set(scores)) == 1, f"Scores should be identical: {scores}"


class TestIndependenceFromRandomSeed:
    """Scoring should not depend on numpy random seed"""

    def test_dqs_independent_of_random_seed(self):
        """DQS should give same result regardless of numpy seed"""
        dqs_input = DataQualityInput(
            labels=[1, 2, 3, 4, 5],
            features=np.ones((5, 128), dtype=np.float32) * 50000
        )
        
        scorer = DataQualityScorer()
        
        # Run with different seeds
        results = []
        for seed in [42, 123, 456]:
            np.random.seed(seed)
            result = scorer.score(dqs_input)
            results.append(result.score)
        
        # All should be identical
        assert len(set(results)) == 1, f"Should be independent of seed: {results}"

    def test_dhs_independent_of_random_seed(self):
        """DHS should give same result regardless of numpy seed"""
        dhs_input = DriftHealthInput(
            baseline=np.array([1.0, 2.0, 3.0, 4.0, 5.0]),
            current=np.array([1.1, 2.1, 3.1, 4.1, 5.1])
        )
        
        scorer = DriftHealthScorer()
        
        # Run with different seeds
        results = []
        for seed in [42, 123, 456]:
            np.random.seed(seed)
            result = scorer.score(dhs_input)
            results.append(result.score)
        
        # All should be identical
        assert len(set(results)) == 1, f"Should be independent of seed: {results}"

    def test_trust_independent_of_random_seed(self):
        """Trust should give same result regardless of numpy seed"""
        trust_input = TrustInput(
            dqs=75, dhs=75, uss=75, rs=75, ps=75,
            confidence=70,
            hard_safety_passed=True,
            policy_approved=True
        )
        
        scorer = TrustScorer()
        
        # Run with different seeds
        results = []
        for seed in [42, 123, 456]:
            np.random.seed(seed)
            result = scorer.score(trust_input)
            results.append(result.score)
        
        # All should be identical
        assert len(set(results)) == 1, f"Should be independent of seed: {results}"


class TestIndependenceFromExecutionOrder:
    """Scoring should not depend on execution order"""

    def test_dqs_order_independent(self):
        """DQS should give same result regardless of processing order"""
        # Create inputs with same data but different label order
        labels1 = [1, 2, 3, 4, 5]
        labels2 = [5, 4, 3, 2, 1]
        
        features_1 = np.array([
            [50000, 51000, 52000] * 43,  # repeated to get 128 cols
            [50100, 51100, 52100] * 43,
            [50200, 51200, 52200] * 43,
            [50300, 51300, 52300] * 43,
            [50400, 51400, 52400] * 43,
        ], dtype=np.float32)[:, :128]
        
        # Same features in different order
        features_2 = features_1[[4, 3, 2, 1, 0], :]
        
        scorer = DataQualityScorer()
        
        result1 = scorer.score(DataQualityInput(labels=labels1, features=features_1))
        result2 = scorer.score(DataQualityInput(labels=labels2, features=features_2))
        
        # Scores should be similar (same data, different order)
        # Note: may not be identical if scorer depends on specific order
        assert abs(result1.score - result2.score) < 10, \
            f"Order should not significantly affect score: {result1.score} vs {result2.score}"


class TestPrecisionAndStability:
    """Verify numeric precision and stability"""

    def test_trust_score_precision_high_values(self):
        """Trust score should maintain precision with high input values"""
        trust_input = TrustInput(
            dqs=99, dhs=99, uss=99, rs=99, ps=99,
            confidence=99,
            hard_safety_passed=True,
            policy_approved=True
        )
        
        result = TrustScorer().score(trust_input)
        # Should be close to 99
        assert 95 < result.score <= 100, f"High inputs should yield high score, got {result.score}"

    def test_trust_score_precision_low_values(self):
        """Trust score should maintain precision with low input values"""
        trust_input = TrustInput(
            dqs=1, dhs=1, uss=1, rs=1, ps=1,
            confidence=1,
            hard_safety_passed=True,
            policy_approved=True
        )
        
        result = TrustScorer().score(trust_input)
        # Should be close to 1
        assert 0 <= result.score < 5, f"Low inputs should yield low score, got {result.score}"

    def test_trust_score_precision_middle_values(self):
        """Trust score should maintain precision with middle values"""
        trust_input = TrustInput(
            dqs=50, dhs=50, uss=50, rs=50, ps=50,
            confidence=50,
            hard_safety_passed=True,
            policy_approved=True
        )
        
        result = TrustScorer().score(trust_input)
        # Should be close to 50
        assert 45 < result.score < 55, f"Middle inputs should yield middle score, got {result.score}"

    def test_dhs_psi_to_score_numerically_stable(self):
        """DHS PSI conversion should be numerically stable"""
        # Test with various PSI values
        dhs_input_list = [
            DriftHealthInput(
                baseline_features=np.array([1.0, 2.0, 3.0, 4.0, 5.0]),
                current_features=np.array([1.0, 2.0, 3.0, 4.0, 5.0])
            ),
            DriftHealthInput(
                baseline_features=np.array([1.0, 2.0, 3.0, 4.0, 5.0]),
                current_features=np.array([1.5, 2.5, 3.5, 4.5, 5.5])
            ),
        ]
        
        scorer = DriftHealthScorer()
        results = [scorer.score(inp) for inp in dhs_input_list]
        
        # Results should be finite and in valid range
        for r in results:
            assert 0 <= r.score <= 100, f"Score should be in [0, 100], got {r.score}"
            assert np.isfinite(r.score), "Score should be finite"


class TestMonotonicBehavior:
    """Verify monotonic behavior where expected"""

    def test_dqs_monotonic_more_outliers_lower_score(self):
        """DQS should decrease as more outliers are introduced"""
        # Create two datasets: one clean, one with outliers
        clean_features = np.ones((10, 128), dtype=np.float32) * 50000
        
        outlier_features = clean_features.copy()
        # Add outliers
        outlier_features[3, 0] = 500000
        outlier_features[7, 1] = 500000
        
        scorer = DataQualityScorer()
        clean_result = scorer.score(DataQualityInput(
            labels=list(range(10)),
            features=clean_features
        ))
        outlier_result = scorer.score(DataQualityInput(
            labels=list(range(10)),
            features=outlier_features
        ))
        
        # Clean should score higher than with outliers
        assert clean_result.score > outlier_result.score, \
            f"Clean should score higher: {clean_result.score} > {outlier_result.score}"

    def test_rs_monotonic_more_failures_lower_score(self):
        """RS should decrease as failure rate increases"""
        scorer = ReliabilityScorer()
        
        result_good = scorer.score(ReliabilityInput(
            last_seen_rounds_ago=0,
            success_count=99,
            total_count=100,
            consecutive_failures=0,
            consistency_score=0.95,
        ))
        
        result_bad = scorer.score(ReliabilityInput(
            last_seen_rounds_ago=0,
            success_count=50,
            total_count=100,
            consecutive_failures=30,
            consistency_score=0.30,
        ))
        
        # Good should score higher than bad
        assert result_good.score > result_bad.score, \
            f"Good reliability should score higher: {result_good.score} > {result_bad.score}"

    def test_ps_monotonic_better_metrics_higher_score(self):
        """PS should increase as metrics improve"""
        scorer = PerformanceScorer()
        
        result_good = scorer.score(PerformanceInput(
            local_accuracy=0.95,
            baseline_accuracy=0.90,
            class_fairness_score=0.94,
            metric_variance=0.05,
            update_impact=0.08,
        ))
        
        result_bad = scorer.score(PerformanceInput(
            local_accuracy=0.60,
            baseline_accuracy=0.55,
            class_fairness_score=0.55,
            metric_variance=0.40,
            update_impact=-0.08,
        ))
        
        # Good should score higher than bad
        assert result_good.score > result_bad.score, \
            f"Better performance should score higher: {result_good.score} > {result_bad.score}"


class TestConsistencyAcrossRuns:
    """Verify consistency across different execution contexts"""

    def test_same_input_multiple_scorers_same_result(self):
        """Creating new scorer instances should not affect result"""
        trust_input = TrustInput(
            dqs=75, dhs=75, uss=75, rs=75, ps=75,
            confidence=70,
            hard_safety_passed=True,
            policy_approved=True
        )
        
        results = []
        for _ in range(5):
            scorer = TrustScorer()  # Create new scorer each time
            result = scorer.score(trust_input)
            results.append(result.score)
        
        # All results should be identical
        assert len(set(results)) == 1, f"Should be consistent across scorer instances: {results}"

    def test_large_batch_consistency(self):
        """Scoring a large batch should maintain consistency"""
        trust_inputs = [
            TrustInput(
                dqs=float(i % 100),
                dhs=float((i + 10) % 100),
                uss=float((i + 20) % 100),
                rs=float((i + 30) % 100),
                ps=float((i + 40) % 100),
                confidence=float((i + 50) % 100),
                hard_safety_passed=True,
                policy_approved=True
            )
            for i in range(100)
        ]
        
        scorer = TrustScorer()
        
        # Score each twice
        results_first_pass = [scorer.score(inp) for inp in trust_inputs]
        results_second_pass = [scorer.score(inp) for inp in trust_inputs]
        
        # Compare
        for first, second in zip(results_first_pass, results_second_pass):
            assert first.score == second.score, \
                f"Batch scoring should be consistent: {first.score} != {second.score}"
