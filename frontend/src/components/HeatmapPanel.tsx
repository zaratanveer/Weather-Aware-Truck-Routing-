import { formatDateTime } from '../format';
import type { TripPlannerState } from '../hooks/useTripPlanner';
import { RiskLegend } from './RiskLegend';

const MAX_HOUR = 48;
const TICKS = [0, 12, 24, 36, 48];

interface HeatmapPanelProps {
  status: TripPlannerState['heatmapStatus'];
  error: string | null;
  times: string[];
  hour: number;
  onHourChange: (hour: number) => void;
  visible: boolean;
  onVisibleChange: (visible: boolean) => void;
}

/** The 0–48 h forecast slider and risk legend, floating over the map. */
export function HeatmapPanel({
  status,
  error,
  times,
  hour,
  onHourChange,
  visible,
  onVisibleChange,
}: HeatmapPanelProps) {
  const ready = status === 'success' && times.length > 0;

  return (
    <div className="map-panel heatmap-panel">
      <div className="heatmap-header">
        <label className="toggle">
          <input
            type="checkbox"
            checked={visible}
            disabled={!ready}
            onChange={(event) => onVisibleChange(event.target.checked)}
          />
          Weather heatmap
        </label>
        <span className="heatmap-time" aria-live="polite">
          {status === 'idle' && 'Plan a trip to see the forecast'}
          {status === 'loading' && 'Loading 48-hour forecast…'}
          {status === 'error' && <span className="error-text">{error}</span>}
          {ready && (
            <>
              <strong>+{hour} h</strong> · {formatDateTime(times[hour])}
            </>
          )}
        </span>
      </div>

      <input
        className="hour-slider"
        type="range"
        min={0}
        max={MAX_HOUR}
        step={1}
        value={hour}
        disabled={!ready}
        aria-label="Forecast hour after departure"
        aria-valuetext={ready ? `${hour} hours after departure, ${formatDateTime(times[hour])}` : undefined}
        onChange={(event) => onHourChange(Number(event.target.value))}
      />
      <div className="slider-ticks" aria-hidden="true">
        {TICKS.map((tick) => (
          <span key={tick}>{tick === 0 ? 'Departure' : `+${tick} h`}</span>
        ))}
      </div>

      <RiskLegend />
    </div>
  );
}
