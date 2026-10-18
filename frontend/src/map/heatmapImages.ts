import type { Heatmap, RiskLevel } from '../api/types';
import { RISK_LEVELS } from '../api/types';
import { RISK_RGB } from '../risk';

/**
 * Turns the heatmap grid into one tiny image per forecast hour.
 *
 * Each grid point becomes one pixel. The map stretches the image over the
 * area and the GPU blends neighbouring pixels, which gives a smooth heatmap
 * at every zoom level. All 49 images are built once, so moving the slider
 * only swaps which image is shown.
 */
export interface HeatmapImages {
  /** [west, south, east, north] of the image, as deck.gl's BitmapLayer expects. */
  bounds: [number, number, number, number];
  frames: HTMLCanvasElement[];
  times: string[];
}

// Opacity per level: calm areas only get a light tint so the map stays readable.
const LEVEL_ALPHA: Record<RiskLevel, number> = {
  Low: 0.08,
  Moderate: 0.35,
  High: 0.45,
  Severe: 0.55,
  'No Travel': 0.65,
};
const ALPHA_RAMP_WITHIN_LEVEL = 0.15;

export function buildHeatmapImages(heatmap: Heatmap): HeatmapImages {
  const size = Math.round(Math.sqrt(heatmap.points.length));
  const [west, south] = heatmap.points[0];
  const [east, north] = heatmap.points[heatmap.points.length - 1];

  // Grid points are pixel *centres*, so the image reaches half a cell beyond them.
  const halfLon = (east - west) / (size - 1) / 2;
  const halfLat = (north - south) / (size - 1) / 2;

  return {
    bounds: [west - halfLon, south - halfLat, east + halfLon, north + halfLat],
    frames: heatmap.frames.map((frame) => frameToCanvas(frame.intensity, size)),
    times: heatmap.frames.map((frame) => frame.time),
  };
}

function frameToCanvas(intensity: number[], size: number): HTMLCanvasElement {
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const context = canvas.getContext('2d')!;
  const image = context.createImageData(size, size);

  for (let row = 0; row < size; row++) {
    for (let col = 0; col < size; col++) {
      const [r, g, b, a] = colorFor(intensity[row * size + col]);
      // Grid rows start in the south; image rows start at the top (north).
      const offset = ((size - 1 - row) * size + col) * 4;
      image.data.set([r, g, b, Math.round(a * 255)], offset);
    }
  }
  context.putImageData(image, 0, 0);
  return canvas;
}

/** The official level colour, slightly more opaque the closer it is to the next level. */
function colorFor(intensity: number): [number, number, number, number] {
  const scaled = Math.min(Math.max(intensity, 0), 1) * (RISK_LEVELS.length - 1);
  const levelIndex = Math.min(Math.floor(scaled), RISK_LEVELS.length - 1);
  const level = RISK_LEVELS[levelIndex];
  const withinLevel = scaled - levelIndex;
  const [r, g, b] = RISK_RGB[level];
  return [r, g, b, LEVEL_ALPHA[level] + ALPHA_RAMP_WITHIN_LEVEL * withinLevel];
}
