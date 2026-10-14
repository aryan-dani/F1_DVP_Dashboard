"""Plotly theme, FastF1 colours, and timing formatters."""

from __future__ import annotations

import pandas as pd

import fastf1.plotting


BG = "#0E0E12"
PLOT = "#14141c"
TEXT = "#F5F5F5"
MUTED = "#C8C8D0"
GRID = "#2A2A34"
ACCENT = "#E10600"

_PALETTE = (
    "#E10600",
    "#00A3E0",
    "#FF8700",
    "#27F4D2",
    "#3671C6",
    "#6692FF",
    "#64C4FF",
    "#52E252",
    "#B6BABD",
    "#FFD700",
)

_COMPOUND_FALLBACK = {
    "SOFT": "#FF2B2B",
    "MEDIUM": "#F5D000",
    "HARD": "#F2F2F2",
    "INTERMEDIATE": "#43B02A",
    "WET": "#2B6CB0",
    "TEST-UNKNOWN": "#888888",
}

_DASH = {
    "-": "solid",
    "--": "dash",
    ":": "dot",
    "-.": "dashdot",
}


def format_seconds(value: float | None) -> str:
    """Render seconds as m:ss.sss."""
    if value is None or pd.isna(value):
        return "—"
    value = float(value)
    sign = "-" if value < 0 else ""
    value = abs(value)
    minutes = int(value // 60)
    seconds = value - 60 * minutes
    return f"{sign}{minutes}:{seconds:06.3f}"


def format_signed_seconds(value: float | None) -> str:
    """Render a delta as +m:ss.sss."""
    if value is None or pd.isna(value):
        return "—"
    number = float(value)
    text = format_seconds(abs(number))
    if number > 0:
        return f"+{text}"
    if number < 0:
        return f"-{text}"
    return text


def driver_style(driver: str, session) -> dict:
    """Colour and Plotly dash for a driver. Safe when session is missing."""
    try:
        style = fastf1.plotting.get_driver_style(
            str(driver),
            ["color", "linestyle"],
            session,
        )
        color = style.get("color") or None
        dash = _DASH.get(style.get("linestyle", "-"), "solid")
        if color:
            return {"color": color, "dash": dash}
    except Exception:
        pass
    return {"color": "", "dash": "solid"}


def driver_color(driver: str, session, index: int = 0) -> str:
    """Team colour, or a fallback swatch when FastF1 has no style."""
    color = driver_style(driver, session)["color"]
    if color:
        return color
    return _PALETTE[index % len(_PALETTE)]


def driver_dash(driver: str, session) -> str:
    """Line dash so teammates who share a colour stay distinct."""
    return driver_style(driver, session)["dash"]


def compound_color(compound: str, session) -> str:
    """Official compound colour, with a fixed fallback."""
    try:
        return fastf1.plotting.get_compound_color(str(compound), session)
    except Exception:
        return _COMPOUND_FALLBACK.get(str(compound).upper(), "#888888")


def apply_layout(fig, title: str, *, hovermode: str = "closest", height: int | None = None):
    """Dark layout. A legend click isolates that series."""
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color=TEXT)),
        paper_bgcolor=BG,
        plot_bgcolor=PLOT,
        font=dict(color=TEXT, size=12),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            x=0,
            font=dict(color=TEXT, size=11),
            itemclick="toggleothers",
            itemdoubleclick="toggle",
        ),
        margin=dict(l=56, r=24, t=72, b=40),
        hovermode=hovermode,
        height=height,
    )
    fig.update_xaxes(gridcolor=GRID, zerolinecolor=GRID, color=MUTED, title_font=dict(color=MUTED))
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=GRID, color=MUTED, title_font=dict(color=MUTED))
    return fig


def empty_figure(title: str, message: str):
    """A titled figure with a single note, used when a slice has no rows."""
    import plotly.graph_objects as go

    fig = go.Figure()
    fig.add_annotation(
        text=message,
        showarrow=False,
        font=dict(color=MUTED, size=14),
    )
    return apply_layout(fig, title, height=320)
