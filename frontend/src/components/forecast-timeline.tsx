/**
 * ForecastTimeline — the bottom dock that scrubs the 0 → 72 h AQI forecast.
 *
 * The slider track is a "heat-track": a gradient built from the city-mean
 * AQI of every forecast hour, so the timeline itself previews where the air
 * gets worse before you scrub there. A 6-hour ruler with emphasized day
 * marks sits underneath, and the thumb is a needle that sweeps the track
 * during playback.
 *
 * Purely controlled (offset + onOffsetChange) — all data fetching lives in
 * the parent (index.tsx) via TanStack Query.
 */

import { useEffect, useMemo, useRef, useState } from 'react'
import { Pause, Play } from 'lucide-react'
import { aqiColor } from '@/lib/aqi'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Kbd } from '@/components/ui/kbd'
import { Separator } from '@/components/ui/separator'
import { SidebarTrigger } from '@/components/ui/sidebar'
import { Slider } from '@/components/ui/slider'
import { Spinner } from '@/components/ui/spinner'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'

const MAX_OFFSET = 72
const PLAY_INTERVAL_MS = 800 // ms between auto-advance ticks
const RULER_STEP_H = 6 // minor tick every 6 h, major tick every 24 h

interface ForecastTimelineProps {
  /** Currently displayed hour offset 0-72 */
  offset: number
  /** Called whenever the slider moves — accepts a value or functional updater */
  onOffsetChange: React.Dispatch<React.SetStateAction<number>>
  /** ISO date string of the base snapshot (T+0) */
  baseDatetime?: string
  /** City-mean AQI per forecast hour (index = offset) — drives the heat-track */
  trend?: Array<number>
  /** Whether forecast data is still loading */
  loading?: boolean
}

