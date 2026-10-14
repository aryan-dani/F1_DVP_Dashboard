"""Loaded-weekend scoreboard."""

import streamlit as st

from src.eda import valid_pace
from src.insights import story_metrics
from src.state import get_bundle
from src.theme import format_seconds


bundle = get_bundle()
session = bundle.session
tables = bundle.tables
laps = tables["laps"]
results = tables["results"]
story = story_metrics(laps, results, tables["weather"], session.name)

st.title("Race weekend")
st.caption("Scoreboard for the loaded session. Open a chart page for the story behind the numbers.")

if story["session_kind"] == "race":
    columns = st.columns(5)
    columns[0].metric(story["leader_label"], story["leader"] or "—")
    columns[1].metric(
        "Fastest lap",
        f"{story['fastest_driver']}  {format_seconds(story['fastest_time'])}"
        if story["fastest_driver"] else "—",
    )
    columns[2].metric("Lead changes", story["lead_changes"] if story["lead_changes"] is not None else "—")
    columns[3].metric("SC / VSC laps", story["sc_laps"] if story["sc_laps"] is not None else "—")
    columns[4].metric("Conditions", story["conditions"])
    places = story["places"]
    if not places.empty and "Abbreviation" in places.columns:
        best = places.sort_values("PlacesGained", ascending=False).iloc[0]
        gained = int(best["PlacesGained"])
        if gained > 0:
            st.caption(
                f"Biggest climb: {best['Abbreviation']} gained {gained} "
                f"places from the grid."
            )
elif story["session_kind"] == "qualifying":
    columns = st.columns(3)
    columns[0].metric("Pole", story["leader"] or "—")
    columns[1].metric(
        "Fastest lap",
        f"{story['fastest_driver']}  {format_seconds(story['fastest_time'])}"
        if story["fastest_driver"] else "—",
    )
    columns[2].metric("Conditions", story["conditions"])
else:
    columns = st.columns(3)
    columns[0].metric(
        "Fastest lap",
        f"{story['fastest_driver']}  {format_seconds(story['fastest_time'])}"
        if story["fastest_driver"] else "—",
    )
    columns[1].metric("Valid pace laps", f"{len(valid_pace(laps)):,}")
    columns[2].metric("Conditions", story["conditions"])

st.subheader("Open")
link_row = st.columns(3)
with link_row[0]:
    st.page_link("src/views/results.py", label="Results")
with link_row[1]:
    st.page_link("src/views/strategy.py", label="Strategy")
with link_row[2]:
    st.page_link("src/views/compare.py", label="Compare")

with st.expander("Where the data comes from"):
    st.markdown(
        """
There is **no static CSV** in this project. FastF1 downloads a session on
first load, then reuses `.fastf1_cache/` and a Parquet snapshot in
`data/processed/`.

| What you see | Source |
| --- | --- |
| Lap times, tyres, weather, race control, telemetry | F1 live-timing archive (`livetiming.formula1.com`, FastF1 mirror fallback) |
| Results, calendar, season standings | Jolpica-F1 (`api.jolpi.ca/ergast/f1`) |
| Weekend schedule | FastF1 schedule JSON, with timing and Jolpica fallbacks |
| Corner markers | MultiViewer circuit data via FastF1 |

Timing and telemetry start in **2018**. The season page reads Jolpica
standings only, so it does not download every race weekend.

1. **Fetch** — `fastf1.get_session` + `session.load()`
2. **Preprocess** — seconds, track status, valid-pace flags, stints, outliers
3. **Snapshot** — Parquet under `data/processed/`
4. **Charts** — Plotly on the pages in the sidebar. Click a legend entry to isolate that driver.
"""
    )

meta = tables["meta"].iloc[0].to_dict() if not tables["meta"].empty else {}
st.caption(
    f"{len(laps):,} lap rows · {len(valid_pace(laps)):,} valid pace · "
    f"{len(results):,} classified rows · "
    f"{meta.get('event_format', '')} format"
)
if laps.empty:
    st.warning("This session has no lap rows yet.")
