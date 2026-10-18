import { RISK_LEVELS } from '../api/types';
import { RISK_COLORS } from '../risk';

export function RiskLegend() {
  return (
    <ul className="risk-legend" aria-label="Risk levels">
      {RISK_LEVELS.map((level) => (
        <li key={level}>
          <span className="legend-swatch" style={{ background: RISK_COLORS[level] }} />
          {level}
        </li>
      ))}
    </ul>
  );
}
