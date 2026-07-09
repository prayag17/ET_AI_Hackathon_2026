# Pollution Heatmap Setup Guide

## Overview
The pollution heatmap is now fully configured and ready to run. The main screen displays a map of Ahmedabad where each 1km² grid cell is colored by its AQI (Air Quality Index) value.

## What Was Built

### Frontend (`/frontend`)
- **Map Component** (`src/components/grid-map.tsx`): Displays the interactive pollution heatmap using MapLibre GL
- **Main Page** (`src/routes/index.tsx`): Shows the map with hover details, loading states, and error handling
- **Features**:
  - Color-coded grid cells based on Indian CPCB AQI scale (Good/Moderate/Poor/Very Poor/Severe)
  - Interactive hover to show detailed cell information
  - City boundary overlay
  - Responsive zoom controls and fullscreen mode
  - Dark theme with OpenFreeMap basemap (no API key required)

### Backend (`/backend`)
- **API Endpoints** (`routers/maps.py`):
  - `GET /maps/getMap` - Returns Ahmedabad 1km grid GeoJSON
  - `GET /maps/getBoundary` - Returns city boundary GeoJSON
  - `GET /maps/getPollution` - Returns AQI values for all grid cells

## Running the Application

### Prerequisites
- Python >=3.14
- Node.js (npm)
- uv (Python package manager)

### Backend
```bash
cd backend
uv run fastapi dev main.py
```
Backend will start on http://localhost:8000

### Frontend
```bash
cd frontend
npm run dev
```
Frontend will start on http://localhost:3000

The frontend automatically proxies `/api/*` requests to the backend at `http://localhost:8000`.

## AQI Color Scale
- **0-99** (Green): Good
- **100-199** (Yellow): Moderate
- **200-299** (Orange): Poor
- **300-399** (Red): Very Poor
- **400+** (Dark Red): Severe

## Map Controls
- **Zoom**: Mouse wheel or +/- buttons
- **Pan**: Click and drag
- **Reset View**: Click the scan icon button
- **Fullscreen**: Click the fullscreen button
- **Hover**: Move mouse over grid cells to see details

## Data Source
The pollution data comes from `ai_model/data/grid_pollution_demo.csv`, which contains AQI values for each grid cell at a specific timestamp.
