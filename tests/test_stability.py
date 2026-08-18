"""
Stability Tests for Trust Score

Validates that small input changes produce proportional output changes.
Tests for unreasonable discontinuities and sharp decision flips.

Methodology:
1. Define baseline scenarios (healthy, degraded, marginal)
2. Perturb each input slightly (±1, ±5, ±10 percent depending on scale)
3. Measure score delta
4. Flag unreasonable discontinuities
5. Allow sharp decision changes only for hard safety
"""

import pytest
import numpy as np
from src.scoring_engines import TrustInput, TrustScorer


class TestStabilityBaseline:
    """Baseline scenarios for stability testing"""

    def test_healthy_baseline_score(self):
        """Healthy participant baseline"""
        trust_input = TrustInput(
            dqs=85, dhs=90, uss=85, rs=80, ps=75,
            confidence=85,
            hard_safety_passed=True,
            policy_approved=True
        )
        result = TrustScorer().score(trust_input)
        
        assert result.decision == "ALLOW", f"Healthy should ALLOW, got {result.decision}"
        assert result.score >= 75, f"Healthy should have high trust, got {result.score}"
        assert result.hard_safety_passed == True
        print(f"\nHealthy baseline: score={result.score:.1f}, decision={result.decision}")
        
        # Store for comparison
        self.healthy_baseline = result

    def test_degraded_baseline_score(self):
        """Degraded participant baseline"""
        trust_input = TrustInput(
            dqs=45, dhs=50, uss=40, rs=35, ps=40,
            confidence=40,
            hard_safety_passed=True,
            policy_approved=True
        )
        result = TrustScorer().score(trust_input)
        
        assert result.decision in {"BLOCK", "REVIEW"}, f"Degraded should BLOCK/REVIEW, got {result.decision}"
        assert result.score < 50, f"Degraded should have low trust, got {result.score}"
        print(f"Degraded baseline: score={result.score:.1f}, decision={result.decision}")
        
        self.degraded_baseline = result

    def test_marginal_baseline_score(self):
        """Marginal/boundary participant"""
        trust_input = TrustInput(
            dqs=70, dhs=72, uss=68, rs=70, ps=65,
            confidence=60,
            hard_safety_passed=True,
            policy_approved=True
        )
        result = TrustScorer().score(trust_input)
        
        assert result.decision in {"MONITOR", "REVIEW"}, f"Marginal should MONITOR/REVIEW, got {result.decision}"
        assert 40 <= result.score < 75, f"Marginal should be mid-range, got {result.score}"
        print(f"Marginal baseline: score={result.score:.1f}, decision={result.decision}")
        
        self.marginal_baseline = result


