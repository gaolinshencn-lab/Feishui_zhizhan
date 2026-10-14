import * as THREE from 'three';
import { CSS2DObject } from 'three/examples/jsm/renderers/CSS2DRenderer.js';
import { Path } from './Path.js';
import { infantryGeometry, cavalryGeometry, boatGeometry, SIDE_COLORS } from './figures.js';
import { makeFlagTexture } from './flags.js';

const easeInOut = (t) => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2);
const easeOut = (t) => 1 - (1 - t) * (1 - t);
const clamp01 = (t) => (t < 0 ? 0 : t > 1 ? 1 : t);
const smoothstep = (a, b, x) => {
  const t = clamp01((x - a) / (b - a));
  return t * t * (3 - 2 * t);
};
const DEG = Math.PI / 180;

function rng(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
function hashString(s) {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 16777619);
  return h >>> 0;
}

const ASPECT = { line: 4.6, thinline: 9, block: 1.35, deep: 2.2, column: 0.16, camp: 1 };

/** Formation slots in spacing units: x = right, z = forward. Centre-out so wings come last. */
function gridSlots(n, aspect) {
  const cols = Math.max(1, Math.round(Math.sqrt(n * aspect)));
  const rows = Math.ceil(n / cols);
  const slots = [];
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) slots.push([c - (cols - 1) / 2, ((rows - 1) / 2 - r) * 0.9]);
  }
  slots.sort((a, b) => Math.abs(a[0]) - Math.abs(b[0]) || b[1] - a[1]);
  return slots.slice(0, n);
}
function campSlots(n) {
  const slots = [];
  for (let i = 0; i < n; i++) {
    const r = 0.62 * Math.sqrt(i + 0.5);
    const a = i * 2.39996;
    slots.push([Math.cos(a) * r * 1.35, Math.sin(a) * r]);
  }
  return slots;
}

export class UnitsLayer {
  /**
   * @param resolver from makeResolver()
   * @param defs unit definitions for this table
   * @param opts { figScale, spacing, bannerScale, boatScale, labelRoot }
   */
  constructor(resolver, defs, opts) {
    this.R = resolver;
    this.proj = resolver.proj;
    this.opts = Object.assign({ figScale: 0.075, spacing: 0.1, bannerScale: 1, boatScale: 2.2, shadows: true }, opts);
    this.group = new THREE.Group();
    this.group.name = 'units';
    this.labelsVisible = true;
    this.units = defs.map((d) => this.prepare(d));
    this.byId = Object.fromEntries(this.units.map((u) => [u.def.id, u]));
    this.buildMeshes();
    this.buildBanners();
    this._tmp = { x: 0, z: 0, tx: 0, tz: 1 };
  }

