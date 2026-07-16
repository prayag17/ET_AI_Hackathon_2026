export interface Recommendation {
  cell_id: string;
  action: string;
  grap_stage: string;
  priority: string;
  reason: string;
  citizen_advisory: string[];
  is_baseline: boolean;
  stage_color: string;
  start_by: string;
  confidence: number;
}

const API_BASE = '/api/maps';

export async function getGrid() {
  const res = await fetch(`${API_BASE}/getMap`);
  if (!res.ok) throw new Error('Failed to fetch grid');
  return res.json();
}

export async function getBoundary() {
  const res = await fetch(`${API_BASE}/getBoundary`);
  if (!res.ok) throw new Error('Failed to fetch boundary');
  return res.json();
}

export async function getPollution() {
  const res = await fetch(`${API_BASE}/getPollution`);
  if (!res.ok) throw new Error('Failed to fetch pollution');
  return res.json();
}

export async function getForecast() {
  const res = await fetch(`${API_BASE}/getForecast`);
  if (!res.ok) throw new Error('Failed to fetch forecast');
  return res.json();
}

export async function getAdvisory(): Promise<{ advisories: Recommendation[] }> {
  const res = await fetch(`${API_BASE}/getAdvisory`);
  if (!res.ok) throw new Error('Failed to fetch advisory');
  return res.json();
}