class TestStabilityDataQualitySmallChange:
    """Test sensitivity to small Data Quality Score changes"""

    def test_dqs_plus_1_percent_from_healthy(self):
        """Increase DQS by 1 point from healthy baseline"""
        baseline = TrustInput(
            dqs=85, dhs=90, uss=85, rs=80, ps=75,
            confidence=85,
            hard_safety_passed=True,
            policy_approved=True
        )
        perturbed = TrustInput(
            dqs=86, dhs=90, uss=85, rs=80, ps=75,  # +1
            confidence=85,
            hard_safety_passed=True,
            policy_approved=True
        )
        
        baseline_result = TrustScorer().score(baseline)
        perturbed_result = TrustScorer().score(perturbed)
        
        delta = perturbed_result.score - baseline_result.score
        print(f"\nDQS +1: {baseline_result.score:.2f} -> {perturbed_result.score:.2f}, delta={delta:.3f}")
        
        # Small change should produce proportional change
        # Weights: DQS=0.20, so +1 should add ~0.002 (±0.05 acceptable)
        assert abs(delta) < 0.5, f"DQS +1 caused excessive delta: {delta}"
        assert delta > 0, f"Increasing DQS should increase trust, got delta={delta}"
        assert perturbed_result.decision == baseline_result.decision, \
            "Small DQS change should not flip decision"

    def test_dqs_minus_5_from_healthy(self):
        """Decrease DQS by 5 points from healthy baseline"""
        baseline = TrustInput(
            dqs=85, dhs=90, uss=85, rs=80, ps=75,
            confidence=85,
            hard_safety_passed=True,
            policy_approved=True
        )
        perturbed = TrustInput(
            dqs=80, dhs=90, uss=85, rs=80, ps=75,  # -5
            confidence=85,
            hard_safety_passed=True,
            policy_approved=True
        )
        
        baseline_result = TrustScorer().score(baseline)
        perturbed_result = TrustScorer().score(perturbed)
        
        delta = perturbed_result.score - baseline_result.score
        print(f"DQS -5: {baseline_result.score:.2f} -> {perturbed_result.score:.2f}, delta={delta:.3f}")
        
        # -5 points should cause ~-1 trust (5 * 0.20)
        assert delta < 0, f"Decreasing DQS should decrease trust, got delta={delta}"
        assert abs(delta) < 2, f"DQS -5 caused excessive delta: {delta}"
        # Decision may stay ALLOW but should not flip to BLOCK
        assert perturbed_result.decision in {"ALLOW", "MONITOR"}, \
            f"DQS -5 should not cause sharp drop, got {perturbed_result.decision}"

    def test_dqs_plus_10_from_marginal(self):
        """Increase DQS by 10 points from marginal baseline"""
        baseline = TrustInput(
            dqs=70, dhs=72, uss=68, rs=70, ps=65,
            confidence=60,
            hard_safety_passed=True,
            policy_approved=True
        )
        perturbed = TrustInput(
            dqs=80, dhs=72, uss=68, rs=70, ps=65,  # +10
            confidence=60,
            hard_safety_passed=True,
            policy_approved=True
        )
        
        baseline_result = TrustScorer().score(baseline)
        perturbed_result = TrustScorer().score(perturbed)
        
        delta = perturbed_result.score - baseline_result.score
        print(f"DQS +10 (marginal): {baseline_result.score:.2f} -> {perturbed_result.score:.2f}, delta={delta:.3f}")
        
        # +10 should increase score
        assert delta > 0, f"Increasing DQS should increase trust"
        assert 1.5 < delta < 2.5, f"DQS +10 should add ~2 points, got {delta}"
        # May upgrade from REVIEW to MONITOR but not to ALLOW
        assert perturbed_result.decision in {"MONITOR", "REVIEW"}, \
            f"Small DQS improvement should not jump to ALLOW, got {perturbed_result.decision}"


class TestStabilityDriftHealthSmallChange:
    """Test sensitivity to small Drift Health Score changes"""

    def test_dhs_plus_2_from_healthy(self):
        """Increase DHS by 2 points from healthy baseline"""
        baseline = TrustInput(
            dqs=85, dhs=90, uss=85, rs=80, ps=75,
            confidence=85,
            hard_safety_passed=True,
            policy_approved=True
        )
        perturbed = TrustInput(
            dqs=85, dhs=92, uss=85, rs=80, ps=75,  # +2
            confidence=85,
            hard_safety_passed=True,
            policy_approved=True
        )
        
        baseline_result = TrustScorer().score(baseline)
        perturbed_result = TrustScorer().score(perturbed)
        
        delta = perturbed_result.score - baseline_result.score
        print(f"\nDHS +2: {baseline_result.score:.2f} -> {perturbed_result.score:.2f}, delta={delta:.3f}")
        
        # +2 should add ~0.4 (2 * 0.20)
        assert delta > 0, "Increasing DHS should increase trust"
        assert abs(delta) < 0.5, f"DHS +2 caused excessive delta: {delta}"
        assert perturbed_result.decision == baseline_result.decision

    def test_dhs_minus_10_from_healthy(self):
        """Decrease DHS by 10 points from healthy baseline"""
        baseline = TrustInput(
            dqs=85, dhs=90, uss=85, rs=80, ps=75,
            confidence=85,
            hard_safety_passed=True,
            policy_approved=True
        )
        perturbed = TrustInput(
            dqs=85, dhs=80, uss=85, rs=80, ps=75,  # -10
            confidence=85,
            hard_safety_passed=True,
            policy_approved=True
        )
        
        baseline_result = TrustScorer().score(baseline)
        perturbed_result = TrustScorer().score(perturbed)
        
        delta = perturbed_result.score - baseline_result.score
        print(f"DHS -10: {baseline_result.score:.2f} -> {perturbed_result.score:.2f}, delta={delta:.3f}")
        
        # -10 should decrease by ~2.0 (10 * 0.20)
        assert delta < 0, "Decreasing DHS should decrease trust"
        assert 1.8 < abs(delta) < 2.2, f"DHS -10 should decrease ~2 points, got {delta}"
        # Should stay in ALLOW or drop to MONITOR, not BLOCK
        assert perturbed_result.decision in {"ALLOW", "MONITOR"}, \
            f"DHS -10 should not cause sharp drop, got {perturbed_result.decision}"

    def test_dhs_gradual_degradation(self):
        """Test gradual DHS degradation from 90 to 50"""
        base_input = TrustInput(
            dqs=85, dhs=90, uss=85, rs=80, ps=75,
            confidence=85,
            hard_safety_passed=True,
            policy_approved=True
        )
        
        results = []
        decisions = []
        for dhs_value in range(90, 49, -5):  # 90, 85, 80, 75, 70, 65, 60, 55, 50
            trust_input = TrustInput(
                dqs=85, dhs=dhs_value, uss=85, rs=80, ps=75,
                confidence=85,
                hard_safety_passed=True,
                policy_approved=True
            )
            result = TrustScorer().score(trust_input)
            results.append(result.score)
            decisions.append(result.decision)
        
        # Check that scores decrease monotonically
        for i in range(len(results) - 1):
            assert results[i] > results[i+1], \
                f"DHS degradation should decrease trust: {results[i]} not > {results[i+1]}"
        
        # Check that decision doesn't flip erratically
        prev_decision = decisions[0]
        decision_changes = 0
        for d in decisions[1:]:
            if d != prev_decision:
                decision_changes += 1
            prev_decision = d
        
        # Should have reasonable number of transitions (maybe 1-2, not 5+)
        print(f"DHS degradation: {results}, decisions: {decisions}")
        assert decision_changes <= 2, f"Too many decision flips during degradation: {decision_changes}"


