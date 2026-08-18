# Multi-Round Simulation Architecture

## Overview

The multi-round simulation layer extends the frozen Protector Uttam scoring engine to support continuous federated learning rounds, where participants submit model updates across multiple time periods and their trust scores evolve based on historical performance and scenario injection.

**Key principle**: The frozen scoring engine, real-data pipeline, and component calculators remain unchanged. The multi-round layer is a wrapper that orchestrates repeated participant evaluation, persists history, and injects controlled scenario conditions.

---

## Architecture Components

### 1. **Scenario Injector** (`src/scenario_injector.py`)

Controls experiment conditions by applying deterministic, bounded modifications to participant feature data.

**Supported scenarios**:
- `normal`: No modifications; baseline participant behavior
- `drift`: Feature distribution shifted (8-20% scale)
- `unreliable`: Additional Gaussian noise (12% std deviation)
- `poor_performance`: Feature degradation (80% scale) + noise
- `unsafe_update`: Extreme perturbation (140% scale) + high noise
- `mixed`: Realistic combination of drift and noise

**Important**: Scenarios modify input features only. Scoring formulas remain frozen.

Example:
```python
from src.scenario_injector import apply_scenario_to_participant

participant_modified, impact = apply_scenario_to_participant(
    participant,
    scenario="drift",
    round_number=3,
    seed=42
)
```

### 2. **Multi-Round Runner** (`src/multi_round_runner.py`)

Orchestrates round-by-round participant evaluation, maintains persistent history, and produces exportable results.

**Pipeline flow**:
1. Load CSV dataset
2. For each round (1 to N):
   - Simulate participant splits
   - Apply scenario to each participant
   - Score with frozen engine
   - Update participant history state
   - Export results

**Key features**:
- Deterministic participant splits (IID/non-IID)
- Global, participant-independent reference baseline
- Persistent trust/decision/performance history
- Scenario-conditioned feature perturbation

Example:
```python
from src.multi_round_runner import run_multi_round_pipeline

rows = run_multi_round_pipeline(
    csv_path="data.csv",
    target_column="label",
    participants=5,
    rounds=10,
    seed=42,
    scenario="mixed",
    output_dir="experiments/results"
)
```

### 3. **Result Exporter** (`src/result_exporter.py`)

Exports multi-round results to CSV and JSON for dashboard consumption.

**Output formats**:
- **CSV**: Flat table with one row per (round, participant) evaluation
- **JSON**: Nested structure with participant history metadata included

Example output row:
```json
{
  "round": 1,
  "participant_id": "ORG-001",
  "participated": true,
  "DQS": 85.0,
  "DHS": 90.0,
  "USS": 88.0,
  "RS": 92.0,
  "PS": 85.0,
  "confidence": 88.0,
  "trust_score": 88.5,
  "decision": "ALLOW",
  "data_origin": "real_csv_dataset",
  "history_source": "simulated prototype metadata",
  "real_data": true,
  "simulated_history_metadata": true,
  "scenario": "mixed",
  "participant_history": {
    "success_count": 1,
    "total_count": 1,
    "consecutive_failures": 0,
    "trust_history": [88.5],
    "decision_history": ["ALLOW"]
  }
}
```

### 4. **Dashboard Data Layer** (`src/dashboard_data.py`)

Provides Streamlit-independent data loading and transformation functions.

Functions:
- `load_results(json_path)`: Load multi-round JSON results
- `results_to_dataframe(rows)`: Convert to pandas DataFrame with typed columns

### 5. **Dashboard UI** (`dashboard.py`)

Streamlit-based interactive visualization of multi-round results.

**Pages**:
- **Overview**: Summary stats, decisions distribution, component averages
- **Trust Analytics**: Trust score trends by participant
- **Component Analytics**: Per-component score distributions and correlations
- **Participant Analytics**: Per-participant round-by-round metrics
- **Decision Analytics**: Decision patterns and distribution over rounds
- **Data Transparency**: Real vs. simulated data classification, validation messages

---

## Data Flow Diagram

```
CSV Dataset
    ↓
Dataset Loader (load_csv)
    ↓
Participant Simulator (simulate_participants)
    ↓
Multi-Round Runner (run_multi_round_pipeline)
    ├─→ For each round:
    │   ├─ Scenario Injector (apply_scenario_to_participant)
    │   ├─ Component Orchestrator (score_data_quality, score_drift_health)
    │   ├─ Model Runner (train local model, extract update safety)
    │   ├─ Frozen Scoring Engine (DQS, DHS, USS, RS, PS, TS)
    │   ├─ History State Updater (track decisions, trust evolution)
    │   └─ Row Generator (per-participant per-round record)
    ↓
Result Exporter (export_results_csv, export_results_json)
    ├─→ experiments/results/multi_round_results.csv
    └─→ experiments/results/multi_round_results.json
    ↓
Dashboard Data Layer (load_results, results_to_dataframe)
    ↓
Dashboard UI (Streamlit pages)
    └─→ Interactive visualization
```

---

## Running the Multi-Round Pipeline

