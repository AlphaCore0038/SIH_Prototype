import type { ForecastPoint } from '../types/cyclone';

const ML_API_BASE = 'http://localhost:8000';
const TIMEOUT_MS = 5000;

interface MlForecastResponse {
  forecast: Array<{ hoursAhead: number; lat: number; lon: number }>;
  model: string;
  source: string;
}

export async function fetchMlForecast(
  track: Array<{ lat: number; lon: number; wind?: number; timestamp?: string }>,
): Promise<ForecastPoint[]> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), TIMEOUT_MS);

  try {
    const res = await fetch(`${ML_API_BASE}/api/forecast`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ track }),
      signal: controller.signal,
    });

    if (!res.ok) {
      throw new Error(`ML API ${res.status}: ${res.statusText}`);
    }

    const data: MlForecastResponse = await res.json();

    return data.forecast.map((f) => ({
      hoursAhead: f.hoursAhead,
      lat: f.lat,
      lon: f.lon,
      timestamp: '', // caller will compute from current time + hoursAhead
    }));
  } finally {
    clearTimeout(timeout);
  }
}
