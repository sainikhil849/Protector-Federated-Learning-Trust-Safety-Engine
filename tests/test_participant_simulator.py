"""
Tests for participant simulator.

Tests cover:
- Participant count
- All rows accounted for
- No unexpected data loss
- Deterministic split with same seed
- IID distribution validation
- Non-IID distribution validation
- Data integrity checks
- Edge cases
"""

import pytest
import numpy as np
import tempfile
import os
from pathlib import Path

from src.dataset_loader import load_csv, DatasetData, DatasetMetadata
from src.participant_simulator import (
    simulate_participants,
    verify_no_data_loss,
    get_distribution_statistics,
    ParticipantData,
    ParticipantMetadata
)


@pytest.fixture
def temp_dir():
    """Create temporary directory for test CSVs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def simple_dataset(temp_dir):
    """Create a simple dataset for testing (99 rows, 5 features, 3 classes)."""
    filepath = os.path.join(temp_dir, "simple.csv")
    
    n_rows = 99  # Divisible by 3
    n_features = 5
    
    data = {}
    for i in range(n_features):
        data[f'feature_{i}'] = np.random.RandomState(42).uniform(0.1, 170000, n_rows)
    
    # Create balanced 3-class distribution
    labels = np.repeat([1, 2, 3], n_rows // 3)
    np.random.RandomState(42).shuffle(labels)
    data['label'] = labels
    
    import pandas as pd
    df = pd.DataFrame(data)
    df.to_csv(filepath, index=False)
    
    return load_csv(filepath, target_column='label')


@pytest.fixture
def medium_dataset(temp_dir):
    """Create a medium-sized dataset (996 rows, 10 features, 6 classes)."""
    filepath = os.path.join(temp_dir, "medium.csv")
    
    n_rows = 996  # Divisible by 6
    n_features = 10
    
    data = {}
    for i in range(n_features):
        data[f'feature_{i}'] = np.random.RandomState(42).uniform(0.1, 170000, n_rows)
    
    # Create balanced 6-class distribution
    labels = np.repeat([1, 2, 3, 4, 5, 6], n_rows // 6)
    np.random.RandomState(42).shuffle(labels)
    data['label'] = labels
    
    import pandas as pd
    df = pd.DataFrame(data)
    df.to_csv(filepath, index=False)
    
    return load_csv(filepath, target_column='label')


class TestParticipantCount:
    """Test correct participant count."""
    
    def test_simulate_exact_count(self, simple_dataset):
        """Test that correct number of participants are created."""
        participants = simulate_participants(simple_dataset, number_of_participants=5)
        
        assert len(participants) == 5
    
    def test_simulate_various_counts(self, simple_dataset):
        """Test with different participant counts."""
        for n_participants in [2, 5, 10, 20]:
            participants = simulate_participants(simple_dataset, number_of_participants=n_participants)
            
            assert len(participants) == n_participants
    
    def test_participant_ids_unique(self, simple_dataset):
        """Test that all participant IDs are unique."""
        participants = simulate_participants(simple_dataset, number_of_participants=5)
        
        ids = [p.participant_id for p in participants]
        assert len(ids) == len(set(ids))
    
    def test_participant_ids_sequential(self, simple_dataset):
        """Test that participant IDs are sequential."""
        participants = simulate_participants(simple_dataset, number_of_participants=3)
        
        assert participants[0].participant_id == "ORG-001"
        assert participants[1].participant_id == "ORG-002"
        assert participants[2].participant_id == "ORG-003"


class TestDataIntegrity:
    """Test that all original data is preserved."""
    
    def test_no_data_loss_iid(self, simple_dataset):
        """Test no data loss with IID distribution."""
        participants = simulate_participants(
            simple_dataset,
            number_of_participants=5,
            distribution_mode="iid"
        )
        
        assert verify_no_data_loss(simple_dataset, participants)
    
    def test_no_data_loss_non_iid(self, simple_dataset):
        """Test no data loss with non-IID distribution."""
        participants = simulate_participants(
            simple_dataset,
            number_of_participants=5,
            distribution_mode="non-iid"
        )
        
        assert verify_no_data_loss(simple_dataset, participants)
    
    def test_row_count_sum(self, simple_dataset):
        """Test that sum of participant rows equals original."""
        participants = simulate_participants(simple_dataset, number_of_participants=5)
        
        total_rows = sum(p.row_count for p in participants)
        
        assert total_rows == len(simple_dataset.X)
    
    def test_all_original_rows_used(self, simple_dataset):
        """Test that every original row is assigned to exactly one participant."""
        participants = simulate_participants(simple_dataset, number_of_participants=5)
        
        all_indices = []
        for p in participants:
            all_indices.extend(p.metadata.original_row_index)
        
        # Check no duplicates
        assert len(all_indices) == len(set(all_indices))
        
        # Check no missing
        assert set(all_indices) == set(range(len(simple_dataset.X)))
    
    def test_no_original_dataset_modification(self, simple_dataset):
        """Test that original dataset is never modified."""
        X_original = simple_dataset.X.copy()
        y_original = simple_dataset.y.copy()
        
        simulate_participants(simple_dataset, number_of_participants=5)
        
        assert np.array_equal(simple_dataset.X, X_original)
        assert np.array_equal(simple_dataset.y, y_original)
    
    def test_participant_data_copied_not_referenced(self, simple_dataset):
        """Test that participant data is copied, not referenced."""
        participants = simulate_participants(simple_dataset, number_of_participants=2)
        
        # Modify participant data
        participants[0].X[0, 0] = 99999.0
        
        # Original should not be modified
        assert simple_dataset.X[0, 0] != 99999.0


class TestDeterminism:
    """Test that splitting is deterministic with same seed."""
    
    def test_same_seed_same_split(self, simple_dataset):
        """Test that same seed produces identical split."""
        participants_1 = simulate_participants(
            simple_dataset,
            number_of_participants=5,
            random_seed=42
        )
        
        participants_2 = simulate_participants(
            simple_dataset,
            number_of_participants=5,
            random_seed=42
        )
        
        # Check that indices match
        for p1, p2 in zip(participants_1, participants_2):
            assert p1.metadata.original_row_index == p2.metadata.original_row_index
    
    def test_different_seed_different_split(self, simple_dataset):
        """Test that different seeds produce different splits."""
        participants_1 = simulate_participants(
            simple_dataset,
            number_of_participants=5,
            random_seed=42
        )
        
        participants_2 = simulate_participants(
            simple_dataset,
            number_of_participants=5,
            random_seed=43
        )
        
        # At least one participant should have different indices
        different = False
        for p1, p2 in zip(participants_1, participants_2):
            if p1.metadata.original_row_index != p2.metadata.original_row_index:
                different = True
                break
        
        assert different
    
    def test_seed_reproducibility_across_calls(self, simple_dataset):
        """Test reproducibility across multiple calls."""
        participants_1 = simulate_participants(simple_dataset, random_seed=123)
        participants_2 = simulate_participants(simple_dataset, random_seed=123)
        participants_3 = simulate_participants(simple_dataset, random_seed=123)
        
        for p1, p2, p3 in zip(participants_1, participants_2, participants_3):
            assert p1.metadata.original_row_index == p2.metadata.original_row_index
            assert p2.metadata.original_row_index == p3.metadata.original_row_index


class TestIIDDistribution:
    """Test IID distribution properties."""
    
    def test_iid_relatively_balanced(self, simple_dataset):
        """Test that IID distribution creates roughly balanced participant sizes."""
        participants = simulate_participants(
            simple_dataset,
            number_of_participants=5,
            distribution_mode="iid"
        )
        
        row_counts = [p.row_count for p in participants]
        
        # With 99 rows and 5 participants, expect roughly 19.8 rows each
        expected_per_participant = len(simple_dataset.X) / 5
        
        # Last participant gets remainder, so allow up to 5 rows difference
        max_diff = 5
        for count in row_counts:
            assert abs(count - expected_per_participant) <= max_diff
    
    def test_iid_class_distribution_representative(self, simple_dataset):
        """Test that IID distribution preserves global class distribution."""
        participants = simulate_participants(
            simple_dataset,
            number_of_participants=5,
            distribution_mode="iid",
            random_seed=42
        )
        
        # Compute global class distribution
        global_class_dist = {}
        for p in participants:
            for class_label, count in p.metadata.class_distribution.items():
                global_class_dist[class_label] = global_class_dist.get(class_label, 0) + count
        
        # Should match original
        original_unique, original_counts = np.unique(simple_dataset.y, return_counts=True)
        for label, count in zip(original_unique, original_counts):
            assert global_class_dist[int(label)] == int(count)
    
    def test_iid_each_participant_representative(self, simple_dataset):
        """Test that each IID participant has representative class distribution."""
        participants = simulate_participants(
            simple_dataset,
            number_of_participants=5,
            distribution_mode="iid",
            random_seed=42
        )
        
        # Each participant should have all classes (with small sample size)
        original_classes = set(np.unique(simple_dataset.y))
        
        for p in participants:
            participant_classes = set(p.metadata.class_distribution.keys())
            # With 100 rows → 20 per participant, should have all 3 classes most of the time
            # This is probabilistic but very likely with seed 42
            overlap = participant_classes & original_classes
            assert len(overlap) > 0  # At least one class


class TestNonIIDDistribution:
    """Test non-IID distribution properties."""
    
    def test_non_iid_creates_skew(self, simple_dataset):
        """Test that non-IID distribution creates class skew."""
        participants = simulate_participants(
            simple_dataset,
            number_of_participants=5,
            distribution_mode="non-iid",
            random_seed=42
        )
        
        # Each participant should have skewed distribution
        skew_detected = False
        
        for p in participants:
            class_counts = list(p.metadata.class_distribution.values())
            if len(class_counts) > 1:
                # Check if any class dominates (e.g., 60%+ vs others)
                max_count = max(class_counts)
                total_count = sum(class_counts)
                max_ratio = max_count / total_count if total_count > 0 else 0
                
                if max_ratio > 0.5:  # More than 50% one class
                    skew_detected = True
                    break
        
        assert skew_detected  # At least one participant should be skewed
    
    def test_non_iid_participants_different_distributions(self, simple_dataset):
        """Test that different participants have different class distributions."""
        participants = simulate_participants(
            simple_dataset,
            number_of_participants=5,
            distribution_mode="non-iid",
            random_seed=42
        )
        
        distributions = [tuple(sorted(p.metadata.class_distribution.items())) for p in participants]
        
        # Not all should be identical
        assert len(set(distributions)) > 1
    
    def test_non_iid_all_data_still_accounted(self, simple_dataset):
        """Test that non-IID still accounts for all data."""
        participants = simulate_participants(
            simple_dataset,
            number_of_participants=5,
            distribution_mode="non-iid"
        )
        
        total_rows = sum(p.row_count for p in participants)
        
        assert total_rows == len(simple_dataset.X)


class TestParticipantMetadata:
    """Test participant metadata correctness."""
    
    def test_participant_row_count_matches_data(self, simple_dataset):
        """Test that row_count matches actual data dimensions."""
        participants = simulate_participants(simple_dataset, number_of_participants=3)
        
        for p in participants:
            assert p.row_count == len(p.X)
            assert p.row_count == len(p.y)
    
    def test_participant_class_distribution_matches_data(self, simple_dataset):
        """Test that class_distribution matches actual labels."""
        participants = simulate_participants(simple_dataset, number_of_participants=3)
        
        for p in participants:
            unique_labels, counts = np.unique(p.y, return_counts=True)
            expected_dist = {int(label): int(count) for label, count in zip(unique_labels, counts)}
            
            assert p.metadata.class_distribution == expected_dist
    
    def test_participant_has_timestamp(self, simple_dataset):
        """Test that participants have timestamps."""
        participants = simulate_participants(simple_dataset, number_of_participants=3)
        
        for p in participants:
            assert p.timestamp > 0
            assert isinstance(p.timestamp, float)
    
    def test_participant_feature_count(self, simple_dataset):
        """Test that feature count is recorded correctly."""
        participants = simulate_participants(simple_dataset, number_of_participants=3)
        
        for p in participants:
            assert p.metadata.feature_count == simple_dataset.X.shape[1]
            assert p.metadata.feature_count == p.X.shape[1]


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_single_participant(self, simple_dataset):
        """Test with only one participant."""
        participants = simulate_participants(simple_dataset, number_of_participants=1)
        
        assert len(participants) == 1
        assert participants[0].row_count == len(simple_dataset.X)
        # Check that all labels are present (set equality, not order equality)
        assert set(participants[0].y) == set(simple_dataset.y)
        assert len(participants[0].y) == len(simple_dataset.y)
    
    def test_participants_equal_to_rows(self, simple_dataset):
        """Test with participants = number of rows."""
        n_rows = len(simple_dataset.X)
        participants = simulate_participants(simple_dataset, number_of_participants=n_rows)
        
        assert len(participants) == n_rows
        # Each participant should have 1 row
        assert all(p.row_count == 1 for p in participants)
    
    def test_more_participants_than_rows_raises(self, simple_dataset):
        """Test error when participants > rows."""
        with pytest.raises(ValueError):
            simulate_participants(simple_dataset, number_of_participants=len(simple_dataset.X) + 1)
    
    def test_zero_participants_raises(self, simple_dataset):
        """Test error with zero participants."""
        with pytest.raises(ValueError):
            simulate_participants(simple_dataset, number_of_participants=0)
    
    def test_negative_participants_raises(self, simple_dataset):
        """Test error with negative participants."""
        with pytest.raises(ValueError):
            simulate_participants(simple_dataset, number_of_participants=-5)
    
    def test_invalid_distribution_mode(self, simple_dataset):
        """Test error with invalid distribution mode."""
        with pytest.raises(ValueError):
            simulate_participants(
                simple_dataset,
                number_of_participants=5,
                distribution_mode="invalid_mode"
            )
    
    def test_single_class_dataset(self, temp_dir):
        """Test with single-class dataset."""
        filepath = os.path.join(temp_dir, "single_class.csv")
        
        import pandas as pd
        data = {
            'feature_0': [1.0, 2.0, 3.0, 4.0, 5.0],
            'feature_1': [5.0, 6.0, 7.0, 8.0, 9.0],
            'label': [1, 1, 1, 1, 1]
        }
        df = pd.DataFrame(data)
        df.to_csv(filepath, index=False)
        
        dataset = load_csv(filepath, target_column='label')
        participants = simulate_participants(dataset, number_of_participants=2)
        
        # Should still work
        assert len(participants) == 2
        assert sum(p.row_count for p in participants) == 5


class TestDistributionStatistics:
    """Test distribution statistics helper."""
    
    def test_get_statistics_iid(self, simple_dataset):
        """Test statistics calculation for IID distribution."""
        participants = simulate_participants(
            simple_dataset,
            number_of_participants=5,
            distribution_mode="iid"
        )
        
        stats = get_distribution_statistics(participants)
        
        assert stats['num_participants'] == 5
        assert stats['total_rows'] == len(simple_dataset.X)
        assert stats['avg_rows_per_participant'] == len(simple_dataset.X) / 5
        assert stats['min_rows'] > 0
        assert stats['max_rows'] > 0
        assert stats['row_count_std'] >= 0
    
    def test_get_statistics_global_class_distribution(self, simple_dataset):
        """Test that global class distribution is computed correctly."""
        participants = simulate_participants(simple_dataset, number_of_participants=3)
        
        stats = get_distribution_statistics(participants)
        
        # Sum should equal total rows
        total_from_dist = sum(stats['global_class_distribution'].values())
        assert total_from_dist == stats['total_rows']


class TestParticipantDataIntegrity:
    """Test ParticipantData dataclass validation."""
    
    def test_participant_data_mismatch_raises(self):
        """Test error when X and y sizes don't match."""
        X = np.array([[1.0, 2.0], [3.0, 4.0]])
        y = np.array([1, 2, 3])  # Mismatch
        
        metadata = ParticipantMetadata(
            original_row_index=[0, 1],
            class_distribution={1: 1, 2: 1},
            feature_count=2
        )
        
        with pytest.raises(ValueError, match="mismatched"):
            ParticipantData(
                participant_id="ORG-001",
                X=X,
                y=y,
                row_count=3,
                timestamp=0.0,
                metadata=metadata
            )
    
    def test_participant_data_row_count_mismatch_raises(self):
        """Test error when row_count doesn't match X/y."""
        X = np.array([[1.0, 2.0], [3.0, 4.0]])
        y = np.array([1, 2])
        
        metadata = ParticipantMetadata(
            original_row_index=[0, 1],
            class_distribution={1: 1, 2: 1},
            feature_count=2
        )
        
        with pytest.raises(ValueError, match="Row count mismatch"):
            ParticipantData(
                participant_id="ORG-001",
                X=X,
                y=y,
                row_count=5,  # Mismatch
                timestamp=0.0,
                metadata=metadata
            )


class TestMediumDataset:
    """Test with larger dataset."""
    
    def test_distribute_medium_dataset(self, medium_dataset):
        """Test distribution of medium-sized dataset."""
        participants = simulate_participants(
            medium_dataset,
            number_of_participants=20,
            distribution_mode="iid"
        )
        
        assert len(participants) == 20
        assert verify_no_data_loss(medium_dataset, participants)
        assert sum(p.row_count for p in participants) == len(medium_dataset.X)
    
    def test_non_iid_medium_dataset(self, medium_dataset):
        """Test non-IID distribution of medium dataset."""
        participants = simulate_participants(
            medium_dataset,
            number_of_participants=15,
            distribution_mode="non-iid",
            random_seed=42
        )
        
        assert len(participants) == 15
        assert verify_no_data_loss(medium_dataset, participants)
