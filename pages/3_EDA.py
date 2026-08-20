"""Missingness, distributions, correlations, lap categories."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from src.eda import (
    category_counts,
    correlation_matrix,
    missingness,
    numeric_describe,
    valid_pace,
)
from src.state import configure_page, get_bundle, show_fig
from src.viz import (
    plot_category_counts,
    plot_correlation_heatmap,
    plot_laptime_distribution,
    plot_laptimes_by_driver,
    plot_missingness,
)

configure_page("EDA")

session, tables, _drivers = get_bundle()
laps = tables["laps"]

st.title("Exploratory data analysis")
st.markdown(
    """
Preprocessing already converted API timedeltas to seconds, labelled track
status, and flagged **valid pace** laps (accurate, not deleted, not in/out
laps, with a lap time). EDA below is computed on that processed table.
"""
)

if laps.empty:
    st.warning("No lap rows to analyse.")
    st.stop()

st.subheader("Missing values")
miss = missingness(laps)
show_fig(plot_missingness(miss))
with st.expander("Missingness table"):
    st.dataframe(miss, width="stretch", hide_index=True)

st.subheader("Lap categories")
counts = category_counts(laps)
c1, c2 = st.columns([1, 2])
with c1:
    st.dataframe(counts, width="stretch", hide_index=True)
with c2:
    show_fig(plot_category_counts(counts))

st.subheader("Numeric summary (valid pace)")
pace = valid_pace(laps)
st.dataframe(numeric_describe(pace), width="stretch")

st.subheader("Lap time distribution")
show_fig(plot_laptime_distribution(laps))

st.subheader("Spread by driver")
show_fig(plot_laptimes_by_driver(laps, session))

st.subheader("Correlations")
st.caption(
    "Pearson correlation on valid-pace laps: lap time, sectors, speed traps, "
    "tyre life, and weather columns joined per lap."
)
corr = correlation_matrix(laps)
show_fig(plot_correlation_heatmap(corr))

n_out = int(pace["IsPaceOutlier"].sum()) if "IsPaceOutlier" in pace.columns else 0
st.metric("Per-driver IQR outliers (valid pace)", n_out)
if n_out:
    cols = [
        c for c in ["Driver", "LapNumber", "LapTime_s", "Compound", "TyreLife"]
        if c in pace.columns
    ]
    st.dataframe(
        pace.loc[pace["IsPaceOutlier"], cols],
        width="stretch",
        hide_index=True,
    )
