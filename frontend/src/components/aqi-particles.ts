/**
 * AqiParticleLayer — ambient AQI particles, drawn on a 2D canvas overlaid on
 * the MapLibre map.
 *
 * Motion model: neighboring cells that share the same AQI *category* are
 * flood-filled into one region, and each region gets its own small flock of
 * particles that swirl around **inside that region only** — a particle over
 * a "Poor" pocket stays in the Poor pocket, it never bleeds into the
 * "Satisfactory" area next door. Worse-air regions get denser, bigger,
 * faster particles. (Free wind-drift across the map read as the map
 * "bleeding"; per-tile particles were too busy — this is the middle:
 * one shared population per same-band neighborhood.)
 *
 * Rendering projects each particle to screen space per frame and draws
 * canvas arcs at ~30fps — no GeoJSONSource.setData() involved, so the
 * animation stays smooth regardless of particle count.
 */

import { AQI_STOPS } from '@/lib/aqi'
import type maplibregl from 'maplibre-gl'
import type { FeatureCollection } from 'geojson'

const MAX_PARTICLES = 450
const FRAME_MS = 33 // ~30fps — ambient texture, doesn't need 60
/** Particles per member cell, indexed by severity (1 = Good … 6 = Severe) */
const WEIGHT_BY_SEVERITY = [0, 0.25, 0.4, 0.8, 1.4, 2.2, 3.2]
const SIZE_BY_SEVERITY = [0, 1, 1.1, 1.3, 1.6, 1.9, 2.3]
/** Wander speed in degrees/second — gentle, scaled up with severity */
const SPEED_BY_SEVERITY = [0, 0.0008, 0.001, 0.0013, 0.0016, 0.002, 0.0024]

export interface CellSample {
  lon: number
  lat: number
  row: number
  col: number
  aqi: number
}

interface Region {
  cells: Array<CellSample>
  /** row/col membership for cheap "is this position still inside?" checks */
  keys: Set<number>
  severity: number
  color: string
}

interface Particle {
  lng: number
  lat: number
  /** Current wander heading, radians */
  heading: number
  /** Constant per-particle turn bias — makes paths curl instead of beeline */
  curl: number
  speed: number
  size: number
  age: number
  life: number
  region: Region
}

const keyOf = (row: number, col: number) => row * 8192 + col

/** Pull per-cell centroid + row/col + AQI samples out of the grid. */
export function collectCellSamples(
  grid: FeatureCollection,
  values: Record<string, number> | undefined,
): Array<CellSample> {
  if (!values) return []
  const samples: Array<CellSample> = []
  for (const feature of grid.features) {
    const props = feature.properties as {
      grid_id?: string
      row?: number
      col?: number
      centroid_lon?: number
      centroid_lat?: number
    } | null
    if (
      props?.grid_id === undefined ||
      !Object.hasOwn(values, props.grid_id) ||
      props.row === undefined ||
      props.col === undefined ||
      props.centroid_lon === undefined ||
      props.centroid_lat === undefined
    )
      continue
    samples.push({
      lon: props.centroid_lon,
      lat: props.centroid_lat,
      row: props.row,
      col: props.col,
      aqi: values[props.grid_id],
    })
  }
  return samples
}

