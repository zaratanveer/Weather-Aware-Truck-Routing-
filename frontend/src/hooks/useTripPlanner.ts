import { useCallback, useEffect, useRef, useState } from 'react';

import { api } from '../api/client';
import type { Heatmap, PlanRequest, TripPlan } from '../api/types';
import { routesBounds } from '../map/bounds';

type Status = 'idle' | 'loading' | 'success' | 'error';

export interface TripPlannerState {
  planStatus: Status;
  plan: TripPlan | null;
  planError: string | null;
  heatmapStatus: Status;
  heatmap: Heatmap | null;
  heatmapError: string | null;
}

const INITIAL_STATE: TripPlannerState = {
  planStatus: 'idle',
  plan: null,
  planError: null,
  heatmapStatus: 'idle',
  heatmap: null,
  heatmapError: null,
};

function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : 'Something went wrong.';
}

/**
 * Plans a trip, then loads the corridor heatmap for it.
 *
 * Routes appear as soon as the plan arrives; the heatmap follows in a second
 * request so the driver isn't kept waiting for it.
 */
export function useTripPlanner() {
  const [state, setState] = useState<TripPlannerState>(INITIAL_STATE);
  const controllerRef = useRef<AbortController | null>(null);

  useEffect(() => () => controllerRef.current?.abort(), []);

  const planTrip = useCallback(async (request: PlanRequest) => {
    // A new search cancels the previous one.
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;

    setState({ ...INITIAL_STATE, planStatus: 'loading' });

    let plan: TripPlan;
    try {
      plan = await api.planTrip(request, controller.signal);
    } catch (error) {
      if (controller.signal.aborted) return;
      setState({ ...INITIAL_STATE, planStatus: 'error', planError: messageOf(error) });
      return;
    }
    setState((previous) => ({ ...previous, planStatus: 'success', plan, heatmapStatus: 'loading' }));

    try {
      const heatmap = await api.fetchHeatmap(
        { ...routesBounds(plan.routes), start: request.departure, load_lb: request.load_lb },
        controller.signal,
      );
      setState((previous) => ({ ...previous, heatmapStatus: 'success', heatmap }));
    } catch (error) {
      if (controller.signal.aborted) return;
      setState((previous) => ({ ...previous, heatmapStatus: 'error', heatmapError: messageOf(error) }));
    }
  }, []);

  return { ...state, planTrip };
}
