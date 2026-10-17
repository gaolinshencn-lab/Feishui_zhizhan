// The sample bank behind the soundscape: war drums, massed shouting, hooves, marching feet, weapons,
// water, fire, horns, the retreat gong and so on. Each sound is synthesised once, in an
// OfflineAudioContext, the first time the viewer turns sound on; no audio files are shipped.
// Everything is seeded, so the battle sounds the same on every visit.

const OAC = window.OfflineAudioContext || window.webkitOfflineAudioContext;

/** Small seeded PRNG (mulberry32). */
export function rng(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const range = (r, a, b) => a + (b - a) * r();
const logRange = (r, a, b) => a * Math.pow(b / a, r());

function render(seconds, channels, rate, build) {
  const ctx = new OAC(channels, Math.ceil(seconds * rate), rate);
  build(ctx);
  return new Promise((resolve, reject) => {
    ctx.oncomplete = (e) => resolve(e.renderedBuffer);
    const p = ctx.startRendering();
    if (p && p.then) p.then(resolve, reject);
  });
}

/** White, pink or brown noise samples. */
function noiseData(len, r, color = 'white') {
  const d = new Float32Array(len);
  let b0 = 0, b1 = 0, b2 = 0, b3 = 0, b4 = 0, b5 = 0, b6 = 0, br = 0;
  for (let i = 0; i < len; i++) {
    const w = r() * 2 - 1;
    if (color === 'white') d[i] = w;
    else if (color === 'pink') {
      // Paul Kellet's filter
      b0 = 0.99886 * b0 + w * 0.0555179;
      b1 = 0.99332 * b1 + w * 0.0750759;
      b2 = 0.969 * b2 + w * 0.153852;
      b3 = 0.8665 * b3 + w * 0.3104856;
      b4 = 0.55 * b4 + w * 0.5329522;
      b5 = -0.7616 * b5 - w * 0.016898;
      d[i] = (b0 + b1 + b2 + b3 + b4 + b5 + b6 + w * 0.5362) * 0.11;
      b6 = w * 0.115926;
    } else {
      br = (br + 0.02 * w) / 1.02;
      d[i] = br * 3.5;
    }
  }
  return d;
}

/** A noise buffer with `channels` independent channels. */
function noise(ctx, seconds, r, color = 'white', channels = 1) {
  const len = Math.ceil(seconds * ctx.sampleRate);
  const buf = ctx.createBuffer(channels, len, ctx.sampleRate);
  for (let c = 0; c < channels; c++) buf.getChannelData(c).set(noiseData(len, r, color));
  return buf;
}

/** Peak-normalises a rendered buffer (all channels together). */
function normalize(buf, peak = 0.9) {
  let m = 0;
  for (let c = 0; c < buf.numberOfChannels; c++) {
    const d = buf.getChannelData(c);
    for (let i = 0; i < d.length; i++) m = Math.max(m, Math.abs(d[i]));
  }
  const k = m > 0 ? peak / m : 1;
  for (let c = 0; c < buf.numberOfChannels; c++) {
    const d = buf.getChannelData(c);
    for (let i = 0; i < d.length; i++) d[i] *= k;
  }
  return buf;
}

/** Cuts `n` equal slots out of one render (variants are rendered side by side). */
function slice(live, buf, n) {
  const len = Math.floor(buf.length / n);
  const out = [];
  for (let i = 0; i < n; i++) {
    const b = live.createBuffer(buf.numberOfChannels, len, buf.sampleRate);
    for (let c = 0; c < buf.numberOfChannels; c++) b.getChannelData(c).set(buf.getChannelData(c).subarray(i * len, (i + 1) * len));
    out.push(normalize(b));
  }
  return out;
}

/**
 * Folds the last `fade` seconds of each channel over its start, so the first `seconds` loop without
 * a seam, and scales the result to an RMS of `level`.
 */
function loop(live, chans, sr, seconds, fade, level = 0.2) {
  const len = Math.round(seconds * sr);
  const f = Math.round(fade * sr);
  const b = live.createBuffer(chans.length, len, sr);
  let sum = 0;
  chans.forEach((src, c) => {
    const d = b.getChannelData(c);
    d.set(src.subarray(0, len));
    for (let i = 0; i < f; i++) {
      const g = (i / f) * (Math.PI / 2);
      d[i] = src[i] * Math.sin(g) + src[len + i] * Math.cos(g);
    }
    for (let i = 0; i < len; i++) sum += d[i] * d[i];
  });
  const k = level / Math.sqrt(sum / (len * chans.length) || 1);
  for (let c = 0; c < chans.length; c++) {
    const d = b.getChannelData(c);
    for (let i = 0; i < len; i++) d[i] *= k;
  }
  return b;
}

const channels = (buf) => Array.from({ length: buf.numberOfChannels }, (_, c) => buf.getChannelData(c));

// --- plain-JS mixing: the long loops are built from hundreds of hits, far cheaper this way ---

/** RBJ biquad, in place. */
function biquad(x, sr, type, f, q = Math.SQRT1_2) {
  const w = (2 * Math.PI * f) / sr;
  const cs = Math.cos(w);
  const al = Math.sin(w) / (2 * q);
  let b0, b1, b2;
  if (type === 'lowpass') [b0, b1, b2] = [(1 - cs) / 2, 1 - cs, (1 - cs) / 2];
  else if (type === 'highpass') [b0, b1, b2] = [(1 + cs) / 2, -(1 + cs), (1 + cs) / 2];
  else [b0, b1, b2] = [al, 0, -al]; // band-pass, 0 dB at the centre
  const a0 = 1 + al;
  const a1 = (-2 * cs) / a0;
  const a2 = (1 - al) / a0;
  b0 /= a0;
  b1 /= a0;
  b2 /= a0;
  let x1 = 0, x2 = 0, y1 = 0, y2 = 0;
  for (let i = 0; i < x.length; i++) {
    const v = x[i];
    const y = b0 * v + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2;
    x2 = x1;
    x1 = v;
    y2 = y1;
    y1 = y;
    x[i] = y;
  }
  return x;
}

/** Adds a mono sample into stereo arrays at `t` seconds, resampled by `rate`, panned. */
function mixIn([L, R], sr, src, srcRate, t, gain, pan, rate = 1) {
  const step = (rate * srcRate) / sr;
  const a = ((pan + 1) * Math.PI) / 4;
  const gl = gain * Math.cos(a);
  const gr = gain * Math.sin(a);
  let i = Math.round(t * sr);
  for (let p = 0; p < src.length - 1 && i < L.length; p += step, i++) {
    if (i < 0) continue;
    const k = p | 0;
    const v = src[k] + (src[k + 1] - src[k]) * (p - k);
    L[i] += v * gl;
    R[i] += v * gr;
  }
}

const hit = (list, r) => list[Math.floor(r() * list.length)];

// --- node helpers for offline graphs -------------------------------------------------------

function filter(ctx, type, freq, q = 0.7, gain = 0) {
  const f = ctx.createBiquadFilter();
  f.type = type;
  f.frequency.value = freq;
  f.Q.value = q;
  f.gain.value = gain;
  return f;
}

/** Gain node with a percussive envelope: linear attack, exponential decay. */
function strike(ctx, t, peak, attack, tau) {
  const g = ctx.createGain();
  g.gain.setValueAtTime(0, t);
  g.gain.linearRampToValueAtTime(peak, t + attack);
  g.gain.setTargetAtTime(0, t + attack, tau);
  return g;
}

function pan(ctx, x) {
  if (!ctx.createStereoPanner) return ctx.createGain();
  const p = ctx.createStereoPanner();
  p.pan.value = Math.max(-1, Math.min(1, x));
  return p;
}

/** A decaying partial with an optional pitch drop at the start. */
function partial(ctx, dest, t, freq, amp, tau, end, drop = 0, dropTau = 0.04) {
  const o = ctx.createOscillator();
  o.frequency.setValueAtTime(freq * (1 + drop), t);
  if (drop) o.frequency.setTargetAtTime(freq, t, dropTau);
  const g = strike(ctx, t, amp, 0.002, tau);
  o.connect(g).connect(dest);
  o.start(t);
  o.stop(end);
}

function burst(ctx, dest, nbuf, r, t, type, freq, q, amp, attack, tau, len = 0.4) {
  const n = ctx.createBufferSource();
  n.buffer = nbuf;
  const g = strike(ctx, t, amp, attack, tau);
  n.connect(filter(ctx, type, freq, q)).connect(g).connect(dest);
  n.start(t, r() * (nbuf.duration - len - 0.01), len);
}

// --- one-shots -----------------------------------------------------------------------------

/**
 * Barrel war drum (战鼓): membrane modes that drop slightly in pitch as the skin relaxes, a felt
 * mallet thud and the ring of the shell. `vel` is the force of the blow.
 */
async function drums(live, r) {
  const SIZES = { big: [62, 1, 1.8], mid: [82, 0.75, 1.3], small: [110, 0.55, 1] }; // f0, decay, slot
  const MODES = [[1, 0.55, 0.42], [1.5, 0.55, 0.3], [1.98, 0.5, 0.26], [2.44, 0.38, 0.2], [2.9, 0.28, 0.16], [3.38, 0.2, 0.12], [3.87, 0.14, 0.1], [4.4, 0.1, 0.08], [5.1, 0.07, 0.06]];
  const out = {};
  for (const [name, [f0, decay, slot]] of Object.entries(SIZES)) {
    const buf = await render(slot * 2, 1, 44100, (ctx) => {
      const nb = noise(ctx, 2, r);
      [1, 0.62].forEach((vel, i) => {
        const t = i * slot + 0.002;
        const end = (i + 1) * slot - 0.001;
        const bus = ctx.createGain();
        bus.connect(filter(ctx, 'lowpass', 2200 + 2600 * vel, -3)).connect(ctx.destination);
        for (const [k, a, tau] of MODES) {
          partial(ctx, bus, t, f0 * k * range(r, 0.994, 1.006), a * (k === 1 ? 1 : 0.5 + 0.5 * vel), tau * decay, end, 0.1 + 0.08 * vel);
        }
        burst(ctx, bus, nb, r, t, 'lowpass', 600 + 1600 * vel, 0, 0.6 * vel, 0.001, 0.012); // mallet on hide
        burst(ctx, bus, nb, r, t, 'bandpass', f0 * 3.2, 1.5, 0.45 * vel, 0.002, 0.11); // air in the shell
      });
    });
    out[name] = slice(live, buf, 2); // [hard, soft]
  }
  return out;
}

/** Blades and spear heads meeting (bright, short, filtered for distance) and wooden shields. */
async function weapons(live, r) {
  const n = 8;
  const slot = 0.7;
  const buf = await render(n * slot, 1, 44100, (ctx) => {
    const nb = noise(ctx, 1, r);
    for (let i = 0; i < n; i++) {
      const t = i * slot + 0.002;
      const end = (i + 1) * slot - 0.001;
      const bus = ctx.createGain();
      if (i < 5) {
        bus.connect(filter(ctx, 'lowpass', 3800, 0.5)).connect(ctx.destination);
        const f1 = range(r, 650, 1500);
        const RATIOS = [1, 2.33, 3.82, 5.24, 6.88];
        const AMPS = [1, 0.6, 0.42, 0.28, 0.18];
        const TAUS = [0.17, 0.1, 0.07, 0.05, 0.035];
        RATIOS.forEach((k, j) => partial(ctx, bus, t, f1 * k * range(r, 0.97, 1.03), AMPS[j], TAUS[j] * range(r, 0.7, 1.3), end));
        burst(ctx, bus, nb, r, t, 'bandpass', 2200, 0.9, 0.6, 0.0005, 0.004);
      } else {
        bus.connect(filter(ctx, 'lowpass', 2600, 0.5)).connect(ctx.destination);
        const f1 = range(r, 170, 360);
        [[1, 1, 0.07], [2.7, 0.4, 0.04], [4.6, 0.2, 0.025]].forEach(([k, a, tau]) => partial(ctx, bus, t, f1 * k, a, tau, end));
        burst(ctx, bus, nb, r, t, 'lowpass', 1200, 0.7, 0.8, 0.0005, 0.008);
      }
    }
  });
  const all = slice(live, buf, n);
  return { metal: all.slice(0, 5), wood: all.slice(5) };
}

/** Hooves on packed earth, feet on dirt, Go stones, a wooden clog snapping. */
async function footfalls(live, r) {
  const n = 12;
  const slot = 0.32;
  const buf = await render(n * slot, 1, 44100, (ctx) => {
    const nb = noise(ctx, 1, r);
    for (let i = 0; i < n; i++) {
      const t = i * slot + 0.002;
      const end = (i + 1) * slot - 0.001;
      const bus = ctx.createGain();
      bus.connect(ctx.destination);
      if (i < 4) {
        // hoof
        partial(ctx, bus, t, range(r, 110, 160), 0.8, 0.03, end, 0.4, 0.012);
        burst(ctx, bus, nb, r, t, 'lowpass', 1000, 0, 0.6, 0.001, 0.018);
        burst(ctx, bus, nb, r, t, 'bandpass', range(r, 700, 1100), 4, 0.5, 0.0005, 0.02); // the hollow hoof wall
        burst(ctx, bus, nb, r, t, 'bandpass', 1800, 1.2, 0.12, 0.0005, 0.006);
      } else if (i < 8) {
        // foot
        burst(ctx, bus, nb, r, t, 'bandpass', range(r, 350, 700), 0.7, 1, 0.004, 0.045);
        burst(ctx, bus, nb, r, t, 'bandpass', 1500, 1, 0.22, 0.002, 0.012);
        partial(ctx, bus, t, range(r, 70, 90), 0.08, 0.03, end);
      } else if (i < 11) {
        // Go stone on a wooden board
        const k = range(r, 0.97, 1.03);
        burst(ctx, bus, nb, r, t, 'highpass', 2500, 0.7, 0.6, 0.0003, 0.0015);
        [[610, 1, 0.045], [1350, 0.55, 0.03], [2240, 0.3, 0.02], [3800, 0.12, 0.012]].forEach(([f, a, tau]) => partial(ctx, bus, t, f * k, a, tau, end));
      } else {
        // a clog tooth snapping
        burst(ctx, bus, nb, r, t, 'bandpass', 1400, 0.8, 1, 0.0005, 0.01);
        [[880, 0.8, 0.03], [2050, 0.4, 0.02], [3300, 0.2, 0.012]].forEach(([f, a, tau]) => partial(ctx, bus, t, f, a, tau, end));
      }
    }
  });
  const all = slice(live, buf, n);
  return { hoof: all.slice(0, 4), foot: all.slice(4, 8), stone: all.slice(8, 11), snap: all[11] };
}

/** Bodies and oars going into the water. */
async function splashes(live, r) {
  const n = 5;
  const slot = 1;
  const buf = await render(n * slot, 1, 32000, (ctx) => {
    const nb = noise(ctx, 1.5, r);
    for (let i = 0; i < n; i++) {
      const t = i * slot + 0.002;
      const end = (i + 1) * slot - 0.001;
      const bus = ctx.createGain();
      bus.connect(filter(ctx, 'lowpass', 3600, 0.5)).connect(ctx.destination);
      const src = ctx.createBufferSource();
      src.buffer = nb;
      const bp = filter(ctx, 'bandpass', 1700, 0.8);
      bp.frequency.setValueAtTime(range(r, 1400, 2000), t);
      bp.frequency.exponentialRampToValueAtTime(range(r, 380, 520), t + 0.3);
      src.connect(bp).connect(strike(ctx, t, 1, 0.004, range(r, 0.08, 0.14))).connect(bus);
      src.start(t, r() * 0.4, 0.9);
      const o = ctx.createOscillator();
      o.frequency.setValueAtTime(range(r, 140, 180), t);
      o.frequency.exponentialRampToValueAtTime(60, t + 0.15);
      o.connect(strike(ctx, t, 0.5, 0.003, 0.05)).connect(bus);
      o.start(t);
      o.stop(end);
      for (let k = 0; k < 4; k++) {
        const tb = t + range(r, 0.05, 0.45);
        const f = logRange(r, 450, 1300);
        const b = ctx.createOscillator();
        b.frequency.setValueAtTime(f, tb);
        b.frequency.exponentialRampToValueAtTime(f * 1.35, tb + 0.04);
        b.connect(strike(ctx, tb, 0.14, 0.002, 0.018)).connect(bus);
        b.start(tb);
        b.stop(Math.min(end, tb + 0.2));
      }
    }
  });
  return slice(live, buf, n);
}

/**
 * The retreat gong (鸣金): bronze partials, each doubled with a slight detune so it shimmers,
 * low-passed so it rings warm rather than clanging.
 */
async function gong(live, r) {
  const buf = await render(5, 1, 44100, (ctx) => {
    const nb = noise(ctx, 1, r);
    const bus = ctx.createGain();
    bus.connect(filter(ctx, 'lowpass', 3000, 0.5)).connect(ctx.destination);
    const f0 = 210;
    const P = [[1, 1, 2.6], [1.47, 0.6, 2], [2, 0.5, 1.8], [2.41, 0.38, 1.4], [2.94, 0.28, 1.1], [3.55, 0.2, 0.8], [4.2, 0.13, 0.6], [5.05, 0.08, 0.45]];
    for (const [k, a, tau] of P) {
      partial(ctx, bus, 0.002, f0 * k * 0.9975, a * 0.5, tau, 4.99);
      partial(ctx, bus, 0.002, f0 * k * 1.0025, a * 0.5, tau, 4.99);
    }
    burst(ctx, bus, nb, r, 0.002, 'lowpass', 1500, 0.6, 0.35, 0.001, 0.03);
  });
  return normalize(buf);
}

/**
 * Ox horns (号角) sounded together: buzzing reed-like tone, the pitch scooping up into the note,
 * brightening as the blower's breath swells and falling away at the end.
 */
async function horns(live, r, twoNote) {
  const dur = twoNote ? 4.6 : 4;
  const buf = await render(dur, 2, 32000, (ctx) => {
    const nb = noise(ctx, 2, r);
    const bus = ctx.createGain();
    bus.connect(filter(ctx, 'peaking', 520, 1, 5)).connect(filter(ctx, 'lowpass', 2400, 0.5)).connect(ctx.destination);
    const f = twoNote ? 98 : 110;
    [[0, -0.45, 1], [0.12, 0.05, 1.006], [0.26, 0.45, 0.994]].forEach(([t0, p, det]) => {
      const t = t0 + 0.02;
      const stop = dur - 0.35 + t0 * 0.5;
      const o = ctx.createOscillator();
      o.type = 'sawtooth';
      const fr = f * det;
      o.frequency.setValueAtTime(fr * 0.92, t);
      o.frequency.exponentialRampToValueAtTime(fr, t + 0.3);
      if (twoNote) {
        o.frequency.setValueAtTime(fr, t + 1.5);
        o.frequency.exponentialRampToValueAtTime(fr * 1.5, t + 1.68);
      }
      const hold = twoNote ? fr * 1.5 : fr;
      o.frequency.setValueAtTime(hold, stop - 0.45);
      o.frequency.exponentialRampToValueAtTime(hold * 0.95, stop);
      const vib = ctx.createOscillator();
      vib.frequency.value = range(r, 4.2, 5.2);
      const vg = ctx.createGain();
      vg.gain.setValueAtTime(0, t);
      vg.gain.linearRampToValueAtTime(hold * 0.004, t + 1);
      vib.connect(vg).connect(o.frequency);
      const lp = filter(ctx, 'lowpass', 250, 0.8);
      lp.frequency.setValueAtTime(250, t);
      lp.frequency.linearRampToValueAtTime(1300, t + 0.5);
      lp.frequency.setTargetAtTime(950, t + 0.6, 0.8);
      lp.frequency.setTargetAtTime(280, stop - 0.4, 0.15);
      const g = ctx.createGain();
      g.gain.setValueAtTime(0, t);
      g.gain.linearRampToValueAtTime(0.5, t + 0.35);
      g.gain.linearRampToValueAtTime(0.6, stop - 0.6);
      g.gain.setTargetAtTime(0, stop - 0.4, 0.12);
      const pp = pan(ctx, p);
      o.connect(lp).connect(g).connect(pp).connect(bus);
      // breath
      const b = ctx.createBufferSource();
      b.buffer = nb;
      const bg = ctx.createGain();
      bg.gain.setValueAtTime(0, t);
      bg.gain.linearRampToValueAtTime(0.03, t + 0.2);
      bg.gain.setTargetAtTime(0, stop - 0.4, 0.12);
      b.connect(filter(ctx, 'bandpass', 900, 0.7)).connect(bg).connect(pp);
      o.start(t);
      vib.start(t);
      b.start(t, 0, dur - t - 0.01);
      o.stop(stop + 0.4);
      vib.stop(stop + 0.4);
    });
  });
  return normalize(buf, 0.85);
}

/** Distant red-crowned cranes: trumpeting two-syllable calls with the rolling trill of the bird. */
async function cranes(live, r) {
  const n = 3;
  const slot = 1.6;
  const buf = await render(n * slot, 1, 32000, (ctx) => {
    for (let i = 0; i < n; i++) {
      const bus = ctx.createGain();
      bus.connect(filter(ctx, 'bandpass', 1500, 0.9)).connect(filter(ctx, 'lowpass', 2200, 0.5)).connect(ctx.destination);
      const k = range(r, 0.9, 1.1);
      let t = i * slot + 0.02;
      const syl = i === 2 ? [[0.2, 760, 840, 700], [0.34, 900, 980, 800], [0.3, 880, 950, 780]] : [[0.22, 780, 850, 720], [0.36, 900, 980, 800]];
      for (const [d, a, b, c] of syl) {
        const o = ctx.createOscillator();
        o.type = 'triangle';
        o.frequency.setValueAtTime(a * k, t);
        o.frequency.linearRampToValueAtTime(b * k, t + d * 0.35);
        o.frequency.linearRampToValueAtTime(c * k, t + d);
        const trill = ctx.createOscillator();
        trill.frequency.value = range(r, 32, 42);
        const tg = ctx.createGain();
        tg.gain.value = 0.4;
        const am = ctx.createGain();
        am.gain.value = 0.6;
        trill.connect(tg).connect(am.gain);
        const g = ctx.createGain();
        g.gain.setValueAtTime(0, t);
        g.gain.linearRampToValueAtTime(1, t + 0.02);
        g.gain.setValueAtTime(1, t + d - 0.05);
        g.gain.linearRampToValueAtTime(0, t + d);
        o.connect(am).connect(g).connect(bus);
        o.start(t);
        trill.start(t);
        o.stop(t + d + 0.01);
        trill.stop(t + d + 0.01);
        t += d + 0.06;
      }
    }
  });
  return slice(live, buf, n);
}

/** A volley: bows released together, the hiss of shafts passing overhead, then they come down. */
async function volley(live, r, hits) {
  const buf = await render(4, 2, 32000, (ctx) => {
    const nb = noise(ctx, 3, r);
    const bus = ctx.createGain();
    bus.connect(filter(ctx, 'lowpass', 3400, 0.5)).connect(ctx.destination);
    for (let i = 0; i < 40; i++) {
      const t = range(r, 0, 0.35);
      const p = pan(ctx, range(r, -0.8, 0.8));
      p.connect(bus);
      partial(ctx, p, t, range(r, 110, 170), 0.12, 0.05, t + 0.3);
      burst(ctx, p, nb, r, t, 'lowpass', 800, 0.7, 0.12, 0.001, 0.01);
    }
    for (let i = 0; i < 60; i++) {
      const t = range(r, 0.1, 0.6);
      const d = range(r, 0.5, 0.9);
      const src = ctx.createBufferSource();
      src.buffer = nb;
      const bp = filter(ctx, 'bandpass', 2400, 1.4);
      bp.frequency.setValueAtTime(range(r, 2000, 2600), t);
      bp.frequency.exponentialRampToValueAtTime(range(r, 600, 800), t + d);
      const g = ctx.createGain();
      const a = range(r, 0.05, 0.16);
      g.gain.setValueAtTime(0, t);
      g.gain.linearRampToValueAtTime(a, t + d * 0.75);
      g.gain.setTargetAtTime(0, t + d * 0.75, 0.05);
      src.connect(bp).connect(g).connect(pan(ctx, range(r, -0.9, 0.9))).connect(bus);
      src.start(t, r() * 2, d + 0.3);
      const th = t + d + range(r, 0, 0.15);
      const h = r() < 0.6 ? hits.hoof[Math.floor(r() * hits.hoof.length)] : hits.wood[Math.floor(r() * hits.wood.length)];
      const s = ctx.createBufferSource();
      s.buffer = h;
      s.playbackRate.value = range(r, 0.8, 1.2);
      const sg = ctx.createGain();
      sg.gain.value = range(r, 0.08, 0.3);
      s.connect(sg).connect(pan(ctx, range(r, -0.9, 0.9))).connect(bus);
      s.start(th);
    }
  });
  return normalize(buf, 0.85);
}

// --- loops ---------------------------------------------------------------------------------

const LOOP_RATE = 22050; // the loops are all dark; this halves their cost

/**
 * Massed shouting (喊杀): many voices, each a buzzing glottal source shaped by the two lowest
 * formants of a shouted vowel, rising and falling through short cries and long yells.
 */
async function roar(live, r) {
  const L = 10;
  const F = 1;
  const VOWELS = [
    [850, 1250], // a
    [620, 980], // o
    [560, 1700], // e
    [760, 1400], // between a and e
  ];
  const buf = await render(L + F, 2, LOOP_RATE, (ctx) => {
    const near = ctx.createGain();
    const far = ctx.createGain();
    near.connect(filter(ctx, 'lowpass', 3300, -3)).connect(ctx.destination);
    far.connect(filter(ctx, 'lowpass', 1700, -3)).connect(ctx.destination);
    // the breath and stamp of the crowd under the voices
    const air = ctx.createBufferSource();
    air.buffer = noise(ctx, L + F, r, 'pink', 2);
    const ag = ctx.createGain();
    ag.gain.value = 0.05;
    air.connect(filter(ctx, 'bandpass', 700, 0.7)).connect(ag).connect(far);
    air.start(0);
    for (let v = 0; v < 40; v++) {
      const isFar = v % 3 !== 0;
      const f0 = logRange(r, 170, 310);
      const o = ctx.createOscillator();
      o.type = 'sawtooth';
      const f1 = filter(ctx, 'bandpass', 800, 8);
      const f2 = filter(ctx, 'bandpass', 1200, 10);
      const g2 = ctx.createGain();
      g2.gain.value = 0.5;
      const env = ctx.createGain();
      env.gain.value = 0;
      o.connect(f1).connect(env);
      o.connect(f2).connect(g2).connect(env);
      env.connect(pan(ctx, range(r, -0.9, 0.9))).connect(isFar ? far : near);
      let t = range(r, -0.8, 0.6);
      while (t < L + F) {
        const d = r() < 0.45 ? range(r, 0.25, 0.45) : range(r, 0.7, 1.6);
        const s = Math.max(0, t);
        const e = t + d;
        if (e > 0.05) {
          const [a1, a2] = VOWELS[Math.floor(r() * VOWELS.length)];
          f1.frequency.setValueAtTime(a1 * range(r, 0.93, 1.07), s);
          f2.frequency.setValueAtTime(a2 * range(r, 0.93, 1.07), s);
          // pitch contour of a cry, with a little irregularity in the voice
          const n = Math.max(2, Math.round((e - s) * 60));
          const curve = new Float32Array(n);
          const up = range(r, 1.02, 1.12);
          let jit = 0;
          for (let k = 0; k < n; k++) {
            const x = k / (n - 1);
            const shape = x < 0.3 ? 0.88 + (up - 0.88) * (x / 0.3) : up - (up - 0.84) * Math.pow((x - 0.3) / 0.7, 1.5);
            jit = jit * 0.7 + (r() - 0.5) * 0.02;
            curve[k] = f0 * shape * (1 + jit);
          }
          o.frequency.setValueCurveAtTime(curve, s, e - s);
          const a = range(r, 0.4, 1) * (isFar ? 0.7 : 1);
          env.gain.setValueAtTime(0, s);
          env.gain.linearRampToValueAtTime(a, s + range(r, 0.03, 0.08));
          env.gain.setTargetAtTime(a * 0.7, s + 0.08, d * 0.6);
          env.gain.setTargetAtTime(0, e - 0.04, 0.05);
        }
        t = e + range(r, 0.12, 1.3);
      }
      o.start(0);
    }
  });
  return loop(live, channels(buf), LOOP_RATE, L, F);
}

/** Thousands on the march: shuffling feet on dirt with a loose common pace, and a low rumble. */
function march(live, r, hits) {
  const L = 10;
  const F = 1;
  const sr = LOOP_RATE;
  const n = Math.ceil((L + F) * sr);
  const ch = [0, 1].map(() => {
    const x = biquad(noiseData(n, r, 'brown'), sr, 'lowpass', 140);
    for (let i = 0; i < n; i++) x[i] *= 0.1;
    return x;
  });
  for (let w = 0; w < 64; w++) {
    const inStep = w % 3 === 0; // a third keep the drum's pace
    const period = inStep ? 0.6 + range(r, -0.01, 0.01) : range(r, 0.52, 0.62);
    let t = inStep ? (w % 2) * 0.3 + range(r, 0, 0.05) : range(r, 0, period);
    const amp = range(r, 0.15, 0.8);
    const p = range(r, -0.9, 0.9);
    while (t < L + F) {
      const b = hit(hits.foot, r);
      mixIn(ch, sr, b.getChannelData(0), b.sampleRate, t, amp * range(r, 0.7, 1), p, range(r, 0.85, 1.15));
      t += period + range(r, -0.02, 0.02);
    }
  }
  for (const x of ch) biquad(biquad(x, sr, 'highpass', 55), sr, 'lowpass', 2000);
  return loop(live, ch, sr, L, F);
}

/** Cavalry at the gallop: four-beat strides of many horses, and the drumming of the ground. */
function cavalry(live, r, hits) {
  const L = 8;
  const F = 1;
  const sr = LOOP_RATE;
  const n = Math.ceil((L + F) * sr);
  const ch = [0, 1].map(() => {
    const x = biquad(noiseData(n, r, 'brown'), sr, 'lowpass', 160);
    for (let i = 0; i < n; i++) x[i] *= 0.1;
    return x;
  });
  for (let h = 0; h < 18; h++) {
    const stride = range(r, 0.4, 0.47);
    const amp = range(r, 0.25, 1);
    const p = range(r, -0.85, 0.85);
    let t = range(r, 0, stride);
    while (t < L + F) {
      for (const off of [0, 0.11, 0.27, 0.38]) {
        const b = hit(hits.hoof, r);
        mixIn(ch, sr, b.getChannelData(0), b.sampleRate, t + off * stride + range(r, -0.006, 0.006), amp * range(r, 0.6, 1), p, range(r, 0.9, 1.1));
      }
      t += stride * range(r, 0.98, 1.02);
    }
  }
  for (const x of ch) biquad(x, sr, 'lowpass', 2200);
  return loop(live, ch, sr, L, F);
}

/** The Fei and the Huai: a low rush of water and the babble of bubbles near the bank. */
function river(live, r) {
  const L = 10;
  const F = 1;
  const sr = LOOP_RATE;
  const n = Math.ceil((L + F) * sr);
  const ch = [0, 1].map(() => {
    const x = biquad(noiseData(n, r, 'pink'), sr, 'lowpass', 420);
    for (let i = 0; i < n; i++) x[i] *= 0.5;
    return x;
  });
  const len = Math.round(0.09 * sr);
  for (let b = 0; b < 300; b++) {
    const start = Math.round(range(r, 0, L + F - 0.1) * sr);
    const f = logRange(r, 350, 1400);
    const up = range(r, 1.2, 1.45);
    const a = range(r, 0.02, 0.1);
    const ang = ((range(r, -0.8, 0.8) + 1) * Math.PI) / 4;
    let ph = 0;
    for (let k = 0; k < len && start + k < n; k++) {
      const t = k / sr;
      ph += (2 * Math.PI * f * Math.pow(up, Math.min(1, t / 0.05))) / sr;
      const v = Math.sin(ph) * Math.min(1, t / 0.002) * Math.exp(-t / 0.018) * a;
      ch[0][start + k] += v * Math.cos(ang);
      ch[1][start + k] += v * Math.sin(ang);
    }
  }
  for (const x of ch) biquad(x, sr, 'lowpass', 3200);
  return loop(live, ch, sr, L, F);
}

/** A burning camp: the low breath of the flames and the crackle of timber. */
function fire(live, r) {
  const L = 8;
  const F = 1;
  const sr = LOOP_RATE;
  const n = Math.ceil((L + F) * sr);
  const ch = [0, 1].map(() => {
    const x = biquad(biquad(noiseData(n, r, 'brown'), sr, 'lowpass', 900), sr, 'highpass', 120);
    for (let i = 0; i < n; i++) x[i] *= 0.45 + 0.15 * Math.sin((2 * Math.PI * 0.31 * i) / sr);
    return x;
  });
  const click = new Float32Array(Math.round(0.03 * sr));
  for (let c = 0; c < 420; c++) {
    const tau = range(r, 0.001, 0.004) * sr;
    for (let k = 0; k < click.length; k++) click[k] = (r() * 2 - 1) * Math.exp(-k / tau);
    biquad(click, sr, 'bandpass', logRange(r, 900, 3200), 1.2);
    mixIn(ch, sr, click, sr, range(r, 0, L + F - 0.05), 0.03 + 0.6 * Math.pow(r(), 4), range(r, -0.7, 0.7));
  }
  for (const x of ch) biquad(x, sr, 'lowpass', 4200);
  return loop(live, ch, sr, L, F);
}

/** Stereo pink noise for the live wind. */
function windNoise(live, r) {
  const sr = LOOP_RATE;
  const n = 9 * sr;
  return loop(live, [noiseData(n, r, 'pink'), noiseData(n, r, 'pink')], sr, 8, 1, 0.25);
}

const breathe = () => new Promise((ok) => setTimeout(ok, 0));

/**
 * Renders everything, a part at a time so the page keeps drawing; `onPart(key, bank)` lets the
 * caller start each sound as soon as its samples exist.
 */
export async function buildBank(live, onPart) {
  const bank = {};
  const add = (key, value) => {
    bank[key] = value;
    onPart?.(key, bank);
  };
  add('wind', windNoise(live, rng(1)));
  const [d, w, s] = await Promise.all([drums(live, rng(2)), weapons(live, rng(3)), footfalls(live, rng(4))]);
  add('drums', d);
  add('weapons', w);
  add('steps', s);
  const roarDone = roar(live, rng(15)).then((x) => add('roar', x)); // the slowest; renders off the main thread
  const hits = { hoof: s.hoof, foot: s.foot, wood: w.wood };
  for (const [key, make] of [['river', () => river(live, rng(5))], ['fire', () => fire(live, rng(6))], ['march', () => march(live, rng(8), hits)], ['cavalry', () => cavalry(live, rng(9), hits)]]) {
    await breathe();
    add(key, make());
  }
  const [sp, g, h1, h2, cr, vo] = await Promise.all([splashes(live, rng(7)), gong(live, rng(10)), horns(live, rng(11), false), horns(live, rng(12), true), cranes(live, rng(13)), volley(live, rng(14), hits)]);
  add('splash', sp);
  add('gong', g);
  add('horn', h1);
  add('horn2', h2);
  add('crane', cr);
  add('volley', vo);
  await roarDone;
  return bank;
}
