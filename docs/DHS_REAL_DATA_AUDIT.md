# DHS Real-Data Audit

## Executive conclusion

The repeated result `DHS = 20.00` is not caused by the drift scorer formula being broken in a random way. It is caused by a baseline construction pattern that makes the baseline extremely small and unrepresentative for each participant.

Classification: `C. Baseline construction issue`

The exact runtime evidence from the repository’s example command shows that each participant is evaluated against a baseline with only 3 rows, constructed from one sample per class, while the current participant contains 8 rows. This produces extremely large PSI values, and the scorer’s threshold logic floors every severe-drift case at exactly 20.0.

---

## Exact execution path

The live example command was:

```bash
python run_real_data.py --csv tests/fixtures/participant_component_fixture.csv --target label --participants 3 --seed 42
```

The relevant path is:

1. CSV file is loaded by `src.dataset_loader.load_csv`
2. The dataset is split into participant datasets by `src.participant_simulator.simulate_participants`
3. The runner in `run_real_data.py` builds a participant-specific baseline with `_deterministic_baseline_indices`
4. The baseline and current participant arrays are passed into `DriftHealthInput`
5. `DriftHealthScorer.score(...)` computes PSI for each feature
6. The mean PSI is mapped by `_psi_to_score(...)`
7. Final `DHS` is returned

---

## The baseline construction used in the example run

In `run_real_data.py`, the baseline for each participant is built as:

- shuffle participant rows
- for each class label in the current participant, take the first sample from that class
- keep one sample per class only

For this fixture, there are exactly 3 classes (`1`, `2`, `3`), so the baseline size is always:

- `baseline_rows = 3`

This is a direct runtime fact from the example execution, not a guess.

---

## Participant-by-participant runtime evidence

### Participant ORG-001

1. Number of baseline rows: `3`
2. Number of participant rows: `8`
3. Feature count: `4`
4. Baseline feature statistics:
   - feature_0: mean=`2066.67`, std=`821.92`, min=`1000.0`, max=`3000.0`
   - feature_1: mean=`2183.33`, std=`777.10`, min=`1200.0`, max=`3100.0`
   - feature_2: mean=`2010.00`, std=`845.50`, min=`900.0`, max=`2950.0`
   - feature_3: mean=`2150.00`, std=`803.12`, min=`1100.0`, max=`3050.0`
5. Current participant feature statistics:
   - feature_0: mean=`2114.38`, std=`799.43`, min=`1000.0`, max=`3010.0`
   - feature_1: mean=`2228.13`, std=`782.66`, min=`1180.0`, max=`3120.0`
   - feature_2: mean=`2077.50`, std=`822.85`, min=`900.0`, max=`2985.0`
   - feature_3: mean=`2192.50`, std=`797.43`, min=`1080.0`, max=`3070.0`
6. Exact drift metrics calculated:
   - `psi_per_feature = [2.80848235, 2.80848235, 2.80848235, 2.80848235]`
   - `psi_average = 2.8084823474851546`
   - `drift_count = 4`
   - `features_with_drift = [0, 1, 2, 3]`
   - `drift_level = "severe"`
7. Intermediate normalized values:
   - This comes from histogram-based proportions inside `DriftHealthScorer._calculate_psi_feature`
   - The formula is:

   `PSI = sum((current_prop - baseline_prop) * log(current_prop / baseline_prop))`

   with:

   `baseline_prop = (baseline_hist + epsilon) / (sum(baseline_hist) + epsilon * num_bins)`
   `current_prop = (current_hist + epsilon) / (sum(current_hist) + epsilon * num_bins)`

   Because the baseline is only 3 rows, the baseline histogram is extremely sparse. This makes `baseline_prop` values tiny or zero and creates large log-ratio terms.
8. Clipping / thresholds:
   - `epsilon = 1e-10`
   - `num_bins = 10`
   - `drift_threshold = 0.25` for drifted feature detection
   - `_psi_to_score` applies:
     - `psi < 0.10 -> 100.0`
     - `0.10 <= psi < 0.25 -> interpolated between 100 and 80`
     - `0.25 <= psi < 0.50 -> interpolated between 80 and 60`
     - `psi >= 0.50 -> max(20.0, 20.0 - (psi - 0.50) * 5.0)`
9. Final raw drift value:
   - `psi_average = 2.8084823474851546`
10. Final DHS score:
   - `score = 20.0`

### Participant ORG-002

