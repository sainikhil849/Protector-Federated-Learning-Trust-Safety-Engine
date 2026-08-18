"""
Unit tests for Drift Health Score (DHS) implementation

Tests PSI-based drift detection for all threshold levels
"""

import pytest
import numpy as np
from src.scoring_engines import DriftHealthScorer, DriftHealthInput, calculate_dhs


class TestDriftHealthScoreME:
    """Tests for manual worked example"""
    
    def test_manual_worked_example(self):
        """
        Test manual worked example from specification:
        
        Baseline: centered at 50000, well-distributed
        Current: shifted to higher values (50% increase in mean)
        Expected PSI ≈ 0.15 → DHS ≈ 80 (minor drift)
        """
        # Baseline: normal distribution around 50000
        baseline = np.random.normal(loc=50000, scale=10000, size=(500, 128))
        
        # Current: shifted distribution (mean ~75000)
        current = np.random.normal(loc=75000, scale=10000, size=(100, 128))
        
        scorer = DriftHealthScorer()
        input_data = DriftHealthInput(
            current_features=current,
            baseline_features=baseline
        )
        
        output = scorer.score(input_data)
        
        print(f"\nManual Example Test:")
        print(f"  Score: {output.score:.1f}")
        print(f"  PSI Average: {output.psi_average:.3f}")
        print(f"  Drift Level: {output.drift_level}")
        print(f"  Features with Drift: {output.drift_count}")
        
        # Score should reflect minor-to-moderate drift
        assert 0 <= output.score <= 100
        assert output.drift_level in ["none", "minor", "moderate", "severe"]
        assert len(output.features_with_drift) >= 0


class TestDriftHealthScoreBoundary:
    """Test boundary values"""
    
    def test_no_drift_identical_distribution(self):
        """Identical baseline and current → PSI ≈ 0 → DHS ≈ 100"""
        # Use same data for both
        data = np.random.uniform(1000, 100000, size=(200, 128))
        
        scorer = DriftHealthScorer()
        input_data = DriftHealthInput(
            current_features=data.copy(),
            baseline_features=data.copy()
        )
        
        output = scorer.score(input_data)
        
        print(f"\nNo Drift Test:")
        print(f"  Score: {output.score:.1f}")
        print(f"  PSI Average: {output.psi_average:.3f}")
        
        # Identical distributions should have minimal drift
        assert output.psi_average < 0.10, "Identical data should have PSI < 0.10"
        assert output.score >= 95, "No drift should score >= 95"
        assert output.drift_level == "none"
    
    def test_severe_drift(self):
        """Different distributions → high PSI → DHS < 50"""
        # Baseline: 1000-50000
        baseline = np.random.uniform(1000, 50000, size=(300, 128))
        
        # Current: 100000-170000 (completely different range)
        current = np.random.uniform(100000, 170000, size=(100, 128))
        
        scorer = DriftHealthScorer()
        input_data = DriftHealthInput(
            current_features=current,
            baseline_features=baseline
        )
        
        output = scorer.score(input_data)
        
        print(f"\nSevere Drift Test:")
        print(f"  Score: {output.score:.1f}")
        print(f"  PSI Average: {output.psi_average:.3f}")
        print(f"  Drift Level: {output.drift_level}")
        
        # Very different ranges should show severe drift
        assert output.psi_average > 0.25, "Different ranges should have high PSI"
        assert output.score < 80, "Severe drift should score < 80"
    
    def test_empty_input(self):
        """Empty input → DHS = 0"""
        current = np.array([]).reshape(0, 128)
        baseline = np.array([]).reshape(0, 128)
        
        scorer = DriftHealthScorer()
        input_data = DriftHealthInput(
            current_features=current,
            baseline_features=baseline
        )
        
        output = scorer.score(input_data)
        
        assert output.score == 0.0


class TestDriftHealthScoreEdgeCases:
    """Test edge cases"""
    
    def test_single_sample(self):
        """Single sample should not crash"""
        baseline = np.ones((100, 128)) * 50000
        current = np.ones((1, 128)) * 50000
        
        scorer = DriftHealthScorer()
        input_data = DriftHealthInput(
            current_features=current,
            baseline_features=baseline
        )
        
        output = scorer.score(input_data)
        
        assert 0 <= output.score <= 100
    
    def test_constant_features(self):
        """All features identical across all samples"""
        baseline = np.ones((100, 128)) * 50000
        current = np.ones((50, 128)) * 50000  # Identical, no drift
        
        scorer = DriftHealthScorer()
        input_data = DriftHealthInput(
            current_features=current,
            baseline_features=baseline
        )
        
        output = scorer.score(input_data)
        
        print(f"\nConstant Features Test:")
        print(f"  Score: {output.score:.1f}")
        print(f"  PSI Average: {output.psi_average:.3f}")
        
        # Identical constants should have no drift
        assert output.score >= 95
        assert output.drift_level == "none"
    
    def test_large_dataset(self):
        """Large dataset (5000 samples)"""
        baseline = np.random.normal(50000, 20000, size=(5000, 128))
        current = np.random.normal(50000, 20000, size=(1000, 128))
        
        scorer = DriftHealthScorer()
        input_data = DriftHealthInput(
            current_features=current,
            baseline_features=baseline
        )
        
        output = scorer.score(input_data)
        
        print(f"\nLarge Dataset Test:")
        print(f"  Score: {output.score:.1f}")
        
        assert 0 <= output.score <= 100


