// Headless screenshots of the model for visual checks and README images.
// Usage: node tools/snapshot.mjs <url> <out-dir> [T1,T2,...] [width]x[height]
//   e.g. node tools/snapshot.mjs http://localhost:5173 shots 0,3.5,9.6 1600x900
import { createRequire } from 'node:module';
import { mkdirSync } from 'node:fs';
import { resolve } from 'node:path';

const require = createRequire(import.meta.url);
let chromium;
try {
  ({ chromium } = require('playwright'));
} catch {
  ({ chromium } = require('/opt/node22/lib/node_modules/playwright'));
}

const [url = 'http://localhost:5173', outDir = 'shots', times = '0', size = '1600x900', extra = ''] = process.argv.slice(2);
const [width, height] = size.split('x').map(Number);
mkdirSync(outDir, { recursive: true });

const browser = await chromium.launch({
  args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--enable-webgl'],
});
const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1 });
const logs = [];
page.on('console', (m) => logs.push(`[${m.type()}] ${m.text()}`));
page.on('pageerror', (e) => logs.push(`[pageerror] ${e.message}`));
await page.goto(url, { waitUntil: 'load', timeout: 120000 });
await page.waitForFunction(() => window.__feishui && window.__feishui.ready, null, { timeout: 180000 }).catch(() => {});
for (const t of times.split(',')) {
  const T = Number(t);
  await page.evaluate(
    ([T, extra]) => {
      const app = window.__feishui;
      app.userTouched = true;
      app.pause?.();
      app.setTime(T, { snap: true });
      const ld = document.querySelector('#loader');
      if (ld) ld.style.display = 'none';
      if (extra) {
        try {
          new Function('app', extra)(app);
        } catch (e) {
          console.error(e);
        }
      }
    },
    [T, extra]
  );
  await page.waitForTimeout(3500);
  const file = resolve(outDir, `t${t.replace('.', '_')}.png`);
  await page.screenshot({ path: file });
  console.log('saved', file);
}
console.log(logs.slice(0, 60).join('\n'));
await browser.close();
