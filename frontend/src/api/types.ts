// Shapes of the JSON exchanged with the Django API (see backend/planner/serializers.py).

export const RISK_LEVELS = ['Low', 'Moderate', 'High', 'Severe', 'No Travel'] as const;
export type RiskLevel = (typeof RISK_LEVELS)[number];

export const CHECKPOINT_INTERVALS = [10, 25, 50] as const;
export type CheckpointInterval = (typeof CHECKPOINT_INTERVALS)[number];

/** [longitude, latitude], the order GeoJSON and map libraries use. */
export type LngLat = [number, number];

export interface Coordinates {
  lat: number;
  lon: number;
}

export interface Place extends Coordinates {
  label: string;
}

export interface Checkpoint extends Coordinates {
  index: number;
  mile: number;
  eta: string; // ISO 8601
  forecast_hour: string; // ISO 8601, the forecast hour used for this ETA
  wind_mph: number;
  rain_in_per_hr: number;
  snow_in_per_hr: number;
  level: RiskLevel;
  drivers: Array<'wind' | 'rain' | 'snow' | 'load'>;
}

export interface RouteSummary {
  miles_by_level: Record<RiskLevel, number>;
  average_risk: number; // 0 (Low) .. 4 (No Travel), weighted by miles
  worst_level: RiskLevel;
  has_no_travel: boolean;
}

export interface PlannedRoute {
  id: number;
  name: string;
  is_recommended: boolean;
  is_detour: boolean;
  distance_miles: number;
  duration_seconds: number;
  geometry: LngLat[];
  summary: RouteSummary;
  checkpoints: Checkpoint[];
}

export interface TripPlan {
  routes: PlannedRoute[];
  recommendation: { route_index: number; reason: string };
  notices: string[];
}

export interface PlanRequest {
  origin: Coordinates;
  destination: Coordinates;
  departure: string; // ISO 8601 with timezone
  load_lb: number;
  interval_miles: CheckpointInterval;
}

export interface HeatmapFrame {
  time: string; // ISO 8601
  intensity: number[]; // 0..1 per grid point, same order as Heatmap.points
}

export interface Heatmap {
  points: LngLat[]; // row by row from the south-west corner
  frames: HeatmapFrame[]; // hour 0..48 after departure
}

export interface Bounds {
  south: number;
  west: number;
  north: number;
  east: number;
}

export interface HeatmapRequest extends Bounds {
  start: string;
  load_lb: number;
}
