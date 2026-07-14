import { useEffect, useRef } from 'react'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import type { ExpressionSpecification } from 'maplibre-gl'
import type { FeatureCollection } from 'geojson'
import { useReducedMotion } from 'motion/react'
import { AQI_STOPS } from '@/lib/aqi'
import { AqiParticleLayer, collectCellSamples } from '@/components/aqi-particles'
import { useTheme } from '@/components/theme-provider'

// OpenFreeMap basemaps — free, no API key, rebuilt weekly from fresh OSM
// data (much more current than Carto's), matching the shadcn palettes
const MAP_STYLES = {
  dark: 'https://tiles.openfreemap.org/styles/dark',
  light: 'https://tiles.openfreemap.org/styles/positron',
} as const

export interface GridCell {
  grid_id: string
  row: number
  col: number
  coverage: number
  area_km2: number
  centroid_lon: number
  centroid_lat: number
}

interface GridMapProps {
  grid: FeatureCollection
  boundary: FeatureCollection
  onHoverCell?: (cell: GridCell | null) => void
  onClickCell?: (cell: GridCell) => void
  pollutionData?: { datetime: string; values: Record<string, number> }
  /** grid_id of the pinned cell — outlined on the map */
  selectedCellId?: string | null
}

// Cells with no reading yet get -1 so the paint rules can tell them apart
const AQI_STATE: ExpressionSpecification = [
  'coalesce',
  ['feature-state', 'aqi'],
  -1,
]

/** Write per-cell AQI into maplibre feature-state (geometry stays untouched,
 *  so this is cheap enough to call on every time-slider tick later). */
function applyPollution(
  map: maplibregl.Map,
  values: Record<string, number> | undefined,
) {
  if (!values || !map.getSource('grid')) return
  for (const [gridId, aqi] of Object.entries(values)) {
    map.setFeatureState({ source: 'grid', id: gridId }, { aqi })
  }
}

/** Compute a [sw, ne] bounding box from any GeoJSON FeatureCollection. */
function bboxOf(fc: FeatureCollection): [[number, number], [number, number]] {
  let minLon = Infinity
  let minLat = Infinity
  let maxLon = -Infinity
  let maxLat = -Infinity
  const walk = (coords: any) => {
    if (typeof coords[0] === 'number') {
      minLon = Math.min(minLon, coords[0])
      maxLon = Math.max(maxLon, coords[0])
      minLat = Math.min(minLat, coords[1])
      maxLat = Math.max(maxLat, coords[1])
    } else {
      for (const c of coords) walk(c)
    }
  }
  for (const f of fc.features) {
    if ('coordinates' in f.geometry) walk(f.geometry.coordinates)
  }
  return [
    [minLon, minLat],
    [maxLon, maxLat],
  ]
}

/** Button control that resets the camera to the city extent. */
class FitCityControl implements maplibregl.IControl {
  private container!: HTMLDivElement

  constructor(
    private bounds: [[number, number], [number, number]],
    private padding: number,
  ) {}

  onAdd(map: maplibregl.Map) {
    this.container = document.createElement('div')
    this.container.className = 'maplibregl-ctrl maplibregl-ctrl-group'
    const button = document.createElement('button')
    button.type = 'button'
    button.title = 'Reset view to city'
    button.setAttribute('aria-label', 'Reset view to city')
    // lucide "scan" icon
    button.innerHTML =
      '<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display:inline"><path d="M3 7V5a2 2 0 0 1 2-2h2"/><path d="M17 3h2a2 2 0 0 1 2 2v2"/><path d="M21 17v2a2 2 0 0 1-2 2h-2"/><path d="M7 21H5a2 2 0 0 1-2-2v-2"/></svg>'
    button.addEventListener('click', () => {
      map.fitBounds(this.bounds, { padding: this.padding })
    })
    this.container.appendChild(button)
    return this.container
  }

  onRemove() {
    this.container.remove()
  }
}

