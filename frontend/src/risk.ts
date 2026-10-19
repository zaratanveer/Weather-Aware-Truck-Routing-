import type { Checkpoint, RiskLevel } from './api/types';

export type Rgb = [number, number, number];

/** One colour per risk level, used by the map, the cards and the legend. */
export const RISK_COLORS: Record<RiskLevel, string> = {
  Low: '#16a34a',
  Moderate: '#eab308',
  High: '#f97316',
  Severe: '#dc2626',
  'No Travel': '#6b21a8',
};

/** Route line colours, chosen so they don't clash with the risk colours. */
export const ROUTE_COLORS = ['#2563eb', '#0891b2', '#334155'];

export function routeColor(index: number): string {
  return ROUTE_COLORS[index % ROUTE_COLORS.length];
}

export function hexToRgb(hex: string): Rgb {
  const value = Number.parseInt(hex.slice(1), 16);
  return [(value >> 16) & 255, (value >> 8) & 255, value & 255];
}

export const RISK_RGB = Object.fromEntries(
  Object.entries(RISK_COLORS).map(([level, hex]) => [level, hexToRgb(hex)]),
) as Record<RiskLevel, Rgb>;

const DRIVER_NAMES: Record<Checkpoint['drivers'][number], string> = {
  wind: 'wind',
  rain: 'rain',
  snow: 'snow',
  load: 'heavy load in strong wind',
};

/** E.g. ["rain", "snow"] -> "Caused by rain and snow". */
export function describeDrivers(drivers: Checkpoint['drivers']): string {
  if (drivers.length === 0) return 'Calm conditions';
  const names = drivers.map((driver) => DRIVER_NAMES[driver]);
  const list = names.length > 1 ? `${names.slice(0, -1).join(', ')} and ${names.at(-1)}` : names[0];
  return `Caused by ${list}`;
}
