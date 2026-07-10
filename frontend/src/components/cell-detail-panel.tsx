/**
 * CellDetailPanel — slides in from the left when the user clicks a grid cell.
 *
 * Shows:
 *  • Cell ID, coordinates, area metadata
 *  • Current AQI badge (colour-coded)
 *  • 72-hour forecast line chart built with Recharts
 *    – Y-axis bands match the CPCB AQI colour scale (reference lines)
 *    – A vertical marker shows the time-slider's current position
 *    – Tooltip shows exact AQI value on hover
 *  • Close button (×) and ESC key support
 *
 * Props are all plain data — no fetching happens inside this component.
 */

import { useEffect } from 'react'
import { X } from 'lucide-react'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  CartesianGrid,
} from 'recharts'
import { AQI_STOPS, aqiColor } from '@/components/grid-map'
import type { GridCell } from '@/components/grid-map'

// ── Types ────────────────────────────────────────────────────────────────────

interface ForecastSnapshot {
  offset_hours: number
  values: Record<string, number>
}

interface CellDetailPanelProps {
  /** The clicked cell's metadata */
  cell: GridCell
  /** AQI at the current slider position */
  currentAqi: number | undefined
  /** All 73 forecast snapshots (T+0 … T+72) */
  snapshots: ForecastSnapshot[]
  /** Current slider offset — shown as a vertical marker on the chart */
  offsetHours: number
  /** Close the panel */
  onClose: () => void
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function aqiLabel(aqi: number): string {
  let label = AQI_STOPS[0].label
  for (const s of AQI_STOPS) if (aqi >= s.aqi) label = s.label
  return label
}

/** Custom tooltip rendered inside the chart */
function ChartTooltip({
  active,
  payload,
}: {
  active?: boolean
  payload?: Array<{ value: number }>
}) {
  if (!active || !payload?.length) return null
  const aqi = payload[0].value
  return (
    <div className="rounded-md border bg-card px-2.5 py-1.5 text-xs shadow-lg">
      <span
        className="mr-1.5 inline-block size-2 rounded-full"
        style={{ backgroundColor: aqiColor(aqi) }}
      />
      <span className="font-mono font-semibold">{Math.round(aqi)}</span>
      <span className="ml-1 text-muted-foreground">{aqiLabel(aqi)}</span>
    </div>
  )
}

/** Custom X-axis tick — only show label at 0 h, 24 h, 48 h, 72 h */
function XTick({
  x,
  y,
  payload,
}: {
  x?: number
  y?: number
  payload?: { value: number }
}) {
  const h = payload?.value ?? 0
  if (h !== 0 && h !== 24 && h !== 48 && h !== 72) return null
  return (
    <text
      x={x}
      y={(y ?? 0) + 12}
      textAnchor="middle"
      fontSize={9}
      fill="var(--muted-foreground)"
    >
      {h === 0 ? 'Now' : `+${h}h`}
    </text>
  )
}

// ── Component ─────────────────────────────────────────────────────────────────

export function CellDetailPanel({
  cell,
  currentAqi,
  snapshots,
  offsetHours,
  onClose,
}: CellDetailPanelProps) {
  // Close on Escape key
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  // Build chart data: one point per snapshot hour
  const chartData = snapshots.map((s) => ({
    h: s.offset_hours,
    aqi: s.values[cell.grid_id] ?? null,
  }))

  // Y-axis domain — pad a bit above/below the data range
  const values = chartData.map((d) => d.aqi).filter((v): v is number => v !== null)
  const minAqi = Math.max(0, Math.min(...values) - 10)
  const maxAqi = Math.min(500, Math.max(...values) + 20)

  const aqi = currentAqi ?? snapshots[0]?.values[cell.grid_id]

  return (
    // Slide-in panel — left side, full height, above vignette (z-20)
    <aside
      className="pointer-events-auto absolute inset-y-0 left-0 z-20 flex w-80 flex-col border-r bg-card/90 shadow-2xl backdrop-blur-md"
      aria-label={`Detail panel for cell ${cell.grid_id}`}
    >
      {/* ── Header ── */}
      <div className="flex items-start justify-between border-b px-4 py-3">
        <div>
          <p className="font-mono text-sm font-semibold leading-none">
            {cell.grid_id}
          </p>
          <p className="mt-1 text-[11px] text-muted-foreground">
            Row {cell.row} · Col {cell.col}
          </p>
        </div>
        <button
          type="button"
          aria-label="Close detail panel"
          onClick={onClose}
          className="ml-2 flex size-6 shrink-0 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
        >
          <X className="size-3.5" />
        </button>
      </div>

      {/* ── Current AQI badge ── */}
      <div className="border-b px-4 py-3">
        <p className="mb-1.5 text-[10px] uppercase tracking-widest text-muted-foreground">
          Current AQI
        </p>
        {aqi !== undefined ? (
          <div className="flex items-center gap-2.5">
            <span
              className="size-3 shrink-0 rounded-sm"
              style={{ backgroundColor: aqiColor(aqi) }}
            />
            <span className="font-mono text-2xl font-bold leading-none">
              {Math.round(aqi)}
            </span>
            <span
              className="rounded-md px-2 py-0.5 text-xs font-semibold"
              style={{
                backgroundColor: `${aqiColor(aqi)}22`,
                color: aqiColor(aqi),
              }}
            >
              {aqiLabel(aqi)}
            </span>
          </div>
        ) : (
          <span className="text-sm text-muted-foreground">No data</span>
        )}
      </div>

      {/* ── Metadata ── */}
      <dl className="border-b px-4 py-3 text-xs">
        <div className="flex justify-between py-0.5">
          <dt className="text-muted-foreground">Area</dt>
          <dd className="font-mono">{cell.area_km2.toFixed(2)} km²</dd>
        </div>
        <div className="flex justify-between py-0.5">
          <dt className="text-muted-foreground">City coverage</dt>
          <dd className="font-mono">{(cell.coverage * 100).toFixed(0)}%</dd>
        </div>
        <div className="flex justify-between py-0.5">
          <dt className="text-muted-foreground">Centroid</dt>
          <dd className="font-mono">
            {cell.centroid_lat.toFixed(4)}, {cell.centroid_lon.toFixed(4)}
          </dd>
        </div>
      </dl>

      {/* ── 72-hour Forecast Chart ── */}
      <div className="flex flex-1 flex-col px-4 py-3">
        <p className="mb-3 text-[10px] uppercase tracking-widest text-muted-foreground">
          72-hour forecast
        </p>

        <div className="flex-1" style={{ minHeight: 0 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={chartData}
              margin={{ top: 4, right: 8, bottom: 16, left: -8 }}
            >
              {/* Subtle grid */}
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="var(--border)"
                vertical={false}
              />

              {/* AQI band reference lines — light horizontal guides */}
              {AQI_STOPS.slice(1).map((s) => (
                <ReferenceLine
                  key={s.aqi}
                  y={s.aqi}
                  stroke={s.color}
                  strokeOpacity={0.35}
                  strokeDasharray="4 4"
                  strokeWidth={1}
                />
              ))}

              {/* Current time-slider position */}
              {offsetHours > 0 && (
                <ReferenceLine
                  x={offsetHours}
                  stroke="var(--foreground)"
                  strokeOpacity={0.5}
                  strokeDasharray="3 3"
                  strokeWidth={1}
                />
              )}

              <XAxis
                dataKey="h"
                type="number"
                domain={[0, 72]}
                ticks={[0, 6, 12, 18, 24, 30, 36, 42, 48, 54, 60, 66, 72]}
                tick={<XTick />}
                axisLine={{ stroke: 'var(--border)' }}
                tickLine={false}
              />

              <YAxis
                domain={[minAqi, maxAqi]}
                tick={{ fontSize: 9, fill: 'var(--muted-foreground)' }}
                axisLine={false}
                tickLine={false}
                width={32}
              />

              <Tooltip content={<ChartTooltip />} />

              {/* The forecast line — colour follows current AQI band */}
              <Line
                type="monotone"
                dataKey="aqi"
                stroke={aqi !== undefined ? aqiColor(aqi) : '#888'}
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 3, strokeWidth: 0 }}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Chart legend row */}
        <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1">
          {AQI_STOPS.map((s, i) => {
            const next = AQI_STOPS[i + 1]
            const range = next ? `${s.aqi}–${next.aqi - 1}` : `${s.aqi}+`
            return (
              <div key={s.label} className="flex items-center gap-1">
                <span
                  className="size-1.5 rounded-full"
                  style={{ backgroundColor: s.color }}
                />
                <span className="text-[9px] text-muted-foreground">
                  {range}
                </span>
              </div>
            )
          })}
        </div>
      </div>
    </aside>
  )
}
