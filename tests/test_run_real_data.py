import json
from pathlib import Path

import pandas as pd
import pytest

from run_real_data import run_real_data_pipeline


FIXTURE = "tests/fixtures/participant_component_fixture.csv"


def test_run_real_data_pipeline_writes_csv_and_json(tmp_path):
    results = run_real_data_pipeline(
        csv_path=FIXTURE,
        target_column="label",
        participants=3,
        seed=42,
        output_dir=tmp_path,
    )

    assert len(results) == 3
    assert all("participant_id" in row for row in results)
    assert all("dqs" in row for row in results)
    assert all("dhs" in row for row in results)
    assert all("uss" in row for row in results)
    assert all("rs" in row for row in results)
    assert all("ps" in row for row in results)
    assert all("trust_score" in row for row in results)
    assert all("confidence" in row for row in results)
    assert all("decision" in row for row in results)
    assert all("decision_reason" in row for row in results)

    csv_path = tmp_path / "real_data_results.csv"
    json_path = tmp_path / "real_data_results.json"
    assert csv_path.exists()
    assert json_path.exists()

    csv_df = pd.read_csv(csv_path)
    assert set(csv_df.columns) >= {
        "participant_id",
        "data_origin",
        "history_source",
        "history_scenario",
        "dqs",
        "dhs",
        "uss",
        "rs",
        "ps",
        "trust_score",
        "confidence",
        "decision",
        "decision_reason",
    }

    json_rows = json.loads(json_path.read_text(encoding="utf-8"))
    assert len(json_rows) == len(results)
    assert all(row["history_source"] == "simulated prototype metadata" for row in json_rows)


def test_run_real_data_pipeline_rejects_invalid_dataset(tmp_path):
    with pytest.raises(ValueError):
        run_real_data_pipeline(
            csv_path="tests/fixtures/does_not_exist.csv",
            target_column="label",
            participants=2,
            seed=7,
            output_dir=tmp_path,
        )

    bad_csv = tmp_path / "bad.csv"
    bad_csv.write_text("feature_0,feature_1,label\n1,2,1\n3,4,\n", encoding="utf-8")
    with pytest.raises(ValueError):
        run_real_data_pipeline(
            csv_path=str(bad_csv),
            target_column="label",
            participants=1,
            seed=7,
            output_dir=tmp_path,
        )
