# Trust Model: Defining Evidence-Based Operational Trust in Federated AI

## Executive Definition

**In Protector Uttam, "Trust" means:**

> An evidence-based operational estimate of the safety and reliability of a participant's model update, based on observable signals across five dimensions, expressed as a confidence score with explicit uncertainty bounds.

**What Trust IS:**
- A quantified estimate (e.g., 0.87 ± 0.12)
- Based on multiple observable signals
- Reproducible and auditable
- Updated with new evidence
- Specific to a single update in a specific context

**What Trust IS NOT:**
- A guarantee that the participant is honest
- A probability the participant is malicious
- A universal security or compliance certificate
- Proof that the update is mathematically correct
- An assessment of intent or trustworthiness as a person/organization
- A binding commitment or contract

**The Core Insight:**

> We cannot know if a participant is inherently trustworthy. We CAN observe whether their update exhibits operational safety characteristics. Our job is to measure the latter, not claim the former.

---

## The Five Evidence Dimensions

### Dimension 1: Data Quality

**What It Answers:**
> How likely is this participant's training data to be representative, accurate, and of high quality?

**Why This Matters:**

Garbage in, garbage out. If a participant trained on corrupted, mislabeled, or severely biased data, the resulting model update will propagate those issues to the global model. Data quality is the upstream cause of many downstream failures.

**Observable Signals:**

We cannot inspect raw training data (privacy boundary), but we can infer data quality from:
- Historical track record (has this participant produced good updates before?)
- Metadata declared by participant (training set size, data collection date)
- Behavioral consistency (does this update look similar to past ones?)
- Proxy metrics (validation accuracy, validation loss on their local test set)

**Raw Data Required:**

```
For each participant:
- Historical updates (stored locally for comparison)
- Declared training metadata: {
    training_set_size,
    validation_metrics,
    timestamp_of_training,
    data_collection_period
  }
- Model statistics from update: {
    gradient_norm,
    weight_magnitudes,
    layer_wise_changes
  }
- Optional: participant self-reported data quality metrics
```

**Mathematical Calculation:**

We compute a **Data Quality Score** (DQS) combining:

1. **Historical Baseline Score** (70% weight in DQS):
```
DQS_historical = Z_normalize(mean(past_validation_metrics))
           + temporal_consistency_factor
           + update_frequency_regularization

Where:
- Z_normalize = (value - historical_mean) / historical_std
- temporal_consistency_factor = 1.0 if recent updates are stable
                              = 0.8 if degrading trend
                              = 0.5 if high volatility
- update_frequency_regularization = penalty if participant is new (less history)
```

2. **Current Metadata Score** (30% weight):
```
DQS_current = validation_accuracy_score
            + training_set_size_adequacy
            + data_freshness_score

Where:
- validation_accuracy_score = min(1.0, participant_val_acc / baseline_val_acc)
- training_set_size_adequacy = min(1.0, declared_size / expected_size)
- data_freshness_score = exp(-days_since_training / 30)  [30-day half-life]
```

3. **Final Data Quality Score:**
```
DQS = 0.7 × DQS_historical + 0.3 × DQS_current
Range: [0.0, 1.0]
Confidence: ±σ(historical_observations)
```

**Assumptions Made:**

1. **Assumption:** Validation accuracy is a proxy for training data quality
   - **Validity:** Strong for well-constructed benchmarks; weak if validation set is corrupted
   - **Mitigation:** Cross-check with other signals

2. **Assumption:** Participant's declared metadata is honest
   - **Validity:** True in most cases; could be gamed
   - **Mitigation:** Flag outliers; require attestation

3. **Assumption:** Historical performance predicts future performance
   - **Validity:** True if organizational practices are stable
   - **Validity:** Weak if participant's training environment changed significantly
   - **Mitigation:** Weight recent history more heavily; detect regime changes

4. **Assumption:** We can normalize across participants fairly
   - **Validity:** Questionable if participants have different data domains
   - **Mitigation:** Per-domain baselines; allow customization

**When This Metric Can Mislead:**

1. **New Participant** → Low score due to no history, even if data is good
   - *Mitigation:* Use domain default baseline; rapid confidence building

2. **Sudden Domain Shift** → High historical score but new data is very different
   - *Mitigation:* Detect distribution shift separately (see Dimension 2)

3. **Validation Set Contamination** → Reported high validation accuracy but data is bad
   - *Mitigation:* Cross-check with global model performance; flag consistency outliers

4. **Intentional Misreporting** → Participant reports false metadata
   - *Mitigation:* Detect via statistical inconsistencies; escalate for review

