/**
 * Map data (GeoJSON) and MapLibre layer styles for routes and checkpoints.
 *
 * Everything is drawn by MapLibre itself. Routes and checkpoints share one
 * GeoJSON source, so their layers are always created together and stacked in
 * a fixed order (route outline, route line, checkpoint dots on top).
 * Highlighting a route only changes a style expression (which route id is
 * "active"), so the GPU restyles the existing data instead of rebuilding it.
 */
import type { FeatureCollection, LineString, Point } from 'geojson';
import type { ExpressionSpecification } from 'maplibre-gl';
import type { LayerProps } from 'react-map-gl/maplibre';

import type { Checkpoint, PlannedRoute } from '../api/types';
import { RISK_LEVELS } from '../api/types';
import { RISK_COLORS, ROUTE_COLORS } from '../risk';

export const ROUTE_CASING_LAYER_ID = 'route-casing';
export const ROUTE_LAYER_ID = 'routes';
export const CHECKPOINT_LAYER_ID = 'checkpoints';

/** A checkpoint plus the route it belongs to (what the popup shows). */
export interface CheckpointPoint {
  routeId: number;
  routeName: string;
  checkpoint: Checkpoint;
}

export const TRIP_SOURCE_ID = 'trip';

type TripFeatureProperties = { routeId: number; index?: number; level?: string };
type TripCollection = FeatureCollection<LineString | Point, TripFeatureProperties>;

/** One collection: a line per route plus a point per checkpoint. */
export function tripToGeoJson(routes: PlannedRoute[]): TripCollection {
  const lines = routes.map((route) => ({
    type: 'Feature' as const,
    properties: { routeId: route.id },
    geometry: { type: 'LineString' as const, coordinates: route.geometry },
  }));
  const points = routes.flatMap((route) =>
    route.checkpoints.map((checkpoint) => ({
      type: 'Feature' as const,
      properties: { routeId: route.id, index: checkpoint.index, level: checkpoint.level },
      geometry: { type: 'Point' as const, coordinates: [checkpoint.lon, checkpoint.lat] },
    })),
  );
  return { type: 'FeatureCollection', features: [...lines, ...points] };
}

const IS_LINE: ExpressionSpecification = ['==', ['geometry-type'], 'LineString'];
const IS_POINT: ExpressionSpecification = ['==', ['geometry-type'], 'Point'];

/** Finds the checkpoint a clicked map feature stands for. */
export function findCheckpoint(
  routes: PlannedRoute[],
  routeId: number,
  index: number,
): CheckpointPoint | null {
  const route = routes.find((candidate) => candidate.id === routeId);
  const checkpoint = route?.checkpoints[index];
  return route && checkpoint ? { routeId, routeName: route.name, checkpoint } : null;
}

/** `whenActive` for the active route's features, `otherwise` for the rest. */
function byActive<T extends number | string>(
  property: string,
  activeId: number | null,
  whenActive: T,
  otherwise: T,
): ExpressionSpecification {
  return ['case', ['==', ['get', property], activeId ?? -1], whenActive, otherwise];
}

/**
 * ['match', input, value1, output1, value2, output2, ..., fallback]
 * MapLibre's types can't describe a list built at runtime, hence the cast.
 */
function matchExpression(property: string, pairs: (string | number)[], fallback: string) {
  return ['match', ['get', property], ...pairs, fallback] as unknown as ExpressionSpecification;
}

// Built for every palette colour (not just the current routes), so the
// expression is valid even before any route exists.
const routeColorExpression = matchExpression(
  'routeId',
  ROUTE_COLORS.flatMap((color, id) => [id, color]),
  ROUTE_COLORS[0],
);

const riskColorExpression = matchExpression(
  'level',
  RISK_LEVELS.flatMap((level) => [level, RISK_COLORS[level]]),
  RISK_COLORS.Low,
);

export function routeCasingLayer(activeId: number | null): LayerProps {
  return {
    id: ROUTE_CASING_LAYER_ID,
    type: 'line',
    filter: IS_LINE,
    layout: {
      'line-cap': 'round',
      'line-join': 'round',
      'line-sort-key': byActive('routeId', activeId, 1, 0), // active route on top
    },
    paint: { 'line-color': '#ffffff', 'line-width': byActive('routeId', activeId, 10, 6) },
  };
}

export function routeLayer(activeId: number | null): LayerProps {
  return {
    id: ROUTE_LAYER_ID,
    type: 'line',
    filter: IS_LINE,
    layout: {
      'line-cap': 'round',
      'line-join': 'round',
      'line-sort-key': byActive('routeId', activeId, 1, 0),
    },
    paint: {
      'line-color': routeColorExpression,
      'line-width': byActive('routeId', activeId, 6, 3.5),
      'line-opacity': byActive('routeId', activeId, 1, 0.6),
    },
  };
}

export function checkpointLayer(activeId: number | null): LayerProps {
  return {
    id: CHECKPOINT_LAYER_ID,
    type: 'circle',
    filter: IS_POINT,
    layout: { 'circle-sort-key': byActive('routeId', activeId, 1, 0) },
    paint: {
      'circle-color': riskColorExpression,
      // Small when zoomed out (checkpoints are close together), bigger when zoomed in.
      'circle-radius': [
        'interpolate',
        ['linear'],
        ['zoom'],
        4,
        byActive('routeId', activeId, 3.5, 2),
        8,
        byActive('routeId', activeId, 7, 4),
      ],
      'circle-opacity': byActive('routeId', activeId, 1, 0.7),
      'circle-stroke-color': '#ffffff',
      'circle-stroke-width': byActive('routeId', activeId, 1.5, 0.75),
    },
  };
}
