# interpolation.py
#
# Issue #33: sensors are scattered points, but we promised a pollution value
# for every 1km grid square. This module fills the gaps with Inverse Distance
# Weighting (IDW): each grid cell gets a weighted average of the sensor
# readings, where nearby sensors matter more (weight = 1 / distance^power).
#
# Usage as a library:
#     from interpolation import load_grid, load_sensors, interpolate_to_grid
#     grid    = load_grid()                       # 502 cells, AHM-0001..
#     sensors = load_sensors()                    # station points (lat/lon)
#     readings = sensors.assign(value=[...])      # one reading per station
#     cells = interpolate_to_grid(readings, grid) # grid_id -> value
#
# Usage as a script (demo + validation):
#     python interpolation.py                # writes data/grid_pollution_demo.csv
#     uv run --with pandas --with numpy --with matplotlib interpolation.py --plot
#                                            # also writes data/interpolation_map.png

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
GRID_GEOJSON = HERE.parent / "backend" / "static" / "ahmedabad_1km_grid.geojson"
SENSORS_CSV = HERE / "data" / "sensor_locations.csv"

EARTH_RADIUS_M = 6_371_000
# If a grid centroid is closer than this to a sensor, use the sensor's value
# directly instead of letting the 1/d^p weight blow up.
SNAP_DIST_M = 100.0


def haversine_m(lat1, lon1, lat2, lon2):
    """Great-circle distance in metres. Broadcasts over numpy arrays."""
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = (np.sin((lat2 - lat1) / 2) ** 2
         + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2)
    return 2 * EARTH_RADIUS_M * np.arcsin(np.sqrt(a))


def load_grid(path=GRID_GEOJSON):
    """Grid cells as a DataFrame: grid_id, centroid_lat, centroid_lon."""
    geo = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = [f["properties"] for f in geo["features"]]
    return pd.DataFrame(rows)[["grid_id", "centroid_lat", "centroid_lon"]]


def load_sensors(path=SENSORS_CSV):
    """Monitoring stations as a DataFrame: station_id, station, lat, lon."""
    return pd.read_csv(path)


def idw(sensor_lat, sensor_lon, values, target_lat, target_lon, power=2.0):
    """IDW-interpolate sensor values onto target points.

    All arguments are 1-D array-likes; returns one value per target point.
    Targets within SNAP_DIST_M of a sensor take that sensor's value exactly.
    """
    sensor_lat = np.asarray(sensor_lat, dtype=float)
    sensor_lon = np.asarray(sensor_lon, dtype=float)
    values = np.asarray(values, dtype=float)
    target_lat = np.asarray(target_lat, dtype=float)
    target_lon = np.asarray(target_lon, dtype=float)

    ok = ~np.isnan(values)
    if not ok.any():
        raise ValueError("No valid sensor readings to interpolate from")
    sensor_lat, sensor_lon, values = sensor_lat[ok], sensor_lon[ok], values[ok]

    # (n_targets, n_sensors) distance matrix
    dist = haversine_m(
        target_lat[:, None], target_lon[:, None],
        sensor_lat[None, :], sensor_lon[None, :],
    )
    weights = 1.0 / np.maximum(dist, SNAP_DIST_M) ** power
    est = (weights * values).sum(axis=1) / weights.sum(axis=1)

    # Snap targets that sit (almost) on top of a sensor
    nearest = dist.argmin(axis=1)
    snap = dist[np.arange(len(est)), nearest] < SNAP_DIST_M
    est[snap] = values[nearest[snap]]
    return est


def interpolate_to_grid(readings, grid, value_col="value", power=2.0):
    """One timestamp's sensor readings -> a value for every grid cell.

    readings: DataFrame with lat, lon and `value_col` (one row per station).
    grid:     DataFrame from load_grid().
    Returns a copy of grid with a `value_col` column added.
    """
    out = grid.copy()
    out[value_col] = idw(
        readings["lat"], readings["lon"], readings[value_col],
        grid["centroid_lat"], grid["centroid_lon"], power=power,
    )
    return out


def interpolate_timeseries(readings, grid, time_col="datetime",
                           value_col="value", power=2.0):
    """Readings for many timestamps -> long table (time, grid_id, value)."""
    frames = []
    for ts, group in readings.groupby(time_col):
        cells = interpolate_to_grid(group, grid, value_col=value_col, power=power)
        cells.insert(0, time_col, ts)
        frames.append(cells)
    return pd.concat(frames, ignore_index=True)


def leave_one_out(readings, value_col="value", power=2.0):
    """Sanity check: predict each sensor from the others.

    Returns the readings with a `predicted` column plus abs error, and the MAE.
    Low error relative to the spread of readings means the surface honours the
    raw sensors instead of inventing values.
    """
    rows = readings.reset_index(drop=True)
    preds = []
    for i in range(len(rows)):
        others = rows.drop(index=i)
        pred = idw(
            others["lat"], others["lon"], others[value_col],
            rows.loc[[i], "lat"], rows.loc[[i], "lon"], power=power,
        )[0]
        preds.append(pred)
    result = rows.copy()
    result["predicted"] = np.round(preds, 1)
    result["abs_error"] = (result["predicted"] - result[value_col]).abs().round(1)
    return result, float(result["abs_error"].mean())


# ---------------------------------------------------------------------------
# Demo: we don't have station-level history in the repo yet (needs an OpenAQ
# key), so anchor synthetic readings to the real city-level Ahmedabad AQI from
# city_hour.csv and give each station a fixed, plausible offset (industrial
# south-east high, green west low). Swap in real per-station readings once
# data/features/air_quality_history.csv exists.
# ---------------------------------------------------------------------------