  // ---------------------------------------------------------------------------
  prepare(def) {
    const N = def.kind === 'navy' ? def.boats || def.figures || 8 : def.figures;
    const seed = hashString(def.id);
    const rand = rng(seed);
    const cavCount = def.kind === 'cav' ? N : def.kind === 'mixed' ? Math.round(N * (def.cav ?? 0.25)) : 0;
    const types = [];
    for (let i = 0; i < N; i++) {
      if (def.kind === 'navy') types.push('boat');
      else types.push(i >= N - cavCount ? 'cav' : 'inf');
    }
    const fig = [];
    for (let i = 0; i < N; i++) {
      fig.push({
        jx: (rand() - 0.5) * 0.32,
        jz: (rand() - 0.5) * 0.32,
        ra: (rand() - 0.5) * 2, // rout angle factor
        rs: 0.62 + rand() * 0.7, // rout speed factor
        rd: (rand() - 0.5) * 2, // rout lateral drift
        bob: rand() * Math.PI * 2,
        tone: 0.86 + rand() * 0.24,
      });
    }
    // death order
    const perm = [...Array(N).keys()];
    for (let i = N - 1; i > 0; i--) {
      const j = Math.floor(rand() * (i + 1));
      [perm[i], perm[j]] = [perm[j], perm[i]];
    }
    // resolve keys
    const keys = [];
    let prev = null;
    for (const k of def.track) {
      const key = { ...k };
      key.form = k.form ?? prev?.form ?? 'block';
      key.n = k.n ?? prev?.n ?? 1;
      key.pos = k.at ? this.R.point(k.at) : prev?.pos;
      if (!key.pos) throw new Error(`unit ${def.id}: key without position`);
      if (k.target) key.targetPos = this.R.point(k.target);
      if (prev && (k.via || (k.at && (Math.abs(key.pos[0] - prev.pos[0]) > 1e-6 || Math.abs(key.pos[1] - prev.pos[1]) > 1e-6)))) {
        const pts = this.R.path([prev.at, ...(k.via || []), k.at ?? prev.at], { smooth: k.smooth !== false });
        key.path = new Path(pts);
      }
      if (typeof k.face === 'string') {
        const tp = this.R.point(k.face);
        key.faceRad = Math.atan2(tp[0] - key.pos[0], -(tp[1] - key.pos[1]));
      } else if (k.face !== undefined) {
        key.faceRad = k.face * DEG;
      } else if (key.path) {
        const e = key.path.at(key.path.length);
        key.faceRad = Math.atan2(e.tx, -e.tz);
      } else {
        key.faceRad = prev?.faceRad ?? 0;
      }
      key.at = k.at ?? prev?.at;
      keys.push(key);
      prev = key;
    }
    // death times
    const deathT = new Float32Array(N).fill(Infinity);
    const vanish = new Uint8Array(N);
    for (let i = 1; i < keys.length; i++) {
      const a = keys[i - 1];
      const b = keys[i];
      const da = N - Math.round(a.n * N);
      const db = N - Math.round(b.n * N);
      for (let d = da; d < db; d++) {
        const f = (d - da + 0.5) / Math.max(1, db - da);
        deathT[perm[d]] = a.t + (b.t - a.t) * f;
        vanish[perm[d]] = b.vanish ? 1 : 0;
      }
    }
    return {
      def,
      N,
      types,
      fig,
      keys,
      deathT,
      vanish,
      deathPos: new Float32Array(N * 3).fill(NaN),
      slotCache: new Map(),
      pos: new Float32Array(N * 2),
      face: new Float32Array(N),
      state: new Uint8Array(N), // 0 hidden, 1 alive, 2 fallen, 3 swimming
      moving: false,
      visible: false,
      center: new THREE.Vector3(),
      head: new THREE.Vector3(),
      appear: 1,
    };
  }

