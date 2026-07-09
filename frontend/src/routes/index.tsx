import { useState } from 'react'
import { createFileRoute } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { LoaderCircle, MapPinned } from 'lucide-react'
import type { FeatureCollection } from 'geojson'
import { AQI_STOPS, GridMap, aqiColor } from '@/components/grid-map'
import type { GridCell } from '@/components/grid-map'
import { TimeSlider } from '@/components/time-slider'
import { AqiLegend } from '@/components/aqi-legend'

function aqiLabel(aqi: number): string {
  let label = AQI_STOPS[0].label
  for (const s of AQI_STOPS) if (aqi >= s.aqi) label = s.label
  return label
}

export const Route = createFileRoute('/')({ component: Home })

async function fetchGeoJson(path: string): Promise<FeatureCollection> {
  const res = await fetch(path)
  if (!res.ok) throw new Error(`${path} responded with ${res.status}`)
  return res.json()
}

function Home() {
  const [hovered, setHovered] = useState<GridCell | null>(null)
  const [offsetHours, setOffsetHours] = useState(0)

  const grid = useQuery({
    queryKey: ['grid'],
    queryFn: () => fetchGeoJson('/api/maps/getMap'),
    staleTime: Infinity,
  })
  const boundary = useQuery({
    queryKey: ['boundary'],
    queryFn: () => fetchGeoJson('/api/maps/getBoundary'),
    staleTime: Infinity,
  })
  const pollution = useQuery({
    queryKey: ['pollution'],
    queryFn: async () => {
      const res = await fetch('/api/maps/getPollution')
      if (!res.ok) throw new Error(`getPollution responded with ${res.status}`)
      return res.json() as Promise<{
        datetime: string
        values: Record<string, number>
      }>
    },
  })

  // Forecast: all 73 hourly snapshots (T+0 … T+72)
  const forecast = useQuery({
    queryKey: ['forecast'],
    queryFn: async () => {
      const res = await fetch('/api/maps/getForecast')
      if (!res.ok) throw new Error(`getForecast responded with ${res.status}`)
      return res.json() as Promise<{
        base_datetime: string
        snapshots: Array<{
          offset_hours: number
          base_datetime: string
          values: Record<string, number>
        }>
      }>
    },
    staleTime: 5 * 60 * 1000, // 5 min — forecast is deterministic, no need to hammer the API
  })

  // The active pollution data shown on the map:
  //   • offset 0 → use the real snapshot from /getPollution (source of truth)
  //   • offset > 0 → use the corresponding forecast snapshot
  const activePollution =
    offsetHours === 0
      ? pollution.data
      : forecast.data
        ? {
            datetime: forecast.data.snapshots[offsetHours]?.base_datetime ?? '',
            values: forecast.data.snapshots[offsetHours]?.values ?? {},
          }
        : pollution.data

  return (
    <div className="dark relative h-dvh w-full overflow-hidden bg-background text-foreground">
      {grid.data && boundary.data && pollution.data && (
        <GridMap
          grid={grid.data}
          boundary={boundary.data}
          onHoverCell={setHovered}
          pollutionData={activePollution}
        />
      )}

      {/* Black halo vignette around the map edges */}
      <div className="pointer-events-none absolute inset-0 z-[5] shadow-[inset_0_0_140px_40px_rgba(0,0,0,0.6)]" />

      {(grid.isPending || boundary.isPending || pollution.isPending) && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <LoaderCircle className="size-4 animate-spin" />
            Loading grid…
          </div>
        </div>
      )}

      {(grid.isError || boundary.isError || pollution.isError) && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="max-w-sm rounded-lg border border-destructive/40 bg-card p-4 text-sm">
            <p className="font-medium text-destructive">
              Failed to load map data
            </p>
            <p className="mt-1 text-muted-foreground">
              Is the backend running? <code>uv run fastapi dev main.py</code>
            </p>
          </div>
        </div>
      )}

      {/* Header */}
      <header className="pointer-events-none absolute left-4 top-4 z-10">
        <div className="pointer-events-auto flex items-center gap-3 rounded-lg border bg-card/80 px-4 py-3 shadow-lg backdrop-blur-md">
          <MapPinned className="size-4 text-muted-foreground" />
          <div>
            <h1 className="text-sm font-semibold leading-none tracking-tight">
              Ahmedabad
            </h1>
            <p className="mt-1 text-xs text-muted-foreground">
              {pollution.data
                ? `AQI · ${new Date(pollution.data.datetime).toLocaleString()}`
                : '1 km² analysis grid'}
            </p>
          </div>
          {grid.data && (
            <span className="ml-2 rounded-md border bg-secondary px-2 py-1 font-mono text-xs text-secondary-foreground">
              {grid.data.features.length} cells
            </span>
          )}
        </div>
      </header>

      {/* Hovered cell details */}
      <aside className="pointer-events-none absolute bottom-6 left-4 z-10">
        <div
          className={`w-60 rounded-lg border bg-card/80 p-4 shadow-lg backdrop-blur-md transition-opacity duration-150 ${
            hovered ? 'opacity-100' : 'opacity-0'
          }`}
        >
          {hovered && (
            <>
              <div className="flex items-baseline justify-between">
                <span className="font-mono text-sm font-semibold">
                  {hovered.grid_id}
                </span>
                <span className="text-xs text-muted-foreground">
                  r{hovered.row} · c{hovered.col}
                </span>
              </div>
              {(() => {
                const aqi = activePollution?.values[hovered.grid_id]
                if (aqi === undefined) return null
                return (
                  <div className="mt-3 flex items-center gap-2">
                    <span
                      className="size-2.5 rounded-full"
                      style={{ backgroundColor: aqiColor(aqi) }}
                    />
                    <span className="font-mono text-lg font-semibold leading-none">
                      {Math.round(aqi)}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      AQI · {aqiLabel(aqi)}
                    </span>
                  </div>
                )
              })()}
              <dl className="mt-3 space-y-1.5 text-xs">
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">Area</dt>
                  <dd className="font-mono">
                    {hovered.area_km2.toFixed(2)} km²
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">City coverage</dt>
                  <dd className="font-mono">
                    {(hovered.coverage * 100).toFixed(0)}%
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">Centroid</dt>
                  <dd className="font-mono">
                    {hovered.centroid_lat.toFixed(4)},{' '}
                    {hovered.centroid_lon.toFixed(4)}
                  </dd>
                </div>
              </dl>
            </>
          )}
        </div>
      </aside>
      {/* AQI Legend — right side, vertically centred */}
      <div className="pointer-events-none absolute right-4 top-1/2 z-10 -translate-y-1/2">
        <div className="pointer-events-auto">
          <AqiLegend />
        </div>
      </div>

      {/* Time Slider — bottom-center, above the map controls */}
      <div className="pointer-events-none absolute bottom-6 left-1/2 z-10 -translate-x-1/2">
        <div className="pointer-events-auto rounded-xl border bg-card/80 px-5 py-4 shadow-lg backdrop-blur-md">
          <TimeSlider
            offset={offsetHours}
            onOffsetChange={setOffsetHours}
            baseDatetime={forecast.data?.base_datetime ?? pollution.data?.datetime}
            loading={forecast.isPending}
          />
        </div>
      </div>
    </div>
  )
}
