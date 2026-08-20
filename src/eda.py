"""Exploratory summaries on the processed lap dataset."""

from __future__ import annotations

import pandas as pd


CORR_CANDIDATES = (
    "LapTime_s",
    "Sector1_s",
    "Sector2_s",
    "Sector3_s",
    "SpeedI1",
    "SpeedI2",
    "SpeedFL",
    "SpeedST",
    "TyreLife",
    "StintLap",
    "AirTemp",
    "TrackTemp",
    "Humidity",
    "WindSpeed",
    "GapToFastest_s",
)


def missingness(df: pd.DataFrame) -> pd.DataFrame:
    """Count and percentage of missing values per column."""
    if df.empty:
        return pd.DataFrame(columns=["column", "missing", "pct"])
    missing = df.isna().sum()
    out = pd.DataFrame({
        "column": missing.index.astype(str),
        "missing": missing.to_numpy(),
        "pct": (missing / len(df) * 100).to_numpy(),
    })
    return out.sort_values("missing", ascending=False).reset_index(drop=True)


def numeric_describe(df: pd.DataFrame, columns: list[str] | None = None) -> pd.DataFrame:
    """pandas describe() for numeric analysis columns."""
    if df.empty:
        return pd.DataFrame()
    if columns is None:
        columns = [c for c in CORR_CANDIDATES if c in df.columns]
    use = df[columns].apply(pd.to_numeric, errors="coerce")
    return use.describe().T


def valid_pace(laps: pd.DataFrame) -> pd.DataFrame:
    """Laps used for pace statistics (green, timed, not a box/deleted lap)."""
    if laps.empty or "IsValidPace" not in laps.columns:
        return laps
    return laps.loc[laps["IsValidPace"]].copy()


def correlation_matrix(laps: pd.DataFrame) -> pd.DataFrame:
    """Pearson correlation on valid-pace laps for selected numeric columns."""
    pace = valid_pace(laps)
    cols = [c for c in CORR_CANDIDATES if c in pace.columns]
    if pace.empty or len(cols) < 2:
        return pd.DataFrame()
    return pace[cols].apply(pd.to_numeric, errors="coerce").corr()


def category_counts(laps: pd.DataFrame) -> pd.DataFrame:
    """How many laps fall into each cleaning category."""
    if laps.empty or "LapCategory" not in laps.columns:
        return pd.DataFrame(columns=["LapCategory", "count"])
    counts = laps["LapCategory"].value_counts(dropna=False).rename_axis(
        "LapCategory"
    ).reset_index(name="count")
    return counts


def fastest_lap_row(laps: pd.DataFrame) -> pd.Series | None:
    """Single fastest valid-pace lap, or None."""
    pace = valid_pace(laps)
    if pace.empty:
        return None
    idx = pace["LapTime_s"].idxmin()
    return pace.loc[idx]


def driver_list(laps: pd.DataFrame, results: pd.DataFrame) -> list[str]:
    """Driver abbreviations, preferring finishing order from results."""
    if not results.empty and "Abbreviation" in results.columns:
        ordered = [
            str(a) for a in results["Abbreviation"].dropna().tolist() if str(a)
        ]
        if ordered:
            return ordered
    if laps.empty or "Driver" not in laps.columns:
        return []
    return sorted(laps["Driver"].dropna().astype(str).unique().tolist())
