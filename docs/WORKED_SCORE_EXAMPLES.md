# Worked Score Examples: Complete End-to-End Calculations

This document provides concrete numerical examples for all scoring calculations. Use these to validate implementations and understand expected behavior.

---

## Scenario Setup

**Context:**
- Multi-hospital federated learning for diagnostic AI
- 10 hospitals training locally
- Updates aggregated weekly
- Baseline global model F1 score: 0.892

**Participant:** Hospital-5

**Current Update Details:**
- Submitted at: 2026-08-17 10:00 UTC
- Training completed: 2026-08-16 22:00 UTC (12 hours ago)
- Training data collected: 2026-07-01 to 2026-08-15
- 450 training samples
- Validation F1 score: 0.901

---

## Part 1: Data Quality Score (DQS) Calculation

### 1a. Schema Score (SS)

**Schema Requirements:**
```
Required fields: patient_id, age, gender, symptoms, test_results, diagnosis
Optional fields: notes, provider_id

Type constraints:
- patient_id: string, non-empty
- age: int, 0-150
- gender: {M, F, Other}
- symptoms: list of strings
- test_results: numeric
- diagnosis: binary {0, 1}
```

**Observed Data Sample (150 records):**
```
Record 1: ✓ All required fields, correct types, constraints satisfied
Record 2: ✓ All required fields, correct types, constraints satisfied
Record 3: ✗ gender = "X" (not in {M, F, Other})
Record 4: ✓ All required fields, correct types, constraints satisfied
Record 5: ✗ age = -5 (violates min=0 constraint)
...
Record 150: ✓ All required fields, correct types, constraints satisfied

Validation Results:
- Valid records: 147 out of 150
- Valid required checks: 147 × 6 = 882
- Total required checks: 150 × 6 = 900
```

**Calculation:**
```
SS = (882 / 900) × 100 = 98.0
```

**Result:** Schema Score = **98.0**

---

### 1b. Completeness Score (CS)

**Data Matrix (simplified: 150 records × 6 required fields):**
```
Total cells: 150 × 6 = 900

Missing cells found:
- Field "test_results": 12 missing (NaN)
- Field "symptoms": 5 missing (None)
- Other fields: 0 missing

Total missing: 12 + 5 = 17 cells
```

**Calculation (Unweighted):**
```
missing_ratio = 17 / 900 = 0.0189
completeness_score = max(0, 100 × (1 - 0.0189))
                  = 100 × 0.9811
                  = 98.11
```

**With Field Weights:**
```
Field weights: {
  "patient_id": 0.10,
  "age": 0.15,
  "gender": 0.10,
  "symptoms": 0.20,  [most important for diagnosis]
  "test_results": 0.30,  [most important]
  "diagnosis": 0.15
}

Missing by field:
- patient_id: 0/150 = 0.0
- age: 0/150 = 0.0
- gender: 0/150 = 0.0
- symptoms: 5/150 = 0.0333
- test_results: 12/150 = 0.0800
- diagnosis: 0/150 = 0.0

Weighted missing = 0.10×0.0 + 0.15×0.0 + 0.10×0.0 + 0.20×0.0333 + 0.30×0.0800 + 0.15×0.0
                 = 0 + 0 + 0 + 0.00666 + 0.0240 + 0
                 = 0.03066

completeness_score = 100 × (1 - 0.03066) = 96.93
```

**Result:** Completeness Score = **96.93** (weighted)

---

### 1c. Validity Score (VS)

**Type and Domain Validators Applied:**

```
Test data (after removing nulls): 893 non-null values

Validation results:
- age: 150 values
  Valid: 148 (all in range [0, 150])
  Invalid: 2 (one negative, one >150)
  
- gender: 150 values
  Valid: 149 (all in {M, F, Other})
  Invalid: 1 (value "X")
  
- test_results: 138 values (12 null removed)
  Valid: 138 (all numeric and in expected range [0, 100])
  Invalid: 0
  
- symptoms: 145 values (5 null removed)
  Valid: 145 (all are lists of strings)
  Invalid: 0
  
- patient_id: 150 values
  Valid: 150 (all non-empty strings)
  Invalid: 0
  
- diagnosis: 150 values
  Valid: 150 (all in {0, 1})
  Invalid: 0

Total non-null values: 893
Total valid values: 148 + 149 + 138 + 145 + 150 + 150 = 880
```

**Calculation:**
```
VS = (880 / 893) × 100 = 98.54
```

**Result:** Validity Score = **98.54**