  // ---------------------------------------------------------------------------
  /** World slots for a key's formation, cached. Returns {x: Float32Array, z, f}. */
  slots(u, ki) {
    let s = u.slotCache.get(ki);
    if (s) return s;
    const key = u.keys[ki];
    const N = u.N;
    const sp = this.opts.spacing * (key.spacing ?? 1) * (u.def.kind === 'navy' ? 2.2 : 1);
    const x = new Float32Array(N);
    const z = new Float32Array(N);
    const f = new Float32Array(N);
    const [cx, cz] = key.pos;
    if (key.form === 'siege' && key.targetPos) {
      const [tx, tz] = key.targetPos;
      const radius = this.proj.kmToWorldLen(key.radius ?? 1.5);
      const [a0, a1] = (key.arc ?? [0, 360]).map((d) => d * DEG);
      const ranks = key.ranks ?? 2;
      const per = Math.ceil(N / ranks);
      for (let i = 0; i < N; i++) {
        const rank = Math.floor(i / per);
        const k = i % per;
        const a = a0 + ((a1 - a0) * (k + 0.5)) / per + u.fig[i].jx * 0.02;
        const r = radius + rank * sp * 0.9 + u.fig[i].jz * sp;
        x[i] = tx + Math.sin(a) * r;
        z[i] = tz - Math.cos(a) * r;
        f[i] = Math.atan2(tx - x[i], -(tz - z[i]));
      }
    } else if (u.def.kind === 'navy' || key.form === 'boats') {
      // moored or anchored boats strung along the nearest river, two abreast
      const river = this.nearestRiver(cx, cz);
      const s0 = river.closestS(cx, cz);
      const dir = key.downstream ? 1 : -1;
      const p = { x: 0, z: 0, tx: 0, tz: 1 };
      for (let i = 0; i < N; i++) {
        const k = Math.floor(i / 2);
        const off = (k - (Math.ceil(N / 2) - 1) / 2) * sp * 1.25;
        river.at(s0 + off, p);
        const lat = (i % 2 === 0 ? -1 : 1) * sp * 0.28;
        x[i] = cx + (p.x - river.at(s0).x) - p.tz * lat;
        z[i] = cz + (p.z - river.at(s0).z) + p.tx * lat;
        f[i] = Math.atan2(dir * p.tx, -(dir * p.tz));
      }
    } else {
      const local = key.form === 'camp' ? campSlots(N) : gridSlots(N, ASPECT[key.form] ?? 1.35);
      const cs = Math.cos(key.faceRad);
      const sn = Math.sin(key.faceRad);
      const loose = key.form === 'camp' ? 1.4 : key.loose ?? 1;
      for (let i = 0; i < N; i++) {
        const lx = (local[i][0] + u.fig[i].jx * loose) * sp;
        const lz = (local[i][1] + u.fig[i].jz * loose) * sp;
        // right = (cos, sin) in (x, z); forward = (sin, -cos)
        x[i] = cx + lx * cs + lz * sn;
        z[i] = cz + lx * sn - lz * cs;
        f[i] = key.faceRad + (key.form === 'camp' ? u.fig[i].ra * 1.2 : 0);
      }
    }
    s = { x, z, f };
    u.slotCache.set(ki, s);
    return s;
  }

  nearestRiver(x, z) {
    let best = null;
    let bd = Infinity;
    for (const r of Object.values(this.R.rivers)) {
      const s = r.closestS(x, z);
      const p = r.at(s);
      const d = (p.x - x) ** 2 + (p.z - z) ** 2;
      if (d < bd) {
        bd = d;
        best = r;
      }
    }
    return best;
  }

