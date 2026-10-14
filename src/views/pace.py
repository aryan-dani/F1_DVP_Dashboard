"""Pace traces, sectors, and tyre degradation."""

import streamlit as st

from src.charts import (
    plot_degradation,
    plot_lap_trace,
    plot_laptimes_by_driver,
    plot_sectors,
)
from src.eda import fastest_lap_row, valid_pace
from src.insights import sector_summary
from src.state import get_bundle, show_fig, show_table
from src.theme import format_seconds


bundle = get_bundle()
session = bundle.session
laps = bundle.view["laps"]
drivers = bundle.drivers

st.title("Pace")
if bundle.filters["narrowed"]:
    st.caption("This page uses the sidebar filters.")

row = fastest_lap_row(laps)
if row is not None:
    cards = st.columns(4)
    cards[0].metric("Fastest driver", str(row["Driver"]))
    cards[1].metric("Lap time", format_seconds(row["LapTime_s"]))
    cards[2].metric("Lap", int(row["LapNumber"]))
    cards[3].metric("Compound", str(row.get("Compound", "—")))

pace = valid_pace(laps)
st.caption(f"{len(pace)} valid-pace laps in this slice. Inaccurate, deleted, and box laps stay out of the traces.")

st.subheader("Lap trace")
st.caption("A rising line is degradation or traffic. A sudden drop is usually a new tyre or a clear lap.")
show_fig(plot_lap_trace(laps, session, drivers=drivers or None))

st.subheader("Spread")
st.caption("The box is the middle half of valid laps. A low, tight box is consistent pace.")
show_fig(plot_laptimes_by_driver(laps, session))

st.subheader("Sectors")
st.caption("Shorter bars are quicker. Compare drivers inside one sector, not across sectors.")
show_fig(plot_sectors(sector_summary(laps), session))

st.subheader("Degradation")
st.caption("Each line is one stint for a highlighted driver. A steep rise is a tyre falling away, in seconds per lap.")
show_fig(plot_degradation(laps, session, drivers=drivers or None))

if not pace.empty:
    st.subheader("Valid-pace laps")
    columns = [
        column for column in (
            "Driver", "LapNumber", "Stint", "Compound", "TyreLife",
            "LapTime_s", "Sector1_s", "Sector2_s", "Sector3_s",
            "GapToLeader_s", "Interval_s", "GapToFastest_s", "TrackStatusLabel",
        ) if column in pace.columns
    ]
    table = pace[columns].sort_values(["Driver", "LapNumber"]).copy()
    for column in ("LapTime_s", "Sector1_s", "Sector2_s", "Sector3_s", "GapToLeader_s", "Interval_s", "GapToFastest_s"):
        if column in table.columns:
            table[column] = table[column].map(format_seconds)
    show_table(table, hide_index=True, height=360)
