import { RISK_LEVELS, type PlannedRoute } from '../api/types';
import { formatDateTime, formatDuration, formatMiles } from '../format';
import { RISK_COLORS, routeColor } from '../risk';

interface RouteCardProps {
  route: PlannedRoute;
  selected: boolean;
  onSelect: (routeId: number) => void;
  onHover: (routeId: number | null) => void;
}

export function RouteCard({ route, selected, onSelect, onHover }: RouteCardProps) {
  const { summary } = route;
  const arrival = route.checkpoints.at(-1)?.eta;

  return (
    <li>
      <button
        type="button"
        className={selected ? 'route-card selected' : 'route-card'}
        aria-pressed={selected}
        onClick={() => onSelect(route.id)}
        onMouseEnter={() => onHover(route.id)}
        onMouseLeave={() => onHover(null)}
        onFocus={() => onHover(route.id)}
        onBlur={() => onHover(null)}
      >
        <div className="route-card-header">
          <span className="route-swatch" style={{ background: routeColor(route.id) }} />
          <span className="route-name">{route.name}</span>
          {route.is_recommended && <span className="badge recommended">Recommended</span>}
          {route.is_detour && <span className="badge detour">Detour</span>}
          {summary.has_no_travel && <span className="badge no-travel">No Travel</span>}
        </div>

        <div className="route-stats">
          <span>{formatMiles(route.distance_miles)}</span>
          <span>{formatDuration(route.duration_seconds)}</span>
          {arrival && <span>Arrive {formatDateTime(arrival)}</span>}
        </div>

        <RiskBar route={route} />

        <dl className="route-risk">
          <div>
            <dt>Severe miles</dt>
            <dd>{summary.miles_by_level.Severe.toFixed(0)}</dd>
          </div>
          <div>
            <dt>High miles</dt>
            <dd>{summary.miles_by_level.High.toFixed(0)}</dd>
          </div>
          <div>
            <dt>Avg risk</dt>
            <dd>{summary.average_risk.toFixed(2)} / 4</dd>
          </div>
          <div>
            <dt>Worst</dt>
            <dd style={{ color: RISK_COLORS[summary.worst_level] }}>{summary.worst_level}</dd>
          </div>
        </dl>
      </button>
    </li>
  );
}

/** A stacked bar: how many of the route's miles are at each risk level. */
function RiskBar({ route }: { route: PlannedRoute }) {
  const total = route.distance_miles || 1;
  const label = RISK_LEVELS.map(
    (level) => `${level}: ${route.summary.miles_by_level[level].toFixed(0)} mi`,
  ).join(', ');

  return (
    <div className="risk-bar" role="img" aria-label={`Miles by risk level. ${label}`} title={label}>
      {RISK_LEVELS.map((level) => {
        const miles = route.summary.miles_by_level[level];
        if (miles <= 0) return null;
        return (
          <span
            key={level}
            style={{ width: `${(miles / total) * 100}%`, background: RISK_COLORS[level] }}
          />
        );
      })}
    </div>
  );
}