---

### 1d. Outlier Health Score (OHS)

**Using IQR Method (Tukey's Fences):**

```
Feature: age (150 values)
Data (sorted): [18, 19, 21, 22, ..., 87, 89, 91, 150]

Quartiles:
Q1 (25th percentile): 35
Q3 (75th percentile): 72
IQR = 72 - 35 = 37

Tukey fences (threshold τ = 1.5):
lower_fence = 35 - 1.5 × 37 = 35 - 55.5 = -20.5
upper_fence = 72 + 1.5 × 37 = 72 + 55.5 = 127.5

All age values in data: [18, 19, 21, ..., 150]
Outliers: Only value 150 is > 127.5 (1 outlier)

OHS_age = (1 - 1/150) × 100 = 99.33
```

**Using MAD Method (for validation):**
```
Feature: age
median = 50
deviations = |age - 50|
MAD = median(deviations) = 15
robust_z = 0.6745 × (value - 50) / (15 + 1e-10)

For outlier detection (threshold τ = 3.0):
- value = 18: robust_z = 0.6745 × (-32) / 15 = -1.44 → NOT outlier
- value = 150: robust_z = 0.6745 × (100) / 15 = 4.50 → OUTLIER (>3.0)

OHS_age = (1 - 1/150) × 100 = 99.33
```

**Feature: test_results (continuous, 138 values):**
```
Data ranges: [5.2, 98.5] (on scale of 0-100)
Median ≈ 55
MAD ≈ 20

No extreme outliers detected beyond ±3σ
OHS_test_results = 100.0
```

**Aggregate OHS (equal weight across features):**
```
OHS = (99.33 + 100.0) / 2 = 99.67
```

**Result:** Outlier Health Score = **99.67**

---

### 1e. Sample Sufficiency Score (SuS)

**Minimum and Recommended Samples for Diagnostic AI:**
```
Domain: Medical diagnosis
Model: Random Forest with 50 features
Minimum required samples: 500 (rule of thumb: 10× features for RF)
Recommended samples: 2000 (for confidence in rare diseases)

Current: 450 samples
```

**Calculation (with both thresholds):**
```
If current (450) < minimum (500):
  SuS = (450 / 500) × 50 = 45

But we're in Zone 1 (below minimum)
SuS = (450 / 500) × 50 = 45.0
```

**Result:** Sample Sufficiency Score = **45.0**

---

### 1f. Final Data Quality Score

**Calculation:**
```
DQS = 0.25×SS + 0.25×CS + 0.15×VS + 0.20×OHS + 0.15×SuS
    = 0.25×98.0 + 0.25×96.93 + 0.15×98.54 + 0.20×99.67 + 0.15×45.0
    = 24.50 + 24.23 + 14.78 + 19.93 + 6.75
    = 90.19
```

**Result: Data Quality Score = 90.19/100**

---

## Part 2: Drift Health Score (DHS) Calculation

### 2a. Historical Data Distribution

**Age Distribution (Historical Baseline from all past updates):**
```
Data (500 samples from past week): [20, 22, 25, 28, ..., 85, 87, 89]

Histogram (10 equal-width bins, range [0, 100]):
Bin 1 [0, 10):    2 samples → 0.4%
Bin 2 [10, 20):   8 samples → 1.6%
Bin 3 [20, 30):   95 samples → 19.0%
Bin 4 [30, 40):   120 samples → 24.0%
Bin 5 [40, 50):   110 samples → 22.0%
Bin 6 [50, 60):   90 samples → 18.0%
Bin 7 [60, 70):   50 samples → 10.0%
Bin 8 [70, 80):   20 samples → 4.0%
Bin 9 [80, 90):   5 samples → 1.0%
Bin 10 [90, 100]: 0 samples → 0.0%

Total: 500 samples (100%)
```

---

### 2b. Current Data Distribution

**Age Distribution (Hospital-5 Current Update, 450 samples):**
```
Data: [21, 23, 26, 29, ..., 88, 90, 92, 102]  [Note: 102 is older than historical]

Histogram (same bins):
Bin 1 [0, 10):    0 samples → 0.0%
Bin 2 [10, 20):   2 samples → 0.4%
Bin 3 [20, 30):   95 samples → 21.1%
Bin 4 [30, 40):   105 samples → 23.3%
Bin 5 [40, 50):   95 samples → 21.1%
Bin 6 [50, 60):   85 samples → 18.9%
Bin 7 [60, 70):   55 samples → 12.2%
Bin 8 [70, 80):   12 samples → 2.7%
Bin 9 [80, 90):   2 samples → 0.4%
Bin 10 [90, 100]: 2 samples → 0.4%  [New: older patients]

Total: 450 samples (100% after rounding)
```

---

### 2c. PSI Calculation

**With Laplace Smoothing (α = 0.5):**

```
Step 1: Apply smoothing
smoothing_factor = 0.5 / 10 = 0.05 per bin

Smoothed historical percentages:
Bin 1: (2 + 0.5) / (500 + 5) = 2.5 / 505 = 0.495%
Bin 2: (8 + 0.5) / 505 = 8.5 / 505 = 1.683%
Bin 3: (95 + 0.5) / 505 = 95.5 / 505 = 18.911%
... (continue for all bins)

Smoothed current percentages:
Bin 1: (0 + 0.5) / (450 + 5) = 0.5 / 455 = 0.110%
Bin 2: (2 + 0.5) / 455 = 2.5 / 455 = 0.549%
Bin 3: (95 + 0.5) / 455 = 95.5 / 455 = 20.879%
... (continue for all bins)

Step 2: Calculate PSI components for each bin
PSI = Σ (p_actual - p_expected) × ln(p_actual / p_expected)

Example calculations:
Bin 1: (0.110% - 0.495%) × ln(0.110 / 0.495)
     = -0.00385 × ln(0.222)
     = -0.00385 × (-1.505)
     = 0.00579

Bin 3: (20.879% - 18.911%) × ln(20.879 / 18.911)
     = 0.01968 × ln(1.104)
     = 0.01968 × 0.0988
     = 0.00194

Bin 10: (0.440% - 0%) × ln(0.440 / 0.495)  [using smoothed historical]
      = 0.00440 × ln(0.888)
      = 0.00440 × (-0.119)
      = -0.000523

[Continue for all 10 bins...]

Total PSI = 0.00579 + 0.00121 + 0.00194 + 0.00089 + 0.00234 + 0.00156 + 0.00289 + 0.00445 + 0.00301 + 0.00523
         ≈ 0.0393
```

**Interpretation:**
```
PSI = 0.0393
Thresholds:
- negligible: 0.1
- small: 0.25
- medium: 0.50

PSI (0.0393) < 0.1 → NEGLIGIBLE DRIFT
```

---

### 2d. PSI-to-Health Score Conversion

**Using Linear Conversion:**
```
PSI = 0.0393
PSI ≤ τ_negligible (0.1) → DHS = 100
```

**Result: Drift Health Score = 100.0**

---

## Part 3: Update Safety Score (USS) Calculation

### 3a. Structural Validity

**Model Update Inspection:**
```
Model: ResNet-50 with ~23.5M parameters
Update size: 94MB (weights after local training)

Checking for invalid values:
- NaN values: 0
- Inf values: 0
- Complex numbers: 0

Total parameters checked: ~23,500,000
Invalid ratio: 0 / 23,500,000 = 0.0

SVS = 1.0 (perfect)
```

**Result:** Structural Validity = **1.0**

---

### 3b. Magnitude Score

**Computing Layer-wise Update Magnitudes:**

```
Historical updates from Hospital-5 (last 8 weeks):
Conv_layer_1 L2 norms: [0.032, 0.041, 0.038, 0.035, 0.039, 0.037, 0.036, 0.040]
Conv_layer_2 L2 norms: [0.018, 0.022, 0.020, 0.019, 0.021, 0.019, 0.020, 0.021]
... (continue for ~50 layers)

Median norms:
Conv_layer_1 median: 0.0375
Conv_layer_2 median: 0.0200
...

Current update magnitudes:
Conv_layer_1: 0.0380 (close to median)
Conv_layer_2: 0.0195 (close to median)
```

**Robust Z-Score Calculation (Conv_layer_1 example):**
```
Current: 0.0380
Median historical: 0.0375
MAD = median(|0.032-0.0375|, |0.041-0.0375|, ...)
    = median(0.0055, 0.0035, 0.0005, 0.0025, 0.0015, 0.0005, 0.0015, 0.0025)
    = 0.0020 (median of sorted deviations)

robust_z = 0.6745 × (0.0380 - 0.0375) / (0.0020 + 1e-10)
         = 0.6745 × 0.0005 / 0.0020
         = 0.6745 × 0.25
         = 0.169

|0.169| ≤ 3.0 (threshold) → MS_layer = 1.0
```

**Aggregate Across ~50 Layers:**
```
All layer magnitudes within expected ranges
MS = mean of all layer scores ≈ 0.98
```

**Result:** Magnitude Score = **0.98**

---

### 3c. Freshness Score

**Age Calculation:**
```
timestamp_created = 2026-08-16 22:00 UTC
timestamp_now = 2026-08-17 10:00 UTC
age_hours = (10:00 - 22:00 on previous day) / 3600
         = 12 hours

FS calculation (τ_max = 168 hours = 7 days):
12 hours ≤ 24 → FS = 0.99
```

**Result:** Freshness Score = **0.99**

---

### 3d. Consistency Score

**Direction Similarity Calculation:**

```
Mean of historical deltas: direction_hist ≈ [+0.005, -0.002, +0.003, ...]
Current delta: direction_curr ≈ [+0.0048, -0.0021, +0.0031, ...]

Cosine similarity = dot(direction_curr, direction_hist) / (||direction_curr|| × ||direction_hist||)
                  ≈ 0.98 [very similar directions]

Magnitude ratio = 0.0376 / 0.0375 = 1.003 [almost identical]
This is in range [0.5, 2.0) → CS_mag = 1.0

CS = 0.7 × 0.98 + 0.3 × 1.0 = 0.686 + 0.300 = 0.986
```

**Result:** Consistency Score = **0.986**

---

### 3e. Final Update Safety Score

**Calculation:**
```
USS = 0.35×SVS + 0.30×MS + 0.20×FS + 0.15×CS
    = 0.35×1.0 + 0.30×0.98 + 0.20×0.99 + 0.15×0.986
    = 0.35 + 0.294 + 0.198 + 0.1479
    = 0.9899

USS_final = 0.9899 × 100 = 98.99
```

**Result: Update Safety Score = 98.99/100**

---

## Part 4: Reliability Score (RS) Calculation

### 4a. Availability Score

**Historical Data (Hospital-5 over past 8 weeks):**
```
Total aggregation rounds: 8 (one per week)
Rounds where Hospital-5 submitted: 8
Rounds where Hospital-5 was absent: 0

AS = (8 / 8) × 100 = 100.0
```

**Result:** Availability Score = **100.0**

---

### 4b. Heartbeat Health Score

**Submission Timestamps (past 8 weeks):**
```
Updates submitted at:
Week 1: Monday 10:05 AM
Week 2: Monday 10:12 AM
Week 3: Monday 10:03 AM
Week 4: Monday 10:08 AM
Week 5: Monday 10:15 AM
Week 6: Monday 10:02 AM
Week 7: Monday 10:09 AM
Week 8: Monday 10:06 AM

Intervals (minutes): [7, -9, 5, 7, -13, 7, -3]
[Note: negative intervals are due to weekly spacing - convert to minutes from weekly cycle]

More realistically - minutes from 10:00 baseline:
[5, 12, 3, 8, 15, 2, 9, 6]

Median interval: 7.5 minutes
Deviations from median: |5-7.5|, |12-7.5|, |3-7.5|, |8-7.5|, |15-7.5|, |2-7.5|, |9-7.5|, |6-7.5|
                      = [2.5, 4.5, 4.5, 0.5, 7.5, 5.5, 1.5, 1.5]

Median deviation: 3.5 minutes

Consistency ratio = 7.5 / 3.5 = 2.14

Since 2 ≤ 2.14 < 3 → HS = 70 (somewhat regular)
```

**Result:** Heartbeat Health Score = **70.0**

---

### 4c. Success Rate Score

**Update Status History (Hospital-5):**
```
Week 1: ACCEPTED
Week 2: ACCEPTED
Week 3: ACCEPTED
Week 4: FLAGGED (for review, but eventually accepted)
Week 5: ACCEPTED
Week 6: ACCEPTED
Week 7: ACCEPTED
Week 8: ACCEPTED

Total updates: 8
Accepted: 7
Flagged: 1
Blocked: 0

SRS = (7 / 8) × 100 = 87.5
```

**Result:** Success Rate Score = **87.5**

---

### 4d. Latency Health Score

**Update Generation Time (Hospital-5):**
```
Acceptable threshold: 3600 seconds (1 hour)

Latency for each update (seconds):
Week 1: 1200 (20 minutes) ✓
Week 2: 890 (15 minutes) ✓
Week 3: 1450 (24 minutes) ✓
Week 4: 2100 (35 minutes) ✓
Week 5: 950 (16 minutes) ✓
Week 6: 1800 (30 minutes) ✓
Week 7: 750 (12 minutes) ✓
Week 8: 1100 (18 minutes) ✓

All 8 updates < 3600 seconds
fraction_on_time = 8/8 = 1.0 (100%)

LHS = 100 (since fraction_on_time ≥ 0.95)
```

**Result:** Latency Health Score = **100.0**

---

### 4e. Consecutive Failure Penalty

**Recent Status (last 5 updates):**
```
Week 4: FLAGGED
Week 5: ACCEPTED
Week 6: ACCEPTED
Week 7: ACCEPTED
Week 8: ACCEPTED

Most recent updates moving backward:
Week 8: ACCEPTED ← stop counting here (first non-failure)

consecutive_failures = 0 (no blocked updates in recent streak)
penalty = 0
```

**Result:** Penalty = **0**

---

### 4f. Final Reliability Score

**Calculation:**
```
RS_raw = 0.35×AS + 0.25×HS + 0.20×SRS + 0.20×LHS
       = 0.35×100.0 + 0.25×70.0 + 0.20×87.5 + 0.20×100.0
       = 35.0 + 17.5 + 17.5 + 20.0
       = 90.0

RS_final = max(0, min(100, 90.0 + 0))
         = 90.0
```

**Result: Reliability Score = 90.0/100**

---

## Part 5: Performance Score (PS) Calculation

### 5a. Global Model Performance Metrics

**Before Aggregation (Current Global Model):**
```
Test Set: 5000 samples from hold-out set
Metrics:
- F1 Score: 0.892
- Precision: 0.885
- Recall: 0.900
- Accuracy: 0.885
```

**After Aggregation (with Hospital-5's Update):**
```
Updated Global Model (averaged Hospital-5 weights with global)
Test Set: Same 5000 samples
Metrics:
- F1 Score: 0.896
- Precision: 0.889
- Recall: 0.905
- Accuracy: 0.889
```

---

### 5b. Performance Delta Calculation

**Using F1 Score (higher is better):**
```
baseline_metric = 0.892
current_metric = 0.896

Δ = (0.896 - 0.892) / 0.892
  = 0.004 / 0.892
  = 0.00449  (0.449% improvement)

PS = min(100, 100 × (1 + 0.00449))
   = min(100, 100.449)
   = 100 (clamped)
```

**Result:** Performance Score = **100.0** (improvement detected)

---

### 5c. Per-Slice Fairness Check

**Performance by Demographics (if available):**
```
Age Group 18-40:
  F1 before: 0.920 → after: 0.923 (Δ = +0.3%)
  
Age Group 40-65:
  F1 before: 0.895 → after: 0.898 (Δ = +0.3%)
  
Age Group 65+:
  F1 before: 0.850 → after: 0.850 (Δ = 0.0%)

Fairness variance = max(0.3%, 0.3%, 0.0%) - min = 0.3%

Since 0.3% < 0.5% (fairness variance < 0.02 in decimal):
fairness_penalty = 0
```

**Result:** Final Performance Score = **100.0**

---

## Part 6: Composite Trust Score

### 6a. Individual Scores Summary

```
Data Quality Score (DQS):      90.19 (weight: 0.25)
Drift Health Score (DHS):      100.0 (weight: 0.25)
Update Safety Score (USS):     98.99 (weight: 0.20)
Reliability Score (RS):        90.0  (weight: 0.20)
Performance Score (PS):        100.0 (weight: 0.10)
```

---

### 6b. Trust Score Calculation

**Weighted Combination:**
```
TRUST = 0.25×DQS + 0.25×DHS + 0.20×USS + 0.20×RS + 0.10×PS
      = 0.25×90.19 + 0.25×100.0 + 0.20×98.99 + 0.20×90.0 + 0.10×100.0
      = 22.548 + 25.000 + 19.798 + 18.000 + 10.000
      = 95.346

TRUST ≈ 95.35 (rounded)
```

---

### 6c. Confidence Interval Calculation

**Standard Errors (estimated from historical variance):**
```
σ_DQS = 2.5  (data quality typically varies ±2.5%)
σ_DHS = 1.8  (drift stable)
σ_USS = 1.5  (safety deterministic)
σ_RS = 3.0   (reliability more variable)
σ_PS = 2.0   (performance noisy)

Combined standard error:
σ_total = √[(0.25×2.5)² + (0.25×1.8)² + (0.20×1.5)² + (0.20×3.0)² + (0.10×2.0)²]
        = √[0.390625 + 0.2025 + 0.09 + 0.36 + 0.04]
        = √1.082 = 1.04

95% confidence interval: ±1.96 × 1.04 = ±2.04
```

**Result:**
```
TRUST = 95.35 ± 2.04 (95% confidence)
Range: [93.31, 97.39]
```

---

### 6d. Decision

**Decision Threshold:**
```
Thresholds:
- ALLOW: ≥ 0.75 (75)
- MONITOR: 0.60 - 0.74 (60-74)
- REVIEW: 0.40 - 0.59 (40-59)
- BLOCK: < 0.40 (40)

TRUST = 95.35

95.35 ≥ 75 → DECISION: ALLOW
```

---

## Audit Trail Output

```
{
  "update_id": "hospital5_week8_20260817",
  "participant": "Hospital-5",
  "timestamp_submitted": "2026-08-17 10:00:00 UTC",
  "timestamp_trained": "2026-08-16 22:00:00 UTC",
  
  "scores": {
    "data_quality_score": {
      "value": 90.19,
      "components": {
        "schema_score": 98.0,
        "completeness_score": 96.93,
        "validity_score": 98.54,
        "outlier_health_score": 99.67,
        "sample_sufficiency_score": 45.0
      },
      "notes": "Low sample count (450 vs 500 minimum)"
    },
    "drift_health_score": {
      "value": 100.0,
      "psi": 0.0393,
      "interpretation": "negligible_drift",
      "notes": "Age distribution very stable"
    },
    "update_safety_score": {
      "value": 98.99,
      "components": {
        "structural_validity": 1.0,
        "magnitude_score": 0.98,
        "freshness_score": 0.99,
        "consistency_score": 0.986
      },
      "notes": "Fresh update, normal magnitudes"
    },
    "reliability_score": {
      "value": 90.0,
      "components": {
        "availability": 100.0,
        "heartbeat_health": 70.0,
        "success_rate": 87.5,
        "latency_health": 100.0,
        "consecutive_failure_penalty": 0.0
      },
      "notes": "Reliable participant, timing slightly variable"
    },
    "performance_score": {
      "value": 100.0,
      "delta": 0.00449,
      "baseline_f1": 0.892,
      "current_f1": 0.896,
      "fairness_check": "passed",
      "notes": "Positive performance impact"
    }
  },
  
  "trust_score": {
    "value": 95.35,
    "confidence_interval": {
      "lower": 93.31,
      "upper": 97.39,
      "confidence_level": 0.95
    }
  },
  
  "decision": {
    "action": "ALLOW",
    "reasoning": "Trust score 95.35 exceeds threshold 75.0",
    "confidence": "high"
  },
  
  "timestamp_decision": "2026-08-17 10:00:15 UTC",
  "processing_latency_ms": 150
}
```

---

## Summary Statistics

| Score | Value | Status |
|-------|-------|--------|
| Data Quality | 90.19 | Good (limited by low sample count) |
| Drift Health | 100.0 | Excellent (stable data distribution) |
| Update Safety | 98.99 | Excellent (fresh, normal, consistent) |
| Reliability | 90.0 | Good (dependable participant) |
| Performance | 100.0 | Excellent (positive impact) |
| **TRUST** | **95.35** | **ALLOW** |

---

## Alternative Scenario: Problematic Update

**What if Hospital-5's update was suspicious?**

```
Changed Conditions:
- Schema Score: 72 (type errors)
- Completeness Score: 60 (30% missing)
- Validity Score: 50 (many invalid values)
- Outlier Health Score: 20 (40% data are outliers)
- Sample Sufficiency Score: 20 (only 100 samples)

DQS = 0.25×72 + 0.25×60 + 0.15×50 + 0.20×20 + 0.15×20
    = 18 + 15 + 7.5 + 4 + 3
    = 47.5 ← RED FLAG

With other scores also degraded:
- DHS = 35 (large drift detected, PSI = 0.55)
- USS = 60 (magnitude outlier, potential divergence)
- RS = 85 (still reliable historically)
- PS = 45 (negative performance impact)

TRUST = 0.25×47.5 + 0.25×35 + 0.20×60 + 0.20×85 + 0.10×45
      = 11.875 + 8.75 + 12 + 17 + 4.5
      = 54.125

Decision: 54.125 in [40, 59] → REVIEW
Action: Flag for human expert review before aggregation
```

---

**Status:** Worked examples complete. Use these for validation testing and implementation verification.
