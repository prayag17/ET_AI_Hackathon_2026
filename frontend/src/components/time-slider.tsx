/**
 * TimeSlider — lets the user scrub through the 0 → 72 h AQI forecast.
 *
 * Design decisions:
 *  • Native <input type="range"> so it works everywhere without extra deps.
 *  • Tick marks at 0 h, +24 h, +48 h, +72 h rendered as a datalist so the
 *    browser shows snap-points on the track on supporting platforms.
 *  • Play/Pause button auto-advances once per second so a demo audience can
 *    watch the forecast animate without the presenter touching anything.
 *  • The component is purely controlled (offset + onOffsetChange) — all data
 *    fetching lives in the parent (index.tsx) via TanStack Query.
 */

import { useEffect, useRef, useState } from 'react'
import { Play, Pause } from 'lucide-react'

interface TimeSliderProps {
  /** Currently displayed hour offset 0-72 */
  offset: number
  /** Called whenever the slider moves */
  onOffsetChange: (offset: number) => void
  /** ISO date string of the base snapshot (T+0) */
  baseDatetime?: string
  /** Whether forecast data is still loading */
  loading?: boolean
}

/** Format a Date as "Wed 14:00" — short enough to fit the slider label. */
function fmtDate(base: Date, offsetHours: number): string {
  const d = new Date(base.getTime() + offsetHours * 3_600_000)
  return d.toLocaleString(undefined, {
    weekday: 'short',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

const MAX_OFFSET = 72
const PLAY_INTERVAL_MS = 800 // ms between auto-advance ticks
const TICK_OFFSETS = [0, 24, 48, 72]

export function TimeSlider({
  offset,
  onOffsetChange,
  baseDatetime,
  loading = false,
}: TimeSliderProps) {
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

  // Stop playing when user drags the slider manually
  function handleSlider(e: React.ChangeEvent<HTMLInputElement>) {
    setPlaying(false)
    onOffsetChange(Number(e.target.value))
  }

  function togglePlay() {
    // If at end, rewind first
    if (!playing && offset >= MAX_OFFSET) onOffsetChange(0)
    setPlaying((p) => !p)
  }

  const baseDate = baseDatetime ? new Date(baseDatetime) : null

  // Percentage for the filled-track pseudo-element trick
  const pct = (offset / MAX_OFFSET) * 100

  return (
    <div className="flex w-full max-w-lg flex-col gap-2">
      {/* Top row: label left, timestamp right */}
      <div className="flex items-baseline justify-between px-0.5">
        <span className="text-xs font-medium text-foreground">
          {offset === 0 ? 'Now' : `+${offset} h`}
        </span>
        <span className="font-mono text-xs text-muted-foreground">
          {baseDate
            ? fmtDate(baseDate, offset)
            : loading
              ? '…'
              : 'No data'}
        </span>
      </div>

      {/* Slider row */}
      <div className="flex items-center gap-3">
        {/* Play / Pause */}
        <button
          type="button"
          aria-label={playing ? 'Pause forecast' : 'Play forecast'}
          disabled={loading}
          onClick={togglePlay}
          className="flex size-7 shrink-0 items-center justify-center rounded-full border border-border bg-card/80 text-foreground shadow transition-colors hover:bg-card disabled:opacity-40"
        >
          {playing ? (
            <Pause className="size-3.5" />
          ) : (
            <Play className="size-3.5 translate-x-px" />
          )}
        </button>

        {/* The range input with custom track fill via CSS variable */}
        <div className="relative flex-1">
          <input
            type="range"
            min={0}
            max={MAX_OFFSET}
            step={1}
            value={offset}
            onChange={handleSlider}
            disabled={loading}
            list="forecast-ticks"
            aria-label="Forecast time offset in hours"
            aria-valuemin={0}
            aria-valuemax={MAX_OFFSET}
            aria-valuenow={offset}
            aria-valuetext={offset === 0 ? 'Now' : `+${offset} hours`}
            style={{ '--pct': `${pct}%` } as React.CSSProperties}
            className="time-slider-input w-full"
          />
          {/* Tick labels below the track */}
          <div className="pointer-events-none mt-1 flex justify-between px-0.5">
            {TICK_OFFSETS.map((t) => (
              <span
                key={t}
                className="text-[10px] leading-none text-muted-foreground"
              >
                {t === 0 ? 'Now' : `+${t}h`}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* datalist for browser snap-point hints */}
      <datalist id="forecast-ticks">
        {TICK_OFFSETS.map((t) => (
          <option key={t} value={t} />
        ))}
      </datalist>
    </div>
  )
}
