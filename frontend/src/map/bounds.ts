import type { Bounds, PlannedRoute } from '../api/types';

/** The smallest box containing every route. */
export function routesBounds(routes: PlannedRoute[]): Bounds {
  const bounds: Bounds = { south: 90, west: 180, north: -90, east: -180 };
  for (const route of routes) {
    for (const [lon, lat] of route.geometry) {
      bounds.south = Math.min(bounds.south, lat);
      bounds.north = Math.max(bounds.north, lat);
      bounds.west = Math.min(bounds.west, lon);
      bounds.east = Math.max(bounds.east, lon);
    }
  }
  return bounds;
}