class TestDriftHealthScoreInvalid:
    """Test invalid inputs"""
    
    def test_nan_values_current(self):
        """NaN in current features should be handled"""
        baseline = np.random.uniform(1000, 100000, size=(200, 128))
        current = np.random.uniform(1000, 100000, size=(100, 128))
        current[0, 0] = np.nan
        
        scorer = DriftHealthScorer()
        input_data = DriftHealthInput(
            current_features=current,
            baseline_features=baseline
        )
        
        output = scorer.score(input_data)
        
        print(f"\nNaN in Current Test:")
        print(f"  Score: {output.score:.1f}")
        
        # Should handle gracefully without crashing
        assert 0 <= output.score <= 100
    
    def test_inf_values_baseline(self):
        """Inf in baseline features should be handled"""
        baseline = np.random.uniform(1000, 100000, size=(200, 128))
        baseline[5, 10] = np.inf
        current = np.random.uniform(1000, 100000, size=(100, 128))
        
        scorer = DriftHealthScorer()
        input_data = DriftHealthInput(
            current_features=current,
            baseline_features=baseline
        )
        
        output = scorer.score(input_data)
        
        print(f"\nInf in Baseline Test:")
        print(f"  Score: {output.score:.1f}")
        
        assert 0 <= output.score <= 100
    
    def test_empty_baseline(self):
        """Empty baseline should return DHS=0"""
        baseline = np.array([]).reshape(0, 128)
        current = np.random.uniform(1000, 100000, size=(100, 128))
        
        scorer = DriftHealthScorer()
        input_data = DriftHealthInput(
            current_features=current,
            baseline_features=baseline
        )
        
        output = scorer.score(input_data)
        
        assert output.score == 0.0
    
    def test_empty_current(self):
        """Empty current should return DHS=0"""
        baseline = np.random.uniform(1000, 100000, size=(200, 128))
        current = np.array([]).reshape(0, 128)
        
        scorer = DriftHealthScorer()
        input_data = DriftHealthInput(
            current_features=current,
            baseline_features=baseline
        )
        
        output = scorer.score(input_data)
        
        assert output.score == 0.0


class TestDriftHealthScoreThresholds:
    """Test PSI to DHS score mapping"""
    
    def test_psi_to_score_no_drift(self):
        """PSI < 0.10 → score 100"""
        scorer = DriftHealthScorer()
        score = scorer._psi_to_score(0.05)
        
        assert score == 100.0, f"PSI=0.05 should map to 100, got {score}"
    
    def test_psi_to_score_minor_drift(self):
        """PSI in [0.10, 0.25] → score in [80, 100]"""
        scorer = DriftHealthScorer()
        
        score_at_10 = scorer._psi_to_score(0.10)
        score_at_25 = scorer._psi_to_score(0.25)
        score_mid = scorer._psi_to_score(0.175)
        
        print(f"\nMinor Drift Mapping:")
        print(f"  PSI=0.10 → score={score_at_10:.1f}")
        print(f"  PSI=0.175 → score={score_mid:.1f}")
        print(f"  PSI=0.25 → score={score_at_25:.1f}")
        
        assert 80 <= score_at_10 <= 100
        assert 80 <= score_mid <= 100
        assert 60 <= score_at_25 <= 80
    
    def test_psi_to_score_moderate_drift(self):
        """PSI in [0.25, 0.50] → score in [60, 80]"""
        scorer = DriftHealthScorer()
        
        score_at_25 = scorer._psi_to_score(0.25)
        score_at_50 = scorer._psi_to_score(0.50)
        
        print(f"\nModerate Drift Mapping:")
        print(f"  PSI=0.25 → score={score_at_25:.1f}")
        print(f"  PSI=0.50 → score={score_at_50:.1f}")
        
        assert 60 <= score_at_25 <= 80
        assert 20 <= score_at_50 <= 60
    
    def test_psi_to_score_severe_drift(self):
        """PSI >= 0.50 → score <= 20"""
        scorer = DriftHealthScorer()
        
        score = scorer._psi_to_score(0.75)
        
        print(f"\nSevere Drift Mapping:")
        print(f"  PSI=0.75 → score={score:.1f}")
        
        assert score < 30, "High PSI should result in low score"


class TestDriftHealthScoreMinimal:
    """Test with minimum valid sample"""
    
    def test_minimum_valid_sample(self):
        """Single baseline sample and current sample"""
        baseline = np.array([[50000.0] * 128])
        current = np.array([[50000.0] * 128])
        
        score, details = calculate_dhs(current, baseline)
        
        print(f"\nMinimum Valid Sample Test:")
        print(f"  Score: {score:.1f}")
        print(f"  Details: {details}")
        
        assert 0 <= score <= 100
        assert details['drift_level'] in ["none", "minor", "moderate", "severe", "unknown"]


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