# Relative pollution level per station vs the city mean
DEMO_STATION_FACTOR = {
    "AMD_AIRPORT": 1.05,      # traffic corridor
    "AMD_BOPAL": 0.75,        # residential west edge
    "AMD_CHANDKHEDA": 0.90,
    "AMD_GYASPUR": 1.30,      # industrial / landfill belt
    "AMD_MANINAGAR": 1.10,
    "AMD_NAVRANGPURA": 0.85,
    "AMD_PIRANA": 1.40,       # Pirana landfill + industry
    "AMD_RAIKHAD": 1.05,      # dense old city
    "AMD_RAKHIAL": 1.20,      # industrial east
    "AMD_SATELLITE": 0.80,    # residential west
}


def demo_readings(sensors):
    """Latest real Ahmedabad city AQI, spread across stations."""
    city = pd.read_csv(HERE / "data" / "city_hour.csv",
                       usecols=["City", "Datetime", "AQI"],
                       parse_dates=["Datetime"])
    city = city[(city["City"] == "Ahmedabad") & city["AQI"].notna()]
    
    # --- CONFIGURATION FLAG ---
    # Set this to False to use the latest real AQI data (which might be low/moderate).
    # Set this to True to force the snapshot to a historical Severe-AQI winter date.
    USE_SEVERE_DEMO_DATE = False
    
    if USE_SEVERE_DEMO_DATE:
        winter_data = city[(city["Datetime"] >= "2019-11-01") & (city["Datetime"] < "2019-12-01")]
        latest = winter_data.sort_values("AQI").iloc[-1]
    else:
        latest = city.sort_values("Datetime").iloc[-1]

    readings = sensors.copy()
    readings["datetime"] = latest["Datetime"]
    readings["value"] = [
        round(latest["AQI"] * DEMO_STATION_FACTOR[sid], 1)
        for sid in readings["station_id"]
    ]
    return readings


def plot_map(cells, readings, out_path, value_col="value"):
    """Grid heatmap + raw sensor dots on the same colour scale."""
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection

    geo = json.loads(GRID_GEOJSON.read_text(encoding="utf-8"))
    values = cells.set_index("grid_id")[value_col]

    polys, colors = [], []
    for f in geo["features"]:
        geom, gid = f["geometry"], f["properties"]["grid_id"]
        rings = ([geom["coordinates"]] if geom["type"] == "Polygon"
                 else geom["coordinates"])
        for ring in rings:
            polys.append(ring[0])  # exterior only
            colors.append(values[gid])

    vmin = min(values.min(), readings[value_col].min())
    vmax = max(values.max(), readings[value_col].max())

    fig, ax = plt.subplots(figsize=(9, 9))
    pc = PolyCollection(polys, array=np.array(colors), cmap="RdYlGn_r",
                        edgecolors="white", linewidths=0.2)
    pc.set_clim(vmin, vmax)
    ax.add_collection(pc)
    ax.scatter(readings["lon"], readings["lat"], c=readings[value_col],
               cmap="RdYlGn_r", vmin=vmin, vmax=vmax, s=140,
               edgecolors="black", linewidths=1.4, zorder=3, label="sensor")
    for _, r in readings.iterrows():
        ax.annotate(f"{r['station']}\n{r[value_col]:.0f}", (r["lon"], r["lat"]),
                    textcoords="offset points", xytext=(0, 10),
                    ha="center", fontsize=7)
    ax.autoscale()
    ax.set_aspect("equal")
    ax.set_title("IDW-interpolated AQI per 1km cell vs raw sensors (black rings)")
    fig.colorbar(pc, ax=ax, shrink=0.7, label="AQI")
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    print(f"Saved map -> {out_path}")


def main():
    parser = argparse.ArgumentParser(description="IDW sensor -> grid demo")
    parser.add_argument("--power", type=float, default=2.0,
                        help="IDW distance exponent (default 2)")
    parser.add_argument("--plot", action="store_true",
                        help="also render data/interpolation_map.png (needs matplotlib)")
    args = parser.parse_args()

    grid = load_grid()
    sensors = load_sensors()
    readings = demo_readings(sensors)
    print(f"{len(grid)} grid cells, {len(readings)} sensors, "
          f"timestamp {readings['datetime'].iloc[0]}")

    cells = interpolate_to_grid(readings, grid, power=args.power)
    cells["value"] = cells["value"].round(1)
    out_csv = HERE / "data" / "grid_pollution_demo.csv"
    cells.insert(0, "datetime", readings["datetime"].iloc[0])
    cells.to_csv(out_csv, index=False)
    print(f"Saved {len(cells)} cell values -> {out_csv}")

    # IDW is a weighted average, so the surface must stay inside sensor range
    assert cells["value"].between(readings["value"].min(),
                                  readings["value"].max()).all()

    loo, mae = leave_one_out(readings, power=args.power)
    spread = readings["value"].max() - readings["value"].min()
    print(f"\nLeave-one-out check (predict each sensor from the others):")
    print(loo[["station", "value", "predicted", "abs_error"]].to_string(index=False))
    print(f"MAE = {mae:.1f} AQI (sensor spread = {spread:.1f})")

    if args.plot:
        plot_map(cells, readings, HERE / "data" / "interpolation_map.png")


if __name__ == "__main__":
    main()
