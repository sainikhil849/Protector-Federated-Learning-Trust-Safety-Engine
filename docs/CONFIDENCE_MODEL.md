# Confidence Model: Evidence Quality Assessment

## Preamble: Why Confidence Matters

The **Trust Score** answers: "How healthy or trustworthy does the participant appear operationally?"

The **Confidence Score** answers: "How sufficient, complete, recent, and stable is the evidence used to calculate that assessment?"

A Trust Score of 90 (indicating strong operational health) means very different things depending on Confidence:

- **Trust=90, Confidence=95**: We have overwhelming evidence of good behavior. Strongly believe this estimate.
- **Trust=90, Confidence=20**: We infer good behavior from limited signals. Should investigate before fully relying on this.
- **Trust=30, Confidence=95**: We have overwhelming evidence of poor behavior. This is a serious concern.
- **Trust=30, Confidence=10**: Single anomaly detected. Might be measurement error. Requires investigation before escalating.

**Purpose of Confidence Model:**

Confidence quantifies the **evidentiary foundation** of the Trust Score. A strong confidence score indicates:
- Sufficient data points
- Historical context available
- Key metrics are present
- Evidence is recent
- Measurements are stable

A weak confidence score indicates:
- Limited data
- Short history
- Missing metrics
- Stale evidence
- Inconsistent measurements

This document specifies exactly how Confidence is calculated.

---

## Design Principle: Five Evidence Dimensions

Confidence depends on five aspects of evidence quality:

| Dimension | Weight | What It Measures | Risk If Low |
|-----------|--------|------------------|------------|
| **Data Coverage** | 30% | How many data points inform the score? | Single data point ≠ reliable trend |
| **Historical Coverage** | 25% | How long have we been observing this participant? | Recent outlier vs. chronic problem unclear |
| **Metric Availability** | 20% | What fraction of expected metrics are available? | Missing critical metrics distort picture |
| **Evidence Freshness** | 15% | How recent is the evidence? | Stale data doesn't reflect current state |
| **Statistical Stability** | 10% | How consistent are measurements over time? | High variance = low confidence in central tendency |

---

## Component 1: Data Coverage

**Question:** How many data points inform the score?

### Rationale

Each dimension of the Trust Score (DQS, DHS, USS, RS, PS) depends on underlying data points:
- DQS uses: schema checks, completeness counts, validity checks, outlier counts, sample counts (~10 measurements)
- DHS uses: PSI calculations per feature (~5-50 features)
- USS uses: structural checks, magnitude measurements, freshness checks (~8 measurements)
- RS uses: availability data, heartbeat records, success counts (~15 measurements)
- PS uses: model metrics, fairness measurements (~5-10 measurements)

**Total potential data points:** 50-150 depending on configuration.

**Data Coverage Score (DCS)** measures: what fraction of potentially available data points are actually present?

### Formula

```
Available_Points = count of non-null measurements that were used in Trust calculation
Expected_Points = total measurements expected for a complete assessment

Data_Coverage_Ratio = Available_Points / Expected_Points

Data_Coverage_Score = min(100, Data_Coverage_Ratio × 100)
```

### Input Specification

```
Required inputs:
- available_points: integer, count of non-null measurements (0 to expected max)
- expected_points: integer, baseline expected measurements

Constraints:
- available_points ≥ 0
- expected_points > 0
- available_points ≤ expected_points × 2  (can't exceed theoretical max)

Edge cases:
- If available_points = 0: DCS = 0
- If available_points ≥ expected_points: DCS = 100 (capped at max)
- If expected_points = 0: DCS = undefined (should not occur; set to 0)
```

### Calculation Steps

```
Step 1: Count available measurements
For Trust Score calculation, count all measurements used:
- Schema score (1 if calculated, 0 if skipped)
- Completeness score (1)
- Validity score (1)
- Outlier health (1)
- Sample sufficiency (1)
- PSI per feature (N_features)
- Structural validity (1)
- Magnitude score (1)
- Freshness score (1)
- Consistency score (1)
- Availability (1)
- Heartbeat health (1)
- Success rate (1)
- Latency health (1)
- Consecutive failures (1)
- Performance metrics (2-3)
- Fairness metrics (1-3)

Typical available_points = 35-60

Step 2: Determine expected baseline
Expected_Points = participant-specific, but typically 45 for standard setup

Step 3: Calculate ratio
Ratio = available_points / expected_points

Step 4: Normalize to 0-100
DCS = min(100, Ratio × 100)
```

### Example Calculation

```
Scenario: Hospital-5 submits update
Measurements actually present:
- Schema: ✓ (1)
- Completeness: ✓ (1)
- Validity: ✓ (1)
- Outlier health: ✓ (1)
- Sample sufficiency: ✓ (1)
- PSI (age, income, diagnosis, lab_values, risk_score) = 5
- Structural validity: ✓ (1)
- Magnitude: ✓ (1)
- Freshness: ✓ (1)
- Consistency: ✓ (1)
- Availability: ✓ (1)
- Heartbeat: ✓ (1)
- Success rate: ✓ (1)
- Latency: ✓ (1)
- Consecutive failures: ✓ (1)
- Model F1 before/after: ✓ (1)
- Fairness (balanced accuracy per demographic): ✓ (1)

Available_Points = 23 (including 5 PSI features)
Expected_Points = 25 (includes expected 5 features)

DCS = min(100, (23/25) × 100) = 92.0
```

### Normalization

**Output Range:** [0, 100]

```
DCS = 0:      Critical failure, no data available
DCS = 25-50:  Sparse data, minimal evidence
DCS = 50-75:  Moderate data, reasonably complete
DCS = 75-95:  Good data, most metrics present
DCS = 100:    Comprehensive data, all expected metrics available
```

### What This Component Captures

✅ Breadth of evidence (how many different measurements?)  
✅ Completeness of expected measurements  
✅ Detectability of data quality issues (more data → better detection)  

### What This Component Does NOT Capture

❌ Time dimension (covered by Historical Coverage)  
❌ Recency (covered by Evidence Freshness)  
❌ Consistency/stability (covered by Statistical Stability)  
❌ Whether measurements are accurate (only that they exist)  

### Failure Modes

```
Failure Mode 1: All measurements present but stale
DCS = 100 (full data coverage)
But measurements are 3 months old
Mitigation: Evidence Freshness component will be low

Failure Mode 2: One critical metric missing
Expected: 25 points, Available: 24 points
DCS = 96 (appears healthy)
But missing metric is crucial (e.g., model fairness)
Mitigation: Metric Availability component flags this

Failure Mode 3: Measurements present but all null
Available_Points counted, but all values are NaN
DCS = 100 (counted as "available")
But actually no usable data
Mitigation: Pre-processing must filter NaN; if all null, set available_points = 0
```

---

## Component 2: Historical Coverage

**Question:** How long have we been observing this participant, and how much history do we have?

### Rationale

A participant with 1 week of data and 1 year of data both can submit an update today. But the confidence in their Trust Score is very different:

- **1 week data**: First update, might be anomaly, no baseline
- **1 year data**: Established pattern, anomalies stand out, behavior consistent

Historical Coverage captures: **"How much history informs this assessment?"**

### Formula

```
Observation_Period_Days = today - first_update_date

Minimum_Observation_Period = 7 days
Standard_Observation_Period = 90 days
Ideal_Observation_Period = 365 days

Historical_Coverage_Ratio = min(1.0, Observation_Period_Days / Standard_Observation_Period)

Historical_Coverage_Score = Historical_Coverage_Ratio × 100
```

