# Dashboard User Guide

## Quick Start

### 1. Generate Multi-Round Results

First, run the multi-round pipeline to generate results:

```bash
python run_multi_round.py \
  --csv tests/fixtures/participant_component_fixture.csv \
  --target label \
  --participants 3 \
  --rounds 5 \
  --seed 42 \
  --scenario mixed
```

This creates:
- `experiments/results/multi_round_results.csv` (flat table)
- `experiments/results/multi_round_results.json` (hierarchical with history)

### 2. Launch the Dashboard

```bash
streamlit run dashboard.py
```

The dashboard will open in your browser at `http://localhost:8501`

### 3. Select Results File (Optional)

By default, the dashboard loads from `experiments/results/multi_round_results.json`.

To use a different results file:
1. Click the text input in the left sidebar labeled "Results JSON path"
2. Enter the full path to your results file
3. Press Enter

---

## Dashboard Pages

### Overview

**What it shows**:
- Total rounds and participants
- Number of evaluations
- Average trust score
- Decisions distribution (pie/bar chart)
- Average trust by round (trend line)
- Component score summary statistics

**Use case**: Get a quick sanity check on the simulation results.

---

### Trust Analytics

**What it shows**:
- Trust score trend line for a selected participant
- Min/max/average trust scores
- Distribution histogram of all trust scores
- Decision summary table (participants × decisions)

**Use case**:
- Monitor a specific participant's trust trajectory
- Identify outliers or sudden changes
- Understand decision distribution patterns

**How to use**:
1. Use the dropdown to select a participant
2. View their trust score over rounds
3. Scroll down to see statistics and aggregate patterns

---

### Component Analytics

**What it shows**:
- Average component scores (DQS, DHS, USS, RS, PS) by round
- Separate histogram for each component
- Correlation matrix between components

**Use case**:
- Understand which components drive trust score changes
- Identify component correlations
- Debug scoring behavior

**Components explained**:
- **DQS** (Data Quality Score): Feature validity, completeness, outliers
- **DHS** (Drift Health Score): Distribution similarity to baseline
- **USS** (Update Safety Score): Gradient validity, magnitude, freshness
- **RS** (Reliability Score): Participant heartbeat, availability, consistency
- **PS** (Performance Score): Model accuracy, fairness, stability

---

### Participant Analytics

**What it shows**:
- Round-by-round scores for a selected participant
- Metric summary (total rounds, avg trust, decision counts)
- Detailed table with all component scores

**Use case**:
- Audit a specific participant's performance
- Verify decisions make sense given scores
- Track performance degradation or improvement

**How to use**:
1. Use the dropdown to select a participant
2. Review the metric summary cards
3. Scroll down to see detailed per-round breakdown

---

### Decision Analytics

**What it shows**:
- Count of each decision type (ALLOW, MONITOR, REVIEW, BLOCK)
- Pie chart of decision distribution
- Stacked bar chart of decisions by round
- Trust score statistics per decision

**Use case**:
- Verify decision distribution is reasonable
- Identify if all decisions are one type (sign of misconfiguration)
- Understand trust score ranges for each decision

**Decision meanings**:
- **ALLOW** (trust ≥75): Contribution accepted
- **MONITOR** (60-74): Accepted with tracking
- **REVIEW** (40-59): Requires manual review
- **BLOCK** (<40): Contribution rejected

---

### Data Transparency

**What it shows**:
- Clear separation of real data vs. simulated metadata
- Sample record with provenance tags
- Baseline validation messages

**Use case**:
- Understand what's real and what's synthetic
- Identify baseline size/quality issues
- Verify data classification is correct

**Real data** (measured from CSV):
- Feature matrices and labels
- Data quality metrics
- Drift health metrics
- Model performance signals
- Update safety signals

**Simulated metadata** (prototype only):
- Participant history (success counts, failures)
- Consistency scores
- Scenario injection effects

⚠️ **Important**: Simulated history values should NEVER be presented as real-world measurements.

---

## Common Workflows

### Debugging Low Trust Scores

1. Go to **Participant Analytics**
2. Select the participant with low trust
3. Find the round with the lowest score
4. Go to **Component Analytics**
5. Check which components are pulling the score down
6. Go to **Data Transparency** to verify baseline validation

### Monitoring Drift Scenario

1. Run pipeline with `--scenario drift`
2. Open **Trust Analytics**
3. Select a participant
4. Watch trust score decrease over rounds (expected)
5. Go to **Component Analytics** → DHS tab
6. Verify DHS scores are decreasing due to drift

### Validating Decision Distribution

1. Go to **Decision Analytics**
2. Check if decisions are balanced across ALLOW/MONITOR/REVIEW/BLOCK
3. If all decisions are ALLOW, the scenario might be too weak
4. If all decisions are BLOCK, the baseline might be too strict
5. Adjust `--seed` or scenario parameters and re-run

### Analyzing Component Correlations

1. Go to **Component Analytics**
2. Scroll to the correlation matrix
3. Identify high-correlation pairs (>0.7)
4. High correlations may indicate redundant signals
5. Low correlations indicate independent evidence

### Exporting Results

1. Results are automatically saved to CSV and JSON
2. Use pandas/Excel to open the CSV for further analysis
3. Use Python to parse the JSON for custom post-processing

