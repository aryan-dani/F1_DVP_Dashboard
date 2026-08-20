"""Turn FastF1 API tables into analysis-ready DataFrames."""

from __future__ import annotations

import pandas as pd

from src.constants import (
    LAP_TIMEDELTA_COLS,
    RESULT_TIMEDELTA_COLS,
    TRACK_STATUS_MAP,
)
from src.data_loader import event_meta, session_key


def _td_seconds(series: pd.Series) -> pd.Series:
    """Convert timedelta or datetime series to float seconds (NaN-preserving).

    Datetimes are returned as seconds from the first valid timestamp so race
    control messages (UTC clocks) still get a numeric axis.
    """
    if series.empty:
        return series
    if pd.api.types.is_timedelta64_dtype(series):
        return series.dt.total_seconds()
    if pd.api.types.is_datetime64_any_dtype(series):
        origin = series.min()
        return (series - origin).dt.total_seconds()
    converted = pd.to_timedelta(series, errors="coerce")
    if converted.notna().any():
        return converted.dt.total_seconds()
    dates = pd.to_datetime(series, errors="coerce")
    origin = dates.min()
    return (dates - origin).dt.total_seconds()


def decode_track_status(code: object) -> str:
    """Map a live-timing status string (e.g. ``'1'``, ``'24'``) to labels."""
    if code is None or (isinstance(code, float) and pd.isna(code)):
        return "Unknown"
    text = str(code).strip()
    if not text or text.lower() == "nan":
        return "Unknown"
    labels = [TRACK_STATUS_MAP.get(ch, f"Code {ch}") for ch in text]
    # unique, preserve order
    seen: list[str] = []
    for label in labels:
        if label not in seen:
            seen.append(label)
    return " + ".join(seen)


def _lap_category(row: pd.Series) -> str:
    if bool(row.get("IsDeleted")):
        return "Deleted"
    if bool(row.get("IsInLap")) or bool(row.get("IsOutLap")):
        return "Box lap"
    if pd.isna(row.get("LapTime_s")):
        return "No time"
    if not bool(row.get("IsAccurate")):
        return "Inaccurate"
    return "Valid pace"


def preprocess_laps(session) -> pd.DataFrame:
    """Clean lap timing, add seconds columns, flags, and pace features."""
    raw = getattr(session, "_laps", None)
    if raw is None:
        try:
            raw = session.laps
        except Exception:
            return pd.DataFrame()

    df = pd.DataFrame(raw).copy()
    if df.empty:
        return df

    for col in LAP_TIMEDELTA_COLS:
        if col in df.columns:
            df[f"{col}_s"] = _td_seconds(df[col])

    rename = {
        "LapTime_s": "LapTime_s",
        "Sector1Time_s": "Sector1_s",
        "Sector2Time_s": "Sector2_s",
        "Sector3Time_s": "Sector3_s",
    }
    df = df.rename(columns=rename)

    df["IsInLap"] = df["PitInTime"].notna() if "PitInTime" in df.columns else False
    df["IsOutLap"] = (
        df["PitOutTime"].notna() if "PitOutTime" in df.columns else False
    )
    df["IsDeleted"] = df["Deleted"].fillna(False).astype(bool) if "Deleted" in df.columns else False
    if "IsAccurate" in df.columns:
        df["IsAccurate"] = df["IsAccurate"].fillna(False).astype(bool)
    else:
        df["IsAccurate"] = False

    df["TrackStatusLabel"] = df["TrackStatus"].map(decode_track_status) if "TrackStatus" in df.columns else "Unknown"

    df["IsValidPace"] = (
        df["IsAccurate"]
        & ~df["IsDeleted"]
        & ~df["IsInLap"]
        & ~df["IsOutLap"]
        & df["LapTime_s"].notna()
        & (df["LapTime_s"] > 0)
    )

    df["LapCategory"] = df.apply(_lap_category, axis=1)

    df["StintLap"] = df.groupby(["Driver", "Stint"]).cumcount() + 1

    valid_mask = df["IsValidPace"]
    if valid_mask.any():
        fastest = df.loc[valid_mask, "LapTime_s"].min()
        df["GapToFastest_s"] = df["LapTime_s"] - fastest
        medians = df.loc[valid_mask].groupby("Driver")["LapTime_s"].median()
        df["PaceDelta_s"] = df["LapTime_s"] - df["Driver"].map(medians)

        q1 = df.loc[valid_mask].groupby("Driver")["LapTime_s"].transform(
            lambda s: s.quantile(0.25)
        )
        q3 = df.loc[valid_mask].groupby("Driver")["LapTime_s"].transform(
            lambda s: s.quantile(0.75)
        )
        iqr = q3 - q1
        df["IsPaceOutlier"] = False
        df.loc[valid_mask, "IsPaceOutlier"] = (
            (df.loc[valid_mask, "LapTime_s"] < q1 - 1.5 * iqr)
            | (df.loc[valid_mask, "LapTime_s"] > q3 + 1.5 * iqr)
        )
    else:
        df["GapToFastest_s"] = pd.NA
        df["PaceDelta_s"] = pd.NA
        df["IsPaceOutlier"] = False

    lap_s = df["LapTime_s"].replace(0, pd.NA)
    for sector in ("Sector1_s", "Sector2_s", "Sector3_s"):
        if sector in df.columns:
            df[sector.replace("_s", "_share")] = df[sector] / lap_s

    df = _attach_weather(session, df)
    return df.reset_index(drop=True)