### Input Specification

```
Required inputs:
- first_update_date: timestamp (ISO 8601 format)
- reference_date: timestamp (typically "today", ISO 8601 format)

Constraints:
- first_update_date ≤ reference_date
- first_update_date ≥ (reference_date - 10 years)  [sanity check]

Edge cases:
- If first_update_date is in the future: HCS = 0
- If first_update_date = reference_date: HCS = 0 (zero history)
- If observation period > 365 days: HCS = 100 (capped)
```

### Calculation Steps

```
Step 1: Calculate observation period
Observation_Days = (reference_date - first_update_date).days

Step 2: Handle boundary cases
if Observation_Days < 0:
  HCS = 0  [invalid, participant doesn't exist yet]
elif Observation_Days = 0:
  HCS = 0  [brand new, no history]
elif Observation_Days < 7:
  HCS = (Observation_Days / 7) × 100  [very new participant]
elif Observation_Days < 90:
  HCS = (Observation_Days / 90) × 100
elif Observation_Days >= 365:
  HCS = 100  [sufficient history]
else:
  HCS = (Observation_Days / 90) × 100  [capped at 100 when days ≥ 90]

Step 3: Clamp to [0, 100]
HCS = max(0, min(100, HCS))
```

### Example Calculation

```
Example 1: Brand New Participant
First update: 2026-08-17
Reference date: 2026-08-17 (same day)
Observation_Days = 0
HCS = 0  (no history)

Interpretation: New participant, zero historical context.
Confidence should be flagged as low regardless of current behavior.

---

Example 2: Established Participant (90 days)
First update: 2026-05-17
Reference date: 2026-08-17
Observation_Days = 92
HCS = min(100, (92/90) × 100) = 100  (capped at 100)

Interpretation: 3+ months of history. Sufficient baseline established.

---

Example 3: Moderately Established Participant (30 days)
First update: 2026-07-17
Reference date: 2026-08-17
Observation_Days = 31
HCS = (31/90) × 100 = 34.4

Interpretation: 1 month of history. Early stage, patterns not yet clear.

---

Example 4: Intermediate Participant (45 days)
First update: 2026-07-03
Reference date: 2026-08-17
Observation_Days = 45
HCS = (45/90) × 100 = 50.0

Interpretation: 1.5 months of history. Moderate baseline, but patterns still developing.
```

### Normalization

**Output Range:** [0, 100]

```
HCS = 0:       New participant (< 1 day)
HCS = 25:      Emerging participant (1-3 weeks)
HCS = 50:      Establishing participant (1-1.5 months)
HCS = 75:      Developing participant (2-3 months)
HCS = 100:     Established participant (3+ months)
```

### What This Component Captures

