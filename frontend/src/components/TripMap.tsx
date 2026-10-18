import 'maplibre-gl/dist/maplibre-gl.css';
import '../map/maplibreWorker';

import type { PickingInfo } from '@deck.gl/core';
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import Map, { NavigationControl, type MapRef } from 'react-map-gl/maplibre';

import type { PlannedRoute, TripPlan } from '../api/types';
import { routesBounds } from '../map/bounds';
import type { HeatmapImages } from '../map/heatmapImages';
import {
  buildCheckpointLayer,
  buildHeatmapLayer,
  buildRouteLayers,
  flattenCheckpoints,
  type CheckpointPoint,
} from '../map/layers';
import { CheckpointPopup } from './CheckpointPopup';
import { DeckOverlay } from './DeckOverlay';

// Free vector basemap from OpenFreeMap (no API key). "Positron" is light and
// calm, so the coloured routes and heatmap stand out.
const MAP_STYLE = 'https://tiles.openfreemap.org/styles/positron';
const INITIAL_VIEW = { longitude: -96, latitude: 38.5, zoom: 3.6 };
// Extra space at the bottom keeps routes clear of the heatmap panel.
const FIT_PADDING = { top: 60, bottom: 190, left: 60, right: 70 };

interface TripMapProps {
  plan: TripPlan | null;
  heatmapImages: HeatmapImages | null;
  heatmapHour: number;
  showHeatmap: boolean;
  selectedRouteId: number | null;
  hoveredRouteId: number | null;
  onSelectRoute: (routeId: number) => void;
  children?: ReactNode; // panels drawn on top of the map
}

export function TripMap({
  plan,
  heatmapImages,
  heatmapHour,
  showHeatmap,
  selectedRouteId,
  hoveredRouteId,
  onSelectRoute,
  children,
}: TripMapProps) {
  const mapRef = useRef<MapRef>(null);
  const routes = useMemo(() => plan?.routes ?? [], [plan]);

  // The popup remembers which routes it belongs to, so it disappears on its own
  // when a new plan arrives.
  const [popup, setPopup] = useState<{ point: CheckpointPoint; routes: PlannedRoute[] } | null>(null);
  const popupPoint = popup?.routes === routes ? popup.point : null;

  // Zoom to the routes whenever a new plan arrives.
  useEffect(() => {
    if (routes.length === 0) return;
    const { south, west, north, east } = routesBounds(routes);
    mapRef.current?.fitBounds(
      [
        [west, south],
        [east, north],
      ],
      { padding: FIT_PADDING, duration: 900 },
    );
  }, [routes]);

  // Each layer is rebuilt only when its own inputs change. Moving the heatmap
  // slider therefore rebuilds one cheap layer and nothing else.
  const checkpointPoints = useMemo(() => flattenCheckpoints(routes), [routes]);
  const routeLayers = useMemo(
    () => buildRouteLayers(routes, { selectedRouteId, hoveredRouteId }),
    [routes, selectedRouteId, hoveredRouteId],
  );
  const checkpointLayer = useMemo(
    () => buildCheckpointLayer(checkpointPoints, { selectedRouteId, hoveredRouteId }),
    [checkpointPoints, selectedRouteId, hoveredRouteId],
  );
  const heatmapLayer = useMemo(
    () => (heatmapImages ? buildHeatmapLayer(heatmapImages, heatmapHour, showHeatmap) : null),
    [heatmapImages, heatmapHour, showHeatmap],
  );
  const layers = useMemo(
    () => [heatmapLayer, ...routeLayers, checkpointLayer],
    [heatmapLayer, routeLayers, checkpointLayer],
  );

  function handleClick(info: PickingInfo) {
    if (info.layer?.id === 'checkpoints' && info.object) {
      setPopup({ point: info.object as CheckpointPoint, routes });
    } else if (info.layer?.id === 'routes' && info.object) {
      onSelectRoute((info.object as PlannedRoute).id);
    }
  }

  return (
    <div className="map-area">
      <Map
        ref={mapRef}
        initialViewState={INITIAL_VIEW}
        mapStyle={MAP_STYLE}
        style={{ width: '100%', height: '100%' }}
        attributionControl={{ compact: true }}
      >
        <NavigationControl position="top-right" showCompass={false} />
        <DeckOverlay
          layers={layers}
          onClick={handleClick}
          getCursor={({ isHovering, isDragging }) =>
            isDragging ? 'grabbing' : isHovering ? 'pointer' : 'grab'
          }
        />
        {popupPoint && <CheckpointPopup point={popupPoint} onClose={() => setPopup(null)} />}
      </Map>
      {children}
    </div>
  );
}
