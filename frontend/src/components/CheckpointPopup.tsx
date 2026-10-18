import { Popup } from 'react-map-gl/maplibre';

import { formatDateTime } from '../format';
import type { CheckpointPoint } from '../map/layers';
import { RISK_COLORS, describeDrivers } from '../risk';

interface CheckpointPopupProps {
  point: CheckpointPoint;
  onClose: () => void;
}

export function CheckpointPopup({ point, onClose }: CheckpointPopupProps) {
  const { checkpoint, routeName } = point;

  return (
    <Popup
      longitude={checkpoint.lon}
      latitude={checkpoint.lat}
      offset={12}
      closeOnClick={false}
      onClose={onClose}
      maxWidth="280px"
    >
      <div className="checkpoint-popup">
        <p className="popup-title">
          {routeName} · mile {checkpoint.mile.toFixed(0)}
        </p>
        <span className="risk-badge" style={{ background: RISK_COLORS[checkpoint.level] }}>
          {checkpoint.level}
        </span>
        <p className="popup-drivers">{describeDrivers(checkpoint.drivers)}</p>
        <dl className="popup-grid">
          <dt>ETA</dt>
          <dd>{formatDateTime(checkpoint.eta)}</dd>
          <dt>Forecast for</dt>
          <dd>{formatDateTime(checkpoint.forecast_hour)}</dd>
          <dt>Wind</dt>
          <dd>{checkpoint.wind_mph.toFixed(1)} mph</dd>
          <dt>Rain</dt>
          <dd>{checkpoint.rain_in_per_hr.toFixed(2)} in/hr</dd>
          <dt>Snow</dt>
          <dd>{checkpoint.snow_in_per_hr.toFixed(2)} in/hr</dd>
        </dl>
      </div>
    </Popup>
  );
}
