import { memo } from 'react';

import type { TripPlan } from '../api/types';
import { RouteCard } from './RouteCard';

interface RouteListProps {
  plan: TripPlan;
  selectedRouteId: number | null;
  onSelect: (routeId: number) => void;
  onHover: (routeId: number | null) => void;
}

/**
 * The route comparison panel. memo() skips re-rendering while only the
 * heatmap slider moves, because none of these props change then.
 */
export const RouteList = memo(function RouteList({ plan, selectedRouteId, onSelect, onHover }: RouteListProps) {
  const recommended = plan.routes[plan.recommendation.route_index];

  return (
    <section className="results" aria-label="Route options">
      <div className="recommendation-banner">
        <p className="eyebrow">Recommended</p>
        <p className="recommendation-title">{recommended.name}</p>
        <p>{plan.recommendation.reason}</p>
      </div>

      {plan.notices.length > 0 && (
        <ul className="notices">
          {plan.notices.map((notice) => (
            <li key={notice}>{notice}</li>
          ))}
        </ul>
      )}

      <ul className="route-list">
        {plan.routes.map((route) => (
          <RouteCard
            key={route.id}
            route={route}
            selected={route.id === selectedRouteId}
            onSelect={onSelect}
            onHover={onHover}
          />
        ))}
      </ul>
    </section>
  );
});
