import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    // MapLibre is ~1.3 MB minified (~380 kB gzipped): expected for a WebGL map app.
    chunkSizeWarningLimit: 1400,
  },
});
