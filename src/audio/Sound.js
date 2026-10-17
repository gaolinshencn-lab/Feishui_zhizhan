// Battlefield soundscape (off until the viewer turns it on). Beds of wind, water, fire, marching feet,
// cavalry and massed shouting follow the timeline; war drums play patterns that quicken with the
// fighting; horns, the retreat gong, arrow volleys and cranes mark particular moments, and a deep
// drum stroke opens each time node. Everything is synthesised in the browser (bank.js).

import { buildBank } from './bank.js';

/** Beds that carry on while the timeline is paused; the rest belong to moving armies. */
export const AMBIENT_BEDS = ['wind', 'water', 'fire'];

// Looping beds: [sample, bus, gain at level 1]
const LOOPS = {
  water: ['river', 'amb', 0.45],
  fire: ['fire', 'amb', 0.5],
  march: ['march', 'act', 0.42],
  hooves: ['cavalry', 'act', 0.55],
  roar: ['roar', 'act', 0.45],
};

// Scattered one-shots: events per second at level 1, which samples, bus, gain range, stereo spread,
// pitch spread (and a fixed pitch factor).
const SCATTER = {
  clash: { rate: 12, pick: (b) => (Math.random() < 0.7 ? b.weapons.metal : b.weapons.wood), bus: 'act', gain: [0.08, 0.28], pan: 0.8, detune: 0.12 },
  splash: { rate: 5, pick: (b) => b.splash, bus: 'act', gain: [0.15, 0.45], pan: 0.8, detune: 0.15 },
  oars: { rate: 0.9, pick: (b) => b.splash, bus: 'act', gain: [0.08, 0.16], pan: 0.6, detune: 0.1 },
  stakes: { rate: 2.5, pick: (b) => b.weapons.wood, bus: 'act', gain: [0.3, 0.55], pan: 0.6, detune: 0.2, pitch: 0.8 },
  stones: { rate: 0.25, pick: (b) => b.steps.stone, bus: 'sig', gain: [0.45, 0.65], pan: 0.15, detune: 0.03 },
};

// War-drum patterns, a bar of sixteenths: X accent, x stroke, . rest. The tier follows the level.
const DRUM_TIERS = [
  { from: 0.05, bpm: 72, parts: { big: 'X.......x.......' } },
  { from: 0.4, bpm: 96, parts: { big: 'X...x...X...x...', mid: '......x.......x.' } },
  { from: 0.72, bpm: 126, parts: { big: 'X..xX...X..xX.x.', mid: '..x...x.x.x...x.', small: 'x.xxx.x.x.xxx.xx' } },
];
const DRUM_GAIN = { big: 0.8, mid: 0.55, small: 0.4 };
const DRUM_PAN = { big: 0, mid: -0.35, small: 0.35 };

const MASTER = 0.7;

const rand = (a, b) => a + (b - a) * Math.random();
const pick = (list) => list[Math.floor(Math.random() * list.length)];

export class Sound {
  constructor() {
    this.ctx = null;
    this.enabled = false;
    this.bank = null;
    this.loading = null;
    this.loops = {};
    this.next = {};
    this.drum = { at: 0, step: 0, bar: 0, tier: DRUM_TIERS[0], roll: false };
    this.surge = 0;
    this.t = 0;
    this.lastChapter = -1;
  }

  /** Builds the mixing graph on a new AudioContext, or on `ctx` (an offline one, for tests). */
  ensure(ctx) {
    if (this.ctx) return this.ctx;
    if (!ctx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return null;
      ctx = new AC();
    }
    this.ctx = ctx;
    // master: fade, no sub-bass, a gentle cut of the top end, and a limiter so nothing clips (a
    // limiter only: the compressor node adds make-up gain, and more compression just makes it loud)
    this.master = ctx.createGain();
    this.master.gain.value = 0;
    const limit = ctx.createDynamicsCompressor();
    limit.threshold.value = -3;
    limit.knee.value = 0;
    limit.ratio.value = 20;
    limit.attack.value = 0.001;
    limit.release.value = 0.15;
    this.master.connect(this.filter('highpass', 35, -3)).connect(this.filter('highshelf', 5000, 0, -5)).connect(limit).connect(ctx.destination);
    // dark open-air reverb: the hills and woods answering the battle
    this.reverb = ctx.createConvolver();
    this.reverb.buffer = this.impulse(3);
    const ret = ctx.createGain();
    ret.gain.value = 0.7;
    this.reverb.connect(ret).connect(this.master);
    const bus = (send) => {
      const g = ctx.createGain();
      const s = ctx.createGain();
      s.gain.value = send;
      g.connect(this.master);
      g.connect(s).connect(this.reverb);
      return g;
    };
    this.amb = bus(0.12);
    this.sig = bus(0.5);
    // the fighting is heard through the air: the farther the camera, the duller and quieter
    this.actOut = bus(0.3);
    this.air = this.filter('lowpass', 3000, -3);
    this.act = ctx.createGain();
    this.act.connect(this.air).connect(this.actOut);
    return ctx;
  }

