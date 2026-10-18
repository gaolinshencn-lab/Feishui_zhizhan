// Renders the documentary's battlefield sound offline with the app's own engine, one live segment at a
// time, driven by the documentary timeline (the sand table's T at 30 Hz, null where stills are shown).
// The buffer stays in the page for chunked export.
import { Sound } from '/src/audio/Sound.js';
import { levelsAt, cuesBetween } from '/src/audio/score.js';
import { EPISODES } from '/src/data/episodes.js';

export async function render(segName) {
  const tl = await (await fetch('/video/doc_timeline.json')).json();
  const seg = tl.segments.find((s) => s.name === segName);
  const sr = 48000;
  const total = seg.end - seg.start;
  const ctx = new OfflineAudioContext(2, Math.ceil(sr * (total + 0.5)), sr);
  const s = new Sound();
  s.ensure(ctx);
  s.setMusic(false);
  await s.setEnabled(true);
  await s.load();
  const step = 1 / 30;
  const keyed = seg.camera === 'keyed';
  let prevT = null;
  let prevIdx = -1;
  for (let k = 1; k * step < total - 0.02; k++) {
    const local = k * step;
    ctx.suspend(local).then(() => {
      const t = seg.start + local;
      const row = tl.sound[Math.min(tl.sound.length - 1, Math.round(t * 30))];
      const T = row[1] ?? (keyed ? seg.T[0] : null);
      if (T === null) {
        s.update(step, levelsAt(0, false), 0);
        ctx.resume();
        return;
      }
      const playing = !keyed || segName === 'intro'; // the intro hears the armies facing across the Fei
      if (playing) {
        const idx = Math.min(12, Math.floor(T));
        if (idx !== prevIdx) {
          if (prevIdx !== -1 || local > 0.5) s.chapter();
          prevIdx = idx;
        }
        if (prevT !== null) for (const c of cuesBetween(prevT, T)) s.cue(c);
        prevT = T;
      }
      let near;
      if (playing) {
        const ep = EPISODES[Math.min(12, Math.floor(T))];
        const p = T - Math.floor(T);
        const d0 = ep.camera.dist;
        const d1 = (ep.camera2 || ep.camera).dist;
        near = Math.max(0, Math.min(1, Math.log(120 / (d0 + (d1 - d0) * p * p * (3 - 2 * p))) / Math.log(10)));
        if (ep.map === 'strategic') near *= 0.6;
      } else near = segName === 'intro' ? Math.min(1, local / 40) * 0.9 : 0.55;
      s.update(step, levelsAt(T, playing), near);
      ctx.resume();
    });
  }
  window.__out = await ctx.startRendering();
  return { sr, length: window.__out.length, channels: window.__out.numberOfChannels, start: seg.start };
}

/** One slice of the rendered buffer, interleaved float32, base64. */
export function slice(offset, n) {
  const b = window.__out;
  const end = Math.min(b.length, offset + n);
  const out = new Float32Array((end - offset) * b.numberOfChannels);
  for (let c = 0; c < b.numberOfChannels; c++) {
    const d = b.getChannelData(c);
    for (let i = offset; i < end; i++) out[(i - offset) * b.numberOfChannels + c] = d[i];
  }
  const u8 = new Uint8Array(out.buffer);
  let s = '';
  for (let i = 0; i < u8.length; i += 0x8000) s += String.fromCharCode.apply(null, u8.subarray(i, i + 0x8000));
  return btoa(s);
}
