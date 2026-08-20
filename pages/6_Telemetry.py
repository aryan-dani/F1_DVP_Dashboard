"""Fastest-lap car telemetry overlay for one or two drivers."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from src.data_loader import fastest_lap_car_data
from src.state import configure_page, get_bundle, show_fig
from src.viz import plot_telemetry_overlay

configure_page("Telemetry")

session, tables, drivers = get_bundle(telemetry=True)

st.title("Telemetry")
st.caption(
    "Car data (Speed, Throttle, Brake) from the F1 live-timing `CarData.z` "
    "stream. Distance is integrated from speed. Two-driver overlays use FastF1 "
    "team colours and line styles."
)

if not drivers:
    st.warning("Pick at least one driver in the sidebar.")
    st.stop()

chosen = drivers[:2]
traces = {}
missing = []
for drv in chosen:
    tel = fastest_lap_car_data(session, drv)
    if tel.empty:
        missing.append(drv)
    else:
        traces[drv] = tel

if missing:
    st.warning("No fastest-lap car data for: " + ", ".join(missing))
if not traces:
    st.stop()

show_fig(plot_telemetry_overlay(traces, session))

st.markdown(
    "**Drivers shown:** "
    + ", ".join(traces.keys())
    + " — each trace is that driver's fastest lap, not a race-average."
)
