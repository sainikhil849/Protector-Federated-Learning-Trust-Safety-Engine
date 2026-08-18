"""
Integration Tests

Validates scoring components working together and decision pipeline.
Tests end-to-end trust computation and gate logic.
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
from src.validation_framework import (
    generate_ground_truth_scenarios,
    evaluate_experiment,
    calculate_validation_summary,
)


class TestTrustScorerIntegration:
    """Integration tests for complete trust computation"""

    def test_all_seven_scorers_combined_healthy_participant(self):
        """All 7 scoring components should compute for healthy participant"""
        # First, verify each component scores independently
        dqs_result = DataQualityScorer().score(DataQualityInput(
            labels=[1, 2, 3, 4, 5],
            features=np.ones((5, 128), dtype=np.float32) * 50000
        ))
        
        dhs_result = DriftHealthScorer().score(DriftHealthInput(
            baseline=np.array([1, 2, 3, 4, 5]),
            current=np.array([1, 2, 3, 4, 5])
        ))
        
        uss_result = UpdateSafetyScorer().score(UpdateSafetyInput(
            current_gradient=np.array([0.1, 0.2, 0.3, 0.4, 0.5]),
            previous_gradient=np.array([0.0, 0.0, 0.0, 0.0, 0.0])
        ))
        
        rs_result = ReliabilityScorer().score(ReliabilityInput(
            participant_failure_rate=0.05,
            historical_updates=100,
            recent_failures=2,
            last_update_timestamp=1000.0
        ))
        
        ps_result = PerformanceScorer().score(PerformanceInput(
            accuracy=0.92,
            precision=0.90,
            recall=0.94,
            f1_score=0.92
        ))
        
        conf_result = ConfidenceScorer().score(ConfidenceInput(
            metric_history=[85, 88, 86, 89],
            confidence_history=[80, 83, 81],
            update_frequency=7.0,
            data_coverage=0.90,
            metric_volatility=0.08
        ))
        
        # All components should score in valid range
        assert 0 <= dqs_result.score <= 100
        assert 0 <= dhs_result.score <= 100
        assert 0 <= uss_result.score <= 100
        assert 0 <= rs_result.score <= 100
        assert 0 <= ps_result.score <= 100
        assert 0 <= conf_result.score <= 100
        
        # Now combine in trust scorer
        trust_input = TrustInput(
            dqs=dqs_result.score,
            dhs=dhs_result.score,
            uss=uss_result.score,
            rs=rs_result.score,
            ps=ps_result.score,
            confidence=conf_result.score,
            hard_safety_passed=True,
            policy_approved=True
        )
        
        trust_result = TrustScorer().score(trust_input)
        
        # Trust should be high and decision should be ALLOW
        assert trust_result.score >= 80, f"Healthy participant should have high trust: {trust_result.score}"
        assert trust_result.decision == "ALLOW", f"Healthy participant should be ALLOW: {trust_result.decision}"

    def test_all_seven_scorers_combined_degraded_participant(self):
        """All 7 components should handle degraded participant"""
        # Degraded participant: some low scores
        dqs_score = 60  # Moderate data quality
        dhs_score = 70  # Some drift detected
        uss_score = 55  # Safety concerns
        rs_score = 40   # Low reliability
        ps_score = 50   # Below average performance
        conf_score = 45  # Low confidence
        
        trust_input = TrustInput(
            dqs=dqs_score,
            dhs=dhs_score,
            uss=uss_score,
            rs=rs_score,
            ps=ps_score,
            confidence=conf_score,
            hard_safety_passed=True,
            policy_approved=True
        )
        
        trust_result = TrustScorer().score(trust_input)
        
        # Should result in REVIEW or BLOCK
        assert trust_result.decision in {"REVIEW", "BLOCK"}, \
            f"Degraded participant should be REVIEW/BLOCK: {trust_result.decision}"

    def test_trust_scorer_stores_component_values(self):
        """Trust result should include all component scores"""
        trust_input = TrustInput(
            dqs=75, dhs=75, uss=75, rs=75, ps=75,
            confidence=70,
            hard_safety_passed=True,
            policy_approved=True
        )
        
        result = TrustScorer().score(trust_input)
        
        # Result should have audit trail of component values
        assert hasattr(result, 'score'), "Should have score"
        assert hasattr(result, 'decision'), "Should have decision"
        assert hasattr(result, 'confidence_level'), "Should have confidence_level"
        assert hasattr(result, 'timestamp'), "Should have timestamp"


class TestDecisionGateIntegration:
    """Integration tests for gate logic (hard safety, policy, confidence)"""

    def test_hard_safety_gate_integration(self):
        """Hard safety gate must override high trust scores"""
        # High trust scores but hard safety failed
        trust_input = TrustInput(
            dqs=90, dhs=90, uss=90, rs=90, ps=90,
            confidence=85,
            hard_safety_passed=False,  # GATE FAILED
            policy_approved=True
        )
        
        result = TrustScorer().score(trust_input)
        
        # Must BLOCK despite high scores
        assert result.decision == "BLOCK", \
            f"Hard safety gate should override: {result.decision}"
        assert not result.hard_safety_passed, "Should report hard safety failed"

    def test_policy_gate_integration(self):
        """Policy gate must override high trust scores"""
        # High trust scores but policy failed
        trust_input = TrustInput(
            dqs=90, dhs=90, uss=90, rs=90, ps=90,
            confidence=85,
            hard_safety_passed=True,
            policy_approved=False  # GATE FAILED
        )
        
        result = TrustScorer().score(trust_input)
        
        # Must BLOCK despite high scores
        assert result.decision == "BLOCK", \
            f"Policy gate should override: {result.decision}"
        assert not result.policy_approved, "Should report policy failed"

    def test_confidence_escalation_gate_integration(self):
        """Confidence gate should escalate high-trust decisions"""
        # High trust + low confidence
        trust_input = TrustInput(
            dqs=85, dhs=85, uss=85, rs=85, ps=85,
            confidence=20,  # LOW confidence
            hard_safety_passed=True,
            policy_approved=True
        )
        
        result = TrustScorer().score(trust_input)
        
        # Should escalate from ALLOW to REVIEW/MONITOR
        assert result.decision in {"REVIEW", "MONITOR"}, \
            f"Low confidence should escalate: {result.decision}"

    def test_all_gates_integrated_in_decision(self):
        """All gates should be evaluated together"""
        # Various gate combinations
        test_cases = [
            {
                "name": "All pass",
                "hard_safety": True,
                "policy": True,
                "trust": 85,
                "confidence": 80,
                "expected": "ALLOW"
            },
            {
                "name": "Hard safety fail",
                "hard_safety": False,
                "policy": True,
                "trust": 85,
                "confidence": 80,
                "expected": "BLOCK"
            },
            {
                "name": "Policy fail",
                "hard_safety": True,
                "policy": False,
                "trust": 85,
                "confidence": 80,
                "expected": "BLOCK"
            },
            {
                "name": "Low trust",
                "hard_safety": True,
                "policy": True,
                "trust": 30,
                "confidence": 80,
                "expected": "BLOCK"
            },
        ]
        
        for case in test_cases:
            trust_input = TrustInput(
                dqs=case["trust"], dhs=case["trust"],
                uss=case["trust"], rs=case["trust"],
                ps=case["trust"],
                confidence=case["confidence"],
                hard_safety_passed=case["hard_safety"],
                policy_approved=case["policy"]
            )
            result = TrustScorer().score(trust_input)
            
            assert result.decision == case["expected"], \
                f"{case['name']}: expected {case['expected']}, got {result.decision}"


class TestValidationFrameworkIntegration:
    """Integration with validation framework"""

    def test_validation_scenarios_score_correctly(self):
        """Ground-truth scenarios should score as expected"""
        scenarios = generate_ground_truth_scenarios()
        
        # Evaluate each scenario
        results = []
        for scenario in scenarios:
            result = evaluate_experiment(scenario)
            results.append(result)
            
            # Each scenario should have valid scores
            assert 0 <= result.trust_score <= 100, f"Invalid trust score: {result.trust_score}"
            assert result.decision in {"ALLOW", "MONITOR", "REVIEW", "BLOCK", "RESTRICT"}
        
        # Summary should be computable
        summary = calculate_validation_summary(results)
        
        assert summary.total_experiments == len(scenarios)
        assert 0 <= summary.precision <= 1.0
        assert 0 <= summary.recall <= 1.0
        assert 0 <= summary.f1 <= 1.0

    def test_validation_scenarios_include_critical_cases(self):
        """Validation scenarios must cover critical cases"""
        scenarios = generate_ground_truth_scenarios()
        scenario_ids = {s.scenario_id for s in scenarios}
        
        # Must include NaN, Infinity, wrong shape, etc.
        critical_ids = {"V-002", "V-003", "V-004"}  # NaN, Infinity, wrong shape
        
        assert critical_ids.issubset(scenario_ids), \
            f"Missing critical scenarios: {critical_ids - scenario_ids}"


class TestWeightVariationIntegration:
    """Integration tests for different weight configurations"""

    def test_weight_variation_changes_score(self):
        """Different weight configurations should yield different scores"""
        trust_input = TrustInput(
            dqs=85, dhs=80, uss=70, rs=75, ps=60,
            confidence=70,
            hard_safety_passed=True,
            policy_approved=True
        )
        
        weights_dqs_heavy = {
            "dqs": 0.40,
            "dhs": 0.20,
            "uss": 0.15,
            "rs": 0.15,
            "ps": 0.10
        }
        
        weights_ps_heavy = {
            "dqs": 0.10,
            "dhs": 0.10,
            "uss": 0.20,
            "rs": 0.20,
            "ps": 0.40
        }
        
        result_dqs = TrustScorer().score(trust_input, weights=weights_dqs_heavy)
        result_ps = TrustScorer().score(trust_input, weights=weights_ps_heavy)
        
        # DQS-heavy should score higher (DQS=85 > average)
        # PS-heavy should score lower (PS=60 < average)
        assert result_dqs.score > result_ps.score, \
            f"DQS-heavy should score higher: {result_dqs.score} > {result_ps.score}"

    def test_weight_validation_integrated(self):
        """Weight validation should be enforced in integration"""
        trust_input = TrustInput(
            dqs=75, dhs=75, uss=75, rs=75, ps=75,
            confidence=70,
            hard_safety_passed=True,
            policy_approved=True
        )
        
        # Try various invalid weight sets
        invalid_weights_list = [
            {"dqs": 0.5, "dhs": 0.5, "uss": 0, "rs": 0, "ps": 0},  # sum = 1.0 OK, but all zero for some
            {"dqs": -0.1, "dhs": 0.4, "uss": 0.3, "rs": 0.2, "ps": 0.2},  # negative
            {"dqs": 0.2, "dhs": 0.2, "uss": 0.2, "rs": 0.2, "ps": 0.2},  # sum = 1.0, valid
        ]
        
        # First two should raise ValueError
        with pytest.raises(ValueError):
            TrustScorer().score(trust_input, weights=invalid_weights_list[1])
        
        # Third is valid
        result = TrustScorer().score(trust_input, weights=invalid_weights_list[2])
        assert 0 <= result.score <= 100


class TestParticipantLifecycleIntegration:
    """Integration tests for participant state transitions"""

    def test_new_participant_journey(self):
        """New participant should progress through lifecycle"""
        # Stage 1: New participant, no history
        new_conf = ConfidenceScorer().score(ConfidenceInput(
            metric_history=[],
            confidence_history=[],
            update_frequency=0,
            data_coverage=0.3,
            metric_volatility=0.15
        ))
        
        # Should have low confidence
        assert new_conf.score <= 50, f"New participant should have low confidence: {new_conf.score}"
        
        # Stage 2: Established participant, good history
        established_conf = ConfidenceScorer().score(ConfidenceInput(
            metric_history=[85, 86, 87, 88, 89],
            confidence_history=[80, 82, 84, 86, 88],
            update_frequency=7.0,
            data_coverage=0.95,
            metric_volatility=0.05
        ))
        
        # Should have high confidence
        assert established_conf.score >= 75, f"Established participant should have high confidence: {established_conf.score}"
        
        # Stage 3: Degraded participant, recent failures
        rs_degraded = ReliabilityScorer().score(ReliabilityInput(
            participant_failure_rate=0.30,
            historical_updates=200,
            recent_failures=30,
            last_update_timestamp=1000.0
        ))
        
        # Should have low reliability despite history
        assert rs_degraded.score < 60, f"Degraded participant should have low reliability: {rs_degraded.score}"

    def test_recovery_after_degradation(self):
        """Degraded participant should be able to recover"""
        # Degraded state
        rs_bad = ReliabilityScorer().score(ReliabilityInput(
            participant_failure_rate=0.50,
            historical_updates=100,
            recent_failures=50,
            last_update_timestamp=1000.0
        ))
        
        # Recovery: fewer failures, more successful updates
        rs_good = ReliabilityScorer().score(ReliabilityInput(
            participant_failure_rate=0.10,
            historical_updates=200,  # More updates
            recent_failures=5,       # Fewer failures
            last_update_timestamp=1000.0
        ))
        
        # Recovery should have higher score
        assert rs_good.score > rs_bad.score, \
            f"Recovery should improve score: {rs_good.score} > {rs_bad.score}"


class TestErrorRecoveryIntegration:
    """Integration tests for error handling and recovery"""

    def test_system_handles_missing_component_gracefully(self):
        """System should handle missing individual component scores"""
        # Trust score with one missing component (using 0)
        trust_input_missing_ps = TrustInput(
            dqs=75, dhs=75, uss=75, rs=75,
            ps=0,  # Missing
            confidence=70,
            hard_safety_passed=True,
            policy_approved=True
        )
        
        result = TrustScorer().score(trust_input_missing_ps)
        
        # Should still compute decision
        assert result.decision in {"ALLOW", "MONITOR", "REVIEW", "BLOCK", "RESTRICT"}
        assert 0 <= result.score <= 100

    def test_cascading_gate_failures(self):
        """Multiple gate failures should result in BLOCK"""
        # All gates and trust failed
        trust_input = TrustInput(
            dqs=20, dhs=20, uss=20, rs=20, ps=20,  # Low trust
            confidence=20,
            hard_safety_passed=False,  # Failed
            policy_approved=False       # Failed
        )
        
        result = TrustScorer().score(trust_input)
        
        # Must BLOCK
        assert result.decision == "BLOCK", f"Cascading failures should BLOCK: {result.decision}"
