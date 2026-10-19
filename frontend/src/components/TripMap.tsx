import 'maplibre-gl/dist/maplibre-gl.css';
import '../map/maplibreWorker';

import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import Map, {
  Layer,
  NavigationControl,
  Source,
  type MapLayerMouseEvent,
  type MapRef,
} from 'react-map-gl/maplibre';

import type { PlannedRoute, TripPlan } from '../api/types';
import { routesBounds } from '../map/bounds';
import type { HeatmapImages } from '../map/heatmapImages';
import {
  CHECKPOINT_LAYER_ID,
  ROUTE_CASING_LAYER_ID,
  ROUTE_LAYER_ID,
  TRIP_SOURCE_ID,
  checkpointLayer,
  findCheckpoint,
  routeCasingLayer,
  routeLayer,
  tripToGeoJson,
  type CheckpointPoint,
} from '../map/layers';
import { CheckpointPopup } from './CheckpointPopup';

// Free vector basemap from OpenFreeMap (no API key). "Positron" is light and
// calm, so the coloured routes and heatmap stand out.
const MAP_STYLE = 'https://tiles.openfreemap.org/styles/positron';
const INITIAL_VIEW = { longitude: -96, latitude: 38.5, zoom: 3.6 };
// Extra space at the bottom keeps routes clear of the heatmap panel.
const FIT_PADDING = { top: 60, bottom: 190, left: 60, right: 70 };
const CLICKABLE_LAYERS = [CHECKPOINT_LAYER_ID, ROUTE_LAYER_ID];

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
  const [cursor, setCursor] = useState('grab');
  const routes = useMemo(() => plan?.routes ?? [], [plan]);
  const activeRouteId = hoveredRouteId ?? selectedRouteId;

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

  // GeoJSON is rebuilt only for a new plan. Highlighting and the heatmap
  // slider just change styles or swap an image, which is cheap.
  const tripData = useMemo(() => tripToGeoJson(routes), [routes]);
  const casingStyle = useMemo(() => routeCasingLayer(activeRouteId), [activeRouteId]);
  const routeStyle = useMemo(() => routeLayer(activeRouteId), [activeRouteId]);
  const checkpointStyle = useMemo(() => checkpointLayer(activeRouteId), [activeRouteId]);

  function handleClick(event: MapLayerMouseEvent) {
    const feature = event.features?.[0];
    if (!feature) return;
    const properties = feature.properties as Record<string, number>;
    if (feature.layer.id === CHECKPOINT_LAYER_ID) {
      const point = findCheckpoint(routes, properties.routeId, properties.index);
      if (point) setPopup({ point, routes });
    } else if (feature.layer.id === ROUTE_LAYER_ID) {
      onSelectRoute(properties.routeId);
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
        interactiveLayerIds={CLICKABLE_LAYERS}
        cursor={cursor}
        onClick={handleClick}
        onMouseEnter={() => setCursor('pointer')}
        onMouseLeave={() => setCursor('grab')}
      >
        <NavigationControl position="top-right" showCompass={false} />

        {/* These layers always exist (empty before a plan), so the heatmap can
            always be inserted underneath them. */}
        <Source id={TRIP_SOURCE_ID} type="geojson" data={tripData}>
          <Layer {...casingStyle} />
          <Layer {...routeStyle} />
          <Layer {...checkpointStyle} />
        </Source>

        {heatmapImages && (
          <Source
            id="heatmap"
            type="image"
            url={heatmapImages.frames[heatmapHour]}
            coordinates={heatmapImages.coordinates}
          >
            <Layer
              id="heatmap"
              type="raster"
              beforeId={ROUTE_CASING_LAYER_ID}
              layout={{ visibility: showHeatmap ? 'visible' : 'none' }}
              paint={{ 'raster-fade-duration': 0, 'raster-resampling': 'linear' }}
            />
          </Source>
        )}

        {popupPoint && <CheckpointPopup point={popupPoint} onClose={() => setPopup(null)} />}
      </Map>
      {children}
    </div>
  );
}
