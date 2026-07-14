# Backend

FastAPI server that delivers the grid, forecasts, GRAP advisories, and live
data updates to the frontend.

| Uses UV package manager, pls use the given command to get started

- Installing UV:

```sh
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

- Installing dependencies:

```sh
uv sync --all-groups
```

> `--all-groups` also installs the `pipeline` dependency group (lightgbm,
> scikit-learn, …) that the root-level `ai_model/` scripts need when run
> through this venv. Plain `uv sync` will prune them.

- Running backend:

```sh
uv run fastapi dev
```

> On Windows, if the reloader crashes on emoji output, run with
> `$env:PYTHONIOENCODING='utf-8'` set.

## Routes (all under `/maps`)

| Route | Kind | Serves |
|-------|------|--------|
| `/maps/getMap` | GET | 1 km grid GeoJSON (502 cells) |
| `/maps/getBoundary` | GET | City boundary GeoJSON |
| `/maps/getPollution` | GET | Current T=0 AQI snapshot |
| `/maps/getForecast` | GET | 73 hourly snapshots (T+0 … T+72) |
| `/maps/getAdvisory` | GET | GRAP advisories (LLM via OpenRouter, deterministic fallback) |
| `/maps/ws` | WebSocket | Live updates — broadcasts `{"type": "data_updated"}` whenever the pollution CSV changes (`routers/live.py`) |

## Background tasks (started via lifespan in `main.py`)

- **Hourly data refresh** — re-runs the root `live_inference.py` (latest
  Open-Meteo readings → IDW grid → LightGBM forecasts) so
  `grid_pollution_demo.csv` and `forecast_demo.json` keep themselves up to
  date. Skips the startup run when the snapshot is under an hour old; a
  failed run keeps the previous data and retries in 10 min. Requires the
  `pipeline` dependency group (`uv sync --all-groups`).
- **File watcher** — polls the CSV's mtime and broadcasts over `/maps/ws`
  when it changes, whichever process rewrote it.

| Env var | Default | Meaning |
|---------|---------|---------|
| `OPENROUTER_API_KEY` | unset | Enables the LLM advisory path; otherwise the rule-based GRAP fallback is used |
| `LIVE_REFRESH_SECONDS` | `3600` | Interval for the auto-refresh loop; `0` disables it (watcher + WS still run) |

Other commands can be found at:
- [uv docs](https://docs.astral.sh/uv/guides/)
- [fastapi docs](https://fastapi.tiangolo.com/)