**What This Signal CAN Detect:**

✅ Participant with consistently poor historical data quality  
✅ Sudden data quality degradation trend  
✅ Training sets that are too small (underfitting risk)  
✅ Stale data (training from very old collection period)  
✅ New participants (high uncertainty, flag for review)  
✅ Anomalously high/low validation metrics (compared to baseline)  

**What This Signal CANNOT Detect:**

❌ Sophisticated adversarial label poisoning (looks good on validation set)  
❌ Systematic data labeling bias (not visible in univariate metrics)  
❌ Data leakage from external sources  
❌ Participant's local overfitting  
❌ Subtle distribution shift that doesn't affect validation accuracy  
❌ Single-instance corruption in large dataset  

**How It Contributes to Final Decision:**

- **Weight in Trust Score:** 25%
- **Decision Threshold:** DQS < 0.5 → FLAG for review
- **Confidence Adjustment:** Low historical data points → lower confidence in score
- **Interaction:** Combined with Dimension 2 (Distribution Health) to confirm data issues

---

### Dimension 2: Distribution Health / Drift

**What It Answers:**
> Is the participant's training data from a different distribution than the historical baseline? Has their data drifted significantly?

**Why This Matters:**

A participant's data distribution can shift over time (concept drift, data drift, covariate shift). When their update is trained on out-of-distribution data, it optimizes for the wrong objective, and integrating it into the global model causes performance degradation.

This is one of the most common failure modes in federated learning.

**Observable Signals:**

We detect drift via:
- Gradient properties (magnitude, direction, outlier-ness)
- Parameter update magnitude and composition
- Comparison to historical "normal" updates from same participant
- Comparison to peer updates (what do other participants look like?)

**Raw Data Required:**

```
For each update:
- Model update: Δθ (gradient or weight delta)
- Gradient norm and layer-wise norms: ||∇||_2, ||∇_layer||_2
- Gradient direction: angle between current and historical gradient
- Update composition: {
    num_parameters_changed,
    max_parameter_magnitude,
    mean_parameter_magnitude,
    num_extreme_changes (> 3σ)
  }
- Participant's historical updates (for baseline comparison)
- Peer updates from other participants (for outlier detection)
```

**Mathematical Calculation:**

We compute a **Distribution Health Score** (DHS) detecting drift via multiple tests:

1. **Gradient Norm Analysis** (40% of DHS):
```
Z_norm = (||Δθ_current|| - mean(||Δθ_historical||)) / std(||Δθ_historical||)

DHS_norm = {
    1.0               if -2 < Z_norm < 2  [within normal range]
    0.5 + 0.25*tanh(Z_norm/5)  if |Z_norm| > 2  [outlier, scaled penalty]
    0.2               if |Z_norm| > 5  [extreme outlier]
}
```

2. **Direction Shift Detection** (30% of DHS):
```
Direction_similarity = (Δθ_current · Δθ_historical) / (||Δθ_current|| × ||Δθ_historical||)
                     [cosine similarity, bounded in [-1, 1]]

DHS_direction = {
    1.0              if direction_similarity > 0.7  [consistent direction]
    0.8              if 0.4 < direction_similarity ≤ 0.7  [mild shift]
    0.5              if 0.0 < direction_similarity ≤ 0.4  [significant shift]
    0.2              if direction_similarity < 0.0  [opposite direction - strong signal of drift]
}
```

3. **Outlier Detection via Peer Comparison** (30% of DHS):
```
Compute Mahalanobis distance of current update relative to peer distribution:

D_mahal = sqrt((Δθ_current - μ_peers)^T × Σ_peers^-1 × (Δθ_current - μ_peers))

DHS_peers = {
    1.0              if D_mahal < 1.96  [within 95% confidence interval]
    0.7              if 1.96 ≤ D_mahal < 3.0  [outlier but not extreme]
    0.3              if D_mahal ≥ 3.0  [severe outlier, likely drift]
}

[If fewer than 10 peers available, use participant's historical distribution instead]
```

4. **Final Distribution Health Score:**
```
DHS = 0.4 × DHS_norm + 0.3 × DHS_direction + 0.3 × DHS_peers
Range: [0.0, 1.0]
Confidence: ±0.15 (calibrated via historical accuracy)
```

**Assumptions Made:**

1. **Assumption:** Gradient properties are indicative of data distribution
   - **Validity:** Strong for simple models; weaker for complex models where optimization landscape is non-convex
   - **Mitigation:** Supplement with other signals

