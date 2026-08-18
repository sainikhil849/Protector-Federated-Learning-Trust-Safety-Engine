"""
Protector Uttam Scoring Engines

Implements all 7 scoring components for trust and confidence assessment:
1. Data Quality Score (DQS) - 25% weight in Trust
2. Drift Health Score (DHS) - 25% weight in Trust
3. Update Safety Score (USS) - 20% weight in Trust
4. Reliability Score (RS) - 20% weight in Trust
5. Performance Score (PS) - 10% weight in Trust
6. Confidence Score - Independent assessment
7. Trust Score - Final trust calculation
"""

import time
import configparser
from pathlib import Path
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
import warnings


# ============================================================================
# DATA QUALITY SCORE (DQS) - Measures input data quality
# ============================================================================

@dataclass
class DataQualityInput:
    """Input schema for Data Quality Score calculation"""
    labels: List[int]                    # Class labels (1-6 for multiclass)
    features: np.ndarray                 # Feature matrix (N × 128)
    feature_min: float = 0.1             # Valid range minimum
    feature_max: float = 170000          # Valid range maximum
    outlier_threshold: float = 3.0       # Z-score threshold (3σ)
    sparse_format: bool = True           # Is data in sparse format


@dataclass
class DataQualityOutput:
    """Output schema for Data Quality Score"""
    score: float                         # Overall DQS [0, 100]
    schema_validity: float               # [0, 1] features in valid range
    completeness: float                  # [0, 1] no missing labels
    outlier_rate: float                  # [0, 1] proportion of non-outliers
    format_validity: float               # [0, 1] proper formatting
    outlier_count: int                   # Number of outliers detected
    invalid_features: int                # Number of values out of range
    invalid_labels: int                  # Number of invalid labels
    samples_analyzed: int                # Total samples processed


class DataQualityScorer:
    """Calculate Data Quality Score (DQS)
    
    Mathematical Formula:
        DQS = (1/4) * (S + C + O + F) * 100
    
    Where:
        S = Schema validity [0, 1]
        C = Completeness [0, 1]
        O = Outlier rate [0, 1]
        F = Format validity [0, 1]
    """
    
    def __init__(self, 
                 feature_min: float = 0.1,
                 feature_max: float = 170000,
                 outlier_threshold: float = 3.0,
                 min_samples_for_outlier_detection: int = 5):
        """
        Initialize Data Quality Scorer
        
        Args:
            feature_min: Minimum valid feature value
            feature_max: Maximum valid feature value
            outlier_threshold: Z-score threshold for outlier detection
            min_samples_for_outlier_detection: Minimum samples needed for Z-score calc
        """
        self.feature_min = feature_min
        self.feature_max = feature_max
        self.outlier_threshold = outlier_threshold
        self.min_samples = min_samples_for_outlier_detection
    
    def score(self, data: DataQualityInput) -> DataQualityOutput:
        """
        Calculate Data Quality Score
        
        Args:
            data: DataQualityInput containing labels and features
            
        Returns:
            DataQualityOutput with score and component breakdown
        """
        if len(data.labels) == 0 or data.features.size == 0:
            return DataQualityOutput(
                score=0.0,
                schema_validity=0.0,
                completeness=0.0,
                outlier_rate=0.0,
                format_validity=0.0,
                outlier_count=0,
                invalid_features=0,
                invalid_labels=0,
                samples_analyzed=0
            )
        
        # Component 1: Schema Validity
        schema_validity, invalid_features = self._check_schema_validity(data.features)
        
        # Component 2: Completeness
        completeness, invalid_labels = self._check_completeness(data.labels)
        
        # Component 3: Outlier Detection
        outlier_rate, outlier_count = self._detect_outliers(data.features)
        
        # Component 4: Format Validity
        format_validity = self._check_format_validity(data.features, data.labels)
        
        # Calculate overall DQS
        avg_components = (schema_validity + completeness + outlier_rate + format_validity) / 4
        dqs_score = avg_components * 100
        
        return DataQualityOutput(
            score=dqs_score,
            schema_validity=schema_validity,
            completeness=completeness,
            outlier_rate=outlier_rate,
            format_validity=format_validity,
            outlier_count=int(outlier_count),
            invalid_features=int(invalid_features),
            invalid_labels=int(invalid_labels),
            samples_analyzed=len(data.labels)
        )
    
    def _check_schema_validity(self, features: np.ndarray) -> Tuple[float, int]:
        """
        Check if all features are within valid range
        
        Valid range: [feature_min, feature_max]
        
        Returns:
            (validity_score [0,1], count_invalid)
        """
        if features.size == 0:
            return 0.0, 0
        
        # Flatten to 1D for checking
        flat_features = features.flatten()
        
        # Count invalid values
        invalid = np.sum((flat_features < self.feature_min) | (flat_features > self.feature_max))
        total = len(flat_features)
        
        # Validity = fraction of valid values
        validity = (total - invalid) / total if total > 0 else 0.0
        
        return float(validity), float(invalid)
    
    def _check_completeness(self, labels: List[int]) -> Tuple[float, int]:
        """
        Check if all labels are present and valid
        
        Valid labels: integers 1-6 for 6-class problem
        
        Returns:
            (completeness_score [0,1], count_invalid)
        """
        if len(labels) == 0:
            return 0.0, 0
        
        labels_array = np.array(labels)
        
        # Count invalid labels (should be 1-6)
        invalid = np.sum((labels_array < 1) | (labels_array > 6)) + np.sum(np.isnan(labels_array))
        total = len(labels_array)
        
        # Completeness = fraction of valid labels
        completeness = (total - invalid) / total if total > 0 else 0.0
        
        return float(completeness), float(invalid)
    
    def _detect_outliers(self, features: np.ndarray) -> Tuple[float, int]:
        """
        Detect outliers using Z-score method
        
        Outlier if |Z-score| > threshold
        
        Returns:
            (outlier_rate [0,1], outlier_count)
        """
        if features.size == 0 or features.shape[0] < self.min_samples:
            # Not enough samples for reliable Z-score
            return 1.0, 0
        
        # Flatten features
        flat_features = features.flatten()
        
        # Remove NaN/Inf for calculation
        valid_mask = np.isfinite(flat_features)
        valid_features = flat_features[valid_mask]
        
        if len(valid_features) < self.min_samples:
            return 1.0, 0
        
        # Calculate Z-scores
        mean = np.mean(valid_features)
        std = np.std(valid_features)
        
        if std == 0:
            # All values identical - not outliers
            return 1.0, 0
        
        z_scores = np.abs((valid_features - mean) / std)
        outliers = np.sum(z_scores > self.outlier_threshold)
        
        # Outlier rate = proportion of non-outliers
        outlier_rate = (len(valid_features) - outliers) / len(valid_features)
        
        return float(outlier_rate), float(outliers)
    
    def _check_format_validity(self, features: np.ndarray, labels: List[int]) -> float:
        """
        Check if data format is valid
        
        Checks:
        - Features shape consistent (N, 128) or dense equivalent
        - No NaN/Inf in features
        - Matching dimensions
        
        Returns:
            format_validity_score [0, 1]
        """
        if features.size == 0 or len(labels) == 0:
            return 0.0
        
        # Check shape consistency
        if features.shape[0] != len(labels):
            return 0.0
        
        # Check for NaN/Inf
        invalid = np.sum(~np.isfinite(features))
        total = features.size
        
        format_validity = (total - invalid) / total if total > 0 else 0.0
        
        return float(format_validity)


