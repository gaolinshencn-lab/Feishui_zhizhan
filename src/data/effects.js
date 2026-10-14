import { T } from './episodes.js';

// Atmospheric effects. Emitters are evaluated against the timeline; particles themselves
// live in real time so scrubbing simply starts or stops the smoke.

export const TACTICAL_FX = {
  emitters: [
    { kind: 'smoke', at: [116.786, 32.5775], radius: 1.0, rate: 16, t0: T('shouyang', 0.5), t1: T('shouyang', 0.8) },
    { kind: 'fire', at: [116.786, 32.5775], radius: 0.7, rate: 10, t0: T('shouyang', 0.58), t1: T('shouyang', 0.76) },
    { kind: 'dust', at: [116.838, 32.587], radius: 0.6, rate: 14, t0: T('advance', 0.5), t1: T('advance', 0.7) },
    { kind: 'fire', at: [117.116, 32.737], radius: 0.75, rate: 34, t0: T('raid', 0.46), t1: T('raid', 0.98) },
    { kind: 'smoke', at: [117.116, 32.737], radius: 0.8, rate: 18, t0: T('raid', 0.46), t1: T('advance', 0.25) },
    { kind: 'dust', at: [117.126, 32.728], radius: 0.5, rate: 12, t0: T('raid', 0.4), t1: T('raid', 0.7) },
    { kind: 'dust', at: [116.785, 32.587], radius: 1.4, rate: 26, t0: T('battle', 0.32), t1: T('battle', 0.92) },
    { kind: 'smoke', at: [116.78, 32.584], radius: 1.0, rate: 8, t0: T('battle', 0.4), t1: T('rout', 0.3) },
    { kind: 'dust', at: [116.72, 32.565], radius: 2.4, rate: 20, t0: T('rout', 0.02), t1: T('rout', 0.7) },
    { kind: 'dust', at: [116.69, 32.598], radius: 1.4, rate: 10, t0: T('rout', 0.05), t1: T('rout', 0.55) },
  ],
  torches: { units: ['q_liang', 'j_liu', 'j_liu_det', 'j_xieshi', 'j_xiexuan', 'j_xieyan', 'j_huanyi'], t0: T('raid', 0.0), t1: T('raid', 1.0), every: 7 },
  campfires: [
    { at: [117.222, 32.702], n: 9, radius: 0.6, t0: T('raid', 0.0), t1: T('raid', 1.0) },
    { at: [117.116, 32.737], n: 7, radius: 0.5, t0: T('raid', 0.0), t1: T('raid', 0.5) },
  ],
  ghosts: { bbox: [116.765, 32.603, 116.86, 32.665], n: 260, t0: T('advance', 0.62), t1: T('standoff', 0.06) },
  gaze: { from: [116.786, 32.587], to: [[116.775, 32.632], [116.835, 32.622]], t0: T('advance', 0.66), t1: T('advance', 1.0) },
  cranes: { flocks: [[[116.86, 32.53], [116.62, 32.63]], [[116.82, 32.50], [116.58, 32.58]], [[116.80, 32.60], [116.56, 32.68]]], n: 11, t0: T('rout', 0.08), t1: T('rout', 0.9), height: 2.2 },
  wind: { at: [116.70, 32.575], radius: 6, n: 70, t0: T('rout', 0.1), t1: T('rout', 0.85) },
  riverTint: { at: [116.776, 32.5925], radius: 2.4, keys: [[T('battle', 0.42), 0], [T('battle', 0.7), 1], [T('rout', 0.4), 0.75], [T('rout', 0.9), 0.25]] },
};

export const STRATEGIC_FX = {
  emitters: [
    { kind: 'smoke', at: [112.14, 31.95], radius: 1.4, rate: 6, scale: 6, t0: T('prologue', 0.5), t1: T('prologue', 0.72) },
    { kind: 'dust', at: [110.3, 34.6], radius: 2.2, rate: 6, scale: 6, t0: T('march', 0.35), t1: T('converge', 0.3) },
    { kind: 'smoke', at: [116.786, 32.5775], radius: 2.5, rate: 8, scale: 6, t0: T('converge', 0.85), t1: T('converge', 1) },
  ],
};

/** Visibility windows for scheduled scenery on the battlefield table. */
export const TACTICAL_PROPS = {
  jincamp: [T('blockade', 0.6), T('advance', 0.4)],
  liangcamp: [T('blockade', 0.5), T('raid', 0.75)],
  qincamp_w: [T('shouyang', 0.9), T('rout', 0.3)],
  qincamp_s: [T('shouyang', 0.9), T('rout', 0.3)],
  palisade: [T('blockade', 0.55), T('raid', 0.8)],
};
