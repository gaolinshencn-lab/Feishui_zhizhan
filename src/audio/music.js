// 《前秦风雨》: an original theme played under the battlefield sounds. A guqin, plucked with the slow
// vibrato of 吟 and touched for harmonics; a xun (clay vessel flute) carrying the melody; a low string
// drone on A and E; and the war drums in the third section. A minor pentatonic (羽调), 60 bpm, sixteen
// bars that loop. Like everything else it is synthesised and sequenced in the browser.

import { render, noise, normalize, filter, rng } from './bank.js';

const RATE = 32000;
const BEAT = 1; // seconds, at 60 bpm
const LOOP = 16 * 4 * BEAT;

const HZ = { A2: 110, C3: 130.81, D3: 146.83, E3: 164.81, G3: 196, A3: 220, C4: 261.63, D4: 293.66, E4: 329.63, G4: 392, A4: 440, C5: 523.25, D5: 587.33, E5: 659.26, A5: 880 };
const QIN_BASES = ['A2', 'D3', 'G3', 'C4', 'E4']; // other notes are these, re-pitched by a tone or two
const XUN_NOTES = ['A3', 'D4', 'E4', 'G4', 'A4', 'C5', 'D5'];

// The score: [bar, beat, note, velocity] for the guqin and its harmonics, [bar, beat, note, beats,
// velocity] for the xun, [bar, beat, drum, velocity] for the drums. Bars count from 1.
const QIN = [
  // 引: the open string under the harmonics
  [1, 0, 'A2', 0.9],
  // 一: the guqin states the theme over its own bass
  [3, 0, 'E4', 0.8], [3, 0, 'A2', 0.7], [3, 2, 'D4', 0.65], [3, 2, 'E3', 0.5], [3, 3, 'C4', 0.65],
  [4, 0, 'A3', 0.8], [4, 0, 'A2', 0.6], [4, 2, 'E3', 0.45], [4, 3, 'G3', 0.6],
  [5, 0, 'A3', 0.75], [5, 0, 'C3', 0.6], [5, 2, 'C4', 0.65], [5, 2, 'G3', 0.45], [5, 3, 'D4', 0.65],
  [6, 0, 'E4', 0.85], [6, 0, 'A2', 0.7], [6, 2, 'E3', 0.5],
  // 二: the xun takes the theme; the guqin keeps the bass
  [7, 0, 'A2', 0.65], [7, 2, 'E3', 0.45], [8, 0, 'D3', 0.6], [8, 2, 'A3', 0.45],
  [9, 0, 'C3', 0.6], [9, 2, 'G3', 0.45], [10, 0, 'A2', 0.65], [10, 2, 'E3', 0.45], [10, 3, 'A3', 0.4],
  // 三: storm. Broken chords under the climbing xun
  [11, 0, 'A2', 0.6], [11, 1, 'E3', 0.4], [11, 2, 'A3', 0.5], [11, 3, 'E3', 0.4],
  [12, 0, 'D3', 0.6], [12, 1, 'A3', 0.4], [12, 2, 'D4', 0.5], [12, 3, 'A3', 0.4],
  [13, 0, 'C3', 0.6], [13, 1, 'G3', 0.4], [13, 2, 'C4', 0.5], [13, 3, 'G3', 0.4],
  [14, 0, 'E3', 0.6], [14, 1, 'G3', 0.4], [14, 2, 'A3', 0.5], [14, 3, 'E4', 0.45],
  // 尾
  [15, 0, 'A2', 0.75], [15, 2, 'E3', 0.5], [16, 0, 'A2', 0.6],
];
const HARMONICS = [[1, 0, 'A4', 0.7], [1, 2.5, 'E5', 0.5], [2, 0, 'A5', 0.45], [2, 2, 'E5', 0.5], [16, 2, 'A4', 0.5], [16, 3, 'E5', 0.45]];
const XUN = [
  [7, 0, 'A4', 2, 0.8], [7, 2, 'G4', 1, 0.7], [7, 3, 'E4', 1, 0.7], [8, 0, 'D4', 3, 0.75], [8, 3, 'E4', 1, 0.65],
  [9, 0, 'G4', 2, 0.8], [9, 2, 'E4', 1, 0.7], [9, 3, 'D4', 1, 0.65], [10, 0, 'E4', 4, 0.8],
  [11, 0, 'C5', 2, 0.85], [11, 2, 'A4', 1, 0.75], [11, 3, 'C5', 1, 0.8], [12, 0, 'D5', 3, 0.9], [12, 3, 'C5', 1, 0.75],
  [13, 0, 'A4', 2, 0.8], [13, 2, 'G4', 1, 0.7], [13, 3, 'E4', 1, 0.7], [14, 0, 'G4', 2, 0.75], [14, 2, 'A4', 2, 0.8],
  [15, 0, 'E4', 2, 0.7], [15, 2, 'D4', 1, 0.65], [15, 3, 'E4', 1, 0.65], [16, 0, 'A3', 3.5, 0.7],
];
const DRUMS = [
  ...[11, 12, 13, 14].flatMap((b) => [[b, 0, 'big', 1], [b, 2, 'big', 0.6]]),
  ...[11, 12, 13].map((b) => [b, 3.5, 'mid', 0.5]),
  ...[2.5, 2.75, 3, 3.25, 3.5, 3.75].map((x, i) => [14, x, 'mid', 0.3 + i * 0.1]), // a roll into the last phrase
  [15, 0, 'big', 0.7],
];

