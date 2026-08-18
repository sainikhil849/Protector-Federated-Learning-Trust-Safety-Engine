"""Data layer for dashboard results - Streamlit-independent utility functions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd


def load_results(json_path: str | Path) -> List[Dict[str, Any]]:
    """Load multi-round results from JSON."""
    json_path = Path(json_path)
    if not json_path.exists():
        return []
    try:
        with json_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def results_to_dataframe(rows: List[Dict[str, Any]]) -> pd.DataFrame:
    """Convert raw results to a pandas DataFrame for analysis."""
    if not rows:
        return pd.DataFrame()

    flattened = []
    for row in rows:
        record = {
            "round": row.get("round"),
            "participant_id": row.get("participant_id"),
            "participated": row.get("participated", True),
            "DQS": row.get("DQS", row.get("dqs", 0.0)),
            "DHS": row.get("DHS", row.get("dhs", 0.0)),
            "USS": row.get("USS", row.get("uss", 0.0)),
            "RS": row.get("RS", row.get("rs", 0.0)),
            "PS": row.get("PS", row.get("ps", 0.0)),
            "confidence": row.get("confidence", row.get("confidence", 0.0)),
            "trust_score": row.get("trust_score", 0.0),
            "decision": row.get("decision", "UNKNOWN"),
            "decision_reason": row.get("decision_reason", ""),
            "scenario": row.get("scenario", row.get("history_scenario", "unknown")),
            "data_origin": row.get("data_origin", "real_csv_dataset"),
            "history_source": row.get("history_source", "simulated prototype metadata"),
            "real_data": row.get("real_data", True),
            "simulated_history": row.get("simulated_history_metadata", False),
            "baseline_sample_count": row.get("baseline_sample_count", 0),
            "baseline_validation_status": row.get("baseline_validation_status", "UNKNOWN"),
            "baseline_validation_message": row.get("baseline_validation_message", ""),
            "psi_average": row.get("psi_average", 0.0),
            "drift_level": row.get("drift_level", "unknown"),
        }
        flattened.append(record)

    return pd.DataFrame(flattened)
