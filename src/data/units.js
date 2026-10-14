import { T } from './episodes.js';

// Movement scripts. Each key: t (global timeline), at [lon,lat] or place id, via (waypoints,
// may include { river, from, to } to follow a river), form (line | block | deep | column |
// camp | siege | rout | hidden), face (deg, 0 = north, or a place id to face), n (strength
// fraction remaining; drops are rendered as fallen figures), vanish (losses taken prisoner).
// Positions not fixed by the sources (camp layouts, approach roads) are reasoned estimates.

const SHOU = 'shouyang';
const huai = (from, to) => ({ river: 'huai', from, to });

// ---------------------------------------------------------------------------
// Battlefield (战役沙盘)
// ---------------------------------------------------------------------------
export const TACTICAL_UNITS = [
  // ===================== 前秦 =====================
  {
    id: 'q_rong', side: 'qin', name: '苻融', label: '苻融 · 前锋主力', strength: '前锋诸军', banner: '苻融',
    kind: 'mixed', figures: 380, cav: 0.25,
    track: [
      { t: T('shouyang', 0.0), at: [116.497, 32.527], form: 'block', face: 125 },
      { t: T('shouyang', 0.1), at: [116.497, 32.527], form: 'block', face: 125 },
      { t: T('shouyang', 0.48), at: [116.742, 32.570], via: [[116.512, 32.514], [116.532, 32.500], [116.575, 32.506], [116.630, 32.528], [116.690, 32.552]], form: 'deep', face: 85 },
      { t: T('shouyang', 0.62), at: [116.742, 32.570], form: 'siege', target: SHOU, radius: 1.9, arc: [200, 350], ranks: 3 },
      { t: T('shouyang', 0.72), at: [116.742, 32.570], form: 'siege', target: SHOU, radius: 1.5, arc: [200, 350], ranks: 3, n: 0.94 },
      { t: T('shouyang', 0.92), at: [116.752, 32.567], form: 'camp', face: 60 },
      { t: T('advance', 0.55), at: [116.752, 32.567], form: 'camp', face: 60 },
      { t: T('advance', 0.9), at: [116.778, 32.5885], form: 'line', face: 15 },
      { t: T('battle', 0.06), at: [116.778, 32.5885], form: 'line', face: 15 },
      { t: T('battle', 0.3), at: [116.775, 32.5815], form: 'line', face: 15, loose: 2.2, n: 0.92 },
      { t: T('rout', 0.85), at: [116.655, 32.528], via: [[116.752, 32.574], [116.715, 32.561], [116.685, 32.546]], form: 'rout', spread: 1.25, n: 0.3 },
    ],
  },
  {
    id: 'q_zhanghao', side: 'qin', name: '张蚝', label: '张蚝', strength: '骁将', banner: '张',
    kind: 'mixed', figures: 170, cav: 0.35,
    track: [
      { t: T('shouyang', 0.9), at: [116.808, 32.568], form: 'hidden' },
      { t: T('shouyang', 0.98), at: [116.808, 32.568], form: 'camp', face: 60 },
      { t: T('advance', 0.36), at: [116.808, 32.568], form: 'camp', face: 60 },
      { t: T('advance', 0.5), at: [116.833, 32.582], via: [[116.820, 32.574]], form: 'line', face: 50 },
      { t: T('advance', 0.66), at: [116.838, 32.588], form: 'line', face: 40, n: 0.95 },
      { t: T('advance', 0.85), at: [116.812, 32.5872], via: [[116.825, 32.586]], form: 'line', face: 20 },
      { t: T('battle', 0.1), at: [116.812, 32.5872], form: 'line', face: 20 },
      { t: T('battle', 0.32), at: [116.815, 32.5905], form: 'line', face: 35, n: 0.86 },
      { t: T('rout', 0.7), at: [116.70, 32.548], via: [[116.808, 32.574], [116.775, 32.562], [116.735, 32.556]], form: 'rout', spread: 1.1, n: 0.35 },
    ],
  },
  {
    id: 'q_cav', side: 'qin', name: '铁骑', label: '秦军铁骑', strength: '“以铁骑蹙而杀之”', banner: '秦',
    kind: 'cav', figures: 150,
    track: [
      { t: T('shouyang', 0.9), at: [116.736, 32.580], form: 'hidden' },
      { t: T('shouyang', 0.98), at: [116.736, 32.580], form: 'camp', face: 80 },
      { t: T('standoff', 0.15), at: [116.736, 32.580], form: 'camp', face: 80 },
      { t: T('standoff', 0.55), at: [116.758, 32.584], form: 'block', face: 30 },
      { t: T('battle', 0.08), at: [116.758, 32.584], form: 'block', face: 30 },
      { t: T('battle', 0.3), at: [116.752, 32.577], form: 'block', face: 30, loose: 1.8 },
      { t: T('rout', 0.55), at: [116.62, 32.585], via: [[116.735, 32.575], [116.70, 32.588], [116.66, 32.59]], form: 'rout', spread: 1.4, n: 0.5 },
    ],
  },
  {
    id: 'q_fujian', side: 'qin', name: '苻坚', label: '苻坚 · 轻骑', strength: '八千骑', banner: '苻坚', bannerStyle: 'imperial',
    kind: 'cav', figures: 70, bannerSize: 1.25,
    track: [
      { t: T('envoy', 0.2), at: [116.425, 32.625], form: 'hidden', face: 135 },
      { t: T('envoy', 0.24), at: [116.425, 32.625], form: 'column', face: 135 },
      { t: T('envoy', 0.6), at: [116.772, 32.574], via: [[116.47, 32.585], [116.505, 32.523], [116.53, 32.503], [116.58, 32.508], [116.64, 32.532], [116.71, 32.558]], form: 'camp', face: 20 },
      { t: T('advance', 0.6), at: [116.772, 32.574], form: 'camp', face: 20 },
      { t: T('advance', 0.75), at: [116.784, 32.581], form: 'block', face: 0 },
      { t: T('battle', 0.3), at: [116.784, 32.581], form: 'block', face: 0 },
      { t: T('battle', 0.62), at: [116.774, 32.577], form: 'block', face: 0, n: 0.8, loose: 2 },
      { t: T('rout', 0.5), at: [116.58, 32.66], via: [[116.74, 32.585], [116.70, 32.60], [116.64, 32.635]], form: 'rout', spread: 1.2, n: 0.1 },
    ],
  },
  {
    id: 'q_fujian_alone', side: 'qin', name: '苻坚', label: '苻坚单骑走淮北', strength: '中流矢', banner: '苻坚', bannerStyle: 'imperial',
    kind: 'cav', figures: 1, bannerSize: 0.9,
    track: [
      { t: T('rout', 0.08), at: [116.765, 32.578], form: 'hidden' },
      { t: T('rout', 0.12), at: [116.765, 32.578], form: 'block', face: 300 },
      { t: T('rout', 0.7), at: [116.43, 32.735], via: [[116.725, 32.592], [116.695, 32.606], [116.64, 32.64], [116.55, 32.69]], form: 'block', face: 300, ease: 'linear' },
      { t: T('rout', 0.74), at: [116.43, 32.735], form: 'hidden' },
    ],
  },
  {
    id: 'q_liang', side: 'qin', name: '梁成', label: '梁成 · 屯洛涧', strength: '众五万', banner: '梁成',
    kind: 'mixed', figures: 320, cav: 0.22,
    track: [
      { t: T('blockade', 0.0), at: [116.815, 32.575], form: 'hidden' },
      { t: T('blockade', 0.06), at: [116.815, 32.575], form: 'block', face: 70 },
      { t: T('blockade', 0.56), at: [117.117, 32.736], via: [[116.84, 32.588], [116.875, 32.603], [116.925, 32.618], [116.975, 32.636], [117.015, 32.655], [117.055, 32.673], [117.088, 32.695], [117.105, 32.718]], form: 'camp', face: 60 },
      { t: T('raid', 0.2), at: [117.117, 32.736], form: 'camp', face: 60 },
      { t: T('raid', 0.36), at: [117.124, 32.7285], form: 'line', face: 62 },
      { t: T('raid', 0.5), at: [117.124, 32.7285], form: 'line', face: 62, n: 0.86 },
      { t: T('raid', 0.92), at: [117.083, 32.768], via: [[117.11, 32.748], [117.095, 32.76]], form: 'rout', spread: 0.9, n: 0.52, speed: 1.15 },
      { t: T('advance', 0.15), at: [117.083, 32.768], form: 'rout', n: 0.5 },
      { t: T('advance', 0.2), at: [117.083, 32.768], form: 'hidden' },
    ],
  },
  {
    id: 'q_xiashi', side: 'qin', name: '围硖石', label: '秦军围硖石', strength: '苻融别部', banner: '秦',
    kind: 'inf', figures: 170,
    track: [
      { t: T('shouyang', 0.74), at: [116.776, 32.586], form: 'hidden' },
      { t: T('shouyang', 0.78), at: [116.776, 32.586], form: 'column', face: 340 },
      { t: T('shouyang', 0.99), at: [116.751, 32.682], via: [[116.762, 32.603], [116.752, 32.628], [116.749, 32.655]], form: 'siege', target: 'xiashi', radius: 1.25, arc: [120, 235], ranks: 3 },
      { t: T('advance', 0.36), at: [116.751, 32.682], form: 'siege', target: 'xiashi', radius: 1.25, arc: [120, 235], ranks: 3 },
      { t: T('advance', 0.75), at: [116.757, 32.5965], via: [[116.752, 32.655], [116.756, 32.625], [116.758, 32.605]], form: 'line', face: 20 },
      { t: T('battle', 0.1), at: [116.757, 32.5965], form: 'line', face: 20 },
      { t: T('battle', 0.32), at: [116.752, 32.59], form: 'line', face: 20, loose: 2, n: 0.9 },
      { t: T('rout', 0.6), at: [116.695, 32.598], via: [[116.735, 32.592], [116.712, 32.596]], form: 'rout', spread: 1.2, n: 0.3 },
    ],
  },
  {
    id: 'q_garrison', side: 'qin', name: '郭褒', label: '寿阳守军', strength: '淮南太守郭褒', banner: '郭',
    kind: 'inf', figures: 70, bannerSize: 0.8,
    track: [
      { t: T('shouyang', 0.8), at: [116.787, 32.578], form: 'hidden' },
      { t: T('shouyang', 0.86), at: [116.787, 32.578], form: 'camp', face: 0 },
      { t: T('rout', 0.45), at: [116.787, 32.578], form: 'camp', face: 0 },
      { t: T('rout', 0.62), at: [116.787, 32.578], form: 'camp', face: 0, n: 0, vanish: true },
    ],
  },
  {
    id: 'q_zhuxu', side: 'qin', name: '朱序', label: '朱序', strength: '原晋襄阳守将', banner: '朱',
    kind: 'inf', figures: 10, bannerSize: 0.75, bannerStyle: 'neutral',
    track: [
      { t: T('envoy', 0.56), at: [116.79, 32.583], form: 'hidden' },
      { t: T('envoy', 0.6), at: [116.79, 32.583], form: 'column', face: 70 },
      { t: T('envoy', 0.86), at: [117.205, 32.703], via: [[116.84, 32.590], [116.90, 32.612], [116.98, 32.640], [117.05, 32.672], [117.12, 32.708], [117.17, 32.706]], form: 'block', face: 90, ease: 'linear' },
      { t: T('envoy', 0.97), at: [117.205, 32.703], form: 'hidden' },
      { t: T('battle', 0.14), at: [116.770, 32.5765], form: 'hidden' },
      { t: T('battle', 0.18), at: [116.770, 32.5765], form: 'block', face: 0 },
      { t: T('rout', 0.3), at: [116.79, 32.598], via: [[116.778, 32.584]], form: 'block', face: 0 },
      { t: T('rout', 0.35), at: [116.79, 32.598], form: 'hidden' },
    ],
  },

  // ===================== 东晋 =====================
  {
    id: 'j_hubin', side: 'jin', name: '胡彬', label: '胡彬 · 水军', strength: '五千', banner: '胡',
    kind: 'navy', boats: 10,
    track: [
      { t: T('shouyang', 0.0), at: [116.880, 32.643], form: 'boats' },
      { t: T('shouyang', 0.55), at: [116.7398, 32.640], via: [huai([116.880, 32.643], [116.7398, 32.640])], form: 'boats', downstream: false },
      { t: T('shouyang', 0.72), at: [116.7398, 32.640], form: 'boats' },
      { t: T('shouyang', 0.95), at: [116.734, 32.693], via: [huai([116.7398, 32.640], [116.734, 32.693])], form: 'boats', downstream: true },
      { t: T('advance', 0.5), at: [116.734, 32.693], form: 'boats', n: 0.9 },
      { t: T('advance', 0.9), at: [116.7425, 32.630], via: [huai([116.734, 32.693], [116.7425, 32.630])], form: 'boats', downstream: false },
    ],
  },
  {
    id: 'j_hubin_fort', side: 'jin', name: '胡彬', label: '硖石守军', strength: '粮尽', banner: '胡', bannerSize: 0.8,
    kind: 'inf', figures: 40,
    track: [
      { t: T('shouyang', 0.9), at: [116.739, 32.6995], form: 'hidden' },
      { t: T('shouyang', 0.96), at: [116.739, 32.6995], form: 'camp', face: 180 },
      { t: T('advance', 0.5), at: [116.739, 32.6995], form: 'camp', face: 180, n: 0.85 },
      { t: T('advance', 0.8), at: [116.741, 32.6995], form: 'camp', face: 180 },
    ],
  },
  {
    id: 'j_xieshi', side: 'jin', name: '谢石', label: '谢石 · 征讨大都督', strength: '北府诸军', banner: '谢石',
    kind: 'mixed', figures: 260, cav: 0.15, bannerSize: 1.15,
    track: [
      { t: T('blockade', 0.25), at: [117.30, 32.682], form: 'hidden' },
      { t: T('blockade', 0.3), at: [117.30, 32.682], form: 'column', face: 280 },
      { t: T('blockade', 0.62), at: [117.226, 32.700], via: [[117.27, 32.688]], form: 'camp', face: 280 },
      { t: T('advance', 0.02), at: [117.226, 32.700], form: 'camp', face: 280 },
      { t: T('advance', 0.44), at: [116.842, 32.603], via: [[117.19, 32.705], [117.155, 32.713], [117.13, 32.708], [117.09, 32.693], [117.045, 32.674], [117.0, 32.656], [116.95, 32.634], [116.90, 32.614], [116.862, 32.606]], form: 'line', face: 215 },
      { t: T('advance', 0.6), at: [116.846, 32.607], form: 'line', face: 215, n: 0.96 },
      { t: T('battle', 0.12), at: [116.846, 32.607], form: 'line', face: 215 },
      { t: T('battle', 0.3), at: [116.849, 32.610], form: 'line', face: 215, n: 0.93 },
      { t: T('battle', 0.62), at: [116.822, 32.589], via: [[116.835, 32.598]], form: 'line', face: 225 },
      { t: T('rout', 0.55), at: [116.792, 32.578], via: [[116.81, 32.583]], form: 'camp', face: 250 },
    ],
  },
  {
    id: 'j_xiexuan', side: 'jin', name: '谢玄', label: '谢玄 · 前锋都督', strength: '北府精锐', banner: '谢玄',
    kind: 'mixed', figures: 210, cav: 0.12, bannerSize: 1.15,
    track: [
      { t: T('blockade', 0.25), at: [117.30, 32.700], form: 'hidden' },
      { t: T('blockade', 0.3), at: [117.30, 32.700], form: 'column', face: 280 },
      { t: T('blockade', 0.62), at: [117.214, 32.707], via: [[117.26, 32.704]], form: 'camp', face: 280 },
      { t: T('advance', 0.06), at: [117.214, 32.707], form: 'camp', face: 280 },
      { t: T('advance', 0.52), at: [116.792, 32.6005], via: [[117.18, 32.71], [117.15, 32.715], [117.12, 32.705], [117.08, 32.69], [117.035, 32.67], [116.99, 32.652], [116.94, 32.63], [116.89, 32.612], [116.845, 32.606], [116.81, 32.602]], form: 'line', face: 192 },
      { t: T('battle', 0.16), at: [116.792, 32.6005], form: 'line', face: 192 },
      { t: T('battle', 0.4), at: [116.787, 32.5868], via: [[116.79, 32.5945], [116.788, 32.590]], form: 'line', face: 195, smooth: false },
      { t: T('battle', 0.62), at: [116.782, 32.5815], form: 'line', face: 200, n: 0.94 },
      { t: T('rout', 0.72), at: [116.646, 32.525], via: [[116.76, 32.572], [116.72, 32.558], [116.685, 32.541]], form: 'line', face: 240 },
    ],
  },
  {
    id: 'j_xieyan', side: 'jin', name: '谢琰', label: '谢琰', strength: '辅国将军', banner: '谢琰',
    kind: 'inf', figures: 130,
    track: [
      { t: T('blockade', 0.3), at: [117.30, 32.712], form: 'hidden' },
      { t: T('blockade', 0.35), at: [117.30, 32.712], form: 'column', face: 280 },
      { t: T('blockade', 0.66), at: [117.232, 32.712], via: [[117.27, 32.712]], form: 'camp', face: 280 },
      { t: T('advance', 0.1), at: [117.232, 32.712], form: 'camp', face: 280 },
      { t: T('advance', 0.58), at: [116.770, 32.6045], via: [[117.19, 32.712], [117.15, 32.716], [117.12, 32.706], [117.08, 32.691], [117.03, 32.669], [116.985, 32.65], [116.935, 32.628], [116.885, 32.611], [116.835, 32.607], [116.80, 32.606]], form: 'line', face: 195 },
      { t: T('battle', 0.18), at: [116.770, 32.6045], form: 'line', face: 195 },
      { t: T('battle', 0.42), at: [116.767, 32.5915], via: [[116.769, 32.599], [116.768, 32.595]], form: 'line', face: 200, smooth: false },
      { t: T('battle', 0.66), at: [116.760, 32.585], form: 'line', face: 215, n: 0.94 },
      { t: T('rout', 0.6), at: [116.70, 32.578], via: [[116.74, 32.583]], form: 'line', face: 260 },
    ],
  },
  {
    id: 'j_huanyi', side: 'jin', name: '桓伊', label: '桓伊', strength: '西中郎将', banner: '桓伊',
    kind: 'inf', figures: 130,
    track: [
      { t: T('blockade', 0.3), at: [117.30, 32.690], form: 'hidden' },
      { t: T('blockade', 0.35), at: [117.30, 32.690], form: 'column', face: 280 },
      { t: T('blockade', 0.66), at: [117.236, 32.693], via: [[117.27, 32.69]], form: 'camp', face: 280 },
      { t: T('advance', 0.08), at: [117.236, 32.693], form: 'camp', face: 280 },
      { t: T('advance', 0.56), at: [116.812, 32.5995], via: [[117.19, 32.703], [117.15, 32.712], [117.12, 32.704], [117.08, 32.689], [117.04, 32.671], [116.995, 32.652], [116.945, 32.631], [116.895, 32.612], [116.85, 32.605]], form: 'line', face: 200 },
      { t: T('battle', 0.2), at: [116.812, 32.5995], form: 'line', face: 200 },
      { t: T('battle', 0.44), at: [116.805, 32.5872], via: [[116.809, 32.5945], [116.807, 32.5905]], form: 'line', face: 205, smooth: false },
      { t: T('battle', 0.68), at: [116.798, 32.580], form: 'line', face: 215, n: 0.95 },
      { t: T('rout', 0.5), at: [116.787, 32.570], form: 'line', face: 250 },
    ],
  },
  {
    id: 'j_liu', side: 'jin', name: '刘牢之', label: '刘牢之 · 广陵相', strength: '精兵五千', banner: '刘',
    kind: 'inf', figures: 150,
    track: [
      { t: T('blockade', 0.3), at: [117.30, 32.676], form: 'hidden' },
      { t: T('blockade', 0.35), at: [117.30, 32.676], form: 'column', face: 280 },
      { t: T('blockade', 0.66), at: [117.222, 32.690], via: [[117.27, 32.682]], form: 'camp', face: 280 },
      { t: T('raid', 0.04), at: [117.222, 32.690], form: 'camp', face: 280 },
      { t: T('raid', 0.3), at: [117.153, 32.7155], via: [[117.20, 32.70], [117.175, 32.71]], form: 'line', face: 292 },
      { t: T('raid', 0.42), at: [117.132, 32.7235], via: [[117.143, 32.7195]], form: 'line', face: 292, smooth: false, n: 0.97 },
      { t: T('raid', 0.62), at: [117.115, 32.736], form: 'line', face: 300, n: 0.94 },
      { t: T('raid', 0.88), at: [117.098, 32.752], form: 'line', face: 315 },
      { t: T('advance', 0.12), at: [117.098, 32.752], form: 'line', face: 315 },
      { t: T('advance', 0.62), at: [116.855, 32.6105], via: [[117.09, 32.735], [117.07, 32.70], [117.03, 32.672], [116.98, 32.652], [116.93, 32.63], [116.885, 32.614]], form: 'block', face: 225 },
      { t: T('battle', 0.5), at: [116.855, 32.6105], form: 'block', face: 225 },
      { t: T('rout', 0.6), at: [116.81, 32.588], via: [[116.84, 32.598]], form: 'block', face: 240 },
    ],
  },
  {
    id: 'j_liu_det', side: 'jin', name: '刘牢之', label: '刘牢之别部', strength: '', minor: true, banner: '刘', bannerSize: 0.75,
    kind: 'inf', figures: 50,
    track: [
      { t: T('raid', 0.3), at: [117.153, 32.7155], form: 'hidden' },
      { t: T('raid', 0.36), at: [117.153, 32.7155], form: 'column', face: 330 },
      { t: T('raid', 0.62), at: [117.088, 32.774], via: [[117.14, 32.735], [117.118, 32.758], [117.10, 32.772]], form: 'line', face: 215 },
      { t: T('advance', 0.15), at: [117.088, 32.774], form: 'line', face: 215 },
      { t: T('advance', 0.2), at: [117.088, 32.774], form: 'hidden' },
    ],
  },
  {
    id: 'j_navy', side: 'jin', name: '晋水军', label: '晋军舟师', strength: '水陆继进', banner: '晋',
    kind: 'navy', boats: 14,
    track: [
      { t: T('blockade', 0.3), at: [117.104, 32.818], form: 'hidden' },
      { t: T('blockade', 0.34), at: [117.104, 32.818], form: 'boats' },
      { t: T('blockade', 0.66), at: [117.1016, 32.7965], via: [huai([117.104, 32.818], [117.1016, 32.7965])], form: 'boats', downstream: false },
      { t: T('advance', 0.0), at: [117.1016, 32.7965], form: 'boats' },
      { t: T('advance', 0.72), at: [116.7427, 32.6331], via: [huai([117.1016, 32.7965], [116.7427, 32.6331])], form: 'boats', downstream: false, ease: 'linear' },
    ],
  },
];

