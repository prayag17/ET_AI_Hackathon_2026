/**
 * CellDetail — the pinned-cell inspector content, embedded in the sidebar.
 *
 * Shows:
 *  • Cell ID, coordinates, area metadata
 *  • Current AQI badge (colour-coded to the CPCB band)
 *  • 72-hour forecast line chart via the shadcn Chart wrapper (Recharts)
 *    – Y-axis bands match the CPCB AQI colour scale (reference lines)
 *    – A vertical marker shows the time-slider's current position
 *    – Tooltip shows exact AQI value on hover
 *  • ESC clears the selection
 *
 * Props are all plain data — no fetching happens inside this component.
 */

import { useEffect } from 'react'
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  XAxis,
  YAxis,
} from 'recharts'
import type { GridCell } from '@/components/grid-map'
import { AQI_STOPS, aqiColor, aqiLabel } from '@/lib/aqi'
import { Badge } from '@/components/ui/badge'
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from '@/components/ui/chart'
import type { ChartConfig } from '@/components/ui/chart'
import {
  Item,
  ItemContent,
  ItemDescription,
  ItemGroup,
} from '@/components/ui/item'
import { Separator } from '@/components/ui/separator'
import CountUp from '@/components/CountUp'

// ── Types ────────────────────────────────────────────────────────────────────

export interface ForecastSnapshot {
  offset_hours: number
  // Values may be missing for cells outside the model's coverage
  values: Record<string, number | undefined>
}

interface CellDetailProps {
  /** The pinned cell's metadata */
  cell: GridCell
  /** AQI at the current slider position */
  currentAqi: number | undefined
  /** All 73 forecast snapshots (T+0 … T+72) */
  snapshots: Array<ForecastSnapshot>
  /** Current slider offset — shown as a vertical marker on the chart */
  offsetHours: number
  /** Clear the selection */
  onClose: () => void
}

// ── Helpers ──────────────────────────────────────────────────────────────────

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

export function CellDetail({
  cell,
  currentAqi,
  snapshots,
  offsetHours,
  onClose,
}: CellDetailProps) {
  // Clear selection on Escape key
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
  const values = chartData
    .map((d) => d.aqi)
    .filter((v): v is number => v !== null)
  const minAqi = Math.max(0, Math.min(...values) - 10)
  const maxAqi = Math.min(500, Math.max(...values) + 20)

  const aqi = currentAqi ?? snapshots[0]?.values[cell.grid_id]

  const chartConfig = {
    aqi: {
      label: 'AQI',
      color: aqi !== undefined ? aqiColor(aqi) : 'var(--muted-foreground)',
    },
  } satisfies ChartConfig

  return (
    <div className="enter-fade-up flex flex-col gap-3">
      {/* Identity */}
      <div className="flex items-baseline justify-between">
        <span className="font-mono text-sm font-semibold">{cell.grid_id}</span>
        <span className="text-xs text-muted-foreground">
          r{cell.row} · c{cell.col}
        </span>
      </div>

      {/* Current AQI */}
      {aqi !== undefined ? (
        <div className="flex items-center gap-2.5">
          <span
            className="size-3 shrink-0 rounded-sm"
            style={{ backgroundColor: aqiColor(aqi) }}
            aria-hidden="true"
          />
          <span className="font-mono text-2xl font-bold leading-none">
            <CountUp to={Math.round(aqi)} duration={0.8} />
          </span>
          {/* CPCB band colour is data-driven, so it comes in via style */}
          <Badge
            variant="secondary"
            className="font-semibold"
            style={{
              backgroundColor: `${aqiColor(aqi)}22`,
              color: aqiColor(aqi),
            }}
          >
            {aqiLabel(aqi)}
          </Badge>
        </div>
      ) : (
        <span className="text-sm text-muted-foreground">No data</span>
      )}

      {/* Metadata */}
      <ItemGroup className="gap-0">
        <Item size="xs" className="px-0 py-1">
          <ItemContent>
            <ItemDescription className="text-xs">Area</ItemDescription>
          </ItemContent>
          <span className="font-mono text-xs">
            {cell.area_km2.toFixed(2)} km²
          </span>
        </Item>
        <Item size="xs" className="px-0 py-1">
          <ItemContent>
            <ItemDescription className="text-xs">
              City coverage
            </ItemDescription>
          </ItemContent>
          <span className="font-mono text-xs">
            {(cell.coverage * 100).toFixed(0)}%
          </span>
        </Item>
        <Item size="xs" className="px-0 py-1">
          <ItemContent>
            <ItemDescription className="text-xs">Centroid</ItemDescription>
          </ItemContent>
          <span className="font-mono text-xs">
            {cell.centroid_lat.toFixed(4)}, {cell.centroid_lon.toFixed(4)}
          </span>
        </Item>
      </ItemGroup>

      <Separator />

      {/* 72-hour forecast chart */}
      <div>
        <p className="mb-2 text-[10px] uppercase tracking-widest text-muted-foreground">
          72-hour forecast
        </p>

        <ChartContainer config={chartConfig} className="aspect-auto h-44 w-full">
          <LineChart
            data={chartData}
            margin={{ top: 4, right: 8, bottom: 16, left: 0 }}
          >
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

            <ChartTooltip
              content={
                <ChartTooltipContent
                  hideLabel
                  hideIndicator
                  formatter={(value) => {
                    const v = Number(value)
                    return (
                      <div className="flex items-center gap-1.5">
                        <span
                          className="size-2 rounded-full"
                          style={{ backgroundColor: aqiColor(v) }}
                        />
                        <span className="font-mono font-semibold">
                          {Math.round(v)}
                        </span>
                        <span className="text-muted-foreground">
                          {aqiLabel(v)}
                        </span>
                      </div>
                    )
                  }}
                />
              }
            />

            {/* The forecast line — colour follows current AQI band */}
            <Line
              type="monotone"
              dataKey="aqi"
              stroke="var(--color-aqi)"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 3, strokeWidth: 0 }}
              isAnimationActive={false}
            />
          </LineChart>
        </ChartContainer>
      </div>
    </div>
  )
}
