"""Interactive Plotly figures for the dashboard."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.eda import valid_pace
from src.theme import (
    ACCENT,
    MUTED,
    TEXT,
    apply_layout,
    compound_color,
    driver_color,
    driver_dash,
    empty_figure,
    format_seconds,
    format_signed_seconds,
)


def _drivers(data: pd.DataFrame, drivers: list[str] | None = None) -> list[str]:
    if data.empty or "Driver" not in data.columns:
        return []
    present = data["Driver"].dropna().astype(str).unique().tolist()
    if not drivers:
        return present
    return [driver for driver in drivers if driver in present]


def _hover_time(series: pd.Series) -> list[str]:
    return [format_seconds(value) for value in series]


def _hover_signed(series: pd.Series) -> list[str]:
    return [format_signed_seconds(value) for value in series]


def _phase_color(status: str) -> str | None:
    """Faint band used behind lap-axis charts. Green stays unmarked."""
    text = str(status).lower()
    if "red" in text:
        return "rgba(225, 6, 0, 0.22)"
    if "safety" in text:
        return "rgba(245, 208, 0, 0.28)"
    if "vsc" in text:
        return "rgba(255, 159, 28, 0.22)"
    if "yellow" in text:
        return "rgba(245, 208, 0, 0.16)"
    return None


def _phase_swatch(status: str) -> str:
    """Solid colour for the track-status timeline."""
    text = str(status).lower()
    if "red" in text:
        return "#E10600"
    if "safety" in text:
        return "#C9A000"
    if "vsc" in text:
        return "#FF9F1C"
    if "yellow" in text:
        return "#F5D000"
    return "#2E7D32"


def _add_phase_bands(fig, phases: pd.DataFrame | None) -> None:
    if phases is None or phases.empty:
        return
    for phase in phases.itertuples(index=False):
        color = _phase_color(phase.Status)
        if color is None:
            continue
        fig.add_vrect(
            x0=float(phase.LapStart) - 0.5,
            x1=float(phase.LapEnd) + 0.5,
            fillcolor=color,
            line_width=0,
            layer="below",
        )


def _driver_lines(
        fig,
        data: pd.DataFrame,
        x: str,
        y: str,
        session,
        *,
        hover_col: str | None = None,
        y_title: str = "",
) -> None:
    names = _drivers(data)
    for index, driver in enumerate(names):
        group = data.loc[data["Driver"].astype(str) == driver].sort_values(x)
        use_hover = bool(hover_col and hover_col in group.columns)
        fig.add_trace(go.Scatter(
            x=group[x],
            y=group[y],
            mode="lines",
            name=driver,
            legendgroup=driver,
            line=dict(
                color=driver_color(driver, session, index),
                dash=driver_dash(driver, session),
                width=2,
            ),
            hovertext=group[hover_col] if use_hover else None,
            hovertemplate=(
                f"%{{fullData.name}}<br>{y_title or y} %{{hovertext}}<br>lap %{{x}}<extra></extra>"
                if use_hover else
                f"%{{fullData.name}}<br>{y_title or y} %{{y}}<br>lap %{{x}}<extra></extra>"
            ),
        ))


def plot_missingness(missing: pd.DataFrame):
    """Horizontal bars of missing-value percentages."""
    title = "Missing values by column"
    if missing is None or missing.empty or "missing" not in missing.columns:
        return empty_figure(title, "No missing-value summary")
    data = missing.loc[missing["missing"] > 0].head(20)
    if data.empty:
        return empty_figure(title, "No missing values in the processed table")
    fig = go.Figure(go.Bar(
        x=data["pct"],
        y=data["column"],
        orientation="h",
        marker_color=ACCENT,
        hovertemplate="%{y}: %{x:.1f}%<extra></extra>",
    ))
    fig.update_yaxes(autorange="reversed", title="")
    fig.update_xaxes(title="Missing (%)")
    return apply_layout(fig, title, height=max(360, 28 * len(data)))


def plot_laptime_distribution(laps: pd.DataFrame):
    """Histogram of valid-pace lap times."""
    title = "Valid-pace lap time distribution"
    pace = valid_pace(laps)
    if pace.empty or "LapTime_s" not in pace.columns:
        return empty_figure(title, "No valid pace laps to plot")
    fig = go.Figure(go.Histogram(
        x=pace["LapTime_s"],
        nbinsx=30,
        marker_color=ACCENT,
        opacity=0.9,
        hovertemplate="Lap time %{x:.3f}s<br>Count %{y}<extra></extra>",
    ))
    fig.update_xaxes(title="Lap time (s)")
    fig.update_yaxes(title="Count")
    return apply_layout(fig, title, height=420)


def plot_laptimes_by_driver(laps: pd.DataFrame, session=None):
    """Box plots of valid pace, ordered from fastest median to slowest."""
    title = "Lap time spread by driver"
    pace = valid_pace(laps)
    if pace.empty or "LapTime_s" not in pace.columns:
        return empty_figure(title, "No valid pace laps to plot")
    order = (
        pace.groupby(pace["Driver"].astype(str))["LapTime_s"]
        .median()
        .sort_values()
        .index
        .tolist()
    )
    fig = go.Figure()
    for index, driver in enumerate(order):
        group = pace.loc[pace["Driver"].astype(str) == driver, "LapTime_s"]
        fig.add_trace(go.Box(
            y=group,
            name=driver,
            marker_color=driver_color(driver, session, index),
            line_color=driver_color(driver, session, index),
            hovertext=[format_seconds(value) for value in group],
            hovertemplate="%{fullData.name}<br>%{hovertext}<extra></extra>",
        ))
    fig.update_yaxes(title="Lap time (s)")
    return apply_layout(fig, title, height=480)


def plot_correlation_heatmap(corr: pd.DataFrame):
    """Pearson correlation heatmap."""
    title = "Pearson correlation (valid pace laps)"
    if corr is None or corr.empty:
        return empty_figure(title, "Not enough numeric columns for a correlation matrix")
    text = np.round(corr.to_numpy(dtype=float), 2)
    fig = go.Figure(go.Heatmap(
        z=corr.to_numpy(dtype=float),
        x=list(corr.columns),
        y=list(corr.index),
        colorscale="RdBu",
        zmid=0,
        text=text,
        texttemplate="%{text:.2f}",
        textfont=dict(size=10, color=TEXT),
        hovertemplate="%{y} vs %{x}: %{z:.2f}<extra></extra>",
        colorbar=dict(title="r"),
    ))
    return apply_layout(fig, title, height=640)


def plot_category_counts(counts: pd.DataFrame):
    """Bar chart of lap cleaning categories."""
    title = "Lap categories after preprocessing"
    if counts is None or counts.empty:
        return empty_figure(title, "No lap categories")
    fig = go.Figure(go.Bar(
        x=counts["LapCategory"],
        y=counts["count"],
        marker_color=ACCENT,
        hovertemplate="%{x}: %{y} laps<extra></extra>",
    ))
    fig.update_yaxes(title="Laps")
    return apply_layout(fig, title, height=380)


def plot_weather(weather: pd.DataFrame):
    """Air and track temperature, with rainfall on a second axis."""
    title = "Weather during the session"
    if weather is None or weather.empty or "Time_min" not in weather.columns:
        return empty_figure(title, "Weather data is not available for this session")
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    if "AirTemp" in weather.columns:
        fig.add_trace(go.Scatter(
            x=weather["Time_min"],
            y=weather["AirTemp"],
            name="Air temp",
            line=dict(color="#FF8700", width=2),
            hovertemplate="Air %{y:.1f}°C<extra></extra>",
        ), secondary_y=False)
    if "TrackTemp" in weather.columns:
        fig.add_trace(go.Scatter(
            x=weather["Time_min"],
            y=weather["TrackTemp"],
            name="Track temp",
            line=dict(color=ACCENT, width=2),
            hovertemplate="Track %{y:.1f}°C<extra></extra>",
        ), secondary_y=False)
    if "Rainfall" in weather.columns:
        rain = weather["Rainfall"].fillna(False).astype(bool).astype(int)
        fig.add_trace(go.Bar(
            x=weather["Time_min"],
            y=rain,
            name="Rain",
            marker_color="rgba(76, 154, 255, 0.45)",
            hovertemplate="Rain %{y}<extra></extra>",
        ), secondary_y=True)
    fig.update_xaxes(title="Session time (min)")
    fig.update_yaxes(title="Temperature (°C)", secondary_y=False)
    fig.update_yaxes(title="Rain", secondary_y=True, range=[0, 1.2], showgrid=False)
    return apply_layout(fig, title, height=420)


def plot_position_changes(laps: pd.DataFrame, session=None):
    """Race position versus lap number."""
    title = "Position changes"
    if laps is None or laps.empty or "Position" not in laps.columns:
        return empty_figure(title, "Position data is not available")
    fig = go.Figure()
    _driver_lines(fig, laps, "LapNumber", "Position", session, y_title="P")
    if not fig.data:
        return empty_figure(title, "Position data is not available")
    fig.update_yaxes(title="Position", autorange="reversed")
    fig.update_xaxes(title="Lap")
    return apply_layout(fig, title, hovermode="x unified", height=560)


def plot_gap_to_leader(laps: pd.DataFrame, session=None):
    """Gap to the leader at the end of each lap."""
    title = "Gap to leader"
    if laps is None or laps.empty or "GapToLeader_s" not in laps.columns:
        return empty_figure(title, "Gap to leader is not available")
    work = laps.dropna(subset=["GapToLeader_s"]).copy()
    work["GapText"] = _hover_signed(work["GapToLeader_s"])
    fig = go.Figure()
    _driver_lines(fig, work, "LapNumber", "GapToLeader_s", session, hover_col="GapText", y_title="gap")
    if not fig.data:
        return empty_figure(title, "Gap to leader is not available")
    fig.update_yaxes(title="Gap (s)")
    fig.update_xaxes(title="Lap")
    return apply_layout(fig, title, hovermode="x unified", height=520)


def plot_intervals(laps: pd.DataFrame, session=None):
    """Interval to the car one position ahead."""
    title = "Interval to the car ahead"
    if laps is None or laps.empty or "Interval_s" not in laps.columns:
        return empty_figure(title, "Interval data is not available")
    work = laps.dropna(subset=["Interval_s"]).copy()
    work["IntervalText"] = _hover_signed(work["Interval_s"])
    fig = go.Figure()
    _driver_lines(
        fig, work, "LapNumber", "Interval_s", session,
        hover_col="IntervalText", y_title="interval",
    )
    if not fig.data:
        return empty_figure(title, "Interval data is not available")
    fig.update_yaxes(title="Interval (s)")
    fig.update_xaxes(title="Lap")
    return apply_layout(fig, title, hovermode="x unified", height=520)


def plot_quali_segments(results: pd.DataFrame, session=None):
    """Q1, Q2, and Q3 times for each driver."""
    title = "Qualifying segments"
    needed = {"Abbreviation", "Q1_s", "Q2_s", "Q3_s"}
    if results is None or results.empty or not needed.issubset(results.columns):
        return empty_figure(title, "No qualifying times to plot")
    work = results.copy()
    work["Best_s"] = work[["Q1_s", "Q2_s", "Q3_s"]].min(axis=1, skipna=True)
    work = work.dropna(subset=["Best_s"]).sort_values("Best_s")
    if work.empty:
        return empty_figure(title, "No qualifying times to plot")
    fig = go.Figure()
    colors = {"Q1": "#8A8A96", "Q2": "#F5D000", "Q3": ACCENT}
    for segment in ("Q1", "Q2", "Q3"):
        column = f"{segment}_s"
        fig.add_trace(go.Bar(
            x=work["Abbreviation"],
            y=work[column],
            name=segment,
            marker_color=colors[segment],
            hovertext=[format_seconds(value) for value in work[column]],
            hovertemplate="%{x} %{fullData.name}: %{hovertext}<extra></extra>",
        ))
    fig.update_layout(barmode="group")
    fig.update_yaxes(title="Time (s)")
    return apply_layout(fig, title, height=480)


def plot_practice_pace(split: pd.DataFrame, session=None):
    """Short-run best lap versus long-run mean pace."""
    title = "One-lap pace versus long-run pace"
    if split is None or split.empty:
        return empty_figure(title, "No practice pace to plot")
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=split["Driver"],
        y=split["ShortRun_s"],
        name="Best of fastest 3",
        marker_color=ACCENT,
        hovertext=[format_seconds(value) for value in split["ShortRun_s"]],
        hovertemplate="%{x} short run %{hovertext}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=split["Driver"],
        y=split["LongRun_s"],
        name="Mean of the other laps",
        marker_color="#00A3E0",
        hovertext=[format_seconds(value) for value in split["LongRun_s"]],
        hovertemplate="%{x} long run %{hovertext}<extra></extra>",
    ))
    fig.update_layout(barmode="group")
    fig.update_yaxes(title="Lap time (s)")
    return apply_layout(fig, title, height=480)


def plot_lap_trace(laps: pd.DataFrame, session=None, drivers: list[str] | None = None):
    """Valid-pace lap time versus lap number."""
    title = "Valid-pace lap times"
    pace = valid_pace(laps)
    if drivers:
        pace = pace.loc[pace["Driver"].astype(str).isin(drivers)]
    if pace.empty:
        return empty_figure(title, "No valid pace laps for the selected drivers")
    work = pace.copy()
    work["LapText"] = _hover_time(work["LapTime_s"])
    fig = go.Figure()
    names = _drivers(work, drivers)
    for index, driver in enumerate(names):
        group = work.loc[work["Driver"].astype(str) == driver].sort_values("LapNumber")
        fig.add_trace(go.Scatter(
            x=group["LapNumber"],
            y=group["LapTime_s"],
            mode="lines+markers",
            name=driver,
            marker=dict(size=6, color=driver_color(driver, session, index)),
            line=dict(
                color=driver_color(driver, session, index),
                dash=driver_dash(driver, session),
                width=2,
            ),
            hovertext=group["LapText"],
            hovertemplate="%{fullData.name}<br>%{hovertext}<br>lap %{x}<extra></extra>",
        ))
    fig.update_xaxes(title="Lap")
    fig.update_yaxes(title="Lap time (s)")
    return apply_layout(fig, title, hovermode="x unified", height=520)


def plot_sectors(summary: pd.DataFrame, session=None):
    """Best sector times, grouped by driver."""
    title = "Best sector times"
    if summary is None or summary.empty:
        return empty_figure(title, "No sector times to plot")
    fig = go.Figure()
    palette = {"BestS1": "#E10600", "BestS2": "#F5D000", "BestS3": "#00A3E0"}
    labels = {"BestS1": "Sector 1", "BestS2": "Sector 2", "BestS3": "Sector 3"}
    for column, label in labels.items():
        if column not in summary.columns:
            continue
        fig.add_trace(go.Bar(
            x=summary["Driver"],
            y=summary[column],
            name=label,
            marker_color=palette[column],
            hovertext=[format_seconds(value) for value in summary[column]],
            hovertemplate="%{x} %{fullData.name}: %{hovertext}<extra></extra>",
        ))
    if not fig.data:
        return empty_figure(title, "No sector times to plot")
    fig.update_layout(barmode="group")
    fig.update_yaxes(title="Best sector (s)")
    return apply_layout(fig, title, height=480)


def plot_degradation(laps: pd.DataFrame, session=None, drivers: list[str] | None = None):
    """Lap time against lap-in-stint, one line per driver and stint."""
    title = "Tyre degradation"
    pace = valid_pace(laps)
    if drivers:
        pace = pace.loc[pace["Driver"].astype(str).isin(drivers)]
    needed = {"Driver", "Stint", "StintLap", "LapTime_s"}
    if pace.empty or not needed.issubset(pace.columns):
        return empty_figure(title, "No valid pace laps for a degradation trace")
    fig = go.Figure()
    names = _drivers(pace, drivers)
    for index, driver in enumerate(names):
        group = pace.loc[pace["Driver"].astype(str) == driver]
        for stint, stint_rows in group.groupby("Stint"):
            stint_rows = stint_rows.sort_values("StintLap")
            compound = ""
            if "Compound" in stint_rows.columns and stint_rows["Compound"].notna().any():
                compound = str(stint_rows["Compound"].iloc[0])
            label = f"{driver} S{int(float(stint))}"
            if compound:
                label = f"{label} {compound}"
            fig.add_trace(go.Scatter(
                x=stint_rows["StintLap"],
                y=stint_rows["LapTime_s"],
                mode="lines+markers",
                name=label,
                legendgroup=driver,
                marker=dict(size=6, color=driver_color(driver, session, index)),
                line=dict(color=driver_color(driver, session, index), width=2),
                hovertext=[format_seconds(value) for value in stint_rows["LapTime_s"]],
                hovertemplate="%{fullData.name}<br>%{hovertext}<br>stint lap %{x}<extra></extra>",
            ))
    if not fig.data:
        return empty_figure(title, "No valid pace laps for a degradation trace")
    fig.update_xaxes(title="Lap in stint")
    fig.update_yaxes(title="Lap time (s)")
    return apply_layout(fig, title, height=520)


def plot_strategy(stints: pd.DataFrame, session=None, phases: pd.DataFrame | None = None):
    """Horizontal stint bars coloured by compound. A legend click isolates a driver."""
    title = "Tyre strategy"
    if stints is None or stints.empty:
        return empty_figure(title, "No stint data")
    fig = go.Figure()
    drivers = stints["Driver"].astype(str).drop_duplicates().tolist()
    for index, driver in enumerate(drivers):
        rows = stints.loc[stints["Driver"].astype(str) == driver].sort_values("Stint")
        hover = []
        colors = []
        for row in rows.itertuples(index=False):
            slope = getattr(row, "DegSlope_s", np.nan)
            slope_text = "—" if pd.isna(slope) else f"{float(slope):+.3f} s/lap"
            pace = format_seconds(getattr(row, "MeanPace_s", None))
            hover.append(
                f"{driver} {row.Compound}<br>"
                f"Laps {int(row.StintStart)}–{int(row.StintEnd)}<br>"
                f"Mean {pace}<br>Degradation {slope_text}"
            )
            colors.append(compound_color(row.Compound, session))
        fig.add_trace(go.Bar(
            y=[driver] * len(rows),
            x=rows["StintLength"],
            base=rows["StintStart"].astype(float) - 1,
            orientation="h",
            name=driver,
            marker_color=colors,
            marker_line_color="#0E0E12",
            marker_line_width=1,
            hovertext=hover,
            hovertemplate="%{hovertext}<extra></extra>",
        ))
    fig.update_layout(barmode="overlay")
    fig.update_yaxes(
        title="",
        categoryorder="array",
        categoryarray=list(reversed(drivers)),
    )
    fig.update_xaxes(title="Lap")
    _add_phase_bands(fig, phases)
    return apply_layout(fig, title, height=max(420, 36 * len(drivers)))


def plot_stint_pace(stints: pd.DataFrame, session=None):
    """Stint length versus mean valid pace."""
    title = "Stint length versus mean pace"
    if stints is None or stints.empty or "MeanPace_s" not in stints.columns:
        return empty_figure(title, "No stint pace to plot")
    data = stints.dropna(subset=["MeanPace_s"])
    if data.empty:
        return empty_figure(title, "No stint pace to plot")
    fig = go.Figure()
    for compound, group in data.groupby(data["Compound"].astype(str)):
        fig.add_trace(go.Scatter(
            x=group["StintLength"],
            y=group["MeanPace_s"],
            mode="markers",
            name=str(compound),
            marker=dict(
                size=12,
                color=compound_color(compound, session),
                line=dict(color="#0E0E12", width=1),
            ),
            text=[
                f"{row.Driver} S{int(float(row.Stint))}"
                for row in group.itertuples(index=False)
            ],
            hovertext=[format_seconds(value) for value in group["MeanPace_s"]],
            hovertemplate="%{text}<br>%{hovertext}<br>%{x} laps<extra></extra>",
        ))
    fig.update_xaxes(title="Stint length (laps)")
    fig.update_yaxes(title="Mean valid pace (s)")
    return apply_layout(fig, title, height=480)


def plot_places(results: pd.DataFrame, session=None):
    """Places gained from grid to finish."""
    title = "Grid to finish"
    if results is None or results.empty or "PlacesGained" not in results.columns:
        return empty_figure(title, "Grid and finish positions are not both available")
    label = "Abbreviation" if "Abbreviation" in results.columns else "Driver"
    work = results.dropna(subset=["PlacesGained", label]).sort_values("PlacesGained")
    if work.empty:
        return empty_figure(title, "Grid and finish positions are not both available")
    fig = go.Figure(go.Bar(
        y=work[label].astype(str),
        x=work["PlacesGained"],
        orientation="h",
        marker_color=[
            driver_color(driver, session, index)
            for index, driver in enumerate(work[label].astype(str))
        ],
        hovertemplate="%{y}: %{x:+.0f} places<extra></extra>",
    ))
    fig.update_xaxes(title="Places gained")
    return apply_layout(fig, title, height=max(420, 28 * len(work)))


def plot_status_timeline(phases: pd.DataFrame):
    """One band per track-status phase across the lap axis."""
    title = "Track status"
    if phases is None or phases.empty:
        return empty_figure(title, "No track-status phases")
    fig = go.Figure()
    for phase in phases.itertuples(index=False):
        color = _phase_swatch(phase.Status)
        length = int(phase.LapEnd) - int(phase.LapStart) + 1
        fig.add_trace(go.Bar(
            x=[length],
            base=[int(phase.LapStart) - 1],
            y=["Status"],
            orientation="h",
            marker_color=color,
            name=str(phase.Status),
            showlegend=False,
            hovertemplate=f"{phase.Status}: laps {int(phase.LapStart)}–{int(phase.LapEnd)}<extra></extra>",
        ))
    fig.update_layout(barmode="overlay")
    fig.update_xaxes(title="Lap")
    fig.update_yaxes(title="")
    return apply_layout(fig, title, height=200)


def _thin(frame: pd.DataFrame, max_points: int = 900) -> pd.DataFrame:
    if len(frame) <= max_points:
        return frame
    step = max(1, len(frame) // max_points)
    return frame.iloc[::step]


def plot_telemetry(traces: dict[str, pd.DataFrame], session=None, corners: pd.DataFrame | None = None):
    """Speed, throttle, brake, gear, RPM, and DRS versus distance."""
    title = "Fastest-lap telemetry"
    channels = [
        ("Speed", "Speed (km/h)"),
        ("Throttle", "Throttle (%)"),
        ("Brake", "Brake"),
        ("nGear", "Gear"),
        ("RPM", "RPM"),
        ("DRS", "DRS"),
    ]
    if not traces:
        return empty_figure(title, "No telemetry loaded")
    present = [
        (column, label)
        for column, label in channels
        if any(column in frame.columns for frame in traces.values())
    ]
    if not present:
        return empty_figure(title, "Telemetry channels are missing")
    fig = make_subplots(
        rows=len(present),
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        subplot_titles=tuple(label for _, label in present),
    )
    for index, (driver, frame) in enumerate(traces.items()):
        sample = _thin(frame)
        color = driver_color(driver, session, index)
        dash = driver_dash(driver, session)
        for row, (column, _label) in enumerate(present, start=1):
            if column not in sample.columns or "Distance" not in sample.columns:
                continue
            y = sample[column]
            if column in {"Brake", "DRS"}:
                y = y.astype(float)
            fig.add_trace(go.Scatter(
                x=sample["Distance"],
                y=y,
                mode="lines",
                name=driver,
                legendgroup=driver,
                showlegend=(row == 1),
                line=dict(color=color, dash=dash, width=1.6),
                hovertemplate=f"{driver}<br>%{{y:.2f}}<br>%{{x:.0f}} m<extra></extra>",
            ), row=row, col=1)
    if corners is not None and not corners.empty and "Distance" in corners.columns:
        for corner in corners.itertuples(index=False):
            distance = getattr(corner, "Distance", None)
            if distance is None or pd.isna(distance):
                continue
            number = getattr(corner, "Number", "")
            letter = getattr(corner, "Letter", "") or ""
            label = f"{int(number)}{letter}" if pd.notna(number) else ""
            fig.add_vline(
                x=float(distance),
                line_dash="dot",
                line_color="#5A5A68",
                line_width=1,
                annotation_text=label,
                annotation_position="top",
                annotation_font_size=9,
                annotation_font_color=MUTED,
                row=1,
                col=1,
            )
    fig.update_xaxes(title_text="Distance (m)", row=len(present), col=1)
    return apply_layout(fig, title, hovermode="x unified", height=220 * len(present) + 80)


def plot_lap_delta(delta: pd.Series, reference_telemetry: pd.DataFrame, reference: str, compare: str):
    """Fastest-lap time delta. Positive means the compared driver is slower."""
    title = f"Delta: {compare} versus {reference}"
    if delta is None or reference_telemetry is None or reference_telemetry.empty:
        return empty_figure(title, "No delta for these laps")
    y = pd.to_numeric(pd.Series(delta), errors="coerce")
    if "Distance" in reference_telemetry.columns:
        distance = pd.to_numeric(reference_telemetry["Distance"], errors="coerce")
    else:
        distance = pd.Series(range(len(y)), dtype=float)
    length = min(len(distance), len(y))
    frame = pd.DataFrame({"Distance": distance.iloc[:length].to_numpy(), "Delta": y.iloc[:length].to_numpy()})
    frame = frame.dropna()
    frame = _thin(frame, max_points=900)
    if frame.empty:
        return empty_figure(title, "No delta for these laps")
    fig = go.Figure(go.Scatter(
        x=frame["Distance"],
        y=frame["Delta"],
        mode="lines",
        name=compare,
        line=dict(color=ACCENT, width=2),
        hovertext=[format_signed_seconds(value) for value in frame["Delta"]],
        hovertemplate="%{hovertext}<br>%{x:.0f} m<extra></extra>",
    ))
    fig.add_hline(y=0, line_dash="dot", line_color=MUTED)
    fig.update_xaxes(title="Distance (m)")
    fig.update_yaxes(title="Delta (s)")
    return apply_layout(fig, title, height=420)


def plot_track_map(
        telemetry: pd.DataFrame,
        driver: str,
        *,
        channel: str = "Speed",
        label: str | None = None,
        corners: pd.DataFrame | None = None,
):
    """Track outline coloured by a telemetry channel."""
    shown = label or channel
    title = f"{driver} — {shown} on track"
    needed = {"X", "Y", channel}
    if telemetry is None or telemetry.empty or not needed.issubset(telemetry.columns):
        return empty_figure(title, "Position telemetry is not available")
    sample = _thin(telemetry.dropna(subset=["X", "Y", channel]), max_points=1600)
    if sample.empty:
        return empty_figure(title, "Position telemetry is not available")
    fig = go.Figure(go.Scatter(
        x=sample["X"],
        y=sample["Y"],
        mode="markers",
        name=driver,
        marker=dict(
            size=4,
            color=sample[channel],
            colorscale="Plasma",
            showscale=True,
            colorbar=dict(title=shown),
        ),
        hovertemplate=f"{channel} %{{marker.color:.0f}}<extra>{driver}</extra>",
    ))
    if corners is not None and not corners.empty and {"X", "Y"}.issubset(corners.columns):
        labels = []
        for row in corners.itertuples(index=False):
            number = getattr(row, "Number", None)
            letter = getattr(row, "Letter", "") or ""
            labels.append(f"{int(number)}{letter}" if pd.notna(number) else "")
        fig.add_trace(go.Scatter(
            x=corners["X"],
            y=corners["Y"],
            mode="text",
            text=labels,
            textfont=dict(color="#FFFFFF", size=11),
            hoverinfo="skip",
            showlegend=False,
        ))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False, scaleanchor="x", scaleratio=1)
    return apply_layout(fig, title, height=680)


def plot_standings(frame: pd.DataFrame, label: str, value: str, title: str):
    """Horizontal points bar, leader at the top."""
    if frame is None or frame.empty or label not in frame.columns or value not in frame.columns:
        return empty_figure(title, "No standings returned")
    work = frame.sort_values(value, ascending=True)
    fig = go.Figure(go.Bar(
        y=work[label].astype(str),
        x=work[value],
        orientation="h",
        marker_color=ACCENT,
        text=work[value],
        textposition="outside",
        textfont=dict(color=TEXT),
        hovertemplate="%{y}: %{x}<extra></extra>",
    ))
    fig.update_xaxes(title="Points")
    return apply_layout(fig, title, height=max(420, 28 * len(work)))


def plot_position_heatmap(results: pd.DataFrame, driver_order: list[str] | None = None):
    """Finishing position by round. Lower numbers use the bright end of the scale."""
    title = "Finishing position by round"
    if results is None or results.empty:
        return empty_figure(title, "No race results for this season")
    work = results.dropna(subset=["Position"]).copy()
    if work.empty:
        return empty_figure(title, "No race results for this season")
    if driver_order:
        order = [code for code in driver_order if code in set(work["Code"].astype(str))]
        missing = [code for code in work["Code"].astype(str).unique() if code not in order]
        order.extend(missing)
    else:
        order = work["Code"].astype(str).drop_duplicates().tolist()
    pivot = work.pivot_table(index="Code", columns="Round", values="Position", aggfunc="first")
    pivot = pivot.reindex(order)
    race_names = (
        work.sort_values("Round")
        .drop_duplicates("Round")
        .set_index("Round")["Race"]
        .to_dict()
    )
    rounds = list(pivot.columns)
    hover = []
    for code in pivot.index:
        row = []
        for rnd in rounds:
            position = pivot.loc[code, rnd]
            race = race_names.get(rnd, f"Round {rnd}")
            if pd.isna(position):
                row.append(f"{code}<br>{race}<br>no result")
            else:
                row.append(f"{code}<br>{race}<br>P{int(position)}")
        hover.append(row)
    fig = go.Figure(go.Heatmap(
        z=pivot.to_numpy(dtype=float),
        x=[str(rnd) for rnd in rounds],
        y=list(pivot.index),
        colorscale="RdYlGn_r",
        zmin=1,
        zmax=20,
        text=hover,
        hovertemplate="%{text}<extra></extra>",
        colorbar=dict(title="Pos"),
    ))
    fig.update_xaxes(title="Round")
    fig.update_yaxes(autorange="reversed")
    return apply_layout(fig, title, height=max(480, 26 * len(pivot.index)))


def plot_points(points: pd.DataFrame, limit: int = 8):
    """Cumulative points for the drivers who finish the year highest."""
    title = "Points over the season"
    if points is None or points.empty:
        return empty_figure(title, "No points history")
    final = points.sort_values("Round").groupby("Code", as_index=False).tail(1)
    keep = set(final.nlargest(limit, "Cumulative")["Code"].astype(str))
    work = points.loc[points["Code"].astype(str).isin(keep)].copy()
    fig = go.Figure()
    for index, code in enumerate(final.sort_values("Cumulative", ascending=False)["Code"].astype(str)):
        if code not in keep:
            continue
        group = work.loc[work["Code"].astype(str) == code].sort_values("Round")
        fig.add_trace(go.Scatter(
            x=group["Round"],
            y=group["Cumulative"],
            mode="lines+markers",
            name=code,
            line=dict(color=driver_color(code, None, index), width=2),
            hovertemplate=f"{code}<br>R%{{x}}: %{{y}} pts<extra></extra>",
        ))
    fig.update_xaxes(title="Round")
    fig.update_yaxes(title="Points")
    return apply_layout(fig, title, hovermode="x unified", height=520)
