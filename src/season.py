"""Season standings and results from Jolpica, cached on disk.

This module never calls ``fetch_session``. A full championship is a few
JSON documents, not 24 telemetry downloads.
"""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd

from src.paths import CACHE_DIR


JOLPICA_ROOT = "https://api.jolpi.ca/ergast/f1"
_USER_AGENT = "F1_DVP_Dashboard"


def _cache_path(name: str):
    folder = CACHE_DIR / "jolpica"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / name


def _fetch_json(url: str) -> dict:
    request = Request(url, headers={"User-Agent": _USER_AGENT, "Accept": "application/json"})
    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Jolpica request failed for {url}") from exc


def _get_json(url: str, cache_name: str) -> dict:
    path = _cache_path(cache_name)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    payload = _fetch_json(url)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return payload


def _driver_code(driver: dict) -> str:
    code = driver.get("code")
    if code:
        return str(code)
    driver_id = str(driver.get("driverId") or "")
    return driver_id[:3].upper()


def _driver_name(driver: dict) -> str:
    given = str(driver.get("givenName") or "").strip()
    family = str(driver.get("familyName") or "").strip()
    return f"{given} {family}".strip() or _driver_code(driver)


def _as_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_driver_standings(payload: dict) -> pd.DataFrame:
    """Flatten a Jolpica driverStandings document."""
    columns = ["Position", "Code", "Driver", "Team", "Points", "Wins"]
    lists = (
        payload.get("MRData", {})
        .get("StandingsTable", {})
        .get("StandingsLists", [])
    )
    if not lists:
        return pd.DataFrame(columns=columns)
    rows = []
    for row in lists[0].get("DriverStandings", []):
        driver = row.get("Driver") or {}
        constructors = row.get("Constructors") or [{}]
        team = constructors[0].get("name", "") if constructors else ""
        position = _as_int(row.get("position"))
        if position is None:
            continue
        rows.append({
            "Position": position,
            "Code": _driver_code(driver),
            "Driver": _driver_name(driver),
            "Team": str(team),
            "Points": float(row.get("points") or 0),
            "Wins": int(row.get("wins") or 0),
        })
    return pd.DataFrame(rows, columns=columns)


def parse_constructor_standings(payload: dict) -> pd.DataFrame:
    """Flatten a Jolpica constructorStandings document."""
    columns = ["Position", "Team", "Points", "Wins"]
    lists = (
        payload.get("MRData", {})
        .get("StandingsTable", {})
        .get("StandingsLists", [])
    )
    if not lists:
        return pd.DataFrame(columns=columns)
    rows = []
    for row in lists[0].get("ConstructorStandings", []):
        constructor = row.get("Constructor") or {}
        position = _as_int(row.get("position"))
        if position is None:
            continue
        rows.append({
            "Position": position,
            "Team": str(constructor.get("name") or ""),
            "Points": float(row.get("points") or 0),
            "Wins": int(row.get("wins") or 0),
        })
    return pd.DataFrame(rows, columns=columns)


def parse_season_results(payload: dict) -> pd.DataFrame:
    """One row per driver per round."""
    columns = ["Round", "Race", "Code", "Driver", "Team", "Position", "Points", "Status"]
    races = payload.get("MRData", {}).get("RaceTable", {}).get("Races", [])
    rows = []
    for race in races:
        round_number = _as_int(race.get("round"))
        if round_number is None:
            continue
        race_name = str(race.get("raceName") or f"Round {round_number}")
        for result in race.get("Results", []):
            position = _as_int(result.get("position"))
            driver = result.get("Driver") or {}
            constructor = result.get("Constructor") or {}
            rows.append({
                "Round": round_number,
                "Race": race_name,
                "Code": _driver_code(driver),
                "Driver": _driver_name(driver),
                "Team": str(constructor.get("name") or ""),
                "Position": position if position is not None else pd.NA,
                "Points": float(result.get("points") or 0),
                "Status": str(result.get("status") or ""),
            })
    if not rows:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame(rows, columns=columns)


def cumulative_points(results: pd.DataFrame) -> pd.DataFrame:
    """Running points total for each driver after every round."""
    if results.empty:
        return pd.DataFrame(columns=["Round", "Race", "Code", "Driver", "Cumulative"])
    ordered = results.sort_values(["Code", "Round"]).copy()
    ordered["Cumulative"] = ordered.groupby("Code")["Points"].cumsum()
    return ordered[["Round", "Race", "Code", "Driver", "Cumulative"]].reset_index(drop=True)


def driver_standings(year: int) -> pd.DataFrame:
    payload = _get_json(
        f"{JOLPICA_ROOT}/{int(year)}/driverStandings.json",
        f"{int(year)}_driver_standings.json",
    )
    return parse_driver_standings(payload)


def constructor_standings(year: int) -> pd.DataFrame:
    payload = _get_json(
        f"{JOLPICA_ROOT}/{int(year)}/constructorStandings.json",
        f"{int(year)}_constructor_standings.json",
    )
    return parse_constructor_standings(payload)


def _result_count(payload: dict) -> tuple[int, int]:
    races = payload.get("MRData", {}).get("RaceTable", {}).get("Races", [])
    got = sum(len(race.get("Results") or []) for race in races)
    try:
        total = int(payload.get("MRData", {}).get("total") or 0)
    except (TypeError, ValueError):
        total = 0
    return got, total


def season_results(year: int) -> pd.DataFrame:
    """All classified results for the year.

    Jolpica caps a response at 100 rows, which is only a handful of races.
    Pages are merged into one cache file.
    """
    cache_name = f"{int(year)}_results.json"
    path = _cache_path(cache_name)
    if path.exists():
        cached = json.loads(path.read_text(encoding="utf-8"))
        got, total = _result_count(cached)
        if total and got >= total:
            return parse_season_results(cached)

    races_by_round: dict[str, dict] = {}
    offset = 0
    limit = 100
    total = 0
    while True:
        page = _fetch_json(
            f"{JOLPICA_ROOT}/{int(year)}/results.json?limit={limit}&offset={offset}"
        )
        got, page_total = _result_count(page)
        total = page_total or total
        for race in page.get("MRData", {}).get("RaceTable", {}).get("Races", []):
            key = str(race.get("round"))
            if key not in races_by_round:
                races_by_round[key] = race
                continue
            races_by_round[key].setdefault("Results", []).extend(race.get("Results") or [])
        offset += limit
        if got == 0 or (total and offset >= total):
            break
        if offset > 5000:
            break

    ordered = [
        races_by_round[key]
        for key in sorted(races_by_round, key=lambda value: int(value))
    ]
    merged = {"MRData": {"total": str(total), "RaceTable": {"Races": ordered}}}
    path.write_text(json.dumps(merged), encoding="utf-8")
    return parse_season_results(merged)


def load_season(year: int) -> dict[str, pd.DataFrame]:
    """Standings, round results, and cumulative points for one championship."""
    results = season_results(year)
    return {
        "drivers": driver_standings(year),
        "constructors": constructor_standings(year),
        "results": results,
        "points": cumulative_points(results),
    }
