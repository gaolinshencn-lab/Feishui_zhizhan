// Renders the documentary's live sand-table footage. Every frame is driven deterministically through
// app.captureFrame(T, 1/fps), grabbed with a CDP screenshot and piped into ffmpeg in chunks of ten
// seconds. Resumable (finished chunks are skipped) and splittable across workers:
//   node capture_doc.mjs doc_timeline.json outDir [segments=A,B] [worker] [workers] [maxChunks]
// Segments run on their own time base; keyed cameras (intro, geography tour) are given relative to it.
import { createRequire } from 'node:module';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { existsSync, readFileSync, renameSync, mkdirSync, rmSync, writeFileSync } from 'node:fs';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

const [timelinePath, outDir, segList = '', worker = '0', workers = '1', maxChunks = '0'] = process.argv.slice(2);
const TL = JSON.parse(readFileSync(timelinePath, 'utf8'));
const FPS = TL.fps;
const CH = 240;
const APP = new URL('../../docs/index.html', import.meta.url).href;
const QUALITY = process.env.QUALITY || 'medium';
const RATIO = Number(process.env.PIXEL_RATIO || 0); // render the 3D view below 1:1, labels stay sharp
const ADAPT = Number(process.env.ADAPT ?? 1);    // 0: draw every frame
mkdirSync(outDir, { recursive: true });

const wanted = segList ? segList.split(',') : null;
const chunks = [];
for (const seg of TL.segments) {
  if (seg.camera === 'still' || (wanted && !wanted.includes(seg.name))) continue;
  for (let c = 0; c * CH < seg.frames; c++) chunks.push({ seg, c, from: c * CH, to: Math.min(seg.frames, (c + 1) * CH) });
}
let mine = chunks.filter((ch, i) => i % Number(workers) === Number(worker));
mine = mine.filter((ch) => !existsSync(`${outDir}/${ch.seg.name}_${String(ch.c).padStart(3, '0')}.mp4`));
if (Number(maxChunks)) mine = mine.slice(0, Number(maxChunks));
console.log(`worker ${worker}/${workers}: ${mine.length} chunks to render`);

const smooth = (x) => x * x * (3 - 2 * x);
function keyed(keys, t) {
  // keys: [t, [lon, lat], dist, yaw, pitch], t relative to the segment
  if (t <= keys[0][0]) return keys[0];
  for (let i = 1; i < keys.length; i++) {
    const a = keys[i - 1];
    const b = keys[i];
    if (t <= b[0]) {
      const u = smooth((t - a[0]) / Math.max(1e-6, b[0] - a[0]));
      return [t, [a[1][0] + (b[1][0] - a[1][0]) * u, a[1][1] + (b[1][1] - a[1][1]) * u],
        Math.exp(Math.log(a[2]) + (Math.log(b[2]) - Math.log(a[2])) * u), a[3] + (b[3] - a[3]) * u, a[4] + (b[4] - a[4]) * u];
    }
  }
  return keys[keys.length - 1];
}

const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--enable-webgl'] });
let page = null;
let cdp = null;
let at = null; // { seg, frame } the page's simulation has reached

const VIDEO_CSS = readFileSync(new URL('./video.css', import.meta.url), 'utf8');

async function freshPage() {
  if (page) await page.close();
  page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  page.on('pageerror', (e) => console.log('pageerror', e.message));
  await page.goto(APP, { waitUntil: 'load', timeout: 180000 });
  await page.waitForFunction(() => window.__feishui && window.__feishui.ready, null, { timeout: 300000 });
  await page.addStyleTag({ content: VIDEO_CSS });
  cdp = await page.context().newCDPSession(page);
  at = null;
}

async function step(seg, f, draw) {
  const cam = seg.keys ? keyed(seg.keys, f / FPS) : null;
  return page.evaluate(
    ([T, cam, dt, draw]) => {
      const a = window.__feishui;
      if (cam) {
        a.rig.setAuto(false);
        a.rig._programmatic = true;
        a.rig.apply(a.rig.poseFrom({ target: cam[1], dist: cam[2], yaw: cam[3], pitch: cam[4] }));
        a.rig._programmatic = false;
      }
      a.captureFrame(T, dt, { draw });
      const p = a.rig.currentPose();
      return { x: p.target.x, y: p.target.y, z: p.target.z, dist: p.dist, yaw: p.yaw, pitch: p.pitch, fov: a.stage.camera.fov };
    },
    [seg.T[f], cam, 1 / FPS, draw],
  );
}

// How far (in pixels, roughly) the picture moves between two camera poses.
function motionPx(a, b) {
  const pxr = 1080 / (2 * Math.tan((a.fov * Math.PI) / 360));
  const d = Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z) / a.dist;
  const ang = (Math.abs(a.yaw - b.yaw) + Math.abs(a.pitch - b.pitch)) * (Math.PI / 180);
  return pxr * (d + ang) + 1100 * Math.abs(a.dist - b.dist) / a.dist;
}

