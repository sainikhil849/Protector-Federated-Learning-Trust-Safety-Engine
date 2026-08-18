# ??? Protector

## Federated Learning Trust & Safety Engine

Protector is an end-to-end prototype for evaluating the trustworthiness, safety, reliability, data quality, drift health, and model performance of federated learning participants before deciding whether their updates should be accepted, monitored, reviewed, or blocked.

## Problem Statement

Federated learning participants can produce updates with different levels of data quality, drift, update safety, reliability, and model performance. Protector evaluates these signals through a structured trust-scoring pipeline so a central coordinator can make explainable decisions instead of blindly averaging all updates.

## Architecture

```text
CSV Dataset
    ?
Dataset Validation
    ?
Participant Simulation
    ?
Reference Baseline Construction
    ?
Local Model Training
    ?
Component Scoring
    +-- Data Quality Score (DQS)
    +-- Drift Health Score (DHS)
    +-- Update Safety Score (USS)
    +-- Reliability Score (RS)
    +-- Performance Score (PS)
    ?
Trust Scoring Engine
    ?
Trust Score + Confidence
    ?
ALLOW / MONITOR / REVIEW / BLOCK
```

## Trust Components

| Component | Purpose |
| --- | --- |
| DQS | Evaluates participant data quality |
| DHS | Measures distribution drift against a reference baseline |
| USS | Evaluates model update safety |
| RS | Evaluates participant reliability |
| PS | Evaluates model performance |
| Trust Score | Combines component signals into a final trust assessment |
| Confidence | Indicates confidence in the evaluation |
| Decision | ALLOW / MONITOR / REVIEW / BLOCK |

## Tech Stack

- Python
- NumPy
- Pandas
- scikit-learn
- Pytest
- Streamlit
- Plotly

## Project Structure

```text
src/
    __init__.py
    component_orchestrator.py
    dashboard_data.py
    dataset_loader.py
    model_runner.py
    multi_round_runner.py
    participant_history.py
    participant_simulator.py
    result_exporter.py
    scenario_injector.py
    scoring_engines.py
    validation_framework.py

tests/
    fixtures/
    test_*.py

docs/
    ...

dashboard.py
run_demo.py
run_real_data.py
run_scenarios.py
requirements.txt
pytest.ini
README.md
.gitignore
```

## Installation

For Windows PowerShell:

```powershell
cd "C:\Users\saini\OneDrive\Desktop\codes\protector_uttam"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Run Tests

```bash
python -m pytest tests -q
```

## Run Scenario Validation

```bash
python run_scenarios.py
```

## Run Real Data Pipeline

```bash
python run_real_data.py --csv tests/fixtures/participant_component_fixture.csv --target label --participants 3 --seed 42
```

This writes JSON and CSV output files for the pipeline results.

## Run Dashboard

```bash
python -m streamlit run dashboard.py
```

## Testing

Verified in the current repository:

- 290 passed
- 0 failed

This verification includes the real test suite, scenario validation, and the real-data pipeline checks.

## Example Output

Example output from the real CSV pipeline:

```text
Participant ORG-001: DQS=100.00 DHS=20.00 USS=75.00 RS=93.08 PS=100.00 Trust=75.46 Decision=ALLOW
Participant ORG-002: DQS=100.00 DHS=20.00 USS=79.29 RS=54.61 PS=100.00 Trust=70.98 Decision=MONITOR
Participant ORG-003: DQS=100.00 DHS=20.00 USS=75.02 RS=72.75 PS=100.00 Trust=72.42 Decision=MONITOR
```

## Prototype Limitations

- Participant history may use simulated prototype metadata.
- Small datasets can produce unstable drift estimates.
- This project is a prototype rather than a distributed production federated learning deployment.
- Larger datasets and multi-round participant histories would strengthen empirical validation.

## Future Improvements

- Larger real-world datasets
- Multi-round participant history
- Actual federated learning integration
- Persistent experiment tracking
- Deployed dashboard and API
- Improved drift baseline management

## Summary

Protector is a research and prototype-grade trust and safety engine for federated learning. It demonstrates the full loop from raw CSV ingestion through validation, participant simulation, local model training, component scoring, and trust-based decisions, while keeping the core scoring engine frozen and the project verifiable through automated tests.
