"""Race-story metrics derived from the processed lap and result tables."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.eda import fastest_lap_row, valid_pace
from src.constants import QUALI_LIKE, RACE_LIKE


def _stint_key(driver, stint) -> tuple:
    try:
        stint_value = float(stint)
    except (TypeError, ValueError):
        stint_value = stint
    return (str(driver), stint_value)


def add_race_gaps(laps: pd.DataFrame) -> pd.DataFrame:
    """Add gap to the lap leader and the interval to the car ahead.

    Gap is session time at the end of the lap minus the smallest session
    time on that lap number. Interval is the gap to the car one position
    ahead.
    """
    df = laps.copy()
    df["GapToLeader_s"] = pd.NA
    df["Interval_s"] = pd.NA
    if df.empty or "Time_s" not in df.columns or "LapNumber" not in df.columns:
        return df

    leader = df.groupby("LapNumber")["Time_s"].transform("min")
    df["GapToLeader_s"] = df["Time_s"] - leader

    pieces: list[pd.DataFrame] = []
    for _, group in df.groupby("LapNumber", sort=False):
        block = group.copy()
        if "Position" in block.columns and block["Position"].notna().any():
            block["_pos"] = pd.to_numeric(block["Position"], errors="coerce")
            block = block.sort_values(["_pos", "Time_s"], na_position="last")
        else:
            block = block.sort_values("Time_s", na_position="last")
        ahead = block["Time_s"].shift(1)
        block["Interval_s"] = block["Time_s"] - ahead
        block = block.drop(columns=["_pos"], errors="ignore")
        pieces.append(block)
    if not pieces:
        return df
    return pd.concat(pieces, ignore_index=True)


def add_degradation(stints: pd.DataFrame, laps: pd.DataFrame) -> pd.DataFrame:
    """Attach seconds-per-lap pace slope for each driver stint.

    The slope is a straight fit of valid-pace lap time against lap-in-stint.
    Stints with fewer than three timed laps stay empty.
    """
    out = stints.copy()
    out["DegSlope_s"] = np.nan
    if out.empty or laps.empty:
        return out
    pace = valid_pace(laps)
    if pace.empty or "StintLap" not in pace.columns or "LapTime_s" not in pace.columns:
        return out

    slopes: dict[tuple, float] = {}
    for (driver, stint), group in pace.groupby(["Driver", "Stint"], dropna=False):
        group = group.dropna(subset=["LapTime_s", "StintLap"])
        if len(group) < 3:
            slopes[_stint_key(driver, stint)] = np.nan
            continue
        x = group["StintLap"].astype(float).to_numpy()
        y = group["LapTime_s"].astype(float).to_numpy()
        slope = float(np.polyfit(x, y, 1)[0])
        slopes[_stint_key(driver, stint)] = slope

    out["DegSlope_s"] = [
        slopes.get(_stint_key(row.Driver, row.Stint), np.nan)
        for row in out.itertuples(index=False)
    ]
    return out


def enrich(tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Return a copy of the processed tables with gap and degradation columns."""
    out = dict(tables)
    laps = add_race_gaps(tables.get("laps", pd.DataFrame()))
    out["laps"] = laps
    out["stints"] = add_degradation(tables.get("stints", pd.DataFrame()), laps)
    return out


def lead_change_count(laps: pd.DataFrame) -> int:
    """How many times the lap leader changed during the session."""
    if laps.empty or "Position" not in laps.columns or "Driver" not in laps.columns:
        return 0
    position = pd.to_numeric(laps["Position"], errors="coerce")
    leaders = laps.loc[position == 1, ["LapNumber", "Driver"]].dropna()
    if leaders.empty:
        return 0
    order = (
        leaders.sort_values("LapNumber")
        .drop_duplicates("LapNumber")["Driver"]
        .astype(str)
        .tolist()
    )
    return sum(previous != current for previous, current in zip(order, order[1:]))


def safety_car_laps(laps: pd.DataFrame) -> int:
    """Unique lap numbers spent under the safety car or a virtual safety car."""
    if laps.empty or "TrackStatusLabel" not in laps.columns:
        return 0
    label = laps["TrackStatusLabel"].astype(str)
    mask = label.str.contains(r"Safety Car|VSC", case=False, regex=True, na=False)
    if "LapNumber" not in laps.columns:
        return int(mask.sum())
    return int(laps.loc[mask, "LapNumber"].nunique())


