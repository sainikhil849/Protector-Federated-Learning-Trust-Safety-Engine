"""Streamlit dashboard for the Protector Uttam trust evaluation framework.

This dashboard reads the actual project outputs from the real-data pipeline and
presents them in a professional operational view without altering the scoring
logic or inventing synthetic performance.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import plotly.express as px
import streamlit as st

from run_real_data import run_real_data_pipeline
from src.dashboard_data import load_results, results_to_dataframe

RESULTS_DIR = Path("experiments/results")
DEFAULT_RESULTS_JSON = RESULTS_DIR / "real_data_results.json"


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _render_dataset_configuration() -> tuple[pd.DataFrame, dict]:
    st.title("Dataset configuration")
    uploaded_file = st.file_uploader("Upload a CSV dataset", type=["csv"])

    if uploaded_file is None:
        st.info("Upload a CSV file to start the real trust evaluation pipeline.")
        return pd.DataFrame(), {}

    upload_directory = Path("experiments/uploads")
    upload_directory.mkdir(parents=True, exist_ok=True)
    uploaded_path = upload_directory / uploaded_file.name
    uploaded_path.write_bytes(uploaded_file.getvalue())

    st.success(f"Uploaded: {uploaded_file.name}")
    df = pd.read_csv(uploaded_path)

    st.write(f"Rows: {len(df)}")
    st.write(f"Columns: {len(df.columns)}")
    st.write(f"Available columns: {list(df.columns)}")

    target_column = st.selectbox("Target column", list(df.columns))
    participant_count = st.number_input(
        "Number of participants",
        min_value=1,
        max_value=max(1, len(df)),
        value=min(3, len(df)),
    )
    random_seed = st.number_input("Random seed", min_value=0, max_value=999999, value=42)
    min_baseline_samples = st.number_input("Minimum baseline samples", min_value=1, max_value=1000, value=12)

    st.subheader("CSV preview")
    st.dataframe(df.head(10), use_container_width=True)

    return df, {
        "csv_path": str(uploaded_path),
        "target_column": target_column,
        "participants": int(participant_count),
        "seed": int(random_seed),
        "min_baseline_samples": int(min_baseline_samples),
    }


def _decision_explanation(row: Dict[str, Any]) -> str:
    dqs = _safe_float(row.get("DQS", 0.0), 0.0)
    dhs = _safe_float(row.get("DHS", 0.0), 0.0)
    uss = _safe_float(row.get("USS", 0.0), 0.0)
    rs = _safe_float(row.get("RS", 0.0), 0.0)
    ps = _safe_float(row.get("PS", 0.0), 0.0)

    lines = [
        f"• Data Quality Score: {dqs:.0f} — {'data passed quality checks' if dqs >= 75 else 'data quality issues detected'}",
        f"• Drift Health Score: {dhs:.0f} — {'no significant distribution drift detected' if dhs >= 75 else 'severe feature distribution drift detected' if dhs <= 20 else 'some drift detected'}",
        f"• Update Safety Score: {uss:.0f} — {'update passed safety evaluation' if uss >= 70 else 'update safety concerns present'}",
        f"• Reliability Score: {rs:.0f} — {'based on prototype participant history' if rs >= 60 else 'history indicates weak reliability'}",
        f"• Performance Score: {ps:.0f} — {'local model performance was strong' if ps >= 75 else 'model performance was weak or inconsistent'}",
    ]
    return "\n".join(lines)


def _overview(df: pd.DataFrame) -> None:
    st.title("Federated Update Trust & Safety Monitor")
    st.caption("Evaluate participant data quality, drift, update safety, reliability, and model performance before accepting model updates.")

    if df.empty:
        st.warning("No results loaded. Please upload a CSV and run the pipeline.")
        return

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        st.metric("Total Participants", int(df["participant_id"].nunique()))
    with col2:
        st.metric("ALLOW", int((df["decision"] == "ALLOW").sum()))
    with col3:
        st.metric("MONITOR", int((df["decision"] == "MONITOR").sum()))
    with col4:
        st.metric("REVIEW", int((df["decision"] == "REVIEW").sum()))
    with col5:
        st.metric("BLOCK", int((df["decision"] == "BLOCK").sum()))
    with col6:
        st.metric("Average Trust Score", f"{df['trust_score'].mean():.2f}")

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Decision distribution")
        decision_counts = df["decision"].value_counts().reindex(["ALLOW", "MONITOR", "REVIEW", "BLOCK"], fill_value=0)
        st.bar_chart(decision_counts)
    with c2:
        st.subheader("Average component scores")
        component_avg = df[["DQS", "DHS", "USS", "RS", "PS"]].mean().sort_values(ascending=False)
        st.bar_chart(component_avg)

    st.subheader("Trust score by participant")
    fig = px.bar(df, x="participant_id", y="trust_score", color="decision", title="Trust Score by Participant")
    st.plotly_chart(fig, use_container_width=True)


def _results(df: pd.DataFrame) -> None:
    st.subheader("Participant results table")
    table_cols = [
        "participant_id",
        "DQS",
        "DHS",
        "USS",
        "RS",
        "PS",
        "trust_score",
        "confidence",
        "decision",
        "data_origin",
        "history_source",
    ]
    table_df = df[table_cols].copy()
    table_df = table_df.rename(columns={"trust_score": "Trust Score", "confidence": "Confidence"})
    st.dataframe(table_df, use_container_width=True, hide_index=True)

    csv_bytes = table_df.to_csv(index=False).encode("utf-8")
    st.download_button("Download results CSV", data=csv_bytes, file_name="real_data_results.csv", mime="text/csv")


def _visualizations(df: pd.DataFrame) -> None:
    component_cols = ["DQS", "DHS", "USS", "RS", "PS"]

    st.subheader("Component score comparison")
    fig_box = px.box(df, y=component_cols, title="Component score comparison")
    st.plotly_chart(fig_box, use_container_width=True)

    selected_participant = st.selectbox("Select participant", sorted(df["participant_id"].unique().tolist()))
    participant_row = df[df["participant_id"] == selected_participant].iloc[0]
    radar_df = pd.DataFrame([{"Component": col, "Score": float(participant_row[col])} for col in component_cols])
    fig_bar = px.bar(radar_df, x="Component", y="Score", color="Component", title=f"Component scores for {selected_participant}")
    st.plotly_chart(fig_bar, use_container_width=True)


def _decision(df: pd.DataFrame) -> None:
    st.subheader("Decision explanation")
    participant = st.selectbox("Participant", sorted(df["participant_id"].unique().tolist()))
    row = df[df["participant_id"] == participant].iloc[0].to_dict()

    st.markdown(f"**Participant:** {participant}")
    st.markdown(f"**Trust Score:** {float(row['trust_score']):.2f}")
    st.markdown(f"**Confidence:** {float(row['confidence']):.2f}")
    st.markdown(f"**Decision:** {row['decision']}")
    st.markdown("**Why this decision?**")
    st.code(_decision_explanation(row))


def _baseline(df: pd.DataFrame) -> None:
    st.subheader("Baseline and DHS display")
    baseline_cols = [
        "participant_id",
        "baseline_sample_count",
        "baseline_validation_status",
        "baseline_validation_message",
        "psi_average",
        "drift_level",
        "DHS",
    ]
    baseline_df = df[baseline_cols].copy()
    st.dataframe(baseline_df, use_container_width=True, hide_index=True)

    for _, row in df.iterrows():
        status = str(row.get("baseline_validation_status", "UNKNOWN"))
        if status in {"INSUFFICIENT_DATA", "ERROR"}:
            st.warning(f"{row['participant_id']}: INSUFFICIENT DATA FOR RELIABLE DRIFT ESTIMATION — {row.get('baseline_validation_message', '')}")


def _prototype_interpretation() -> None:
    st.subheader("Prototype Interpretation")
    st.info(
        "- CSV-derived scores are based on real dataset processing.\n"
        "- Participant history may be simulated prototype metadata when no multi-round historical data is available.\n"
        "- Small datasets can produce unstable drift estimates.\n"
        "- A DHS score at the severe-drift floor is an output of the existing frozen scorer.\n"
        "- The project is a prototype trust evaluation framework, not a production federated learning deployment."
    )


def _run_pipeline(config: Dict[str, Any]) -> pd.DataFrame:
    rows = run_real_data_pipeline(
        csv_path=config["csv_path"],
        target_column=config["target_column"],
        participants=config["participants"],
        seed=config["seed"],
        output_dir=RESULTS_DIR,
        min_baseline_samples=config["min_baseline_samples"],
    )
    return results_to_dataframe(rows)


def main() -> None:
    st.set_page_config(page_title="Federated Update Trust & Safety Monitor", page_icon="🛡️", layout="wide")

    with st.sidebar:
        st.header("Run trust evaluation")
        _, config = _render_dataset_configuration()
        if config:
            if st.button("Run Trust Evaluation", type="primary"):
                try:
                    with st.spinner("Running the real trust pipeline..."):
                        df = _run_pipeline(config)
                    st.session_state["dashboard_df"] = df
                    st.session_state["dashboard_rows"] = load_results(RESULTS_DIR / "real_data_results.json")
                    st.success("Trust evaluation completed successfully.")
                except Exception as exc:
                    st.error(f"Evaluation failed: {exc}")
                    return

            if "dashboard_rows" in st.session_state:
                payload = json.dumps(st.session_state["dashboard_rows"], indent=2).encode("utf-8")
                st.download_button("Download final JSON", payload, file_name="real_data_results.json", mime="application/json")

    if "dashboard_df" in st.session_state and not st.session_state["dashboard_df"].empty:
        df = st.session_state["dashboard_df"]
        tabs = st.tabs(["Overview", "Participant Results", "Visualizations", "Decision Explanation", "Baseline & DHS", "Prototype Interpretation"])
        with tabs[0]:
            _overview(df)
        with tabs[1]:
            _results(df)
        with tabs[2]:
            _visualizations(df)
        with tabs[3]:
            _decision(df)
        with tabs[4]:
            _baseline(df)
        with tabs[5]:
            _prototype_interpretation()
    else:
        st.info("Upload a CSV and run the trust evaluation to populate the dashboard.")


if __name__ == "__main__":
    main()