class TestStabilityUpdateSafetySmallChange:
    """Test sensitivity to small Update Safety Score changes"""

    def test_uss_plus_3_from_healthy(self):
        """Increase USS by 3 points from healthy baseline"""
        baseline = TrustInput(
            dqs=85, dhs=90, uss=85, rs=80, ps=75,
            confidence=85,
            hard_safety_passed=True,
            policy_approved=True
        )
        perturbed = TrustInput(
            dqs=85, dhs=90, uss=88, rs=80, ps=75,  # +3
            confidence=85,
            hard_safety_passed=True,
            policy_approved=True
        )
        
        baseline_result = TrustScorer().score(baseline)
        perturbed_result = TrustScorer().score(perturbed)
        
        delta = perturbed_result.score - baseline_result.score
        print(f"\nUSS +3: {baseline_result.score:.2f} -> {perturbed_result.score:.2f}, delta={delta:.3f}")
        
        # +3 should add ~0.9 (3 * 0.30)
        assert delta > 0, "Increasing USS should increase trust"
        assert 0.7 < delta < 1.1, f"USS +3 should add ~0.9, got {delta}"
        assert perturbed_result.decision == baseline_result.decision

    def test_uss_minus_8_from_healthy(self):
        """Decrease USS by 8 points from healthy baseline"""
        baseline = TrustInput(
            dqs=85, dhs=90, uss=85, rs=80, ps=75,
            confidence=85,
            hard_safety_passed=True,
            policy_approved=True
        )
        perturbed = TrustInput(
            dqs=85, dhs=90, uss=77, rs=80, ps=75,  # -8
            confidence=85,
            hard_safety_passed=True,
            policy_approved=True
        )
        
        baseline_result = TrustScorer().score(baseline)
        perturbed_result = TrustScorer().score(perturbed)
        
        delta = perturbed_result.score - baseline_result.score
        print(f"USS -8: {baseline_result.score:.2f} -> {perturbed_result.score:.2f}, delta={delta:.3f}")
        
        # -8 should decrease by ~2.4 (8 * 0.30)
        assert delta < 0, "Decreasing USS should decrease trust"
        assert 2.2 < abs(delta) < 2.6, f"USS -8 should decrease ~2.4, got {delta}"
        # May drop from ALLOW to MONITOR but not BLOCK
        assert perturbed_result.decision in {"ALLOW", "MONITOR"}, \
            f"USS -8 should not cause sharp drop, got {perturbed_result.decision}"


