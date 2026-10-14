"""Fastest-lap channels and the delta to a reference lap."""

import streamlit as st

from src.charts import plot_lap_delta, plot_telemetry
from src.data_loader import circuit_corners, fastest_lap_car_data, fastest_lap_delta
from src.insights import faster_driver
from src.state import get_bundle, show_fig


bundle = get_bundle(telemetry=True)
session = bundle.session
chosen = list(bundle.drivers[:2])

st.title("Telemetry")
st.caption("Each trace is that driver's fastest lap. Click a name in the legend to isolate them. Corner ticks sit on the speed trace.")

if not chosen:
    st.warning("Pick at least one driver in the sidebar.")
    st.stop()

traces = {}
missing = []
for driver in chosen:
    telemetry = fastest_lap_car_data(session, driver)
    if telemetry.empty:
        missing.append(driver)
    else:
        traces[driver] = telemetry

if missing:
    st.warning("No fastest-lap car data for: " + ", ".join(missing))
if not traces:
    st.stop()

show_fig(plot_telemetry(traces, session, corners=circuit_corners(session)))

if len(chosen) >= 2 and chosen[0] in traces and chosen[1] in traces:
    reference, other = faster_driver(bundle.tables["laps"], chosen[0], chosen[1])
    st.subheader("Delta to the faster lap")
    st.caption(f"Positive means {other} is slower than {reference} at that point on the lap. The reference is whichever of the two has the quicker valid lap.")
    delta = fastest_lap_delta(session, reference, other)
    if delta is None:
        st.info("FastF1 could not build a delta for these two laps.")
    else:
        series, reference_telemetry, _compare_telemetry = delta
        show_fig(plot_lap_delta(series, reference_telemetry, reference, other))
