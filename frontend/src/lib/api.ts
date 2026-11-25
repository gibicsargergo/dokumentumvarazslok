import type { SearchStatsResponse } from './searchStats';

// Requests go to /api, which the Vite dev server proxies to the FastAPI backend.
const API_BASE = '/api';

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail ?? `Request failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}

export function getSearchStats(): Promise<SearchStatsResponse> {
  return getJson<SearchStatsResponse>('/admin/stats');
}
