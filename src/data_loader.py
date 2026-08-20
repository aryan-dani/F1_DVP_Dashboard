"""Fetch Formula 1 session data through FastF1 (live timing + Jolpica APIs)."""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

import fastf1

from src.constants import MAX_YEAR, MIN_YEAR
from src.paths import CACHE_DIR, PROCESSED_DIR


_CACHE_ENABLED = False


def enable_fastf1_cache() -> None:
    """Point FastF1 at the dashboard cache directory.

    Must run before any ``get_session`` / ``get_event_schedule`` call so
    HTTP responses and parsed timing files are reused.
    """
    global _CACHE_ENABLED
    if _CACHE_ENABLED:
        return
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(CACHE_DIR))
    _CACHE_ENABLED = True


def session_key(year: int, gp: str, identifier: str) -> str:
    """Build a filesystem-safe key for parquet snapshots."""
    def _slug(value: str) -> str:
        return re.sub(r"[^A-Za-z0-9]+", "_", str(value)).strip("_")

    return f"{int(year)}_{_slug(gp)}_{_slug(identifier)}"


def fetch_schedule(year: int) -> pd.DataFrame:
    """Return the championship calendar (no testing events).

    Source: FastF1 schedule JSON, with F1 timing / Jolpica fallbacks inside
    ``fastf1.get_event_schedule``.
    """
    enable_fastf1_cache()
    if year < MIN_YEAR:
        raise ValueError(
            "Timing and telemetry start in 2018. Choose 2018 or later."
        )
    if year > MAX_YEAR:
        raise ValueError(f"Year {year} is not supported.")

    schedule = fastf1.get_event_schedule(year, include_testing=False)
    return pd.DataFrame(schedule).reset_index(drop=True)


def event_sessions(schedule: pd.DataFrame, event_name: str) -> list[str]:
    """List named sessions for one Grand Prix from the schedule row."""
    match = schedule[schedule["EventName"] == event_name]
    if match.empty:
        return []
    row = match.iloc[0]
    names: list[str] = []
    for i in range(1, 6):
        value = row.get(f"Session{i}")
        if isinstance(value, str) and value.strip():
            names.append(value)
    return names


def fetch_session(
        year: int,
        gp: str,
        identifier: str,
        *,
        telemetry: bool = False,
) -> fastf1.core.Session:
    """Download (or cache-load) one session via FastF1.

    Args:
        year: Championship year (2018+ for timing data).
        gp: Event name or round number understood by ``fastf1.get_session``.
        identifier: Session name or abbreviation (``Race``, ``Q``, ...).
        telemetry: If False, skip car/position streams to save time and quota.
    """
    enable_fastf1_cache()
    session = fastf1.get_session(year, gp, identifier)
    if not session.f1_api_support:
        raise ValueError(
            "The F1 live-timing API does not cover this session "
            "(typical for seasons before 2018)."
        )
    session.load(
        laps=True,
        telemetry=telemetry,
        weather=True,
        messages=True,
    )
    return session


def event_meta(session: fastf1.core.Session) -> dict[str, Any]:
    """Small JSON-serializable summary of the loaded weekend/session."""
    event = session.event
    return {
        "year": int(event.year),
        "round": int(event["RoundNumber"]),
        "event_name": str(event["EventName"]),
        "official_name": str(event.get("OfficialEventName", "") or ""),
        "country": str(event["Country"]),
        "location": str(event["Location"]),
        "event_format": str(event["EventFormat"]),
        "session_name": str(session.name),
        "session_date_utc": str(session.date),
        "f1_api_support": bool(session.f1_api_support),
    }


def processed_paths(key: str) -> dict[str, Any]:
    """Parquet destinations for one session key."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    return {
        "laps": PROCESSED_DIR / f"{key}_laps.parquet",
        "results": PROCESSED_DIR / f"{key}_results.parquet",
        "stints": PROCESSED_DIR / f"{key}_stints.parquet",
        "weather": PROCESSED_DIR / f"{key}_weather.parquet",
        "rcm": PROCESSED_DIR / f"{key}_rcm.parquet",
        "meta": PROCESSED_DIR / f"{key}_meta.parquet",
    }


def save_processed(key: str, tables: dict[str, pd.DataFrame]) -> None:
    """Write analysis tables next to the dashboard so EDA can be repeated."""
    paths = processed_paths(key)
    for name, path in paths.items():
        frame = tables.get(name)
        if frame is None:
            continue
        frame.to_parquet(path, index=False)


def load_processed(key: str) -> dict[str, pd.DataFrame] | None:
    """Reload parquet snapshots if a full set exists."""
    paths = processed_paths(key)
    if not all(path.exists() for path in paths.values()):
        return None
    return {name: pd.read_parquet(path) for name, path in paths.items()}


def fastest_lap_car_data(session, driver: str) -> pd.DataFrame:
    """Car telemetry for a driver's fastest lap, with Distance in metres."""
    try:
        laps = session.laps.pick_drivers(driver)
        lap = laps.pick_fastest()
    except Exception:
        return pd.DataFrame()
    if lap is None or getattr(lap, "empty", False):
        return pd.DataFrame()
    try:
        car = lap.get_car_data().add_distance()
    except Exception:
        return pd.DataFrame()
    return pd.DataFrame(car)


def fastest_lap_map_data(session, driver: str) -> pd.DataFrame:
    """Merged telemetry (speed + X/Y) for a speed-colored track map."""
    try:
        laps = session.laps.pick_drivers(driver)
        lap = laps.pick_fastest()
        tel = lap.get_telemetry()
    except Exception:
        return pd.DataFrame()
    return pd.DataFrame(tel)


def circuit_corners(session) -> pd.DataFrame:
    """Corner markers from the MultiViewer circuit info endpoint."""
    try:
        info = session.get_circuit_info()
    except Exception:
        return pd.DataFrame()
    if info is None:
        return pd.DataFrame()
    return pd.DataFrame(info.corners)
