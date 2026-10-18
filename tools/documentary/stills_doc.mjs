// Renders the high-resolution stills (3840x2160) the documentary pans across: one per camera shot,
// on the strategic table, at the start of the campaign (background) or at its end (aftermath).
//   node stills_doc.mjs doc_timeline.json outDir
import { createRequire } from 'node:module';
import { existsSync, readFileSync, mkdirSync, writeFileSync } from 'node:fs';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

const [timelinePath, outDir] = process.argv.slice(2);
const TL = JSON.parse(readFileSync(timelinePath, 'utf8'));
const SHOTS = JSON.parse(readFileSync(new URL('./shots.json', import.meta.url), 'utf8'));
const APP = new URL('../../docs/index.html', import.meta.url).href;
mkdirSync(outDir, { recursive: true });
const CSS = readFileSync(new URL('./video.css', import.meta.url), 'utf8');

// which stills are needed: (shot, phase) where phase is the campaign state shown
const bgEnd = TL.segments.find((s) => s.name === 'bg').end;
const need = new Map();
for (const st of TL.stills) {
  const phase = st.start < bgEnd ? 'start' : 'end';
  need.set(`${st.shot}@${phase}`, { shot: st.shot, phase });
}
const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--enable-webgl'] });
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 2 });
page.on('pageerror', (e) => console.log('pageerror', e.message));
await page.goto(APP, { waitUntil: 'load', timeout: 180000 });
await page.waitForFunction(() => window.__feishui && window.__feishui.ready, null, { timeout: 300000 });
await page.addStyleTag({ content: CSS });
for (const { shot, phase } of need.values()) {
  const out = `${outDir}/${shot}@${phase}.png`;
  if (existsSync(out)) continue;
  const [, target, dist, yaw, pitch] = SHOTS[shot];
  const T = phase === 'start' ? 0.0005 : 13 - 1e-4;
  const t0 = Date.now();
  await page.evaluate(([T, cam]) => {
    const a = window.__feishui;
    a.userTouched = true;
    a.pause();
    a.capturing = true;
    a.setQuality('high');
    a.setTime(T, { snap: true });
    // let lighting, labels and effects settle at this moment, then place the camera
    for (let i = 0; i < 48; i++) a.captureFrame(T, 1 / 24, { draw: false });
    a.rig.setAuto(false);
    a.rig._programmatic = true;
    a.rig.apply(a.rig.poseFrom(cam));
    a.rig._programmatic = false;
    for (let i = 0; i < 3; i++) a.captureFrame(T, 1 / 24, { draw: i === 2 });
  }, [T, { target, dist, yaw, pitch }]);
  await page.screenshot({ path: out, type: 'png' });
  console.log(out, `${((Date.now() - t0) / 1000).toFixed(0)}s`);
}
writeFileSync(`${outDir}/done.json`, JSON.stringify([...need.keys()]));
await browser.close();
