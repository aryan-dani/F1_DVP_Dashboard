"""Shared Streamlit shell: sidebar, caching, filters, and chart display."""

from __future__ import annotations

import unicodedata
from typing import NamedTuple

import pandas as pd
import streamlit as st

from src.constants import (
    DEFAULT_EVENT,
    DEFAULT_SESSION,
    DEFAULT_YEAR,
    MAX_YEAR,
    MIN_YEAR,
)
from src.data_loader import (
    event_sessions,
    fetch_schedule,
    fetch_session,
    save_processed,
    session_key,
)
from src.eda import driver_list
from src.insights import enrich, weather_line
from src.preprocess import build_processed_tables


_CSS = """
<style>
[data-testid="stMetricValue"], [data-testid="stMetricDelta"] {
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
}
[data-testid="stMetric"] {
  background: #1A1A22;
  border: 1px solid #2C2C36;
  border-radius: 10px;
  padding: 0.7rem 0.85rem;
}
</style>
"""


class Bundle(NamedTuple):
    """Loaded session, the full tables, the filtered slice, and highlight drivers."""

    session: object
    tables: dict
    view: dict
    drivers: list
    filters: dict


def configure_page(title: str = "F1 Dashboard") -> None:
    """Must be the first Streamlit call in the entrypoint."""
    st.set_page_config(
        page_title=title,
        page_icon="🏁",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def inject_css() -> None:
    """Tabular timing figures and a little padding around metric cards."""
    st.markdown(_CSS, unsafe_allow_html=True)


def _supports_stretch_width() -> bool:
    """width='stretch' arrived in Streamlit 1.49. Earlier builds want a pixel count."""
    parts = []
    for piece in str(st.__version__).split("."):
        digits = ""
        for char in piece:
            if char.isdigit():
                digits += char
            else:
                break
        if not digits:
            break
        parts.append(int(digits))
    major = parts[0] if parts else 0
    minor = parts[1] if len(parts) > 1 else 0
    return (major, minor) >= (1, 49)


def show_fig(fig) -> None:
    """Render a Plotly figure across the content width."""
    if _supports_stretch_width():
        st.plotly_chart(fig, width="stretch")
    else:
        st.plotly_chart(fig, use_container_width=True)


def show_table(data, **kwargs) -> None:
    """Render a dataframe across the content width on Streamlit 1.40 and later."""
    if _supports_stretch_width():
        st.dataframe(data, width="stretch", **kwargs)
    else:
        st.dataframe(data, use_container_width=True, **kwargs)


@st.cache_data(show_spinner="Loading season calendar...")
def cached_schedule(year: int):
    return fetch_schedule(year)


@st.cache_resource(show_spinner="Fetching session from FastF1 APIs...")
def cached_session(year: int, gp: str, identifier: str, telemetry: bool):
    return fetch_session(year, gp, identifier, telemetry=telemetry)


@st.cache_data(show_spinner="Preprocessing and saving parquet snapshot...")
def cached_tables(year: int, gp: str, identifier: str):
    session = cached_session(year, gp, identifier, False)
    tables = build_processed_tables(session)
    save_processed(session_key(year, gp, identifier), tables)
    return tables


def _fold(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return ascii_text.casefold().strip()


def _match_event(name: str, events: list[str]) -> str | None:
    """Match a Jolpica race name to a FastF1 event, ignoring accents."""
    wanted = _fold(name)
    for event in events:
        if _fold(event) == wanted:
            return event
    return None


def _selection_signature(params) -> str:
    return "|".join((
        str(params.get("year", "")),
        str(params.get("gp", "")),
        str(params.get("session", "")),
    ))


def _init_selection() -> None:
    """Seed year, event, and session from the URL when it changes from outside."""
    params = st.query_params
    signature = _selection_signature(params)
    if (
        st.session_state.get("_selection_ready")
        and st.session_state.get("_url_sig") == signature
    ):
        return
    try:
        year = int(params.get("year", st.session_state.get("year", DEFAULT_YEAR)))
    except (TypeError, ValueError):
        year = DEFAULT_YEAR
    st.session_state["year"] = min(max(year, MIN_YEAR), MAX_YEAR)
    st.session_state["gp"] = str(params.get("gp", st.session_state.get("gp", DEFAULT_EVENT)))
    st.session_state["identifier"] = str(
        params.get("session", st.session_state.get("identifier", DEFAULT_SESSION))
    )
    st.session_state["_selection_ready"] = True
    st.session_state["_url_sig"] = signature


def _apply_pending_round() -> None:
    """Apply a season-page deep link before the sidebar widgets are built."""
    pending = st.session_state.pop("pending_round", None)
    if not pending:
        return
    st.session_state["year"] = int(pending["year"])
    st.session_state["gp"] = str(pending["gp"])
    st.session_state["identifier"] = str(pending.get("session", "Race"))
    st.session_state["_selection_ready"] = True


def render_sidebar():
    """Year, event, and session controls. Returns the selection and Load click."""
    _init_selection()
    _apply_pending_round()
    st.sidebar.title("F1 Dashboard")
    st.sidebar.caption("Pick a weekend, then load it. Changing the dropdown does not download.")

    # Value comes from session state, not a widget key. A keyed number input
    # resets to its minimum when the page changes, which would drop the loaded race.
    year = int(st.sidebar.number_input(
        "Year",
        min_value=MIN_YEAR,
        max_value=MAX_YEAR,
        value=int(st.session_state.get("year", DEFAULT_YEAR)),
        step=1,
    ))
    st.session_state["year"] = year
    try:
        schedule = cached_schedule(year)
    except Exception as exc:
        st.sidebar.error(str(exc))
        st.stop()

    events = schedule["EventName"].astype(str).tolist()
    if not events:
        st.sidebar.error("No Grands Prix listed for this season.")
        st.stop()
    stored_gp = str(st.session_state.get("gp", DEFAULT_EVENT))
    if stored_gp not in events:
        stored_gp = _match_event(stored_gp, events) or events[0]
    gp = st.sidebar.selectbox("Grand Prix", events, index=events.index(stored_gp))
    st.session_state["gp"] = gp

    sessions = event_sessions(schedule, gp)
    if not sessions:
        st.sidebar.error("No sessions listed for this event.")
        st.stop()
    stored_session = str(st.session_state.get("identifier", DEFAULT_SESSION))
    if stored_session not in sessions:
        stored_session = "Race" if "Race" in sessions else sessions[0]
    identifier = st.sidebar.selectbox(
        "Session",
        sessions,
        index=sessions.index(stored_session),
    )
    st.session_state["identifier"] = identifier

    clicked = st.sidebar.button("Load session", type="primary")
    st.query_params["year"] = str(year)
    st.query_params["gp"] = gp
    st.query_params["session"] = identifier
    st.session_state["_url_sig"] = f"{year}|{gp}|{identifier}"
    return year, gp, identifier, schedule, clicked


def _unique(frame: pd.DataFrame, column: str) -> list[str]:
    if frame.empty or column not in frame.columns:
        return []
    return sorted(frame[column].dropna().astype(str).unique().tolist())


def _ensure_filter_state(key: str, laps: pd.DataFrame) -> tuple[list[str], list[str], int, int]:
    teams = _unique(laps, "Team")
    compounds = _unique(laps, "Compound")
    numbers = pd.Series(dtype=float)
    if not laps.empty and "LapNumber" in laps.columns:
        numbers = pd.to_numeric(laps["LapNumber"], errors="coerce").dropna()
    if numbers.empty:
        lap_min, lap_max = 1, 1
    else:
        lap_min = int(numbers.min())
        lap_max = int(numbers.max())
    if st.session_state.get("filter_session") != key:
        st.session_state["filter_session"] = key
        st.session_state["filter_teams"] = teams
        st.session_state["filter_compounds"] = compounds
        st.session_state["filter_lap_range"] = (lap_min, lap_max)
        st.session_state["filter_valid"] = False
    return teams, compounds, lap_min, lap_max


def _as_lap_range(raw, lap_min: int, lap_max: int) -> tuple[int, int]:
    """Coerce a slider result into an inclusive lap pair.

    A range slider returns two numbers. A single-value slider, or a stale
    session value, returns one int.
    """
    if isinstance(raw, (tuple, list)) and len(raw) >= 2:
        lo, hi = int(raw[0]), int(raw[1])
    else:
        lo = hi = int(raw)
    lo = min(max(lo, lap_min), lap_max)
    hi = min(max(hi, lap_min), lap_max)
    if lo > hi:
        lo, hi = hi, lo
    return lo, hi


def render_slice_controls(tables: dict, key: str) -> dict:
    """Team, compound, lap range, and valid-pace filters for the loaded session."""
    laps = tables.get("laps", pd.DataFrame())
    teams, compounds, lap_min, lap_max = _ensure_filter_state(key, laps)
    st.sidebar.divider()
    selected_teams = st.sidebar.multiselect("Teams", teams, key="filter_teams") if teams else []
    selected_compounds = (
        st.sidebar.multiselect("Compounds", compounds, key="filter_compounds")
        if compounds else []
    )
    if lap_min < lap_max:
        stored = _as_lap_range(
            st.session_state.get("filter_lap_range", (lap_min, lap_max)),
            lap_min,
            lap_max,
        )
        # value= makes this a two-handle slider. A key alone is a single int.
        lap_range = _as_lap_range(
            st.sidebar.slider(
                "Lap range",
                min_value=lap_min,
                max_value=lap_max,
                value=stored,
            ),
            lap_min,
            lap_max,
        )
        st.session_state["filter_lap_range"] = lap_range
    else:
        lap_range = (lap_min, lap_max)
    valid_only = st.sidebar.toggle("Valid pace only", key="filter_valid")
    narrowed = (
        set(selected_teams) != set(teams)
        or set(selected_compounds) != set(compounds)
        or lap_range != (lap_min, lap_max)
        or bool(valid_only)
    )
    return {
        "teams": selected_teams,
        "compounds": selected_compounds,
        "all_teams": teams,
        "all_compounds": compounds,
        "lap_range": lap_range,
        "valid_only": bool(valid_only),
        "narrowed": narrowed,
    }


def slice_tables(tables: dict, filters: dict) -> dict:
    """Apply the shared sidebar slice to laps, overlapping stints, and results."""
    source_laps = tables.get("laps", pd.DataFrame())
    had_lap_drivers = (
        not source_laps.empty
        and "Driver" in source_laps.columns
        and source_laps["Driver"].notna().any()
    )
    laps = source_laps.copy()
    if not laps.empty:
        if filters["all_teams"] and "Team" in laps.columns:
            if not filters["teams"]:
                laps = laps.iloc[0:0]
            else:
                laps = laps.loc[laps["Team"].astype(str).isin(filters["teams"])]
        if filters["all_compounds"] and "Compound" in laps.columns:
            if not filters["compounds"]:
                laps = laps.iloc[0:0]
            else:
                laps = laps.loc[laps["Compound"].astype(str).isin(filters["compounds"])]
        if "LapNumber" in laps.columns:
            lo, hi = filters["lap_range"]
            number = pd.to_numeric(laps["LapNumber"], errors="coerce")
            laps = laps.loc[(number >= lo) & (number <= hi)]
        if filters["valid_only"] and "IsValidPace" in laps.columns:
            laps = laps.loc[laps["IsValidPace"]]

    drivers = set()
    if not laps.empty and "Driver" in laps.columns:
        drivers = set(laps["Driver"].astype(str))

    stints = tables.get("stints", pd.DataFrame()).copy()
    if not stints.empty and "Driver" in stints.columns:
        if not drivers:
            stints = stints.iloc[0:0]
        else:
            stints = stints.loc[stints["Driver"].astype(str).isin(drivers)]
        if filters["all_compounds"] and "Compound" in stints.columns:
            if not filters["compounds"]:
                stints = stints.iloc[0:0]
            else:
                stints = stints.loc[stints["Compound"].astype(str).isin(filters["compounds"])]
        if {"StintStart", "StintEnd"}.issubset(stints.columns):
            lo, hi = filters["lap_range"]
            start = pd.to_numeric(stints["StintStart"], errors="coerce")
            end = pd.to_numeric(stints["StintEnd"], errors="coerce")
            stints = stints.loc[(end >= lo) & (start <= hi)]

    results = tables.get("results", pd.DataFrame()).copy()
    if not results.empty:
        if filters["all_teams"] and "TeamName" in results.columns:
            if not filters["teams"]:
                results = results.iloc[0:0]
            else:
                results = results.loc[results["TeamName"].astype(str).isin(filters["teams"])]
        if "Abbreviation" in results.columns:
            if drivers:
                results = results.loc[results["Abbreviation"].astype(str).isin(drivers)]
            elif had_lap_drivers:
                results = results.iloc[0:0]

    view = dict(tables)
    view["laps"] = laps.reset_index(drop=True)
    view["stints"] = stints.reset_index(drop=True)
    view["results"] = results.reset_index(drop=True)
    return view


def render_header(session, tables: dict) -> None:
    """Event, session, circuit, and a one-line weather summary."""
    meta = {}
    if tables.get("meta") is not None and not tables["meta"].empty:
        meta = tables["meta"].iloc[0].to_dict()
    event = meta.get("event_name") or getattr(session, "name", "Session")
    session_name = meta.get("session_name") or getattr(session, "name", "")
    place = ", ".join(
        part for part in (str(meta.get("location") or ""), str(meta.get("country") or "")) if part
    )
    weather = weather_line(tables.get("weather", pd.DataFrame()))
    st.markdown(f"**{event}** · {session_name} · {place} · {weather}")


def _highlight_drivers(options: list[str], key: str) -> list[str]:
    if st.session_state.get("driver_key") != key:
        st.session_state["drivers"] = options[:2]
        st.session_state["driver_key"] = key
    current = st.session_state.get("drivers") or []
    kept = [driver for driver in current if driver in options]
    if not kept:
        kept = options[:2]
    if kept != current:
        st.session_state["drivers"] = kept
    if not options:
        return []
    picked = st.sidebar.multiselect(
        "Drivers to highlight",
        options,
        key="drivers",
        help="Used on pace traces, degradation, telemetry, and the track map.",
    )
    return picked or options[:2]


def get_bundle(*, telemetry: bool = False) -> Bundle:
    """Return the loaded session, or stop the page until Load session is clicked.

    The first visit loads the sidebar selection. After that, a new year, event,
    or session waits for **Load session** so a dropdown change cannot start a
    long download.
    """
    year, gp, identifier, _schedule, clicked = render_sidebar()
    key = session_key(year, gp, identifier)
    loaded = st.session_state.get("loaded_key")

    if not (clicked or loaded == key or loaded is None):
        st.info(
            "Session selection changed. Click **Load session** to download "
            "and preprocess the new weekend."
        )
        st.stop()

    try:
        session = cached_session(year, gp, identifier, telemetry)
        tables = enrich(cached_tables(year, gp, identifier))
    except Exception as exc:
        st.error("Could not load this session from the FastF1 APIs.")
        with st.expander("Error detail"):
            st.exception(exc)
        st.stop()

    st.session_state["loaded_key"] = key
    st.sidebar.success(f"Loaded {gp} — {identifier} ({year})")
    render_header(session, tables)
    filters = render_slice_controls(tables, key)
    view = slice_tables(tables, filters)
    options = driver_list(view["laps"], view["results"])
    if not options:
        options = driver_list(tables["laps"], tables["results"])
    drivers = _highlight_drivers(options, key)
    return Bundle(session, tables, view, drivers, filters)
