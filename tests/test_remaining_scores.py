"""
Unit tests for remaining scoring engines:
- Update Safety Score (USS)
- Reliability Score (RS)  
- Performance Score (PS)
- Confidence Score
- Trust Score
"""

import pytest
import numpy as np
from src.scoring_engines import (
    UpdateSafetyScorer, UpdateSafetyInput,
    ReliabilityScorer, ReliabilityInput,
    PerformanceScorer, PerformanceInput,
    ConfidenceScorer, ConfidenceInput,
    TrustScorer, TrustInput
)
import time


# ============================================================================
# UPDATE SAFETY SCORE (USS) TESTS
# ============================================================================

class TestUpdateSafetyScore:
    """Tests for Update Safety Score"""
    
    def test_perfect_gradient(self):
        """Perfect valid gradient"""
        # Create gradient with magnitude ~100 (middle of valid range)
        gradient = np.random.normal(0, 0.7, 128)  # ~100 magnitude
        gradient = gradient / np.linalg.norm(gradient) * 100  # Normalize to 100
        
        scorer = UpdateSafetyScorer()
        
        input_data = UpdateSafetyInput(
            gradient=gradient,
            timestamp=time.time() - 5,  # 5 seconds old (very fresh)
            current_time=time.time()
        )
        
        output = scorer.score(input_data)
        
        print(f"\nPerfect Gradient Test:")
        print(f"  USS Score: {output.score:.1f}")
        print(f"  Magnitude: {output.gradient_magnitude:.1f}")
        print(f"  Bounds Check: {output.bounds_check:.3f}")
        print(f"  Is Valid: {output.is_valid}")
        
        # With magnitude 100, bounds ~0.1, freshness ~0.975
        # USS = (1.0 + 0.1 + 0.975 + 1.0)/4 * 100 ≈ 77
        assert output.score > 70, f"Valid gradient should score > 70, got {output.score}"
        assert output.is_valid == True
    
    def test_empty_gradient(self):
        """Empty gradient"""
        scorer = UpdateSafetyScorer()
        input_data = UpdateSafetyInput(
            gradient=np.array([]),
            timestamp=time.time()
        )
        
        output = scorer.score(input_data)
        
        assert output.score == 0.0
        assert output.is_valid == False
    
    def test_wrong_shape(self):
        """Wrong gradient shape"""
        gradient = np.ones(100)  # Should be 128
        scorer = UpdateSafetyScorer()
        
        input_data = UpdateSafetyInput(
            gradient=gradient,
            timestamp=time.time()
        )
        
        output = scorer.score(input_data)
        
        assert output.is_valid == False
        assert "Invalid shape" in str(output.violation_reasons)
    
    def test_nan_gradient(self):
        """NaN in gradient"""
        gradient = np.ones(128)
        gradient[0] = np.nan
        
        scorer = UpdateSafetyScorer()
        input_data = UpdateSafetyInput(
            gradient=gradient,
            timestamp=time.time()
        )
        
        output = scorer.score(input_data)
        
        assert output.is_valid == False
        assert output.validity_check < 1.0
    
    def test_magnitude_too_large(self):
        """Magnitude exceeds max (exploding gradient)"""
        gradient = np.ones(128) * 1500  # > 1000
        scorer = UpdateSafetyScorer()
        
        input_data = UpdateSafetyInput(
            gradient=gradient,
            timestamp=time.time()
        )
        
        output = scorer.score(input_data)
        
        assert output.is_valid == False
        assert "exploding" in str(output.violation_reasons)
    
    def test_stale_gradient(self):
        """Gradient too old (> 60 seconds)"""
        gradient = np.ones(128) * 45.3
        scorer = UpdateSafetyScorer()
        
        input_data = UpdateSafetyInput(
            gradient=gradient,
            timestamp=time.time() - 100,  # 100 seconds old
            current_time=time.time()
        )
        
        output = scorer.score(input_data)
        
        assert output.is_valid == False
        assert output.freshness_check < 1.0
    
    def test_with_previous_gradient(self):
        """Stability check with previous gradient"""
        current = np.ones(128) * 45.3
        previous = np.ones(128) * 42.1
        
        scorer = UpdateSafetyScorer()
        input_data = UpdateSafetyInput(
            gradient=current,
            timestamp=time.time(),
            previous_gradient=previous
        )
        
        output = scorer.score(input_data)
        
        # Change: (45.3-42.1)/42.1 = 7.6% (within threshold)
        assert output.stability_check > 0.7