def track_status_phases(laps: pd.DataFrame) -> pd.DataFrame:
    """Collapse consecutive laps that share a track-status label."""
    columns = ["LapStart", "LapEnd", "Status"]
    if laps.empty or "TrackStatusLabel" not in laps.columns or "LapNumber" not in laps.columns:
        return pd.DataFrame(columns=columns)

    per_lap = (
        laps.groupby("LapNumber")["TrackStatusLabel"]
        .agg(lambda series: series.dropna().astype(str).mode().iloc[0] if series.dropna().size else "Unknown")
        .sort_index()
    )
    rows: list[dict] = []
    start = None
    previous = None
    previous_lap = None
    for lap, status in per_lap.items():
        if status != previous:
            if previous is not None:
                rows.append({
                    "LapStart": int(start),
                    "LapEnd": int(previous_lap),
                    "Status": previous,
                })
            start = lap
            previous = status
        previous_lap = lap
    if previous is not None:
        rows.append({
            "LapStart": int(start),
            "LapEnd": int(previous_lap),
            "Status": previous,
        })
    return pd.DataFrame(rows, columns=columns)


def sector_summary(laps: pd.DataFrame) -> pd.DataFrame:
    """Best and median sector times per driver on valid-pace laps."""
    pace = valid_pace(laps)
    columns = [
        "Driver", "Team",
        "BestS1", "MedianS1", "BestS2", "MedianS2", "BestS3", "MedianS3",
    ]
    if pace.empty:
        return pd.DataFrame(columns=columns)
    rows = []
    for driver, group in pace.groupby("Driver"):
        row = {
            "Driver": str(driver),
            "Team": str(group["Team"].iloc[0]) if "Team" in group.columns else "",
        }
        for source, name in (("Sector1_s", "S1"), ("Sector2_s", "S2"), ("Sector3_s", "S3")):
            if source in group.columns:
                row[f"Best{name}"] = group[source].min()
                row[f"Median{name}"] = group[source].median()
            else:
                row[f"Best{name}"] = pd.NA
                row[f"Median{name}"] = pd.NA
        rows.append(row)
    if not rows:
        return pd.DataFrame(columns=columns)
    summary = pd.DataFrame(rows)
    if "BestS1" in summary.columns:
        summary = summary.sort_values("BestS1", na_position="last")
    return summary.reset_index(drop=True)


def places_gained(results: pd.DataFrame) -> pd.DataFrame:
    """Grid position minus classified position. Positive means places gained."""
    if results.empty or "GridPosition" not in results.columns or "Position" not in results.columns:
        return pd.DataFrame()
    df = results.copy()
    grid = pd.to_numeric(df["GridPosition"], errors="coerce")
    position = pd.to_numeric(df["Position"], errors="coerce")
    df["PlacesGained"] = grid - position
    return df.dropna(subset=["PlacesGained"]).reset_index(drop=True)


def qualifying_progression(results: pd.DataFrame) -> pd.DataFrame:
    """Mark how far each driver went: Q3, out in Q2, or out in Q1."""
    if results.empty:
        return results
    work = results.copy()

    def reached(row: pd.Series) -> str:
        if pd.notna(row.get("Q3_s")):
            return "Q3"
        if pd.notna(row.get("Q2_s")):
            return "Out in Q2"
        if pd.notna(row.get("Q1_s")):
            return "Out in Q1"
        return "No time"

    work["Reached"] = work.apply(reached, axis=1)
    return work


def practice_split(laps: pd.DataFrame, short_n: int = 3) -> pd.DataFrame:
    """Best of the fastest few laps versus the mean of the laps after those."""
    pace = valid_pace(laps)
    columns = ["Driver", "ShortRun_s", "LongRun_s", "LongLaps"]
    if pace.empty or "LapTime_s" not in pace.columns:
        return pd.DataFrame(columns=columns)
    rows = []
    for driver, group in pace.groupby("Driver"):
        ordered = group.dropna(subset=["LapTime_s"]).sort_values("LapTime_s")
        if ordered.empty:
            continue
        short = ordered.head(short_n)
        long = ordered.iloc[short_n:]
        rows.append({
            "Driver": str(driver),
            "ShortRun_s": float(short["LapTime_s"].min()),
            "LongRun_s": float(long["LapTime_s"].mean()) if not long.empty else np.nan,
            "LongLaps": int(len(long)),
        })
    if not rows:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame(rows).sort_values("ShortRun_s").reset_index(drop=True)


