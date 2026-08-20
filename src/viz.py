"""Matplotlib / seaborn figures for the Streamlit pages."""

from __future__ import annotations

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.collections import LineCollection

import fastf1.plotting

from src.eda import valid_pace


mpl.use("Agg")
sns.set_theme(style="whitegrid", context="talk")
fastf1.plotting.setup_mpl(mpl_timedelta_support=True, color_scheme=None)

plt.rcParams.update({
    "figure.dpi": 120,
    "savefig.dpi": 120,
    "axes.titlesize": 14,
    "axes.labelsize": 11,
    "legend.fontsize": 9,
})


def _fig(figsize=(10, 5)):
    return plt.subplots(figsize=figsize, layout="constrained")


def _driver_style(driver: str, session) -> dict:
    try:
        return fastf1.plotting.get_driver_style(
            driver, ["color", "linestyle"], session
        )
    except Exception:
        return {"color": "#444444", "linestyle": "-"}


def _compound_color(compound: str, session) -> str:
    try:
        return fastf1.plotting.get_compound_color(str(compound), session)
    except Exception:
        return "#888888"


def plot_missingness(missing: pd.DataFrame):
    """Horizontal bar chart of missing-value percentages."""
    fig, ax = _fig((10, 6))
    data = missing[missing["missing"] > 0].head(20)
    if data.empty:
        ax.set_title("No missing values in the processed table")
        ax.axis("off")
        return fig
    sns.barplot(data=data, y="column", x="pct", ax=ax, color="#1f77b4")
    ax.set_xlabel("Missing (%)")
    ax.set_ylabel("")
    ax.set_title("Missing values by column")
    return fig


def plot_laptime_distribution(laps: pd.DataFrame):
    """Histogram + KDE of valid pace lap times."""
    fig, ax = _fig((10, 4.5))
    pace = valid_pace(laps)
    if pace.empty:
        ax.set_title("No valid pace laps to plot")
        ax.axis("off")
        return fig
    sns.histplot(pace["LapTime_s"], bins=30, kde=True, ax=ax, color="#1f77b4")
    ax.set_xlabel("Lap time (s)")
    ax.set_ylabel("Count")
    ax.set_title("Valid-pace lap time distribution")
    return fig


def plot_laptimes_by_driver(laps: pd.DataFrame, session=None):
    """Boxplots of valid pace times per driver."""
    pace = valid_pace(laps)
    fig, ax = _fig((12, 5.5))
    if pace.empty:
        ax.set_title("No valid pace laps to plot")
        ax.axis("off")
        return fig
    order = (
        pace.groupby("Driver")["LapTime_s"].median().sort_values().index.tolist()
    )
    if session is not None:
        palette = {drv: _driver_style(drv, session)["color"] for drv in order}
        sns.boxplot(
            data=pace, x="Driver", y="LapTime_s", order=order,
            hue="Driver", palette=palette, legend=False, ax=ax,
        )
    else:
        sns.boxplot(
            data=pace, x="Driver", y="LapTime_s", order=order, ax=ax,
        )
    ax.tick_params(axis="x", rotation=45)
    ax.set_ylabel("Lap time (s)")
    ax.set_title("Lap time spread by driver (valid pace only)")
    return fig


def plot_correlation_heatmap(corr: pd.DataFrame):
    """Seaborn heatmap of the EDA correlation matrix."""
    fig, ax = _fig((9, 7))
    if corr.empty:
        ax.set_title("Not enough numeric columns for a correlation matrix")
        ax.axis("off")
        return fig
    sns.heatmap(
        corr, ax=ax, cmap="vlag", center=0, annot=True, fmt=".2f",
        annot_kws={"size": 8},
    )
    ax.set_title("Pearson correlation (valid pace laps)")
    return fig


def plot_category_counts(counts: pd.DataFrame):
    """Bar chart of lap cleaning categories."""
    fig, ax = _fig((8, 4))
    if counts.empty:
        ax.set_title("No lap categories")
        ax.axis("off")
        return fig
    sns.barplot(data=counts, x="LapCategory", y="count", ax=ax, color="#1f77b4")
    ax.set_xlabel("")
    ax.set_ylabel("Laps")
    ax.set_title("Lap categories after preprocessing")
    ax.tick_params(axis="x", rotation=20)
    return fig