  // ---------------------------------------------------------------------------
  /** Position of figure i of unit u at time T (ignores death). Writes u.pos/u.face. */
  evalFigure(u, i, T, segInfo) {
    const { ki, a, b, f } = segInfo;
    const A = this.slots(u, a);
    if (b < 0) {
      u.pos[i * 2] = A.x[i];
      u.pos[i * 2 + 1] = A.z[i];
      u.face[i] = A.f[i];
      return 0;
    }
    const kb = u.keys[b];
    const B = this.slots(u, b);
    const fig = u.fig[i];
    if (kb.form === 'rout') {
      // scatter from formation A along the flight path
      const path = kb.path;
      const ff = easeOut(f);
      const ui = clamp01(ff * fig.rs * (kb.speed ?? 1));
      const t = this._tmp;
      const L = path ? path.length : 0;
      let px;
      let pz;
      let tx = 0;
      let tz = -1;
      if (path) {
        path.at(ui * L, t);
        const p0 = path.at(0, {});
        px = t.x - p0.x;
        pz = t.z - p0.z;
        tx = t.tx;
        tz = t.tz;
      } else {
        px = 0;
        pz = 0;
      }
      const spread = (kb.spread ?? 1) * (1 + 2.2 * ui);
      const ox = A.x[i] - u.keys[a].pos[0];
      const oz = A.z[i] - u.keys[a].pos[1];
      const ang = fig.ra * 0.9 * ui;
      const ca = Math.cos(ang);
      const sa = Math.sin(ang);
      const rx = (ox * ca - oz * sa) * spread;
      const rz = (ox * sa + oz * ca) * spread;
      const drift = fig.rd * ui * L * 0.16 * (kb.spread ?? 1);
      u.pos[i * 2] = u.keys[a].pos[0] + px + rx + -tz * drift;
      u.pos[i * 2 + 1] = u.keys[a].pos[1] + pz + rz + tx * drift;
      u.face[i] = Math.atan2(tx, -tz) + fig.ra * 0.6;
      return ui < 0.999 ? 1 : 0;
    }
    if (!kb.path) {
      // stationary morph between formations
      const e = easeInOut(f);
      u.pos[i * 2] = A.x[i] + (B.x[i] - A.x[i]) * e;
      u.pos[i * 2 + 1] = A.z[i] + (B.z[i] - A.z[i]) * e;
      let df = B.f[i] - A.f[i];
      df = Math.atan2(Math.sin(df), Math.cos(df));
      u.face[i] = A.f[i] + df * e;
      const moved = Math.hypot(B.x[i] - A.x[i], B.z[i] - A.z[i]) > 1e-4 && f > 0 && f < 1;
      return moved ? 1 : 0;
    }
    // march along the path in column, peeling off formation A and forming up as B
    const path = kb.path;
    const L = path.length;
    const N = u.N;
    const naval = u.def.kind === 'navy';
    const colsM = naval ? 2 : Math.max(2, Math.min(6, Math.round(Math.sqrt(N / 14))));
    const spM = this.opts.spacing * (naval ? 2.6 : 0.85);
    const rows = Math.ceil(N / colsM);
    const Lc = rows * spM;
    const ramp = Math.max(spM * 5, this.opts.spacing * 6);
    const e = kb.ease === 'linear' ? f : easeInOut(f);
    const sHead = e * (L + Lc);
    const row = Math.floor(i / colsM);
    const col = i % colsM;
    const lateral = (col - (colsM - 1) / 2) * spM;
    const si = sHead - row * spM;
    const t = this._tmp;
    if (si <= 0) {
      path.at(0, t);
      const w = smoothstep(-ramp, 0, si);
      u.pos[i * 2] = A.x[i] + (t.x - t.tz * lateral - A.x[i]) * w;
      u.pos[i * 2 + 1] = A.z[i] + (t.z + t.tx * lateral - A.z[i]) * w;
      u.face[i] = w > 0.01 ? Math.atan2(t.tx, -t.tz) : A.f[i];
      return w > 0.001 && w < 0.999 ? 1 : 0;
    }
    if (si >= L) {
      path.at(L, t);
      const w = smoothstep(L, L + ramp, si);
      const ex = t.x - t.tz * lateral;
      const ez = t.z + t.tx * lateral;
      u.pos[i * 2] = ex + (B.x[i] - ex) * w;
      u.pos[i * 2 + 1] = ez + (B.z[i] - ez) * w;
      u.face[i] = w > 0.98 ? B.f[i] : Math.atan2(t.tx, -t.tz);
      return w < 0.999 ? 1 : 0;
    }
    path.at(si, t);
    u.pos[i * 2] = t.x - t.tz * lateral;
    u.pos[i * 2 + 1] = t.z + t.tx * lateral;
    u.face[i] = Math.atan2(t.tx, -t.tz);
    return 1;
  }

  segmentAt(u, T) {
    const keys = u.keys;
    if (T < keys[0].t) return null;
    let a = keys.length - 1;
    for (let k = 0; k < keys.length - 1; k++) {
      if (T < keys[k + 1].t) {
        a = k;
        break;
      }
    }
    const b = a < keys.length - 1 ? a + 1 : -1;
    const f = b < 0 ? 1 : clamp01((T - keys[a].t) / Math.max(1e-6, keys[b].t - keys[a].t));
    return { a, b, f };
  }

