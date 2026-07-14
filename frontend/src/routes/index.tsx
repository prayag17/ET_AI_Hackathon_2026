import { lazy, Suspense, useMemo, useState } from 'react'
import { createFileRoute } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { GridMap } from '@/components/grid-map'
import type { GridCell } from '@/components/grid-map'
import { ForecastTimeline } from '@/components/forecast-timeline'
import { InspectorSidebar } from '@/components/inspector-sidebar'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { SidebarInset, SidebarProvider } from '@/components/ui/sidebar'
import { Spinner } from '@/components/ui/spinner'
import { getBoundary, getForecast, getGrid, getPollution } from '@/lib/api'
import { useLiveUpdates } from '@/hooks/use-live-updates'

// Code-split: keeps the `motion` + react-bits flourish out of the main
// bundle until the map itself has rendered.
const AiAssistant = lazy(() =>
  import('@/components/ai-assistant/ai-assistant').then((m) => ({
    default: m.AiAssistant,
  })),
)

export const Route = createFileRoute('/')({ component: Home })

function Home() {
  const [hovered, setHovered] = useState<GridCell | null>(null)
  const [offsetHours, setOffsetHours] = useState(0)
  const [clickedCell, setClickedCell] = useState<GridCell | null>(null)

  // Refetch pollution/forecast/advisory automatically when the backend
  // announces new data over the /maps/ws live channel
  const liveConnected = useLiveUpdates()

  const grid = useQuery({
    queryKey: ['grid'],
    queryFn: getGrid,
    staleTime: Infinity,
  })
  const boundary = useQuery({
    queryKey: ['boundary'],
    queryFn: getBoundary,
    staleTime: Infinity,
  })
  const pollution = useQuery({
    queryKey: ['pollution'],
    queryFn: getPollution,
  })

  // Forecast: all 73 hourly snapshots (T+0 … T+72)
  const forecast = useQuery({
    queryKey: ['forecast'],
    queryFn: getForecast,
    staleTime: 5 * 60 * 1000, // 5 min — forecast is deterministic, no need to hammer the API
  })

  // The active pollution data shown on the map:
  //   • offset 0 → use the real snapshot from /getPollution (source of truth)
  //   • offset > 0 → use the corresponding forecast snapshot
  // Memoized so hovering/selecting cells (which re-render Home but don't
  // change the underlying data) doesn't hand GridMap a new object reference
  // every time — that was retriggering its pollutionData effect (and
  // reseeding the AQI particles) on every mousemove.
  const activePollution = useMemo(() => {
    if (offsetHours === 0) return pollution.data
    if (forecast.data) {
      return {
        datetime: forecast.data.snapshots[offsetHours]?.base_datetime ?? '',
        values: forecast.data.snapshots[offsetHours]?.values ?? {},
      }
    }
    return pollution.data
  }, [offsetHours, forecast.data, pollution.data])
  // City-mean AQI per forecast hour — drives the timeline heat-track
  const cityTrend = useMemo(() => {
    if (!forecast.data) return undefined
    return forecast.data.snapshots.map((s) => {
      const values = Object.values(s.values)
      if (values.length === 0) return 0
      return values.reduce((sum, v) => sum + v, 0) / values.length
    })
  }, [forecast.data])

  const hoveredAqi = hovered
    ? activePollution?.values[hovered.grid_id]
    : undefined
  const selectedAqi = clickedCell
    ? activePollution?.values[clickedCell.grid_id]
    : undefined

  // City-mean AQI at the current slider position — highlights the scale band.
  // At offset 0 this comes from the live snapshot, otherwise from the trend.
  const cityAqi = useMemo(() => {
    if (offsetHours > 0) return cityTrend?.[offsetHours]
    const values = activePollution ? Object.values(activePollution.values) : []
    if (values.length === 0) return undefined
    return values.reduce((sum, v) => sum + v, 0) / values.length
  }, [activePollution, cityTrend, offsetHours])

  return (
    <SidebarProvider
      className="h-svh overflow-hidden"
      style={{ '--sidebar-width': '21rem' } as React.CSSProperties}
    >
      <SidebarInset className="flex h-svh flex-col overflow-hidden">
        {/* Map canvas — no overlays, the sidebar and dock own the chrome */}
        <div className="relative min-h-0 flex-1">
          {grid.data && boundary.data && pollution.data && (
            <GridMap
              grid={grid.data}
              boundary={boundary.data}
              onHoverCell={setHovered}
              onClickCell={setClickedCell}
              pollutionData={activePollution}
              selectedCellId={clickedCell?.grid_id ?? null}
            />
          )}

          {(grid.isPending || boundary.isPending || pollution.isPending) && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Spinner />
                Loading grid…
              </div>
            </div>
          )}

          {(grid.isError || boundary.isError || pollution.isError) && (
            <div className="absolute inset-0 flex items-center justify-center">
              <Alert variant="destructive" className="enter-fade-up max-w-sm">
                <AlertTitle>Failed to load map data</AlertTitle>
                <AlertDescription>
                  Is the backend running?{' '}
                  <code>uv run fastapi dev main.py</code>
                </AlertDescription>
              </Alert>
            </div>
          )}

          <Suspense fallback={null}>
            <AiAssistant />
          </Suspense>
        </div>

        {/* Forecast timeline dock */}
        <ForecastTimeline
          offset={offsetHours}
          onOffsetChange={setOffsetHours}
          baseDatetime={
            forecast.data?.base_datetime ?? pollution.data?.datetime
          }
          trend={cityTrend}
          loading={forecast.isPending}
        />
      </SidebarInset>

      <InspectorSidebar
        datetime={activePollution?.datetime}
        liveConnected={liveConnected}
        hovered={hovered}
        hoveredAqi={hoveredAqi}
        selected={clickedCell}
        selectedAqi={selectedAqi}
        snapshots={forecast.data?.snapshots}
        offsetHours={offsetHours}
        cityAqi={cityAqi}
        onClearSelection={() => setClickedCell(null)}
      />
    </SidebarProvider>
  )
}