def plot_weather(weather: pd.DataFrame):
    """Air and track temperature over session time."""
    fig, ax = _fig((10, 4.5))
    if weather.empty or "Time_min" not in weather.columns:
        ax.set_title("Weather data is not available for this session")
        ax.axis("off")
        return fig
    ax.plot(weather["Time_min"], weather["AirTemp"], label="Air temp (°C)")
    ax.plot(weather["Time_min"], weather["TrackTemp"], label="Track temp (°C)")
    ax.set_xlabel("Session time (min)")
    ax.set_ylabel("Temperature (°C)")
    ax.set_title("Weather during the session")
    ax.legend()
    return fig


def plot_position_changes(laps: pd.DataFrame, session):
    """Race position vs lap number for every driver."""
    fig, ax = _fig((11, 6))
    if laps.empty or "Position" not in laps.columns:
        ax.set_title("Position data is not available")
        ax.axis("off")
        return fig
    for driver, group in laps.groupby("Driver"):
        style = _driver_style(str(driver), session)
        ax.plot(group["LapNumber"], group["Position"], label=driver, **style)
    ax.set_xlabel("Lap")
    ax.set_ylabel("Position")
    ax.invert_yaxis()
    ax.set_title("Position changes")
    ax.legend(ncol=4, loc="lower right")
    return fig


def plot_quali_times(results: pd.DataFrame, session):
    """Horizontal bars of each driver's best qualifying segment time."""
    fig, ax = _fig((10, 6))
    if results.empty:
        ax.set_title("No qualifying results")
        ax.axis("off")
        return fig
    work = results.copy()
    work["Best_s"] = work[["Q1_s", "Q2_s", "Q3_s"]].min(axis=1, skipna=True)
    work = work.dropna(subset=["Best_s"]).sort_values("Best_s")
    if work.empty:
        ax.set_title("No qualifying times to plot")
        ax.axis("off")
        return fig
    colors = [
        _driver_style(str(row["Abbreviation"]), session)["color"]
        for _, row in work.iterrows()
    ]
    ax.barh(work["Abbreviation"], work["Best_s"], color=colors, edgecolor="black")
    ax.invert_yaxis()
    ax.set_xlabel("Best lap (s)")
    ax.set_title("Best qualifying lap per driver")
    return fig


def plot_lap_trace(laps: pd.DataFrame, session, drivers: list[str] | None = None):
    """Lap time vs lap number for selected drivers."""
    fig, ax = _fig((11, 5.5))
    pace = valid_pace(laps)
    if drivers:
        pace = pace[pace["Driver"].isin(drivers)]
    if pace.empty:
        ax.set_title("No valid pace laps for the selected drivers")
        ax.axis("off")
        return fig
    for driver, group in pace.groupby("Driver"):
        style = _driver_style(str(driver), session)
        ax.plot(group["LapNumber"], group["LapTime_s"], label=driver, **style)
    ax.set_xlabel("Lap")
    ax.set_ylabel("Lap time (s)")
    ax.set_title("Valid-pace lap times")
    ax.legend(ncol=4)
    return fig


def plot_strategy(stints: pd.DataFrame, session):
    """Horizontal tyre-stint bars (FastF1 compound colors)."""
    fig, ax = _fig((10, 7))
    if stints.empty:
        ax.set_title("No stint data")
        ax.axis("off")
        return fig

    drivers = []
    if session is not None:
        try:
            drivers = [
                session.get_driver(num)["Abbreviation"]
                for num in session.drivers
            ]
        except Exception:
            drivers = stints["Driver"].drop_duplicates().tolist()
    else:
        drivers = stints["Driver"].drop_duplicates().tolist()

    for driver in drivers:
        driver_stints = stints.loc[stints["Driver"] == driver]
        left = 0
        for _, row in driver_stints.iterrows():
            ax.barh(
                y=driver,
                width=row["StintLength"],
                left=left,
                color=_compound_color(row["Compound"], session),
                edgecolor="black",
            )
            left += row["StintLength"]

    ax.set_xlabel("Lap number")
    ax.set_title("Tyre strategy")
    ax.invert_yaxis()
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    return fig


