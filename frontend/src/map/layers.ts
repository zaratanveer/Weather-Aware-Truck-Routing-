import { COORDINATE_SYSTEM } from '@deck.gl/core';
import { BitmapLayer, PathLayer, ScatterplotLayer } from '@deck.gl/layers';

import type { Checkpoint, PlannedRoute } from '../api/types';
import { RISK_RGB, hexToRgb, routeColor } from '../risk';
import type { HeatmapImages } from './heatmapImages';

/** A checkpoint plus the route it belongs to (deck.gl layers want one flat list). */
export interface CheckpointPoint {
  routeId: number;
  routeName: string;
  checkpoint: Checkpoint;
}

export interface Highlight {
  selectedRouteId: number | null;
  hoveredRouteId: number | null;
}

const WHITE: [number, number, number] = [255, 255, 255];

export function flattenCheckpoints(routes: PlannedRoute[]): CheckpointPoint[] {
  return routes.flatMap((route) =>
    route.checkpoints.map((checkpoint) => ({ routeId: route.id, routeName: route.name, checkpoint })),
  );
}

export function buildHeatmapLayer(images: HeatmapImages, hour: number, visible: boolean) {
  return new BitmapLayer({
    id: 'weather-heatmap',
    image: images.frames[hour],
    bounds: images.bounds,
    // Grid rows are evenly spaced in latitude, so map the image in lng/lat space.
    _imageCoordinateSystem: COORDINATE_SYSTEM.LNGLAT,
    visible,
  });
}

/** Route lines. The highlighted route is drawn last (on top) with a white casing. */
export function buildRouteLayers(routes: PlannedRoute[], highlight: Highlight) {
  const activeId = highlight.hoveredRouteId ?? highlight.selectedRouteId;
  const ordered = [...routes].sort((a, b) => Number(a.id === activeId) - Number(b.id === activeId));
  const isActive = (route: PlannedRoute) => route.id === activeId;

  return [
    new PathLayer<PlannedRoute>({
      id: 'route-casing',
      data: ordered,
      getPath: (route) => route.geometry,
      getColor: [...WHITE, 230],
      getWidth: (route) => (isActive(route) ? 10 : 6),
      widthUnits: 'pixels',
      capRounded: true,
      jointRounded: true,
      updateTriggers: { getWidth: activeId },
    }),
    new PathLayer<PlannedRoute>({
      id: 'routes',
      data: ordered,
      pickable: true,
      getPath: (route) => route.geometry,
      getColor: (route) => [...hexToRgb(routeColor(route.id)), isActive(route) ? 255 : 150],
      getWidth: (route) => (isActive(route) ? 6 : 3.5),
      widthUnits: 'pixels',
      capRounded: true,
      jointRounded: true,
      updateTriggers: { getColor: activeId, getWidth: activeId },
    }),
  ];
}

/** Checkpoint dots coloured by risk level; the highlighted route's dots are larger. */
export function buildCheckpointLayer(points: CheckpointPoint[], highlight: Highlight) {
  const activeId = highlight.hoveredRouteId ?? highlight.selectedRouteId;
  const isActive = (point: CheckpointPoint) => point.routeId === activeId;

  return new ScatterplotLayer<CheckpointPoint>({
    id: 'checkpoints',
    data: points,
    pickable: true,
    getPosition: (point) => [point.checkpoint.lon, point.checkpoint.lat],
    getFillColor: (point) => [...RISK_RGB[point.checkpoint.level], isActive(point) ? 255 : 170],
    getRadius: (point) => (isActive(point) ? 6 : 3.5),
    radiusUnits: 'pixels',
    stroked: true,
    getLineColor: WHITE,
    getLineWidth: (point) => (isActive(point) ? 2 : 1),
    lineWidthUnits: 'pixels',
    updateTriggers: { getFillColor: activeId, getRadius: activeId, getLineWidth: activeId },
  });
}
