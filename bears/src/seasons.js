// The four seasons, after the four Boonie Bears series 春日对对碰 / 夏日连连看 / 秋日团团转 / 冬日乐翻天.
// Every visual parameter is a number or colour so that any two seasons can be cross-faded.
import * as THREE from 'three';

export const SEASONS = [
  {
    key: 'spring', name: '春', series: '春日对对碰', tag: '冰雪消融 · 百花盛开',
    grass: '#93cf5c', grass2: '#73b84b', meadow: '#a9da6a', dirt: '#b98d5c', rock: '#8e8a82', bank: '#c8b27a',
    leaf: ['#86d65c', '#a4e070', '#f2a7c3'], pine: '#3a7d4c', larch: '#9fd06a', birch: '#b2e07a',
    skyTop: '#7cc6f5', skyBottom: '#eaf7ff', fog: '#d9eef7', sun: '#fff4e0', sunI: 2.6, hemiI: 1.05,
    water: '#4fb5da', waterDeep: '#2b7fb0', ice: 0,
    snow: 0, leafScale: 1, flowers: 1, litter: 0, cropScale: 0.25,
  },
  {
    key: 'summer', name: '夏', series: '夏日连连看', tag: '林深叶茂 · 蝉鸣湖光',
    grass: '#5fae3f', grass2: '#428f33', meadow: '#7cbf47', dirt: '#ad8352', rock: '#86837c', bank: '#c4ac72',
    leaf: ['#3e9e3a', '#4fae3f', '#2f8a35'], pine: '#2d6a46', larch: '#5f9e48', birch: '#5db24a',
    skyTop: '#3fa7f2', skyBottom: '#d8f0ff', fog: '#cbe6f5', sun: '#fffbe8', sunI: 3.0, hemiI: 1.0,
    water: '#2fa2cc', waterDeep: '#1a6c9c', ice: 0,
    snow: 0, leafScale: 1.08, flowers: 0.35, litter: 0, cropScale: 0.7,
  },
  {
    key: 'autumn', name: '秋', series: '秋日团团转', tag: '层林尽染 · 硕果满枝',
    grass: '#bea64e', grass2: '#a5823a', meadow: '#cfae55', dirt: '#a97a4a', rock: '#8a837a', bank: '#c7a96b',
    leaf: ['#ee8a2c', '#d8442b', '#f3bf3a'], pine: '#3a6a46', larch: '#e3b23a', birch: '#f4cb3e',
    skyTop: '#f0b979', skyBottom: '#fbeedb', fog: '#f3dfc6', sun: '#ffd9a6', sunI: 2.6, hemiI: 0.95,
    water: '#3f9cbd', waterDeep: '#255f80', ice: 0,
    snow: 0, leafScale: 0.92, flowers: 0, litter: 1, cropScale: 1,
  },
  {
    key: 'winter', name: '冬', series: '冬日乐翻天', tag: '银装素裹 · 冰湖嬉雪',
    grass: '#dfe8ef', grass2: '#cfdbe5', meadow: '#e6edf3', dirt: '#b6a596', rock: '#8a8e96', bank: '#d4dde6',
    leaf: ['#8a6a4a', '#8a6a4a', '#8a6a4a'], pine: '#2f5a44', larch: '#a08060', birch: '#c9b48a',
    skyTop: '#9fb9d3', skyBottom: '#f1f6fb', fog: '#e4edf5', sun: '#eef4ff', sunI: 2.2, hemiI: 1.15,
    water: '#cfe7f3', waterDeep: '#9cc6de', ice: 1,
    snow: 1, leafScale: 0, flowers: 0, litter: 0, cropScale: 0,
  },
];

const tmpA = new THREE.Color(), tmpB = new THREE.Color();
const KEYS = Object.keys(SEASONS[0]).filter((k) => !['key', 'name', 'series', 'tag'].includes(k));

// s is a continuous season position: 0 spring, 1 summer, 2 autumn, 3 winter, 4 == 0 again.
export function blendSeason(s, out = {}) {
  const n = SEASONS.length;
  s = ((s % n) + n) % n;
  const i = Math.floor(s), f = s - i;
  const A = SEASONS[i], B = SEASONS[(i + 1) % n];
  out.weights = [0, 0, 0, 0];
  out.weights[i] += 1 - f;
  out.weights[(i + 1) % n] += f;
  for (const k of KEYS) {
    const a = A[k], b = B[k];
    if (typeof a === 'number') out[k] = a + (b - a) * f;
    else if (Array.isArray(a)) {
      out[k] = out[k] || a.map(() => new THREE.Color());
      a.forEach((c, j) => out[k][j].copy(tmpA.set(c)).lerp(tmpB.set(b[j]), f));
    } else {
      out[k] = out[k] || new THREE.Color();
      out[k].copy(tmpA.set(a)).lerp(tmpB.set(b), f);
    }
  }
  return out;
}