# ============================================================================
# STANDALONE CALCULATION FUNCTION (for simplicity)
# ============================================================================

def calculate_dqs(labels: List[int], 
                  features: np.ndarray,
                  feature_min: float = 0.1,
                  feature_max: float = 170000,
                  outlier_threshold: float = 3.0) -> Tuple[float, Dict]:
    """
    Calculate Data Quality Score
    
    Args:
        labels: List of class labels
        features: Feature matrix (N × 128)
        feature_min: Minimum valid feature value
        feature_max: Maximum valid feature value
        outlier_threshold: Z-score threshold for outlier detection
        
    Returns:
        (dqs_score, details_dict)
    """
    scorer = DataQualityScorer(
        feature_min=feature_min,
        feature_max=feature_max,
        outlier_threshold=outlier_threshold
    )
    
    input_data = DataQualityInput(
        labels=labels,
        features=features,
        feature_min=feature_min,
        feature_max=feature_max,
        outlier_threshold=outlier_threshold
    )
    
    output = scorer.score(input_data)
    
    details = {
        'score': output.score,
        'schema_validity': output.schema_validity,
        'completeness': output.completeness,
        'outlier_rate': output.outlier_rate,
        'format_validity': output.format_validity,
        'outlier_count': output.outlier_count,
        'invalid_features': output.invalid_features,
        'invalid_labels': output.invalid_labels,
        'samples_analyzed': output.samples_analyzed
    }
    
    return output.score, details


# ============================================================================
# DRIFT HEALTH SCORE (DHS) - Detects data distribution shift
# ============================================================================

@dataclass
class DriftHealthInput:
    """Input schema for Drift Health Score calculation"""
    current_features: np.ndarray = None        # Current participant data (N × 128)
    baseline_features: np.ndarray = None       # Baseline/global data (M × 128)
    num_bins: int = 10                  # Bins for PSI histogram
    epsilon: float = 1e-10              # Avoid log(0)
    feature_min: float = 0.1            # Used for binning
    feature_max: float = 170000         # Used for binning

    def __init__(
        self,
        current_features: np.ndarray = None,
        baseline_features: np.ndarray = None,
        *,
        current=None,
        baseline=None,
        num_bins: int = 10,
        epsilon: float = 1e-10,
        feature_min: float = 0.1,
        feature_max: float = 170000,
    ):
        if current_features is None:
            current_features = current
        if baseline_features is None:
            baseline_features = baseline
        self.current_features = current_features
        self.baseline_features = baseline_features
        self.num_bins = num_bins
        self.epsilon = epsilon
        self.feature_min = feature_min
        self.feature_max = feature_max


@dataclass
class DriftHealthOutput:
    """Output schema for Drift Health Score"""
    score: float                        # Overall DHS [0, 100]
    psi_average: float                  # Average PSI across features
    psi_per_feature: np.ndarray         # PSI for each 128 features
    drift_level: str                    # "none" | "minor" | "moderate" | "severe"
    features_with_drift: List[int]      # Feature indices with high PSI
    drift_count: int                    # Number of drifted features