const at = (bar, beat) => ((bar - 1) * 4 + beat) * BEAT;
const EVENTS = [
  ...QIN.map(([b, x, note, vel]) => ({ t: at(b, x), kind: 'qin', note, vel })),
  ...HARMONICS.map(([b, x, note, vel]) => ({ t: at(b, x), kind: 'harm', note, vel })),
  ...XUN.map(([b, x, note, beats, vel]) => ({ t: at(b, x), kind: 'xun', note, len: beats * BEAT, vel })),
  ...DRUMS.map(([b, x, part, vel]) => ({ t: at(b, x), kind: 'drum', part, vel })),
].sort((a, b) => a.t - b.t);

/** A guqin note: partials of a string plucked near the bridge, the high ones dying first, the slow
 * vibrato of 吟 setting in as it rings, and the body of the instrument. */
function qinNote(f, r) {
  return render(6, 1, RATE, (ctx) => {
    const out = ctx.createGain();
    out.connect(filter(ctx, 'peaking', 190, 1.2, 4)).connect(filter(ctx, 'peaking', 430, 1.5, 3)).connect(filter(ctx, 'lowpass', 3500, -3)).connect(ctx.destination);
    const lfo = ctx.createOscillator();
    lfo.frequency.value = 4.6;
    const depth = ctx.createGain();
    depth.gain.setValueAtTime(0, 0);
    depth.gain.setValueAtTime(0, 0.5);
    depth.gain.linearRampToValueAtTime(1, 1.4);
    lfo.connect(depth);
    const ring = f < 150 ? 4 : f < 300 ? 3 : 2.2;
    for (let n = 1; n <= 16; n++) {
      const fn = f * n * Math.sqrt(1 + 0.00012 * n * n);
      const o = ctx.createOscillator();
      o.frequency.value = fn;
      const vib = ctx.createGain();
      vib.gain.value = fn * 0.006;
      depth.connect(vib).connect(o.frequency);
      const g = ctx.createGain();
      g.gain.setValueAtTime(0, 0);
      g.gain.linearRampToValueAtTime(Math.abs(Math.sin(n * Math.PI * 0.13)) / Math.pow(n, 0.9), 0.004);
      g.gain.setTargetAtTime(0, 0.004, ring / (1 + 0.35 * (n - 1)));
      o.connect(g).connect(out);
      o.start(0);
      o.stop(6);
    }
    // the finger leaving the string
    const s = ctx.createBufferSource();
    s.buffer = noise(ctx, 0.2, r);
    const sg = ctx.createGain();
    sg.gain.setValueAtTime(0, 0);
    sg.gain.linearRampToValueAtTime(0.05, 0.002);
    sg.gain.setTargetAtTime(0, 0.002, 0.01);
    s.connect(filter(ctx, 'bandpass', 1200, 1)).connect(sg).connect(out);
    s.start(0);
    lfo.start(0);
    lfo.stop(6);
  }).then((b) => normalize(b, 0.8));
}

