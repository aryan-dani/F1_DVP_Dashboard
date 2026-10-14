"""Weekend timetable, weather, track status, and race control."""

import pandas as pd
import streamlit as st

from src.charts import plot_status_timeline, plot_weather
from src.insights import race_control_highlights, track_status_phases
from src.state import get_bundle, show_fig, show_table


def _short_time(value) -> str:
    text = str(value).replace("T", " ")
    return text[:16] if text and text != "None" else "—"


bundle = get_bundle()
session = bundle.session
tables = bundle.tables
event = session.event
meta = tables["meta"].iloc[0].to_dict() if not tables["meta"].empty else {}

st.title("Weekend")
st.caption(str(meta.get("official_name") or meta.get("event_format") or ""))

schedule_rows = []
for index in range(1, 6):
    name = event.get(f"Session{index}")
    if not isinstance(name, str) or not name:
        continue
    schedule_rows.append({
        "Session": name,
        "Local start": _short_time(event.get(f"Session{index}Date", "")),
    })

if schedule_rows:
    st.subheader("Sessions")
    cards = st.columns(len(schedule_rows))
    for card, row in zip(cards, schedule_rows):
        card.metric(row["Session"], row["Local start"])

left, right = st.columns(2)
with left:
    st.subheader("Event")
    show_table(
        pd.DataFrame({
            "Field": ["Round", "Country", "Location", "Official name"],
            "Value": [
                str(meta.get("round")),
                str(meta.get("country")),
                str(meta.get("location")),
                str(meta.get("official_name")),
            ],
        }),
        hide_index=True,
    )
with right:
    st.subheader("Weather")
    show_fig(plot_weather(tables["weather"]))

st.subheader("Track status")
phases = track_status_phases(tables["laps"])
show_fig(plot_status_timeline(phases))
if not phases.empty:
    flagged = phases.loc[~phases["Status"].astype(str).str.fullmatch("Green", case=False)]
    if not flagged.empty:
        show_table(flagged, hide_index=True)

st.subheader("Race control")
rcm = tables["rcm"]
highlights = race_control_highlights(rcm)
if highlights.empty:
    st.write("No flags, penalties, or safety-car messages for this session.")
else:
    show_cols = [column for column in ("Lap", "Flag", "Category", "Message", "Status") if column in highlights.columns]
    show_table(highlights[show_cols].astype(str), hide_index=True, height=320)
with st.expander("All race-control messages"):
    if rcm.empty:
        st.write("No race-control messages for this session.")
    else:
        show_cols = [column for column in rcm.columns if column != "Time"]
        show_table(rcm[show_cols].astype(str), hide_index=True, height=360)