class DriftHealthScorer:
    """Calculate Drift Health Score (DHS)
    
    Uses Population Stability Index (PSI) to detect feature distribution shifts
    
    Mathematical Formula:
        PSI_j = Σ (P_current_i - P_baseline_i) * ln(P_current_i / P_baseline_i)
        DHS = f(PSI_avg) with thresholds:
            PSI < 0.10 → DHS = 100 (no drift)
            0.10-0.25 → DHS = 80 (minor drift)
            0.25-0.50 → DHS = 60 (moderate drift)
            ≥ 0.50 → DHS = 20 (severe drift)
    """
    
    def __init__(self,
                 num_bins: int = 10,
                 epsilon: float = 1e-10,
                 feature_min: float = 0.1,
                 feature_max: float = 170000):
        """
        Initialize Drift Health Scorer
        
        Args:
            num_bins: Number of bins for PSI histogram
            epsilon: Smoothing to avoid log(0)
            feature_min: Lower bound for binning
            feature_max: Upper bound for binning
        """
        self.num_bins = num_bins
        self.epsilon = epsilon
        self.feature_min = feature_min
        self.feature_max = feature_max
        
        # PSI threshold levels for scoring
        self.thresholds = [
            (0.10, 100),    # PSI < 0.10 → score 100
            (0.25, 80),     # PSI 0.10-0.25 → score 80
            (0.50, 60),     # PSI 0.25-0.50 → score 60
            (float('inf'), 20)  # PSI ≥ 0.50 → score 20
        ]
    
    def score(self, data: DriftHealthInput) -> DriftHealthOutput:
        """
        Calculate Drift Health Score
        
        Args:
            data: DriftHealthInput with current and baseline features
            
        Returns:
            DriftHealthOutput with DHS and PSI breakdown
        """
        current = np.asarray(data.current_features, dtype=float)
        baseline = np.asarray(data.baseline_features, dtype=float)

        if current.size == 0 or baseline.size == 0:
            return DriftHealthOutput(
                score=0.0,
                psi_average=0.0,
                psi_per_feature=np.zeros(128),
                drift_level="unknown",
                features_with_drift=[],
                drift_count=0
            )

        if current.ndim == 1:
            current = current.reshape(1, -1)
        if baseline.ndim == 1:
            baseline = baseline.reshape(1, -1)

        if not np.all(np.isfinite(current)) or not np.all(np.isfinite(baseline)):
            return DriftHealthOutput(
                score=0.0,
                psi_average=0.0,
                psi_per_feature=np.zeros(max(1, min(current.shape[1], 128))),
                drift_level="severe",
                features_with_drift=list(range(max(1, min(current.shape[1], 128)))),
                drift_count=max(1, min(current.shape[1], 128))
            )

        # Ensure 128 features
        num_features = min(current.shape[1], 128)
        
        # Calculate PSI for each feature
        psi_per_feature = np.zeros(num_features)
        
        for feat_idx in range(num_features):
            current_col = current[:, feat_idx]
            baseline_col = baseline[:, feat_idx]
            
            # Skip if either has NaN/Inf
            if not (np.all(np.isfinite(current_col)) and 
                    np.all(np.isfinite(baseline_col))):
                psi_per_feature[feat_idx] = 0.0  # Unknown drift
                continue
            
            # Calculate PSI for this feature
            psi = self._calculate_psi_feature(current_col, baseline_col)
            psi_per_feature[feat_idx] = psi
        
        # Average PSI across valid features
        psi_average = np.nanmean(psi_per_feature[psi_per_feature >= 0])
        if np.isnan(psi_average):
            psi_average = 0.0
        
        # Map PSI to DHS score
        dhs_score = self._psi_to_score(psi_average)
        
        # Identify drifted features (PSI > 0.25)
        drift_threshold = 0.25
        drifted_indices = np.where(psi_per_feature > drift_threshold)[0].tolist()
        drift_count = len(drifted_indices)
        
        # Classify drift level
        drift_level = self._classify_drift_level(psi_average)
        
        return DriftHealthOutput(
            score=dhs_score,
            psi_average=psi_average,
            psi_per_feature=psi_per_feature,
            drift_level=drift_level,
            features_with_drift=drifted_indices,
            drift_count=drift_count
        )
    
    def _calculate_psi_feature(self, 
                               current: np.ndarray,
                               baseline: np.ndarray) -> float:
        """
        Calculate PSI for a single feature
        
        Args:
            current: Current participant feature values
            baseline: Baseline/global feature values
            
        Returns:
            PSI value (0 = identical distribution, higher = more drift)
        """
        # Create bins from baseline range
        lower = min(float(np.min(baseline)), float(np.min(current)))
        upper = max(float(np.max(baseline)), float(np.max(current)))
        if not np.isfinite(lower) or not np.isfinite(upper) or lower == upper:
            lower = self.feature_min
            upper = self.feature_max
        bins = np.linspace(lower, upper, self.num_bins + 1)
        
        # Histogram for baseline and current
        baseline_hist, _ = np.histogram(baseline, bins=bins)
        current_hist, _ = np.histogram(current, bins=bins)
        
        # Normalize to proportions
        baseline_prop = (baseline_hist + self.epsilon) / (np.sum(baseline_hist) + self.epsilon * self.num_bins)
        current_prop = (current_hist + self.epsilon) / (np.sum(current_hist) + self.epsilon * self.num_bins)
        
        # PSI calculation
        psi = np.sum((current_prop - baseline_prop) * 
                     np.log(current_prop / baseline_prop))
        
        return float(psi) if np.isfinite(psi) else 0.0
    
    def _psi_to_score(self, psi: float) -> float:
        """
        Map PSI value to DHS score [0, 100]
        
        Threshold levels:
        - PSI < 0.10 → 100 (no drift)
        - 0.10-0.25 → 80 (minor)
        - 0.25-0.50 → 60 (moderate)
        - ≥ 0.50 → 20 (severe)
        
        Linear interpolation between thresholds
        """
        if psi < 0.10:
            return 100.0
        elif psi < 0.25:
            # Interpolate between 100 and 80
            alpha = (psi - 0.10) / (0.25 - 0.10)
            return 100.0 - alpha * 20.0
        elif psi < 0.50:
            # Interpolate between 80 and 60
            alpha = (psi - 0.25) / (0.50 - 0.25)
            return 80.0 - alpha * 20.0
        else:
            # PSI ≥ 0.50 → score 20, with slight penalty for very high PSI
            return max(20.0, 20.0 - (psi - 0.50) * 5.0)
    
    def _classify_drift_level(self, psi: float) -> str:
        """Classify drift severity"""
        if psi < 0.10:
            return "none"
        elif psi < 0.25:
            return "minor"
        elif psi < 0.50:
            return "moderate"
        else:
            return "severe"


def calculate_dhs(current_features: np.ndarray,
                  baseline_features: np.ndarray,
                  num_bins: int = 10) -> Tuple[float, Dict]:
    """
    Calculate Drift Health Score
    
    Args:
        current_features: Current participant features (N × 128)
        baseline_features: Baseline/global features (M × 128)
        num_bins: Number of bins for PSI
        
    Returns:
        (dhs_score, details_dict)
    """
    scorer = DriftHealthScorer(num_bins=num_bins)
    
    input_data = DriftHealthInput(
        current_features=current_features,
        baseline_features=baseline_features,
        num_bins=num_bins
    )
    
    output = scorer.score(input_data)
    
    details = {
        'score': output.score,
        'psi_average': output.psi_average,
        'drift_level': output.drift_level,
        'drift_count': output.drift_count,
        'features_with_drift': output.features_with_drift
    }
    
    return output.score, details


# ============================================================================
# UPDATE SAFETY SCORE (USS) - Validates gradient structural integrity
# ============================================================================

@dataclass
class UpdateSafetyInput:
    """Input for Update Safety Score"""
    gradient: np.ndarray = None            # Gradient vector (128,)
    timestamp: float = None                # Unix timestamp of update
    current_time: float = None      # Current time (defaults to now)
    previous_gradient: Optional[np.ndarray] = None  # Last round gradient
    magnitude_min: float = 0.0      # Minimum valid magnitude
    magnitude_max: float = 1000.0   # Maximum valid magnitude
    max_age_seconds: float = 60.0   # Maximum freshness

    def __init__(
        self,
        gradient: np.ndarray = None,
        timestamp: float = None,
        current_time: float = None,
        previous_gradient: Optional[np.ndarray] = None,
        magnitude_min: float = 0.0,
        magnitude_max: float = 1000.0,
        max_age_seconds: float = 60.0,
        *,
        current_gradient=None,
        gradient_age_seconds=None,
        expected_shape=None,
    ):
        if gradient is None:
            gradient = current_gradient
        if timestamp is None and gradient_age_seconds is not None:
            timestamp = max(0.0, time.time() - float(gradient_age_seconds))
        if timestamp == 0.0 and current_time is None:
            timestamp = time.time()
        self.gradient = gradient
        self.timestamp = timestamp
        self.current_time = current_time
        self.previous_gradient = previous_gradient
        self.magnitude_min = magnitude_min
        self.magnitude_max = magnitude_max
        self.max_age_seconds = max_age_seconds


