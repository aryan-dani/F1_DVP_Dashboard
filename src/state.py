"""Shared Streamlit sidebar, caching, and session-bundle access."""

from __future__ import annotations

import matplotlib.pyplot as plt
import streamlit as st

from src.constants import DEFAULT_EVENT, DEFAULT_SESSION, DEFAULT_YEAR
from src.data_loader import (
    event_sessions,
    fetch_schedule,
    fetch_session,
    save_processed,
    session_key,
)
from src.eda import driver_list
from src.preprocess import build_processed_tables


def configure_page(title: str) -> None:
    """Must be the first Streamlit call on each page."""
    st.set_page_config(
        page_title=f"{title} | F1_DVP_Dashboard",
        layout="wide",
    )


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


def render_sidebar():
    """Year / event / session controls. Returns widget values and Load click."""
    st.sidebar.title("F1_DVP_Dashboard")
    st.sidebar.caption(
        "Data is fetched through FastF1 from the F1 live-timing archive "
        "and Jolpica-F1. Nothing is hardcoded as a CSV."
    )
    year = int(st.sidebar.number_input(
        "Year",
        min_value=2018,
        max_value=2026,
        value=int(st.session_state.get("year", DEFAULT_YEAR)),
        step=1,
    ))
    try:
        schedule = cached_schedule(year)
    except Exception as exc:
        st.sidebar.error(str(exc))
        st.stop()

    events = schedule["EventName"].astype(str).tolist()
    stored_gp = st.session_state.get("gp", DEFAULT_EVENT)
    gp_index = events.index(stored_gp) if stored_gp in events else 0
    gp = st.sidebar.selectbox("Grand Prix", events, index=gp_index)

    sessions = event_sessions(schedule, gp)
    if not sessions:
        st.sidebar.error("No sessions listed for this event.")
        st.stop()
    stored_ses = st.session_state.get("identifier", DEFAULT_SESSION)
    if stored_ses in sessions:
        ses_index = sessions.index(stored_ses)
    elif "Race" in sessions:
        ses_index = sessions.index("Race")
    else:
        ses_index = 0
    identifier = st.sidebar.selectbox("Session", sessions, index=ses_index)

    clicked = st.sidebar.button("Load session", type="primary")
    st.session_state["year"] = year
    st.session_state["gp"] = gp
    st.session_state["identifier"] = identifier
    return year, gp, identifier, schedule, clicked


def get_bundle(*, telemetry: bool = False):
    """Return (session, tables, selected_drivers) or stop the page.

    The first visit loads the sidebar selection (default: 2024 Italian GP
    Race). After that, click **Load session** when you change year/event.

    Args:
        telemetry: Request car/position streams (telemetry and track-map pages).
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
        tables = cached_tables(year, gp, identifier)
    except Exception as exc:
        st.error("Could not load this session from the FastF1 APIs.")
        st.exception(exc)
        st.stop()

    st.session_state["loaded_key"] = key
    st.sidebar.success(f"Loaded {gp} — {identifier} ({year})")

    drivers = driver_list(tables["laps"], tables["results"])
    if st.session_state.get("driver_key") != key:
        st.session_state["drivers"] = [d for d in drivers[:2]]
        st.session_state["driver_key"] = key

    picked = st.sidebar.multiselect(
        "Drivers to highlight",
        drivers,
        key="drivers",
        help="Used on lap times, telemetry and the track map.",
    )
    return session, tables, picked or drivers[:2]


def show_fig(fig) -> None:
    """Render a matplotlib figure and free it."""
    try:
        st.pyplot(fig, width="stretch", clear_figure=True)
    except TypeError:
        st.pyplot(fig, use_container_width=True, clear_figure=True)
    plt.close(fig)
