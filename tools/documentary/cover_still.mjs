// Renders a still of one sand-table moment for the cover, with the camera moved off the scripted pose
// so the action sits where the cover's title leaves room.
//   node cover_still.mjs T dpr '[{"name":"a","fx":0.12,"fy":0.15,"dist":0.85,"pitch":-6,"yaw":0}]' outDir
// fx / fy: how far the picture moves right / down, as a fraction of the frame; dist: scale of the scripted
// distance; pitch / yaw: degrees added to the scripted angles.
import { createRequire } from 'node:module';
import { readFileSync, mkdirSync } from 'node:fs';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

const [T, dpr, specs, outDir] = process.argv.slice(2);
const APP = new URL('../../docs/index.html', import.meta.url).href;
mkdirSync(outDir, { recursive: true });
const CSS = readFileSync(new URL('./video.css', import.meta.url), 'utf8');

const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--enable-webgl'] });
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: Number(dpr) });
page.on('pageerror', (e) => console.log('pageerror', e.message));
await page.goto(APP, { waitUntil: 'load', timeout: 180000 });
await page.waitForFunction(() => window.__feishui && window.__feishui.ready, null, { timeout: 300000 });
await page.addStyleTag({ content: CSS });
await page.evaluate((T) => {
  const a = window.__feishui;
  a.userTouched = true;
  a.pause();
  a.capturing = true;
  a.setQuality('high');
  a.stage.vignette.uniforms.uGrain.value = 0;
  a.setTime(T, { snap: true });
  for (let i = 0; i < 48; i++) a.captureFrame(T, 1 / 24, { draw: false });
}, Number(T));
for (const s of JSON.parse(specs)) {
  const t0 = Date.now();
  await page.evaluate(([T, s]) => {
    const a = window.__feishui;
    a.setTime(T, { snap: true });
    const p = a.rig.currentPose();
    const cam = a.stage.camera;
    const dist = p.dist * (s.dist ?? 1);
    const pitch = p.pitch + (s.pitch ?? 0);
    const yaw = p.yaw + (s.yaw ?? 0);
    const th = Math.tan((cam.fov * Math.PI) / 360);
    const y = (yaw * Math.PI) / 180;
    const right = [Math.cos(y), Math.sin(y)];
    const look = [Math.sin(y), -Math.cos(y)];
    const sx = -(s.fx ?? 0) * 2 * dist * th * cam.aspect;
    const sy = ((s.fy ?? 0) * 2 * dist * th) / Math.sin((pitch * Math.PI) / 180);
    const target = p.target.clone();
    target.x += right[0] * sx + look[0] * sy;
    target.z += right[1] * sx + look[1] * sy;
    a.rig.setAuto(false);
    a.rig._programmatic = true;
    a.rig.apply({ target, dist, yaw, pitch });
    a.rig._programmatic = false;
    for (let i = 0; i < 3; i++) a.captureFrame(T, 1 / 24, { draw: i === 2 });
  }, [Number(T), s]);
  await page.screenshot({ path: `${outDir}/${s.name}.png`, type: 'png' });
  console.log(s.name, `${((Date.now() - t0) / 1000).toFixed(0)}s`);
}
await browser.close();