// ---------------------------------------------------------------------------
// Strategic overview (战略全局)
// ---------------------------------------------------------------------------
export const STRATEGIC_UNITS = [
  {
    id: 's_fujian', side: 'qin', name: '苻坚', label: '苻坚 · 主力', strength: '戎卒六十余万 骑二十七万', banner: '苻坚', bannerStyle: 'imperial',
    kind: 'mixed', figures: 46, cav: 0.32, bannerSize: 1.2,
    track: [
      { t: T('prologue', 0.0), at: 'changan', form: 'camp', face: 90 },
      { t: T('march', 0.3), at: 'changan', form: 'camp', face: 90 },
      { t: T('converge', 0.38), at: 'xiangcheng', via: ['tongguan', [111.3, 34.66], 'luoyang', [113.3, 34.45], [113.95, 34.05], [114.6, 33.68]], form: 'camp', face: 120, ease: 'linear' },
      { t: T('news', 0.0), at: 'xiangcheng', form: 'camp', face: 120 },
      { t: T('news', 0.28), at: 'xiangcheng', form: 'camp', face: 120, n: 0.4, vanish: true },
      { t: T('news', 0.6), at: 'luoyang', via: [[114.6, 33.7], [113.9, 34.1], [113.3, 34.45]], form: 'column', face: 290 },
      { t: T('news', 0.95), at: 'changan', via: [[111.3, 34.66], 'tongguan'], form: 'camp', face: 270 },
      { t: T('epilogue', 0.5), at: 'changan', form: 'camp', face: 270, n: 0.25, vanish: true },
      { t: T('epilogue', 0.72), at: 'xinping', via: [[108.5, 34.62]], form: 'camp', face: 320 },
      { t: T('epilogue', 0.86), at: 'xinping', form: 'camp', face: 320, n: 0, vanish: true },
    ],
  },
  {
    id: 's_furong', side: 'qin', name: '苻融', label: '苻融 · 前锋', strength: '步骑二十五万', banner: '苻融',
    kind: 'mixed', figures: 34, cav: 0.3,
    track: [
      { t: T('prologue', 0.6), at: [109.0, 34.27], form: 'hidden' },
      { t: T('prologue', 0.7), at: [109.0, 34.27], form: 'camp', face: 90 },
      { t: T('march', 0.05), at: [109.0, 34.27], form: 'camp', face: 90 },
      { t: T('march', 0.8), at: [112.9, 34.62], via: ['tongguan', [111.3, 34.66], 'luoyang'], form: 'column', face: 100 },
      { t: T('converge', 0.55), at: [116.42, 32.56], via: [[113.5, 34.35], [114.15, 33.92], [114.63, 33.665], [115.1, 33.45], [115.6, 33.12], [115.95, 32.86], [116.2, 32.66]], form: 'camp', face: 120 },
      { t: T('converge', 0.97), at: [116.42, 32.56], form: 'camp', face: 120 },
      { t: T('news', 0.0), at: [116.42, 32.56], form: 'hidden' },
    ],
  },
  {
    id: 's_murong', side: 'qin', name: '慕容垂', label: '慕容垂', strength: '前锋所部', banner: '慕容',
    kind: 'cav', figures: 18,
    track: [
      { t: T('prologue', 0.32), at: 'luoyang', form: 'hidden' },
      { t: T('prologue', 0.36), at: 'luoyang', form: 'column', face: 180 },
      { t: T('prologue', 0.66), at: [112.25, 32.3], via: [[112.55, 34.0], [112.53, 33.0]], form: 'block', face: 180 },
      { t: T('prologue', 0.92), at: [112.6, 33.4], via: [[112.4, 32.8]], form: 'camp', face: 0 },
      { t: T('march', 0.4), at: [112.6, 33.4], form: 'camp', face: 0 },
      { t: T('converge', 0.4), at: 'yuncheng', via: [[112.6, 32.6], [112.9, 31.7]], form: 'block', face: 160 },
      { t: T('news', 0.2), at: 'yuncheng', form: 'block', face: 160 },
      { t: T('news', 0.8), at: [112.75, 34.45], via: [[112.8, 31.8], [112.55, 32.9], [112.55, 33.8]], form: 'camp', face: 20 },
      { t: T('epilogue', 0.08), at: [112.75, 34.45], form: 'camp', face: 20 },
      { t: T('epilogue', 0.5), at: 'ye', via: [[113.45, 34.96], [113.9, 35.5]], form: 'camp', face: 20 },
    ],
  },
  {
    id: 's_yaochang', side: 'qin', name: '姚苌', label: '姚苌 · 督益梁', strength: '龙骧将军', banner: '姚',
    kind: 'cav', figures: 14,
    track: [
      { t: T('march', 0.2), at: [107.85, 33.25], form: 'hidden' },
      { t: T('march', 0.3), at: [107.85, 33.25], form: 'camp', face: 150 },
      { t: T('epilogue', 0.12), at: [107.85, 33.25], form: 'camp', face: 150 },
      { t: T('epilogue', 0.45), at: [108.85, 34.75], via: [[108.4, 33.9], [108.6, 34.45]], form: 'camp', face: 60 },
    ],
  },
  {
    id: 's_huanchong', side: 'jin', name: '桓冲', label: '桓冲 · 荆州', strength: '众十万', banner: '桓冲',
    kind: 'mixed', figures: 30, cav: 0.15,
    track: [
      { t: T('prologue', 0.0), at: 'shangming', form: 'camp', face: 20 },
      { t: T('prologue', 0.2), at: 'shangming', form: 'camp', face: 20 },
      { t: T('prologue', 0.5), at: [112.12, 31.84], via: ['jiangling', [112.3, 31.0]], form: 'line', face: 0 },
      { t: T('prologue', 0.62), at: [112.12, 31.84], form: 'line', face: 0, n: 0.95 },
      { t: T('prologue', 0.9), at: 'shangming', via: [[112.3, 31.0], 'jiangling'], form: 'camp', face: 20 },
    ],
  },
  {
    id: 's_qinrelief', side: 'qin', name: '苻叡', label: '苻叡 · 救襄阳', strength: '步骑五万', banner: '苻叡',
    kind: 'mixed', figures: 22, cav: 0.4,
    track: [
      { t: T('prologue', 0.36), at: 'luoyang', form: 'hidden' },
      { t: T('prologue', 0.4), at: 'luoyang', form: 'column', face: 200 },
      { t: T('prologue', 0.7), at: [112.36, 32.5], via: [[112.4, 33.9], [112.5, 33.0]], form: 'block', face: 190 },
      { t: T('prologue', 0.9), at: [112.36, 32.5], form: 'block', face: 190 },
      { t: T('prologue', 0.98), at: [112.36, 32.5], form: 'hidden' },
    ],
  },
  {
    id: 's_liangzhou', side: 'qin', name: '凉州兵', label: '凉州之兵', strength: '始达咸阳', banner: '凉',
    kind: 'cav', figures: 14,
    track: [
      { t: T('converge', 0.06), at: [107.55, 34.72], form: 'hidden' },
      { t: T('converge', 0.1), at: [107.55, 34.72], form: 'column', face: 100 },
      { t: T('converge', 0.6), at: 'xianyang', via: [[108.1, 34.55]], form: 'camp', face: 100 },
      { t: T('news', 0.0), at: 'xianyang', form: 'hidden' },
    ],
  },
  {
    id: 's_shuhan', side: 'qin', name: '蜀汉兵', label: '蜀、汉之兵', strength: '方顺流而下', banner: '蜀',
    kind: 'navy', boats: 8,
    track: [
      { t: T('converge', 0.06), at: [107.532, 33.2135], form: 'hidden' },
      { t: T('converge', 0.1), at: [107.532, 33.2135], form: 'boats', downstream: true },
      { t: T('converge', 0.8), at: [110.585, 32.8295], via: [{ river: 'han', from: [107.532, 33.2135], to: [110.585, 32.8295] }], form: 'boats', downstream: true, ease: 'linear' },
      { t: T('news', 0.0), at: [110.585, 32.8295], form: 'hidden' },
    ],
  },
  {
    id: 's_youji', side: 'qin', name: '幽冀兵', label: '幽、冀之兵', strength: '至于彭城', banner: '幽冀',
    kind: 'mixed', figures: 20, cav: 0.5,
    track: [
      { t: T('converge', 0.06), at: [115.9, 36.5], form: 'hidden' },
      { t: T('converge', 0.1), at: [115.9, 36.5], form: 'column', face: 160 },
      { t: T('converge', 0.7), at: [117.05, 34.42], via: [[116.3, 35.7], [116.7, 35.0]], form: 'camp', face: 160 },
      { t: T('news', 0.0), at: [117.05, 34.42], form: 'hidden' },
    ],
  },
  {
    id: 's_xieshi', side: 'jin', name: '谢石', label: '谢石 · 征讨大都督', strength: '众八万（合谢玄诸军）', banner: '谢石',
    kind: 'mixed', figures: 30, cav: 0.12,
    track: [
      { t: T('prologue', 0.0), at: [118.95, 32.12], form: 'hidden' },
      { t: T('converge', 0.28), at: [118.95, 32.12], form: 'hidden' },
      { t: T('converge', 0.32), at: [118.95, 32.12], form: 'camp', face: 330 },
      { t: T('converge', 0.9), at: [117.3, 32.66], via: [[118.6, 32.3], [118.15, 32.42], [117.7, 32.55]], form: 'camp', face: 290 },
      { t: T('converge', 0.99), at: [117.3, 32.66], form: 'camp', face: 290 },
      { t: T('news', 0.0), at: [116.95, 32.6], form: 'camp', face: 290 },
      { t: T('news', 0.35), at: [116.95, 32.6], form: 'camp', face: 290 },
      { t: T('news', 0.95), at: [118.9, 32.15], via: [[117.7, 32.55], [118.2, 32.42], [118.6, 32.3]], form: 'camp', face: 120 },
    ],
  },
  {
    id: 's_xiexuan', side: 'jin', name: '谢玄', label: '谢玄 · 前锋都督', strength: '北府兵', banner: '谢玄',
    kind: 'mixed', figures: 26, cav: 0.12,
    track: [
      { t: T('prologue', 0.0), at: 'guangling', form: 'camp', face: 300 },
      { t: T('converge', 0.3), at: 'guangling', form: 'camp', face: 300 },
      { t: T('converge', 0.92), at: [117.38, 32.78], via: [[119.1, 32.75], [118.6, 33.0], [118.1, 32.96], [117.75, 32.88]], form: 'camp', face: 270 },
      { t: T('news', 0.0), at: [117.05, 32.60], form: 'camp', face: 270 },
      { t: T('news', 0.97), at: [117.05, 32.60], form: 'camp', face: 270 },
      { t: T('epilogue', 0.0), at: 'huaiyin', form: 'hidden' },
      { t: T('epilogue', 0.08), at: 'huaiyin', form: 'camp', face: 330 },
      { t: T('epilogue', 0.62), at: [115.55, 35.5], via: [[118.0, 34.08], 'pengcheng', [116.3, 34.95]], form: 'camp', face: 300 },
    ],
  },
  {
    id: 's_hubin', side: 'jin', name: '胡彬', label: '胡彬 · 水军', strength: '五千', banner: '胡',
    kind: 'navy', boats: 6,
    track: [
      { t: T('converge', 0.3), at: [117.20, 31.945], form: 'hidden' },
      { t: T('converge', 0.34), at: [117.20, 31.945], form: 'boats', downstream: true },
      { t: T('converge', 0.82), at: [116.88, 32.50], via: [{ river: 'fei', from: [117.20, 31.945], to: [116.88, 32.50] }], form: 'boats', downstream: true },
      { t: T('news', 0.0), at: [116.88, 32.50], form: 'hidden' },
    ],
  },
  {
    id: 's_xiean', side: 'jin', name: '谢安', label: '谢安 · 坐镇建康', strength: '征讨大都督', banner: '谢安', bannerSize: 1.15,
    kind: 'inf', figures: 12,
    track: [
      { t: T('prologue', 0.0), at: 'jiankang', form: 'camp', face: 0 },
    ],
  },
];