# ============================================================================
# RELIABILITY SCORE (RS) TESTS
# ============================================================================

class TestReliabilityScore:
    """Tests for Reliability Score"""
    
    def test_perfect_participant(self):
        """Perfect reliability"""
        scorer = ReliabilityScorer()
        input_data = ReliabilityInput(
            last_seen_rounds_ago=0,
            success_count=50,
            total_count=50,
            consecutive_failures=0,
            consistency_score=0.95
        )
        
        output = scorer.score(input_data)
        
        print(f"\nPerfect Participant Test:")
        print(f"  RS Score: {output.score:.1f}")
        print(f"  Quarantine: {output.quarantine_level}")
        
        assert output.score > 90
        assert output.quarantine_level == "ok"
    
    def test_stale_participant(self):
        """No recent updates"""
        scorer = ReliabilityScorer()
        input_data = ReliabilityInput(
            last_seen_rounds_ago=10,  # > 5 round threshold
            success_count=40,
            total_count=50,
            consecutive_failures=3,
            consistency_score=0.7
        )
        
        output = scorer.score(input_data)
        
        print(f"\nStale Participant Test:")
        print(f"  RS Score: {output.score:.1f}")
        print(f"  Quarantine: {output.quarantine_level}")
        
        assert output.quarantine_level in ["warning", "quarantine"]
    
    def test_failed_participant(self):
        """Multiple consecutive failures"""
        scorer = ReliabilityScorer()
        input_data = ReliabilityInput(
            last_seen_rounds_ago=2,
            success_count=10,
            total_count=50,
            consecutive_failures=6,  # > 5 threshold
            consistency_score=0.3
        )
        
        output = scorer.score(input_data)
        
        assert output.quarantine_level == "quarantine"


# ============================================================================
# PERFORMANCE SCORE (PS) TESTS
# ============================================================================

class TestPerformanceScore:
    """Tests for Performance Score"""
    
    def test_good_performance(self):
        """Improving local model"""
        scorer = PerformanceScorer()
        input_data = PerformanceInput(
            local_accuracy=0.85,
            baseline_accuracy=0.80,
            class_fairness_score=0.92,
            metric_variance=0.05,
            update_impact=0.08  # Positive impact
        )
        
        output = scorer.score(input_data)
        
        print(f"\nGood Performance Test:")
        print(f"  PS Score: {output.score:.1f}")
        print(f"  Impact: {output.impact_assessment}")
        
        assert output.score > 80
        assert output.impact_assessment == "positive"
    
    def test_poor_performance(self):
        """Degrading accuracy"""
        scorer = PerformanceScorer()
        input_data = PerformanceInput(
            local_accuracy=0.60,
            baseline_accuracy=0.80,
            class_fairness_score=0.50,
            metric_variance=0.40,
            update_impact=-0.15
        )
        
        output = scorer.score(input_data)
        
        assert output.score < 70
        assert output.impact_assessment == "negative"


# ============================================================================
# CONFIDENCE SCORE TESTS
# ============================================================================

