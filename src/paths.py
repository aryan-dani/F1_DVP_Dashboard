"""Filesystem locations for the dashboard app."""

from pathlib import Path


DASHBOARD_ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = DASHBOARD_ROOT / ".fastf1_cache"
PROCESSED_DIR = DASHBOARD_ROOT / "data" / "processed"
