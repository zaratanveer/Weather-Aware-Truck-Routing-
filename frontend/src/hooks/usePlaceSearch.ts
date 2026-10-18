import { useEffect, useState } from 'react';

import { api } from '../api/client';
import type { Place } from '../api/types';
import { useDebouncedValue } from './useDebouncedValue';

const MIN_QUERY_LENGTH = 2;
const DEBOUNCE_MS = 300;

interface PlaceSearch {
  results: Place[];
  loading: boolean;
  error: string | null;
}

interface SearchResponse {
  query: string; // which query these results answer
  results: Place[];
  error: string | null;
}

const NO_SEARCH: PlaceSearch = { results: [], loading: false, error: null };

/** Autocomplete suggestions for `query`, fetched 300 ms after typing stops. */
export function usePlaceSearch(query: string, enabled: boolean): PlaceSearch {
  const debouncedQuery = useDebouncedValue(query.trim(), DEBOUNCE_MS);
  const active = enabled && debouncedQuery.length >= MIN_QUERY_LENGTH;
  const [response, setResponse] = useState<SearchResponse>({ query: '', results: [], error: null });

  useEffect(() => {
    if (!active) return;

    // Cancel the previous request so a slow old answer can't overwrite a newer one.
    const controller = new AbortController();
    api
      .searchPlaces(debouncedQuery, controller.signal)
      .then((results) => setResponse({ query: debouncedQuery, results, error: null }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        const message = error instanceof Error ? error.message : 'Place search failed.';
        setResponse({ query: debouncedQuery, results: [], error: message });
      });

    return () => controller.abort();
  }, [active, debouncedQuery]);

  if (!active) return NO_SEARCH;

  // Loading = we don't have the answer for the current query yet. Meanwhile the
  // previous suggestions stay visible, so the list doesn't flicker while typing.
  const isCurrent = response.query === debouncedQuery;
  return { results: response.results, loading: !isCurrent, error: isCurrent ? response.error : null };
}