  filter(type, freq, q = 0, gain = 0) {
    const f = this.ctx.createBiquadFilter();
    f.type = type;
    f.frequency.value = freq;
    f.Q.value = q;
    f.gain.value = gain;
    return f;
  }

  impulse(seconds) {
    const ctx = this.ctx;
    const sr = ctx.sampleRate;
    const len = Math.floor(sr * seconds);
    const pre = Math.floor(sr * 0.02);
    const buf = ctx.createBuffer(2, len, sr);
    for (let c = 0; c < 2; c++) {
      const d = buf.getChannelData(c);
      let lp = 0;
      for (let i = pre; i < len; i++) {
        const t = (i - pre) / sr;
        // the tail darkens as it fades: air and foliage swallow the highs first
        const a = Math.exp((-2 * Math.PI * (4500 * Math.exp(-t / 0.5) + 450)) / sr);
        lp = a * lp + (1 - a) * (Math.random() * 2 - 1);
        d[i] = lp * Math.exp(-t / 0.42) * Math.min(1, t / 0.015);
      }
    }
    return buf;
  }

  async setEnabled(v) {
    this.enabled = v;
    const ctx = this.ensure();
    if (!ctx) return false;
    if (ctx.state === 'suspended') await ctx.resume().catch(() => {});
    const now = ctx.currentTime;
    this.master.gain.cancelScheduledValues(now);
    this.master.gain.setTargetAtTime(v ? MASTER : 0, now, 0.4);
    clearTimeout(this.sleep);
    // once faded out, stop the audio thread altogether
    if (!v) this.sleep = setTimeout(() => !this.enabled && ctx.suspend?.(), 2500);
    else this.load();
    return true;
  }

  /** Renders the sample bank (once) and starts the beds. */
  load() {
    if (!this.loading) {
      this.loading = buildBank(this.ctx).then((bank) => {
        this.bank = bank;
        this.startBeds();
        return bank;
      });
    }
    return this.loading;
  }

  startBeds() {
    const ctx = this.ctx;
    // wind: stereo pink noise as a low rumble plus a band that wanders with the gusts
    const w = ctx.createBufferSource();
    w.buffer = this.bank.wind;
    w.loop = true;
    this.windGain = ctx.createGain();
    this.windGain.gain.value = 0;
    this.windBand = this.filter('bandpass', 500, 0.7);
    this.windBandGain = ctx.createGain();
    const lowGain = ctx.createGain();
    lowGain.gain.value = 0.8;
    w.connect(this.filter('lowpass', 230, -3)).connect(lowGain).connect(this.windGain);
    w.connect(this.windBand).connect(this.windBandGain).connect(this.windGain);
    this.windGain.connect(this.amb);
    w.start();
    for (const [key, [sample, bus]] of Object.entries(LOOPS)) {
      this.loops[key] = [this.startLoop(sample, bus, 1)];
    }
    // a second, slower crowd so the shouting never audibly repeats
    this.loops.roar.push(this.startLoop('roar', 'act', 0.93));
  }

  startLoop(sample, bus, rate) {
    const ctx = this.ctx;
    const buf = this.bank[sample];
    const src = ctx.createBufferSource();
    src.buffer = buf;
    src.loop = true;
    src.playbackRate.value = rate;
    const g = ctx.createGain();
    g.gain.value = 0;
    src.connect(g).connect(this[bus]);
    src.start(ctx.currentTime, Math.random() * buf.duration);
    return g;
  }

  play(buf, bus, gain, when, pan = 0, rate = 1) {
    const ctx = this.ctx;
    const s = ctx.createBufferSource();
    s.buffer = buf;
    s.playbackRate.value = rate;
    const g = ctx.createGain();
    g.gain.value = gain;
    let out = s.connect(g);
    if (pan && ctx.createStereoPanner) {
      const p = ctx.createStereoPanner();
      p.pan.value = Math.max(-1, Math.min(1, pan));
      out = out.connect(p);
    }
    out.connect(this[bus]);
    s.start(when);
  }

  /** A deep drum stroke as each time node begins. */
  chapter() {
    if (!this.enabled || !this.ctx) return;
    if (!this.bank) {
      this.load().then(() => this.chapter());
      return;
    }
    const now = this.ctx.currentTime + 0.04;
    if (now - this.lastChapter < 0.5) return; // jumping to a node and pressing play asks twice
    this.lastChapter = now;
    this.play(this.bank.drums.big[0], 'sig', 0.45, now, 0, 0.92);
    this.play(this.bank.drums.mid[0], 'sig', 0.22, now + 0.008, 0, 0.9);
  }