class TestStabilityReliabilitySmallChange:
    """Test sensitivity to small Reliability Score changes"""

    def test_rs_plus_4_from_healthy(self):
        """Increase RS by 4 points from healthy baseline"""
        baseline = TrustInput(
            dqs=85, dhs=90, uss=85, rs=80, ps=75,
            confidence=85,
            hard_safety_passed=True,
            policy_approved=True
        )
        perturbed = TrustInput(
            dqs=85, dhs=90, uss=85, rs=84, ps=75,  # +4
            confidence=85,
            hard_safety_passed=True,
            policy_approved=True
        )
        
        baseline_result = TrustScorer().score(baseline)
        perturbed_result = TrustScorer().score(perturbed)
        
        delta = perturbed_result.score - baseline_result.score
        print(f"\nRS +4: {baseline_result.score:.2f} -> {perturbed_result.score:.2f}, delta={delta:.3f}")
        
        # +4 should add ~0.6 (4 * 0.15)
        assert delta > 0, "Increasing RS should increase trust"
        assert abs(delta) < 1.0, f"RS +4 caused excessive delta: {delta}"
        assert perturbed_result.decision == baseline_result.decision

    def test_rs_minus_15_from_healthy(self):
        """Decrease RS by 15 points from healthy baseline"""
        baseline = TrustInput(
            dqs=85, dhs=90, uss=85, rs=80, ps=75,
            confidence=85,
            hard_safety_passed=True,
            policy_approved=True
        )
        perturbed = TrustInput(
            dqs=85, dhs=90, uss=85, rs=65, ps=75,  # -15
            confidence=85,
            hard_safety_passed=True,
            policy_approved=True
        )
        
        baseline_result = TrustScorer().score(baseline)
        perturbed_result = TrustScorer().score(perturbed)
        
        delta = perturbed_result.score - baseline_result.score
        print(f"RS -15: {baseline_result.score:.2f} -> {perturbed_result.score:.2f}, delta={delta:.3f}")
        
        # -15 should decrease by ~2.25 (15 * 0.15)
        assert delta < 0, "Decreasing RS should decrease trust"
        assert 2.0 < abs(delta) < 2.5, f"RS -15 should decrease ~2.25, got {delta}"


class TestStabilityPerformanceSmallChange:
    """Test sensitivity to small Performance Score changes"""

    def test_ps_plus_5_from_healthy(self):
        """Increase PS by 5 points from healthy baseline"""
        baseline = TrustInput(
            dqs=85, dhs=90, uss=85, rs=80, ps=75,
            confidence=85,
            hard_safety_passed=True,
            policy_approved=True
        )
        perturbed = TrustInput(
            dqs=85, dhs=90, uss=85, rs=80, ps=80,  # +5
            confidence=85,
            hard_safety_passed=True,
            policy_approved=True
        )
        
        baseline_result = TrustScorer().score(baseline)
        perturbed_result = TrustScorer().score(perturbed)
        
        delta = perturbed_result.score - baseline_result.score
        print(f"\nPS +5: {baseline_result.score:.2f} -> {perturbed_result.score:.2f}, delta={delta:.3f}")
        
        # +5 should add ~0.5 (5 * 0.10)
        assert delta > 0, "Increasing PS should increase trust"
        assert abs(delta) < 1.0, f"PS +5 caused excessive delta: {delta}"
        assert perturbed_result.decision == baseline_result.decision

    def test_ps_minus_20_from_healthy(self):
        """Decrease PS by 20 points from healthy baseline"""
        baseline = TrustInput(
            dqs=85, dhs=90, uss=85, rs=80, ps=75,
            confidence=85,
            hard_safety_passed=True,
            policy_approved=True
        )
        perturbed = TrustInput(
            dqs=85, dhs=90, uss=85, rs=80, ps=55,  # -20
            confidence=85,
            hard_safety_passed=True,
            policy_approved=True
        )
        
        baseline_result = TrustScorer().score(baseline)
        perturbed_result = TrustScorer().score(perturbed)
        
        delta = perturbed_result.score - baseline_result.score
        print(f"PS -20: {baseline_result.score:.2f} -> {perturbed_result.score:.2f}, delta={delta:.3f}")
        
        # -20 should decrease by ~3.0 (20 * 0.15, PS weight is 0.15)
        assert delta < 0, "Decreasing PS should decrease trust"
        assert 2.8 < abs(delta) < 3.2, f"PS -20 should decrease ~3.0, got {delta}"


