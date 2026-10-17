// Small math helpers: seeded RNG, value noise, polylines.
import * as THREE from 'three';

export function rng(seed = 1) {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function hash2(x, z) {
  const s = Math.sin(x * 127.1 + z * 311.7) * 43758.5453;
  return s - Math.floor(s);
}

export function noise2(x, z) {
  const xi = Math.floor(x), zi = Math.floor(z);
  const xf = x - xi, zf = z - zi;
  const u = xf * xf * (3 - 2 * xf), v = zf * zf * (3 - 2 * zf);
  const a = hash2(xi, zi), b = hash2(xi + 1, zi), c = hash2(xi, zi + 1), d = hash2(xi + 1, zi + 1);
  return (a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v) * 2 - 1;
}

export function fbm(x, z, oct = 4) {
  let sum = 0, amp = 0.5, f = 1;
  for (let i = 0; i < oct; i++) {
    sum += amp * noise2(x * f, z * f);
    f *= 2.03;
    amp *= 0.5;
  }
  return sum;
}

export const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
export const lerp = (a, b, t) => a + (b - a) * t;
export const smooth = (e0, e1, x) => {
  const t = clamp((x - e0) / (e1 - e0), 0, 1);
  return t * t * (3 - 2 * t);
};

// Polyline in the XZ plane, with distance queries and arc-length sampling.
export class Line2 {
  constructor(pts, smoothN = 0) {
    let p = pts.map(([x, z]) => new THREE.Vector2(x, z));
    if (smoothN) {
      const curve = new THREE.SplineCurve(p);
      p = curve.getSpacedPoints(smoothN);
    }
    this.p = p;
    this.len = [0];
    for (let i = 1; i < p.length; i++) this.len.push(this.len[i - 1] + p[i].distanceTo(p[i - 1]));
    this.total = this.len[this.len.length - 1];
  }
  // returns { d, t } distance to line and normalised arc position of the closest point
  closest(x, z) {
    let best = Infinity, bt = 0;
    const p = this.p;
    for (let i = 0; i < p.length - 1; i++) {
      const ax = p[i].x, az = p[i].y, bx = p[i + 1].x, bz = p[i + 1].y;
      const dx = bx - ax, dz = bz - az;
      const l2 = dx * dx + dz * dz || 1;
      let t = ((x - ax) * dx + (z - az) * dz) / l2;
      t = clamp(t, 0, 1);
      const qx = ax + dx * t - x, qz = az + dz * t - z;
      const d = qx * qx + qz * qz;
      if (d < best) {
        best = d;
        bt = (this.len[i] + t * (this.len[i + 1] - this.len[i])) / this.total;
      }
    }
    return { d: Math.sqrt(best), t: bt };
  }
  at(t) {
    const L = clamp(t, 0, 1) * this.total;
    let i = 1;
    while (i < this.len.length - 1 && this.len[i] < L) i++;
    const a = this.p[i - 1], b = this.p[i];
    const k = (L - this.len[i - 1]) / (this.len[i] - this.len[i - 1] || 1);
    return { x: a.x + (b.x - a.x) * k, z: a.y + (b.y - a.y) * k, dx: b.x - a.x, dz: b.y - a.y };
  }
}
