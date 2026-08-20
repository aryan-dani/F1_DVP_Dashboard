"""Valid-pace lap time traces and the session's fastest lap."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from src.eda import fastest_lap_row, valid_pace
from src.state import configure_page, get_bundle, show_fig
from src.viz import format_seconds, plot_lap_trace, plot_laptimes_by_driver

configure_page("Lap times")

session, tables, drivers = get_bundle()
laps = tables["laps"]

st.title("Lap times")

row = fastest_lap_row(laps)
if row is not None:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Fastest driver", str(row["Driver"]))
    c2.metric("Lap time", format_seconds(row["LapTime_s"]))
    c3.metric("Lap number", int(row["LapNumber"]))
    c4.metric("Compound", str(row.get("Compound", "—")))

pace = valid_pace(laps)
st.caption(
    f"{len(pace)} valid-pace laps "
    "(inaccurate, deleted, and box laps are excluded from the traces)."
)

st.subheader("Race / session trace")
show_fig(plot_lap_trace(laps, session, drivers=drivers or None))

st.subheader("Distribution by driver")
show_fig(plot_laptimes_by_driver(laps, session))

if not pace.empty:
    st.subheader("Valid-pace table")
    cols = [
        c for c in [
            "Driver", "LapNumber", "Stint", "Compound", "TyreLife",
            "LapTime_s", "Sector1_s", "Sector2_s", "Sector3_s",
            "GapToFastest_s", "PaceDelta_s", "TrackStatusLabel", "IsPaceOutlier",
        ] if c in pace.columns
    ]
    st.dataframe(
        pace[cols].sort_values(["Driver", "LapNumber"]),
        width="stretch",
        hide_index=True,
        height=360,
    )