  /** One-off moments on the timeline. */
  cue(name) {
    if (!this.enabled || !this.bank) return;
    const b = this.bank;
    const now = this.ctx.currentTime + 0.03;
    if (name === 'horn') this.play(b.horn, 'sig', 0.55, now, rand(-0.3, 0.3));
    else if (name === 'horns') {
      // answered from the other wing
      this.play(b.horn, 'sig', 0.5, now, -0.35);
      this.play(b.horn2, 'sig', 0.45, now + 0.9, 0.35);
    } else if (name === 'gong') [0, 0.85, 1.7].forEach((d, i) => this.play(b.gong, 'sig', 0.5 - i * 0.06, now + d, 0.1));
    else if (name === 'toll') this.play(b.gong, 'sig', 0.42, now, 0, 0.84);
    else if (name === 'volley') this.play(b.volley, 'act', 0.9, now);
    else if (name === 'surge') this.surge = 1;
    else if (name === 'crane') this.play(pick(b.crane), 'sig', 0.22, now, rand(-0.7, 0.7));
    else if (name === 'snap') this.play(b.steps.snap, 'sig', 0.4, now, 0.1);
  }

  /**
   * Called every frame with the level (0..1) of each bed and how close the camera is to the
   * table (0 far .. 1 near).
   */
  update(dt, levels, near = 0.5) {
    if (!this.enabled || !this.bank) return;
    const now = this.ctx.currentTime;
    this.t += dt;
    this.surge = Math.max(0, this.surge - dt / 3);
    this.air.frequency.setTargetAtTime(1400 * Math.pow(2, 2.2 * near), now, 0.3);
    this.actOut.gain.setTargetAtTime(0.7 + 0.4 * near, now, 0.3);
    // gusts wander slowly
    const t = this.t;
    const g = 0.5 + 0.25 * Math.sin(t * 0.23) + 0.15 * Math.sin(t * 0.61 + 1.3) + 0.1 * Math.sin(t * 1.37 + 0.4);
    this.windGain.gain.setTargetAtTime((levels.wind || 0) * 0.7 * (0.5 + 0.5 * g), now, 0.4);
    this.windBand.frequency.setTargetAtTime(260 + 620 * g, now, 0.6);
    this.windBandGain.gain.setTargetAtTime(0.3 + 0.7 * g * g, now, 0.4);
    for (const [key, [, , mix]] of Object.entries(LOOPS)) {
      let lvl = levels[key] || 0;
      if (key === 'roar') lvl = Math.min(1, lvl + this.surge * 0.6);
      for (const gain of this.loops[key]) gain.gain.setTargetAtTime(lvl * mix, now, 0.5);
    }
    for (const [key, s] of Object.entries(SCATTER)) {
      const lvl = (levels[key] || 0) + (key === 'clash' ? this.surge * 0.5 : 0);
      if (lvl < 0.02) {
        this.next[key] = 0;
        continue;
      }
      if (!this.next[key] || this.next[key] < now) this.next[key] = now + Math.random() / (s.rate * lvl);
      while (this.next[key] < now + 0.12) {
        const gain = rand(s.gain[0], s.gain[1]) * (0.4 + 0.6 * lvl);
        const rate = (s.pitch || 1) * (1 + rand(-0.5, 0.5) * s.detune);
        this.play(pick(s.pick(this.bank)), s.bus, gain, this.next[key], rand(-s.pan, s.pan), rate);
        this.next[key] += -Math.log(1 - Math.random()) / (s.rate * lvl);
      }
    }
    this.drums(now, levels.drums || 0);
  }

  drums(now, level) {
    const d = this.drum;
    if (level < 0.05) {
      d.at = 0;
      return;
    }
    if (d.at < now) {
      d.at = now + 0.05;
      d.step = 0;
    }
    while (d.at < now + 0.15) {
      if (d.step === 0) {
        d.bar++;
        d.tier = DRUM_TIERS.filter((x) => level >= x.from).pop();
        d.roll = level > 0.85 && d.bar % 4 === 0; // every fourth bar the small drums roll
      }
      for (const [part, pat] of Object.entries(d.tier.parts)) {
        const roll = d.roll && part === 'small';
        const c = roll ? 'x' : pat[d.step];
        if (c === '.') continue;
        const vel = roll ? 0.4 + 0.6 * (d.step / 15) : (c === 'X' ? 1 : 0.62) * (0.65 + 0.35 * level);
        this.drumHit(part, vel, d.at + rand(-0.006, 0.006));
      }
      d.at += 60 / d.tier.bpm / 4;
      d.step = (d.step + 1) % 16;
    }
  }

  drumHit(part, vel, when) {
    const [hard, soft] = this.bank.drums[part];
    const buf = vel > 0.8 ? hard : soft;
    const g = DRUM_GAIN[part] * vel * 0.6;
    const p = DRUM_PAN[part];
    // two drummers to a part, a hair apart
    this.play(buf, 'act', g, when, p - 0.2, rand(0.985, 1.015));
    this.play(buf, 'act', g, when + rand(0.004, 0.016), p + 0.2, rand(0.985, 1.015));
  }
}
