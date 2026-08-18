"""
Dataset loading and validation layer for real data integration.

This module provides functionality to load and validate CSV classification datasets
without modifying the frozen scoring engine.

Version 1.0: Supports single CSV format with numeric features only.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import os
import pandas as pd
import numpy as np


@dataclass
class DatasetMetadata:
    """Metadata about loaded dataset."""
    row_count: int
    feature_count: int
    missing_value_count: int
    duplicate_row_count: int
    class_distribution: Dict[int, int]  # {class_label: count}
    feature_names: List[str] = field(default_factory=list)
    target_column: str = ""
    file_path: str = ""


@dataclass
class DatasetData:
    """Loaded dataset with features, labels, and metadata."""
    X: np.ndarray  # Feature matrix (N × M)
    y: np.ndarray  # Label vector (N,)
    metadata: DatasetMetadata
    
    def __post_init__(self):
        """Validate shapes after initialization."""
        if len(self.X) != len(self.y):
            raise ValueError(
                f"Feature matrix ({len(self.X)} rows) and labels ({len(self.y)} rows) "
                f"have mismatched lengths"
            )


def load_csv(
    filepath: str,
    target_column: str,
    verbose: bool = False
) -> DatasetData:
    """
    Load and validate a CSV classification dataset.
    
    Parameters
    ----------
    filepath : str
        Path to CSV file
    target_column : str
        Name of the column containing labels/targets
    verbose : bool
        Whether to print validation details
    
    Returns
    -------
    DatasetData
        Loaded dataset with features, labels, and metadata
    
    Raises
    ------
    FileNotFoundError
        If CSV file does not exist
    ValueError
        If CSV is empty, target column missing, has missing values,
        or contains non-numeric features
    """
    
    # ========== STEP 1: FILE VALIDATION ==========
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Dataset file not found: {filepath}")
    
    # ========== STEP 2: LOAD CSV ==========
    try:
        df = pd.read_csv(filepath)
    except Exception as e:
        error_msg = str(e)
        if "No columns to parse" in error_msg:
            raise ValueError("Dataset CSV is empty or has no columns")
        raise ValueError(f"Failed to load CSV: {e}")
    
    # ========== STEP 3: EMPTY CHECK ==========
    if df.empty:
        raise ValueError("Dataset CSV is empty (0 rows)")
    
    if len(df.columns) == 0:
        raise ValueError("Dataset CSV has no columns")
    
    # ========== STEP 4: TARGET COLUMN VALIDATION ==========
    if target_column not in df.columns:
        available = list(df.columns)
        raise ValueError(
            f"Target column '{target_column}' not found in CSV. "
            f"Available columns: {available}"
        )
    
    # ========== STEP 5: SEPARATE X AND Y ==========
    y = df[target_column].copy()
    X_df = df.drop(columns=[target_column]).copy()
    
    # ========== STEP 6: VALIDATE LABELS ==========
    # Check for missing values in labels
    if y.isnull().any():
        missing_label_count = y.isnull().sum()
        raise ValueError(
            f"Target column contains {missing_label_count} missing values. "
            f"Cannot have NaN in labels."
        )
    
    # Check that labels are numeric integers
    try:
        y_numeric = y.astype(int)
    except (ValueError, TypeError):
        raise ValueError(
            f"Target column must contain numeric integer values. "
            f"Found non-numeric values: {y.unique()[:5]}"
        )
    
    y = y_numeric.values  # Convert to numpy array
    
    # ========== STEP 7: VALIDATE FEATURES ==========
    # Detect missing values before converting
    missing_value_count = X_df.isnull().sum().sum()
    
    if missing_value_count > 0:
        raise ValueError(
            f"Features contain {missing_value_count} missing values. "
            f"Cannot have NaN in features. Please handle missing values before loading."
        )
    
    # Convert all features to numeric
    try:
        X_numeric = X_df.astype(float)
    except (ValueError, TypeError) as e:
        # Identify which columns are non-numeric
        non_numeric_cols = []
        for col in X_df.columns:
            try:
                pd.to_numeric(X_df[col], errors='coerce')
            except:
                non_numeric_cols.append(col)
        
        raise ValueError(
            f"Features contain non-numeric columns (version 1.0 only supports numeric features). "
            f"Non-numeric columns: {non_numeric_cols}. "
            f"Please convert all features to numeric or remove them."
        )
    
    X = X_numeric.values  # Convert to numpy array
    
    # ========== STEP 8: DETECT DUPLICATES ==========
    duplicate_rows = df.duplicated().sum()
    
    # ========== STEP 9: BUILD METADATA ==========
    # Class distribution
    unique_labels, counts = np.unique(y, return_counts=True)
    class_distribution = {int(label): int(count) for label, count in zip(unique_labels, counts)}
    
    metadata = DatasetMetadata(
        row_count=len(X),
        feature_count=X.shape[1],
        missing_value_count=missing_value_count,
        duplicate_row_count=duplicate_rows,
        class_distribution=class_distribution,
        feature_names=list(X_df.columns),
        target_column=target_column,
        file_path=filepath
    )
    
    # ========== STEP 10: PRINT VALIDATION RESULTS ==========
    if verbose:
        print(f"✓ Dataset loaded: {filepath}")
        print(f"  - Rows: {metadata.row_count}")
        print(f"  - Features: {metadata.feature_count}")
        print(f"  - Missing values: {metadata.missing_value_count}")
        print(f"  - Duplicate rows: {metadata.duplicate_row_count}")
        print(f"  - Classes: {metadata.class_distribution}")
    
    # ========== RETURN DATASETDATA ==========
    return DatasetData(X=X, y=y, metadata=metadata)


def validate_dataset_shape(
    X: np.ndarray,
    expected_features: Optional[int] = None
) -> bool:
    """
    Validate dataset shape matches expectations.
    
    Parameters
    ----------
    X : np.ndarray
        Feature matrix
    expected_features : int, optional
        Expected number of features (e.g., 128 for frozen engine)
    
    Returns
    -------
    bool
        True if valid
    
    Raises
    ------
    ValueError
        If shape doesn't match expectations
    """
    if len(X.shape) != 2:
        raise ValueError(f"Feature matrix must be 2D, got shape {X.shape}")
    
    if expected_features is not None:
        if X.shape[1] != expected_features:
            raise ValueError(
                f"Expected {expected_features} features, got {X.shape[1]}"
            )
    
    return True


def get_class_imbalance_ratio(class_distribution: Dict[int, int]) -> float:
    """
    Calculate class imbalance ratio (max_count / min_count).
    
    Parameters
    ----------
    class_distribution : Dict[int, int]
        {class_label: count}
    
    Returns
    -------
    float
        Imbalance ratio (1.0 = perfectly balanced)
    """
    counts = list(class_distribution.values())
    if len(counts) == 0:
        return 1.0
    
    return max(counts) / max(1, min(counts))