/** Format a Date as "Wed 14:00" — short enough to fit the readout. */
function fmtDate(base: Date, offsetHours: number): string {
  const d = new Date(base.getTime() + offsetHours * 3_600_000)
  return d.toLocaleString(undefined, {
    weekday: 'short',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

/** Short weekday name at base + offset, e.g. "Fri". */
function fmtDay(base: Date, offsetHours: number): string {
  const d = new Date(base.getTime() + offsetHours * 3_600_000)
  return d.toLocaleString(undefined, { weekday: 'short' })
}

export function ForecastTimeline({
  offset,
  onOffsetChange,
  baseDatetime,
  trend,
  loading = false,
}: ForecastTimelineProps) {
  const [playing, setPlaying] = useState(false)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Auto-play: advance offset by 1 h every PLAY_INTERVAL_MS
  useEffect(() => {
    if (playing) {
      intervalRef.current = setInterval(() => {
        onOffsetChange((prev) => {
          const next = prev + 1
          if (next >= MAX_OFFSET) {
            setPlaying(false)
            return MAX_OFFSET
          }
          return next
        })
      }, PLAY_INTERVAL_MS)
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [playing, onOffsetChange])

  // The heat-track gradient: one colour stop per forecast hour
  const heatGradient = useMemo(() => {
    if (!trend || trend.length < 2) return undefined
    const last = trend.length - 1
    const stops = trend.map(
      (aqi, i) => `${aqiColor(aqi)} ${((i / last) * 100).toFixed(2)}%`,
    )
    return `linear-gradient(90deg, ${stops.join(', ')})`
  }, [trend])

  // Stop playing when the user scrubs manually
  function handleSlider(values: Array<number>) {
    setPlaying(false)
    onOffsetChange(values[0] ?? 0)
  }

  function togglePlay() {
    // If at end, rewind first
    if (!playing && offset >= MAX_OFFSET) onOffsetChange(0)
    setPlaying((p) => !p)
  }

  const baseDate = baseDatetime ? new Date(baseDatetime) : null

  return (
    <div className="flex items-center gap-4 border-t bg-background px-4 py-3">
      {/* Transport */}
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            type="button"
            variant="outline"
            size="icon"
            aria-label={playing ? 'Pause forecast' : 'Play forecast'}
            disabled={loading}
            onClick={togglePlay}
          >
            {loading ? (
              <Spinner />
            ) : (
              /* Icon swap — both icons share one grid cell and crossfade */
              <span className="grid size-4 place-items-center">
                <Play
                  className={cn(
                    'col-start-1 row-start-1 size-4 transition-[opacity,transform] duration-200 ease-out',
                    playing
                      ? 'scale-75 opacity-0'
                      : 'translate-x-px scale-100 opacity-100',
                  )}
                />
                <Pause
                  className={cn(
                    'col-start-1 row-start-1 size-4 transition-[opacity,transform] duration-200 ease-out',
                    playing ? 'scale-100 opacity-100' : 'scale-75 opacity-0',
                  )}
                />
              </span>
            )}
          </Button>
        </TooltipTrigger>
        <TooltipContent>
          {playing ? 'Pause' : 'Play the 72-hour forecast'}
        </TooltipContent>
      </Tooltip>

      {/* Readout — fixed width so scrubbing doesn't shift the layout */}
      <div className="w-24 shrink-0">
        <p className="font-mono text-lg font-semibold leading-none tabular-nums">
          {offset === 0 ? 'Now' : `+${offset} h`}
        </p>
        <p className="mt-1 font-mono text-[11px] leading-none text-muted-foreground tabular-nums">
          {baseDate ? fmtDate(baseDate, offset) : loading ? '…' : 'No data'}
        </p>
      </div>

      <Separator orientation="vertical" className="h-8" />

      {/* Heat-track — keyed so the gradient fades in when forecast data lands */}
      <div
        key={heatGradient ? 'heat' : 'flat'}
        className="enter-fade flex min-w-0 flex-1 flex-col gap-1.5"
      >
        <Slider
          min={0}
          max={MAX_OFFSET}
          step={1}
          value={[offset]}
          onValueChange={handleSlider}
          disabled={loading}
          aria-label="Forecast time offset in hours"
          // The gradient encodes forecast data (like chart colours), so it is
          // injected as a CSS var; the track falls back to bg-muted without it.
          style={
            heatGradient
              ? ({ '--heat-track': heatGradient } as React.CSSProperties)
              : undefined
          }
          className="[&_[data-slot=slider-range]]:bg-transparent [&_[data-slot=slider-thumb]]:h-5 [&_[data-slot=slider-thumb]]:w-2 [&_[data-slot=slider-thumb]]:rounded-[3px] [&_[data-slot=slider-thumb]]:border-2 [&_[data-slot=slider-thumb]]:border-background [&_[data-slot=slider-thumb]]:bg-foreground [&_[data-slot=slider-track]]:h-2 [&_[data-slot=slider-track]]:rounded-[3px] [&_[data-slot=slider-track]]:[background-image:var(--heat-track)]"
        />

        {/* Ruler — minor tick every 6 h, taller mark at each day boundary */}
        <div className="relative h-2" aria-hidden="true">
          {Array.from({ length: MAX_OFFSET / RULER_STEP_H + 1 }, (_, i) => {
            const h = i * RULER_STEP_H
            const major = h % 24 === 0
            return (
              <span
                key={h}
                className={
                  major
                    ? 'absolute top-0 h-2 w-px -translate-x-1/2 bg-muted-foreground/60'
                    : 'absolute top-0 h-1 w-px -translate-x-1/2 bg-border'
                }
                style={{ left: `${(h / MAX_OFFSET) * 100}%` }}
              />
            )
          })}
        </div>

        {/* Day labels aligned with the major ticks */}
        <div className="flex justify-between font-mono text-[10px] leading-none text-muted-foreground">
          <span>Now</span>
          {[24, 48, 72].map((h) => (
            <span key={h}>{baseDate ? fmtDay(baseDate, h) : `+${h}h`}</span>
          ))}
        </div>
      </div>

      <Separator orientation="vertical" className="h-8" />

      {/* Inspector toggle */}
      <Tooltip>
        <TooltipTrigger asChild>
          <SidebarTrigger />
        </TooltipTrigger>
        <TooltipContent className="flex items-center gap-1.5">
          Toggle inspector <Kbd>Ctrl B</Kbd>
        </TooltipContent>
      </Tooltip>
    </div>
  )
}
