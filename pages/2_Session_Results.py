"""Classified results plus position changes or qualifying bars."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st

from src.constants import QUALI_LIKE, RACE_LIKE
from src.state import configure_page, get_bundle, show_fig
from src.viz import format_seconds, plot_position_changes, plot_quali_times

configure_page("Session results")

session, tables, _drivers = get_bundle()
results = tables["results"].copy()
laps = tables["laps"]

st.title(f"Session results — {session.name}")

if results.empty:
    st.warning("No result table for this session.")
    st.stop()

display = results.copy()
for src, dst in (
    ("Q1_s", "Q1"),
    ("Q2_s", "Q2"),
    ("Q3_s", "Q3"),
    ("Time_s", "Time"),
):
    if src in display.columns:
        display[dst] = display[src].map(format_seconds)

keep = [
    c for c in [
        "Position", "ClassifiedPosition", "Abbreviation", "FullName", "TeamName",
        "GridPosition", "Q1", "Q2", "Q3", "Time", "Status", "Points", "Laps",
    ] if c in display.columns
]
st.dataframe(
    display[keep].sort_values("Position", na_position="last"),
    width="stretch",
    hide_index=True,
)

if session.name in RACE_LIKE:
    st.subheader("Position changes")
    show_fig(plot_position_changes(laps, session))
elif session.name in QUALI_LIKE:
    st.subheader("Best qualifying lap")
    show_fig(plot_quali_times(results, session))
elif "Time_s" in results.columns and results["Time_s"].notna().any():
    plot_df = results.dropna(subset=["Time_s"]).sort_values("Time_s")
    st.subheader("Best lap (practice)")
    st.bar_chart(
        pd.Series(
            plot_df["Time_s"].to_numpy(),
            index=plot_df["Abbreviation"].astype(str),
            name="Best lap (s)",
        )
    )
