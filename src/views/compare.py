"""Two-driver comparison on the loaded session."""

import pandas as pd
import streamlit as st

from src.charts import plot_lap_delta, plot_lap_trace, plot_strategy
from src.data_loader import fastest_lap_delta
from src.eda import driver_list, valid_pace
from src.insights import faster_driver, places_gained, sector_summary, track_status_phases
from src.state import get_bundle, show_fig, show_table
from src.theme import format_seconds, format_signed_seconds


def _best(summary: pd.DataFrame, driver: str, column: str):
    if summary.empty or column not in summary.columns:
        return None
    rows = summary.loc[summary["Driver"].astype(str) == driver, column]
    if rows.empty or rows.isna().all():
        return None
    return float(rows.iloc[0])


bundle = get_bundle(telemetry=True)
session = bundle.session
options = driver_list(bundle.tables["laps"], bundle.tables["results"])
if len(options) < 2:
    st.title("Compare")
    st.warning("This session needs two drivers to compare.")
    st.stop()

default_a = bundle.drivers[0] if bundle.drivers else options[0]
default_b = bundle.drivers[1] if len(bundle.drivers) > 1 else options[1]
if default_a == default_b:
    default_b = next(driver for driver in options if driver != default_a)

st.title("Compare")
st.caption("Both drivers come from the loaded session. Pace and stints follow the sidebar filters.")

picks = st.columns(2)
first = picks[0].selectbox("Driver A", options, index=options.index(default_a))
second_options = [driver for driver in options if driver != first] or options
second_index = second_options.index(default_b) if default_b in second_options else 0
second = picks[1].selectbox("Driver B", second_options, index=second_index)

laps = bundle.view["laps"]
pace = valid_pace(laps)
pace = pace.loc[pace["Driver"].astype(str).isin([first, second])] if not pace.empty else pace
summary = sector_summary(pace if not pace.empty else laps)
results = bundle.tables["results"]
gained = places_gained(results)

def _pace_mean(driver: str):
    if pace.empty:
        return None
    values = pace.loc[pace["Driver"].astype(str) == driver, "LapTime_s"]
    if values.empty:
        return None
    return float(values.mean())


def _fastest(driver: str):
    source = valid_pace(bundle.tables["laps"])
    if source.empty:
        return None
    values = source.loc[source["Driver"].astype(str) == driver, "LapTime_s"]
    if values.empty:
        return None
    return float(values.min())


def _places(driver: str):
    if gained.empty or "Abbreviation" not in gained.columns:
        return None
    rows = gained.loc[gained["Abbreviation"].astype(str) == driver, "PlacesGained"]
    if rows.empty:
        return None
    return int(rows.iloc[0])


mean_a, mean_b = _pace_mean(first), _pace_mean(second)
fast_a, fast_b = _fastest(first), _fastest(second)
cards = st.columns(4)
if mean_a is not None and mean_b is not None:
    cards[0].metric("Mean pace gap", format_signed_seconds(mean_a - mean_b), help=f"{first} minus {second}. Negative means {first} is quicker.")
else:
    cards[0].metric("Mean pace gap", "—")
if fast_a is not None and fast_b is not None:
    cards[1].metric("Fastest-lap gap", format_signed_seconds(fast_a - fast_b))
else:
    cards[1].metric("Fastest-lap gap", "—")
cards[2].metric(f"{first} places", "—" if _places(first) is None else f"{_places(first):+d}")
cards[3].metric(f"{second} places", "—" if _places(second) is None else f"{_places(second):+d}")

sector_rows = []
for label, column in (("Sector 1", "BestS1"), ("Sector 2", "BestS2"), ("Sector 3", "BestS3")):
    best_a = _best(summary, first, column)
    best_b = _best(summary, second, column)
    delta = None if best_a is None or best_b is None else best_a - best_b
    sector_rows.append({
        "Sector": label,
        first: format_seconds(best_a),
        second: format_seconds(best_b),
        f"{first} − {second}": format_signed_seconds(delta),
    })
show_table(pd.DataFrame(sector_rows), hide_index=True)
st.caption(f"Sector delta is {first} minus {second} on each driver's best valid sector. Negative means {first} is quicker.")

st.subheader("Pace")
st.caption("Overlay of valid laps in the current slice.")
show_fig(plot_lap_trace(laps, session, drivers=[first, second]))

st.subheader("Stints")
stints = bundle.view["stints"]
if not stints.empty and "Driver" in stints.columns:
    stints = stints.loc[stints["Driver"].astype(str).isin([first, second])]
show_fig(plot_strategy(stints, session, phases=track_status_phases(bundle.tables["laps"])))

st.subheader("Fastest-lap delta")
reference, other = faster_driver(bundle.tables["laps"], first, second)
st.caption(f"Reference is {reference}, the faster valid lap of the two. Positive means {other} is behind at that distance.")
delta = fastest_lap_delta(session, reference, other)
if delta is None:
    st.info("FastF1 could not build a delta for these two laps.")
else:
    series, reference_telemetry, _compare_telemetry = delta
    show_fig(plot_lap_delta(series, reference_telemetry, reference, other))