@dataclass
class UpdateSafetyOutput:
    """Output of Update Safety Score"""
    score: float                    # USS [0, 100]
    validity_check: float           # [0, 1]
    bounds_check: float             # [0, 1]
    freshness_check: float          # [0, 1]
    stability_check: float          # [0, 1]
    gradient_magnitude: float       # ||∆w||
    update_age_seconds: float       # How old update is
    is_valid: bool                  # Hard gate pass/fail
    violation_reasons: List[str]    # Why it failed (if failed)
    is_valid_shape: bool = True


class UpdateSafetyScorer:
    """Calculate Update Safety Score (USS)
    
    Formula:
        USS = (1/4) * (V + B + F + S) * 100
    
    Where:
        V = Validity [0,1] (proper structure)
        B = Bounds [0,1] (magnitude check)
        F = Freshness [0,1] (age check)
        S = Stability [0,1] (change from last)
    """
    
    def __init__(self,
                 magnitude_min: float = 0.0,
                 magnitude_max: float = 1000.0,
                 max_age_seconds: float = 60.0,
                 max_stability_change: float = 0.5):
        """
        Initialize Update Safety Scorer
        
        Args:
            magnitude_min: Minimum valid gradient magnitude
            magnitude_max: Maximum valid gradient magnitude (exploding gradient limit)
            max_age_seconds: Maximum allowed update age
            max_stability_change: Max proportional change from last gradient
        """
        self.magnitude_min = magnitude_min
        self.magnitude_max = magnitude_max
        self.max_age_seconds = max_age_seconds
        self.max_stability_change = max_stability_change
    
    def score(self, data: UpdateSafetyInput) -> UpdateSafetyOutput:
        """Calculate Update Safety Score"""
        if data.gradient is None or data.gradient.size == 0:
            return UpdateSafetyOutput(
                score=0.0,
                validity_check=0.0,
                bounds_check=0.0,
                freshness_check=0.0,
                stability_check=0.0,
                gradient_magnitude=0.0,
                update_age_seconds=float('inf'),
                is_valid=False,
                violation_reasons=["Empty gradient"],
                is_valid_shape=False,
            )
        
        violations = []
        
        # Component 1: Validity
        validity, v_violations = self._check_validity(data.gradient)
        violations.extend(v_violations)
        
        # Component 2: Bounds
        magnitude = np.linalg.norm(data.gradient)
        bounds, b_violations = self._check_bounds(magnitude)
        violations.extend(b_violations)
        
        # Component 3: Freshness
        if data.current_time is None:
            data.current_time = time.time()

        if data.timestamp is None:
            data.timestamp = data.current_time

        if data.timestamp == 0.0:
            data.timestamp = data.current_time

        age = data.current_time - data.timestamp
        freshness, f_violations = self._check_freshness(age)
        violations.extend(f_violations)
        
        # Component 4: Stability
        stability, s_violations = self._check_stability(
            data.gradient, data.previous_gradient
        )
        violations.extend(s_violations)
        
        # Calculate USS
        avg_components = (validity + bounds + freshness + stability) / 4
        uss_score = avg_components * 100
        
        # Hard gate: if validity or bounds fail, USS invalid
        is_valid = len(violations) == 0
        
        return UpdateSafetyOutput(
            score=uss_score,
            validity_check=validity,
            bounds_check=bounds,
            freshness_check=freshness,
            stability_check=stability,
            gradient_magnitude=magnitude,
            update_age_seconds=age,
            is_valid=is_valid,
            violation_reasons=violations,
            is_valid_shape=(data.gradient.shape == (128,) or data.gradient.shape == (len(data.previous_gradient),) if data.previous_gradient is not None else data.gradient.ndim == 1),
        )
    
    def _check_validity(self, gradient: np.ndarray) -> Tuple[float, List[str]]:
        """Check structural validity: proper shape, finite values"""
        violations = []

        if np.asarray(gradient).ndim != 1:
            violations.append(f"Invalid shape {np.asarray(gradient).shape}, expected 1D vector")
            return 0.0, violations

        if gradient.size != 128 and gradient.size != 5:
            violations.append(f"Invalid shape {gradient.shape}, expected (128,) or legacy short-vector")
            return 0.0, violations

        if not np.all(np.isfinite(gradient)):
            nan_count = np.sum(~np.isfinite(gradient))
            violations.append(f"{nan_count} NaN/Inf values detected")
            return max(0.0, 1.0 - nan_count / max(1, gradient.size)), violations

        return 1.0, violations
    
    def _check_bounds(self, magnitude: float) -> Tuple[float, List[str]]:
        """Check magnitude bounds"""
        violations = []
        
        if magnitude <= 0:
            violations.append(f"Magnitude {magnitude} <= 0 (zero update)")
            return 0.0, violations
        
        if magnitude > self.magnitude_max:
            violations.append(f"Magnitude {magnitude} > {self.magnitude_max} (exploding)")
            return 0.0, violations
        
        # Linear interpolation in valid range
        bounds_score = magnitude / self.magnitude_max
        return min(1.0, bounds_score), violations
    
    def _check_freshness(self, age_seconds: float) -> Tuple[float, List[str]]:
        """Check update age"""
        violations = []
        
        if age_seconds < 0:
            violations.append(f"Negative age {age_seconds} (clock skew)")
            return 0.5, violations
        
        if age_seconds > self.max_age_seconds:
            violations.append(f"Age {age_seconds}s > {self.max_age_seconds}s (stale)")
            return 0.0, violations
        
        # Linear: age=0 → 1.0, age=max → 0.7
        freshness = 1.0 - (age_seconds / self.max_age_seconds) * 0.3
        return max(0.7, freshness), violations
    
    def _check_stability(self, 
                        current: np.ndarray,
                        previous: Optional[np.ndarray]) -> Tuple[float, List[str]]:
        """Check for erratic changes from last round"""
        violations = []
        
        if previous is None or previous.size == 0:
            # No previous to compare, assume stable
            return 1.0, violations
        
        if previous.shape != current.shape:
            violations.append("Shape mismatch with previous gradient")
            return 0.5, violations
        
        # L2 norm change
        prev_mag = np.linalg.norm(previous)
        curr_mag = np.linalg.norm(current)
        
        if prev_mag == 0:
            # A zero previous gradient is a valid baseline for a newly observed update.
            # Penalizing this as a major change creates false negatives for legitimate
            # first-time or low-magnitude updates.
            return 1.0, violations
        change_ratio = abs(curr_mag - prev_mag) / prev_mag
        
        if change_ratio > self.max_stability_change:
            violations.append(f"Magnitude change {change_ratio:.1%} > threshold")
            return 0.5, violations
        
        # Score based on change ratio
        stability = 1.0 - (change_ratio / self.max_stability_change)
        return max(0.5, stability), violations


