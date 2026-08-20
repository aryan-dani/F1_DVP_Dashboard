"""Speed-colored track map from merged position + car telemetry."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from src.data_loader import circuit_corners, fastest_lap_map_data
from src.state import configure_page, get_bundle, show_fig
from src.viz import plot_track_map

configure_page("Track map")

session, tables, drivers = get_bundle(telemetry=True)

st.title("Track map")
st.caption(
    "X/Y come from the live-timing position stream; colour is speed. "
    "Corner numbers are MultiViewer circuit markers (not GPS-survey grade)."
)

if not drivers:
    st.warning("Pick a driver in the sidebar.")
    st.stop()

driver = drivers[0]
tel = fastest_lap_map_data(session, driver)
if tel.empty:
    st.error(f"No map telemetry for {driver}. Try another driver or session.")
    st.stop()

corners = circuit_corners(session)
show_fig(plot_track_map(tel, driver, corners=corners))

if len(drivers) > 1:
    st.caption(
        f"Showing {driver} (first selected driver). "
        "Change the sidebar order to plot someone else."
    )