def weather_line(weather: pd.DataFrame) -> str:
    """One-line air, track, and wet/dry summary."""
    if weather is None or weather.empty:
        return "Weather unavailable"
    parts: list[str] = []
    if "AirTemp" in weather.columns and weather["AirTemp"].notna().any():
        parts.append(f"Air {float(weather['AirTemp'].mean()):.0f}°C")
    if "TrackTemp" in weather.columns and weather["TrackTemp"].notna().any():
        parts.append(f"Track {float(weather['TrackTemp'].mean()):.0f}°C")
    wet = False
    if "Rainfall" in weather.columns:
        wet = bool(weather["Rainfall"].fillna(False).astype(bool).any())
    parts.append("Wet" if wet else "Dry")
    return " · ".join(parts)


def conditions_label(weather: pd.DataFrame) -> str:
    """Wet when any weather sample reports rainfall, otherwise Dry."""
    if weather is None or weather.empty or "Rainfall" not in weather.columns:
        return "Dry"
    wet = bool(weather["Rainfall"].fillna(False).astype(bool).any())
    return "Wet" if wet else "Dry"


def story_metrics(
        laps: pd.DataFrame,
        results: pd.DataFrame,
        weather: pd.DataFrame,
        session_name: str,
) -> dict:
    """Header numbers for the loaded session."""
    fastest = fastest_lap_row(laps)
    metrics = {
        "leader": None,
        "leader_name": None,
        "leader_label": "Leader",
        "fastest_driver": None if fastest is None else str(fastest["Driver"]),
        "fastest_time": None if fastest is None else float(fastest["LapTime_s"]),
        "fastest_lap": None if fastest is None else int(fastest["LapNumber"]),
        "lead_changes": None,
        "sc_laps": None,
        "conditions": conditions_label(weather),
        "places": places_gained(results) if session_name in RACE_LIKE else pd.DataFrame(),
        "session_kind": (
            "race" if session_name in RACE_LIKE
            else "qualifying" if session_name in QUALI_LIKE
            else "practice"
        ),
    }
    if results is None or results.empty or "Position" not in results.columns:
        return metrics
    position = pd.to_numeric(results["Position"], errors="coerce")
    leader_rows = results.loc[position == 1]
    if leader_rows.empty:
        return metrics
    leader = leader_rows.iloc[0]
    code = leader.get("Abbreviation")
    metrics["leader"] = None if pd.isna(code) else str(code)
    name = leader.get("FullName")
    metrics["leader_name"] = metrics["leader"] if pd.isna(name) else str(name)
    if session_name in RACE_LIKE:
        metrics["lead_changes"] = lead_change_count(laps)
        metrics["sc_laps"] = safety_car_laps(laps)
    elif session_name in QUALI_LIKE:
        metrics["leader_label"] = "Pole"
    return metrics


def faster_driver(laps: pd.DataFrame, first: str, second: str) -> tuple[str, str]:
    """Return (reference, other) where reference has the faster valid lap."""
    pace = valid_pace(laps)
    times: dict[str, float] = {}
    for driver in (first, second):
        if pace.empty or "Driver" not in pace.columns:
            break
        subset = pace.loc[pace["Driver"].astype(str) == str(driver), "LapTime_s"]
        if subset.notna().any():
            times[str(driver)] = float(subset.min())
    if str(first) in times and str(second) in times and times[str(second)] < times[str(first)]:
        return str(second), str(first)
    return str(first), str(second)


def race_control_highlights(rcm: pd.DataFrame) -> pd.DataFrame:
    """Flags, penalties, investigations, and safety-car messages."""
    if rcm is None or rcm.empty:
        return rcm if rcm is not None else pd.DataFrame()
    mask = pd.Series(False, index=rcm.index)
    if "Flag" in rcm.columns:
        mask = mask | rcm["Flag"].notna()
    if "Category" in rcm.columns:
        mask = mask | rcm["Category"].astype(str).str.contains(
            r"Flag|Safety|Penalty|Investigat",
            case=False,
            na=False,
        )
    if "Message" in rcm.columns:
        mask = mask | rcm["Message"].astype(str).str.contains(
            r"safety car|virtual|red flag|yellow|penalty|investigation|black flag",
            case=False,
            na=False,
        )
    return rcm.loc[mask].reset_index(drop=True)