✅ Maturity of relationship (how long we've worked with this participant)  
✅ Baseline establishment (can we detect when behavior changes?)  
✅ Anomaly detection capability (more history = better anomaly detection)  

### What This Component Does NOT Capture

❌ Data quality within that history (covered by Data Coverage)  
❌ Freshness of most recent data (covered by Evidence Freshness)  
❌ Whether historical data is consistent (covered by Statistical Stability)  

### Failure Modes

```
Failure Mode 1: New participant with excellent first update
HCS = 0 (brand new)
But first update is high quality and trustworthy
Confidence = low, yet behavior is good
Mitigation: This is correct behavior. New participants should have lower confidence
  regardless of first update quality. Low confidence doesn't mean distrust,
  just insufficient evidence for strong claim.

Failure Mode 2: Long history, but recent regime change
Observation_Days = 365, HCS = 100
But organization changed 2 weeks ago (new team, new process)
Old history no longer predictive
Mitigation: Data Coverage and Statistical Stability will be lower because
  recent patterns don't match historical patterns.

Failure Mode 3: Participant inactive for 6 months
First update: 2025-02-17, Last update: 2025-02-17
Reference date: 2026-08-17
Observation_Days = 545, HCS = 100
But no updates in 6 months!
Mitigation: Evidence Freshness will be very low (stale data). Statistical Stability
  will flag that recent updates are missing.
```

---

## Component 3: Metric Availability

**Question:** What fraction of expected metrics are available for this assessment?

### Rationale

Some participants provide rich data; others provide sparse data. Metric Availability captures:

"Of all metrics we'd ideally like to assess this participant, how many are actually present?"

Example metrics:
- Data Quality: schema, completeness, validity, outliers, sample count
- Drift: PSI per feature
- Update Safety: structural validity, magnitude, freshness, consistency
- Reliability: availability, heartbeat, success rate, latency
- Performance: model metrics, fairness metrics

A participant might be missing:
- No historical baseline (can't compute drift)
- No model performance data (can't assess performance impact)
- No fairness data (can't assess for bias)

Metric Availability quantifies the gaps.

### Formula

```
Available_Metrics = count of distinct metric categories with ≥1 measurement

Expected_Metrics = standard metric categories for assessment
  Standard set: [schema, completeness, validity, outliers, sample_sufficiency,
                 psi_features, structural_validity, magnitude, freshness,
                 consistency, availability, heartbeat, success_rate, latency,
                 model_performance, fairness]
  Count = 16 categories

Metric_Availability_Ratio = Available_Metrics / Expected_Metrics

Metric_Availability_Score = min(100, Metric_Availability_Ratio × 100)
```

### Input Specification

```
Required inputs:
- metric_presence: dict mapping metric_category -> boolean (present/absent)
  Example:
  {
    "schema": true,
    "completeness": true,
    "validity": true,
    "outliers": true,
    "sample_sufficiency": true,
    "psi_features": true,
    "structural_validity": true,
    "magnitude": true,
    "freshness": true,
    "consistency": true,
    "availability": true,
    "heartbeat": true,
    "success_rate": true,
    "latency": true,
    "model_performance": true,
    "fairness": false  [missing: no fairness data]
  }

Constraints:
- metric_presence must have exactly 16 entries (or be configurable per domain)
- Values must be boolean or null (treated as false)

Edge cases:
- If all metrics missing: MAS = 0
- If all metrics present: MAS = 100
- Metrics marked null/NaN: count as absent
```

### Calculation Steps

```
Step 1: Count available metrics
available_count = 0
for each (metric_name, is_present) in metric_presence:
  if is_present and is_not_null:
    available_count += 1

Step 2: Count expected metrics
expected_count = len(metric_presence)  [should be 16 standard]

Step 3: Calculate ratio
ratio = available_count / expected_count

Step 4: Normalize to 0-100
MAS = min(100, ratio × 100)
```

### Example Calculation

```
Example 1: Complete Metric Set
Participant: Hospital-5, comprehensive submission
Metric presence:
  schema: ✓
  completeness: ✓
  validity: ✓
  outliers: ✓
  sample_sufficiency: ✓
  psi_features: ✓ (5 features tested)
  structural_validity: ✓
  magnitude: ✓
  freshness: ✓
  consistency: ✓
  availability: ✓
  heartbeat: ✓
  success_rate: ✓
  latency: ✓
  model_performance: ✓
  fairness: ✓

Available = 16, Expected = 16
MAS = (16/16) × 100 = 100

Interpretation: All metrics available, full assessment possible.

---

Example 2: Missing Fairness
Participant: Hospital-3, no demographic breakdown
Metric presence: [16 metrics, but fairness = false]

Available = 15, Expected = 16
MAS = (15/16) × 100 = 93.75

Interpretation: One important metric missing (fairness), but assessment
  still comprehensive. Could indicate either (a) model isn't production yet,
  or (b) fairness analysis not performed. Should investigate.

---

Example 3: Minimal Metrics
Participant: NewStartup, first submission
Metric presence:
  schema: ✓
  completeness: ✓
  validity: ✓
  outliers: ✗ (no historical baseline for comparison)
  sample_sufficiency: ✓
  psi_features: ✗ (can't compute PSI, no baseline)
  structural_validity: ✓
  magnitude: ✗ (no historical magnitude baseline)
  freshness: ✓
  consistency: ✗ (can't assess consistency with no history)
  availability: ✗ (only one submission)
  heartbeat: ✗ (insufficient history)
  success_rate: ✗ (insufficient history)
  latency: ✗ (insufficient history)
  model_performance: ✓
  fairness: ✗ (not computed)

Available = 8, Expected = 16
MAS = (8/16) × 100 = 50.0

Interpretation: About half the expected metrics available. New participant
  lacks historical context (drift, consistency, reliability). Assessment
  is biased toward snapshot data quality, not behavior patterns.
```

### Normalization

**Output Range:** [0, 100]

```
MAS = 0:       No metrics available (critical failure)
MAS = 25-50:   Sparse metrics, major gaps (new participant, missing baselines)
MAS = 50-75:   Moderate metrics, some gaps
MAS = 75-95:   Most metrics available, minor gaps
MAS = 100:     All metrics available, comprehensive assessment
```

### What This Component Captures

✅ Breadth of assessment dimensions  
✅ Which critical metrics are missing  
✅ Ability to assess all Trust Score components  

### What This Component Does NOT Capture

❌ Whether metrics are actually good quality (just that they're present)  
❌ Recency of metrics (covered by Evidence Freshness)  
❌ Consistency over time (covered by Statistical Stability)  

### Failure Modes

```
Failure Mode 1: All metrics present but baseline missing
MAS = 100 (all expected metrics exist)
But PSI and consistency require historical baseline
Baseline is null/missing
Mitigation: Historical Coverage component will be low (new participant).
  Overall Confidence will be lower because Historical Coverage is factored in.

Failure Mode 2: Custom metrics not in standard set
Participant submits 25 metrics, but only 8 overlap with expected 16
MAS = 50 (considers only standard 16)
But 17 additional custom metrics available
Mitigation: System should be flexible to accept and score custom metrics.
  Could have "expected metrics per domain" configuration.

Failure Mode 3: Metric marked present but all values are NaN
metric_presence["model_performance"] = true
But all performance values are NaN
MAS = 100 (counts as present)
But actually no usable data
Mitigation: Data validation should filter NaN values. If metric is all-NaN,
  should be marked as effectively absent.
```

---

## Component 4: Evidence Freshness

**Question:** How recent is the evidence that informs this assessment?

### Rationale

A Trust assessment based on data from today is more reliable than one based on data from 6 months ago.

Evidence Freshness measures: **"How old is the most recent evidence used in this assessment?"**

Different metrics have different relevance periods:
- Model performance: relevant for ~30 days (models drift)
- Data quality: relevant for ~14 days (training data changes)
- Operational reliability: relevant for ~7 days (systems evolve)
- Drift detection: should use recent historical window (~30 days)

### Formula

```
Metric Freshness values:
- Most recent metric timestamp: timestamp_most_recent_metric
- Reference time: now
- Age_Hours = (now - timestamp_most_recent_metric) / 3600

Age_Decay_Function:
  if Age_Hours ≤ 24:
    Freshness_Ratio = 1.0  (data from today is fresh)
  elif Age_Hours ≤ 168:  (7 days)
    Freshness_Ratio = 1.0 - (Age_Hours - 24) / 168
  elif Age_Hours ≤ 720:  (30 days)
    Freshness_Ratio = 0.75 - ((Age_Hours - 168) / 720) × 0.75
  elif Age_Hours ≤ 2160:  (90 days)
    Freshness_Ratio = 0.25 - ((Age_Hours - 720) / 1440) × 0.25
  else:
    Freshness_Ratio = 0.0  (stale, no confidence)

Evidence_Freshness_Score = Freshness_Ratio × 100
```

### Input Specification

```
Required inputs:
- timestamp_most_recent_metric: ISO 8601 timestamp
- reference_time: ISO 8601 timestamp (default: now)

Constraints:
- timestamp_most_recent_metric ≤ reference_time
- timestamp_most_recent_metric ≥ (reference_time - 10 years)

Edge cases:
- If timestamp_most_recent_metric is in the future: EFS = 0
- If timestamp_most_recent_metric is very old (>2 years): EFS = 0
- If timestamps equal: EFS = 100 (data generated right now)
```

### Calculation Steps

```
Step 1: Calculate age in hours
age_hours = (reference_time - timestamp_most_recent_metric).total_seconds() / 3600

Step 2: Apply decay function
if age_hours < 0:
  freshness_ratio = 0.0  [invalid future timestamp]
elif age_hours <= 24:
  freshness_ratio = 1.0
elif age_hours <= 168:
  freshness_ratio = 1.0 - (age_hours - 24) / (168 - 24)
  freshness_ratio = 1.0 - (age_hours - 24) / 144
elif age_hours <= 720:
  freshness_ratio = 0.75 - ((age_hours - 168) / (720 - 168)) × 0.75
  freshness_ratio = 0.75 - ((age_hours - 168) / 552) × 0.75
elif age_hours <= 2160:
  freshness_ratio = 0.25 - ((age_hours - 720) / (2160 - 720)) × 0.25
  freshness_ratio = 0.25 - ((age_hours - 720) / 1440) × 0.25
else:
  freshness_ratio = 0.0

Step 3: Normalize to 0-100
EFS = freshness_ratio × 100
```

### Example Calculations

```
Example 1: Fresh Data (submitted today)
timestamp_most_recent_metric: 2026-08-17 09:00:00
reference_time: 2026-08-17 10:00:00
age_hours = 1

freshness_ratio = 1.0  (within 24 hours)
EFS = 100

Interpretation: Data from today, maximum freshness.

---

Example 2: Recent Data (3 days old)
timestamp_most_recent_metric: 2026-08-14 10:00:00
reference_time: 2026-08-17 10:00:00
age_hours = 72

72 is between 24 and 168
freshness_ratio = 1.0 - (72 - 24) / 144
freshness_ratio = 1.0 - 48/144 = 1.0 - 0.333 = 0.667

EFS = 66.7

Interpretation: Data from 3 days ago, still quite fresh.

---

Example 3: Moderately Stale (14 days)
timestamp_most_recent_metric: 2026-08-03 10:00:00
reference_time: 2026-08-17 10:00:00
age_hours = 336

336 is between 168 and 720
freshness_ratio = 0.75 - ((336 - 168) / 552) × 0.75
freshness_ratio = 0.75 - (168/552) × 0.75
freshness_ratio = 0.75 - 0.304 × 0.75
freshness_ratio = 0.75 - 0.228 = 0.522

EFS = 52.2

Interpretation: Data from 2 weeks ago, moderately stale. Still has some utility,
but confidence should be reduced.

---

Example 4: Stale (45 days)
timestamp_most_recent_metric: 2026-07-03 10:00:00
reference_time: 2026-08-17 10:00:00
age_hours = 1080

1080 is between 720 and 2160
freshness_ratio = 0.25 - ((1080 - 720) / 1440) × 0.25
freshness_ratio = 0.25 - (360/1440) × 0.25
freshness_ratio = 0.25 - 0.25 × 0.25
freshness_ratio = 0.25 - 0.0625 = 0.1875

EFS = 18.75

Interpretation: Data from 1.5 months ago, quite stale. Limited confidence
in this assessment.

---

Example 5: Very Stale (6 months)
timestamp_most_recent_metric: 2026-02-17 10:00:00
reference_time: 2026-08-17 10:00:00
age_hours = 4392

4392 > 2160
freshness_ratio = 0.0

EFS = 0

Interpretation: Data from 6 months ago, no confidence. Assessment
should be considered invalid for current decision-making.
```

### Freshness Decay Curve

```
Freshness Curve Over Time:

100 |●●●●●●●●●●●
    |          \●●
 75 |            \●●●
    |                \●●●
 50 |                    \●●●●
    |                        \●●●●●●
 25 |                              \●●●●●●●
    |                                      \●
  0 |________|_______|_______|_______|_______|
    0       24h     7d      30d      90d    180d
    
    - 0-24h:   100 (full confidence)
    - 24h-7d:  Linear decay from 100 to 75
    - 7d-30d:  Linear decay from 75 to 25
    - 30d-90d: Linear decay from 25 to 0
    - >90d:    0 (no confidence)
```

### Normalization

**Output Range:** [0, 100]

```
EFS = 100:     Data from today (0-24 hours)
EFS = 75-99:   Data from this week (24h-7d)
EFS = 50-75:   Data from 1-2 weeks old
EFS = 25-50:   Data from 2-4 weeks old
EFS = 1-25:    Data from 1-3 months old
EFS = 0:       Data older than 3 months (too stale to use)
```

### What This Component Captures

✅ Age of most recent evidence  
✅ Relevance of data for current assessment  
✅ Whether data reflects current state or history  

### What This Component Does NOT Capture

❌ Consistency over time (covered by Statistical Stability)  
❌ How often updates are submitted (covered by Historical Coverage implicitly)  
❌ Whether recent data is of good quality (covered by Data Coverage)  

### Failure Modes

```
Failure Mode 1: Single recent measurement, no historical baseline
EFS = 100 (data from today is fresh)
But only 1 data point, no trend
Mitigation: Data Coverage and Statistical Stability will be low. Overall
  Confidence will be low because these components are included.

Failure Mode 2: Participant hasn't submitted update in 2 months
EFS = 0 (most recent metric is 2 months old)
But participant submitted excellent updates historically
Confidence indicates lack of evidence
Mitigation: This is correct. Without recent data, we can't assess current state.
  Organization might have shut down, changed processes, or temporarily paused.
  Can't assume historical behavior continues without recent evidence.

Failure Mode 3: Timestamp precision loss
Metric submitted with only date, not time
Treated as submitted at 00:00:00
But actually submitted at 23:59:00 same day
Age calculation off by up to 24 hours
Mitigation: Request full timestamp with time component.
```

---

## Component 5: Statistical Stability

**Question:** How consistent are measurements over time? Do repeated measurements of the same participant show stable or erratic values?

### Rationale

A participant with stable, consistent measurements deserves more confidence than one with erratic, volatile measurements.

Examples:
- Participant A: Trust scores 88, 89, 87, 89, 88 (stable)
- Participant B: Trust scores 95, 30, 88, 15, 90 (erratic)

Both have average trust ≈ 85, but Participant A's assessment is much more reliable.

Statistical Stability measures: **"How consistent are the measurements over recent history?"**

### Formula

```
Measurement_History = list of recent Trust scores (e.g., last 10 submissions)
Recent_Window = last N days (e.g., N=30)

Mean_Score = mean(Measurement_History)
StdDev_Score = stdev(Measurement_History)

Coefficient_of_Variation = StdDev_Score / (Mean_Score + ε)

Stability_Ratio = 1.0 - min(1.0, Coefficient_of_Variation / 0.30)

Statistical_Stability_Score = Stability_Ratio × 100
```

### Input Specification

```
Required inputs:
- measurement_history: list of numeric values (recent Trust scores)
  Example: [88, 89, 87, 89, 88, 90, 88, 87, 89, 88]
- window_days: integer, time window for history (default 30 days)

Constraints:
- measurement_history must have ≥ 2 elements
  (need at least 2 points to calculate variation)
- If < 2 measurements: SSS = 0 (insufficient data for stability assessment)
- All values must be numeric and in range [0, 100]

Edge cases:
- All measurements identical: StdDev = 0, SSS = 100 (perfect stability)
- Only 1 measurement: SSS = 0 (can't assess stability with single point)
- Measurements all missing/NaN: SSS = 0
- High variation: SSS can approach 0
```

### Calculation Steps

```
Step 1: Validate measurement history
if len(measurement_history) < 2:
  SSS = 0  [insufficient data to assess stability]
  return

Step 2: Filter to recent window
filtered_history = [x for x in measurement_history 
                    if (now - timestamp[x]).days <= window_days]

if len(filtered_history) < 2:
  SSS = 0  [no sufficient recent measurements]
  return

Step 3: Calculate statistics
mean_score = mean(filtered_history)
stdev_score = stdev(filtered_history)

Step 4: Calculate coefficient of variation
if mean_score ≈ 0:
  cv = infinity  [edge case: mean near zero]
  SSS = 0
  return

cv = stdev_score / mean_score

Step 5: Calculate stability ratio
tolerance_cv = 0.30  [allow up to 30% coefficient of variation]

stability_ratio = 1.0 - min(1.0, cv / tolerance_cv)

Step 6: Normalize to 0-100
SSS = max(0, stability_ratio × 100)
```

### Example Calculations

```
Example 1: Stable Participant
Measurement history (10 most recent Trust scores):
[88, 89, 87, 89, 88, 90, 88, 87, 89, 88]

Mean = 88.3
StdDev = 0.95
CV = 0.95 / 88.3 = 0.0108  (1.08%)

Stability ratio = 1.0 - min(1.0, 0.0108 / 0.30)
                = 1.0 - min(1.0, 0.036)
                = 1.0 - 0.036
                = 0.964

SSS = 96.4

Interpretation: Very stable. Scores cluster tightly. High confidence
in the measurement.

---

Example 2: Moderately Stable Participant
Measurement history:
[82, 85, 79, 88, 81, 84, 80, 87, 83, 86]

Mean = 83.5
StdDev = 3.27
CV = 3.27 / 83.5 = 0.0392  (3.92%)

Stability ratio = 1.0 - min(1.0, 0.0392 / 0.30)
                = 1.0 - min(1.0, 0.131)
                = 1.0 - 0.131
                = 0.869

SSS = 86.9

Interpretation: Moderately stable. Scores vary by a few points.
Still good confidence.

---

Example 3: Volatile Participant
Measurement history:
[95, 30, 88, 15, 90, 25, 92, 20, 89, 18]

Mean = 56.2
StdDev = 37.9
CV = 37.9 / 56.2 = 0.674  (67.4%)

Stability ratio = 1.0 - min(1.0, 0.674 / 0.30)
                = 1.0 - min(1.0, 2.247)
                = 1.0 - 1.0
                = 0.0

SSS = 0

Interpretation: Highly erratic. Score jumps wildly. No confidence
in stability. Something unstable about this participant (could indicate
underlying issues or measurement problems).

---

Example 4: Moderately Erratic Participant
Measurement history:
[85, 65, 80, 55, 78, 60, 82, 58, 75, 62]

Mean = 70.0
StdDev = 10.5
CV = 10.5 / 70.0 = 0.15  (15%)

Stability ratio = 1.0 - min(1.0, 0.15 / 0.30)
                = 1.0 - min(1.0, 0.50)
                = 1.0 - 0.50
                = 0.50

SSS = 50.0

Interpretation: Moderately erratic. Scores vary by ~15%. Borderline
confidence. Investigate underlying causes.

---

Example 5: Newly Established Participant (only 2 measurements)
Measurement history: [85, 87]

Mean = 86.0
StdDev = 1.41
CV = 1.41 / 86.0 = 0.0164

Stability ratio = 1.0 - min(1.0, 0.0164 / 0.30)
                = 1.0 - 0.055
                = 0.945

SSS = 94.5

Interpretation: Only 2 measurements, but they're close. SSS is high,
but should be interpreted cautiously because we don't have much history.
This is why other Confidence components (Historical Coverage, Data Coverage)
are important—they'll flag the limited data.
```

### Statistical Interpretation

```
Coefficient of Variation (CV) scale:
CV < 0.05  (5%):    Excellent stability
CV 0.05-0.10:       Very good stability
CV 0.10-0.20:       Good stability
CV 0.20-0.30:       Moderate stability (threshold for tolerance)
CV 0.30-0.50:       Borderline stability
CV > 0.50:          Poor stability (erratic)

Tolerance threshold: CV = 0.30 (30%)
Rationale: Beyond 30% variation relative to mean, pattern is unreliable
for governance decisions.
```

### Normalization

**Output Range:** [0, 100]

```
SSS = 100:    CV < 5% (excellent stability)
SSS = 75-99:  CV 5-10% (very good stability)
SSS = 50-75:  CV 10-20% (good to moderate)
SSS = 25-50:  CV 20-30% (borderline)
SSS = 1-25:   CV 30-50% (poor, erratic)
SSS = 0:      CV > 50% or insufficient data (unreliable)
```

### What This Component Captures

✅ Consistency of measurements over time  
✅ Volatility/erraticity of Trust scores  
✅ Reliability of current measurement relative to recent history  
✅ Whether changes reflect true change or measurement noise  

### What This Component Does NOT Capture

❌ Whether measurements are accurate (just that they're consistent)  
❌ Direction of change (improving vs. degrading)  
❌ Root cause of instability (could be data, system, or participant)  
❌ Long-term trends (only recent stability)  

### Failure Modes

```
Failure Mode 1: Recent sudden change, but stable before
Historical scores: [88, 89, 87, 88, 89, 88, 87, 89]  (stable, CV≈1%)
Most recent: 45  (major drop)
Including recent: [88, 89, 87, 88, 89, 88, 87, 89, 45]  (CV≈11%)

SSS will drop from ~99 to ~63
Interpretation: Correct! Stability has degraded because something changed.
This alerts us to investigate the recent sharp decline.

---

Failure Mode 2: Two-state oscillation
Measurement history: [50, 95, 50, 95, 50, 95, 50, 95]  (perfectly alternating)

Mean = 72.5
StdDev = 22.4
CV = 0.309  (30.9%)

SSS ≈ 0 (just above threshold)

Interpretation: Correct. Oscillating pattern is unreliable, indicates
underlying instability even though values are predictable.

---

Failure Mode 3: Gradual degradation misidentified as stability
Measurement history (over time):
[90, 89, 88, 87, 86, 85, 84, 83, 82, 81]  (steady decline)

Mean = 85.5
StdDev = 3.27
CV = 0.0382  (3.82%)

SSS ≈ 87.4 (appears stable)

But actually trending downward! Stability metric doesn't capture trend.

Mitigation: This is expected. SSS measures variance around mean, not trends.
For trend detection, a separate trend analysis component would be needed.
Could add: slope of recent measurements, Mann-Kendall test, etc.
But for now, SSS captures variability, which is its intended purpose.
```

---

## Composite Confidence Score

**Question:** Combining all five components, what is the overall evidence quality?

### Formula

```
CONFIDENCE = 
  0.30 × Data_Coverage_Score
  + 0.25 × Historical_Coverage_Score
  + 0.20 × Metric_Availability_Score
  + 0.15 × Evidence_Freshness_Score
  + 0.10 × Statistical_Stability_Score

Range: [0, 100]
```

### Weight Justification

| Component | Weight | Rationale |
|-----------|--------|-----------|
| **Data Coverage** | 30% | Most critical: more data points → more evidence |
| **Historical Coverage** | 25% | Very important: established relationships provide context |
| **Metric Availability** | 20% | Important: gaps in metrics reduce assessment completeness |
| **Evidence Freshness** | 15% | Moderately important: recent data more relevant than stale |
| **Statistical Stability** | 10% | Least critical: consistency useful but not as fundamental as data quantity |

### Calculation Steps

```
Step 1: Calculate all five components
dcs = data_coverage_score()        [0-100]
hcs = historical_coverage_score()  [0-100]
mas = metric_availability_score()  [0-100]
efs = evidence_freshness_score()   [0-100]
sss = statistical_stability_score() [0-100]

Step 2: Weighted sum
confidence_raw = 0.30*dcs + 0.25*hcs + 0.20*mas + 0.15*efs + 0.10*sss

Step 3: Clamp to valid range
confidence = max(0, min(100, confidence_raw))

Step 4: Calculate confidence interval (optional, advanced)
If we have component uncertainties:
  confidence_ci_lower = confidence - margin_of_error
  confidence_ci_upper = confidence + margin_of_error
  (see Advanced Confidence below)
```

### Example Composite Calculations

See "Three Detailed Examples" section below.

---

## Confidence Classification

**Question:** What level of confidence do we have in this assessment?

### Classification Rules

```
Confidence Score Range → Classification

[90, 100]     → HIGH
  Interpretation: Strong evidence, recent, complete, stable.
                 Trust score is reliable. Can base major decisions on this.

[70, 90)      → MEDIUM
  Interpretation: Good evidence, but some gaps or mild staleness.
                 Trust score is informative but use with some caution.
                 Should monitor for changes.

[40, 70)      → LOW
  Interpretation: Weak evidence, significant gaps or older data.
                 Trust score is tentative. Treat as exploratory.
                 Recommend additional investigation before major decisions.

[0, 40)       → INSUFFICIENT_EVIDENCE
  Interpretation: Critical gaps in evidence. Score is unreliable.
                 Cannot confidently base decisions on this.
                 Require more data, more history, or more recent metrics
                 before trusting assessment.
```

### Classification Examples

```
Example 1: Established Participant with Recent Update
DCS = 95 (comprehensive data)
HCS = 100 (12 months history)
MAS = 100 (all metrics)
EFS = 100 (submitted today)
SSS = 92 (very stable pattern)

Confidence = 0.30*95 + 0.25*100 + 0.20*100 + 0.15*100 + 0.10*92
           = 28.5 + 25 + 20 + 15 + 9.2
           = 97.7

Classification: HIGH
Interpretation: Excellent. Can fully rely on this assessment.

---

Example 2: Moderate Participant with Some Staleness
DCS = 78 (good data, minor gaps)
HCS = 85 (6 months history)
MAS = 88 (one metric missing)
EFS = 55 (data 14 days old)
SSS = 81 (mostly stable)

Confidence = 0.30*78 + 0.25*85 + 0.20*88 + 0.15*55 + 0.10*81
           = 23.4 + 21.25 + 17.6 + 8.25 + 8.1
           = 78.6

Classification: MEDIUM
Interpretation: Good evidence but some concerns (staleness, missing metric).
Should monitor for recent changes. Might want to request update.

---

Example 3: New Participant
DCS = 82 (decent first submission)
HCS = 15 (1 week old)
MAS = 50 (missing baseline metrics)
EFS = 100 (data from today)
SSS = 0 (only one submission, can't assess stability)

Confidence = 0.30*82 + 0.25*15 + 0.20*50 + 0.15*100 + 0.10*0
           = 24.6 + 3.75 + 10 + 15 + 0
           = 53.35

Classification: LOW
Interpretation: Data quality looks decent, but insufficient history,
missing baseline metrics, can't assess stability. Wait for more submissions
before making critical decisions. Recommend preliminary ALLOW with monitoring.

---

Example 4: Critical Gaps
DCS = 25 (minimal data, sparse submission)
HCS = 5 (1 day old)
MAS = 30 (major metrics missing)
EFS = 20 (data 40 days old, not updated)
SSS = 0 (insufficient history)

Confidence = 0.30*25 + 0.25*5 + 0.20*30 + 0.15*20 + 0.10*0
           = 7.5 + 1.25 + 6 + 3 + 0
           = 17.75

Classification: INSUFFICIENT_EVIDENCE
Interpretation: Cannot assess this participant reliably.
Multiple critical gaps. Require: recent data, more complete metrics,
established history, before trusting any assessment.
Recommend BLOCK pending more evidence or MONITOR with reservations.
```

---

## Three Detailed Examples

### EXAMPLE 1: Strong Trust, Strong Evidence

**Scenario:** Hospital-5, 12 months operational, submitting weekly updates

```
Input Data:
  Trust Score = 90
  
  Data Coverage:
    Available_Points = 47
    Expected_Points = 50
    DCS = (47/50) × 100 = 94.0
  
  Historical Coverage:
    First update: 2025-08-17
    Reference date: 2026-08-17
    Observation_Days = 365
    HCS = 100  (capped at 365 days)
  
  Metric Availability:
    All 16 expected metrics present
    MAS = (16/16) × 100 = 100.0
  
  Evidence Freshness:
    Most recent metric: 2026-08-17 09:30:00
    Reference: 2026-08-17 10:00:00
    Age_Hours = 0.5
    EFS = 100.0  (within 24 hours)
  
  Statistical Stability:
    Recent 10 submissions Trust scores:
    [91, 90, 89, 91, 90, 92, 89, 91, 90, 90]
    Mean = 90.3, StdDev = 0.95, CV = 0.0105
    SSS = 94.5

Confidence Calculation:
  CONFIDENCE = 0.30×94.0 + 0.25×100.0 + 0.20×100.0 + 0.15×100.0 + 0.10×94.5
             = 28.2 + 25.0 + 20.0 + 15.0 + 9.45
             = 97.65

Classification: HIGH

Interpretation:
  ✅ Trust Score = 90 indicates strong operational health
  ✅ Confidence = 97.65 indicates very strong evidence for this assessment
  
  This hospital is:
  - Well-established (12 months of data)
  - Consistently performing (stable scores around 90)
  - Recently assessed (submitted today)
  - Comprehensively evaluated (all metrics available)
  
  DECISION: Confidently ALLOW this update. Strong assessment backed by
  substantial evidence. This participant has earned trust through
  demonstrated reliable behavior over time.
```

---

### EXAMPLE 2: Strong Trust, Weak Evidence

**Scenario:** StartupAI, first submission, looks very good but insufficient data

```
Input Data:
  Trust Score = 90
  
  Data Coverage:
    Available_Points = 28
    Expected_Points = 50
    DCS = (28/50) × 100 = 56.0
    [Can't fully assess; missing several historical metrics]
  
  Historical Coverage:
    First update: 2026-08-17
    Reference date: 2026-08-17
    Observation_Days = 0
    HCS = 0  (brand new, no history)
  
  Metric Availability:
    Metrics present: [schema, completeness, validity, sample_sufficiency,
                      structural_validity, magnitude, freshness,
                      model_performance]
    Metrics missing: [outliers (no baseline), psi_features (no baseline),
                      consistency (no history), availability (too new),
                      heartbeat (too new), success_rate (too new),
                      latency (too new), fairness]
    MAS = (8/16) × 100 = 50.0
  
  Evidence Freshness:
    Most recent metric: 2026-08-17 14:30:00
    Reference: 2026-08-17 14:45:00
    Age_Hours = 0.25
    EFS = 100.0  (submitted just now)
  
  Statistical Stability:
    Only 1 submission (current)
    Cannot assess stability
    SSS = 0  (insufficient history)

Confidence Calculation:
  CONFIDENCE = 0.30×56.0 + 0.25×0 + 0.20×50.0 + 0.15×100.0 + 0.10×0
             = 16.8 + 0 + 10.0 + 15.0 + 0
             = 41.8

Classification: LOW

Interpretation:
  ⚠️ Trust Score = 90 looks excellent on the surface
  ⚠️ Confidence = 41.8 reveals critical weaknesses in evidence
  
  This startup:
  - Just submitted first update (no historical context)
  - Can't assess outliers (no baseline to compare against)
  - Can't assess drift (no historical distribution)
  - Can't assess consistency (only one data point)
  - Can't assess reliability (too new)
  
  The high Trust Score is based on:
  - Good data quality (what we can measure)
  - Good model structure and magnitudes
  - Good immediate performance
  
  But we lack:
  - Behavioral history (is this an anomaly?)
  - Consistency verification (is this repeatable?)
  - Operational track record (can we trust them long-term?)
  
  DECISION: Conditional ALLOW with monitoring. The first submission looks
  good, but we lack sufficient evidence to fully trust this participant.
  Recommend:
  1. Allow this update (it passes quality checks)
  2. Monitor the next 3-5 submissions
  3. Recalculate confidence after 2-4 weeks
  4. Escalate to BLOCK if future submissions show quality degradation
  
  Don't dismiss the high Trust Score; just recognize it's based on
  limited evidence (snapshot quality, not established behavior).
```

---

### EXAMPLE 3: Weak Trust, Strong Evidence

**Scenario:** Hospital-3, degrading performance, well-documented pattern

```
Input Data:
  Trust Score = 35
  
  Data Coverage:
    Available_Points = 48
    Expected_Points = 50
    DCS = (48/50) × 100 = 96.0
  
  Historical Coverage:
    First update: 2025-02-17
    Reference date: 2026-08-17
    Observation_Days = 546
    HCS = 100  (>365 days)
  
  Metric Availability:
    All 16 metrics present and measured
    MAS = (16/16) × 100 = 100.0
  
  Evidence Freshness:
    Most recent metric: 2026-08-16 08:00:00
    Reference: 2026-08-17 10:00:00
    Age_Hours = 26
    EFS = 100.0 - (26-24)/144 = 98.6  (still very recent)
  
  Statistical Stability:
    Recent 12 submissions Trust scores:
    [85, 80, 78, 72, 68, 65, 58, 52, 45, 38, 35, 32]
    Clear downward trend
    Mean = 59.3, StdDev = 21.2, CV = 0.357
    SSS = 0  (erratic relative to tolerance threshold)

Confidence Calculation:
  CONFIDENCE = 0.30×96.0 + 0.25×100.0 + 0.20×100.0 + 0.15×98.6 + 0.10×0
             = 28.8 + 25.0 + 20.0 + 14.79 + 0
             = 88.59

Classification: MEDIUM  (borderline HIGH)

Interpretation:
  ⚠️ Trust Score = 35 indicates serious operational problems
  ✅ Confidence = 88.59 indicates we have strong evidence to support this concern
  
  This hospital:
  - Has been observed for 18 months (long track record)
  - Provides comprehensive data (all metrics)
  - Is recently assessed (submitted yesterday)
  - Shows clear pattern of degradation
  
  Evidence strongly suggests:
  - Data quality declining over time
  - Model performance degrading
  - Update patterns becoming unreliable
  - Serious operational issue, not temporary glitch
  
  Pattern analysis:
  - Submissions 1-3: High trust (85, 80, 78)
  - Submissions 4-6: Declining (72, 68, 65)
  - Submissions 7-12: Poor (58, 52, 45, 38, 35, 32)
  
  This is a **degradation scenario**, not a **new scenario**. We have
  historical evidence that Hospital-3 was trustworthy, then degraded.
  
  DECISION: BLOCK this update with investigation.
  Rationale:
  1. 18-month trend shows consistent degradation (not random fluctuation)
  2. Current Trust Score (35) is critically low
  3. We have strong confidence in this assessment (88.59)
  4. Pattern suggests systemic problem (data quality? model training? team change?)
  
  Recommended actions:
  1. Escalate to Hospital-3 operations team
  2. Request explanation for trend
  3. Audit their data collection and model training process
  4. Offer support/investigation to identify root cause
  5. Consider temporary pause until issues resolved
  
  This is a case where strong confidence in a bad outcome warrants
  serious attention and escalation.
```

---

## Confidence-Trust Interpretation Matrix

How to interpret different combinations of Trust and Confidence scores:

```
┌─────────────┬──────────────┬──────────────┬──────────────┬──────────────┐
│   TRUST ↓   │  HIGH CONF   │ MEDIUM CONF  │  LOW CONF    │ INSUFF CONF  │
│ CONFIDENCE→ │   (90-100)   │   (70-90)    │   (40-70)    │   (0-40)     │
├─────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ HIGH TRUST  │ ✅ ALLOW     │ ✅ ALLOW     │ ⚠️ ALLOW +   │ ⚠️ ALLOW +   │
│ (75-100)    │ Confident &  │ Good &      │ MONITOR      │ MONITOR      │
│             │ reliable     │ reliable    │ (weak data)  │ (insufficient)
│             │              │             │              │              │
├─────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ MEDIUM TRUST│ ⚠️ REVIEW    │ ⚠️ REVIEW    │ ⚠️ REVIEW    │ ❌ BLOCK     │
│ (60-75)     │ Borderline,  │ Borderline,  │ Borderline,  │ Insufficient │
│             │ investigate  │ investigate  │ investigate  │ evidence;    │
│             │ (strong data)│ (fair data)  │ (weak data)  │ wait for more│
│             │              │              │              │              │
├─────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ LOW TRUST   │ ❌ BLOCK     │ ❌ BLOCK     │ ❌ BLOCK     │ ❌ BLOCK     │
│ (40-60)     │ Concerning,  │ Concerning,  │ Concerning,  │ Concerning,  │
│             │ serious data │ fair data    │ weak data    │ no data      │
│             │ → escalate   │ → escalate   │ → escalate   │ → escalate   │
│             │              │              │              │              │
├─────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ CRITICAL    │ ❌ BLOCK     │ ❌ BLOCK     │ ❌ BLOCK     │ ❌ BLOCK     │
│ DISTRUST    │ Immediate    │ High priority│ Concerning   │ Cannot       │
│ (<40)       │ escalation   │ escalation   │ but data     │ evaluate;    │
│             │ (strong data)│ (good data)  │ limited      │ must wait    │
│             │              │              │              │              │
└─────────────┴──────────────┴──────────────┴──────────────┴──────────────┘
```

**Decision Rules:**

```
If TRUST ≥ 75 AND CONFIDENCE ≥ 70:
  → Confidently ALLOW (strong data supports good behavior)

If TRUST ≥ 75 AND CONFIDENCE < 70:
  → Cautiously ALLOW + MONITOR (looks good but limited data)

If 60 ≤ TRUST < 75:
  → REVIEW (regardless of confidence)
  → Request additional information
  → Make decision on case-by-case basis

If TRUST < 60 AND CONFIDENCE ≥ 70:
  → BLOCK (strong data confirms concern)
  → Investigate root cause
  → Consider escalation

If TRUST < 60 AND CONFIDENCE < 70:
  → BLOCK or REQUEST MORE DATA (insufficient evidence to decide)
  → Get more information before relying on assessment
```

---

## Limitations and Known Gaps

### Limitations of Confidence Model

1. **Assumes Independence of Components**
   - In reality, data coverage and metric availability are correlated
   - If a participant provides comprehensive data, they likely provide all metrics
   - Model doesn't capture these interdependencies

2. **Weight Selection Not Data-Driven**
   - Weights (0.30, 0.25, 0.20, 0.15, 0.10) are domain-expert estimates
   - Not calibrated against real deployment outcomes
   - Should be revisited after 6-12 months of real data

3. **Time Window Not Adaptive**
   - Evidence Freshness uses fixed decay curves
   - Different domains might need different freshness standards
   - 30-day window optimized for healthcare; might not suit all domains

4. **Statistical Stability Only Measures Recent History**
   - Doesn't capture long-term trends
   - Doesn't detect slow degradation (only erratic variance)
   - See Example 3 above: degradation from 85→32 flagged as low stability,
     but root cause (systematic decline) not explicitly identified

5. **No Evaluation of Metric Quality**
   - "Metric available" ≠ "metric is good quality"
   - System only checks presence, not validity or accuracy
   - A metric could be consistently wrong but still boost confidence

6. **Assumes Continuous Assessment**
   - Confidence model assumes regular submissions
   - Long gaps in submissions (e.g., 6-month hiatus) not explicitly handled
   - Historical Coverage captures time since first update, not submission frequency

7. **Missing Dimension: Source Trustworthiness**
   - Doesn't evaluate trustworthiness of data source
   - If a participant lies about their data, our confidence metrics won't catch it
   - Example: "Yes, we validated this" (actually they didn't)
   - Mitigation: Requires external audit of participant processes

### What Confidence Model Does NOT Measure

❌ Participant honesty (can't detect intentional false data)  
❌ Long-term trends (only recent variance)  
❌ Quality of individual metrics (only their presence)  
❌ Adversarial robustness (against participants gaming the system)  
❌ Accuracy of the Trust Score itself (circular: can't measure confidence in confidence)  

### When Confidence Model Fails

```
Failure Mode 1: Garbage In, Garbage Out
  Participant submits garbage data regularly (all metrics present, recent, stable)
  → Confidence = HIGH (checks all boxes)
  → But Trust Score is based on bad data
  → Both scores are high but misleading
  
  Mitigation: External validation required. This system measures evidence
  quality, not evidence truthfulness. Regular spot-checks of source data
  (by humans) are essential.

---

Failure Mode 2: Participant Suddenly Stops Reporting
  Hospital has submitted for 12 months, then goes silent
  → Historical Coverage = 100 (established relationship)
  → Evidence Freshness = 0 (no recent data)
  → Confidence drops appropriately
  
  But what happened? Did they:
  - Go out of business?
  - Pause operations?
  - Experience technical failure?
  - Deliberately withdraw?
  
  System can't answer. Recommendation: Manual follow-up with participant.

---

Failure Mode 3: Calibration Decay
  Thresholds optimized for 2026 data patterns
  In 2027, participant population has shifted
  → Weights are no longer optimal
  → Confidence remains high but Trust becomes misaligned
  
  Mitigation: Recalibrate weights annually or after major distribution shift.
  Monitor Trust-vs-Confidence divergence as canary for needed recalibration.
```

---

## Advanced Topics

### Confidence Intervals (Optional)

For more rigorous statistical treatment, can calculate confidence intervals:

```
Assume each component has measurement uncertainty:

DCS_CI = DCS ± σ_dcs × z_α/2
HCS_CI = HCS ± σ_hcs × z_α/2
MAS_CI = MAS ± σ_mas × z_α/2
EFS_CI = EFS ± σ_efs × z_α/2
SSS_CI = SSS ± σ_sss × z_α/2

Where:
- σ_i is the estimated standard deviation of component i
- z_α/2 is the critical value for desired confidence level (1.96 for 95%)

Then propagate to composite:

CONFIDENCE_CI_lower = 0.30×DCS_lower + 0.25×HCS_lower + ...
CONFIDENCE_CI_upper = 0.30×DCS_upper + 0.25×HCS_upper + ...

Example:
  CONFIDENCE = 78.5 ± 4.2  (95% CI: [74.3, 82.7])
  
  Interpretation: We're 95% confident the true confidence is between 74.3 and 82.7.
```

This adds rigor but increases complexity. Recommended for research/advanced use only.

### Domain-Specific Customization

Different domains might require different weights:

```
Healthcare (Conservative):
  DCS: 30% → 35%  (data quality critical)
  HCS: 25% → 25%
  MAS: 20% → 20%
  EFS: 15% → 15%
  SSS: 10% → 5%   (stability less critical than absolute quality)

Enterprise (Balanced):
  DCS: 30%, HCS: 25%, MAS: 20%, EFS: 15%, SSS: 10%  [default]

Research (Permissive):
  DCS: 25% → 20%
  HCS: 25% → 30%  (long-term research history valued)
  MAS: 20% → 20%
  EFS: 15% → 10%  (older data still useful)
  SSS: 10% → 20%  (consistency/reproducibility valued)

Federated Learning (Special):
  DCS: 30% → 40%  (data distribution critical)
  HCS: 25% → 20%
  MAS: 20% → 20%
  EFS: 15% → 10%
  SSS: 10% → 10%
```

Each domain can customize weights based on their risk tolerance and data access patterns.

---

## Edge Cases and Handling

```
Edge Case 1: No measurements ever submitted
  DCS = 0, HCS = 0, MAS = 0, EFS = 0, SSS = 0
  CONFIDENCE = 0
  Classification: INSUFFICIENT_EVIDENCE
  Decision: Cannot score participant without any data

---

Edge Case 2: Perfect participant (all scores 100)
  DCS = 100, HCS = 100, MAS = 100, EFS = 100, SSS = 100
  CONFIDENCE = 100
  Interpretation: Ideal scenario (rare, unless carefully staged tests)
  Real world: Some imperfection is expected; 100 might indicate fabricated data

---

Edge Case 3: Only missing data (no measurements available)
  All metric_presence values = false
  MAS = 0
  But if other components high, overall CONFIDENCE still weighted
  Example: HCS=100 (established), but MAS=0 (no metrics provided)
  CONFIDENCE = 0.30×0 + 0.25×100 + 0.20×0 + ... = 25
  Classification: LOW / INSUFFICIENT_EVIDENCE
  Interpretation: Long-standing relationship but no recent data to assess

---

Edge Case 4: Timestamp precision loss
  Metric timestamp only has date, not time
  Treated as 00:00:00 of that day
  Could age by up to 24 hours
  Mitigation: Request timestamps with time component
  Fallback: Assume worst case (interpret date-only as end-of-day)

---

Edge Case 5: Participant clock skew
  Submitted timestamp in future (system clock incorrect)
  Age_Hours becomes negative
  EFS = 0 (invalid)
  Mitigation: Validate timestamps before calculation
  Flag submissions with future timestamps as data quality issue
```

---

## Monitoring and Recalibration

### Recommended Monitoring Metrics

Track over time:

1. **Average Confidence by Participant**
   - Watch for participants whose confidence is consistently low
   - Watch for sudden confidence drops (might indicate data issues)

2. **Confidence vs. Trust Correlation**
   - High confidence should correlate with outcome quality
   - If high confidence + low trust consistently leads to problems,
     recalibrate weights

3. **False Positive/Negative Rates by Confidence Band**
   - At 90%+ confidence, how often is Trust Score "wrong"?
   - If high confidence correlates with errors, increase component weights

4. **Recalibration Schedule**
   - Annual weight revalidation
   - Quarterly calibration checks
   - Immediate recalibration if significant environment shift

### Audit Trail for Confidence

Log for every assessment:

```json
{
  "decision_id": "...",
  "timestamp": "2026-08-17T10:00:00Z",
  
  "confidence_components": {
    "data_coverage_score": 94.0,
    "historical_coverage_score": 100.0,
    "metric_availability_score": 100.0,
    "evidence_freshness_score": 100.0,
    "statistical_stability_score": 94.5
  },
  
  "confidence_calculation": {
    "raw": 97.65,
    "clamped": 97.65,
    "classification": "HIGH"
  },
  
  "confidence_interpretation": {
    "data_coverage_comment": "All expected measurements present",
    "historical_coverage_comment": "12 months of established relationship",
    "metric_availability_comment": "All 16 metric categories available",
    "evidence_freshness_comment": "Submitted today",
    "statistical_stability_comment": "Highly consistent scores over time"
  },
  
  "overall_assessment": "Strong evidence supports high confidence in Trust Score"
}
```

---

## Summary: Five Components → One Score

| Component | Question | Formula | Weight | Range |
|-----------|----------|---------|--------|-------|
| **Data Coverage** | How many measurements? | ratio × 100 | 30% | [0,100] |
| **Historical Coverage** | How long observed? | time ratio × 100 | 25% | [0,100] |
| **Metric Availability** | What metrics present? | ratio × 100 | 20% | [0,100] |
| **Evidence Freshness** | How recent? | decay function | 15% | [0,100] |
| **Statistical Stability** | How consistent? | variation ratio | 10% | [0,100] |
| **CONFIDENCE** | **Overall evidence quality** | **Weighted sum** | **100%** | **[0,100]** |

**Classification:**
- HIGH (90-100): Trust assessment is reliable
- MEDIUM (70-90): Trust assessment is informative but use with caution
- LOW (40-70): Trust assessment is tentative, requires validation
- INSUFFICIENT_EVIDENCE (0-40): Cannot confidently assess, need more data

---

## Conclusion: Confidence Complements Trust

**Trust Score** (0-100): Based on five evidence dimensions (DQS, DHS, USS, RS, PS)
- Answers: "How operationally healthy is this participant?"
- Used for: Approval/rejection/monitoring decisions

**Confidence Score** (0-100): Based on five quality-of-evidence dimensions (DCS, HCS, MAS, EFS, SSS)
- Answers: "How much can we rely on this Trust assessment?"
- Used for: Risk adjustment, escalation, monitoring intensity

**Together they answer:** "How healthy is this participant, and how much should we trust our assessment?"

A Trust Score without Confidence is like a medical diagnosis without understanding the reliability of the test. Together, they enable governance that is both evidence-based and evidence-aware.

---

**Document Status:** Complete specification of Confidence Model with formulas, examples, classifications, and limitations.

**Next Steps:**
1. Implement Confidence Model per this specification
2. Integrate with Trust Score in decision logic
3. Create decision matrices based on Trust × Confidence combinations
4. Monitor Confidence scores in production
5. Recalibrate weights after 3-6 months of real data