### Command Format

```bash
python run_multi_round.py \
  --csv <path-to-dataset.csv> \
  --target <target-column> \
  --participants <num-participants> \
  --rounds <num-rounds> \
  --seed <random-seed> \
  --scenario <scenario-name> \
  --output-dir <output-directory>
```

### Example Commands

**Normal operation (5 participants, 10 rounds, mixed scenario)**:
```bash
python run_multi_round.py \
  --csv tests/fixtures/participant_component_fixture.csv \
  --target label \
  --participants 5 \
  --rounds 10 \
  --seed 42 \
  --scenario mixed
```

**Drift scenario (2 participants, 5 rounds)**:
```bash
python run_multi_round.py \
  --csv data/my_dataset.csv \
  --target target \
  --participants 2 \
  --rounds 5 \
  --seed 123 \
  --scenario drift
```

### Output

Results are written to:
- `experiments/results/multi_round_results.csv` — flat tabular format
- `experiments/results/multi_round_results.json` — hierarchical format with history

---

## Running the Dashboard

### Prerequisites

Install Streamlit:
```bash
pip install streamlit
```

### Command

```bash
streamlit run dashboard.py
```

### Default Results Location

The dashboard looks for results at `experiments/results/multi_round_results.json` by default.
You can override this path in the sidebar.

### Pages Overview

1. **Overview**: High-level metrics and decision distribution
2. **Trust Analytics**: Per-participant trust score evolution
3. **Component Analytics**: DQS/DHS/USS/RS/PS breakdown
4. **Participant Analytics**: Detailed per-participant scorecard
5. **Decision Analytics**: Decision patterns across all participants
6. **Data Transparency**: Real data vs. simulated metadata classification

---

## History State Persistence

The `ParticipantHistoryState` class tracks evolution across rounds:

```python
@dataclass
class ParticipantHistoryState:
    participant_id: str
    round_history: List[int]              # Rounds participated in
    decision_history: List[str]           # ALLOW/MONITOR/REVIEW/BLOCK decisions
    trust_history: List[float]            # Trust scores over time
    confidence_history: List[float]       # Confidence scores over time
    performance_history: List[float]      # Performance scores over time
    last_seen_round: int                  # Most recent round participated
    success_count: int                    # Cumulative successful decisions
    total_count: int                      # Total participation count
    consecutive_failures: int             # Current failure streak
    last_seen_rounds_ago: int            # Rounds since last participation
    consistency_score: float              # Estimated consistency [0, 1]
```

This state is updated after each round's scoring and eventually mapped into the ReliabilityInput for the frozen ReliabilityScorer.

---

## Real vs. Simulated Data Classification

### Real Data (from CSV)

- Feature matrices (X)
- Labels (y)
- Data quality metrics (completeness, outliers, schema validity)
- Drift health signals (PSI-based distribution comparison)
- Model performance (accuracy, fairness, stability)
- Update safety signals (gradient magnitude, freshness, stability)

**Marked as**: `"real_data": true, "data_origin": "real_csv_dataset"`

### Simulated Metadata (Prototype Only)

- Participant success/failure history
- Consistency scores
- Last seen rounds
- Scenario injection perturbations

**Marked as**: `"simulated_history_metadata": true, "history_source": "simulated prototype metadata"`

**Important**: Simulated history values should NEVER be presented as real-world measurements. They exist solely for prototype experimentation.

---

## Scenario Injection Details

Each scenario applies bounded, deterministic feature modifications designed to stress the scoring engine under realistic failure conditions.

| Scenario | Feature Scaling | Noise | Impact |
|----------|-----------------|-------|--------|
| normal | 1.0 | 0% | Baseline behavior |
| drift | 1.05-1.20 | 2% | Distribution shift |
| unreliable | 1.0 | 12% | Data uncertainty |
| poor_performance | 0.8 | 7% | Feature degradation |
| unsafe_update | 1.4 | 15% | Safety gate stress |
| mixed | 1.1 | 6% | Realistic combination |

All modifications use a seeded random number generator for reproducibility.

---

## Testing

### Regression Suite

```bash
pytest tests -q
```

Includes:
- 285 core scoring engine tests (DQS, DHS, USS, RS, PS, TS, confidence)
- 1 multi-round edge case test (empty baseline handling)
- 4 dashboard data layer tests (load, transform, schema)

### Running Specific Tests

```bash
# Test multi-round edge cases
pytest tests/test_multi_round.py -v

# Test dashboard data layer
pytest tests/test_dashboard_data.py -v

# Test real-data pipeline integration
pytest tests/test_run_real_data.py -v
```

---

## Integration with Frozen Scoring Engine

The multi-round runner preserves the frozen scoring engine's contract:

1. **No formula modifications**: DQS, DHS, USS, RS, PS, confidence, and trust score formulas are unchanged.
2. **No input/output schema changes**: Input types (DataQualityInput, DriftHealthInput, etc.) remain the same.
3. **Wrapper-only modifications**: The multi-round layer wraps participant data, calls the frozen scorers, and persists results.
4. **Deterministic baseline construction**: Uses the same participant-independent reference baseline as `run_real_data.py`.

