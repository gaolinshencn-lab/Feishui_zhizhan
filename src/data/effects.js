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

/**
 * The soundscape. Each bed has windows [t0, t1, level] on the timeline (it fades in just before t0
 * and out just after t1); cues are one-off moments [t, name]. Wind, water and fire carry on while
 * paused, the rest sound only while the armies move.
 */
export const SOUNDSCAPE = {
  beds: {
    wind: [
      [T('prologue', 0), T('converge', 1), 0.3],
      [T('shouyang', 0), T('advance', 0.6), 0.16],
      [T('advance', 0.62), T('standoff', 0.06), 0.5], // 草木皆兵: wind in the grass on 八公山
      [T('standoff', 0.06), T('battle', 1), 0.16],
      [T('rout', 0.04), T('rout', 0.96), 1], // 风声鹤唳
      [T('news', 0), T('news', 1), 0.4],
      [T('epilogue', 0), T('epilogue', 1), 0.45],
    ],
    water: [[T('shouyang', 0), T('rout', 1), 0.35]], // the Huai, the Fei and 洛涧 on the battlefield table
    fire: [
      [T('shouyang', 0.58), T('shouyang', 0.86), 0.7],
      [T('raid', 0), T('raid', 0.44), 0.18], // torches and campfires in the night
      [T('raid', 0.46), T('raid', 1), 0.8], // 梁成's camp burning
    ],
    march: [
      [T('march', 0.05), T('march', 1), 0.85],
      [T('converge', 0), T('converge', 0.85), 0.65],
      [T('shouyang', 0), T('shouyang', 0.5), 0.55],
      [T('blockade', 0), T('blockade', 0.66), 0.45],
      [T('raid', 0.04), T('raid', 0.36), 0.3], // 刘牢之's five thousand close in by night
      [T('advance', 0), T('advance', 0.5), 0.6],
    ],
    hooves: [
      [T('prologue', 0.55), T('prologue', 0.8), 0.3],
      [T('march', 0.3), T('march', 1), 0.5], // 骑二十七万
      [T('envoy', 0.3), T('envoy', 0.72), 0.85], // 苻坚轻骑八千
      [T('battle', 0.4), T('battle', 0.6), 0.45], // 苻融驰骑略陈
      [T('rout', 0), T('rout', 0.72), 0.55],
      [T('news', 0.02), T('news', 0.22), 0.25], // the courier with the dispatch
      [T('epilogue', 0.4), T('epilogue', 0.7), 0.2],
    ],
    drums: [
      [T('prologue', 0.46), T('prologue', 0.78), 0.35],
      [T('march', 0.05), T('march', 1), 0.3],
      [T('converge', 0), T('converge', 0.8), 0.25],
      [T('shouyang', 0.48), T('shouyang', 0.76), 0.65],
      [T('raid', 0.38), T('raid', 0.78), 0.9],
      [T('advance', 0.48), T('advance', 0.72), 0.5],
      [T('standoff', 0.08), T('standoff', 0.95), 0.2],
      [T('battle', 0.22), T('battle', 0.96), 1],
      [T('rout', 0), T('rout', 0.35), 0.55],
      [T('epilogue', 0.35), T('epilogue', 0.7), 0.2],
    ],
    roar: [
      [T('prologue', 0.48), T('prologue', 0.76), 0.25],
      [T('shouyang', 0.5), T('shouyang', 0.76), 0.7],
      [T('raid', 0.4), T('raid', 0.78), 0.9],
      [T('advance', 0.5), T('advance', 0.72), 0.5],
      [T('battle', 0.26), T('battle', 0.95), 1],
      [T('rout', 0), T('rout', 0.55), 0.45],
    ],
    clash: [
      [T('shouyang', 0.55), T('shouyang', 0.74), 0.55],
      [T('raid', 0.42), T('raid', 0.75), 0.8],
      [T('advance', 0.52), T('advance', 0.7), 0.45],
      [T('battle', 0.36), T('battle', 0.8), 1],
      [T('rout', 0), T('rout', 0.3), 0.35],
    ],
    splash: [
      [T('raid', 0.38), T('raid', 0.46), 0.5], // over 洛涧 to the attack
      [T('raid', 0.7), T('raid', 0.95), 0.75], // 争赴淮水
      [T('battle', 0.16), T('battle', 0.42), 0.8], // the eight thousand wade the Fei
      [T('battle', 0.58), T('battle', 0.85), 0.7], // 肥水为之不流
      [T('rout', 0), T('rout', 0.3), 0.4],
    ],
    oars: [
      [T('converge', 0.1), T('converge', 0.8), 0.6],
      [T('shouyang', 0), T('shouyang', 0.55), 0.5],
      [T('blockade', 0.34), T('blockade', 0.66), 0.5],
      [T('advance', 0.5), T('advance', 0.9), 0.4],
    ],
    stakes: [[T('blockade', 0.55), T('blockade', 0.8), 1]], // 栅淮: driving the palisade into the riverbed
    stones: [
      [T('converge', 0.14), T('converge', 0.5), 1], // 谢安与谢玄围棋赌墅
      [T('news', 0.26), T('news', 0.76), 1],
    ],
  },
  cues: [
    [T('prologue', 0.47), 'horn'],
    [T('march', 0.03), 'horns'],
    [T('march', 0.33), 'horns'],
    [T('converge', 0.03), 'horn'],
    [T('shouyang', 0.47), 'horns'],
    [T('shouyang', 0.53), 'volley'],
    [T('shouyang', 0.72), 'surge'], // 寿阳陷
    [T('blockade', 0.6), 'horn'],
    [T('envoy', 0.42), 'horn'],
    [T('raid', 0.38), 'surge'], // the night attack breaks on 梁成's camp
    [T('raid', 0.44), 'volley'],
    [T('advance', 0.47), 'horns'],
    [T('standoff', 0.1), 'horn'],
    [T('standoff', 0.32), 'horns'],
    [T('battle', 0.05), 'gong'], // 麾兵使却: the Qin line is signalled to pull back
    [T('battle', 0.3), 'surge'], // 朱序大呼“秦兵败矣”
    [T('battle', 0.4), 'volley'],
    [T('battle', 0.62), 'volley'], // 苻坚中流矢
    [T('rout', 0.16), 'crane'],
    [T('rout', 0.33), 'crane'],
    [T('rout', 0.52), 'crane'],
    [T('rout', 0.7), 'crane'],
    [T('news', 0.74), 'snap'], // 不觉屐齿之折
    [T('epilogue', 0.42), 'horn'],
    [T('epilogue', 0.74), 'toll'], // 苻坚死于新平
  ],
};
