"""Home page: data sources, load a race weekend, show preprocess counts."""

from src.constants import QUALI_LIKE, RACE_LIKE
from src.eda import valid_pace
from src.state import configure_page, get_bundle
from src.viz import format_seconds

import streamlit as st

configure_page("Home")

session, tables, _drivers = get_bundle()
meta = tables["meta"].iloc[0].to_dict() if not tables["meta"].empty else {}
laps = tables["laps"]
results = tables["results"]

st.title("Formula 1 race-weekend dashboard")
st.caption(
    "Data visualization with Python (DVP) — Streamlit + matplotlib/seaborn + FastF1"
)

st.markdown(
    f"**{meta.get('official_name') or meta.get('event_name', '')}**  \n"
    f"{meta.get('session_name', '')} · Round {meta.get('round', '—')} · "
    f"{meta.get('location', '')}, {meta.get('country', '')} · "
    f"{meta.get('session_date_utc', '')}"
)

st.header("Where the data comes from")
st.markdown(
    """
There is **no static CSV bundled with FastF1**. This dashboard calls FastF1,
which is an API client. On first load it downloads session files; afterwards
it reuses FastF1's local cache and a processed Parquet snapshot.

| What you see | Source | Protocol |
| --- | --- | --- |
| Lap times, tyres, weather, race control, telemetry | F1 live-timing archive (`livetiming.formula1.com`, FastF1 mirror fallback) | HTTP JSON / jsonStream (car and position streams are zlib-compressed) |
| Results, historical calendar, standings | Jolpica-F1 (`api.jolpi.ca/ergast/f1`, Ergast-compatible) | HTTP JSON |
| Weekend schedule and local start times | FastF1 schedule JSON on GitHub, F1 timing / Jolpica as fallback | HTTP JSON |
| Corner markers on the track map | MultiViewer circuit data via FastF1 `mvapi` | HTTP JSON |

Timing and telemetry exist from **2018** onward. Older seasons can still
supply results through Jolpica, but this app stays on 2018+ so EDA has
lap-level data.
"""
)

st.header("Pipeline")
st.markdown(
    """
1. **Fetch** — `fastf1.get_session` + `session.load()`
2. **Preprocess** — timedeltas to seconds, track-status labels, valid-pace flags, stints, IQR outliers
3. **Snapshot** — Parquet under `dashboard/data/processed/`
4. **EDA / viz** — the pages in the sidebar
"""
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Laps (raw rows)", f"{len(laps):,}")
c2.metric("Valid pace laps", f"{len(valid_pace(laps)):,}")
c3.metric("Drivers", f"{laps['Driver'].nunique() if not laps.empty else 0}")
c4.metric("Results rows", f"{len(results):,}")

if not laps.empty and "IsValidPace" in laps.columns and laps["IsValidPace"].any():
    row = laps.loc[laps.loc[laps["IsValidPace"], "LapTime_s"].idxmin()]
    st.metric(
        "Fastest valid lap",
        f"{row['Driver']}  {format_seconds(row['LapTime_s'])}",
        help="Fastest accurate, non-deleted, non-box lap after preprocessing.",
    )

st.subheader("Processed tables")
st.write(
    {
        "laps columns": (
            list(laps.columns[:12]) + ["…"]
            if len(laps.columns) > 12
            else list(laps.columns)
        ),
        "stints": len(tables["stints"]),
        "weather samples": len(tables["weather"]),
        "race control messages": len(tables["rcm"]),
        "session type": (
            "race-like" if session.name in RACE_LIKE
            else "qualifying-like" if session.name in QUALI_LIKE
            else session.name
        ),
    }
)

st.info(
    "Use the pages on the left: weekend overview, results, EDA, lap times, "
    "strategy, telemetry, and track map."
)