Example integration point:
```python
# Inside run_multi_round_pipeline:
dqs = score_data_quality(scenario_participant)
dhs = score_drift_health(scenario_participant, baseline_features=baseline_features)
uss = UpdateSafetyScorer().score(model_run.update_safety_input)
rs = ReliabilityScorer().score(reliability_input)
ps = PerformanceScorer().score(model_run.performance_input)

trust_input = TrustInput(dqs=..., dhs=..., uss=..., rs=..., ps=..., ...)
trust_output = TrustScorer().score(trust_input)  # Frozen engine
```

---

## Baseline Validation

The multi-round runner validates baselines using the same criteria as `run_real_data.py`:

- Baseline must contain ≥12 samples (configurable minimum)
- Baseline must match participant feature count
- Baseline must be free of NaN/Inf values
- If validation fails, DHS defaults to 0 with "INSUFFICIENT DATA" status

Example validation output:
```
"validation_message": "Baseline contains 11 rows, below the prototype minimum of 12. 
                       INSUFFICIENT DATA FOR RELIABLE DRIFT ESTIMATION."
```

---

## File Structure

```
protector_uttam/
├── src/
│   ├── scoring_engines.py          (Frozen core: 7 scoring systems)
│   ├── component_orchestrator.py    (DQS + DHS wrapper)
│   ├── dataset_loader.py            (CSV loading)
│   ├── participant_simulator.py     (IID/non-IID splits)
│   ├── model_runner.py              (Local model training)
│   ├── participant_history.py       (Simulated metadata)
│   ├── scenario_injector.py         (NEW: Scenario application)
│   ├── result_exporter.py           (NEW: Export to CSV/JSON)
│   ├── multi_round_runner.py        (NEW: Round orchestration)
│   ├── dashboard_data.py            (NEW: Dashboard data layer)
│   └── validation_framework.py      (Data validation utilities)
├── dashboard.py                     (NEW: Streamlit UI)
├── run_multi_round.py               (NEW: CLI entry point)
├── run_real_data.py                 (Existing single-round pipeline)
├── run_scenarios.py                 (Existing scenario validation)
├── run_demo.py                      (Existing demo runner)
├── tests/
│   ├── test_multi_round.py          (NEW: Multi-round tests)
│   ├── test_dashboard_data.py       (NEW: Dashboard data layer tests)
│   ├── test_*.py                    (285 existing core tests)
│   └── fixtures/
│       └── participant_component_fixture.csv
├── experiments/
│   └── results/
│       ├── multi_round_results.csv
│       └── multi_round_results.json
└── docs/
    ├── MULTI_ROUND_SIMULATION.md    (This file)
    ├── DASHBOARD_GUIDE.md           (Dashboard usage)
    └── ...
```

---

## Performance Characteristics

**Typical runtime** (5 participants × 10 rounds on 48-sample fixture):
- Data loading: ~10ms
- Baseline construction: ~20ms
- Per-round scoring: ~50-100ms
- Total: ~0.5-1 second

**Memory usage**:
- Results DataFrame: ~1MB per 10,000 rows
- History state: ~10KB per participant
- Typical case (5P × 10R): <5MB total

---

## Future Enhancements

1. **Multi-batch processing**: Parallelize rounds across worker processes
2. **Model persistence**: Save trained models per participant per round
3. **Policy customization**: Allow user-defined decision thresholds per scenario
4. **Anomaly detection**: Automated flagging of unusual trust patterns
5. **Audit logging**: Full decision trail with intermediate scores
6. **A/B testing**: Compare different scoring weights across runs

---

## Troubleshooting

### Empty Baseline Error

**Symptom**: `ValueError: Found array with 0 sample(s) (shape=(0, 4)) while a minimum of 1 is required`

**Cause**: The global baseline construction returned zero samples (rare edge case).

**Solution**: This is now handled gracefully. The model runner will not attempt to fit a baseline model when baseline arrays are empty. DHS will report `INSUFFICIENT DATA`.

### Low Baseline Samples Warning

**Symptom**: `"Baseline contains 11 rows, below the prototype minimum of 12. INSUFFICIENT DATA FOR RELIABLE DRIFT ESTIMATION."`

**Cause**: The dataset is too small to construct a meaningful 12+ sample baseline.

**Solution**: Use a larger dataset, or set `--min-baseline-samples 5` in the pipeline.

### Missing Results File

**Symptom**: Dashboard shows "No results found"

**Cause**: `run_multi_round.py` hasn't been run, or results were saved to a different path.

**Solution**: Run the pipeline first, then point the dashboard to the correct results file via the sidebar.

---

## References

- [Scoring Engines Documentation](../docs/IMPLEMENTATION_COMPLETE.md)
- [Real-Data Pipeline Guide](../docs/BASELINE_AND_DHS_VALIDATION.md)
- [Scenario Validation](../run_scenarios.py)
- [Dashboard Guide](./DASHBOARD_GUIDE.md)
