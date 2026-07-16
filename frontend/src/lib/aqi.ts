export const AQI_STOPS = [
  { aqi: 0, color: '#6FCB6F', label: 'Good' },
  { aqi: 51, color: '#F8DF72', label: 'Satisfactory' },
  { aqi: 101, color: '#F4A93B', label: 'Moderate' },
  { aqi: 201, color: '#E4572E', label: 'Poor' },
  { aqi: 301, color: '#A62E2E', label: 'Very Poor' },
  { aqi: 401, color: '#6A0DAD', label: 'Severe' },
]

export function aqiColor(aqi: number) {
  let color = AQI_STOPS[0].color
  for (const stop of AQI_STOPS) {
    if (aqi >= stop.aqi) color = stop.color
  }
  return color
}

export function aqiLabel(aqi: number): string {
  let label = AQI_STOPS[0].label
  for (const s of AQI_STOPS) if (aqi >= s.aqi) label = s.label
  return label
}
