"""Tests for multi-round results and dashboard data layer."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.dashboard_data import load_results, results_to_dataframe


def test_load_results_from_json():
    """Verify dashboard can load multi-round JSON results."""
    results_file = Path("experiments/results/multi_round_results.json")
    
    if not results_file.exists():
        # Skip if results haven't been generated yet
        return
    
    rows = load_results(results_file)
    assert isinstance(rows, list)
    assert len(rows) > 0
    
    first_row = rows[0]
    assert "round" in first_row
    assert "participant_id" in first_row
    assert "trust_score" in first_row
    assert "decision" in first_row


def test_results_to_dataframe():
    """Verify conversion from raw results to DataFrame."""
    sample_rows = [
        {
            "round": 1,
            "participant_id": "ORG-001",
            "participated": True,
            "DQS": 85.0,
            "DHS": 90.0,
            "USS": 88.0,
            "RS": 92.0,
            "PS": 85.0,
            "confidence": 88.0,
            "trust_score": 88.5,
            "decision": "ALLOW",
            "scenario": "normal",
            "data_origin": "test",
            "real_data": True,
            "simulated_history_metadata": True,
        }
    ]
    
    df = results_to_dataframe(sample_rows)
    
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert df.iloc[0]["participant_id"] == "ORG-001"
    assert df.iloc[0]["trust_score"] == 88.5
    assert df.iloc[0]["decision"] == "ALLOW"


def test_results_to_dataframe_empty():
    """Verify empty results handle gracefully."""
    df = results_to_dataframe([])
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 0


def test_dataframe_component_columns_exist():
    """Verify DataFrame has all component columns."""
    sample_rows = [
        {
            "round": 1,
            "participant_id": "ORG-001",
            "participated": True,
            "DQS": 80.0,
            "DHS": 75.0,
            "USS": 85.0,
            "RS": 90.0,
            "PS": 88.0,
            "confidence": 85.0,
            "trust_score": 84.0,
            "decision": "MONITOR",
            "scenario": "drift",
            "data_origin": "test",
            "real_data": True,
            "simulated_history_metadata": True,
        }
    ]
    
    df = results_to_dataframe(sample_rows)
    
    expected_cols = ["DQS", "DHS", "USS", "RS", "PS", "confidence", "trust_score"]
    for col in expected_cols:
        assert col in df.columns, f"Missing column: {col}"
