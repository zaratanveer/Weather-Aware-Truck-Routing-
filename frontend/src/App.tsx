import { useCallback, useMemo, useState } from 'react';

import './App.css';
import type { PlanRequest } from './api/types';
import { HeatmapPanel } from './components/HeatmapPanel';
import { RouteList } from './components/RouteList';
import { TripForm } from './components/TripForm';
import { TripMap } from './components/TripMap';
import { useTripPlanner } from './hooks/useTripPlanner';
import { buildHeatmapImages } from './map/heatmapImages';

export default function App() {
  const planner = useTripPlanner();
  const { plan, heatmap } = planner;

  const [pickedRouteId, setPickedRouteId] = useState<number | null>(null);
  const [hoveredRouteId, setHoveredRouteId] = useState<number | null>(null);
  const [heatmapHour, setHeatmapHour] = useState(0);
  const [showHeatmap, setShowHeatmap] = useState(true);

  // Until the driver picks a route, the recommended one is selected.
  const selectedRouteId = pickedRouteId ?? plan?.recommendation.route_index ?? null;

  // Built once per heatmap download; the slider then only picks a frame.
  const heatmapImages = useMemo(() => (heatmap ? buildHeatmapImages(heatmap) : null), [heatmap]);

  const { planTrip } = planner;
  const handleSubmit = useCallback(
    (request: PlanRequest) => {
      setPickedRouteId(null);
      setHoveredRouteId(null);
      setHeatmapHour(0);
      void planTrip(request);
    },
    [planTrip],
  );

  return (
    <div className="app">
      <aside className="sidebar">
        <header className="app-header">
          <h1>Weather-Aware Truck Routing</h1>
          <p>Compare up to 3 routes by weather risk, load weight and travel time.</p>
        </header>

        <TripForm loading={planner.planStatus === 'loading'} onSubmit={handleSubmit} />

        {planner.planStatus === 'idle' && (
          <p className="empty-state">
            Enter an origin, destination, departure time and load. Weather is checked at every
            checkpoint for the time the truck will be there.
          </p>
        )}
        {planner.planStatus === 'loading' && <ResultsSkeleton />}
        {planner.planStatus === 'error' && (
          <div className="error-box" role="alert">
            <strong>Could not plan this trip.</strong>
            <p>{planner.planError}</p>
          </div>
        )}
        {plan && (
          <RouteList
            plan={plan}
            selectedRouteId={selectedRouteId}
            onSelect={setPickedRouteId}
            onHover={setHoveredRouteId}
          />
        )}
      </aside>

      <main className="map-container">
        <TripMap
          plan={plan}
          heatmapImages={heatmapImages}
          heatmapHour={heatmapHour}
          showHeatmap={showHeatmap}
          selectedRouteId={selectedRouteId}
          hoveredRouteId={hoveredRouteId}
          onSelectRoute={setPickedRouteId}
        >
          <HeatmapPanel
            status={planner.heatmapStatus}
            error={planner.heatmapError}
            times={heatmapImages?.times ?? []}
            hour={heatmapHour}
            onHourChange={setHeatmapHour}
            visible={showHeatmap}
            onVisibleChange={setShowHeatmap}
          />
        </TripMap>
      </main>
    </div>
  );
}

function ResultsSkeleton() {
  return (
    <div className="skeleton-list" aria-busy="true" aria-label="Loading routes">
      <p className="skeleton-caption">Finding routes and checking the forecast at every checkpoint…</p>
      {[0, 1, 2].map((key) => (
        <div key={key} className="skeleton-card" />
      ))}
    </div>
  );
}