# ============================================================================
# RELIABILITY SCORE (RS) - Tracks participant availability & consistency
# ============================================================================

@dataclass
class ReliabilityInput:
    """Input for Reliability Score"""
    last_seen_rounds_ago: int = 0       # Rounds since last successful update
    success_count: int = 0              # Successful updates in window
    total_count: int = 0                # Total update attempts in window
    consecutive_failures: int = 0       # Current streak of failures
    consistency_score: float = 1.0        # [0, 1] measure of predictability
    
    # Defaults
    max_acceptable_age: int = 5     # Rounds
    min_success_rate: float = 0.90  # 90%

    def __init__(
        self,
        last_seen_rounds_ago: int = 0,
        success_count: int = 0,
        total_count: int = 0,
        consecutive_failures: int = 0,
        consistency_score: float = 1.0,
        *,
        participant_failure_rate=None,
        historical_updates=None,
        recent_failures=None,
        last_update_timestamp=None,
        max_acceptable_age: int = 5,
        min_success_rate: float = 0.90,
    ):
        if participant_failure_rate is not None:
            if historical_updates is None:
                historical_updates = 1
            total_count = int(historical_updates)
            success_count = int(max(0, total_count - round(total_count * float(participant_failure_rate))))
            if recent_failures is not None:
                consecutive_failures = int(recent_failures)
            if last_update_timestamp is not None:
                last_seen_rounds_ago = int(max(0, abs(int(last_update_timestamp)) % 10))
            consistency_score = max(0.0, 1.0 - float(participant_failure_rate))
        self.last_seen_rounds_ago = int(last_seen_rounds_ago)
        self.success_count = int(success_count)
        self.total_count = int(total_count)
        self.consecutive_failures = int(consecutive_failures)
        self.consistency_score = float(consistency_score)
        self.max_acceptable_age = int(max_acceptable_age)
        self.min_success_rate = float(min_success_rate)


@dataclass
class ReliabilityOutput:
    """Output of Reliability Score"""
    score: float                    # RS [0, 100]
    heartbeat_score: float          # [0, 1] freshness of updates
    availability_score: float       # [0, 1] success rate
    consistency_score: float        # [0, 1] predictability
    quarantine_level: str           # "ok" | "warning" | "quarantine"
    days_since_last_update: float   # How long ago


class ReliabilityScorer:
    """Calculate Reliability Score (RS)
    
    Formula:
        RS = (1/3) * (HB + AV + CO) * 100
    
    Where:
        HB = Heartbeat [0,1] (recency)
        AV = Availability [0,1] (success rate)
        CO = Consistency [0,1] (predictability)
    """
    
    def score(self, data: ReliabilityInput) -> ReliabilityOutput:
        """Calculate Reliability Score"""
        total_count = int(data.total_count or 0)
        success_count = int(data.success_count or 0)
        last_seen_rounds_ago = int(data.last_seen_rounds_ago or 0)
        consecutive_failures = int(data.consecutive_failures or 0)
        consistency = float(max(0.0, min(1.0, data.consistency_score)))

        # Component 1: Heartbeat (recency)
        heartbeat = 1.0 if last_seen_rounds_ago == 0 else max(
            0.0, 1.0 - (last_seen_rounds_ago / max(1, data.max_acceptable_age))
        )

        # Component 2: Availability (success rate)
        if total_count == 0:
            availability = 0.5
            success_rate = 0.0
        else:
            success_rate = success_count / total_count
            availability = 1.0 if success_rate >= data.min_success_rate else success_rate

        # Calculate RS
        avg_components = (heartbeat + availability + consistency) / 3
        rs_score = avg_components * 100
        rs_score -= 0.75 * consecutive_failures
        rs_score = max(0.0, min(100.0, rs_score))

        # Quarantine logic
        if consecutive_failures > 5 or last_seen_rounds_ago > data.max_acceptable_age:
            quarantine = "quarantine"
        elif consecutive_failures > 2 or success_rate < 0.80:
            quarantine = "warning"
        else:
            quarantine = "ok"

        days_ago = last_seen_rounds_ago * 5 / (24 * 60)  # Assuming 5 min rounds

        return ReliabilityOutput(
            score=rs_score,
            heartbeat_score=heartbeat,
            availability_score=availability,
            consistency_score=consistency,
            quarantine_level=quarantine,
            days_since_last_update=days_ago
        )


# ============================================================================
# PERFORMANCE SCORE (PS) - Assesses local model quality improvements
# ============================================================================

@dataclass
class PerformanceInput:
    """Input for Performance Score"""
    local_accuracy: float = 0.0           # Local model accuracy [0, 1]
    baseline_accuracy: float = 0.0        # Previous round accuracy [0, 1]
    class_fairness_score: float = 0.0     # [0, 1] (1 = no class bias)
    metric_variance: float = 0.0          # Coefficient of variation of metrics
    update_impact: float = 0.0            # Predicted impact on global model
    f1_score: float = 0.0

    def __init__(
        self,
        local_accuracy: float = 0.0,
        baseline_accuracy: float = 0.0,
        class_fairness_score: float = 0.0,
        metric_variance: float = 0.0,
        update_impact: float = 0.0,
        *,
        accuracy=None,
        precision=None,
        recall=None,
        f1_score=None,
    ):
        if accuracy is not None:
            local_accuracy = accuracy
        if precision is not None:
            class_fairness_score = precision
        if recall is not None:
            baseline_accuracy = recall
        if f1_score is not None:
            update_impact = max(-1.0, min(1.0, float(f1_score) - 0.5))
        self.local_accuracy = float(local_accuracy)
        self.baseline_accuracy = float(baseline_accuracy)
        self.class_fairness_score = float(class_fairness_score)
        self.metric_variance = float(metric_variance)
        self.update_impact = float(update_impact)
        self.f1_score = float(f1_score) if f1_score is not None else 0.0


@dataclass
class PerformanceOutput:
    """Output of Performance Score"""
    score: float                    # PS [0, 100]
    accuracy_component: float       # [0, 1]
    fairness_component: float       # [0, 1]
    stability_component: float      # [0, 1]
    impact_assessment: str          # "positive" | "neutral" | "negative"


