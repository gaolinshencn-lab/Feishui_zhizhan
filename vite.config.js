import { defineConfig } from 'vite';
import { viteSingleFile } from 'vite-plugin-singlefile';

// Builds one self-contained HTML file (all JS, CSS, fonts and terrain data inlined),
// so the model opens by double-clicking docs/index.html with no server or network.
export default defineConfig({
  base: './',
  plugins: [viteSingleFile({ removeViteModuleLoader: true })],
  build: {
    target: 'es2020',
    assetsInlineLimit: 100_000_000,
    cssCodeSplit: false,
    chunkSizeWarningLimit: 10_000,
    reportCompressedSize: false,
  },
  server: { host: true, port: 5173 },
});