/** A harmonic (泛音): the string touched at a node, almost a pure tone, glassy and long. */
function harmonic(f, r) {
  return render(5, 1, RATE, (ctx) => {
    const out = ctx.createGain();
    out.connect(ctx.destination);
    [[1, 1, 2.8], [2, 0.12, 1.2], [3, 0.04, 0.6]].forEach(([n, a, tau]) => {
      const o = ctx.createOscillator();
      o.frequency.value = f * n;
      const g = ctx.createGain();
      g.gain.setValueAtTime(0, 0);
      g.gain.linearRampToValueAtTime(a, 0.003);
      g.gain.setTargetAtTime(0, 0.003, tau);
      o.connect(g).connect(out);
      o.start(0);
      o.stop(5);
    });
    const s = ctx.createBufferSource();
    s.buffer = noise(ctx, 0.2, r);
    const sg = ctx.createGain();
    sg.gain.setValueAtTime(0, 0);
    sg.gain.linearRampToValueAtTime(0.03, 0.002);
    sg.gain.setTargetAtTime(0, 0.002, 0.008);
    s.connect(filter(ctx, 'bandpass', 2000, 1)).connect(sg).connect(out);
    s.start(0);
  }).then((b) => normalize(b, 0.8));
}

/**
 * A xun note, held: a dark, nearly pure tone with a breath of noise around it, scooping up into
 * pitch, then a gentle vibrato and swell. Playback cuts it to length with a soft release.
 */
function xunNote(f, r) {
  return render(7, 1, RATE, (ctx) => {
    const out = ctx.createGain();
    out.connect(filter(ctx, 'lowpass', 2600, -3)).connect(ctx.destination);
    const env = ctx.createGain();
    env.gain.setValueAtTime(0, 0);
    env.gain.linearRampToValueAtTime(0.8, 0.12);
    env.gain.linearRampToValueAtTime(1, 1.5);
    env.gain.setValueAtTime(1, 6.6);
    env.gain.linearRampToValueAtTime(0, 7);
    env.connect(out);
    const lfo = ctx.createOscillator();
    lfo.frequency.value = 4.8;
    const vib = ctx.createGain();
    vib.gain.setValueAtTime(0, 0);
    vib.gain.setValueAtTime(0, 0.6);
    vib.gain.linearRampToValueAtTime(f * 0.005, 1.6);
    lfo.connect(vib);
    const breathe = ctx.createGain();
    const trem = ctx.createGain();
    trem.gain.setValueAtTime(0, 0);
    trem.gain.setValueAtTime(0, 0.6);
    trem.gain.linearRampToValueAtTime(0.06, 1.6);
    lfo.connect(trem).connect(breathe.gain);
    breathe.connect(env);
    [[1, 1], [2, 0.08], [3, 0.12], [4, 0.025]].forEach(([n, a]) => {
      const o = ctx.createOscillator();
      o.frequency.setValueAtTime(f * n * 0.97, 0);
      o.frequency.exponentialRampToValueAtTime(f * n, 0.12);
      const vn = ctx.createGain();
      vn.gain.value = n;
      vib.connect(vn).connect(o.frequency);
      const g = ctx.createGain();
      g.gain.value = a;
      o.connect(g).connect(breathe);
      o.start(0);
      o.stop(7);
    });
    const nb = noise(ctx, 7, r);
    [[f, 14, 2], [1400, 0.8, 0.05]].forEach(([fc, q, a], i) => {
      const s = ctx.createBufferSource();
      s.buffer = nb;
      const g = ctx.createGain();
      g.gain.value = a;
      s.connect(filter(ctx, 'bandpass', fc, q)).connect(g).connect(breathe);
      s.start(0, i * 3);
    });
    lfo.start(0);
    lfo.stop(7);
  }).then((b) => normalize(b, 0.8));
}

async function buildMusicBank() {
  const r = rng(383383);
  const [qin, harm, xun] = await Promise.all([
    Promise.all(QIN_BASES.map((n) => qinNote(HZ[n], r))),
    harmonic(HZ.E5, r),
    Promise.all(XUN_NOTES.map((n) => xunNote(HZ[n], r))),
  ]);
  return { qin: Object.fromEntries(QIN_BASES.map((n, i) => [n, qin[i]])), harm, xun: Object.fromEntries(XUN_NOTES.map((n, i) => [n, xun[i]])) };
}

/** The nearest rendered guqin note, and the playback rate that turns it into `note`. */
function qinSample(bank, note) {
  let best = null;
  for (const base of QIN_BASES) {
    const rate = HZ[note] / HZ[base];
    if (!best || Math.abs(Math.log(rate)) < Math.abs(Math.log(best[1]))) best = [bank.qin[base], rate];
  }
  return best;
}

export class Music {
  /** `out` is the node the music plays into; `drums()` returns the war-drum samples once ready. */
  constructor(ctx, out, drums) {
    this.ctx = ctx;
    this.out = out;
    this.drums = drums;
    this.bank = null;
    this.loading = null;
    this.playing = false;
    this.start0 = 0;
    this.cursor = 0;
    this.drone = null;
  }