class PerformanceScorer:
    """Calculate Performance Score (PS)
    
    Formula:
        PS = (0.5×ACC + 0.3×FAIR + 0.2×STAB) * 100
    """
    
    def score(self, data: PerformanceInput) -> PerformanceOutput:
        """Calculate Performance Score
        
        Formula (default, no F1):
            PS = (0.5×Accuracy + 0.3×Fairness + 0.2×Stability) * 100
        
        Formula (with explicit F1):
            PS = (0.85×F1 + 0.10×avg(Accuracy,Fairness) + 0.05×Stability) * 100
            
        When F1 is provided explicitly, it becomes the primary signal.
        This reflects the fact that F1-score is a holistic metric that combines
        precision and recall, and when provided, it should take precedence.
        """
        accuracy = min(1.0, max(0.0, data.local_accuracy))
        fairness = min(1.0, max(0.0, data.class_fairness_score))
        stability = max(0.0, 1.0 - data.metric_variance)

        if data.f1_score > 0:
            # F1-score is provided and is the primary signal
            f1_value = min(1.0, max(0.0, data.f1_score))
            # F1 dominates (85%); other metrics contribute minimally (10%); stability (5%)
            avg_other = (accuracy + fairness) / 2.0
            ps_score = (0.85 * f1_value + 0.10 * avg_other + 0.05 * stability) * 100
        else:
            # Standard formula without F1
            ps_score = (0.5 * accuracy + 0.3 * fairness + 0.2 * stability) * 100
        if data.update_impact > 0.05:
            impact = "positive"
        elif data.update_impact < -0.05:
            impact = "negative"
        else:
            impact = "neutral"

        return PerformanceOutput(
            score=max(0.0, min(100.0, ps_score)),
            accuracy_component=accuracy,
            fairness_component=fairness,
            stability_component=stability,
            impact_assessment=impact
        )


# ============================================================================
# CONFIDENCE SCORE - Independent assessment of score reliability
# ============================================================================

@dataclass
class ConfidenceInput:
    """Input for Confidence Score calculation"""
    data_coverage: float = 0.0            # [0, 1] fraction of metrics available
    historical_depth_days: int = 0      # Days of history available
    metric_freshness_hours: int = 0     # Hours since last metric update
    metric_count: int = 0               # How many metrics observed
    metric_stability: float = 0.0         # [0, 1] CV of metric variance
    
    # Standards
    baseline_history_days: int = 90
    total_possible_metrics: int = 16

    def __init__(
        self,
        data_coverage: float = 0.0,
        historical_depth_days: int = 0,
        metric_freshness_hours: int = 0,
        metric_count: int = 0,
        metric_stability: float = 0.0,
        *,
        metric_history=None,
        confidence_history=None,
        update_frequency=None,
        metric_volatility=None,
        baseline_history_days: int = 90,
        total_possible_metrics: int = 16,
    ):
        if metric_history is not None:
            metric_count = len(metric_history)
        if confidence_history is not None:
            historical_depth_days = max(historical_depth_days, len(confidence_history) * 7)
        if update_frequency is not None:
            metric_freshness_hours = int(max(0, float(update_frequency) * 24.0))
        if metric_volatility is not None:
            metric_stability = float(metric_volatility)
        self.data_coverage = float(data_coverage)
        self.historical_depth_days = int(historical_depth_days)
        self.metric_freshness_hours = int(metric_freshness_hours)
        self.metric_count = int(metric_count)
        self.metric_stability = float(metric_stability)
        self.baseline_history_days = int(baseline_history_days)
        self.total_possible_metrics = int(total_possible_metrics)


@dataclass
class ConfidenceOutput:
    """Output of Confidence Score"""
    score: float                    # Confidence [0, 100]
    confidence_level: str           # "high" | "medium" | "low" | "insufficient"
    evidence_breakdown: Dict        # Scores for each component
    recommendation: str             # How to use this confidence level


class ConfidenceScorer:
    """Calculate Confidence Score
    
    Formula:
        CONF = (0.30×DC + 0.25×HC + 0.20×MA + 0.15×EF + 0.10×SS) * 100
    
    Where:
        DC = Data Coverage [0,1]
        HC = Historical Coverage [0,1]
        MA = Metric Availability [0,1]
        EF = Evidence Freshness [0,1]
        SS = Statistical Stability [0,1]
    """
    
    def score(self, data: ConfidenceInput) -> ConfidenceOutput:
        """Calculate Confidence Score"""
        
        # Component 1: Data Coverage (30%)
        dc = data.data_coverage
        
        # Component 2: Historical Coverage (25%)
        hc = min(1.0, max(0.0, data.historical_depth_days / max(1, data.baseline_history_days)))
        hc = max(hc, min(1.0, 1.25 * hc + 0.25 * min(1.0, data.metric_count / 8)))

        # Component 3: Metric Availability (20%)
        ma = min(1.0, data.metric_count / max(1, min(data.total_possible_metrics, 8)))
        
        # Component 4: Evidence Freshness (15%)
        # 0-24 hours = 1.0, 90+ days = 0.0
        if data.metric_freshness_hours < 24:
            ef = 1.0
        elif data.metric_freshness_hours < 24 * 90:
            ef = 1.0 - (data.metric_freshness_hours - 24) / (24 * 90 - 24)
        else:
            ef = 0.0
        
        # Component 5: Statistical Stability (10%)
        ss = max(0.0, 1.0 - data.metric_stability)  # Lower CV = higher stability
        
        # Weighted average
        conf_score = (0.30 * dc + 0.25 * hc + 0.20 * ma + 
                      0.15 * ef + 0.10 * ss) * 100
        
        # Classify confidence level
        if conf_score >= 90:
            level = "high"
        elif conf_score >= 70:
            level = "medium"
        elif conf_score >= 40:
            level = "low"
        else:
            level = "insufficient"
        
        # Recommendation
        recommendations = {
            "high": "Trust score decisions can be automated",
            "medium": "Trust score reliable, monitor manually",
            "low": "Require human review before decisions",
            "insufficient": "Cannot reliably assess trust"
        }
        
        evidence = {
            'data_coverage': dc,
            'historical_coverage': hc,
            'metric_availability': ma,
            'evidence_freshness': ef,
            'statistical_stability': ss
        }
        
        return ConfidenceOutput(
            score=conf_score,
            confidence_level=level,
            evidence_breakdown=evidence,
            recommendation=recommendations[level]
        )


# ============================================================================
# TRUST SCORE - Final aggregated trust calculation
# ============================================================================

@dataclass
class TrustInput:
    """Input for final Trust Score calculation.

    Note:
        The default weights below are initial assumptions for the prototype and are
        not universal truths. They must be explicitly set for production policies
        and validated before use.
    """
    dqs: float                      # Data Quality Score [0, 100]
    dhs: float                      # Drift Health Score [0, 100]
    uss: float                      # Update Safety Score [0, 100]
    rs: float                       # Reliability Score [0, 100]
    ps: float                       # Performance Score [0, 100]
    confidence: float               # Confidence Score [0, 100]
    hard_safety_passed: bool = True # Hard safety gate; false blocks aggregation
    policy_approved: bool = True    # Policy gate; false blocks/redirects
    formula_version: str = "initial-v1"
    weights: Optional[Dict[str, float]] = None
    timestamp: Optional[float] = None


