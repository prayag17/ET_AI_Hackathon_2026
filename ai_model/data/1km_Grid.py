import geopandas as gpd
from shapely.geometry import Polygon
import numpy as np

# 1. Define Ahmedabad's bounding box in standard Lat/Lon (WGS84)
# This box covers the extended urban area from the southern rings up to the northern corridor
min_lon, min_lat = 72.3941, 22.8888
max_lon, max_lat = 72.7630, 23.2098

# Create a polygon for the bounding box
bbox_poly = Polygon([
    (min_lon, min_lat),
    (max_lon, min_lat),
    (max_lon, max_lat),
    (min_lon, max_lat)
])

# Create a GeoDataFrame for the bounding box
gdf_bbox = gpd.GeoDataFrame({'geometry': [bbox_poly]}, crs="EPSG:4326")

# 2. Project to a metric coordinate system (UTM Zone 43N for Gujarat/Ahmedabad)
# This allows us to measure out exactly 1000 meters (1km) without distortion.
gdf_bbox_metric = gdf_bbox.to_crs("EPSG:32643")

# Get the metric bounds
minx, miny, maxx, maxy = gdf_bbox_metric.total_bounds

# 3. Define the grid size (1000 meters = 1km)
grid_size = 1000

# Create the grid cells
grid_cells = []
x_coords = np.arange(minx, maxx, grid_size)
y_coords = np.arange(miny, maxy, grid_size)

# 4. Generate the polygons and assign unique IDs
grid_id_counter = 1
for x0 in x_coords:
    for y0 in y_coords:
        # Define the four corners of the 1km cell
        x1 = x0 + grid_size
        y1 = y0 + grid_size
        
        # Create the polygon
        cell_poly = Polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
        
        # Format a unique ID for Ahmedabad (e.g., AHM-0001)
        cell_id = f"AHM-{grid_id_counter:04d}"
        
        grid_cells.append({'grid_id': cell_id, 'geometry': cell_poly})
        grid_id_counter += 1

# Convert the grid cells back to a GeoDataFrame in the metric system
gdf_grid_metric = gpd.GeoDataFrame(grid_cells, crs="EPSG:32643")

# 5. Project back to standard Lat/Lon (WGS84) for map rendering
gdf_grid_wgs84 = gdf_grid_metric.to_crs("EPSG:4326")

# 6. Export to GeoJSON
output_filename = "ahmedabad_1km_grid.geojson"
gdf_grid_wgs84.to_file(output_filename, driver="GeoJSON")

print(f"Success! Generated {len(gdf_grid_wgs84)} 1km grid squares for Ahmedabad.")
print(f"Saved to {output_filename}")