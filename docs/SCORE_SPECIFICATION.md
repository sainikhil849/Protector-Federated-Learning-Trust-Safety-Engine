# Score Specification: Complete Mathematical Definition

This document specifies every score in Protector Uttam with complete mathematical rigor, ensuring all calculations are reproducible and auditable.

---

## Part 1: Data Quality Score (DQS)

### Overview

The Data Quality Score measures the fitness of participant's training data based on five sub-components:
1. Schema Score (data structure validity)
2. Completeness Score (missing values)
3. Validity Score (data type correctness)
4. Outlier Health Score (anomalous values)
5. Sample Sufficiency Score (adequate volume)

**Final Formula:**
```
DQS = 0.25×SS + 0.25×CS + 0.15×VS + 0.20×OHS + 0.15×SuS

where:
- SS = Schema Score
- CS = Completeness Score
- VS = Validity Score
- OHS = Outlier Health Score
- SuS = Sample Sufficiency Score

WEIGHTS: [0.25, 0.25, 0.15, 0.20, 0.15] (INITIAL PROTOTYPE WEIGHTS - CONFIGURABLE)
```

---

### 1a. Schema Score (SS)

**Purpose:** Validate that data structure matches expected schema (required fields present, correct types).

**Raw Inputs:**
```
- schema_definition: Dict[field_name → {type, required, constraints}]
- observed_data: DataFrame or JSON records
- validation_rules: Dict[rule_name → rule_function]
```

**Input Validation:**
```
1. schema_definition is non-empty
2. observed_data has at least 1 record
3. validation_rules are callable functions
4. Field names in observed_data subset of schema_definition (allow extras)
```

**Exact Formula:**

```
valid_required_checks = count(required fields that are present AND correct type)
total_required_checks = count(required fields in schema)

SS = (valid_required_checks / total_required_checks) × 100

Range: [0, 100]
```

**Intermediate Calculations:**

For each required field in schema:
```
field_valid = (field exists in data) AND
              (field_type matches schema type) AND
              (field satisfies constraints)

Example:
Schema says: age (type=int, required=true, min=0, max=150)
Data has: age values 25, 32, 105, -5, None
Invalid checks: -5 (violates min constraint), None (missing)
```

**Normalization:**

- Per-record basis, then aggregate
- Missing required field → 0 for that record
- Type mismatch → 0 for that field
- Constraint violation → 0 for that field

**Output Range:**

- Minimum: 0.0 (all required fields missing/invalid)
- Maximum: 100.0 (all required fields present and valid)
- Typical range: [60, 100] (some missing/corrupt typical)

**Edge Case Behavior:**

1. **Empty schema** → SS = 100 (no requirements to fail)
2. **No required fields** → SS = 100 (vacuous truth)
3. **All data missing** → SS = 0
4. **Single field schema** → Either 0 or 100
5. **Type coercion** → Allow int→float but not string→int without explicit rule

**Example Calculation:**

```
Schema:
{
  "age": {type: int, required: true, min: 0, max: 150},
  "income": {type: float, required: true, min: 0},
  "phone": {type: str, required: false},
  "email": {type: str, required: true}
}

Sample records:
1. age=25, income=50000.0, phone="123-456", email="a@b.com" → VALID
2. age=32, income=75000.0, phone=None, email="c@d.com" → VALID
3. age=-5, income=40000.0, phone=None, email=None → INVALID (age < 0, email missing)
4. age=None, income=60000.0, phone=None, email="e@f.com" → INVALID (age missing)

Checking required fields for each record:
Record 1: 3/3 required fields valid → 1.0
Record 2: 3/3 required fields valid → 1.0
Record 3: 1/3 required fields valid (only income) → 0.33
Record 4: 2/3 required fields valid (income, email) → 0.67

Average: (1.0 + 1.0 + 0.33 + 0.67) / 4 = 0.75

SS = 0.75 × 100 = 75.0
```

**Failure Cases:**

1. **False Positives:** Schema too strict; legitimate data marked invalid
   - *Mitigation:* Review constraints with domain experts
2. **False Negatives:** Schema too lenient; garbage data passes
   - *Mitigation:* Add statistical validation rules
3. **Changing Schema:** Schema updated but historical baselines outdated
   - *Mitigation:* Version schema; flag changes explicitly

**Unit Tests Required:**

```python
test_schema_score_all_valid()
  # All records pass all checks → SS = 100

test_schema_score_partial_invalid()
  # Some records fail → SS = expected_percentage

test_schema_score_all_invalid()
  # All records fail → SS = 0

test_schema_score_empty_schema()
  # No required fields → SS = 100

test_schema_score_type_coercion()
  # int vs float coercion → handled per config

test_schema_score_constraint_violations()
  # min/max/regex violations detected correctly

test_schema_score_missing_fields()
  # Required field absence correctly decreases score
```

---

### 1b. Completeness Score (CS)

**Purpose:** Measure fraction of data that is complete (non-null/non-missing).

**Raw Inputs:**
```
- data: DataFrame with potentially missing values
- missing_indicators: List[None, NaN, "", "N/A", custom_null_values]
- field_weights: Dict[field_name → importance_weight] (optional)
```

**Input Validation:**
```
1. data has at least 1 record and 1 field
2. missing_indicators is a list of comparable values
3. field_weights sum to 1.0 (if provided)
4. All field names in field_weights exist in data
```

**Exact Formula:**

```
missing_ratio = count(missing cells) / count(total cells)

completeness_score = max(0, 100 × (1 - missing_ratio))

Range: [0, 100]
```

**Intermediate Calculations:**

```
Step 1: Count total cells
  total_cells = num_records × num_fields

Step 2: Count missing cells
  missing_cells = 0
  for each cell in data:
    if cell in missing_indicators OR is_null(cell):
      missing_cells += 1

Step 3: Calculate ratio
  missing_ratio = missing_cells / total_cells

Step 4: Transform to score
  completeness_score = max(0, 100 × (1 - missing_ratio))
```

**With Field Weights (Optional):**

```
If field_weights provided (e.g., critical fields weighted higher):

weighted_missing = 0
for each field:
  field_missing_count = count(missing in field)
  field_missing_ratio = field_missing_count / num_records
  weighted_missing += field_weights[field] × field_missing_ratio

completeness_score = max(0, 100 × (1 - weighted_missing))
```

**Normalization:**

- Cell-level detection of missing values
- Aggregate to dataset-level score
- Clamp to [0, 100] range

**Output Range:**

- Minimum: 0.0 (all cells missing)
- Maximum: 100.0 (no missing cells)
- Typical: [70, 99] (some missing typical)

**Edge Case Behavior:**

1. **No fields** → Return NaN (error)
2. **No records** → Return NaN (error)
3. **All cells missing** → CS = 0
4. **No cells missing** → CS = 100
5. **Empty strings** → Treat as missing if "" in missing_indicators
6. **Whitespace-only strings** → Configurable (strip or treat as missing)
7. **NaN in float columns** → Always treat as missing
8. **Zero values** → Never treat as missing (zero is valid)

**Example Calculation:**

```
Data:
  age  income  email
1 25   50000   a@b.com
2 32   NaN     c@d.com
3 None 40000   None
4 45   60000   e@f.com

Total cells = 4 rows × 3 cols = 12 cells
Missing cells = 1 (NaN in income) + 1 (None in age) + 1 (None in email) = 3
Missing ratio = 3 / 12 = 0.25
Completeness score = 100 × (1 - 0.25) = 75.0
```

