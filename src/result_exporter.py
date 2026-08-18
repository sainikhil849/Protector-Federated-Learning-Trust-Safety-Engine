"""Export helpers for the multi-round prototype results."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List


def export_results_csv(rows: Iterable[Dict[str, Any]], output_path: str | Path) -> Path:
    """Write rows to a CSV file using a stable, explicit schema."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows = list(rows)
    if not rows:
        fieldnames = [
            "round",
            "participant_id",
            "participated",
            "DQS",
            "DHS",
            "USS",
            "RS",
            "PS",
            "confidence",
            "trust_score",
            "decision",
            "data_origin",
            "history_source",
            "real_data",
            "simulated_history_metadata",
            "scenario",
        ]
        with output_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
        return output_path

    fieldnames = list(rows[0].keys())
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return output_path


def export_results_json(rows: Iterable[Dict[str, Any]], output_path: str | Path) -> Path:
    """Write rows to a JSON file."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = list(rows)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output_path