def _attach_weather(session, laps: pd.DataFrame) -> pd.DataFrame:
    """Left-join one weather sample per lap (FastF1 already aligns this)."""
    weather_cols = ["AirTemp", "TrackTemp", "Humidity", "Rainfall", "WindSpeed"]
    try:
        weather = session.laps.get_weather_data()
    except Exception:
        for col in weather_cols:
            if col not in laps.columns:
                laps[col] = pd.NA
        return laps

    weather = pd.DataFrame(weather).reset_index(drop=True)
    laps = laps.reset_index(drop=True)
    if len(weather) != len(laps):
        for col in weather_cols:
            if col not in laps.columns:
                laps[col] = pd.NA
        return laps
    keep = [c for c in weather.columns if c != "Time"]
    return pd.concat([laps, weather.loc[:, keep]], axis=1)


def preprocess_results(session) -> pd.DataFrame:
    """Flatten session results with times in seconds."""
    try:
        raw = session.results
    except Exception:
        return pd.DataFrame()

    df = pd.DataFrame(raw).copy()
    if df.empty:
        return df

    for col in RESULT_TIMEDELTA_COLS:
        if col in df.columns:
            df[f"{col}_s"] = _td_seconds(df[col])

    preferred = [
        "DriverNumber", "Abbreviation", "FullName", "BroadcastName",
        "TeamName", "Position", "ClassifiedPosition", "GridPosition",
        "Q1_s", "Q2_s", "Q3_s", "Time_s", "Status", "Points", "Laps",
        "CountryCode",
    ]
    cols = [c for c in preferred if c in df.columns]
    extra = [c for c in df.columns if c not in cols and not c.endswith("Time")]
    return df[cols + extra].reset_index(drop=True)


def preprocess_stints(laps: pd.DataFrame) -> pd.DataFrame:
    """One row per driver stint: compound, length, mean valid pace."""
    if laps.empty or "Stint" not in laps.columns:
        return pd.DataFrame(
            columns=[
                "Driver", "Team", "Stint", "Compound", "StintLength",
                "StintStart", "StintEnd", "MeanPace_s",
            ]
        )

    grouped = laps.groupby(["Driver", "Stint", "Compound"], dropna=False)
    stints = grouped.agg(
        Team=("Team", "first"),
        StintLength=("LapNumber", "count"),
        StintStart=("LapNumber", "min"),
        StintEnd=("LapNumber", "max"),
    ).reset_index()

    means = []
    for _, row in stints.iterrows():
        mask = (
            (laps["Driver"] == row["Driver"])
            & (laps["Stint"] == row["Stint"])
            & laps["IsValidPace"]
        )
        means.append(laps.loc[mask, "LapTime_s"].mean())
    stints["MeanPace_s"] = means
    return stints.sort_values(["Driver", "Stint"]).reset_index(drop=True)


def preprocess_weather(session) -> pd.DataFrame:
    """Session weather samples with time in seconds."""
    try:
        raw = session.weather_data
    except Exception:
        return pd.DataFrame()

    df = pd.DataFrame(raw).copy()
    if df.empty:
        return df
    if "Time" in df.columns:
        df["Time_s"] = _td_seconds(df["Time"])
        df["Time_min"] = df["Time_s"] / 60.0
    return df.reset_index(drop=True)


def preprocess_rcm(session) -> pd.DataFrame:
    """Race-control messages with a numeric timestamp."""
    try:
        raw = session.race_control_messages
    except Exception:
        return pd.DataFrame()

    df = pd.DataFrame(raw).copy()
    if df.empty:
        return df
    if "Time" in df.columns:
        df["Time_s"] = _td_seconds(df["Time"])
    return df.reset_index(drop=True)


def build_processed_tables(session) -> dict[str, pd.DataFrame]:
    """Run the full preprocess pipeline and return named tables."""
    laps = preprocess_laps(session)
    results = preprocess_results(session)
    stints = preprocess_stints(laps)
    weather = preprocess_weather(session)
    rcm = preprocess_rcm(session)
    meta = pd.DataFrame([event_meta(session)])
    return {
        "laps": laps,
        "results": results,
        "stints": stints,
        "weather": weather,
        "rcm": rcm,
        "meta": meta,
    }


def snapshot_key(session) -> str:
    """Parquet key from a loaded session."""
    return session_key(session.event.year, session.event["EventName"], session.name)
