"""Load the default session, preprocess, and build figures (no Streamlit)."""

from __future__ import annotations

import sys
from pathlib import Path

DASHBOARD_ROOT = Path(__file__).resolve().parent
if str(DASHBOARD_ROOT) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_ROOT))

from src.constants import DEFAULT_EVENT, DEFAULT_SESSION, DEFAULT_YEAR
from src.data_loader import (
    enable_fastf1_cache,
    fetch_session,
    save_processed,
    session_key,
)
from src.eda import correlation_matrix, missingness, valid_pace
from src.preprocess import build_processed_tables
from src.viz import (
    plot_laptime_distribution,
    plot_strategy,
    plot_track_map,
)


def main() -> None:
    enable_fastf1_cache()
    print(f"Loading {DEFAULT_YEAR} {DEFAULT_EVENT} {DEFAULT_SESSION} ...")
    session = fetch_session(
        DEFAULT_YEAR,
        DEFAULT_EVENT,
        DEFAULT_SESSION,
        telemetry=True,
    )
    tables = build_processed_tables(session)
    key = session_key(DEFAULT_YEAR, DEFAULT_EVENT, DEFAULT_SESSION)
    save_processed(key, tables)

    laps = tables["laps"]
    print(f"event: {session.event['EventName']} — {session.name}")
    print(f"laps: {len(laps)}  valid pace: {len(valid_pace(laps))}")
    print(f"results: {len(tables['results'])}  stints: {len(tables['stints'])}")
    print(f"weather: {len(tables['weather'])}  rcm: {len(tables['rcm'])}")
    print("missing columns with NaNs:", int((missingness(laps)["missing"] > 0).sum()))
    corr = correlation_matrix(laps)
    print(f"correlation matrix: {corr.shape}")

    fig = plot_laptime_distribution(laps)
    fig.savefig(DASHBOARD_ROOT / "data" / "processed" / f"{key}_eda_hist.png")
    fig = plot_strategy(tables["stints"], session)
    fig.savefig(DASHBOARD_ROOT / "data" / "processed" / f"{key}_strategy.png")

    drv = str(laps.loc[laps["IsValidPace"], "Driver"].iloc[0])
    from src.data_loader import circuit_corners, fastest_lap_map_data
    tel = fastest_lap_map_data(session, drv)
    print(f"map telemetry for {drv}: {len(tel)} samples")
    fig = plot_track_map(tel, drv, corners=circuit_corners(session))
    fig.savefig(DASHBOARD_ROOT / "data" / "processed" / f"{key}_track.png")
    print("Wrote preview PNGs next to the parquet snapshot.")
    print("OK")


if __name__ == "__main__":
    main()
