/**
 * InspectorSidebar — the right-hand panel that holds everything that used to
 * float over the map: city header, live cursor sample, pinned-cell inspector,
 * and the CPCB legend. Collapsible (Ctrl+B or the dock trigger) so the map
 * can take the whole viewport; becomes a Sheet on mobile.
 */

import { MapPinned, MousePointerClick, X } from 'lucide-react'
import { AqiLegend } from '@/components/aqi-legend'
import { ThemeToggle } from '@/components/theme-toggle'
import { CellDetail } from '@/components/cell-detail-panel'
import type { ForecastSnapshot } from '@/components/cell-detail-panel'
import type { GridCell } from '@/components/grid-map'
import { aqiColor, aqiLabel } from '@/lib/aqi'
import { cn } from '@/lib/utils'
import CountUp from '@/components/CountUp'
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from '@/components/ui/empty'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupAction,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarSeparator,
} from '@/components/ui/sidebar'

interface InspectorSidebarProps {
  /** Timestamp of the snapshot currently shown on the map */
  datetime?: string
  /** Whether the live-update WebSocket is currently connected */
  liveConnected?: boolean
  /** Cell currently under the cursor */
  hovered: GridCell | null
  /** AQI of the hovered cell at the current slider position */
  hoveredAqi?: number
  /** Cell pinned by clicking */
  selected: GridCell | null
  /** AQI of the pinned cell at the current slider position */
  selectedAqi?: number
  /** All 73 forecast snapshots (T+0 … T+72) */
  snapshots?: Array<ForecastSnapshot>
  /** Current slider offset */
  offsetHours: number
  /** City-mean AQI at the current slider position — highlights the scale */
  cityAqi?: number
  /** Unpin the selected cell */
  onClearSelection: () => void
}

export function InspectorSidebar({
  datetime,
  liveConnected = false,
  hovered,
  hoveredAqi,
  selected,
  selectedAqi,
  snapshots,
  offsetHours,
  cityAqi,
  onClearSelection,
}: InspectorSidebarProps) {
  return (
    <Sidebar side="right" collapsible="offcanvas">
      <SidebarHeader>
        <div className="flex items-center gap-3 px-2 py-1">
          <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-sidebar-accent">
            <MapPinned className="size-4 text-sidebar-accent-foreground" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold leading-none tracking-tight">
              Ahmedabad
            </p>
            <p className="mt-1 truncate text-xs text-muted-foreground">
              {datetime
                ? `AQI · ${new Date(datetime).toLocaleString()}`
                : '1 km² analysis grid'}
            </p>
          </div>
          {/* Live-channel status — real state from the /maps/ws socket */}
          <span
            className="flex shrink-0 items-center gap-1.5 text-[10px] font-medium uppercase tracking-widest text-muted-foreground"
            title={
              liveConnected
                ? 'Live updates connected — the dashboard refreshes itself'
                : 'Live updates disconnected — data may be stale'
            }
          >
            <span
              aria-hidden="true"
              className={cn(
                'size-1.5 rounded-full',
                liveConnected
                  ? 'bg-emerald-500 shadow-[0_0_6px_1px] shadow-emerald-500/60'
                  : 'bg-muted-foreground/40',
              )}
            />
            {liveConnected ? 'Live' : 'Offline'}
          </span>
        </div>
      </SidebarHeader>

      <SidebarSeparator />

      <SidebarContent>
        {/* Live cursor sample */}
        <SidebarGroup>
          <SidebarGroupLabel>Cursor</SidebarGroupLabel>
          <SidebarGroupContent className="px-2">
            {hovered ? (
              <div className="flex items-center justify-between gap-2">
                <div className="min-w-0">
                  <p className="truncate font-mono text-sm font-semibold">
                    {hovered.grid_id}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    r{hovered.row} · c{hovered.col}
                  </p>
                </div>
                {hoveredAqi !== undefined && (
                  <div className="flex shrink-0 items-center gap-2">
                    <span
                      className="size-2.5 rounded-full"
                      style={{ backgroundColor: aqiColor(hoveredAqi) }}
                      aria-hidden="true"
                    />
                    <span className="font-mono text-lg font-semibold leading-none">
                      <CountUp to={Math.round(hoveredAqi)} duration={0.6} />
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {aqiLabel(hoveredAqi)}
                    </span>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">
                Hover the grid to sample a cell.
              </p>
            )}
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarSeparator />

        {/* Pinned cell inspector */}
        <SidebarGroup>
          <SidebarGroupLabel>Cell inspector</SidebarGroupLabel>
          {selected && (
            <SidebarGroupAction
              aria-label="Clear selection"
              onClick={onClearSelection}
            >
              <X />
            </SidebarGroupAction>
          )}
          <SidebarGroupContent className="px-2">
            {selected && snapshots ? (
              // Keyed by cell so pinning a different cell replays the entrance
              <CellDetail
                key={selected.grid_id}
                cell={selected}
                currentAqi={selectedAqi}
                snapshots={snapshots}
                offsetHours={offsetHours}
                onClose={onClearSelection}
              />
            ) : (
              <Empty className="enter-fade p-6">
                <EmptyHeader>
                  <EmptyMedia variant="icon">
                    <MousePointerClick />
                  </EmptyMedia>
                  <EmptyTitle className="text-sm">No cell pinned</EmptyTitle>
                  <EmptyDescription className="text-xs">
                    Click any grid cell on the map to pin its 72-hour
                    forecast here.
                  </EmptyDescription>
                </EmptyHeader>
              </Empty>
            )}
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarSeparator />

        {/* CPCB legend */}
        <SidebarGroup>
          <SidebarGroupLabel>AQI scale</SidebarGroupLabel>
          <SidebarGroupContent className="px-2">
            <AqiLegend activeAqi={cityAqi} />
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter>
        <div className="flex items-center justify-between gap-2">
          <p className="px-2 text-[10px] leading-tight text-muted-foreground">
            Indian CPCB scale · 1 km² grid
          </p>
          <ThemeToggle />
        </div>
      </SidebarFooter>
    </Sidebar>
  )
}
