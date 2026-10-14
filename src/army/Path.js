// Polyline in world XZ with arc-length parameterisation.
export class Path {
  constructor(points) {
    // drop consecutive duplicates
    const pts = [];
    for (const p of points) {
      const last = pts[pts.length - 1];
      if (!last || Math.hypot(p[0] - last[0], p[1] - last[1]) > 1e-6) pts.push([p[0], p[1]]);
    }
    if (pts.length === 1) pts.push([pts[0][0] + 1e-4, pts[0][1]]);
    this.pts = pts;
    this.cum = [0];
    for (let i = 1; i < pts.length; i++) {
      this.cum.push(this.cum[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
    }
    this.length = this.cum[this.cum.length - 1];
  }

  /** Smooth a coarse waypoint list (Chaikin) before building a path. */
  static smooth(points, iterations = 2) {
    let pts = points.map((p) => [p[0], p[1]]);
    for (let it = 0; it < iterations; it++) {
      if (pts.length < 3) break;
      const out = [pts[0]];
      for (let i = 0; i < pts.length - 1; i++) {
        const a = pts[i];
        const b = pts[i + 1];
        out.push([0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]]);
        out.push([0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1]]);
      }
      out.push(pts[pts.length - 1]);
      pts = out;
    }
    return pts;
  }

  /** Point and unit tangent at arc length s (clamped). Writes into out = {x, z, tx, tz}. */
  at(s, out = { x: 0, z: 0, tx: 0, tz: 1 }) {
    const L = this.length;
    if (s <= 0) s = 0;
    if (s >= L) s = L;
    // binary search
    let lo = 0;
    let hi = this.cum.length - 1;
    while (hi - lo > 1) {
      const mid = (lo + hi) >> 1;
      if (this.cum[mid] <= s) lo = mid;
      else hi = mid;
    }
    const a = this.pts[lo];
    const b = this.pts[hi];
    const seg = this.cum[hi] - this.cum[lo] || 1e-9;
    const f = (s - this.cum[lo]) / seg;
    out.x = a[0] + (b[0] - a[0]) * f;
    out.z = a[1] + (b[1] - a[1]) * f;
    out.tx = (b[0] - a[0]) / seg;
    out.tz = (b[1] - a[1]) / seg;
    return out;
  }

  /** Sub-path between arc lengths s0..s1. */
  slice(s0, s1) {
    const pts = [];
    const p0 = this.at(s0);
    pts.push([p0.x, p0.z]);
    for (let i = 0; i < this.pts.length; i++) {
      if (this.cum[i] > s0 && this.cum[i] < s1) pts.push(this.pts[i]);
    }
    const p1 = this.at(s1);
    pts.push([p1.x, p1.z]);
    return new Path(pts);
  }

  /** Arc length of the vertex closest to (x, z). */
  closestS(x, z) {
    let best = Infinity;
    let bestS = 0;
    for (let i = 0; i < this.pts.length - 1; i++) {
      const a = this.pts[i];
      const b = this.pts[i + 1];
      const dx = b[0] - a[0];
      const dz = b[1] - a[1];
      const l2 = dx * dx + dz * dz || 1e-12;
      let f = ((x - a[0]) * dx + (z - a[1]) * dz) / l2;
      f = Math.max(0, Math.min(1, f));
      const px = a[0] + dx * f;
      const pz = a[1] + dz * f;
      const d = (px - x) ** 2 + (pz - z) ** 2;
      if (d < best) {
        best = d;
        bestS = this.cum[i] + Math.sqrt(l2) * f;
      }
    }
    return bestS;
  }
}