async function seek(seg, frame) {
  if (at && at.seg === seg && at.frame <= frame) {
    for (let f = at.frame; f < frame; f++) await step(seg, f, false);
  } else {
    await freshPage();
    await page.evaluate(([T, quality, ratio]) => {
      const a = window.__feishui;
      a.userTouched = true;
      a.pause();
      a.capturing = true;
      a.setQuality(quality);
      a.stage.bloom.enabled = false;
      a.stage.vignette.uniforms.uGrain.value = 0; // film grain only costs bits (and Bilibili re-encodes it to mush)
      if (ratio) {
        a.stage.renderer.setPixelRatio(ratio);
        a.stage.composer.setPixelRatio?.(ratio);
      }
      a.setTime(T, { snap: true });
    }, [seg.T[0], QUALITY, RATIO]);
    for (let f = 0; f < frame; f++) await step(seg, f, false);
  }
  at = { seg, frame };
}

const TEST = Number(process.env.TEST_FRAMES || 0);
// Several workers can share one list: a chunk is claimed with a lock file holding the worker's pid
// (a lock left by a process that no longer runs is taken over).
function claim(name) {
  if (existsSync(`${outDir}/${name}.mp4`)) return false;
  const lock = `${outDir}/.${name}.lock`;
  try {
    writeFileSync(lock, String(process.pid), { flag: 'wx' });
    return true;
  } catch {
    const pid = Number(readFileSync(lock, 'utf8'));
    try { process.kill(pid, 0); return false; } catch { writeFileSync(lock, String(process.pid)); return true; }
  }
}
for (const ch of mine) {
  if (TEST) ch.to = Math.min(ch.to, ch.from + TEST);
  const name = `${ch.seg.name}_${String(ch.c).padStart(3, '0')}`;
  if (!TEST && !claim(name)) continue;
  const t00 = Date.now();
  await seek(ch.seg, ch.from);
  const t0 = Date.now();
  const tmp = `${outDir}/.${name}.${process.pid}.mp4`;
  rmSync(tmp, { force: true });
  const dir = `${outDir}/.${name}_frames_${process.pid}`;
  rmSync(dir, { recursive: true, force: true });
  mkdirSync(dir, { recursive: true });
  const durs = ch.seg.durations || null;
  let tStep = 0, tShot = 0;
  const rendered = [];
  let last = null;
  for (let f = ch.from; f < ch.to; f++) {
    const a0 = Date.now();
    const pose = await step(ch.seg, f, false);
    // sand-table pace at this frame (node-seconds per second of film): fast sand table, render every frame
    const dT = Math.abs((ch.seg.T[Math.min(f + 1, ch.seg.frames - 1)] ?? 0) - (ch.seg.T[f] ?? 0));
    const pace = dT * ((TL.node_durations || [])[Math.min(12, Math.floor(ch.seg.T[f]))] || 15) * FPS;
    const maxGap = pace >= 0.8 ? 1 : pace >= 0.4 ? 2 : 4;
    const must = f === ch.from || f === ch.to - 1 || !last || f - last.f >= maxGap || motionPx(last.pose, pose) > 1.2 || ADAPT === 0;
    tStep += Date.now() - a0;
    if (!must) continue;
    const a1 = Date.now();
    await page.evaluate(() => { const a = window.__feishui; a.stage.render(a.elapsed); });
    const { data } = await cdp.send('Page.captureScreenshot', { format: 'jpeg', quality: 94 });
    writeFileSync(`${dir}/${String(f).padStart(6, '0')}.jpg`, Buffer.from(data, 'base64'));
    tShot += Date.now() - a1;
    rendered.push(f);
    last = { f, pose };
  }
  // concat list with each rendered frame held until the next one; the framerate filter blends between
  let list = 'ffconcat version 1.0\n';
  rendered.forEach((f, k) => {
    const next = k + 1 < rendered.length ? rendered[k + 1] : ch.to;
    list += `file '${String(f).padStart(6, '0')}.jpg'\nduration ${((next - f) / FPS).toFixed(6)}\n`;
  });
  list += `file '${String(rendered[rendered.length - 1]).padStart(6, '0')}.jpg'\n`;
  writeFileSync(`${dir}/list.txt`, list);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', `${dir}/list.txt`,
    '-vf', `framerate=fps=${FPS}:interp_start=1:interp_end=254:scene=100,format=yuv420p`, '-frames:v', String(ch.to - ch.from),
    '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '14', '-r', String(FPS), tmp], { stdio: ['ignore', 'inherit', 'inherit'] });
  const [code] = await once(ff, 'exit');
  rmSync(dir, { recursive: true, force: true });
  if (code !== 0) throw new Error(`ffmpeg failed on ${name}`);
  if (TEST) {
    renameSync(tmp, `${outDir}/test_${name}.mp4`);
  } else {
    renameSync(tmp, `${outDir}/${name}.mp4`);
    writeFileSync(`${outDir}/${name}.json`, JSON.stringify({ frames: ch.to - ch.from, T0: ch.seg.T[ch.from], T1: ch.seg.T[ch.to - 1] }));
    rmSync(`${outDir}/.${name}.lock`, { force: true });
  }
  at = { seg: ch.seg, frame: ch.to };
  console.log(`  ${rendered.length}/${ch.to - ch.from} frames drawn; step ${(tStep / (ch.to - ch.from)).toFixed(0)} ms/frame, draw ${(tShot / Math.max(1, rendered.length)).toFixed(0)} ms/drawn frame`);
  console.log(`${name} frames ${ch.from}-${ch.to} in ${((Date.now() - t00) / 1000).toFixed(0)}s (seek ${((t0 - t00) / 1000).toFixed(0)}s, ${((Date.now() - t0) / 1000 / (ch.to - ch.from)).toFixed(2)} s/frame)`);
}
await browser.close();
console.log('worker done');