2. **Assumption:** Peer distribution is representative of "normal"
   - **Validity:** True if no coordinated attacks; weak under Byzantine scenarios
   - **Mitigation:** Use robust statistics (median, IQR) instead of mean/std

3. **Assumption:** Historical gradient is baseline for drift
   - **Validity:** True if participant is stable; weak if participant's data evolves naturally
   - **Mitigation:** Use sliding window baseline; detect gradual vs. sudden shifts

4. **Assumption:** Cosine similarity captures meaningful direction alignment
   - **Validity:** True for high-dimensional spaces; can fail in very high dimensions
   - **Mitigation:** Use multiple distance metrics (Euclidean, Manhattan)

**When This Metric Can Mislead:**

1. **Legitimate Training Diversity** → Different participant uses different model architecture
   - *Cause:* Gradient norms not comparable across architectures
   - *Mitigation:* Normalize by model size; allow per-architecture baselines

2. **Learning Rate Differences** → Participant uses higher learning rate
   - *Cause:* Larger gradients even if data is identical
   - *Mitigation:* Request learning rate metadata; normalize gradients

3. **Early Training Phase** → New participant's first update looks anomalous
   - *Cause:* No historical baseline; random initialization effects
   - *Mitigation:* Use bootstrap period (first 3–5 updates flagged but not blocked)

4. **Natural Concept Drift** → Participant's data genuinely evolves
   - *Cause:* Real distribution shift gets flagged as anomaly
   - *Mitigation:* Distinguish gradual drift (acceptable) from sudden shifts (suspicious)

**What This Signal CAN Detect:**