class TestStabilityConfidenceSmallChange:
    """Test sensitivity to small Confidence changes"""

    def test_confidence_plus_5_high_to_higher(self):
        """Increase confidence by 5 points from healthy high"""
        baseline = TrustInput(
            dqs=85, dhs=90, uss=85, rs=80, ps=75,
            confidence=85,  # Already high
            hard_safety_passed=True,
            policy_approved=True
        )
        perturbed = TrustInput(
            dqs=85, dhs=90, uss=85, rs=80, ps=75,
            confidence=90,  # +5, even higher
            hard_safety_passed=True,
            policy_approved=True
        )
        
        baseline_result = TrustScorer().score(baseline)
        perturbed_result = TrustScorer().score(perturbed)
        
        # Confidence doesn't affect score directly, only decisions at boundary
        # So score should remain essentially the same
        delta = perturbed_result.score - baseline_result.score
        print(f"\nConfidence +5 (high->higher): {baseline_result.score:.2f} -> {perturbed_result.score:.2f}")
        
        assert abs(delta) < 0.1, f"Confidence should not affect score, got delta={delta}"
        # Both should have same decision since score is above threshold
        assert perturbed_result.decision == baseline_result.decision

    def test_confidence_drops_at_boundary(self):
        """Test confidence gate at boundary (trust ~65, confidence drops 70->30)"""
        baseline = TrustInput(
            dqs=70, dhs=72, uss=68, rs=70, ps=65,
            confidence=70,  # High confidence
            hard_safety_passed=True,
            policy_approved=True
        )
        perturbed = TrustInput(
            dqs=70, dhs=72, uss=68, rs=70, ps=65,
            confidence=30,  # Low confidence
            hard_safety_passed=True,
            policy_approved=True
        )
        
        baseline_result = TrustScorer().score(baseline)
        perturbed_result = TrustScorer().score(perturbed)
        
        # Score should be identical
        assert abs(baseline_result.score - perturbed_result.score) < 0.01, \
            "Score should not change"
        
        print(f"\nConfidence gate at boundary: {baseline_result.score:.2f}")
        print(f"  High confidence (70): {baseline_result.decision}")
        print(f"  Low confidence (30): {perturbed_result.decision}")
        
        # Decision may differ due to confidence gate at boundary
        # This is allowed


class TestStabilityMultiComponentChange:
    """Test stability across multiple simultaneous small changes"""

    def test_all_components_increase_by_2(self):
        """Increase all components by 2 points"""
        baseline = TrustInput(
            dqs=80, dhs=80, uss=80, rs=80, ps=80,
            confidence=80,
            hard_safety_passed=True,
            policy_approved=True
        )
        perturbed = TrustInput(
            dqs=82, dhs=82, uss=82, rs=82, ps=82,  # All +2
            confidence=82,
            hard_safety_passed=True,
            policy_approved=True
        )
        
        baseline_result = TrustScorer().score(baseline)
        perturbed_result = TrustScorer().score(perturbed)
        
        delta = perturbed_result.score - baseline_result.score
        print(f"\nAll components +2: {baseline_result.score:.2f} -> {perturbed_result.score:.2f}, delta={delta:.3f}")
        
        # All +2 should increase by 2.0 (all weights sum to 1.0, 2 * 1.0 = 2.0)
        assert 1.9 < delta < 2.1, f"All +2 should add ~2.0, got {delta}"
        # May upgrade decision but should be reasonable
        decision_upgrade = (
            baseline_result.decision == "MONITOR" and perturbed_result.decision == "ALLOW"
        ) or (
            baseline_result.decision == "REVIEW" and perturbed_result.decision == "MONITOR"
        ) or (
            baseline_result.decision == perturbed_result.decision
        )
        assert decision_upgrade, f"Decision upgrade should be reasonable, got {baseline_result.decision}->{perturbed_result.decision}"

    def test_all_components_decrease_by_5(self):
        """Decrease all components by 5 points"""
        baseline = TrustInput(
            dqs=75, dhs=75, uss=75, rs=75, ps=75,
            confidence=75,
            hard_safety_passed=True,
            policy_approved=True
        )
        perturbed = TrustInput(
            dqs=70, dhs=70, uss=70, rs=70, ps=70,  # All -5
            confidence=70,
            hard_safety_passed=True,
            policy_approved=True
        )
        
        baseline_result = TrustScorer().score(baseline)
        perturbed_result = TrustScorer().score(perturbed)
        
        delta = perturbed_result.score - baseline_result.score
        print(f"All components -5: {baseline_result.score:.2f} -> {perturbed_result.score:.2f}, delta={delta:.3f}")
        
        # All -5 should decrease by 5.0
        assert -5.1 < delta < -4.9, f"All -5 should decrease ~5.0, got {delta}"


