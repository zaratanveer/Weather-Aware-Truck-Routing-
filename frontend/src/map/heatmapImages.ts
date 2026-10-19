import type { Heatmap, RiskLevel } from '../api/types';
import { RISK_LEVELS } from '../api/types';
import { RISK_RGB } from '../risk';

/**
 * Turns the heatmap grid into one small image per forecast hour.
 *
 * The forecast grid is coarse (15 x 15 points), so each image pixel blends
 * the four nearest grid points (bilinear interpolation), which gives a smooth
 * heatmap. All 49 images are built once, so moving the slider only swaps
 * which image the map shows.
 */
export interface HeatmapImages {
  /** Image corners [lon, lat]: top-left, top-right, bottom-right, bottom-left. */
  coordinates: [[number, number], [number, number], [number, number], [number, number]];
  frames: string[]; // PNG data URLs, one per hour
  times: string[];
}

const IMAGE_SIZE = 96; // pixels per side

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
  const grid = { size, west, south, east, north };

  return {
    coordinates: [
      [west, north],
      [east, north],
      [east, south],
      [west, south],
    ],
    frames: heatmap.frames.map((frame) => frameToDataUrl(frame.intensity, grid)),
    times: heatmap.frames.map((frame) => frame.time),
  };
}

interface Grid {
  size: number;
  west: number;
  south: number;
  east: number;
  north: number;
}

function frameToDataUrl(intensity: number[], grid: Grid): string {
  const canvas = document.createElement('canvas');
  canvas.width = IMAGE_SIZE;
  canvas.height = IMAGE_SIZE;
  const context = canvas.getContext('2d')!;
  const image = context.createImageData(IMAGE_SIZE, IMAGE_SIZE);

  const topY = mercatorY(grid.north);
  const bottomY = mercatorY(grid.south);
  for (let y = 0; y < IMAGE_SIZE; y++) {
    // The map stretches images in Mercator space, so rows are spaced in
    // Mercator y (not in latitude) to line up exactly with the grid points.
    const lat = latitudeFromMercatorY(topY + ((y + 0.5) / IMAGE_SIZE) * (bottomY - topY));
    const row = ((lat - grid.south) / (grid.north - grid.south)) * (grid.size - 1);
    for (let x = 0; x < IMAGE_SIZE; x++) {
      const col = ((x + 0.5) / IMAGE_SIZE) * (grid.size - 1);
      const [r, g, b, a] = colorFor(sample(intensity, grid.size, row, col));
      image.data.set([r, g, b, Math.round(a * 255)], (y * IMAGE_SIZE + x) * 4);
    }
  }
  context.putImageData(image, 0, 0);
  return canvas.toDataURL('image/png');
}

/** Bilinear interpolation between the four grid points around (row, col). */
function sample(values: number[], size: number, row: number, col: number): number {
  const r0 = Math.min(Math.max(Math.floor(row), 0), size - 2);
  const c0 = Math.min(Math.max(Math.floor(col), 0), size - 2);
  const fr = Math.min(Math.max(row - r0, 0), 1);
  const fc = Math.min(Math.max(col - c0, 0), 1);
  const at = (r: number, c: number) => values[r * size + c]; // rows start in the south
  const bottom = at(r0, c0) * (1 - fc) + at(r0, c0 + 1) * fc;
  const top = at(r0 + 1, c0) * (1 - fc) + at(r0 + 1, c0 + 1) * fc;
  return bottom * (1 - fr) + top * fr;
}

function mercatorY(lat: number): number {
  return Math.log(Math.tan(Math.PI / 4 + (lat * Math.PI) / 360));
}

function latitudeFromMercatorY(y: number): number {
  return (Math.atan(Math.exp(y)) * 360) / Math.PI - 90;
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