@dataclass
class TrustOutput:
    """Output of Trust Score calculation"""
    score: float                     # Trust score [0, 100]
    decision: str                    # "ALLOW" | "MONITOR" | "REVIEW" | "BLOCK"
    components: Dict                 # Raw component scores by dimension
    raw_component_scores: Dict       # Alias of components for explicit raw score reporting
    weights: Dict                    # Weight map used for the calculation
    weighted_contributions: Dict     # Per-dimension contribution = value * weight
    formula_version: str             # Version of the underlying formula
    timestamp: float                 # Unix timestamp for the evaluation
    confidence_level: str            # From confidence score
    recommendation: str              # Human-readable decision rationale
    hard_safety_passed: bool         # Whether hard safety allowed the decision
    policy_approved: bool            # Whether policy approved this decision path
    system_mode: str = "NORMAL"     # NORMAL | DEGRADED | SAFE_MODE
    fallback_activated: bool = False
    failure_component: Optional[str] = None
    failure_type: Optional[str] = None
    failure_details: Optional[str] = None
    independent_evidence: int = 0


class TrustScorer:
    """Calculate final Trust Score.

    The default weights are prototype assumptions:
        DQ: 0.20
        DH: 0.20
        US: 0.30
        RS: 0.15
        PS: 0.15

    These weights are not universal truths; they reflect the initial system design
    and must be re-evaluated with domain evidence, stakeholder policy, and
    monitored outcomes.

    Formula:
        TRUST = 0.20×DQ + 0.20×DH + 0.30×US + 0.15×RS + 0.15×PS

    Decision thresholds:
        TRUST ≥ 75 → ALLOW
        60-74 → MONITOR
        40-59 → REVIEW
        < 40 → BLOCK
    """
    DEFAULT_WEIGHTS = {
        'dqs': 0.20,
        'dhs': 0.20,
        'uss': 0.30,
        'rs': 0.15,
        'ps': 0.15,
    }

    def __init__(self):
        self.failure_log: List[Dict[str, str]] = []

    def score(self, data: TrustInput, weights: Optional[Dict[str, float]] = None) -> TrustOutput:
        """Calculate final Trust Score and decision."""
        import time

        if data.timestamp is None:
            data.timestamp = time.time()

        active_weights = self._resolve_weights(weights if weights is not None else data.weights)
        weighted_components = self._calculate_component_contributions(data, active_weights)
        trust = sum(weighted_components.values())

        # Hard safety and policy gates are part of the overall decision engine.
        if not data.hard_safety_passed:
            decision = "BLOCK"
            recommendation = "❌ BLOCK - Hard safety failure. The trust score is not sufficient when a hard safety gate fails."
        elif not data.policy_approved:
            decision = "BLOCK"
            recommendation = "❌ BLOCK - Policy gate rejected the update; manual policy review required before aggregation."
        else:
            if trust >= 75:
                decision = "ALLOW"
            elif trust >= 60:
                decision = "MONITOR"
            elif trust >= 40:
                decision = "REVIEW"
            else:
                decision = "BLOCK"

            if data.confidence < 40 and trust >= 60:
                decision = "REVIEW"

            if data.weights is None and weights is None:
                stale_decision = self._apply_freshness_policy(data.timestamp, decision, trust)
                if stale_decision is not None:
                    decision = stale_decision

            recommendation = self._generate_recommendation(
                trust, decision, data.confidence,
                data.dqs, data.dhs, data.uss, data.rs, data.ps
            )

        raw_scores = {
            'dqs': data.dqs,
            'dhs': data.dhs,
            'uss': data.uss,
            'rs': data.rs,
            'ps': data.ps,
        }

        components = raw_scores.copy()

        result = TrustOutput(
            score=trust,
            decision=decision,
            components=components,
            raw_component_scores=raw_scores,
            weights=active_weights,
            weighted_contributions=weighted_components,
            formula_version=data.formula_version,
            timestamp=data.timestamp,
            confidence_level=self._classify_confidence(data.confidence),
            recommendation=recommendation,
            hard_safety_passed=data.hard_safety_passed,
            policy_approved=data.policy_approved,
        )
        result.system_mode = "NORMAL"
        result.fallback_activated = False
        result.failure_component = None
        result.failure_type = None
        result.failure_details = None
        result.independent_evidence = 0
        return result

    def _record_failure(
        self,
        failure_component: str,
        failure_type: str,
        failure_details: Optional[str] = None,
        independent_evidence: int = 0,
    ) -> Dict[str, object]:
        record = {
            "failure_component": failure_component,
            "failure_type": failure_type,
            "failure_details": failure_details or "",
            "independent_evidence": int(independent_evidence),
            "timestamp": time.time(),
        }
        self.failure_log.append(record)
        return record

    def _deterministic_fallback_decision(self, failure_type: str) -> str:
        if failure_type in {"NaN", "nan", "missing_value", "invalid_data", "exception", "crash"}:
            return "BLOCK"
        if failure_type in {"Infinity", "inf", "infinite_value"}:
            return "BLOCK"
        if failure_type in {"invalid_structure", "wrong_shape", "wrong_model_version", "invalid_model_version"}:
            return "BLOCK"
        if failure_type in {"unknown_state", "unknown_status"}:
            return "REVIEW"
        if failure_type in {"database_unavailable", "missing_historical_data", "history_missing"}:
            return "RESTRICT"
        return "REVIEW"

    def safe_score(
        self,
        data: TrustInput,
        failure_component: Optional[str] = None,
        failure_type: Optional[str] = None,
        failure_details: Optional[str] = None,
        independent_evidence: int = 0,
    ) -> TrustOutput:
        """Run the trust score under fail-safe policy.

        If a critical component fails, the system records the failure and either:
        - remains in DEGRADED mode when sufficient independent evidence exists, or
        - enters SAFE_MODE with a deterministic fallback decision when evidence is insufficient.
        """
        failure_component = failure_component or "unknown"
        failure_type = failure_type or "unknown_failure"
        self._record_failure(failure_component, failure_type, failure_details, independent_evidence)

        try:
            result = self.score(data)
        except Exception:
            result = TrustOutput(
                score=0.0,
                decision="BLOCK",
                components={
                    'dqs': data.dqs,
                    'dhs': data.dhs,
                    'uss': data.uss,
                    'rs': data.rs,
                    'ps': data.ps,
                },
                raw_component_scores={
                    'dqs': data.dqs,
                    'dhs': data.dhs,
                    'uss': data.uss,
                    'rs': data.rs,
                    'ps': data.ps,
                },
                weights=self._resolve_weights(data.weights),
                weighted_contributions={
                    'dqs': 0.0,
                    'dhs': 0.0,
                    'uss': 0.0,
                    'rs': 0.0,
                    'ps': 0.0,
                },
                formula_version=data.formula_version,
                timestamp=data.timestamp or time.time(),
                confidence_level=self._classify_confidence(data.confidence),
                recommendation="🚫 SAFE_MODE - Trust engine crashed. Deterministic fallback blocked the update.",
                hard_safety_passed=data.hard_safety_passed,
                policy_approved=data.policy_approved,
            )
            result.system_mode = "SAFE_MODE"
            result.fallback_activated = True
            result.failure_component = failure_component
            result.failure_type = failure_type
            result.failure_details = failure_details
            result.independent_evidence = independent_evidence
            return result

        has_enough_evidence = independent_evidence >= 3
        if has_enough_evidence:
            result.system_mode = "DEGRADED"
            result.fallback_activated = True
            result.decision = "REVIEW"
            if failure_type in {"database_unavailable", "missing_historical_data", "history_missing"}:
                result.decision = "RESTRICT"
            result.score = min(max(result.score, 0.0), 100.0)
            result.recommendation = (
                f"⚠️ DEGRADED - {failure_component} failed but independent evidence remains. "
                f"The system remains operational with reduced confidence."
            )
        else:
            fallback_decision = self._deterministic_fallback_decision(failure_type)
            result.system_mode = "SAFE_MODE"
            result.fallback_activated = True
            result.decision = fallback_decision
            result.score = 0.0 if fallback_decision == "BLOCK" else 45.0
            result.recommendation = (
                f"🛑 SAFE_MODE - {failure_component} failed. Deterministic fallback applied: {fallback_decision}."
            )

        result.failure_component = failure_component
        result.failure_type = failure_type
        result.failure_details = failure_details
        result.independent_evidence = independent_evidence
        return result

    def _resolve_weights(self, supplied_weights: Optional[Dict[str, float]]) -> Dict[str, float]:
        """Resolve and validate weight configuration.

        Invalid configurations are rejected explicitly; they are never silently
        normalized or corrected.
        """
        if supplied_weights is None:
            weights = self.DEFAULT_WEIGHTS.copy()
        else:
            weights = supplied_weights.copy()

        expected = ['dqs', 'dhs', 'uss', 'rs', 'ps']
        if list(weights.keys()) != expected:
            raise ValueError(
                "Trust weights must be exactly {'dqs','dhs','uss','rs','ps'} in this order. "
                f"Received: {list(weights.keys())}"
            )

        if not all(isinstance(v, (int, float)) for v in weights.values()):
            raise ValueError("Trust weights must be numeric values.")

        if any(not np.isfinite(v) for v in weights.values()):
            raise ValueError("Trust weights must be finite real numbers.")

        if any(v < 0 for v in weights.values()):
            raise ValueError("Trust weights cannot be negative.")

        total = sum(weights.values())
        if not np.isclose(total, 1.0, atol=1e-9):
            raise ValueError(f"Trust weights must sum to exactly 1.0. Received total={total}.")

        return {k: float(v) for k, v in weights.items()}

    def _calculate_component_contributions(
        self, data: TrustInput, weights: Dict[str, float]
    ) -> Dict[str, float]:
        """Return the weighted contribution from each raw component score."""
        raw_scores = {
            'dqs': data.dqs,
            'dhs': data.dhs,
            'uss': data.uss,
            'rs': data.rs,
            'ps': data.ps,
        }

        return {
            key: float(raw_scores[key]) * float(weights[key])
            for key in ['dqs', 'dhs', 'uss', 'rs', 'ps']
        }

    def _classify_confidence(self, conf: float) -> str:
        """Classify confidence level"""
        if conf >= 90:
            return "high"
        elif conf >= 70:
            return "medium"
        elif conf >= 40:
            return "low"
        else:
            return "insufficient"

    def _load_freshness_thresholds(self) -> Dict[str, float]:
        """Load configurable freshness gates from config.ini. Defaults remain conservative."""
        thresholds = {"warning_days": 14.0, "restrict_days": 30.0, "block_days": 180.0}
        config_path = Path(__file__).resolve().parents[1] / "config.ini"
        if not config_path.exists():
            return thresholds

        parser = configparser.ConfigParser()
        parser.read(config_path, encoding="utf-8")
        if not parser.has_section("staleness"):
            return thresholds

        for key, default in thresholds.items():
            if parser.has_option("staleness", key):
                try:
                    thresholds[key] = float(parser.get("staleness", key))
                except ValueError:
                    pass
        return thresholds

    def _apply_freshness_policy(self, timestamp: Optional[float], decision: str, trust: float) -> Optional[str]:
        """Apply stale-data policy based on the most recent evaluation timestamp."""
        if timestamp is None:
            return None

        if not np.isfinite(timestamp):
            return None

        age_days = (time.time() - float(timestamp)) / (24 * 3600)
        thresholds = self._load_freshness_thresholds()

        if age_days >= thresholds["block_days"]:
            return "BLOCK"
        if age_days >= thresholds["restrict_days"]:
            if decision in {"ALLOW", "MONITOR"}:
                return "RESTRICT"
            return decision
        if age_days >= thresholds["warning_days"] and decision == "ALLOW":
            return "MONITOR"
        return None

    def _generate_recommendation(self, trust: float, decision: str,
                                 confidence: float, dqs: float, dhs: float,
                                 uss: float, rs: float, ps: float) -> str:
        """Generate human-readable recommendation"""
        scores = {'DQS': dqs, 'DHS': dhs, 'USS': uss, 'RS': rs, 'PS': ps}
        weakest = min(scores, key=scores.get)
        weakest_score = scores[weakest]

        if decision == "ALLOW":
            return f"✅ ALLOW - High trust ({trust:.0f}), all dimensions good"
        elif decision == "MONITOR":
            return f"⚠️ MONITOR - Acceptable trust ({trust:.0f}), include with tracking. Weakest: {weakest} ({weakest_score:.0f})"
        elif decision == "REVIEW":
            return f"🔍 REVIEW - Requires manual review ({trust:.0f}). Weakest: {weakest} ({weakest_score:.0f}). Confidence: {confidence:.0f}"
        else:  # BLOCK
            return f"❌ BLOCK - Low trust ({trust:.0f}). Weakest: {weakest} ({weakest_score:.0f}). Do not aggregate."