Example Python:
```python
import json
import pandas as pd

# Load results
with open("experiments/results/multi_round_results.json") as f:
    rows = json.load(f)

# Convert to DataFrame
df = pd.DataFrame(rows)

# Analyze
print(df.groupby("decision")["trust_score"].agg(["mean", "std", "min", "max"]))
```

---

## Customization

### Change Default Results Path

Edit `dashboard.py` line 18:
```python
DEFAULT_RESULTS_JSON = RESULTS_DIR / "my_custom_results.json"
```

Or use the sidebar input (recommended).

### Add Custom Metrics

Add a new page function in `dashboard.py`:
```python
def page_custom_metrics(df: pd.DataFrame) -> None:
    st.title("Custom Metrics")
    # Your visualization here
```

Then add to the pages dictionary:
```python
pages = {
    ...
    "Custom Metrics": page_custom_metrics,
}
```

### Modify Thresholds

Thresholds are defined in the frozen scoring engine (`src/scoring_engines.py`).
To change them for the dashboard visualization only (without modifying scoring):

```python
# In dashboard.py, create a mapping
DECISION_THRESHOLDS = {
    "ALLOW": 75,
    "MONITOR": 60,
    "REVIEW": 40,
    "BLOCK": 0,
}
```

Then use in visualizations as needed.

---

## Troubleshooting

### "No data loaded. Please run the multi-round pipeline."

**Cause**: Results file doesn't exist or is empty.

**Fix**:
```bash
python run_multi_round.py --csv data.csv --target label --participants 3 --rounds 5
```

### "Failed to load results: ..."

**Cause**: JSON is malformed or file is corrupted.

**Fix**:
1. Verify the file exists: `ls -la experiments/results/multi_round_results.json`
2. Validate JSON: `python -m json.tool experiments/results/multi_round_results.json | head`
3. Re-run the pipeline

### Streamlit not found

**Fix**: Install it
```bash
pip install streamlit
```

### Dashboard shows only zeros

**Cause**: Results file exists but contains no valid data.

**Fix**:
1. Check if dataset has enough samples (≥12 for baseline)
2. Run pipeline with verbose output
3. Verify CSV target column exists and has valid labels

### Very slow performance

**Cause**: Results file is very large (1M+ rows).

**Workaround**:
1. Reduce `--rounds` and `--participants`
2. Use a filtered subset of results
3. Run dashboard on a more powerful machine

---

## Best Practices

### Before Sharing Results

1. Verify data transparency classifications are correct
2. Check baseline validation messages for warnings
3. Confirm no sensitive information is in the CSV
4. Export anonymized results

### Scenario Selection

- **normal**: Baseline behavior (all components stable)
- **drift**: Test drift detection sensitivity
- **unreliable**: Test participant consistency scoring
- **poor_performance**: Test performance component
- **unsafe_update**: Test safety gate effectiveness
- **mixed**: Realistic combined stress test

### Dataset Size Guidelines

- **Minimum**: 50 rows (small prototype)
- **Recommended**: 100-500 rows (good baseline)
- **Production**: 1000+ rows (robust estimation)

### Seed Management

- Use `--seed 42` for reproducible experiments
- Use different seeds to test sensitivity
- Document seed values in reports

---

## Integration with Other Tools

### Export to Excel

```bash
# Export CSV
python -c "
import pandas as pd
df = pd.read_csv('experiments/results/multi_round_results.csv')
df.to_excel('results.xlsx', index=False)
"
```

### Create Custom Visualizations

```python
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("experiments/results/multi_round_results.csv")

# Plot trust by participant
df.groupby("participant_id")["trust_score"].mean().plot(kind="bar")
plt.title("Average Trust Score by Participant")
plt.show()
```

### Integrate with ML Pipeline

```python
from src.dashboard_data import load_results, results_to_dataframe

rows = load_results("experiments/results/multi_round_results.json")
df = results_to_dataframe(rows)

# Use for downstream analysis
accepted = df[df["decision"] == "ALLOW"]
print(f"Acceptance rate: {len(accepted) / len(df) * 100:.1f}%")
```

---

## FAQ

**Q: Can I run multiple simulations and compare them?**

A: Yes, save results to different directories:
```bash
python run_multi_round.py --csv data.csv --target label --scenario drift --output-dir results/drift_scenario
python run_multi_round.py --csv data.csv --target label --scenario unreliable --output-dir results/unreliable_scenario
```

Then open each in the dashboard by changing the results path.

**Q: Why does my trust score go to zero suddenly?**

A: Likely a hard safety gate failure (USS < 0) or baseline validation failure. Check the `validation_message` column.

**Q: Can I modify scores after generation?**

A: Not recommended. The scores come from the frozen engine. If you need different thresholds, re-run with a different scenario or modify the pipeline code.

**Q: How do I export the dashboard?**

A: Use Streamlit's built-in export:
1. Click the menu (hamburger icon) in the top-right
2. Select "Rerun" to refresh data
3. Use browser Print to PDF

**Q: Are the simulated history values realistic?**

A: No. They're prototype-only synthetic metadata designed for testing the reliability scoring component. Never present them as real-world measurements.

---

## References

- [Multi-Round Simulation Architecture](./MULTI_ROUND_SIMULATION.md)
- [Real-Data Pipeline](../run_real_data.py)
- [Scoring Engines Documentation](./IMPLEMENTATION_COMPLETE.md)
- [Scenario Validation](../run_scenarios.py)