1. Number of baseline rows: `3`
2. Number of participant rows: `8`
3. Feature count: `4`
4. Baseline feature statistics:
   - feature_0: mean=`2095.00`, std=`960.79`, min=`980.0`, max=`3325.0`
   - feature_1: mean=`2245.00`, std=`887.59`, min=`1220.0`, max=`3385.0`
   - feature_2: mean=`2113.33`, std=`1005.00`, min=`910.0`, max=`3370.0`
   - feature_3: mean=`2230.00`, std=`953.34`, min=`1110.0`, max=`3440.0`
5. Current participant feature statistics:
   - feature_0: mean=`1953.75`, std=`871.80`, min=`980.0`, max=`3340.0`
   - feature_1: mean=`2083.75`, std=`824.31`, min=`1210.0`, max=`3415.0`
   - feature_2: mean=`1972.50`, std=`897.67`, min=`910.0`, max=`3370.0`
   - feature_3: mean=`2069.38`, std=`878.75`, min=`1090.0`, max=`3460.0`
6. Exact drift metrics calculated:
   - `psi_per_feature = [5.75646273, 5.75646273, 5.75646273, 5.75646273]`
   - `psi_average = 5.756462731397495`
   - `drift_count = 4`
   - `features_with_drift = [0, 1, 2, 3]`
   - `drift_level = "severe"`
7. Intermediate normalized values:
   - same histogram/PSI path as above, but with a larger mismatch between the tiny 3-row baseline and the 8-row participant distribution
8. Clipping / thresholds:
   - same as above; because PSI is well above `0.50`, the score is forced to the floor `20.0`
9. Final raw drift value:
   - `psi_average = 5.756462731397495`
10. Final DHS score:
   - `score = 20.0`

### Participant ORG-003

1. Number of baseline rows: `3`
2. Number of participant rows: `8`
3. Feature count: `4`
4. Baseline feature statistics:
   - feature_0: mean=`2346.67`, std=`730.60`, min=`1525.0`, max=`3300.0`
   - feature_1: mean=`2421.67`, std=`737.34`, min=`1620.0`, max=`3400.0`
   - feature_2: mean=`2373.33`, std=`743.58`, min=`1565.0`, max=`3360.0`
   - feature_3: mean=`2441.67`, std=`767.38`, min=`1590.0`, max=`3450.0`
5. Current participant feature statistics:
   - feature_0: mean=`2455.63`, std=`628.66`, min=`1525.0`, max=`3335.0`
   - feature_1: mean=`2521.88`, std=`631.81`, min=`1620.0`, max=`3400.0`
   - feature_2: mean=`2468.13`, std=`628.01`, min=`1565.0`, max=`3365.0`
   - feature_3: mean=`2555.00`, std=`638.54`, min=`1590.0`, max=`3455.0`
6. Exact drift metrics calculated:
   - `psi_per_feature = [8.69245636, 8.69245636, 8.69245636, 5.74447598]`
   - `psi_average = 7.955461265836562`
   - `drift_count = 4`
   - `features_with_drift = [0, 1, 2, 3]`
   - `drift_level = "severe"`
7. Intermediate normalized values:
   - same PSI formula as above; the 3-row baseline creates large histogram mismatches again
8. Clipping / thresholds:
   - same floor rule: `psi >= 0.50` yields `score = max(20.0, 20.0 - (psi - 0.50) * 5.0)`
   - this remains exactly `20.0`
9. Final raw drift value:
   - `psi_average = 7.955461265836562`
10. Final DHS score:
   - `score = 20.0`

---

## Why every participant gets exactly 20.00

The deterministic path is:

1. Each participant has `baseline_rows = 3` because the runner picks one representative sample per class.
2. The participant itself has `8` rows and 4 features.
3. `DriftHealthScorer._calculate_psi_feature` computes PSI comparing the current distribution to the baseline distribution.
4. Since the baseline is extremely sparse, the histogram proportions differ dramatically, producing enormous PSI values.
5. Every participant ends up with `psi_average > 0.50`.
6. In `DriftHealthScorer._psi_to_score`, the severe-drift rule is:

```python
else:
    return max(20.0, 20.0 - (psi - 0.50) * 5.0)
```

This creates a hard lower bound of `20.0` for all PSI values above `0.50`.

So the final output is not a mystery: the baseline is too small and too unrepresentative, and the severe drift floor forces the score to `20.0` exactly.

---

## Root cause summary

This is not a scoring bug in the sense of a formula error for the intended input domain; it is a baseline construction issue caused by using a baseline that is intentionally tiny and not statistically representative of the participant distribution. The example fixture itself also amplifies the effect because it has only three classes and a very small number of samples per participant.

That makes the result best classified as:

`C. Baseline construction issue`
