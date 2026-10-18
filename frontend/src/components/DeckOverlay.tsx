import { MapboxOverlay, type MapboxOverlayProps } from '@deck.gl/mapbox';
import { useControl } from 'react-map-gl/maplibre';

/**
 * Draws deck.gl layers on top of the MapLibre map.
 *
 * useControl creates the overlay once and adds it to the map; every render
 * then just passes the new props (layers) to it.
 */
export function DeckOverlay(props: MapboxOverlayProps) {
  const overlay = useControl<MapboxOverlay>(() => new MapboxOverlay(props));
  overlay.setProps(props);
  return null;
}