  load() {
    if (!this.loading) this.loading = buildMusicBank().then((b) => (this.bank = b));
    return this.loading;
  }

  async start() {
    if (this.playing) return;
    this.playing = true;
    await this.load();
    if (!this.playing) return;
    this.start0 = this.ctx.currentTime + 0.3;
    this.cursor = 0;
    this.startDrone();
  }

  stop() {
    this.playing = false;
    if (!this.drone) return;
    const now = this.ctx.currentTime;
    this.drone.gain.gain.setTargetAtTime(0, now, 0.6);
    for (const o of this.drone.oscs) o.stop(now + 4);
    this.drone = null;
  }

  /** A low string drone on A and E that breathes slowly. */
  startDrone() {
    const ctx = this.ctx;
    const gain = ctx.createGain();
    gain.gain.value = 0;
    gain.gain.setTargetAtTime(0.5, ctx.currentTime, 2.5);
    const lp = filter(ctx, 'lowpass', 340, -3);
    lp.connect(gain).connect(this.out);
    const lfo = ctx.createOscillator();
    lfo.frequency.value = 0.06;
    const lg = ctx.createGain();
    lg.gain.value = 90;
    lfo.connect(lg).connect(lp.frequency);
    const oscs = [lfo];
    [[55, 0.22, -0.4], [55.12, 0.14, 0.4], [82.41, 0.14, 0], [110.1, 0.06, 0]].forEach(([f, a, p]) => {
      const o = ctx.createOscillator();
      o.type = 'sawtooth';
      o.frequency.value = f;
      const g = ctx.createGain();
      g.gain.value = a;
      let node = o.connect(g);
      if (ctx.createStereoPanner) {
        const pn = ctx.createStereoPanner();
        pn.pan.value = p;
        node = node.connect(pn);
      }
      node.connect(lp);
      oscs.push(o);
    });
    for (const o of oscs) o.start();
    this.drone = { gain, oscs };
  }

  /** Schedules the notes due in the next moment; `quietDrums` while the battle has its own. */
  update(quietDrums) {
    if (!this.playing || !this.bank) return;
    const now = this.ctx.currentTime;
    if (now - this.start0 > LOOP) {
      // fell far behind (the page slept): pick the piece up again from the top
      this.start0 = now + 0.2;
      this.cursor = 0;
    }
    for (;;) {
      const ev = EVENTS[this.cursor];
      const t = this.start0 + ev.t;
      if (t > now + 0.3) break;
      if (t > now - 0.05) this.play(ev, Math.max(t, now), quietDrums);
      if (++this.cursor === EVENTS.length) {
        this.cursor = 0;
        this.start0 += LOOP;
      }
    }
  }

  play(ev, t, quietDrums) {
    const ctx = this.ctx;
    const b = this.bank;
    const swing = (Math.random() - 0.5) * 0.02;
    const vel = ev.vel * (0.92 + Math.random() * 0.16);
    let buf;
    let rate = 1;
    let gain;
    let pan = 0;
    if (ev.kind === 'qin') {
      [buf, rate] = qinSample(b, ev.note);
      gain = vel * 0.55;
      pan = HZ[ev.note] < 200 ? -0.15 : 0.15;
    } else if (ev.kind === 'harm') {
      buf = b.harm;
      rate = HZ[ev.note] / HZ.E5;
      gain = vel * 0.3;
      pan = 0.25;
    } else if (ev.kind === 'xun') {
      buf = b.xun[ev.note];
      gain = vel * 0.5;
      pan = -0.1;
    } else {
      const set = this.drums()?.[ev.part];
      if (!set || quietDrums) return;
      buf = ev.vel > 0.8 ? set[0] : set[1];
      gain = vel * 0.35;
    }
    const s = ctx.createBufferSource();
    s.buffer = buf;
    s.playbackRate.value = rate;
    const g = ctx.createGain();
    const when = t + (ev.kind === 'xun' ? 0 : swing);
    g.gain.setValueAtTime(gain, when);
    if (ev.kind === 'xun') g.gain.setTargetAtTime(0, when + ev.len, 0.18); // legato: each note fades under the next
    let node = s.connect(g);
    if (pan && ctx.createStereoPanner) {
      const p = ctx.createStereoPanner();
      p.pan.value = pan;
      node = node.connect(p);
    }
    node.connect(this.out);
    s.start(Math.max(when, ctx.currentTime));
    if (ev.kind === 'xun') s.stop(when + ev.len + 1.2);
  }
}
