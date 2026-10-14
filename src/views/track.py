"""Speed or gear coloured track map for one highlighted driver."""

import streamlit as st

from src.charts import plot_track_map
from src.data_loader import circuit_corners, fastest_lap_map_data
from src.state import get_bundle, show_fig


bundle = get_bundle(telemetry=True)
session = bundle.session
drivers = bundle.drivers

st.title("Track map")
st.caption("X/Y come from the position stream. Corner numbers are MultiViewer markers, not a surveyed centre line.")

if not drivers:
    st.warning("Pick a driver in the sidebar.")
    st.stop()

controls = st.columns(2)
driver = controls[0].selectbox("Driver", drivers, index=0)
channel = controls[1].radio("Colour", ("Speed", "Gear"), horizontal=True)
color_col = "Speed" if channel == "Speed" else "nGear"

telemetry = fastest_lap_map_data(session, driver)
if telemetry.empty:
    st.error(f"No map telemetry for {driver}. Try another driver or session.")
    st.stop()
if color_col not in telemetry.columns:
    st.error(f"{channel} is not in this lap's telemetry.")
    st.stop()

show_fig(plot_track_map(
    telemetry,
    driver,
    channel=color_col,
    label=channel,
    corners=circuit_corners(session),
))
