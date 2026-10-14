"""Check insight columns and Plotly traces without starting Streamlit.

Uses the processed Parquet snapshot when it exists, and always checks a
small synthetic race so the assertions do not need a network call.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

DASHBOARD_ROOT = Path(__file__).resolve().parent
if str(DASHBOARD_ROOT) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_ROOT))

from src.charts import (
    plot_degradation,
    plot_gap_to_leader,
    plot_position_changes,
    plot_sectors,
    plot_strategy,
)
from src.constants import DEFAULT_EVENT, DEFAULT_SESSION, DEFAULT_YEAR
from src.data_loader import load_processed, session_key
from src.insights import (
    add_degradation,
    add_race_gaps,
    sector_summary,
    story_metrics,
    track_status_phases,
)
from src.season import parse_driver_standings, parse_season_results


def synthetic_tables() -> dict[str, pd.DataFrame]:
    """A two-driver, seven-lap race with a safety-car lap."""
    rows = []
    clock = {"VER": 0.0, "LEC": 1.2}
    bases = {"VER": 80.0, "LEC": 80.5}
    for lap in range(1, 8):
        for driver, team in (("VER", "Red Bull"), ("LEC", "Ferrari")):
            lap_time = bases[driver] + 0.08 * lap
            clock[driver] += lap_time
            rows.append({
                "Driver": driver,
                "Team": team,
                "LapNumber": lap,
                "Stint": 1,
                "StintLap": lap,
                "Compound": "MEDIUM",
                "LapTime_s": lap_time,
                "Time_s": clock[driver],
                "Position": 1 if driver == "VER" else 2,
                "Sector1_s": lap_time * 0.3,
                "Sector2_s": lap_time * 0.4,
                "Sector3_s": lap_time * 0.3,
                "IsValidPace": True,
                "IsPaceOutlier": False,
                "LapCategory": "Valid pace",
                "TrackStatusLabel": "Safety Car" if lap == 4 else "Green",
                "TyreLife": lap,
            })
    laps = pd.DataFrame(rows)
    stints = pd.DataFrame([
        {
            "Driver": "VER", "Team": "Red Bull", "Stint": 1, "Compound": "MEDIUM",
            "StintLength": 7, "StintStart": 1, "StintEnd": 7, "MeanPace_s": 80.3,
        },
        {
            "Driver": "LEC", "Team": "Ferrari", "Stint": 1, "Compound": "MEDIUM",
            "StintLength": 7, "StintStart": 1, "StintEnd": 7, "MeanPace_s": 80.8,
        },
    ])
    results = pd.DataFrame([
        {
            "Abbreviation": "VER", "FullName": "Max Verstappen", "TeamName": "Red Bull",
            "Position": 1, "GridPosition": 2, "Status": "Finished",
        },
        {
            "Abbreviation": "LEC", "FullName": "Charles Leclerc", "TeamName": "Ferrari",
            "Position": 2, "GridPosition": 1, "Status": "Finished",
        },
    ])
    weather = pd.DataFrame([{"AirTemp": 25.0, "TrackTemp": 36.0, "Rainfall": False, "Time_min": 0.0}])
    return {
        "laps": laps,
        "results": results,
        "stints": stints,
        "weather": weather,
        "rcm": pd.DataFrame(),
        "meta": pd.DataFrame([{"event_name": "Synthetic Grand Prix", "session_name": "Race"}]),
    }


def _assert_figures(laps: pd.DataFrame, stints: pd.DataFrame) -> None:
    figures = [
        plot_position_changes(laps, None),
        plot_gap_to_leader(laps, None),
        plot_strategy(stints, None, phases=track_status_phases(laps)),
        plot_degradation(laps, None),
        plot_sectors(sector_summary(laps), None),
    ]
    for fig in figures:
        if len(fig.data) < 1:
            raise AssertionError(f"Figure '{fig.layout.title.text}' has no traces")


def _assert_insights(tables: dict[str, pd.DataFrame], label: str) -> None:
    laps = add_race_gaps(tables["laps"])
    if "GapToLeader_s" not in laps.columns or "Interval_s" not in laps.columns:
        raise AssertionError(f"{label}: gap columns missing")
    if not laps["GapToLeader_s"].notna().any():
        raise AssertionError(f"{label}: gap to leader is empty")
    stints = add_degradation(tables["stints"], laps)
    if "DegSlope_s" not in stints.columns:
        raise AssertionError(f"{label}: degradation slope missing")
    if not stints["DegSlope_s"].notna().any():
        raise AssertionError(f"{label}: degradation slope is empty")
    phases = track_status_phases(laps)
    if not {"LapStart", "LapEnd", "Status"}.issubset(phases.columns):
        raise AssertionError(f"{label}: track-status phases missing")
    story = story_metrics(laps, tables["results"], tables["weather"], "Race")
    if not story["fastest_driver"]:
        raise AssertionError(f"{label}: fastest driver missing")
    _assert_figures(laps, stints)
    print(
        f"{label}: laps={len(laps)} gaps={int(laps['GapToLeader_s'].notna().sum())} "
        f"slopes={int(stints['DegSlope_s'].notna().sum())} "
        f"leader={story['leader']} fastest={story['fastest_driver']}"
    )


def _assert_season_parser() -> None:
    standings = parse_driver_standings({
        "MRData": {"StandingsTable": {"StandingsLists": [{
            "DriverStandings": [{
                "position": "1",
                "points": "437",
                "wins": "9",
                "Driver": {"code": "VER", "givenName": "Max", "familyName": "Verstappen"},
                "Constructors": [{"name": "Red Bull"}],
            }],
        }]}}
    })
    if standings.iloc[0]["Code"] != "VER" or standings.iloc[0]["Points"] != 437:
        raise AssertionError("driver standings parser mismatch")
    results = parse_season_results({
        "MRData": {"RaceTable": {"Races": [{
            "round": "1",
            "raceName": "Bahrain Grand Prix",
            "Results": [{
                "position": "1",
                "points": "25",
                "status": "Finished",
                "Driver": {"code": "VER", "givenName": "Max", "familyName": "Verstappen"},
                "Constructor": {"name": "Red Bull"},
            }],
        }]}}
    })
    if results.iloc[0]["Race"] != "Bahrain Grand Prix":
        raise AssertionError("season results parser mismatch")
    print("jolpica parsers: ok")


def main() -> None:
    _assert_insights(synthetic_tables(), "synthetic")
    key = session_key(DEFAULT_YEAR, DEFAULT_EVENT, DEFAULT_SESSION)
    stored = load_processed(key)
    if stored is None:
        print(f"no processed snapshot for {key}")
    else:
        print(f"using processed snapshot {key}")
        _assert_insights(stored, "snapshot")
    _assert_season_parser()
    print("OK")


if __name__ == "__main__":
    main()
