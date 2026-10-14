"""Data-quality view of the processed lap table."""

import streamlit as st

from src.charts import (
    plot_category_counts,
    plot_correlation_heatmap,
    plot_laptime_distribution,
    plot_laptimes_by_driver,
    plot_missingness,
)
from src.eda import (
    category_counts,
    correlation_matrix,
    missingness,
    numeric_describe,
    valid_pace,
)
from src.state import get_bundle, show_fig, show_table
from src.theme import format_seconds


bundle = get_bundle()
session = bundle.session
laps = bundle.tables["laps"]

st.title("Data quality")
st.caption(
    "These counts use the full loaded session, before the sidebar filters. "
    "Valid pace means an accurate lap that is not deleted and is not a pit in-lap or out-lap."
)

if laps.empty:
    st.warning("No lap rows to analyse.")
    st.stop()

st.subheader("Missing values")
miss = missingness(laps)
show_fig(plot_missingness(miss))
with st.expander("Missingness table"):
    show_table(miss, hide_index=True)

st.subheader("Lap categories")
counts = category_counts(laps)
left, right = st.columns([1, 2])
with left:
    show_table(counts, hide_index=True)
with right:
    show_fig(plot_category_counts(counts))

st.subheader("Numeric summary")
show_table(numeric_describe(valid_pace(laps)))

st.subheader("Distribution")
show_fig(plot_laptime_distribution(laps))

st.subheader("Spread by driver")
show_fig(plot_laptimes_by_driver(laps, session))

st.subheader("Correlations")
st.caption("Pearson correlation on valid-pace laps: lap time, sectors, speed traps, tyre life, and the weather sample joined to each lap.")
show_fig(plot_correlation_heatmap(correlation_matrix(laps)))

pace = valid_pace(laps)
outliers = pace.loc[pace["IsPaceOutlier"]] if "IsPaceOutlier" in pace.columns else pace.iloc[0:0]
st.metric("Per-driver IQR outliers", int(len(outliers)))
if not outliers.empty:
    columns = [
        column for column in ("Driver", "LapNumber", "LapTime_s", "Compound", "TyreLife")
        if column in outliers.columns
    ]
    table = outliers[columns].copy()
    if "LapTime_s" in table.columns:
        table["LapTime_s"] = table["LapTime_s"].map(format_seconds)
    show_table(table, hide_index=True)