**With Field Weights:**

```
Weights: age=0.3, income=0.5, email=0.2 (income most important)

Missing by field:
- age: 1 missing out of 4 = 0.25 missing ratio
- income: 1 missing out of 4 = 0.25 missing ratio
- email: 1 missing out of 4 = 0.25 missing ratio

Weighted missing = 0.3×0.25 + 0.5×0.25 + 0.2×0.25 = 0.25
Completeness score = 100 × (1 - 0.25) = 75.0

Note: Even though income is weighted more, all fields have same missing ratio.
If income had zero missing:
Weighted missing = 0.3×0.25 + 0.5×0.0 + 0.2×0.25 = 0.125
Completeness score = 100 × (1 - 0.125) = 87.5
```

**Failure Cases:**

1. **Sparse Data:** Legitimate missing data (e.g., optional fields)
   - *Mitigation:* Distinguish "missing by design" from "missing by error"
2. **Correlated Missing:** Multiple fields missing together (systematic issue)
   - *Mitigation:* Detect and flag separately from random missing
3. **Missing Drift:** Missing pattern changes over time
   - *Mitigation:* Track missing ratio over time; detect sudden changes

**Unit Tests Required:**

```python
test_completeness_no_missing()
  # All cells present → CS = 100

test_completeness_all_missing()
  # All cells missing → CS = 0

test_completeness_partial_missing()
  # 25% missing → CS = 75

test_completeness_field_weights()
  # Weighted calculation correct

test_completeness_missing_indicators()
  # Detects None, NaN, custom null values

test_completeness_zero_valid()
  # Zero values not marked as missing

test_completeness_whitespace()
  # Whitespace handling per config
```

---

### 1c. Validity Score (VS)

**Purpose:** Measure fraction of values that satisfy data type and domain constraints.

**Raw Inputs:**
```
- data: DataFrame
- type_validators: Dict[field_name → type_check_function]
- domain_validators: Dict[field_name → domain_check_function]
  Example: {age: lambda x: 0 <= x <= 150}
```

**Input Validation:**
```
1. data has at least 1 record
2. Validators are callable
3. Validators return boolean
4. All validator field names exist in data (or extras ignored)
```

**Exact Formula:**

```
valid_values = count(values that pass both type AND domain validation)
total_values = count(non-null values in data)

validity_score = (valid_values / total_values) × 100

Range: [0, 100]
```

**Intermediate Calculations:**

```
Step 1: For each non-null value in data
  valid = type_validator(value) AND domain_validator(value)

Step 2: Count valid values
  valid_count = count(value where valid == True)
  total_count = count(value where value is not null)

Step 3: Calculate score
  validity_score = (valid_count / total_count) × 100
```

**Normalization:**

- Only non-null values included in denominator
- Type check must pass first (short-circuit)
- Domain check applied only to type-valid values

**Output Range:**

- Minimum: 0.0 (no valid values)
- Maximum: 100.0 (all non-null values valid)
- Typical: [90, 99] (most values valid)

**Edge Case Behavior:**

1. **All null values** → Denominator = 0; return NaN or skip (handled in CS)
2. **No validators** → VS = 100 (all non-null values considered valid)
3. **Validator raises exception** → Log error, mark value invalid, continue
4. **Mixed types in column** → Type validator must handle (or flag as invalid)
5. **Empty string on string field** → Valid (unless "" in missing_indicators)

**Example Calculation:**

```
Data: age column
Values (excluding null): 25, 32, 150, 200, -5, 45

Type validator: isinstance(x, int)
Domain validator: 0 <= x <= 150

Checking each:
- 25: type=int✓, domain=0≤25≤150✓ → VALID
- 32: type=int✓, domain=0≤32≤150✓ → VALID
- 150: type=int✓, domain=0≤150≤150✓ → VALID
- 200: type=int✓, domain=0≤200≤150✗ → INVALID
- -5: type=int✓, domain=0≤-5≤150✗ → INVALID
- 45: type=int✓, domain=0≤45≤150✓ → VALID

Valid count = 4
Total count = 6
Validity score = (4/6) × 100 = 66.7
```

**Failure Cases:**

1. **Type Mismatch:** Mixed int/float in column
   - *Mitigation:* Allow safe coercion (int→float)
2. **Edge Values:** Boundary values (0, max int) incorrectly flagged
   - *Mitigation:* Test validators with boundary cases
3. **Domain Shift:** Domain constraints outdated
   - *Mitigation:* Versioning; allow multi-domain support

**Unit Tests Required:**

```python
test_validity_all_valid()
  # All non-null values pass → VS = 100

test_validity_all_invalid()
  # All non-null values fail → VS = 0

test_validity_mixed()
  # Some pass, some fail → VS = expected percentage

test_validity_type_check_only()
  # Domain validator absent → passes type

test_validity_domain_check_only()
  # Type validator absent → passes domain

test_validity_validator_exception()
  # Validator raises exception → handled gracefully

test_validity_edge_values()
  # Boundary values handled correctly
```

---

### 1d. Outlier Health Score (OHS)

**Purpose:** Measure how many values are statistical anomalies (outliers) using robust methods.

**Rationale for Robustness:**

Outliers are not necessarily bad; they may be legitimate edge cases. Instead of flagging all outliers as invalid, we measure the **fraction of data that is outlier-free**, which indicates how "typical" the distribution is.

**Raw Inputs:**
```
- data: Dict[field_name → list of numeric values]
- method: 'iqr' (default) or 'mad' or 'zscore'
- threshold: {
    iqr: 1.5 (standard is 1.5×IQR),
    mad: 3.0 (standard is 3×MAD),
    zscore: 3.0 (standard is 3σ)
  }
- exclude_null: bool (default: true)
```

**Input Validation:**
```
1. data contains numeric columns
2. Each column has at least 4 values (need for quartiles)
3. method in ['iqr', 'mad', 'zscore']
4. threshold > 0
```

