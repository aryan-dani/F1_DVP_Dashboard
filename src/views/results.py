"""Classified results, gaps, qualifying segments, and practice pace."""

import pandas as pd
import streamlit as st

from src.charts import (
    plot_gap_to_leader,
    plot_intervals,
    plot_places,
    plot_position_changes,
    plot_practice_pace,
    plot_quali_segments,
)
from src.constants import QUALI_LIKE, RACE_LIKE
from src.data_loader import session_key
from src.insights import places_gained, practice_split, qualifying_progression
from src.state import get_bundle, show_fig, show_table
from src.theme import format_seconds


bundle = get_bundle()
session = bundle.session
view = bundle.view
results = view["results"].copy()
laps = view["laps"]

st.title("Results")
if bundle.filters["narrowed"]:
    st.caption("Charts and the table follow the sidebar filters.")

if results.empty:
    st.warning("No classified rows in the current slice.")
else:
    display = results.copy()
    for source, dest in (("Q1_s", "Q1"), ("Q2_s", "Q2"), ("Q3_s", "Q3"), ("Time_s", "Time")):
        if source in display.columns:
            display[dest] = display[source].map(format_seconds)
    keep = [
        column for column in (
            "Position", "ClassifiedPosition", "Abbreviation", "FullName", "TeamName",
            "GridPosition", "Q1", "Q2", "Q3", "Time", "Status", "Points", "Laps",
        ) if column in display.columns
    ]
    ordered = display[keep]
    if "Position" in ordered.columns:
        ordered = ordered.assign(_pos=pd.to_numeric(ordered["Position"], errors="coerce"))
        ordered = ordered.sort_values("_pos", na_position="last").drop(columns="_pos")
    show_table(ordered, hide_index=True)
    meta = bundle.tables["meta"]
    year = int(meta.iloc[0]["year"]) if not meta.empty else 0
    event_name = str(meta.iloc[0]["event_name"]) if not meta.empty else session.name
    filename = f"{session_key(year, event_name, session.name)}_results.csv"
    st.download_button(
        "Download results CSV",
        ordered.to_csv(index=False).encode("utf-8"),
        file_name=filename,
        mime="text/csv",
    )

if session.name in RACE_LIKE:
    st.subheader("Position")
    st.caption("The leader sits at the top. A line that climbs the chart is a car making ground.")
    show_fig(plot_position_changes(laps, session))
    st.subheader("Gap to leader")
    st.caption("Each point is session time at the end of the lap, minus the leader on that lap.")
    show_fig(plot_gap_to_leader(laps, session))
    st.subheader("Interval")
    st.caption("Gap to the car one position ahead. The leader has no interval.")
    show_fig(plot_intervals(laps, session))
    gained = places_gained(results)
    if not gained.empty:
        st.subheader("Grid to finish")
        st.caption("Positive is places gained. A pit-lane start uses grid position 0 when that is how the result is filed.")
        show_fig(plot_places(gained, session))
elif session.name in QUALI_LIKE:
    st.subheader("Segments")
    st.caption("Q3 is the pole shootout. Drivers with no Q2 or Q3 bar dropped out in the earlier segment.")
    progression = qualifying_progression(results)
    show_fig(plot_quali_segments(results, session))
    if not progression.empty and "Reached" in progression.columns:
        cols = [column for column in ("Abbreviation", "TeamName", "Reached", "Q1_s", "Q2_s", "Q3_s") if column in progression.columns]
        show = progression[cols].copy()
        for column in ("Q1_s", "Q2_s", "Q3_s"):
            if column in show.columns:
                show[column] = show[column].map(format_seconds)
        show_table(show, hide_index=True)
else:
    st.subheader("One-lap pace and the long run")
    st.caption("Short run is the best of each driver's fastest three valid laps. Long run is the mean of the laps after those.")
    show_fig(plot_practice_pace(practice_split(laps), session))
