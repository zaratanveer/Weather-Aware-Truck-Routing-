import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    // MapLibre + deck.gl are ~2 MB minified (~560 kB gzipped): expected for a WebGL map app.
    chunkSizeWarningLimit: 2100,
  },
});