export function GridMap({
  grid,
  boundary,
  onHoverCell,
  onClickCell,
  pollutionData,
  selectedCellId,
}: GridMapProps) {
  const { resolvedTheme } = useTheme()
  const isDark = resolvedTheme === 'dark'
  const reducedMotion = useReducedMotion()
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<maplibregl.Map | null>(null)
  const particleLayerRef = useRef<AqiParticleLayer | null>(null)
  // Camera carried across map re-creation (theme switches rebuild the map,
  // since maplibre's setStyle would drop our custom sources/layers anyway)
  const cameraRef = useRef<{
    center: maplibregl.LngLat
    zoom: number
  } | null>(null)
  const onHoverRef = useRef(onHoverCell)
  onHoverRef.current = onHoverCell
  const onClickRef = useRef(onClickCell)
  onClickRef.current = onClickCell
  // Values may arrive before or after the map's 'load' event; keep the latest
  // in a ref so the load handler can pick them up either way
  const pollutionRef = useRef(pollutionData)
  pollutionRef.current = pollutionData
  // Same race applies to the selection: keep the target and the currently
  // applied id in refs so both the effect and the load handler can sync them
  const selectedRef = useRef<string | null>(selectedCellId ?? null)
  selectedRef.current = selectedCellId ?? null
  const appliedSelectionRef = useRef<string | null>(null)

  const applySelection = (map: maplibregl.Map) => {
    if (!map.getSource('grid')) return
    const prev = appliedSelectionRef.current
    const next = selectedRef.current
    if (prev && prev !== next) {
      map.setFeatureState({ source: 'grid', id: prev }, { selected: false })
    }
    if (next) {
      map.setFeatureState({ source: 'grid', id: next }, { selected: true })
    }
    appliedSelectionRef.current = next
  }

  const applyParticles = () => {
    particleLayerRef.current?.setData(
      collectCellSamples(grid, pollutionRef.current?.values),
    )
  }

  useEffect(() => {
    if (!mapRef.current) return
    applyPollution(mapRef.current, pollutionData?.values)
    applyParticles()
  }, [pollutionData])

  useEffect(() => {
    if (mapRef.current) applySelection(mapRef.current)
  }, [selectedCellId])

  useEffect(() => {
    if (!containerRef.current) return

    const bounds = bboxOf(boundary)
    // Let panning breathe past the city, but no further — pad the max bounds
    // by half the city's span on each side
    const padLon = (bounds[1][0] - bounds[0][0]) / 2
    const padLat = (bounds[1][1] - bounds[0][1]) / 2
    const maxBounds: [[number, number], [number, number]] = [
      [bounds[0][0] - padLon, bounds[0][1] - padLat],
      [bounds[1][0] + padLon, bounds[1][1] + padLat],
    ]
    // First mount fits the city; theme switches keep the previous camera
    const camera = cameraRef.current
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: MAP_STYLES[isDark ? 'dark' : 'light'],
      ...(camera
        ? { center: camera.center, zoom: camera.zoom }
        : { bounds, fitBoundsOptions: { padding: 48 } }),
      maxBounds,
      attributionControl: { compact: true },
      dragRotate: false,
      pitchWithRotate: false,
    })
    map.touchZoomRotate.disableRotation()
    mapRef.current = map

    // Map chrome: zoom buttons, reset-to-city, scale bar
    map.addControl(
      new maplibregl.NavigationControl({ showCompass: false }),
      'top-right',
    )
    map.addControl(new FitCityControl(bounds, 48), 'top-right')
    map.addControl(
      new maplibregl.ScaleControl({ maxWidth: 120, unit: 'metric' }),
      'bottom-right',
    )

    // AQI haze — decorative motion, so skipped under prefers-reduced-motion
    if (!reducedMotion) {
      particleLayerRef.current = new AqiParticleLayer(map)
    }

    let hoveredId: string | number | null = null

    // Overlay ink — white lattice over the dark basemap, near-black over light
    const ink = isDark ? '#ffffff' : '#1a1a1a'

    map.on('load', () => {
      map.addSource('grid', {
        type: 'geojson',
        data: grid,
        promoteId: 'grid_id',
      })
      map.addSource('boundary', { type: 'geojson', data: boundary })

      // AQI heatmap fill; cells without a value yet stay near-invisible
      // white (so the lattice is still hoverable before data arrives)
      map.addLayer({
        id: 'grid-fill',
        type: 'fill',
        source: 'grid',
        paint: {
          // 'step' (not 'interpolate') so each cell shows its band's exact
          // color — an AQI-98 cell is green like its "Good" label, not
          // 98%-blended toward yellow
          'fill-color': [
            'case',
            ['<', AQI_STATE, 0],
            ink,
            [
              'step',
              AQI_STATE,
              AQI_STOPS[0].color,
              ...AQI_STOPS.slice(1).flatMap((s) => [s.aqi, s.color]),
            ],
          ],
          'fill-opacity': [
            'case',
            ['<', AQI_STATE, 0],
            ['case', ['boolean', ['feature-state', 'hover'], false], 0.27, 0.1],
            // Kept low enough that the basemap (streets, terrain) stays
            // legible under the heatmap — the band color still reads
            // clearly at this opacity, it just doesn't paint over everything.
            ['case', ['boolean', ['feature-state', 'hover'], false], 0.45, 0.24],
          ],
        },
      })
      map.addLayer({
        id: 'grid-line',
        type: 'line',
        source: 'grid',
        paint: {
          'line-color': ink,
          // fade the lattice in as you zoom closer; maplibre requires the
          // zoom expression at the top level, so hover lives in the outputs
          'line-opacity': [
            'interpolate',
            ['linear'],
            ['zoom'],
            10,
            ['case', ['boolean', ['feature-state', 'hover'], false], 0.6, 0.15],
            13,
            ['case', ['boolean', ['feature-state', 'hover'], false], 0.6, 0.35],
          ],
          'line-width': [
            'case',
            ['boolean', ['feature-state', 'hover'], false],
            1.5,
            0.5,
          ],
        },
      })
      // Pinned-cell outline — sits above the lattice so the selection stays
      // visible at any zoom (feature-state can't be used in filters, so the
      // layer is always present and non-selected cells render transparent)
      map.addLayer({
        id: 'grid-selected',
        type: 'line',
        source: 'grid',
        paint: {
          'line-color': ink,
          'line-opacity': [
            'case',
            ['boolean', ['feature-state', 'selected'], false],
            0.95,
            0,
          ],
          'line-width': 2.5,
        },
      })
      map.addLayer({
        id: 'boundary-line',
        type: 'line',
        source: 'boundary',
        paint: {
          'line-color': ink,
          'line-opacity': 0.35,
          'line-width': 1.5,
        },
      })

      // Values / selection may have arrived while the style was still loading
      applyPollution(map, pollutionRef.current?.values)
      applySelection(map)
      applyParticles()

      map.on('mousemove', 'grid-fill', (e) => {
        const feature = e.features?.[0]
        if (!feature) return
        if (hoveredId !== null && hoveredId !== feature.id) {
          map.setFeatureState(
            { source: 'grid', id: hoveredId },
            { hover: false },
          )
        }
        if (hoveredId !== feature.id) {
          hoveredId = feature.id ?? null
          map.setFeatureState(
            { source: 'grid', id: hoveredId! },
            { hover: true },
          )
          onHoverRef.current?.(feature.properties as unknown as GridCell)
        }
        map.getCanvas().style.cursor = 'crosshair'
      })
      map.on('mouseleave', 'grid-fill', () => {
        if (hoveredId !== null) {
          map.setFeatureState(
            { source: 'grid', id: hoveredId },
            { hover: false },
          )
          hoveredId = null
        }
        onHoverRef.current?.(null)
        map.getCanvas().style.cursor = ''
      })

      // Click — fire onClickCell so the detail panel can open
      map.on('click', 'grid-fill', (e) => {
        const feature = e.features?.[0]
        if (!feature) return
        onClickRef.current?.(feature.properties as unknown as GridCell)
      })
    })

    return () => {
      // Remember the view and forget map-scoped feature-state so the next
      // map (e.g. after a theme switch) resumes where this one left off
      cameraRef.current = { center: map.getCenter(), zoom: map.getZoom() }
      appliedSelectionRef.current = null
      mapRef.current = null
      particleLayerRef.current?.destroy()
      particleLayerRef.current = null
      map.remove()
    }
  }, [grid, boundary, isDark, reducedMotion])

  // maplibre-gl.css forces `position: relative` on the map element itself,
  // so size it with h-full inside an absolutely-positioned wrapper instead.
  // The wrapper fades in when data arrives (this component mounts data-ready).
  return (
    <div className="enter-fade absolute inset-0">
      <div ref={containerRef} className="h-full w-full" />
      <div aria-hidden className="map-vignette" />
    </div>
  )
}