class TestConfidenceScore:
    """Tests for Confidence Score"""
    
    def test_high_confidence(self):
        """Complete evidence, fresh, stable"""
        scorer = ConfidenceScorer()
        input_data = ConfidenceInput(
            data_coverage=0.95,
            historical_depth_days=120,
            metric_freshness_hours=6,
            metric_count=16,
            metric_stability=0.08
        )
        
        output = scorer.score(input_data)
        
        print(f"\nHigh Confidence Test:")
        print(f"  Confidence Score: {output.score:.1f}")
        print(f"  Level: {output.confidence_level}")
        
        assert output.score > 85
        assert output.confidence_level == "high"
    
    def test_low_confidence(self):
        """Sparse evidence, old, unstable"""
        scorer = ConfidenceScorer()
        input_data = ConfidenceInput(
            data_coverage=0.30,
            historical_depth_days=10,
            metric_freshness_hours=240,  # 10 days old
            metric_count=4,
            metric_stability=0.50
        )
        
        output = scorer.score(input_data)
        
        print(f"\nLow Confidence Test:")
        print(f"  Confidence Score: {output.score:.1f}")
        print(f"  Level: {output.confidence_level}")
        
        assert output.score < 60
        assert output.confidence_level in ["low", "insufficient"]
    
    def test_insufficient_confidence(self):
        """No evidence"""
        scorer = ConfidenceScorer()
        input_data = ConfidenceInput(
            data_coverage=0.0,
            historical_depth_days=0,
            metric_freshness_hours=1000,
            metric_count=0,
            metric_stability=1.0
        )
        
        output = scorer.score(input_data)
        
        assert output.confidence_level == "insufficient"


# ============================================================================
# TRUST SCORE TESTS
# ============================================================================

class TestTrustScore:
    """Tests for final Trust Score"""
    
    def test_trust_allow(self):
        """All dimensions excellent → ALLOW"""
        scorer = TrustScorer()
        input_data = TrustInput(
            dqs=95,  # Data Quality
            dhs=92,  # Drift Health
            uss=98,  # Update Safety
            rs=90,   # Reliability
            ps=88,   # Performance
            confidence=88
        )
        
        output = scorer.score(input_data)
        
        print(f"\nTrust ALLOW Test:")
        print(f"  Trust Score: {output.score:.1f}")
        print(f"  Decision: {output.decision}")
        
        assert output.score >= 75
        assert output.decision == "ALLOW"
    
    def test_trust_monitor(self):
        """Good but not excellent → MONITOR"""
        scorer = TrustScorer()
        input_data = TrustInput(
            dqs=78,
            dhs=72,
            uss=75,
            rs=68,
            ps=65,
            confidence=75
        )
        
        output = scorer.score(input_data)
        
        print(f"\nTrust MONITOR Test:")
        print(f"  Trust Score: {output.score:.1f}")
        print(f"  Decision: {output.decision}")
        
        assert 60 <= output.score < 75
        assert output.decision in ["MONITOR", "REVIEW"]
    
    def test_trust_review(self):
        """Ambiguous → REVIEW"""
        scorer = TrustScorer()
        input_data = TrustInput(
            dqs=55,
            dhs=50,
            uss=48,
            rs=45,
            ps=40,
            confidence=35
        )
        
        output = scorer.score(input_data)
        
        print(f"\nTrust REVIEW Test:")
        print(f"  Trust Score: {output.score:.1f}")
        print(f"  Decision: {output.decision}")
        
        assert output.decision in ["REVIEW", "BLOCK"]
    
    def test_trust_block(self):
        """Poor performance → BLOCK"""
        scorer = TrustScorer()
        input_data = TrustInput(
            dqs=10,
            dhs=12,
            uss=8,
            rs=15,
            ps=18,
            confidence=20
        )
        
        output = scorer.score(input_data)
        
        print(f"\nTrust BLOCK Test:")
        print(f"  Trust Score: {output.score:.1f}")
        print(f"  Decision: {output.decision}")
        
        assert output.decision == "BLOCK"
    
    def test_confidence_gate_escalation(self):
        """Low confidence escalates to REVIEW"""
        scorer = TrustScorer()
        input_data = TrustInput(
            dqs=72,  # Would be MONITOR
            dhs=68,
            uss=70,
            rs=65,
            ps=62,
            confidence=25  # Very low confidence
        )
        
        output = scorer.score(input_data)
        
        print(f"\nConfidence Escalation Test:")
        print(f"  Trust Score: {output.score:.1f}")
        print(f"  Confidence: {output.confidence_level}")
        print(f"  Decision: {output.decision}")
        
        # Confidence should escalate to REVIEW
        assert output.decision == "REVIEW"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
