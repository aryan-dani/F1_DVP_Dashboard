# F1_DVP_Dashboard

Formula 1 race-weekend dashboard.

Streamlit app for a Data Visualization with Python project. It does not ship
a CSV. FastF1 downloads Formula 1 data from public APIs, the app preprocesses
it, and Plotly draws the charts. Matplotlib stays installed because FastF1
uses it. The pages themselves do not render Matplotlib figures.

Default session: **2024 Italian Grand Prix, Race**.

## Where the data comes from

FastF1 is an API client:

1. **F1 live-timing archive** — `https://livetiming.formula1.com`
   (FastF1 falls back to `https://livetiming-mirror.fastf1.dev`).
   Lap timing, tyres, telemetry, position, weather, race control (2018+).
2. **Jolpica-F1** — `https://api.jolpi.ca/ergast/f1` (Ergast-compatible).
   Results, the historical calendar, and the season standings page.
3. **FastF1 schedule JSON** — GitHub `theOehrly/f1schedule`.
4. **MultiViewer circuit data** — corner markers on the track map.

First load of a session can take a minute. Afterwards FastF1's cache
(`.fastf1_cache/`) and Parquet snapshots (`data/processed/`) make reruns fast.
Season standings are cached as JSON under `.fastf1_cache/jolpica/` and do not
download every race.

## Setup

Python 3.10 or newer.

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Start the dashboard

```powershell
.\venv\Scripts\Activate.ps1
streamlit run app.py
```

Then open **http://localhost:8501**

Home loads the 2024 Italian GP race automatically. Use the sidebar to pick
another 2018–2026 weekend, then **Load session**. The year, Grand Prix, and
session are stored in the page URL.

Click a chart legend entry to isolate that driver. Sidebar filters (team,
compound, lap range, valid pace only) apply to results, pace, and strategy.

## Pages

| Page | Contents |
| --- | --- |
| Home | Scoreboard for the loaded session, plus the data-source notes |
| Weekend | Session cards, weather, track-status timeline, race control |
| Results | Classification and CSV download; gaps and intervals, or qualifying segments, or practice pace |
| Pace | Lap traces, driver spread, sectors, tyre degradation |
| Strategy | Compound stints, safety-car bands, degradation slope |
| Telemetry | Fastest-lap speed, throttle, brake, gear, RPM, DRS, and a delta trace |
| Track map | Fastest lap coloured by speed or gear |
| Compare | Two drivers: pace gap, sectors, stints, telemetry delta |
| Season | Jolpica standings, points, and a finishing-position heatmap |
| Data quality | Missingness, lap categories, correlations, outlier laps |

## Check the pipeline

`smoke_test.py` checks gap, interval, and degradation columns, and that the
main Plotly figures have traces. It uses `data/processed/` when that snapshot
exists, and a tiny synthetic race otherwise. It does not start Streamlit and
it does not call Jolpica.

```powershell
.\venv\Scripts\python.exe smoke_test.py
```

## Layout

```
app.py                 navigation
src/views/             one screen per page
src/                   data_loader, preprocess, insights, charts, season, state
data/processed/        parquet snapshots
.streamlit/config.toml dark theme
```
