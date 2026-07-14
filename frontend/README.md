# Frontend — Ahmedabad AQI Dashboard

React dashboard for the Ahmedabad AQI Forecast & Advisory system: an
interactive 1 km grid heatmap with a 72-hour forecast timeline, a pinned-cell
inspector, and an AI advisory assistant, all refreshing live over a WebSocket.

## Stack

- **React 19** + **Vite** with **TanStack Router** (file-based routes) and
  **TanStack Query** (server state)
- **MapLibre GL JS** for the map; grid AQI is written via `feature-state` so
  time-scrubbing never re-uploads geometry
- **shadcn/ui** + **Tailwind CSS 4** (CSS-first config in `src/styles.css`),
  plus a few [react-bits](https://reactbits.dev) components (StarBorder,
  SpotlightCard, Strands, GlassSurface, CountUp)
- **motion** for enter/exit animation; `prefers-reduced-motion` is honored
  everywhere (decorative motion is skipped entirely)
- **Recharts** for the per-cell forecast chart

## Getting started

```bash
pnpm install
pnpm dev        # http://localhost:3000
```

The dev server proxies `/api/*` → `http://localhost:8000/*` (REST **and** the
`/maps/ws` WebSocket — see `vite.config.ts`), so start the backend first:

```bash
cd ../backend
uv run fastapi dev main.py
```

Other scripts: `pnpm build`, `pnpm test` (Vitest), `pnpm lint`, `pnpm check`.

## How it's put together

```
src/
├── routes/index.tsx            # Dashboard page — owns all queries + UI state
├── lib/api.ts                  # Typed fetchers for the /maps/* endpoints
├── hooks/
│   └── use-live-updates.ts     # /maps/ws WebSocket → invalidates queries on
│                               # "data_updated"; returns connection state
└── components/
    ├── grid-map.tsx            # MapLibre map: AQI fill, lattice, selection,
    │                           # hover sampling, camera persistence
    ├── aqi-particles.ts        # Canvas particle layer — cells sharing an AQI
    │                           # band are flood-filled into regions; each
    │                           # region's particles swirl inside it only
    ├── forecast-timeline.tsx   # Bottom dock: play/scrub T+0…T+72 over a
    │                           # city-mean AQI "heat-track" gradient
    ├── inspector-sidebar.tsx   # Right panel: live cursor sample, pinned-cell
    │                           # inspector, CPCB legend, Live/Offline dot
    ├── cell-detail-panel.tsx   # Pinned cell: current AQI + 72 h line chart
    ├── ai-assistant/           # Floating glass button + popover panel that
    │                           # renders /maps/getAdvisory (GRAP stages,
    │                           # citizen advisories, confidence)
    └── ui/                     # shadcn primitives
```

Design notes worth knowing before changing things:

- **Particles are screen-space canvas, not a MapLibre source.** Animating a
  GeoJSON source means `setData()` re-tiles the payload every frame and lags;
  the canvas layer projects each particle per frame (~30 fps) instead. It's
  created only when `prefers-reduced-motion` is off.
- **`activePollution` is memoized in `index.tsx`** — passing a fresh object
  each render would reseed the particles on every mousemove.
- **The AI panel uses a plain `overflow-y-auto` div**, not Radix ScrollArea,
  which never resolved a height inside the popover's flex chain. Scrollbars
  are styled globally (thin, theme-tinted) in `styles.css`.
- The map basemap comes from OpenFreeMap (no API key); light/dark styles swap
  with the theme, which rebuilds the map while preserving the camera.
