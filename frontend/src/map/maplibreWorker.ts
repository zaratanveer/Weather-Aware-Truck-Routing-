import { setWorkerUrl } from 'maplibre-gl';
// "?worker&url" asks Vite to bundle MapLibre's web worker (with everything it
// imports) as its own file and give us that file's URL.
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url';

/**
 * MapLibre decodes map tiles in a background web worker. It normally finds the
 * worker file next to its own code, but bundlers move files around, so we
 * tell it explicitly where Vite put the worker.
 */
setWorkerUrl(workerUrl);
