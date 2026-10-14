"""Tyre stints, degradation slope, and safety-car bands."""

import pandas as pd
import streamlit as st

from src.charts import plot_stint_pace, plot_strategy
from src.insights import track_status_phases
from src.state import get_bundle, show_fig, show_table
from src.theme import format_seconds


bundle = get_bundle()
session = bundle.session
stints = bundle.view["stints"]
phases = track_status_phases(bundle.tables["laps"])

st.title("Strategy")
st.caption("Each bar is a stint in that driver's compound colour. Shaded bands are yellow, safety-car, or red-flag laps.")
if bundle.filters["narrowed"]:
    st.caption("Stints follow the sidebar filters.")

if stints.empty:
    st.warning("No stint information in the current slice.")
    st.stop()

show_fig(plot_strategy(stints, session, phases=phases))

st.subheader("Stint length versus mean pace")
st.caption("Further right is a longer stint. Lower is a quicker average valid lap.")
show_fig(plot_stint_pace(stints, session))

st.subheader("Stints")
table = stints.copy()
if "MeanPace_s" in table.columns:
    table["Mean pace"] = table["MeanPace_s"].map(format_seconds)
if "DegSlope_s" in table.columns:
    table["Degradation (s/lap)"] = table["DegSlope_s"].map(
        lambda value: "—" if pd.isna(value) else f"{float(value):+.3f}"
    )
show_cols = [
    column for column in (
        "Driver", "Team", "Stint", "Compound", "StintStart", "StintEnd",
        "StintLength", "Mean pace", "Degradation (s/lap)",
    ) if column in table.columns
]
show_table(table[show_cols], hide_index=True)
