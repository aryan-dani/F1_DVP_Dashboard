"""Weekend schedule, weather, and race-control messages."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st

from src.state import configure_page, get_bundle, show_fig
from src.viz import plot_weather

configure_page("Weekend overview")

session, tables, _drivers = get_bundle()
event = session.event
meta = tables["meta"].iloc[0].to_dict() if not tables["meta"].empty else {}

st.title("Weekend overview")
st.caption(
    f"{meta.get('event_name')} ({meta.get('year')}) — {meta.get('event_format')} format"
)

schedule_rows = []
for i in range(1, 6):
    name = event.get(f"Session{i}")
    if not isinstance(name, str) or not name:
        continue
    schedule_rows.append({
        "Session": name,
        "Local start": str(event.get(f"Session{i}Date", "")),
        "UTC start": str(event.get(f"Session{i}DateUtc", "")),
    })
st.subheader("Session timetable")
st.dataframe(pd.DataFrame(schedule_rows), width="stretch", hide_index=True)

left, right = st.columns(2)
with left:
    st.subheader("Event")
    st.dataframe(
        pd.DataFrame({
            "Field": [
                "Round", "Country", "Location", "Official name", "F1 API support",
            ],
            "Value": [
                str(meta.get("round")),
                str(meta.get("country")),
                str(meta.get("location")),
                str(meta.get("official_name")),
                str(meta.get("f1_api_support")),
            ],
        }),
        width="stretch",
        hide_index=True,
    )

with right:
    st.subheader("Weather")
    show_fig(plot_weather(tables["weather"]))

st.subheader("Race control messages")
rcm = tables["rcm"]
if rcm.empty:
    st.write("No race-control messages for this session.")
else:
    show_cols = [c for c in rcm.columns if c != "Time"]
    st.dataframe(
        rcm[show_cols].astype(str),
        width="stretch",
        hide_index=True,
        height=360,
    )