def plot_stint_pace(stints: pd.DataFrame, session):
    """Stint length vs mean pace, colored by compound."""
    fig, ax = _fig((9, 5))
    data = stints.dropna(subset=["MeanPace_s"])
    if data.empty:
        ax.set_title("No stint pace to plot")
        ax.axis("off")
        return fig
    colors = [_compound_color(c, session) for c in data["Compound"]]
    ax.scatter(
        data["StintLength"], data["MeanPace_s"],
        c=colors, s=80, edgecolor="black",
    )
    for _, row in data.iterrows():
        ax.annotate(
            f"{row['Driver']} S{int(row['Stint'])}",
            (row["StintLength"], row["MeanPace_s"]),
            textcoords="offset points", xytext=(4, 4), fontsize=8,
        )
    ax.set_xlabel("Stint length (laps)")
    ax.set_ylabel("Mean valid pace (s)")
    ax.set_title("Stint length vs mean pace")
    return fig


def plot_telemetry_overlay(traces: dict[str, pd.DataFrame], session):
    """Speed / throttle / brake vs distance for one or two drivers."""
    fig, axes = plt.subplots(
        3, 1, figsize=(11, 8), sharex=True, layout="constrained"
    )
    if not traces:
        axes[0].set_title("No telemetry loaded")
        for ax in axes:
            ax.axis("off")
        return fig

    channels = [
        ("Speed", "Speed (km/h)"),
        ("Throttle", "Throttle (%)"),
        ("Brake", "Brake"),
    ]
    for ax, (col, ylabel) in zip(axes, channels):
        for driver, tel in traces.items():
            if col not in tel.columns or "Distance" not in tel.columns:
                continue
            style = _driver_style(driver, session)
            y = tel[col]
            if col == "Brake":
                y = y.astype(float)
            ax.plot(tel["Distance"], y, label=driver, **style)
        ax.set_ylabel(ylabel)
        ax.legend(loc="upper right")
    axes[-1].set_xlabel("Distance (m)")
    axes[0].set_title("Fastest-lap telemetry overlay")
    return fig


def plot_track_map(
        tel: pd.DataFrame,
        driver: str,
        corners: pd.DataFrame | None = None,
):
    """Speed-colored track outline from position telemetry."""
    fig, ax = plt.subplots(figsize=(10, 6.5), layout="constrained")
    needed = {"X", "Y", "Speed"}
    if tel.empty or not needed.issubset(tel.columns):
        ax.set_title("Position telemetry is not available")
        ax.axis("off")
        return fig

    x = tel["X"].to_numpy()
    y = tel["Y"].to_numpy()
    color = tel["Speed"].to_numpy()
    points = np.array([x, y]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)

    ax.plot(x, y, color="black", linewidth=12, zorder=0)
    norm = plt.Normalize(np.nanmin(color), np.nanmax(color))
    lc = LineCollection(
        segments, cmap=mpl.cm.plasma, norm=norm, linewidth=4,
    )
    lc.set_array(color)
    line = ax.add_collection(lc)
    fig.colorbar(line, ax=ax, label="Speed (km/h)", fraction=0.046)
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")
    ax.set_title(f"{driver} — speed on track (fastest lap)")

    if corners is not None and not corners.empty:
        for _, row in corners.iterrows():
            number = row.get("Number")
            letter = row.get("Letter") or ""
            label = f"{int(number)}{letter}" if pd.notna(number) else ""
            ax.text(
                row["X"], row["Y"], label, fontsize=8,
                ha="center", va="center", color="black",
                bbox={"boxstyle": "round,pad=0.15", "fc": "white", "alpha": 0.7},
            )
    return fig


def format_seconds(value: float | None) -> str:
    """Render seconds as m:ss.sss for tables and metrics."""
    if value is None or pd.isna(value):
        return "—"
    value = float(value)
    minutes = int(value // 60)
    seconds = value - 60 * minutes
    return f"{minutes}:{seconds:06.3f}"