✅ Sudden covariate shift (participant's feature distribution changed)  
✅ Concept drift (participant's labels changed)  
✅ Data corruption (manifests as extreme gradients)  
✅ Model training failure (produces empty/NaN gradients)  
✅ Participant going offline then returning (stale update has different direction)  
✅ Synchronized participant behavior (multiple participants with identical anomaly)  

**What This Signal CANNOT Detect:**

❌ Subtle, gradual drift that affects all participants equally  
❌ Label bias that doesn't change gradient magnitude  
❌ Adversarial perturbations designed to have normal-looking gradients  
❌ Poisoning that carefully mimics peer distribution  
❌ Legitimate domain specialization (if some participants serve different populations)  

**How It Contributes to Final Decision:**

- **Weight in Trust Score:** 25%
- **Decision Threshold:** DHS < 0.4 → FLAG for review
- **Confidence Adjustment:** Low peer population → lower confidence
- **Interaction:** Correlated with Dimension 1 (Data Quality); when both low → strong signal of data problems

---

### Dimension 3: Model Update Safety

**What It Answers:**
> Are the parameters in this update anomalous or extreme? Do they violate expected bounds?

**Why This Matters:**

Even if the training process was sound, the resulting update might be pathological:
- Exploding gradients or vanishing gradients
- Parameter values outside reasonable ranges
- Numerical instability (NaN, Inf values)
- Model collapse or mode-seeking behavior
- Suspicious sparsity or concentration in certain layers

This is primarily a **safety filter** to catch obvious failures, not a sophisticated anomaly detector.

**Observable Signals:**

We examine:
- Raw parameter magnitudes and distributions
- Layer-wise norms and statistics
- Comparison to historical ranges for same participant
- Comparison to peers
- Presence of NaN, Inf, or other invalid values

**Raw Data Required:**

```
For model update Δθ (or θ_new):
- Full parameter tensor (or representative sample for large models)
- Layer-wise breakdowns: {
    layer_name,
    num_parameters,
    mean,
    std,
    min,
    max,
    median,
    num_nan_values,
    num_inf_values,
    num_zero_values,
    sparsity
  }
- Overall statistics: ||Δθ||_1, ||Δθ||_2, ||Δθ||_∞
- Comparison baselines (historical ranges per participant, peer ranges)
```

**Mathematical Calculation:**

We compute a **Model Update Safety Score** (MUSS) via multiple checks:

1. **Numerical Validity Check** (15% of MUSS):
```
MUSS_validity = {
    1.0           if no NaN, Inf, or complex values
    0.5           if <0.1% invalid values (rounding errors)
    0.0           if >0.1% invalid values (model corruption)
}
```

2. **Parameter Magnitude Check** (40% of MUSS):
```
For each layer, compute Z-score of L2 norm:
Z_layer = (||Δθ_layer|| - μ_layer_historical) / σ_layer_historical

MUSS_magnitude = mean(min(1.0, exp(-Z_layer^2)))
               [gaussian penalty for outliers]

Special case: If any layer has Z > 5, MUSS_magnitude = 0.2
```

3. **Sparsity Consistency Check** (25% of MUSS):
```
Compute sparsity (fraction of zero parameters) per layer:
sparsity_layer = num_zeros / num_parameters

Flag if:
- Sparsity > 50% in layers where historically sparsity < 10%
- Sparsity changed by >20 percentage points from historical

MUSS_sparsity = {
    1.0            if sparsity consistent with history
    0.7            if mild sparsity change
    0.3            if significant sparsity change
    0.1            if extreme sparsity (>90% zeros)
}
```

4. **Outlier Comparison vs. Peers** (20% of MUSS):
```
D_l2_peer = (||Δθ|| - median_peers_||Δθ||) / IQR_peers_||Δθ||

MUSS_peers = {
    1.0            if -2 < D_l2_peer < 2  [within peer range]
    0.6            if 2 ≤ |D_l2_peer| < 3  [outlier but tolerable]
    0.2            if |D_l2_peer| ≥ 3  [severe outlier]
}
```

5. **Final Model Update Safety Score:**
```
MUSS = 0.15×MUSS_validity + 0.4×MUSS_magnitude + 0.25×MUSS_sparsity + 0.2×MUSS_peers
Range: [0.0, 1.0]
Confidence: ±0.10 (high confidence due to deterministic checks)
```

**Assumptions Made:**

1. **Assumption:** Parameter magnitudes indicate healthy training
   - **Validity:** Generally true; extreme values usually indicate problems
   - **Mitigation:** Account for different model architectures

2. **Assumption:** Peer comparison is fair
   - **Validity:** True if peers use same model architecture
   - **Validity:** Weak if peer set is heterogeneous
   - **Mitigation:** Use architecture-specific baselines

3. **Assumption:** Historical ranges are appropriate
   - **Validity:** True for stable participants; weak for evolving systems
   - **Mitigation:** Use rolling window (last 20 updates) not all-time

4. **Assumption:** Sparsity changes are undesirable
   - **Validity:** Context-dependent; fine for networks with learned sparsity
   - **Mitigation:** Allow per-participant sparsity policies

**When This Metric Can Mislead:**

1. **Different Model Architecture** → Participant uses layer-wise normalization
   - *Cause:* Parameter magnitudes not comparable
   - *Mitigation:* Normalize by model size; allow architecture flexibility

2. **Legitimate Training Dynamics** → Learning rate annealing → smaller gradients
   - *Cause:* Historical average includes high-learning-rate phase
   - *Mitigation:* Use recent history (last 10 updates) as baseline

3. **Floating-Point Precision** → Rounding errors create NaN in large models
   - *Cause:* Numerical instability, not model corruption
   - *Mitigation:* Allow <0.01% invalid values as acceptable

4. **Pruning or Compression** → Participant intentionally zeros out parameters
   - *Cause:* Legitimate sparsification gets flagged as anomaly
   - *Mitigation:* Allow per-participant compression policies

**What This Signal CAN Detect:**

✅ Exploding or vanishing gradients  
✅ Training divergence (model collapse)  
✅ Numerical instability (NaN/Inf propagation)  
✅ Severe overfitting (extreme weight magnitude)  
✅ Mode-seeking behavior (weight concentration)  
✅ Model corruption or transmission errors  
✅ Unintended model architecture changes  

**What This Signal CANNOT Detect:**

❌ Subtle parameter changes that stay within normal ranges  
❌ Adversarial perturbations designed to have normal magnitude  
❌ Poisoning that subtly shifts decision boundaries  
❌ Training on out-of-distribution data (if output looks normal)  
❌ Mislabeled data (if training converges normally)  

**How It Contributes to Final Decision:**

- **Weight in Trust Score:** 20%
- **Decision Threshold:** MUSS < 0.3 → BLOCK immediately (safety critical)
- **Confidence Adjustment:** Always high confidence (mostly deterministic checks)
- **Interaction:** Orthogonal to other dimensions; catches obvious failures early

---

### Dimension 4: Operational Reliability

**What It Answers:**
> What is the historical track record of this participant? How reliable have their past updates been in practice?

**Why This Matters:**

The best predictor of future behavior is past behavior. If a participant has consistently produced good updates, they're more likely to continue. If they have a history of causing problems, that's a strong signal.

This dimension aggregates long-term behavioral evidence.

**Observable Signals:**

We track:
- Historical acceptance rate (how many updates were accepted vs. flagged?)
- Impact on global model performance (did their updates help or hurt?)
- Frequency and pattern of rejections
- Correlation between our flags and actual problems
- Consistency of behavior over time

**Raw Data Required:**

```
For each participant (historical tracking):
- Acceptance history: [update_id, timestamp, accepted/flagged/blocked, reason]
- Impact metrics: {
    update_id,
    global_model_accuracy_before,
    global_model_accuracy_after_aggregation,
    validation_on_test_set,
    inference_latency_impact
  }
- Flagging history: [update_id, timestamp, flags_raised, actual_issue_found]
- Reliability metrics: {
    total_updates_sent,
    accepted_count,
    flagged_count,
    blocked_count,
    false_positive_rate,
    mean_performance_impact
  }
```

**Mathematical Calculation:**

We compute an **Operational Reliability Score** (ORS) based on historical record:

1. **Acceptance Rate** (35% of ORS):
```
acceptance_rate = accepted_updates / total_updates

ORS_acceptance = {
    1.0                      if acceptance_rate > 95%
    0.8                      if 85% ≤ acceptance_rate ≤ 95%
    0.5                      if 70% ≤ acceptance_rate < 85%
    0.3 × acceptance_rate    if acceptance_rate < 70%
}
```

2. **Performance Impact** (35% of ORS):
```
For each update, compute delta:
Δ_accuracy = accuracy_after - accuracy_before

performance_impact = mean(Δ_accuracy)

ORS_performance = {
    1.0                 if mean(Δ_accuracy) > +0.5%
    0.9                 if -0.5% < mean(Δ_accuracy) ≤ 0.5%  [neutral]
    0.6                 if -2% ≤ mean(Δ_accuracy) < -0.5%  [slight degradation]
    0.2                 if mean(Δ_accuracy) < -2%  [significant degradation]
}
```

3. **Flag Accuracy** (20% of ORS):
```
When we flag an update, how often is it actually problematic?

flag_accuracy = (flags_raised_where_problems_found) / (total_flags_raised)

ORS_flag_accuracy = min(1.0, flag_accuracy * 1.25)
                  [reward for accurate flagging; scale up to 1.0]

If no historical flags, use neutral value 0.9
```

4. **Consistency Over Time** (10% of ORS):
```
Compute trend in reliability over last N updates (N=20):

trend = (mean_reliability_last_10 - mean_reliability_10_before) / mean_reliability_10_before

ORS_consistency = {
    1.0 + 0.1 × trend    if improving trend  [reward improvement]
    1.0 - 0.2 × |trend|  if declining trend  [penalty decline]
}
[clipped to [0.0, 1.0]]
```

5. **Final Operational Reliability Score:**
```
ORS = 0.35×ORS_acceptance + 0.35×ORS_performance + 0.20×ORS_flag_accuracy + 0.10×ORS_consistency

Range: [0.0, 1.0]
Confidence: ±0.15  [lower confidence early, increases with history]

Confidence_multiplier = min(1.0, total_updates_sent / 30)
[less than 30 updates = lower confidence]
```

**Assumptions Made:**

1. **Assumption:** Historical acceptance rate predicts future reliability
   - **Validity:** True if participant's practices are stable
   - **Validity:** Weak if participant recently changed training procedures
   - **Mitigation:** Weight recent history more heavily

2. **Assumption:** Performance impact is attributable to participant
   - **Validity:** Weak in federated settings where multiple updates interact
   - **Validity:** Stronger in small cohorts or with ablation studies
   - **Mitigation:** Account for confounding (other participant updates aggregated same iteration)

3. **Assumption:** Our flags correlate with actual problems
   - **Validity:** True if detection methods are well-calibrated
   - **Validity:** Weak if flag threshold is poorly tuned
   - **Mitigation:** Continuously calibrate threshold against real outcomes

4. **Assumption:** Track record predicts future (organizational stability)
   - **Validity:** Generally true; weak if participant's environment changed
   - **Mitigation:** Detect regime changes; reset history on major changes

**When This Metric Can Mislead:**

1. **New Participant** → No history, so low reliability score
   - *Cause:* Unfair comparison to established participants
   - *Mitigation:* Bootstrap with default score; confidence grows with each update

2. **Environmental Change** → Participant got new hardware, changed data source
   - *Cause:* Historical performance no longer predictive
   - *Mitigation:* Detect sudden behavior change; reset history partially

3. **Confounding** → Performance degradation caused by other participant, not this one
   - *Cause:* Attribute success/failure incorrectly
   - *Mitigation:* Use per-participant ablation; separate signal from noise

4. **Aggregate Mask** → Participant sends good updates masked by other bad ones
   - *Cause:* Individual reliability hidden in aggregate metrics
   - *Mitigation:* Track per-update impact separately (but hard in federated setting)

**What This Signal CAN Detect:**

✅ Consistently problematic participants  
✅ Recent degradation in participant's reliability  
✅ Participants with improving track record  
✅ One-off anomalies vs. systematic issues  
✅ Timing of problems (early in deployment vs. recent)  

**What This Signal CANNOT DETECT:**

❌ First incident from new participant (no history to detect)  
❌ Sudden one-time failure (may get hidden in average)  
❌ Issues caused by external environment changes  
❌ Problems unrelated to participant's update (coordination failures)  

**How It Contributes to Final Decision:**

- **Weight in Trust Score:** 20%
- **Decision Threshold:** ORS < 0.4 → Monitor closely or block
- **Confidence Adjustment:** New participants (< 10 updates) get low confidence
- **Interaction:** Combined with Dimensions 1–3 to contextualize current update against history

---

### Dimension 5: Model Performance Health

**What It Answers:**
> After aggregating this participant's update, does the global model's performance remain healthy? Do we see any degradation signals?

**Why This Matters:**

This is the ultimate signal: **Does the update make the global model better, worse, or neutral?**

However, this is also the noisiest signal because performance depends on:
- Test set quality and representativeness
- Other participants' updates
- Non-stationary test distributions
- Evaluation metrics

Therefore, it's weighted lower and used primarily as a **validation signal** for other dimensions.

**Observable Signals:**

We track:
- Global model accuracy on validation set (before and after aggregation)
- Accuracy on different data slices/demographics (if available)
- Inference latency and other performance characteristics
- Generalization gap (train vs. validation accuracy)
- Calibration of confidence scores

**Raw Data Required:**

```
For each aggregation round:
- Update ID and participant
- Global model metrics before aggregation: {
    validation_accuracy,
    validation_loss,
    test_set_accuracy,
    inference_latency_p50,
    inference_latency_p99,
    memory_usage
  }
- Global model metrics after aggregation (with this update): {
    same as above
  }
- Per-slice metrics (if available): {
    slice_id,
    accuracy_before,
    accuracy_after,
    delta_accuracy
  }
- Baseline/null model metrics (for comparison)
```

**Mathematical Calculation:**

We compute a **Model Performance Health Score** (MPHS) measuring impact:

1. **Aggregate Performance Change** (50% of MPHS):
```
Δ_accuracy = accuracy_after - accuracy_before

MPHS_accuracy = {
    1.0              if Δ_accuracy > +0.2%  [improvement]
    0.9              if +0.05% ≤ Δ_accuracy ≤ +0.2%  [mild improvement]
    0.8              if -0.05% < Δ_accuracy < +0.05%  [neutral/noise]
    0.5              if -0.5% ≤ Δ_accuracy ≤ -0.05%  [slight degradation]
    0.2              if Δ_accuracy < -0.5%  [significant degradation]
}
```

2. **Consistency Across Slices** (30% of MPHS):
```
If per-slice metrics available, compute variance:

slice_accuracy_deltas = [Δ_accuracy_slice_i for each slice]
consistency_score = -std(slice_accuracy_deltas)  [negative because high variance is bad]

MPHS_consistency = {
    1.0              if std < 0.1%  [consistent across slices]
    0.8              if 0.1% ≤ std < 0.5%  [mostly consistent]
    0.5              if 0.5% ≤ std < 1.0%  [variable across slices - fairness concern]
    0.2              if std > 1.0%  [highly inconsistent - possible bias introduced]
}

If per-slice metrics unavailable, use neutral 0.9
```

3. **Generalization Gap Change** (20% of MPHS):
```
gen_gap_before = train_accuracy_before - val_accuracy_before
gen_gap_after = train_accuracy_after - val_accuracy_after
Δ_gen_gap = gen_gap_after - gen_gap_before

MPHS_generalization = {
    1.0              if Δ_gen_gap < +0.1%  [generalization improves or stable]
    0.7              if +0.1% ≤ Δ_gen_gap < +0.5%  [mild overfitting increase]
    0.4              if +0.5% ≤ Δ_gen_gap < +1.0%  [moderate overfitting increase]
    0.1              if Δ_gen_gap ≥ +1.0%  [severe overfitting]
}
```

4. **Final Model Performance Health Score:**
```
MPHS = 0.5×MPHS_accuracy + 0.3×MPHS_consistency + 0.2×MPHS_generalization

Range: [0.0, 1.0]
Confidence: ±0.20  [high uncertainty due to noise and confounding]
```

**Assumptions Made:**

1. **Assumption:** Performance change is attributable to participant's update
   - **Validity:** Weak; multiple updates aggregate simultaneously
   - **Mitigation:** Use ablation or analyze update in isolation if flagged

2. **Assumption:** Test set is representative and uncontaminated
   - **Validity:** True if test set is static and offline
   - **Validity:** Weak if test set is online/adaptive (participant may have seen it)
   - **Mitigation:** Request test set metadata; flag if suspiciously high accuracy

3. **Assumption:** Small performance changes are noise
   - **Validity:** True for confidence threshold of ±0.5%
   - **Validity:** Weak for critical systems where 0.1% accuracy = lives
   - **Mitigation:** Adjust thresholds by domain; healthcare stricter than retail

4. **Assumption:** Performance metrics reflect true capability
   - **Validity:** Weak if participant is gaming the metric
   - **Validity:** True if metric selection is adversarially resistant
   - **Mitigation:** Use multiple metrics; avoid single-metric systems

**When This Metric Can Mislead:**

1. **Measurement Noise** → Random test set fluctuations create false signals
   - *Cause:* Small test set or non-representative samples
   - *Mitigation:* Use larger test sets; multiple evaluation runs

2. **Confounding** → Other participants' good updates mask this one's harm
   - *Cause:* Federated aggregation combines multiple updates
   - *Mitigation:* Isolate update impact via ablation (expensive)

3. **Test Set Shift** → Distribution drift in test set, unrelated to update quality
   - *Cause:* Real-world distribution changes over time
   - *Mitigation:* Detect test set shift separately; adjust thresholds

4. **Metric Gaming** → Participant optimizes for test set metric, not real performance
   - *Cause:* Proxy metric misalignment
   - *Mitigation:* Use multiple metrics; holdout evaluation

**What This Signal CAN Detect:**

✅ Updates that immediately degrade accuracy  
✅ Accumulation of degradation over time  
✅ Fairness issues (different accuracy across demographics)  
✅ Overfitting increases  
✅ Consistency problems (helps/hurts different populations differently)  

**What This Signal CANNOT DETECT:**

❌ Subtle degradation masked by noise  
❌ Long-term drift (takes many updates to accumulate)  
❌ Issues that don't affect accuracy (e.g., latency, memory)  
❌ Correct predictions for wrong reasons (Goodhart's law)  
❌ Distribution shift in evaluation vs. production  

**How It Contributes to Final Decision:**

- **Weight in Trust Score:** 10%
- **Decision Threshold:** MPHS < 0.4 → Downweight this update or monitor
- **Confidence Adjustment:** Highest uncertainty; considered secondary signal
- **Interaction:** Used to validate or challenge other dimensions; if MPHS disagrees with Dimensions 1–4, investigate

---

## Complete Evidence-Based Trust Scoring Framework

### The Trust Score Formula

```
TRUST_SCORE = w₁ × DQS + w₂ × DHS + w₃ × MUSS + w₄ × ORS + w₅ × MPHS

Where:
- DQS = Data Quality Score
- DHS = Distribution Health Score
- MUSS = Model Update Safety Score
- ORS = Operational Reliability Score
- MPHS = Model Performance Health Score

Weights (configurable):
- w₁ = 0.25 (Data Quality)
- w₂ = 0.25 (Distribution Health)
- w₃ = 0.20 (Model Update Safety)
- w₄ = 0.20 (Operational Reliability)
- w₅ = 0.10 (Model Performance Health)

Total: 1.0
```

### Confidence Interval

```
Each dimension has its own confidence σᵢ.

Overall confidence:
σ_total = sqrt(Σᵢ (wᵢ × σᵢ)²)

TRUST_SCORE = [TRUST_SCORE_mean ± σ_total] with 95% confidence
```

### Decision Thresholds

```
TRUST_SCORE → Decision

≥ 0.75        ALLOW (high confidence)
0.60 – 0.74   MONITOR (good but watch)
0.40 – 0.59   REVIEW (uncertain, needs human)
< 0.40        BLOCK (low confidence)

Adjustable per domain:
- Healthcare: Threshold higher (more conservative)
- Enterprise: Threshold balanced
- Research: Threshold lower (more permissive)
```

---

## Evidence Signals Reference Table

| **Dimension** | **Signal Measured** | **Question Answered** | **Raw Evidence Required** | **Calculation Method** | **Why Used** | **Failure Modes** | **Limitations** |
|---|---|---|---|---|---|---|---|
| **Data Quality** | Historical validation metrics, training metadata | Is participant's training data representative and accurate? | Validation accuracy, training set size, collection timestamp | Z-normalize historical mean + temporal consistency factor | Early indicator of data problems | New participants lack history; validation set contamination hides issues | Cannot inspect raw labels; misses subtle bias |
| **Distribution Health / Drift** | Gradient norm, direction, peer outlier score | Has participant's data distribution shifted? | Model gradients, historical gradients, peer gradients | Mahalanobis distance + cosine similarity + Z-score normalization | Detects covariate/concept drift | Different architectures not comparable; learning rate sensitivity | Subtle drift undetected; adversarial evasion possible |
| **Model Update Safety** | Parameter magnitudes, sparsity, validity | Are update parameters anomalous or extreme? | Parameter tensors, layer-wise stats, min/max/NaN counts | L2 norm Z-score + sparsity consistency check + peer comparison | Catches obvious numerical failures | Different architectures have different norms; legitimate pruning flagged | Cannot detect subtle parameter-level poisoning |
| **Operational Reliability** | Historical acceptance rate, performance impact | What is participant's track record? | Acceptance history, global model performance before/after | Mean acceptance rate + performance delta tracking + flag accuracy | Long-term behavioral pattern | Confounding from multiple updates; environment changes mask signal | One-off failures hidden in aggregate; new participants unfairly disadvantaged |
| **Model Performance Health** | Global model accuracy change, per-slice consistency | Does update degrade global model? | Validation accuracy before/after, per-slice accuracy, generalization gap | Aggregate accuracy delta + per-slice variance + gen gap change | Ultimate validation signal | Noise masks small changes; confounding from other updates | High uncertainty; reactive not proactive; metric gaming possible |

---

## What "Trust" Means in Protector Uttam: Summary

| Aspect | Definition | Example |
|--------|-----------|---------|
| **What Trust Is** | Evidence-based operational estimate (0.0–1.0 range) | "This update has trust=0.82±0.11 (95% confidence)" |
| **What Trust Measures** | Safety of aggregating this update into global model | "Update is statistically normal, from reliable participant, safe to use" |
| **What Trust Does NOT Measure** | Inherent trustworthiness of participant or organization | NOT: "Hospital is trustworthy" or "CEO is honest" |
| **How It's Calculated** | Weighted combination of five observable dimensions | DQS + DHS + MUSS + ORS + MPHS with configurable weights |
| **How It's Used** | Decision threshold for ALLOW/MONITOR/REVIEW/BLOCK | Trust ≥ 0.75 → ALLOW; 0.40–0.59 → REVIEW; < 0.40 → BLOCK |
| **How It Changes** | Updated with new evidence; responsive to participant behavior | Good track record increases ORS; poor update lowers DQS next time |
| **How It Fails** | Multiple ways; explicitly documented per dimension | See "Failure Modes" and "Limitations" in each section above |
| **What Replaces It** | Human judgment and organizational policy | If humans override, log rationale; update assumptions |

---

## Implications for Implementation

### What This Model Enables

1. ✅ **Reproducible Decisions** — Different analysts reach same conclusion from same evidence
2. ✅ **Auditable Governance** — Regulators can see why each decision was made
3. ✅ **Configurable Risk** — Organizations tune thresholds to their tolerance
4. ✅ **Transparency** — No black-box; each signal is explainable
5. ✅ **Continuous Learning** — System improves as it gathers evidence

### What This Model Requires

1. ⚠️ **Complete Metadata** — All five dimensions need data to compute scores
2. ⚠️ **Baseline Establishment** — Need 10–20 historical updates per participant
3. ⚠️ **Threshold Tuning** — No universal thresholds; must customize per domain
4. ⚠️ **Honest Labeling** — When we're wrong, update our assumptions
5. ⚠️ **Human Oversight** — System informs; humans decide policy

### What This Model Cannot Do

❌ Guarantee all poisoning will be detected  
❌ Prove participant is fundamentally trustworthy  
❌ Work without any historical data (new participants start uncertain)  
❌ Replace domain expertise and regulatory requirements  
❌ Provide liability protection or legal guarantees  

---

## Next Steps

This Trust Model is the foundation for:
1. **System Design** — Architecture built to compute these dimensions efficiently
2. **Implementation** — Code that calculates scores and applies thresholds
3. **Validation** — Testing against synthetic poisoning and real federated learning datasets
4. **Calibration** — Tuning thresholds and weights with early customers
5. **Monitoring** — Tracking accuracy of predictions over time

**Status:** Definition complete. Ready for technical architecture and implementation.