  // ---------------------------------------------------------------------------
  buildMeshes() {
    const counts = {};
    for (const u of this.units) {
      for (const t of u.types) {
        const k = `${u.def.side}-${t}`;
        counts[k] = (counts[k] || 0) + 1;
      }
    }
    this.meshes = {};
    const geos = {};
    const matFor = () =>
      new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.72, metalness: 0.05 });
    for (const [k, count] of Object.entries(counts)) {
      const [side, type] = k.split('-');
      const g = (geos[k] = type === 'inf' ? infantryGeometry(side) : type === 'cav' ? cavalryGeometry(side) : boatGeometry(side));
      const mesh = new THREE.InstancedMesh(g, matFor(), count);
      mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
      mesh.castShadow = this.opts.shadows;
      mesh.receiveShadow = false;
      mesh.frustumCulled = false;
      const white = new THREE.Color(1, 1, 1);
      for (let i = 0; i < count; i++) mesh.setColorAt(i, white);
      mesh.instanceColor.setUsage(THREE.DynamicDrawUsage);
      mesh.name = `fig-${k}`;
      this.meshes[k] = mesh;
      this.group.add(mesh);
    }
    // assign instance slots
    const next = {};
    for (const u of this.units) {
      u.inst = new Int32Array(u.N);
      u.meshKey = [];
      for (let i = 0; i < u.N; i++) {
        const k = `${u.def.side}-${u.types[i]}`;
        u.meshKey.push(k);
        u.inst[i] = next[k] = (next[k] ?? -1) + 1;
      }
    }
    this.color = new THREE.Color();
  }

  buildBanners() {
    const s = this.opts.bannerScale;
    for (const u of this.units) {
      if (u.def.noBanner) continue;
      const side = u.def.side;
      const g = new THREE.Group();
      const poleH = 1.0 * s * (u.def.bannerSize ?? 1);
      const pole = new THREE.Mesh(
        new THREE.CylinderGeometry(0.012 * s, 0.016 * s, poleH, 6),
        new THREE.MeshStandardMaterial({ color: '#3b2a1a', roughness: 0.7 })
      );
      pole.position.y = poleH / 2;
      pole.castShadow = true;
      g.add(pole);
      const finial = new THREE.Mesh(
        new THREE.ConeGeometry(0.03 * s, 0.09 * s, 6),
        new THREE.MeshStandardMaterial({ color: '#d9b25f', roughness: 0.35, metalness: 0.6 })
      );
      finial.position.y = poleH + 0.03 * s;
      g.add(finial);
      const text = u.def.banner || '';
      const tex = makeFlagTexture(text, side, u.def.bannerStyle);
      const fw = 0.34 * s * (u.def.bannerSize ?? 1);
      const fh = (text.length > 1 ? 0.56 : 0.4) * s * (u.def.bannerSize ?? 1);
      const flagGeo = new THREE.PlaneGeometry(fw, fh, 8, 2);
      flagGeo.translate(fw / 2, 0, 0);
      const flagMat = new THREE.MeshStandardMaterial({ map: tex, side: THREE.DoubleSide, roughness: 0.8, transparent: true, alphaTest: 0.4 });
      const waveU = { uTime: { value: 0 }, uAmp: { value: 0.045 * s }, uW: { value: fw } };
      flagMat.onBeforeCompile = (sh) => {
        Object.assign(sh.uniforms, waveU);
        sh.vertexShader = sh.vertexShader
          .replace('#include <common>', '#include <common>\nuniform float uTime; uniform float uAmp; uniform float uW;')
          .replace(
            '#include <begin_vertex>',
            `#include <begin_vertex>
float k = clamp(position.x / uW, 0.0, 1.0);
transformed.z += sin(position.x / uW * 5.0 - uTime * 4.0) * uAmp * k;
transformed.y -= k * k * uAmp * 0.6;`
          );
      };
      flagMat.customProgramCacheKey = () => 'flag';
      const flag = new THREE.Mesh(flagGeo, flagMat);
      flag.position.y = poleH - fh / 2 - 0.02 * s;
      flag.castShadow = true;
      g.add(flag);
      g.visible = false;
      u.banner = g;
      u.flagWave = waveU;
      this.group.add(g);

      // HTML label
      const el = document.createElement('div');
      el.className = `unit-label side-${side}`;
      el.innerHTML = `<span class="ul-name">${u.def.label ?? u.def.name}</span>${u.def.strength ? `<span class="ul-str">${u.def.strength}</span>` : ''}`;
      el.title = [u.def.label ?? u.def.name, u.def.strength].filter(Boolean).join(' · ');
      const lab = new CSS2DObject(el);
      lab.center.set(0.5, 1.15);
      lab.position.y = poleH + 0.08 * s;
      g.add(lab);
      u.label = lab;
      u.labelEl = el;
    }
  }

  setLabelsVisible(v) {
    this.labelsVisible = v;
  }

  collect(items) {
    for (const u of this.units) if (u.label && u.label.visible) items.push({ el: u.labelEl, obj: u.label, want: true, prio: 40 + (u.def.minor ? 5 : 0) });
  }

  setVisible(v) {
    this.group.visible = v;
    if (!v) for (const u of this.units) if (u.label) u.label.visible = false;
  }

  // ---------------------------------------------------------------------------
  update(T, time) {
    const proj = this.proj;
    const ys = proj.yScale;
    const fs = this.opts.figScale;
    const touched = new Set();
    for (const u of this.units) {
      const seg = this.segmentAt(u, T);
      let hidden = !seg;
      if (seg) {
        const ka = u.keys[seg.a];
        const kb = seg.b >= 0 ? u.keys[seg.b] : null;
        if (ka.form === 'hidden' && (!kb || kb.form === 'hidden')) hidden = true;
        if (ka.form === 'hidden' && kb && kb.form !== 'hidden') {
          // appear at B
          u.appear = smoothstep(0, 0.4, seg.f);
          seg.a = seg.b;
          seg.b = -1;
          seg.f = 1;
        } else if (kb && kb.form === 'hidden') {
          u.appear = 1 - smoothstep(0.6, 1, seg.f);
          seg.b = -1;
        } else u.appear = 1;
      }
      u.visible = !hidden;
      const routing = !!seg && ((seg.b >= 0 && u.keys[seg.b].form === 'rout') || u.keys[seg.a].form === 'rout');
      let cx = 0;
      let cz = 0;
      let cnt = 0;
      let moving = 0;
      for (let i = 0; i < u.N; i++) {
        const mk = u.meshKey[i];
        const mesh = this.meshes[mk];
        const idx = u.inst[i];
        const arr = mesh.instanceMatrix.array;
        const o = idx * 16;
        touched.add(mk);
        if (hidden) {
          arr[o] = arr[o + 5] = arr[o + 10] = 0;
          arr[o + 12] = 0;
          arr[o + 13] = -1000;
          arr[o + 14] = 0;
          continue;
        }
        const dT = u.deathT[i];
        let state = 1;
        let x;
        let z;
        let face;
        if (T >= dT) {
          if (u.vanish[i]) {
            arr[o] = arr[o + 5] = arr[o + 10] = 0;
            arr[o + 13] = -1000;
            continue;
          }
          state = 2;
          if (Number.isNaN(u.deathPos[i * 3])) {
            const s2 = this.segmentAt(u, dT) || seg;
            this.evalFigure(u, i, dT, s2);
            u.deathPos[i * 3] = u.pos[i * 2];
            u.deathPos[i * 3 + 1] = u.pos[i * 2 + 1];
            u.deathPos[i * 3 + 2] = u.face[i];
          }
          x = u.deathPos[i * 3];
          z = u.deathPos[i * 3 + 1];
          face = u.deathPos[i * 3 + 2];
        } else {
          moving += this.evalFigure(u, i, T, seg);
          x = u.pos[i * 2];
          z = u.pos[i * 2 + 1];
          face = u.face[i];
          cx += x;
          cz += z;
          cnt++;
        }
        const type = u.types[i];
        const wet = type !== 'boat' ? proj.waterAt(x, z) : 0;
        let y = proj.groundY(x, z);
        let k = fs * (type === 'boat' ? this.opts.boatScale : 1) * u.appear;
        if (state === 1 && routing && wet < -6 && type !== 'boat') {
          state = 3;
          y -= k * 0.55 * smoothstep(-6, -60, wet);
        }
        const c = Math.cos(face);
        const sn = Math.sin(face);
        if (state === 2) {
          // fallen: lying along its last heading
          const kk = k * 0.95;
          arr[o] = c * kk;
          arr[o + 1] = 0;
          arr[o + 2] = -sn * kk;
          arr[o + 3] = 0;
          arr[o + 4] = sn * kk;
          arr[o + 5] = 0;
          arr[o + 6] = c * kk;
          arr[o + 7] = 0;
          arr[o + 8] = 0;
          arr[o + 9] = -kk;
          arr[o + 10] = 0;
          arr[o + 11] = 0;
          arr[o + 12] = x;
          arr[o + 13] = y + kk * 0.12 + (wet < -6 ? -kk * 0.3 : 0);
          arr[o + 14] = z;
          arr[o + 15] = 1;
          const tone = wet < -6 ? 0.25 : 0.42;
          mesh.instanceColor.setXYZ(idx, tone, tone * 0.95, tone * 0.9);
        } else {
          const bob = moving && type !== 'boat' ? Math.abs(Math.sin(time * 9 + u.fig[i].bob)) * k * 0.08 : 0;
          const roll = type === 'boat' ? Math.sin(time * 1.3 + u.fig[i].bob) * 0.04 : 0;
          // rotation about Y (forward = (sin, -cos) in x,z → local +Z)
          const yaw = Math.atan2(sn, -c);
          const cy = Math.cos(yaw);
          const sy = Math.sin(yaw);
          arr[o] = cy * k;
          arr[o + 1] = roll * k;
          arr[o + 2] = -sy * k;
          arr[o + 3] = 0;
          arr[o + 4] = -roll * cy * k;
          arr[o + 5] = k;
          arr[o + 6] = 0;
          arr[o + 7] = 0;
          arr[o + 8] = sy * k;
          arr[o + 9] = 0;
          arr[o + 10] = cy * k;
          arr[o + 11] = 0;
          arr[o + 12] = x;
          arr[o + 13] = y + bob + (type === 'boat' ? k * 0.02 : 0);
          arr[o + 14] = z;
          arr[o + 15] = 1;
          const tn = u.fig[i].tone * (state === 3 ? 0.7 : 1);
          mesh.instanceColor.setXYZ(idx, tn, tn, tn * (state === 3 ? 1.1 : 1));
        }
      }
      u.moving = moving > 0;
      if (cnt > 0) {
        u.center.set(cx / cnt, 0, cz / cnt);
        u.center.y = proj.groundY(u.center.x, u.center.z);
      }
      if (u.banner) {
        const show = !hidden && cnt > 0;
        u.banner.visible = show;
        if (show) {
          // banner rides at the front-centre of the living figures
          u.banner.position.copy(u.center);
          u.banner.scale.setScalar(Math.max(0.01, u.appear));
          u.flagWave.uTime.value = time + (u.def.id.length % 7);
          const yawB = (u.def.side === 'jin' ? 0.6 : -0.6) + Math.sin(time * 0.3) * 0.15;
          u.banner.rotation.y = yawB;
        }
        if (u.label) u.label.visible = show && this.labelsVisible && this.group.visible;
      }
    }
    for (const k of touched) {
      this.meshes[k].instanceMatrix.needsUpdate = true;
      if (this.meshes[k].instanceColor) this.meshes[k].instanceColor.needsUpdate = true;
    }
  }

  /** Current anchor (banner position) of a unit, or null if not on the table. */
  anchor(id) {
    const u = this.byId[id];
    if (!u || !u.visible) return null;
    return u.center;
  }
}

export { SIDE_COLORS };
