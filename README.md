# F1_DVP_Dashboard

Formula 1 race-weekend DVP dashboard.

Streamlit app for a Data Visualization with Python project. It **does not
ship a CSV**. FastF1 downloads Formula 1 data from public APIs, the app
preprocesses it, runs EDA, and plots a full race weekend with matplotlib and
seaborn only (no React/HTML frontend).

Default session: **2024 Italian Grand Prix, Race**.

## Where the data comes from

FastF1 is an API client:

1. **F1 live-timing archive** — `https://livetiming.formula1.com`
   (FastF1 falls back to `https://livetiming-mirror.fastf1.dev`).
   Lap timing, tyres, telemetry, position, weather, race control (2018+).
2. **Jolpica-F1** — `https://api.jolpi.ca/ergast/f1` (Ergast-compatible).
   Results and historical calendar.
3. **FastF1 schedule JSON** — GitHub `theOehrly/f1schedule`.
4. **MultiViewer circuit data** — corner markers on the track map.

First load of a session can take a minute. Afterwards FastF1's cache
(`.fastf1_cache/`) and Parquet snapshots (`data/processed/`) make reruns fast.

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
another 2018–2026 weekend, then **Load session**.

## Pages

| Page | Contents |
| --- | --- |
| Home | Data sources, pipeline, row counts |
| Weekend overview | Timetable, weather, race-control messages |
| Session results | Classified results; position chart or quali bars |
| EDA | Missingness, categories, distributions, correlations |
| Lap times | Valid-pace traces and fastest lap |
| Strategy | Tyre stints and stint length vs pace |
| Telemetry | Fastest-lap speed / throttle / brake overlay |
| Track map | Speed-coloured layout with corner numbers |

## Layout

```
app.py
pages/
src/          data_loader, preprocess, eda, viz, state
data/processed/
requirements.txt
```
