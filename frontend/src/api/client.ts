import type { Heatmap, HeatmapRequest, Place, PlanRequest, TripPlan } from './types';

const API_URL = (import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000/api').replace(/\/$/, '');

/** Friendly names for the field keys DRF uses in validation errors. */
const FIELD_LABELS: Record<string, string> = {
  origin: 'Origin',
  destination: 'Destination',
  departure: 'Departure',
  start: 'Departure',
  load_lb: 'Load weight',
  interval_miles: 'Checkpoint interval',
};

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, init);
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error;
    throw new ApiError('Cannot reach the server. Is the backend running?', 0);
  }

  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) throw new ApiError(errorMessage(body, response.status), response.status);
  return body as T;
}

/** Turns DRF error bodies ({"detail": "..."} or {"field": ["..."]}) into one sentence. */
function errorMessage(body: unknown, status: number): string {
  if (body && typeof body === 'object') {
    const record = body as Record<string, unknown>;
    if (typeof record.detail === 'string') return record.detail;

    const messages = Object.entries(record).flatMap(([field, value]) => {
      const texts = Array.isArray(value) ? value : [value];
      const label = FIELD_LABELS[field];
      return texts.map((text) => (label ? `${label}: ${String(text)}` : String(text)));
    });
    if (messages.length > 0) return messages.join(' ');
  }
  return `Request failed (HTTP ${status}).`;
}

export const api = {
  searchPlaces(query: string, signal?: AbortSignal): Promise<Place[]> {
    const params = new URLSearchParams({ q: query });
    return request<{ results: Place[] }>(`/geocode/?${params}`, { signal }).then((data) => data.results);
  },

  planTrip(body: PlanRequest, signal?: AbortSignal): Promise<TripPlan> {
    return request<TripPlan>('/plan/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal,
    });
  },

  fetchHeatmap(query: HeatmapRequest, signal?: AbortSignal): Promise<Heatmap> {
    const params = new URLSearchParams(
      Object.entries(query).map(([key, value]) => [key, String(value)]),
    );
    return request<Heatmap>(`/heatmap/?${params}`, { signal });
  },
};
