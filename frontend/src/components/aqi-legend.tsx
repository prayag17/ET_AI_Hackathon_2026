/**
 * AqiLegend — the Indian CPCB AQI colour bands as a contiguous spectrum
 * strip (a thermometer read vertically), designed to sit inside a sidebar
 * group. When the current city-mean AQI is provided, its band is
 * highlighted so the scale doubles as a live indicator.
 *
 * Reads directly from AQI_STOPS so colour definitions stay in one place.
 * The upper bound for each band is the start of the next band minus 1
 * (or "500+" for the last / Severe band).
 */

import { AQI_STOPS, aqiLabel } from '@/lib/aqi'
import { cn } from '@/lib/utils'

interface AqiLegendProps {
  /** Current city-mean AQI — highlights the matching band */
  activeAqi?: number
}

export function AqiLegend({ activeAqi }: AqiLegendProps) {
  const activeLabel = activeAqi !== undefined ? aqiLabel(activeAqi) : undefined

  return (
    <div className="flex flex-col gap-2">
      <ul aria-label="AQI colour legend" className="flex flex-col" role="list">
        {AQI_STOPS.map((stop, i) => {
          const next = AQI_STOPS.at(i + 1)
          const range = next ? `${stop.aqi}–${next.aqi - 1}` : `${stop.aqi}+`
          const active = stop.label === activeLabel

          return (
            <li
              key={stop.label}
              className={cn(
                'flex items-stretch gap-2.5 rounded-md pl-1.5 pr-2 transition-colors duration-200',
                active && 'bg-sidebar-accent',
              )}
            >
              {/* Band segment — rows have no gap, so the segments join into
                  one continuous CPCB spectrum strip */}
              <span
                className={cn(
                  'w-1.5 shrink-0',
                  i === 0 && 'rounded-t-full',
                  i === AQI_STOPS.length - 1 && 'rounded-b-full',
                )}
                style={{ backgroundColor: stop.color }}
                aria-hidden="true"
              />
              <div className="flex min-w-0 flex-1 items-center justify-between gap-1 py-1.5">
                <span
                  className={cn(
                    'truncate text-xs leading-none',
                    active ? 'font-semibold' : 'font-medium',
                  )}
                >
                  {stop.label}
                </span>
                <span
                  className={cn(
                    'shrink-0 font-mono text-[10px] leading-none transition-colors duration-200',
                    active
                      ? 'font-semibold text-foreground'
                      : 'text-muted-foreground',
                  )}
                >
                  {active && activeAqi !== undefined
                    ? `● ${Math.round(activeAqi)}`
                    : range}
                </span>
              </div>
            </li>
          )
        })}
      </ul>

      {activeAqi !== undefined && (
        <p className="px-1.5 text-[10px] leading-none text-muted-foreground">
          ● City mean at the selected hour
        </p>
      )}
    </div>
  )
}