class TestStabilityHardSafetyDiscontinuity:
    """Hard safety changes are allowed to create sharp decision flips"""

    def test_hard_safety_false_creates_block(self):
        """Hard safety failure should immediately flip to BLOCK"""
        baseline = TrustInput(
            dqs=90, dhs=90, uss=90, rs=90, ps=90,
            confidence=90,
            hard_safety_passed=True,
            policy_approved=True
        )
        perturbed = TrustInput(
            dqs=90, dhs=90, uss=90, rs=90, ps=90,
            confidence=90,
            hard_safety_passed=False,  # FAIL
            policy_approved=True
        )
        
        baseline_result = TrustScorer().score(baseline)
        perturbed_result = TrustScorer().score(perturbed)
        
        print(f"\nHard safety gate: {baseline_result.decision} -> {perturbed_result.decision}")
        
        # Score may be unchanged (hard safety is a gate, not a scored component)
        assert baseline_result.score == perturbed_result.score, \
            "Score should not change with hard safety"
        
        # Decision should flip sharply
        assert baseline_result.decision == "ALLOW", "High scores should ALLOW"
        assert perturbed_result.decision == "BLOCK", "Hard safety fail should BLOCK"
        
        # This discontinuity is ALLOWED and expected
        print("  ✓ Hard safety discontinuity is expected and correct")

    def test_policy_failure_overrides_trust(self):
        """Policy failure should override trust score"""
        baseline = TrustInput(
            dqs=85, dhs=85, uss=85, rs=85, ps=85,
            confidence=85,
            hard_safety_passed=True,
            policy_approved=True
        )
        perturbed = TrustInput(
            dqs=85, dhs=85, uss=85, rs=85, ps=85,
            confidence=85,
            hard_safety_passed=True,
            policy_approved=False  # FAIL
        )
        
        baseline_result = TrustScorer().score(baseline)
        perturbed_result = TrustScorer().score(perturbed)
        
        print(f"\nPolicy gate: {baseline_result.decision} -> {perturbed_result.decision}")
        
        # Score unchanged
        assert baseline_result.score == perturbed_result.score
        
        # Decision should change (ALLOW -> REVIEW or BLOCK)
        assert baseline_result.decision == "ALLOW"
        assert perturbed_result.decision in {"REVIEW", "BLOCK"}
        
        print("  ✓ Policy gate override is expected")


class TestStabilityEdgeCaseNearThresholds:
    """Test stability near decision thresholds"""

    def test_score_near_75_allow_block(self):
        """Test stability near ALLOW (75) threshold"""
        # Just below 75
        input_74 = TrustInput(
            dqs=74, dhs=74, uss=74, rs=74, ps=74,
            confidence=70,
            hard_safety_passed=True,
            policy_approved=True
        )
        # Just above 75
        input_76 = TrustInput(
            dqs=76, dhs=76, uss=76, rs=76, ps=76,
            confidence=70,
            hard_safety_passed=True,
            policy_approved=True
        )
        
        result_74 = TrustScorer().score(input_74)
        result_76 = TrustScorer().score(input_76)
        
        print(f"\nNear ALLOW threshold (75):")
        print(f"  Score 74: {result_74.decision}")
        print(f"  Score 76: {result_76.decision}")
        
        # Decision may flip here, but only by one step
        assert result_74.score < 75
        assert result_76.score > 75
        # Decisions should be adjacent (REVIEW->MONITOR or MONITOR->ALLOW)
        allowed_transitions = {
            ("REVIEW", "MONITOR"),
            ("MONITOR", "ALLOW"),
            ("REVIEW", "ALLOW"),  # May skip MONITOR
        }
        transition = (result_74.decision, result_76.decision)
        assert transition[0] in {"REVIEW", "MONITOR"}, f"Below 75 should be REVIEW/MONITOR, got {result_74.decision}"
        assert transition[1] in {"MONITOR", "ALLOW"}, f"Above 75 should be MONITOR/ALLOW, got {result_76.decision}"

    def test_score_near_40_review_block(self):
        """Test stability near BLOCK (40) threshold"""
        input_39 = TrustInput(
            dqs=39, dhs=39, uss=39, rs=39, ps=39,
            confidence=40,
            hard_safety_passed=True,
            policy_approved=True
        )
        input_41 = TrustInput(
            dqs=41, dhs=41, uss=41, rs=41, ps=41,
            confidence=40,
            hard_safety_passed=True,
            policy_approved=True
        )
        
        result_39 = TrustScorer().score(input_39)
        result_41 = TrustScorer().score(input_41)
        
        print(f"\nNear BLOCK threshold (40):")
        print(f"  Score 39: {result_39.decision}")
        print(f"  Score 41: {result_41.decision}")
        
        # Both should be low decisions
        assert result_39.decision in {"REVIEW", "BLOCK"}
        assert result_41.decision in {"REVIEW", "BLOCK"}