**Exact Formula (Method 1: IQR - Tukey's Fences):**

```
IQR = Q3 - Q1
lower_fence = Q1 - threshold × IQR
upper_fence = Q3 + threshold × IQR

is_outlier(x) = (x < lower_fence) OR (x > upper_fence)

outlier_health_score = (1 - (outlier_count / total_count)) × 100

Range: [0, 100]
```

**Exact Formula (Method 2: MAD - Median Absolute Deviation):**

```
MAD = median(abs(x_i - median(x)))

robust_z_score(x) = 0.6745 × (x - median(x)) / (MAD + epsilon)
                    [0.6745 is scaling factor for normal distribution]

is_outlier(x) = abs(robust_z_score(x)) > threshold

outlier_health_score = (1 - (outlier_count / total_count)) × 100

where epsilon = 1e-10 (avoid division by zero)
```

**Exact Formula (Method 3: Z-Score):**

```
z_score(x) = (x - mean(x)) / (std(x) + epsilon)

is_outlier(x) = abs(z_score(x)) > threshold

outlier_health_score = (1 - (outlier_count / total_count)) × 100
```

**Intermediate Calculations (IQR Example):**

```
Step 1: Sort data
  data_sorted = sort(data)

Step 2: Calculate quartiles
  Q1 = data_sorted[len(data) × 0.25]  [25th percentile]
  Q3 = data_sorted[len(data) × 0.75]  [75th percentile]
  IQR = Q3 - Q1

Step 3: Define fences
  lower_fence = Q1 - threshold × IQR
  upper_fence = Q3 + threshold × IQR

Step 4: Count outliers
  outlier_count = 0
  for each value in data:
    if value < lower_fence OR value > upper_fence:
      outlier_count += 1

Step 5: Calculate score
  outlier_health_score = (1 - outlier_count/total_count) × 100
```

**Intermediate Calculations (MAD Example):**

```
Step 1: Calculate median
  med = median(data)

Step 2: Calculate deviations from median
  deviations = [abs(x - med) for x in data]

Step 3: Calculate MAD
  MAD = median(deviations)

Step 4: Robust Z-score for each value
  for each value x in data:
    robust_z = 0.6745 × (x - med) / (MAD + 1e-10)
    if abs(robust_z) > threshold:
      mark as outlier

Step 5: Calculate score
  outlier_health_score = (1 - outlier_count/total_count) × 100
```

**Normalization:**

- Per-field basis, then aggregate with equal weight (or configurable weights)
- Clamp to [0, 100]

**Output Range:**

- Minimum: 0.0 (all values are outliers)
- Maximum: 100.0 (no outliers)
- Typical: [95, 99] (1–5% outliers normal for real data)

**Edge Case Behavior:**

1. **All identical values (zero variance)**
   - IQR/MAD/Z-score undefined
   - *Behavior:* No outliers (all values equal) → OHS = 100

2. **Single column, <4 values**
   - Can't compute quartiles
   - *Behavior:* Insufficient data → return NaN or flag for review

3. **Negative outlier threshold**
   - Invalid; flag as error
   - *Behavior:* Use absolute value or raise exception

4. **No numeric columns**
   - Not applicable to outlier detection
   - *Behavior:* Skip field; return NaN or neutral score (100)

5. **Bimodal distributions**
   - Legitimate cluster on each mode may look like outliers
   - *Mitigation:* Document that OHS assumes unimodal distribution

**Example Calculation (IQR Method):**

```
Data: [10, 12, 15, 18, 20, 22, 25, 28, 30, 100]
(Note: 100 is suspicious outlier)

Step 1: Sorted (already sorted)
Step 2: Calculate quartiles
  Q1 at 25th percentile = 15
  Q3 at 75th percentile = 28
  IQR = 28 - 15 = 13

Step 3: Define fences (using threshold=1.5)
  lower_fence = 15 - 1.5×13 = -4.5
  upper_fence = 28 + 1.5×13 = 47.5

Step 4: Identify outliers
  All values in [-4.5, 47.5] except:
  100 > 47.5 → OUTLIER

Step 5: Calculate score
  outlier_count = 1
  total_count = 10
  OHS = (1 - 1/10) × 100 = 90.0
```

**Example Calculation (MAD Method):**

```
Same data: [10, 12, 15, 18, 20, 22, 25, 28, 30, 100]

Step 1: Median
  med = (20 + 22) / 2 = 21

Step 2: Deviations
  abs(x - 21) = [11, 9, 6, 3, 1, 1, 4, 7, 9, 79]

Step 3: MAD
  MAD = median([1, 1, 3, 4, 6, 7, 9, 9, 11, 79]) = (6 + 7) / 2 = 6.5

Step 4: Robust Z-scores (using threshold=3.0)
  For x=10: robust_z = 0.6745 × (10-21)/(6.5+1e-10) = 0.6745 × (-11/6.5) ≈ -1.14 → NOT outlier
  For x=100: robust_z = 0.6745 × (100-21)/6.5 ≈ 8.22 → OUTLIER (>3.0)

Step 5: Calculate score
  OHS = (1 - 1/10) × 100 = 90.0
```

**Failure Cases:**

1. **False Positives:** Legitimate extreme values flagged as outliers
   - *Mitigation:* Lower threshold; use domain knowledge to filter
2. **False Negatives:** Outliers within fences due to long-tail distribution
   - *Mitigation:* Use robust method (MAD preferred over Z-score)
3. **Tied Values:** Many identical values skew quartiles
   - *Mitigation:* Interpolation method for percentiles (linear/lower/higher)

**Unit Tests Required:**

```python
test_iqr_single_outlier()
  # One clear outlier → OHS ≈ 90

test_iqr_no_outliers()
  # Clean data → OHS = 100

test_iqr_all_outliers()
  # All values outside fences → OHS = 0

test_mad_robust_to_extreme_values()
  # MAD less affected by extreme outlier than Z-score

test_zero_variance()
  # All identical values → OHS = 100

test_insufficient_data()
  # <4 values → return NaN or neutral

test_method_comparison()
  # IQR vs MAD vs Z-score give expected differences
```

---

### 1e. Sample Sufficiency Score (SuS)

**Purpose:** Measure whether training set size is adequate for model learning.

**Raw Inputs:**
```
- current_samples: int (number of training records)
- minimum_required_samples: int (domain/model-specific)
- recommended_samples: int (optional; better quality)
```

**Input Validation:**
```
1. current_samples ≥ 0
2. minimum_required_samples > 0
3. current_samples ≥ 0, recommended_samples ≥ minimum_required_samples (if provided)
```

**Exact Formula:**

```
If recommended_samples not provided:
  sus_score = min(100, (current_samples / minimum_required_samples) × 100)

If recommended_samples provided:
  if current_samples < minimum_required_samples:
    sus_score = (current_samples / minimum_required_samples) × 50
  elif current_samples < recommended_samples:
    sus_score = 50 + 50 × (current_samples - minimum_required_samples) / (recommended_samples - minimum_required_samples)
  else:
    sus_score = 100

Range: [0, 100]
```

**Intermediate Calculations:**

```
Method 1 (Simple):
  ratio = current_samples / minimum_required_samples
  sus_score = min(100, ratio × 100)
  
  Example: current=150, minimum=100
  ratio = 1.5
  sus_score = min(100, 150) = 100

Method 2 (With Recommended):
  Zone 1: [0, minimum) → score = (current/minimum) × 50
  Zone 2: [minimum, recommended) → score = 50 + 50 × (current-minimum)/(recommended-minimum)
  Zone 3: [recommended, ∞) → score = 100
  
  Example: current=150, minimum=100, recommended=1000
  Zone 2: 50 + 50 × (150-100)/(1000-100) = 50 + 50 × 0.056 = 52.8
```

**Normalization:**

- Clamp output to [0, 100]
- Handle division by zero (minimum_required_samples should never be 0)

**Output Range:**

- Minimum: 0.0 (zero samples, obviously insufficient)
- Maximum: 100.0 (at or above recommended count)
- Typical: [70, 100] (varies by domain)

**Edge Case Behavior:**

1. **Zero current samples** → SuS = 0
2. **current > recommended** → SuS = 100 (no additional credit for oversizing)
3. **minimum == recommended** → Division by zero in Zone 2
   - *Mitigation:* Treat as Zone 1 (simple ratio)
4. **Negative samples** → Invalid; raise error
5. **Non-integer samples** → Round down or flag as unusual

**Example Calculation (Simple):**

```
minimum_required_samples = 500
recommended_samples = not provided

Test cases:
- current = 100 → sus_score = min(100, 100/500 × 100) = 20
- current = 500 → sus_score = min(100, 500/500 × 100) = 100
- current = 750 → sus_score = min(100, 750/500 × 100) = 100 (capped)
- current = 0 → sus_score = 0
```

**Example Calculation (With Recommended):**

```
minimum_required_samples = 500
recommended_samples = 10000

Test cases:
- current = 100 (Zone 1):
  sus_score = (100/500) × 50 = 10

- current = 500 (boundary):
  sus_score = 50 (transition point)

- current = 2500 (Zone 2):
  sus_score = 50 + 50 × (2500-500)/(10000-500)
            = 50 + 50 × 2000/9500
            = 50 + 10.53
            = 60.53

- current = 10000 (Zone 3):
  sus_score = 100

- current = 15000 (beyond recommended):
  sus_score = 100 (no extra credit)
```

**Failure Cases:**

1. **Domain-Specific Minimum:** What's sufficient varies wildly by domain
   - *Mitigation:* Configurable minimum; document per-domain values
2. **Curse of Dimensionality:** High-dimensional data needs more samples
   - *Mitigation:* Consider feature count in minimum (advanced)
3. **Imbalanced Classes:** Rare class needs larger overall dataset
   - *Mitigation:* Consider class distribution in calculation

**Unit Tests Required:**

```python
test_sus_zero_samples()
  # current = 0 → SuS = 0

test_sus_exact_minimum()
  # current = minimum → SuS = 100

test_sus_below_minimum()
  # current < minimum → SuS < 100

test_sus_with_recommended()
  # current between minimum and recommended → SuS between 50 and 100

test_sus_above_recommended()
  # current > recommended → SuS = 100 (capped)

test_sus_clamping()
  # Output always in [0, 100]
```

---

### 1f. Final Data Quality Score

**Exact Formula:**

```
DQS = 0.25×SS + 0.25×CS + 0.15×VS + 0.20×OHS + 0.15×SuS

Weights (INITIAL PROTOTYPE - CONFIGURABLE):
- Schema Score: 0.25
- Completeness Score: 0.25
- Validity Score: 0.15
- Outlier Health Score: 0.20
- Sample Sufficiency Score: 0.15

Range: [0, 100]
```

**Intermediate Calculations:**

```
Step 1: Compute each sub-score (SS, CS, VS, OHS, SuS)
  - Each is in range [0, 100]

Step 2: Weighted sum
  DQS = 0.25×SS + 0.25×CS + 0.15×VS + 0.20×OHS + 0.15×SuS

Step 3: Clamp to range
  DQS = max(0, min(100, DQS))

Output: scalar in [0, 100]
```

**Normalization:**

- All sub-scores normalized to [0, 100] before combination
- Weighted average ensures final score also in [0, 100]

**Output Range:**

- Minimum: 0.0 (complete data failure)
- Maximum: 100.0 (perfect data quality)
- Typical: [60, 95]

**Edge Case Behavior:**

1. **No input data** → DQS = 0 (or raise error)
2. **Partial failures** → Affected sub-scores zero out
3. **Perfect data** → All sub-scores 100 → DQS = 100

---

## Part 2: Drift Health Score (DHS)

### Overview

The Drift Health Score measures whether a participant's data distribution has shifted from the historical baseline using the Population Stability Index (PSI).

**Algorithm:**
1. Create histogram (bins) of historical data (reference distribution)
2. Create histogram of current data (actual distribution)
3. Compute PSI comparing actual to reference
4. Convert PSI to health score [0, 100]

---

### 2a. Population Stability Index (PSI)

**Purpose:** Quantify shift in univariate distributions.

**Raw Inputs:**
```
- historical_data: list/array of numeric values (reference distribution)
- current_data: list/array of numeric values (actual distribution)
- num_bins: int (default: 10, configurable)
- smoothing: bool (default: true)
- zero_handling: 'add_smoothing' or 'skip' or 'boundary_shift' (default: 'add_smoothing')
```

**Input Validation:**
```
1. historical_data has at least 50 samples (need representative distribution)
2. current_data has at least 10 samples
3. num_bins > 0 and reasonable (5-100 typical)
4. Both are numeric arrays
5. No NaN values (handle separately)
```

**Exact Formula:**

```
PSI = Σᵢ (actual_pct_i - expected_pct_i) × ln(actual_pct_i / expected_pct_i)

where:
- i = bin index
- actual_pct_i = fraction of current_data in bin i
- expected_pct_i = fraction of historical_data in bin i
- ln = natural logarithm

Interpretation:
- PSI < 0.1: negligible drift
- PSI 0.1–0.25: small drift
- PSI 0.25–0.50: medium drift
- PSI > 0.50: large drift (severe shift)
```

**Step-by-Step Calculation:**

```
Step 1: Determine bins from historical data
  If binning_method == 'quantile':
    bin_edges = [quantile(historical_data, i/num_bins) for i in 0..num_bins]
  Else if binning_method == 'equal_width':
    min_val = min(historical_data)
    max_val = max(historical_data)
    bin_edges = [min_val + (max_val - min_val) × i/num_bins for i in 0..num_bins]

Step 2: Create reference histogram (expected)
  expected_counts = histogram(historical_data, bin_edges)
  expected_pct = expected_counts / len(historical_data)

Step 3: Create actual histogram
  actual_counts = histogram(current_data, bin_edges)
  actual_pct = actual_counts / len(current_data)

Step 4: Handle zeros (smoothing)
  If zero_handling == 'add_smoothing':
    smoothing_factor = 0.5 / num_bins
    expected_pct = (expected_pct × len(historical_data) + smoothing_factor) / (len(historical_data) + smoothing_factor × num_bins)
    actual_pct = (actual_pct × len(current_data) + smoothing_factor) / (len(current_data) + smoothing_factor × num_bins)

Step 5: Calculate PSI
  psi = 0
  for each bin i:
    if expected_pct[i] > 0:
      psi += (actual_pct[i] - expected_pct[i]) × ln(actual_pct[i] / expected_pct[i])
    else:
      # Handle the case where expected is 0 but actual is not
      # This typically means new values in current data
      if zero_handling == 'boundary_shift':
        psi += actual_pct[i] × ln(actual_pct[i] / (smoothing_factor / num_bins))

Output: scalar PSI value (typically [0, 2])
```

**Binning Strategies:**

```
Method 1: Quantile Binning (recommended for uniform coverage)
- Equal number of samples per bin
- Handles different feature ranges naturally
- Better for highly skewed distributions
- Example: [0, 25, 50, 75, 100] percentiles

Method 2: Equal Width Binning (simpler)
- Equal-width intervals
- Can create empty bins for sparse distributions
- Better for uniform distributions
- Example: [0, 20, 40, 60, 80, 100] values

Method 3: Custom Binning (domain-specific)
- User provides bin edges
- Requires domain knowledge
- Example: age bins [0, 18, 35, 65, 100]
```

**Smoothing Justification:**

Problem: If expected_pct[i] = 0 (no historical samples in bin), division by zero in ln(actual/expected).

Solution: Laplace smoothing
```
Adjusted percentage = (count + smoothing) / (total + smoothing × num_bins)

Typical smoothing = 0.5 or 1.0
Effect: Prevents zero probabilities; small bias toward uniform distribution
```

**Zero Handling Strategies:**

```
Strategy 1: Add Smoothing (default)
- Add small constant before calculation
- Prevents division by zero
- Assumes zero count is measurement error, not true absence

Strategy 2: Skip (ignore zero bins)
- Only compute PSI for bins where expected_pct > 0
- Assumes historical data is complete representation
- Can underestimate drift in new regions

Strategy 3: Boundary Shift Detection (advanced)
- If actual_pct[i] > 0 but expected_pct[i] = 0, flag separately
- Indicates completely new data region (potential concern)
- Contributes higher penalty to PSI
```

**Intermediate Calculations (Example):**

```
Historical: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
Current:    [2, 3, 4, 5, 6, 7, 8, 9, 10, 20]  ← Note: 20 is outside original range

num_bins = 3 (for simplicity)
binning_method = 'equal_width'

Step 1: Bin edges
  min = 1, max = 10
  width = (10 - 1) / 3 = 3
  edges = [1, 4, 7, 10]

Step 2: Historical histogram
  Bin 1 [1,4):   values 1,2,3 → count=3 → pct=0.3
  Bin 2 [4,7):   values 4,5,6 → count=3 → pct=0.3
  Bin 3 [7,10]:  values 7,8,9,10 → count=4 → pct=0.4

Step 3: Current histogram
  Note: value 20 outside bins → assigned to highest bin
  Bin 1 [1,4):   values 2,3 → count=2 → pct=0.2
  Bin 2 [4,7):   values 4,5,6 → count=3 → pct=0.3
  Bin 3 [7,10]:  values 7,8,9,10,20 → count=5 → pct=0.5

Step 4: Calculate PSI
  PSI = Σ(actual - expected) × ln(actual / expected)
      = (0.2 - 0.3) × ln(0.2/0.3) + (0.3 - 0.3) × ln(0.3/0.3) + (0.5 - 0.4) × ln(0.5/0.4)
      = -0.1 × ln(0.667) + 0 + 0.1 × ln(1.25)
      = -0.1 × (-0.405) + 0.1 × 0.223
      = 0.0405 + 0.0223
      = 0.0628

Interpretation: PSI ≈ 0.063 → negligible drift (< 0.1)
```

**Handling Missing Values:**

```
Before calculating PSI:
1. Remove NaN from both historical and current
2. If >5% missing in historical, flag data quality issue separately
3. If >10% missing in current, flag as incomplete update

Example:
  historical = [1, 2, 3, None, 5] → remove None → [1, 2, 3, 5]
  current = [2, 3, 4, None, None, 6] → remove None → [2, 3, 4, 6]
  Proceed with cleaned data
```

---

### 2b. Feature-Level Drift Detection

**Purpose:** Compute PSI for each numeric feature independently.

**Raw Inputs:**
```
- historical_data: DataFrame with multiple columns
- current_data: DataFrame with same columns
- features_to_check: List[str] (default: all numeric columns)
- num_bins: int or Dict[feature_name → num_bins]
- exclude_features: List[str] (features to skip)
```

**Calculation:**

```
For each feature in features_to_check:
  if feature in exclude_features:
    skip
  
  psi_feature = PSI(historical_data[feature], current_data[feature])
  psi_dict[feature] = psi_feature

Output: Dict[feature_name → psi_value]
```

**Example:**

```
Historical data (4 samples):
  age: [25, 32, 45, 28]
  income: [50000, 75000, 120000, 60000]
  score: [0.8, 0.9, 0.7, 0.85]

Current data (4 samples):
  age: [26, 31, 50, 27]  ← Similar to historical
  income: [55000, 80000, 150000, 65000]  ← Slightly higher
  score: [0.2, 0.3, 0.4, 0.35]  ← Very different

Feature-level PSI:
  age: 0.04 (negligible)
  income: 0.15 (small drift)
  score: 0.95 (large drift!) ← Would be flagged

Interpretation:
- Age distribution stable
- Income slightly shifted higher
- Score distribution drastically different (potential data issue)
```

---

### 2c. Drift-to-Health Score Conversion

**Purpose:** Convert PSI (technical metric) into 0-100 health score (business metric).

**Raw Inputs:**
```
- psi_value: float (typically [0, 2])
- psi_thresholds: Dict with keys 'negligible', 'small', 'medium', 'large'
  Default: {negligible: 0.1, small: 0.25, medium: 0.5}
- conversion_method: 'linear' (default), 'sigmoid', 'custom'
```

**Exact Formula (Linear Conversion):**

```
if psi ≤ threshold_negligible:
  dhs_single = 100
elif psi ≤ threshold_small:
  dhs_single = 90 + 10 × (threshold_small - psi) / (threshold_small - threshold_negligible)
elif psi ≤ threshold_medium:
  dhs_single = 70 + 20 × (threshold_medium - psi) / (threshold_medium - threshold_small)
else:  # psi > threshold_medium
  dhs_single = max(0, 70 - 70 × (psi - threshold_medium) / threshold_medium)

Clamp to [0, 100]
```

**Alternative: Sigmoid Conversion (Smooth Boundaries):**

```
dhs_single = 100 / (1 + exp(k × (psi - psi_inflection)))

where:
- k = steepness (default: 10)
- psi_inflection = transition point (default: 0.25)

Effect: Smooth S-curve instead of piecewise linear
```

**Intermediate Calculations (Linear Example):**

```
Thresholds: negligible=0.1, small=0.25, medium=0.5

Test cases:
- PSI = 0.03:
  0.03 ≤ 0.1 → DHS = 100

- PSI = 0.15:
  0.1 < 0.15 ≤ 0.25 → DHS = 90 + 10 × (0.25-0.15)/(0.25-0.1)
                         = 90 + 10 × 0.10/0.15
                         = 90 + 6.67 = 96.67

- PSI = 0.35:
  0.25 < 0.35 ≤ 0.5 → DHS = 70 + 20 × (0.5-0.35)/(0.5-0.25)
                        = 70 + 20 × 0.15/0.25
                        = 70 + 12 = 82

- PSI = 0.75:
  0.75 > 0.5 → DHS = max(0, 70 - 70 × (0.75-0.5)/0.5)
                    = max(0, 70 - 35) = 35

- PSI = 1.50:
  1.50 > 0.5 → DHS = max(0, 70 - 70 × 1.0/0.5)
                    = max(0, 70 - 140) = 0
```

**Multi-Feature Aggregation:**

```
If checking multiple features, combine their drift scores:

Method 1: Average
  dhs = mean(dhs_feature_1, dhs_feature_2, ..., dhs_feature_n)

Method 2: Weighted Average (domain knowledge)
  dhs = Σᵢ w_i × dhs_feature_i
  where w_i = importance weight (sum to 1.0)

Method 3: Minimum (conservative - any significant drift reduces score)
  dhs = min(dhs_feature_1, dhs_feature_2, ...)

Method 4: Maximum Drift (flag highest issue)
  dhs = dhs_of_feature_with_max_psi
```

**Output Range:**

- Minimum: 0.0 (extreme drift, PSI >> 1.0)
- Maximum: 100.0 (no drift, PSI < 0.1)
- Typical: [70, 100] (most stable participants)

**Edge Cases:**

```
1. All features have zero variance → PSI undefined
   Behavior: Mark as data quality issue, DHS = 50 (uncertain)

2. Current data is empty → Cannot compute
   Behavior: Flag as missing update, DHS = 0

3. Historical data is empty → No baseline
   Behavior: Use neutral DHS = 50 (no comparison possible)

4. Categorical features → PSI not applicable
   Behavior: Skip; only process numeric features
```

---

## Part 3: Update Safety Score (USS)

### Overview

The Update Safety Score measures whether model parameter updates are anomalous or pathological.

**Components:**
1. Structural Validity (no NaN/Inf)
2. Magnitude Score (parameter sizes in expected range)
3. Freshness Score (update not stale)
4. Consistency Score (matches historical patterns)

---

### 3a. Delta Weight Calculation

**Purpose:** Compute the model parameter change (Delta W) from global to client version.

**Raw Inputs:**
```
- W_client: Dict[layer_name → parameter_tensor]
  (client's model weights after local training)
- W_global: Dict[layer_name → parameter_tensor]
  (global model weights before aggregation)
```

**Exact Formula:**

```
For each layer:
  ΔW_layer = W_client_layer - W_global_layer

Aggregate:
  ΔW_norm_l2 = sqrt(Σ_layer ||ΔW_layer||²)
  ΔW_norm_l1 = Σ_layer ||ΔW_layer||_1
```

**Edge Cases:**

```
1. Shape mismatch → Error; cannot compute
2. Layer absent in client → Missing layer (possible architecture issue)
3. NaN in W_client → Flag as model corruption
4. Inf in W_client → Flag as divergence/explosion
```

---

### 3b. Structural Validity Score

**Purpose:** Check for numerical anomalies (NaN, Inf, complex numbers).

**Raw Inputs:**
```
- delta_w: parameter delta
- epsilon: small constant (default: 1e-10)
```

**Exact Formula:**

```
num_nan = count(isnan(delta_w))
num_inf = count(isinf(delta_w))
num_complex = count(iscomplex(delta_w))
num_invalid = num_nan + num_inf + num_complex

invalid_ratio = num_invalid / total_parameters

structural_validity_score = {
  1.0          if invalid_ratio == 0  [perfect]
  0.8          if 0 < invalid_ratio < 0.001  [trace amounts, rounding error]
  0.5          if 0.001 ≤ invalid_ratio < 0.01  [concerning]
  0.2          if 0.01 ≤ invalid_ratio < 0.1  [serious corruption]
  0.0          if invalid_ratio ≥ 0.1  [severe corruption, model unusable]
}

Range: [0, 1]
```

**Example:**

```
Model has 1,000,000 parameters
Found: 5 NaN values, 2 Inf values
Invalid count = 7
Invalid ratio = 7 / 1,000,000 = 0.000007
This is < 0.001 → structural_validity_score = 0.8
```

---

### 3c. Magnitude Score

**Purpose:** Check if parameter changes are within expected bounds (not exploding or vanishing).

**Raw Inputs:**
```
- delta_w: parameter delta
- historical_deltas: List[previous_delta_w] (for baseline)
- method: 'iqr' (default) or 'mad' or 'zscore'
- threshold: multiplier for outlier detection (default: 3.0)
```

**Exact Formula (using Median Absolute Deviation):**

```
1. Compute statistics on historical deltas
   median_delta = median(||ΔW_historical||)
   mad = median(abs(||ΔW_historical|| - median_delta))

2. Robust Z-score for current delta
   robust_z = (||ΔW_current|| - median_delta) / (0.6745 × (MAD + epsilon))

3. Scale to [0, 1] based on outlier criterion
   if abs(robust_z) ≤ threshold:
     magnitude_score_layer = 1.0  [normal magnitude]
   else if abs(robust_z) ≤ 2 × threshold:
     magnitude_score_layer = 0.5 + 0.5 × (1 - abs(robust_z)/(2×threshold))  [outlier, penalty]
   else:
     magnitude_score_layer = 0.0  [extreme outlier]

4. Aggregate across layers (equal weight or configurable)
   magnitude_score = mean(magnitude_score_layer for each layer)

Range: [0, 1]
```

**Intermediate Calculations:**

```
Historical layer norms (L2): [1.5, 1.8, 1.6, 2.0, 1.7]
Current layer norm: 5.0

Step 1: Statistics
  median = 1.7
  deviations = abs([1.5-1.7, 1.8-1.7, 1.6-1.7, 2.0-1.7, 1.7-1.7])
            = [0.2, 0.1, 0.1, 0.3, 0]
  MAD = median([0, 0.1, 0.1, 0.2, 0.3]) = 0.1

Step 2: Robust Z-score
  robust_z = (5.0 - 1.7) / (0.6745 × 0.1)
           = 3.3 / 0.06745
           ≈ 48.9  [extremely high!]

Step 3: Scale (with threshold=3.0)
  abs(48.9) >> 2×3.0 → magnitude_score = 0.0

Interpretation: Update has extremely large gradient; possible divergence
```

---

### 3d. Freshness Score

**Purpose:** Penalize stale updates (trained from outdated data or long ago).

**Raw Inputs:**
```
- timestamp_created: datetime (when update was created)
- timestamp_now: datetime (current time)
- max_acceptable_age: timedelta (default: 7 days)
```

**Exact Formula:**

```
age_hours = (timestamp_now - timestamp_created).total_seconds() / 3600

if age_hours ≤ 1:  [freshly trained]
  freshness_score = 1.0

elif age_hours ≤ 24:  [trained within 1 day]
  freshness_score = 0.99

elif age_hours ≤ 72:  [trained within 3 days]
  freshness_score = 0.95 - 0.05 × (age_hours - 24) / 48

elif age_hours ≤ max_acceptable_age_hours:  [< 7 days]
  freshness_score = 0.8 - 0.5 × (age_hours - 72) / (max_acceptable_age_hours - 72)

else:  [stale]
  freshness_score = max(0.1, 0.3 - 0.2 × (age_hours - max_acceptable_age_hours) / max_acceptable_age_hours)

Range: [0.1, 1.0]
```

**Example:**

```
max_acceptable_age = 7 days = 168 hours

- age = 1 hour → freshness_score = 1.0
- age = 24 hours → freshness_score = 0.99
- age = 48 hours → freshness_score = 0.95 - 0.05 × (48-24)/48 = 0.925
- age = 120 hours → freshness_score = 0.8 - 0.5 × (120-72)/(168-72) = 0.8 - 0.244 = 0.556
- age = 168 hours (7 days, boundary) → freshness_score = 0.3
- age = 336 hours (14 days, 2× max) → freshness_score = max(0.1, 0.3 - 0.2) = 0.1
```

---

### 3e. Consistency Score

**Purpose:** Check if current update follows historical patterns for this participant.

**Raw Inputs:**
```
- delta_w_current: current parameter delta
- historical_deltas: List[previous_delta_w]
- historical_metadata: List[{timestamp, global_accuracy, ...}]
```

**Exact Formula:**

```
1. Compute gradient direction similarity
   direction_similarity = dot_product(δW_current, mean(δW_historical)) / (||δW_current|| × ||mean(δW_historical)||)
   [cosine similarity, bounded in [-1, 1]]

2. Compute magnitude consistency
   median_mag = median(||δW_historical||)
   current_mag = ||δW_current||
   mag_ratio = current_mag / (median_mag + epsilon)
   
   consistency_magnitude = {
     1.0          if 0.5 < mag_ratio < 2.0  [within 2x range]
     0.8          if 0.25 < mag_ratio ≤ 0.5 or 2.0 < mag_ratio ≤ 4.0  [2-4x]
     0.5          if 0.1 < mag_ratio ≤ 0.25 or 4.0 < mag_ratio ≤ 10.0  [4-10x]
     0.2          if mag_ratio ≤ 0.1 or mag_ratio > 10.0  [extreme]
   }

3. Combine scores
   consistency_score = 0.7 × direction_similarity + 0.3 × consistency_magnitude
   
   Then clamp and scale to [0, 1]
   consistency_score = max(0, min(1, consistency_score))

Range: [0, 1]
```

**Example:**

```
Historical deltas (simplified):
  Update 1: direction=[+1, +0.5], magnitude=1.5
  Update 2: direction=[+0.9, +0.6], magnitude=1.8
  Update 3: direction=[+1.1, +0.4], magnitude=1.6

Mean historical: direction ≈ [+1.0, +0.5], magnitude ≈ 1.63

Current update: direction=[+0.8, +0.7], magnitude=3.2

Step 1: Direction similarity
  cosine_similarity([0.8, 0.7], [1.0, 0.5]) / (norm[0.8,0.7] × norm[1.0,0.5])
  ≈ 0.81  [reasonably similar direction]

Step 2: Magnitude consistency
  mag_ratio = 3.2 / 1.63 ≈ 1.96
  Ratio in [0.5, 2.0) → consistency_magnitude = 1.0

Step 3: Combine
  consistency_score = 0.7 × 0.81 + 0.3 × 1.0
                    = 0.567 + 0.3 = 0.867
```

---

### 3f. Final Update Safety Score

**Exact Formula:**

```
USS = 0.35×SVS + 0.30×MS + 0.20×FS + 0.15×CS

where:
- SVS = Structural Validity Score [0, 1]
- MS = Magnitude Score [0, 1]
- FS = Freshness Score [0.1, 1]
- CS = Consistency Score [0, 1]

Weights (INITIAL PROTOTYPE - CONFIGURABLE):
  Structural: 0.35 [most critical - no NaN/Inf]
  Magnitude: 0.30 [parameter ranges reasonable]
  Freshness: 0.20 [data not stale]
  Consistency: 0.15 [historical pattern]

Range: [0, 1]
```

**Scaling to [0, 100]:**

```
USS_final = USS × 100

Range: [0, 100]
```

---

## Part 4: Reliability Score (RS)

### Overview

The Reliability Score measures participant's operational track record across multiple metrics.

**Components:**
1. Availability (% of rounds with successful submission)
2. Heartbeat Health (update frequency)
3. Success Rate (fraction of updates accepted vs. rejected)
4. Latency Health (response time within bounds)
5. Consecutive Failure Penalty (punish recent bad streak)

---

### 4a. Availability Score

**Purpose:** Track how often participant sends updates (shows up for training).

**Raw Inputs:**
```
- total_rounds: int (number of aggregation rounds that occurred)
- successful_submits: int (number where participant sent update)
```

**Exact Formula:**

```
availability = successful_submits / total_rounds

availability_score = availability × 100

Range: [0, 100]
```

**Example:**

```
total_rounds = 20
successful_submits = 18
availability = 18/20 = 0.9
availability_score = 90
```

---

### 4b. Heartbeat Health Score

**Purpose:** Check regularity of updates (detect long absences).

**Raw Inputs:**
```
- timestamps: List[datetime] (when updates were received)
- expected_interval: timedelta (how often updates expected)
```

**Exact Formula:**

```
intervals = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]

if len(intervals) == 0:
  heartbeat_score = 100  [only one update, can't assess pattern]

else:
  median_interval = median(intervals)
  deviations = [abs(interval - median_interval) for interval in intervals]
  
  consistency_ratio = (median_interval) / (median(deviations) + epsilon)
  
  heartbeat_score = {
    100         if consistency_ratio > 5  [very regular]
    90          if 3 ≤ consistency_ratio ≤ 5  [regular]
    70          if 2 ≤ consistency_ratio < 3  [somewhat regular]
    50          if 1 ≤ consistency_ratio < 2  [sporadic]
    30          if consistency_ratio < 1  [very irregular]
  }

Range: [0, 100]
```

**Example:**

```
Timestamps: [10:00, 10:05, 10:10, 10:15, 10:30, 10:35, ...]
Intervals (minutes): [5, 5, 5, 15, 5, ...]
Median interval: 5 minutes
Deviations: [0, 0, 0, 10, 0, ...]
Median deviation: 0
Consistency ratio: 5 / (small value) → very high
Heartbeat score: 100 (if consistency_ratio > 5)

Alternative (less regular):
Timestamps: [10:00, 10:05, 10:12, 10:30, 11:00]
Intervals: [5, 7, 18, 30]
Median: 12.5
Deviations: [7.5, 5.5, 5.5, 17.5]
Median deviation: 11.5
Consistency ratio: 12.5/11.5 ≈ 1.09 → heartbeat_score = 50 (sporadic)
```

---

### 4c. Success Rate Score

**Purpose:** Track fraction of updates accepted vs. flagged/blocked.

**Raw Inputs:**
```
- total_updates: int
- accepted: int
- flagged: int
- blocked: int
```

**Exact Formula:**

```
success_rate = accepted / total_updates

success_rate_score = success_rate × 100

Range: [0, 100]
```

**Example:**

```
total_updates = 20
accepted = 16
flagged = 3
blocked = 1

success_rate = 16/20 = 0.8
success_rate_score = 80
```

---

### 4d. Latency Health Score

**Purpose:** Check response times are acceptable.

**Raw Inputs:**
```
- latencies: List[seconds] (time to generate and send update)
- acceptable_threshold: seconds (default: 3600 = 1 hour)
```

**Exact Formula:**

```
fraction_on_time = count(latency ≤ acceptable_threshold) / len(latencies)

if fraction_on_time >= 0.95:
  latency_health_score = 100

elif fraction_on_time >= 0.80:
  latency_health_score = 80 + 20 × (fraction_on_time - 0.80) / 0.15

elif fraction_on_time >= 0.60:
  latency_health_score = 50 + 30 × (fraction_on_time - 0.60) / 0.20

else:
  latency_health_score = max(10, 50 × fraction_on_time)

Range: [0, 100]
```

**Example:**

```
latencies (minutes): [5, 8, 120, 45, 30, 7, 9, 1800]  [last one is 30 hrs, way overdue]
acceptable_threshold = 60 minutes

On-time count: [5, 8, 30, 45, 7] = 5 out of 8
fraction_on_time = 5/8 = 0.625

Since 0.625 in [0.60, 0.80):
latency_health_score = 50 + 30 × (0.625 - 0.60) / 0.20
                     = 50 + 30 × 0.025 / 0.20
                     = 50 + 3.75 = 53.75
```

---

### 4e. Consecutive Failure Penalty

**Purpose:** Penalize if participant has recent bad streak.

**Raw Inputs:**
```
- update_history: List[{timestamp, status}]  [status ∈ {accepted, flagged, blocked}]
- lookback_window: int (number of recent updates to examine, default: 5)
```

**Exact Formula:**

```
recent_updates = update_history[-lookback_window:]

consecutive_failures = 0
for update in reversed(recent_updates):
  if update.status == 'blocked':
    consecutive_failures += 1
  else:
    break  [stop counting at first non-failure]

failure_penalty = {
  0        if consecutive_failures == 0
  -10      if consecutive_failures == 1
  -25      if consecutive_failures == 2
  -50      if consecutive_failures >= 3
}

Range: [-50, 0]
```

**Example:**

```
Recent update history (last 5):
  [accepted, accepted, flagged, blocked, blocked]

consecutive_failures = 2 (the two most recent)
failure_penalty = -25
```

---

### 4f. Final Reliability Score

**Exact Formula:**

```
RS_raw = 0.35×AS + 0.25×HS + 0.20×SRS + 0.20×LHS

where:
- AS = Availability Score [0, 100]
- HS = Heartbeat Health Score [0, 100]
- SRS = Success Rate Score [0, 100]
- LHS = Latency Health Score [0, 100]

RS_with_penalty = RS_raw + failure_penalty

RS_final = max(0, min(100, RS_with_penalty))

Range: [0, 100]
```

**Example:**

```
AS = 90 (90% of rounds)
HS = 85 (regular updates)
SRS = 80 (80% accepted)
LHS = 75 (75% on-time)
failure_penalty = -25 (recent bad streak)

RS_raw = 0.35×90 + 0.25×85 + 0.20×80 + 0.20×75
       = 31.5 + 21.25 + 16 + 15
       = 83.75

RS_final = 83.75 - 25 = 58.75
```

---

## Part 5: Performance Score (PS)

### Overview

The Performance Score measures the impact of aggregating participant's update on global model performance.

**Flexibility:** Metric choice depends on ML task (classification, regression, ranking, NLP, etc.).

---

### 5a. Common Performance Metrics

**For Classification:**
```
F1 Score = 2 × (Precision × Recall) / (Precision + Recall)
Precision = TP / (TP + FP)
Recall = TP / (TP + FN)

Range: [0, 1]

Why: Balances false positives and false negatives
When to use: Multi-class or imbalanced classification
```

**For Regression:**
```
Mean Absolute Error (MAE) = mean(|y_true - y_pred|)
Mean Squared Error (MSE) = mean((y_true - y_pred)²)
Root Mean Squared Error (RMSE) = sqrt(MSE)

Range: [0, ∞)

Why: Sensitive to large errors
When to use: Continuous prediction tasks
```

**For Ranking:**
```
NDCG@k = Normalized Discounted Cumulative Gain
AUC-ROC = Area Under Receiver Operating Characteristic

Range: [0, 1]

Why: Measures ranking quality
When to use: Recommendation systems, search ranking
```

**For NLP/LLMs:**
```
BLEU Score = n-gram precision with brevity penalty
ROUGE = Recall-Oriented Understudy for Gisting Evaluation
Perplexity = exp(cross_entropy_loss)

Range: varies

Why: Task-specific evaluation
When to use: Machine translation, summarization, language modeling
```

---

### 5b. Performance Health Calculation

**Purpose:** Compare current model performance to baseline.

**Raw Inputs:**
```
- baseline_metric: float (performance before aggregation)
- current_metric: float (performance after aggregation)
- metric_type: 'higher_is_better' or 'lower_is_better'
- task: str (e.g., 'classification', 'regression')
```

**Exact Formula:**

```
if metric_type == 'higher_is_better':  [e.g., F1, NDCG, AUC]
  
  if baseline_metric == 0:
    delta = 0  [no baseline]
  else:
    delta = (current_metric - baseline_metric) / baseline_metric
  
  performance_health = min(100, 100 × (1 + delta))
  
  # Clipping: delta ∈ [-1, 1] maps to health ∈ [0, 100]
  # Example: if delta = +0.1 (10% improvement), health = 110 → clamped to 100
  # Example: if delta = -0.1 (10% degradation), health = 90

elif metric_type == 'lower_is_better':  [e.g., MAE, MSE]
  
  if baseline_metric == 0:
    delta = 0
  else:
    delta = (baseline_metric - current_metric) / baseline_metric
  
  performance_health = min(100, 100 × (1 + delta))
  # Similar logic but direction reversed

Range: [0, 100]
```

**Intermediate Calculations:**

```
Example 1: F1 Score (higher is better)
  baseline_f1 = 0.850
  current_f1 = 0.865
  delta = (0.865 - 0.850) / 0.850 = 0.0176 (1.76% improvement)
  performance_health = min(100, 100 × 1.0176) = 101.76 → clamped to 100

Example 2: Mean Squared Error (lower is better)
  baseline_mse = 0.150
  current_mse = 0.140
  delta = (0.150 - 0.140) / 0.150 = 0.0667 (6.67% improvement in lower metric)
  performance_health = min(100, 100 × 1.0667) = 106.67 → clamped to 100

Example 3: F1 Score (degradation)
  baseline_f1 = 0.850
  current_f1 = 0.810
  delta = (0.810 - 0.850) / 0.850 = -0.047 (4.7% degradation)
  performance_health = 100 × (1 - 0.047) = 95.3
```

**Normalization:**

- Clamp to [0, 100] range
- Small improvements/degradations (< ±1%) should not significantly move score
- Large degradations (> -20%) should push toward 0
- Large improvements (> +20%) capped at 100

**Output Range:**

- Minimum: 0 (catastrophic degradation)
- Maximum: 100 (improvement or stable)
- Typical: [85, 100] (most updates neutral or improving)

---

### 5c. Per-Slice Performance (Fairness Check)

**Purpose:** Ensure update doesn't degrade performance for specific subgroups (fairness).

**Raw Inputs:**
```
- slice_metrics: Dict[slice_name → {baseline_metric, current_metric}]
  Example: {
    'age_0_18': {baseline: 0.85, current: 0.83},
    'age_18_65': {baseline: 0.92, current: 0.91},
    'age_65_plus': {baseline: 0.88, current: 0.78}  ← Problem!
  }
```

**Calculation:**

```
For each slice:
  slice_health = performance_health(baseline, current)

fairness_penalty = {
  0       if max(slice_deltas) - min(slice_deltas) < 0.02  [consistent across slices]
  -5      if 0.02 ≤ difference < 0.05  [some variance]
  -15     if 0.05 ≤ difference < 0.10  [significant fairness issue]
  -30     if difference ≥ 0.10  [severe fairness problem]
}

Example:
  age_0_18: delta = -2.3%
  age_18_65: delta = -1.1%
  age_65_plus: delta = -11.4%  ← Severe degradation for elderly
  
  max - min = |-1.1% - (-11.4%)| = 10.3% → fairness_penalty = -30
```

---

### 5d. Final Performance Score

**Exact Formula:**

```
PS = performance_health + fairness_penalty

Range: [-30, 100]

Then normalize to [0, 100] if needed:
PS_normalized = max(0, min(100, PS))
```

---

## Summary Table: All Scores

| Score | Input | Formula | Range | Weight in Trust |
|-------|-------|---------|-------|-----------------|
| **DQS** | Schema, completeness, validity, outliers, samples | Weighted avg of 5 sub-scores | [0,100] | 25% |
| **DHS** | Historical vs. current distributions | PSI + threshold conversion | [0,100] | 25% |
| **USS** | Model deltas, metadata | Struct validity + magnitude + freshness + consistency | [0,100] | 20% |
| **RS** | Submission history, timing | Availability + heartbeat + success + latency | [0,100] | 20% |
| **PS** | Global model performance | Before/after metric comparison | [0,100] | 10% |

---

**Status:** All score specifications complete with formulas, examples, edge cases, and test requirements.

**Next:** Implementation document (FORMULAS.md) and worked examples (WORKED_SCORE_EXAMPLES.md).
