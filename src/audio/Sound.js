// Small synthesised soundscape (off until the viewer turns it on): plucked-string phrases in a
// pentatonic mode at each time node, war drums under battles, wind for 风声鹤唳, crickets at night.
// Everything is generated with Web Audio; no audio files are shipped.

const PENTA = [146.83, 164.81, 185.0, 220.0, 246.94, 293.66, 329.63, 369.99, 440.0, 493.88]; // D E F# A B (宫商角徵羽)

export class Sound {
  constructor() {
    this.ctx = null;
    this.enabled = false;
    this.windLevel = 0;
    this.drumLevel = 0;
    this.nextDrum = 0;
  }

  ensure() {
    if (this.ctx) return this.ctx;
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return null;
    const ctx = new AC();
    this.ctx = ctx;
    this.master = ctx.createGain();
    this.master.gain.value = 0;
    const comp = ctx.createDynamicsCompressor();
    comp.threshold.value = -18;
    comp.ratio.value = 3;
    this.master.connect(comp).connect(ctx.destination);
    // a gentle hall
    this.reverb = ctx.createConvolver();
    this.reverb.buffer = this.impulse(2.6);
    const wet = ctx.createGain();
    wet.gain.value = 0.28;
    this.reverb.connect(wet).connect(this.master);
    this.dry = ctx.createGain();
    this.dry.connect(this.master);
    this.dry.connect(this.reverb);
    // wind bed: looping noise through a moving band-pass
    const noise = ctx.createBufferSource();
    noise.buffer = this.noiseBuffer(4);
    noise.loop = true;
    this.windFilter = ctx.createBiquadFilter();
    this.windFilter.type = 'bandpass';
    this.windFilter.frequency.value = 500;
    this.windFilter.Q.value = 0.8;
    this.windGain = ctx.createGain();
    this.windGain.gain.value = 0;
    noise.connect(this.windFilter).connect(this.windGain).connect(this.dry);
    noise.start();
    return ctx;
  }

  impulse(seconds) {
    const ctx = this.ctx;
    const len = Math.floor(ctx.sampleRate * seconds);
    const buf = ctx.createBuffer(2, len, ctx.sampleRate);
    for (let c = 0; c < 2; c++) {
      const d = buf.getChannelData(c);
      for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len, 2.6);
    }
    return buf;
  }

  noiseBuffer(seconds) {
    const ctx = this.ctx;
    const len = Math.floor(ctx.sampleRate * seconds);
    const buf = ctx.createBuffer(1, len, ctx.sampleRate);
    const d = buf.getChannelData(0);
    let b = 0;
    for (let i = 0; i < len; i++) {
      b = 0.97 * b + 0.03 * (Math.random() * 2 - 1);
      d[i] = b * 6;
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
    this.master.gain.setTargetAtTime(v ? 0.9 : 0, now, 0.4);
    return true;
  }

  /** Karplus–Strong style pluck built from a delay loop. */
  pluck(freq, when, gain = 0.5, decay = 0.985) {
    const ctx = this.ctx;
    const burst = ctx.createBufferSource();
    const len = Math.floor(ctx.sampleRate / freq);
    const buf = ctx.createBuffer(1, len * 2, ctx.sampleRate);
    const d = buf.getChannelData(0);
    for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * (1 - i / len);
    burst.buffer = buf;
    const delay = ctx.createDelay(1);
    delay.delayTime.value = 1 / freq;
    const fb = ctx.createGain();
    fb.gain.value = decay;
    const lp = ctx.createBiquadFilter();
    lp.type = 'lowpass';
    lp.frequency.value = Math.min(5200, freq * 9);
    const out = ctx.createGain();
    out.gain.setValueAtTime(gain, when);
    out.gain.exponentialRampToValueAtTime(0.0001, when + 4.2);
    burst.connect(delay);
    delay.connect(lp).connect(fb).connect(delay);
    lp.connect(out).connect(this.dry);
    burst.start(when);
    burst.stop(when + 0.1);
    setTimeout(() => {
      out.disconnect();
      fb.disconnect();
      lp.disconnect();
      delay.disconnect();
    }, (when - ctx.currentTime + 4.5) * 1000);
  }

  drum(when, gain = 0.8) {
    const ctx = this.ctx;
    const o = ctx.createOscillator();
    o.type = 'sine';
    o.frequency.setValueAtTime(78, when);
    o.frequency.exponentialRampToValueAtTime(42, when + 0.35);
    const g = ctx.createGain();
    g.gain.setValueAtTime(0.0001, when);
    g.gain.exponentialRampToValueAtTime(gain, when + 0.01);
    g.gain.exponentialRampToValueAtTime(0.0001, when + 0.9);
    o.connect(g).connect(this.dry);
    o.start(when);
    o.stop(when + 1);
    const n = ctx.createBufferSource();
    n.buffer = this.noiseBuffer(0.2);
    const f = ctx.createBiquadFilter();
    f.type = 'lowpass';
    f.frequency.value = 900;
    const ng = ctx.createGain();
    ng.gain.setValueAtTime(gain * 0.5, when);
    ng.gain.exponentialRampToValueAtTime(0.0001, when + 0.18);
    n.connect(f).connect(ng).connect(this.dry);
    n.start(when);
  }

  /** A short phrase when a new time node begins; brighter for victories, lower for the epilogue. */
  phrase(index) {
    if (!this.enabled || !this.ctx) return;
    const t0 = this.ctx.currentTime + 0.05;
    const base = [0, 2, 3, 1, 3, 1, 4, 2, 1, 5, 4, 2, 0][index % 13];
    const steps = [0, 2, 1, 3, 4];
    steps.forEach((s, i) => this.pluck(PENTA[(base + s) % PENTA.length], t0 + i * 0.32 + (i === 4 ? 0.2 : 0), i === 0 ? 0.55 : 0.36));
  }

  /** Called every frame with the battle intensity (0..1) and wind (0..1). */
  update(dt, { drums = 0, wind = 0 }) {
    if (!this.enabled || !this.ctx) return;
    const ctx = this.ctx;
    const now = ctx.currentTime;
    this.windLevel += (wind - this.windLevel) * Math.min(1, dt * 1.5);
    this.windGain.gain.setTargetAtTime(this.windLevel * 0.22, now, 0.3);
    this.windFilter.frequency.setTargetAtTime(380 + 420 * Math.sin(now * 0.37) ** 2, now, 0.5);
    if (drums > 0.05 && now >= this.nextDrum) {
      const g = 0.35 + drums * 0.5;
      this.drum(now + 0.02, g);
      if (Math.random() < 0.6) this.drum(now + 0.24, g * 0.7);
      this.nextDrum = now + 1.1 - drums * 0.45 + Math.random() * 0.3;
    }
  }
}
