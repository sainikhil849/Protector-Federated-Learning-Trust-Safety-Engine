"""
Tests for dataset loading and validation layer.

Tests cover:
- Valid CSV loading
- File not found
- Empty CSV
- Missing target column
- Missing values in features
- Missing values in labels
- Duplicate rows detection
- Non-numeric features
- Single-class dataset
"""

import pytest
import pandas as pd
import numpy as np
import tempfile
import os
from pathlib import Path

from src.dataset_loader import load_csv, validate_dataset_shape, get_class_imbalance_ratio, DatasetData


@pytest.fixture
def temp_dir():
    """Create temporary directory for test CSVs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def valid_csv_file(temp_dir):
    """Create a valid CSV file for testing."""
    filepath = os.path.join(temp_dir, "valid_dataset.csv")
    
    # Create simple 5-feature, 3-class dataset
    data = {
        'feature_0': [1.2, 2.3, 3.4, 4.5, 5.6],
        'feature_1': [10.1, 20.2, 30.3, 40.4, 50.5],
        'feature_2': [100.0, 200.0, 300.0, 400.0, 500.0],
        'feature_3': [0.5, 1.5, 2.5, 3.5, 4.5],
        'feature_4': [999.9, 888.8, 777.7, 666.6, 555.5],
        'label': [1, 2, 3, 1, 2]
    }
    
    df = pd.DataFrame(data)
    df.to_csv(filepath, index=False)
    
    return filepath


@pytest.fixture
def valid_csv_many_features(temp_dir):
    """Create a CSV with many features matching REAL_DATA_INTEGRATION_SPEC."""
    filepath = os.path.join(temp_dir, "dataset_many_features.csv")
    
    n_rows = 100
    n_features = 128
    
    # Create feature columns
    data = {}
    for i in range(n_features):
        data[f'feature_{i}'] = np.random.uniform(0.1, 170000, n_rows)
    
    # Create labels (6-class classification)
    data['label'] = np.random.randint(1, 7, n_rows)
    
    df = pd.DataFrame(data)
    df.to_csv(filepath, index=False)
    
    return filepath


class TestValidCSVLoading:
    """Test valid CSV loading scenarios."""
    
    def test_load_valid_csv(self, valid_csv_file):
        """Test loading a valid CSV file."""
        dataset = load_csv(valid_csv_file, target_column='label')
        
        assert dataset.X.shape == (5, 5)  # 5 rows, 5 features
        assert dataset.y.shape == (5,)
        assert dataset.metadata.row_count == 5
        assert dataset.metadata.feature_count == 5
        assert dataset.metadata.missing_value_count == 0
        assert dataset.metadata.duplicate_row_count == 0
    
    def test_load_valid_csv_metadata(self, valid_csv_file):
        """Test metadata is correct for valid CSV."""
        dataset = load_csv(valid_csv_file, target_column='label')
        
        assert dataset.metadata.file_path == valid_csv_file
        assert dataset.metadata.target_column == 'label'
        assert dataset.metadata.feature_count == 5
        assert len(dataset.metadata.feature_names) == 5
    
    def test_load_valid_csv_class_distribution(self, valid_csv_file):
        """Test class distribution is correctly computed."""
        dataset = load_csv(valid_csv_file, target_column='label')
        
        # Expected: [1, 2, 3, 1, 2]
        assert dataset.metadata.class_distribution == {1: 2, 2: 2, 3: 1}
    
    def test_load_many_features_csv(self, valid_csv_many_features):
        """Test loading CSV with 128 features (prototype spec)."""
        dataset = load_csv(valid_csv_many_features, target_column='label')
        
        assert dataset.X.shape == (100, 128)
        assert dataset.y.shape == (100,)
        assert dataset.metadata.feature_count == 128
        assert len(dataset.metadata.feature_names) == 128
    
    def test_labels_are_integers(self, valid_csv_file):
        """Test that loaded labels are integers."""
        dataset = load_csv(valid_csv_file, target_column='label')
        
        assert dataset.y.dtype in [np.int32, np.int64]
        assert np.all((dataset.y >= 1) & (dataset.y <= 3))


class TestFileValidation:
    """Test file validation errors."""
    
    def test_missing_file(self, temp_dir):
        """Test error when file does not exist."""
        nonexistent_path = os.path.join(temp_dir, "nonexistent.csv")
        
        with pytest.raises(FileNotFoundError):
            load_csv(nonexistent_path, target_column='label')
    
    def test_empty_csv(self, temp_dir):
        """Test error when CSV is empty."""
        filepath = os.path.join(temp_dir, "empty.csv")
        
        # Create completely empty file
        with open(filepath, 'w') as f:
            f.write("")
        
        with pytest.raises(ValueError, match="empty or has no columns"):
            load_csv(filepath, target_column='label')
    
    def test_csv_no_columns(self, temp_dir):
        """Test error when CSV has no columns."""
        filepath = os.path.join(temp_dir, "no_columns.csv")
        
        # Create CSV with only newlines (no header)
        with open(filepath, 'w') as f:
            f.write("\n\n\n")
        
        with pytest.raises(ValueError, match="empty or has no columns"):
            load_csv(filepath, target_column='label')


class TestTargetColumnValidation:
    """Test target column validation."""
    
    def test_missing_target_column(self, temp_dir):
        """Test error when target column is missing."""
        filepath = os.path.join(temp_dir, "no_target.csv")
        
        data = {
            'feature_0': [1.0, 2.0, 3.0],
            'feature_1': [4.0, 5.0, 6.0],
            'other_column': [7, 8, 9]
        }
        
        df = pd.DataFrame(data)
        df.to_csv(filepath, index=False)
        
        with pytest.raises(ValueError, match="Target column"):
            load_csv(filepath, target_column='label')
    
    def test_target_column_suggestions(self, temp_dir):
        """Test error message lists available columns."""
        filepath = os.path.join(temp_dir, "available_cols.csv")
        
        data = {
            'feature_x': [1.0, 2.0],
            'feature_y': [3.0, 4.0]
        }
        
        df = pd.DataFrame(data)
        df.to_csv(filepath, index=False)
        
        with pytest.raises(ValueError) as exc_info:
            load_csv(filepath, target_column='missing_label')
        
        assert 'feature_x' in str(exc_info.value)
        assert 'feature_y' in str(exc_info.value)


class TestMissingValuesValidation:
    """Test missing value detection and validation."""
    
    def test_csv_with_missing_feature_values(self, temp_dir):
        """Test error when features contain NaN."""
        filepath = os.path.join(temp_dir, "missing_features.csv")
        
        data = {
            'feature_0': [1.0, np.nan, 3.0],
            'feature_1': [4.0, 5.0, 6.0],
            'label': [1, 2, 3]
        }
        
        df = pd.DataFrame(data)
        df.to_csv(filepath, index=False)
        
        with pytest.raises(ValueError, match="missing values"):
            load_csv(filepath, target_column='label')
    
    def test_csv_with_missing_label_values(self, temp_dir):
        """Test error when target contains NaN."""
        filepath = os.path.join(temp_dir, "missing_labels.csv")
        
        data = {
            'feature_0': [1.0, 2.0, 3.0],
            'feature_1': [4.0, 5.0, 6.0],
            'label': [1, np.nan, 3]
        }
        
        df = pd.DataFrame(data)
        df.to_csv(filepath, index=False)
        
        with pytest.raises(ValueError, match="missing values"):
            load_csv(filepath, target_column='label')
    
    def test_csv_missing_value_count(self, temp_dir):
        """Test missing value count is correct."""
        filepath = os.path.join(temp_dir, "some_missing.csv")
        
        # Create a valid CSV first (no missing values)
        data = {
            'feature_0': [1.0, 2.0, 3.0, 4.0],
            'feature_1': [5.0, 6.0, 7.0, 8.0],
            'label': [1, 1, 2, 2]
        }
        
        df = pd.DataFrame(data)
        df.to_csv(filepath, index=False)
        
        dataset = load_csv(filepath, target_column='label')
        
        assert dataset.metadata.missing_value_count == 0


class TestDuplicateRowDetection:
    """Test duplicate row detection."""
    
    def test_csv_with_duplicate_rows(self, temp_dir):
        """Test duplicate row detection."""
        filepath = os.path.join(temp_dir, "duplicates.csv")
        
        data = {
            'feature_0': [1.0, 2.0, 1.0, 3.0],
            'feature_1': [4.0, 5.0, 4.0, 6.0],
            'label': [1, 2, 1, 2]
        }
        
        df = pd.DataFrame(data)
        df.to_csv(filepath, index=False)
        
        dataset = load_csv(filepath, target_column='label')
        
        assert dataset.metadata.duplicate_row_count == 1  # Row 0 and 2 are identical
    
    def test_csv_no_duplicates(self, valid_csv_file):
        """Test duplicate count is 0 for unique rows."""
        dataset = load_csv(valid_csv_file, target_column='label')
        
        assert dataset.metadata.duplicate_row_count == 0


class TestNonNumericFeatures:
    """Test handling of non-numeric features."""
    
    def test_non_numeric_string_feature(self, temp_dir):
        """Test error when features are strings."""
        filepath = os.path.join(temp_dir, "string_features.csv")
        
        data = {
            'feature_0': ['a', 'b', 'c'],
            'feature_1': [4.0, 5.0, 6.0],
            'label': [1, 2, 3]
        }
        
        df = pd.DataFrame(data)
        df.to_csv(filepath, index=False)
        
        with pytest.raises(ValueError, match="non-numeric"):
            load_csv(filepath, target_column='label')
    
    def test_non_numeric_categorical_feature(self, temp_dir):
        """Test error when features are categorical."""
        filepath = os.path.join(temp_dir, "categorical_features.csv")
        
        data = {
            'feature_0': ['red', 'green', 'blue'],
            'feature_1': [4.0, 5.0, 6.0],
            'label': [1, 2, 3]
        }
        
        df = pd.DataFrame(data)
        df.to_csv(filepath, index=False)
        
        with pytest.raises(ValueError, match="non-numeric"):
            load_csv(filepath, target_column='label')
    
    def test_version_1_only_numeric(self, temp_dir):
        """Test error message indicates version 1.0 limitation."""
        filepath = os.path.join(temp_dir, "version1_limit.csv")
        
        data = {
            'feature_0': [1.0, 2.0, 3.0],
            'mixed': ['text', 'data', 'here'],
            'label': [1, 2, 3]
        }
        
        df = pd.DataFrame(data)
        df.to_csv(filepath, index=False)
        
        with pytest.raises(ValueError, match="version 1.0"):
            load_csv(filepath, target_column='label')


class TestSingleClassDataset:
    """Test handling of single-class datasets."""
    
    def test_single_class_dataset_loads(self, temp_dir):
        """Test that single-class dataset loads but is flagged."""
        filepath = os.path.join(temp_dir, "single_class.csv")
        
        data = {
            'feature_0': [1.0, 2.0, 3.0, 4.0],
            'feature_1': [5.0, 6.0, 7.0, 8.0],
            'label': [1, 1, 1, 1]  # All same class
        }
        
        df = pd.DataFrame(data)
        df.to_csv(filepath, index=False)
        
        dataset = load_csv(filepath, target_column='label')
        
        # Should load without error
        assert dataset.X.shape == (4, 2)
        assert dataset.y.shape == (4,)
        
        # But class distribution should show only 1 class
        assert len(dataset.metadata.class_distribution) == 1
        assert dataset.metadata.class_distribution[1] == 4


class TestDatasetDataIntegrity:
    """Test DatasetData dataclass integrity."""
    
    def test_datasetdata_shape_mismatch(self):
        """Test error when X and y have mismatched lengths."""
        X = np.array([[1.0, 2.0], [3.0, 4.0]])
        y = np.array([1, 2, 3])  # Mismatched length
        
        from src.dataset_loader import DatasetMetadata
        
        metadata = DatasetMetadata(
            row_count=3,
            feature_count=2,
            missing_value_count=0,
            duplicate_row_count=0,
            class_distribution={1: 1, 2: 1, 3: 1}
        )
        
        with pytest.raises(ValueError, match="mismatched"):
            DatasetData(X=X, y=y, metadata=metadata)
    
    def test_datasetdata_valid(self, valid_csv_file):
        """Test DatasetData is valid after loading."""
        dataset = load_csv(valid_csv_file, target_column='label')
        
        assert len(dataset.X) == len(dataset.y)
        assert dataset.X.ndim == 2
        assert dataset.y.ndim == 1


class TestValidateDatasetShape:
    """Test dataset shape validation helper."""
    
    def test_validate_shape_2d(self):
        """Test that 2D arrays pass validation."""
        X = np.array([[1.0, 2.0], [3.0, 4.0]])
        
        assert validate_dataset_shape(X) is True
    
    def test_validate_shape_with_expected_features(self):
        """Test validation with expected feature count."""
        X = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
        
        assert validate_dataset_shape(X, expected_features=3) is True
    
    def test_validate_shape_feature_mismatch(self):
        """Test error when feature count doesn't match."""
        X = np.array([[1.0, 2.0], [3.0, 4.0]])
        
        with pytest.raises(ValueError, match="Expected 3 features"):
            validate_dataset_shape(X, expected_features=3)
    
    def test_validate_shape_not_2d(self):
        """Test error when array is not 2D."""
        X = np.array([1.0, 2.0, 3.0])  # 1D array
        
        with pytest.raises(ValueError, match="2D"):
            validate_dataset_shape(X)