/** Flood-fill 4-connected cells sharing one AQI band into regions. */
function buildRegions(samples: Array<CellSample>): Array<Region> {
  const severityOf = (aqi: number) =>
    AQI_STOPS.filter((stop) => aqi >= stop.aqi).length // 1..6

  const byKey = new Map<number, CellSample>()
  for (const s of samples) byKey.set(keyOf(s.row, s.col), s)

  const visited = new Set<number>()
  const regions: Array<Region> = []

  for (const s of samples) {
    const startKey = keyOf(s.row, s.col)
    if (visited.has(startKey)) continue

    const severity = severityOf(s.aqi)
    const cells: Array<CellSample> = []
    const keys = new Set<number>()
    const stack = [s]
    visited.add(startKey)

    while (stack.length > 0) {
      const cell = stack.pop()!
      cells.push(cell)
      keys.add(keyOf(cell.row, cell.col))
      for (const [dr, dc] of [
        [1, 0],
        [-1, 0],
        [0, 1],
        [0, -1],
      ]) {
        const nKey = keyOf(cell.row + dr, cell.col + dc)
        if (visited.has(nKey)) continue
        const neighbor = byKey.get(nKey)
        if (neighbor && severityOf(neighbor.aqi) === severity) {
          visited.add(nKey)
          stack.push(neighbor)
        }
      }
    }

    regions.push({
      cells,
      keys,
      severity,
      color: AQI_STOPS[severity - 1]?.color ?? '#999999',
    })
  }
  return regions
}

export class AqiParticleLayer {
  private canvas: HTMLCanvasElement
  private ctx: CanvasRenderingContext2D | null
  private rafId: number | null = null
  private particles: Array<Particle> = []
  private rafLastFrame = 0
  // Grid geometry (derived from the samples) — maps lng/lat back to
  // row/col so containment checks are O(1) set lookups
  private lon0 = 0
  private lat0 = 0
  private lonStep = 0.009
  private latStep = 0.009

  constructor(private map: maplibregl.Map) {
    this.canvas = document.createElement('canvas')
    this.canvas.style.cssText =
      'position:absolute;inset:0;width:100%;height:100%;pointer-events:none;'
    this.canvas.setAttribute('aria-hidden', 'true')
    // Canvas container keeps the haze under the map controls / attribution
    map.getCanvasContainer().appendChild(this.canvas)
    this.ctx = this.canvas.getContext('2d')
    this.rafId = requestAnimationFrame(this.tick)
  }

  /** (Re)build regions + particle population from the current snapshot. */
  setData(samples: Array<CellSample>): void {
    if (samples.length === 0) {
      this.particles = []
      return
    }

    // Fit the grid's linear row/col ↔ lon/lat mapping from the data itself
    let minRow = Infinity
    let maxRow = -Infinity
    let minCol = Infinity
    let maxCol = -Infinity
    let minRowCell = samples[0]
    let maxRowCell = samples[0]
    let minColCell = samples[0]
    let maxColCell = samples[0]
    for (const s of samples) {
      if (s.row < minRow) [minRow, minRowCell] = [s.row, s]
      if (s.row > maxRow) [maxRow, maxRowCell] = [s.row, s]
      if (s.col < minCol) [minCol, minColCell] = [s.col, s]
      if (s.col > maxCol) [maxCol, maxColCell] = [s.col, s]
    }
    if (maxCol > minCol)
      this.lonStep = (maxColCell.lon - minColCell.lon) / (maxCol - minCol)
    if (maxRow > minRow)
      this.latStep = (maxRowCell.lat - minRowCell.lat) / (maxRow - minRow)
    this.lon0 = minColCell.lon - minCol * this.lonStep
    this.lat0 = minRowCell.lat - minRow * this.latStep

    const regions = buildRegions(samples)

    // Allocate the particle budget across regions by size × severity
    let totalWeight = 0
    for (const r of regions)
      totalWeight += r.cells.length * (WEIGHT_BY_SEVERITY[r.severity] ?? 0)
    const scale =
      totalWeight > 0 ? Math.min(1, MAX_PARTICLES / totalWeight) : 0

    this.particles = []
    for (const region of regions) {
      const weight =
        region.cells.length * (WEIGHT_BY_SEVERITY[region.severity] ?? 0)
      const count = Math.round(weight * scale)
      for (let i = 0; i < count; i++) {
        const p = this.spawn(region)
        // Stagger ages so fades aren't synchronized across the population
        p.age = Math.random() * p.life
        this.particles.push(p)
      }
    }
  }

