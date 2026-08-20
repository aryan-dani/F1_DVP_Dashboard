"""Defaults and lookup tables for the dashboard."""

DEFAULT_YEAR = 2024
DEFAULT_EVENT = "Italian Grand Prix"
DEFAULT_SESSION = "Race"

MIN_YEAR = 2018
MAX_YEAR = 2026

# F1 live-timing track status codes (first digit is the current flag).
TRACK_STATUS_MAP = {
    "1": "Green",
    "2": "Yellow",
    "3": "Unknown",
    "4": "Safety Car",
    "5": "Red Flag",
    "6": "VSC",
    "7": "VSC Ending",
}

RACE_LIKE = ("Race", "Sprint")
QUALI_LIKE = ("Qualifying", "Sprint Qualifying", "Sprint Shootout")

LAP_TIMEDELTA_COLS = (
    "Time",
    "LapTime",
    "PitOutTime",
    "PitInTime",
    "Sector1Time",
    "Sector2Time",
    "Sector3Time",
    "Sector1SessionTime",
    "Sector2SessionTime",
    "Sector3SessionTime",
    "LapStartTime",
)

RESULT_TIMEDELTA_COLS = ("Q1", "Q2", "Q3", "Time")