class TestClassImbalanceRatio:
    """Test class imbalance ratio calculation."""
    
    def test_balanced_classes(self):
        """Test perfectly balanced classes."""
        class_dist = {1: 10, 2: 10, 3: 10}
        
        ratio = get_class_imbalance_ratio(class_dist)
        
        assert ratio == 1.0
    
    def test_imbalanced_classes(self):
        """Test imbalanced class distribution."""
        class_dist = {1: 100, 2: 10}
        
        ratio = get_class_imbalance_ratio(class_dist)
        
        assert ratio == 10.0
    
    def test_single_class(self):
        """Test single class."""
        class_dist = {1: 50}
        
        ratio = get_class_imbalance_ratio(class_dist)
        
        assert ratio == 1.0
    
    def test_empty_distribution(self):
        """Test empty class distribution."""
        class_dist = {}
        
        ratio = get_class_imbalance_ratio(class_dist)
        
        assert ratio == 1.0


class TestVerboseMode:
    """Test verbose output mode."""
    
    def test_verbose_output(self, valid_csv_file, capsys):
        """Test verbose mode prints metadata."""
        load_csv(valid_csv_file, target_column='label', verbose=True)
        
        captured = capsys.readouterr()
        
        assert "✓ Dataset loaded" in captured.out
        assert "Rows:" in captured.out
        assert "Features:" in captured.out
        assert "Missing values:" in captured.out
        assert "Classes:" in captured.out
    
    def test_non_verbose_output(self, valid_csv_file, capsys):
        """Test quiet mode (verbose=False) doesn't print."""
        load_csv(valid_csv_file, target_column='label', verbose=False)
        
        captured = capsys.readouterr()
        
        assert "Dataset loaded" not in captured.out
