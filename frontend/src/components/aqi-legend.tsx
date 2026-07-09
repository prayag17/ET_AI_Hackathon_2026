/**
 * AqiLegend — compact right-hand panel showing the Indian CPCB AQI colour
 * bands so users immediately understand what the map colours mean.
 *
 * Reads directly from AQI_STOPS so colour definitions stay in one place.
 * The upper bound for each band is the start of the next band minus 1
 * (or "500+" for the last / Severe band).
 */

import { AQI_STOPS } from '@/components/grid-map'

export function AqiLegend() {
  return (
    <aside
      aria-label="AQI colour legend"
      className="w-44 rounded-xl border bg-card/80 p-3 shadow-lg backdrop-blur-md"
    >
      {/* Title */}
      <p className="mb-2.5 text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
        AQI Index
      </p>

      <ul className="space-y-1.5" role="list">
        {AQI_STOPS.map((stop, i) => {
          const next = AQI_STOPS[i + 1]
          const range = next ? `${stop.aqi}–${next.aqi - 1}` : `${stop.aqi}+`

          return (
            <li key={stop.label} className="flex items-center gap-2.5">
              {/* Colour swatch */}
              <span
                className="size-3 shrink-0 rounded-sm"
                style={{ backgroundColor: stop.color }}
                aria-hidden="true"
              />
              <div className="flex min-w-0 flex-1 items-baseline justify-between gap-1">
                {/* Label */}
                <span className="truncate text-xs font-medium leading-none">
                  {stop.label}
                </span>
                {/* Range */}
                <span className="shrink-0 font-mono text-[10px] leading-none text-muted-foreground">
                  {range}
                </span>
              </div>
            </li>
          )
        })}
      </ul>

      {/* Footer note */}
      <p className="mt-3 text-[9px] leading-tight text-muted-foreground">
        Indian CPCB scale
      </p>
    </aside>
  )
}
