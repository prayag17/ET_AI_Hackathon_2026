import { useState } from 'react'
import { createFileRoute } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { LoaderCircle, MapPinned } from 'lucide-react'
import type { FeatureCollection } from 'geojson'
import { GridMap } from '@/components/grid-map'
import type { GridCell } from '@/components/grid-map'

export const Route = createFileRoute('/')({ component: Home })

async function fetchGeoJson(path: string): Promise<FeatureCollection> {
  const res = await fetch(path)
  if (!res.ok) throw new Error(`${path} responded with ${res.status}`)
  return res.json()
}

function Home() {
  const [hovered, setHovered] = useState<GridCell | null>(null)

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

  return (
    <div className="dark relative h-dvh w-full overflow-hidden bg-background text-foreground">
      {grid.data && boundary.data && (
        <GridMap
          grid={grid.data}
          boundary={boundary.data}
          onHoverCell={setHovered}
        />
      )}

      {/* Black halo vignette around the map edges */}
      <div className="pointer-events-none absolute inset-0 z-[5] shadow-[inset_0_0_140px_40px_rgba(0,0,0,0.6)]" />

      {(grid.isPending || boundary.isPending) && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <LoaderCircle className="size-4 animate-spin" />
            Loading grid…
          </div>
        </div>
      )}

      {(grid.isError || boundary.isError) && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="max-w-sm rounded-lg border border-destructive/40 bg-card p-4 text-sm">
            <p className="font-medium text-destructive">Failed to load map data</p>
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
              1 km² analysis grid
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
              <dl className="mt-3 space-y-1.5 text-xs">
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">Area</dt>
                  <dd className="font-mono">{hovered.area_km2.toFixed(2)} km²</dd>
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
    </div>
  )
}