  destroy(): void {
    if (this.rafId !== null) cancelAnimationFrame(this.rafId)
    this.rafId = null
    this.canvas.remove()
  }

  private spawn(region: Region): Particle {
    const cell = region.cells[(Math.random() * region.cells.length) | 0]
    return {
      lng: cell.lon + (Math.random() - 0.5) * this.lonStep * 0.9,
      lat: cell.lat + (Math.random() - 0.5) * this.latStep * 0.9,
      heading: Math.random() * Math.PI * 2,
      curl: (Math.random() - 0.5) * 1.6,
      speed:
        (SPEED_BY_SEVERITY[region.severity] ?? 0.001) *
        (0.7 + Math.random() * 0.6),
      size: SIZE_BY_SEVERITY[region.severity] ?? 1,
      age: 0,
      life: 8 + Math.random() * 8,
      region,
    }
  }

  private inRegion(region: Region, lng: number, lat: number): boolean {
    const col = Math.round((lng - this.lon0) / this.lonStep)
    const row = Math.round((lat - this.lat0) / this.latStep)
    return region.keys.has(keyOf(row, col))
  }

  private tick = (now: number) => {
    this.rafId = requestAnimationFrame(this.tick)
    if (document.hidden || now - this.rafLastFrame < FRAME_MS) return
    // Clamp dt so a background/tab-switch gap doesn't teleport everything
    const dt = Math.min((now - this.rafLastFrame) / 1000, 0.1)
    this.rafLastFrame = now

    const ctx = this.ctx
    if (!ctx || this.particles.length === 0) return

    // Keep the canvas matched to the map (cheap check every frame)
    const w = this.canvas.clientWidth
    const h = this.canvas.clientHeight
    const dpr = Math.min(window.devicePixelRatio || 1, 2)
    if (this.canvas.width !== w * dpr || this.canvas.height !== h * dpr) {
      this.canvas.width = w * dpr
      this.canvas.height = h * dpr
    }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    ctx.clearRect(0, 0, w, h)

    for (const p of this.particles) {
      p.age += dt
      if (p.age >= p.life) {
        // Respawn inside the same region — the per-region census stays put
        Object.assign(p, this.spawn(p.region), { region: p.region })
      }

      // Curling wander: constant per-particle turn bias + a little jitter
      p.heading += (p.curl + (Math.random() - 0.5) * 2) * dt
      let nextLng = p.lng + Math.cos(p.heading) * p.speed * dt
      let nextLat = p.lat + Math.sin(p.heading) * p.speed * dt * 0.85

      if (!this.inRegion(p.region, nextLng, nextLat)) {
        // About to cross the region border — turn back toward a random
        // member cell instead of leaving
        const home =
          p.region.cells[(Math.random() * p.region.cells.length) | 0]
        p.heading = Math.atan2(home.lat - p.lat, home.lon - p.lng)
        nextLng = p.lng + Math.cos(p.heading) * p.speed * dt
        nextLat = p.lat + Math.sin(p.heading) * p.speed * dt * 0.85
        if (!this.inRegion(p.region, nextLng, nextLat)) {
          // Cornered (single-cell region edge) — stay put this frame
          nextLng = p.lng
          nextLat = p.lat
        }
      }
      p.lng = nextLng
      p.lat = nextLat

      const pt = this.map.project([p.lng, p.lat])
      if (pt.x < -12 || pt.y < -12 || pt.x > w + 12 || pt.y > h + 12) continue

      // Ease in over the first ~1.2s, out over the last ~2s
      const alpha =
        0.65 * Math.min(1, p.age / 1.2, Math.max(0, (p.life - p.age) / 2))
      if (alpha <= 0.01) continue

      ctx.globalAlpha = alpha
      ctx.fillStyle = p.region.color
      ctx.beginPath()
      ctx.arc(pt.x, pt.y, p.size, 0, Math.PI * 2)
      ctx.fill()
    }
    ctx.globalAlpha = 1
  }
}
