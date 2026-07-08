"""Generate a 1km x 1km analysis grid clipped to the real Ahmedabad boundary.

Instead of gridding a rectangular bounding box (which renders as a big square),
this script:
  1. Fetches the actual Ahmedabad municipal boundary polygon from OSM (Nominatim).
  2. Builds a 1km grid in a metric CRS (UTM 43N) over the boundary's extent.
  3. Keeps only cells that intersect the city, clipping edge cells to the
     boundary so the grid follows the city's real shape.

Outputs (written next to this script):
  - ahmedabad_boundary.geojson   the city outline, useful for rendering
  - ahmedabad_1km_grid.geojson   the clipped 1km grid

Run with:  uv run --with geopandas --with requests 1km_Grid.py
"""

import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import requests
from shapely.geometry import MultiPolygon, Polygon, shape

OUT_DIR = Path(__file__).resolve().parent
BOUNDARY_FILE = OUT_DIR / "ahmedabad_boundary.geojson"
GRID_FILE = OUT_DIR / "ahmedabad_1km_grid.geojson"

WGS84 = "EPSG:4326"      # lat/lon, what web maps expect
UTM_43N = "EPSG:32643"   # metric CRS covering Gujarat, for exact 1km cells
GRID_SIZE_M = 1000
# Drop clipped slivers smaller than this fraction of a full cell
MIN_CELL_FRACTION = 0.05

# OSM has no single relation for the AMC city limits, but the city area is the
# union of the five talukas the former Ahmedabad City taluka was split into.
CITY_TALUKA_RELATIONS = {
    "Maninagar": 16736464,
    "Vatva": 16736465,
    "Asarva": 16736466,
    "Ghatlodiya": 16736467,
    "Vejalpur": 16736469,
}


def fill_holes(geom):
    """Drop interior rings, keeping only exterior shells."""
    if geom.geom_type == "Polygon":
        return Polygon(geom.exterior)
    return MultiPolygon([Polygon(p.exterior) for p in geom.geoms])


def fetch_ahmedabad_boundary() -> gpd.GeoDataFrame:
    """Fetch the Ahmedabad city boundary polygon from OSM Nominatim (cached)."""
    if BOUNDARY_FILE.exists():
        print(f"Using cached boundary: {BOUNDARY_FILE.name}")
        return gpd.read_file(BOUNDARY_FILE)

    print("Fetching Ahmedabad city talukas from OSM Nominatim...")
    resp = requests.get(
        "https://nominatim.openstreetmap.org/lookup",
        params={
            "osm_ids": ",".join(f"R{rid}" for rid in CITY_TALUKA_RELATIONS.values()),
            "format": "jsonv2",
            "polygon_geojson": 1,
        },
        headers={"User-Agent": "ahmedabad-grid-generator/1.0"},
        timeout=60,
    )
    resp.raise_for_status()
    results = resp.json()
    if len(results) != len(CITY_TALUKA_RELATIONS):
        raise RuntimeError(
            f"Expected {len(CITY_TALUKA_RELATIONS)} taluka polygons, got {len(results)}"
        )

    talukas = gpd.GeoDataFrame(
        geometry=[shape(r["geojson"]) for r in results], crs=WGS84
    )
    # Union the talukas and drop internal slivers along shared edges
    city = talukas.union_all().buffer(0)
    # The historic city core has no taluka relation in OSM, which leaves a gap
    # in the middle of the union, connected to the outside through narrow
    # channels. Morphological closing (in metres) seals the channels, and
    # filling interior rings then recovers the full city footprint.
    city_metric = gpd.GeoSeries([city], crs=WGS84).to_crs(UTM_43N).iloc[0]
    city_metric = fill_holes(city_metric.buffer(2000).buffer(-2000))
    city = gpd.GeoSeries([city_metric], crs=UTM_43N).to_crs(WGS84).iloc[0]
    boundary = gpd.GeoDataFrame({"name": ["Ahmedabad"], "geometry": [city]}, crs=WGS84)
    boundary.to_file(BOUNDARY_FILE, driver="GeoJSON")
    print(f"Saved boundary to {BOUNDARY_FILE.name}")
    return boundary


def build_grid(boundary: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Build a 1km grid over the boundary and clip it to the city shape."""
    boundary_metric = boundary.to_crs(UTM_43N)
    city_shape = boundary_metric.union_all()
    minx, miny, maxx, maxy = city_shape.bounds

    # Snap grid origin to a whole kilometre so cell edges are stable across runs
    x_coords = np.arange(np.floor(minx / GRID_SIZE_M) * GRID_SIZE_M, maxx, GRID_SIZE_M)
    y_coords = np.arange(np.floor(miny / GRID_SIZE_M) * GRID_SIZE_M, maxy, GRID_SIZE_M)

    full_area = GRID_SIZE_M * GRID_SIZE_M
    cells = []
    for row, y0 in enumerate(y_coords):
        for col, x0 in enumerate(x_coords):
            cell = Polygon([
                (x0, y0),
                (x0 + GRID_SIZE_M, y0),
                (x0 + GRID_SIZE_M, y0 + GRID_SIZE_M),
                (x0, y0 + GRID_SIZE_M),
            ])
            if not cell.intersects(city_shape):
                continue
            clipped = cell.intersection(city_shape)
            if clipped.is_empty or clipped.area / full_area < MIN_CELL_FRACTION:
                continue
            centroid = clipped.centroid
            cells.append({
                "row": row,
                "col": col,
                "coverage": round(clipped.area / full_area, 3),
                "area_km2": round(clipped.area / 1e6, 3),
                "geometry": clipped,
                "_centroid": centroid,
            })

    grid = gpd.GeoDataFrame(cells, crs=UTM_43N)
    grid["grid_id"] = [f"AHM-{i + 1:04d}" for i in range(len(grid))]

    # Centroid in lat/lon for joining with point data (weather, AQI stations...)
    centroids = gpd.GeoSeries(grid.pop("_centroid"), crs=UTM_43N).to_crs(WGS84)
    grid["centroid_lon"] = centroids.x.round(6)
    grid["centroid_lat"] = centroids.y.round(6)

    return grid.to_crs(WGS84)[
        ["grid_id", "row", "col", "coverage", "area_km2",
         "centroid_lon", "centroid_lat", "geometry"]
    ]


def main() -> None:
    boundary = fetch_ahmedabad_boundary()
    grid = build_grid(boundary)
    grid.to_file(GRID_FILE, driver="GeoJSON")

    # Trim coordinate precision (~0.1m at 6 decimals) to keep the file small
    data = json.loads(GRID_FILE.read_text(encoding="utf-8"))

    def round_coords(coords):
        if isinstance(coords[0], (int, float)):
            return [round(c, 6) for c in coords]
        return [round_coords(c) for c in coords]

    for feature in data["features"]:
        geom = feature["geometry"]
        geom["coordinates"] = round_coords(geom["coordinates"])
    GRID_FILE.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")

    print(f"Success! Generated {len(grid)} 1km grid cells clipped to Ahmedabad.")
    print(f"Saved to {GRID_FILE.name}")


if __name__ == "__main__":
    main()
