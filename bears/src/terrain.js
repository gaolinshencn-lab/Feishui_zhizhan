// Procedural terrain of Bear Ridge: heightfield, seasonal ground shader, diorama board, and water.
import * as THREE from 'three';
import { fbm, Line2, smooth, clamp, lerp } from './util.js';
import { BOARD, LAKE, RIVER, OUTFLOW, PATHS, CLEARINGS, HILLS, WATERFALL } from './places.js';
import { U, snowify } from './shared.js';

const HALF = BOARD / 2;
const RES = 200;

export class HeightField {
  constructor() {
    this.river = new Line2(RIVER, 120);
    this.outflow = new Line2(OUTFLOW, 40);
    this.paths = PATHS.map((p) => ({ w: p.w, line: new Line2(p.pts, 60) }));
    this.clearings = CLEARINGS.map((c) => ({ ...c, h: this.base(c.x, c.z) }));
    // River bed: running minimum of the ground along the creek so water always flows downhill.
    const N = 120;
    this.bed = [];
    let m = Infinity;
    for (let i = 0; i <= N; i++) {
      const p = this.river.at(i / N);
      m = Math.min(m, this.flat(p.x, p.z) - 1.4);
      const toLake = smooth(0.8, 1, i / N);
      this.bed.push(lerp(m, LAKE.level - 0.9, toLake));
    }
    for (let i = 1; i <= N; i++) this.bed[i] = Math.min(this.bed[i], this.bed[i - 1]);
    // Height grid used for fast lookups.
    this.grid = new Float32Array((RES + 1) * (RES + 1));
    for (let j = 0; j <= RES; j++)
      for (let i = 0; i <= RES; i++) {
        const x = -HALF + (i / RES) * BOARD, z = -HALF + (j / RES) * BOARD;
        this.grid[j * (RES + 1) + i] = this.compute(x, z);
      }
  }

  base(x, z) {
    let h = 4 + fbm(x * 0.017 + 3.1, z * 0.017 - 1.7, 5) * 7 + fbm(x * 0.07, z * 0.07, 3) * 1.2;
    const m = smooth(-38, -95, z);
    h += m * (16 + fbm(x * 0.028 + 7, z * 0.03, 4) * 14);
    for (const [hx, hz, a, r] of HILLS) {
      const d2 = ((x - hx) ** 2 + (z - hz) ** 2) / (r * r);
      h += a * Math.exp(-d2 * 1.4);
    }
    // gentle rise toward the board edges keeps the forest in a bowl
    const e = Math.max(Math.abs(x), Math.abs(z)) / HALF;
    h += smooth(0.75, 1, e) * 3;
    return h;
  }

  // base terrain with clearings flattened
  flat(x, z) {
    let h = this.base(x, z);
    for (const c of this.clearings || []) {
      const d = Math.hypot(x - c.x, z - c.z);
      const k = 1 - smooth(c.r * 0.6, c.r * 1.25, d);
      h = lerp(h, c.h, k * 0.9);
    }
    return h;
  }

  compute(x, z) {
    let h = this.flat(x, z);
    // creek
    const r = this.river.closest(x, z);
    const w = this.riverWidth(r.t);
    const bed = this.bedAt(r.t);
    let k = 1 - smooth(w * 0.7, w + 5, r.d);
    h = Math.min(h, lerp(h, bed - 0.4 * (1 - r.d / (w + 5)), k));
    // waterfall pool
    const [px, pz] = WATERFALL.pool;
    const dp = Math.hypot(x - px, z - pz);
    h = Math.min(h, lerp(h, this.bed[0] - 0.6, 1 - smooth(3, 8, dp)));
    // outflow
    const o = this.outflow.closest(x, z);
    const ob = LAKE.level - 1 - o.t * 1.5;
    k = 1 - smooth(2.2, 7, o.d);
    h = Math.min(h, lerp(h, ob, k));
    // lake basin
    const e = Math.hypot((x - LAKE.x) / LAKE.rx, (z - LAKE.z) / LAKE.rz);
    const lb = LAKE.level - 0.6 - 2.8 * smooth(0.95, 0.2, e);
    h = Math.min(h, lerp(h, lb, 1 - smooth(0.85, 1.35, e)));
    // keep dry land above the lake and creek near the lake
    if (e > 1.12 && k < 0.05 && r.d > w + 4 && dp > 8) h = Math.max(h, LAKE.level + 0.5);
    return h;
  }

  riverWidth(t) {
    return 1.6 + t * 2.4;
  }
  bedAt(t) {
    const f = clamp(t, 0, 1) * (this.bed.length - 1);
    const i = Math.floor(f);
    return lerp(this.bed[i], this.bed[Math.min(i + 1, this.bed.length - 1)], f - i);
  }

  // bilinear lookup on the grid
  h(x, z) {
    const fx = clamp(((x + HALF) / BOARD) * RES, 0, RES - 1e-4), fz = clamp(((z + HALF) / BOARD) * RES, 0, RES - 1e-4);
    const i = Math.floor(fx), j = Math.floor(fz), u = fx - i, v = fz - j;
    const g = this.grid, W = RES + 1;
    const a = g[j * W + i], b = g[j * W + i + 1], c = g[(j + 1) * W + i], d = g[(j + 1) * W + i + 1];
    return a * (1 - u) * (1 - v) + b * u * (1 - v) + c * (1 - u) * v + d * u * v;
  }

  normalY(x, z) {
    const e = 0.8;
    const dx = this.h(x + e, z) - this.h(x - e, z), dz = this.h(x, z + e) - this.h(x, z - e);
    return 2 * e / Math.hypot(dx, 2 * e, dz);
  }

  pathDist(x, z) {
    let best = Infinity;
    for (const p of this.paths) best = Math.min(best, p.line.closest(x, z).d - p.w * 0.5);
    return best;
  }

  waterDist(x, z) {
    const r = this.river.closest(x, z);
    const o = this.outflow.closest(x, z);
    const e = Math.hypot((x - LAKE.x) / LAKE.rx, (z - LAKE.z) / LAKE.rz);
    const [px, pz] = WATERFALL.pool;
    return Math.min(r.d - this.riverWidth(r.t), o.d - 2.6, (e - 1) * Math.min(LAKE.rx, LAKE.rz), Math.hypot(x - px, z - pz) - 4);
  }
}

// ---------------------------------------------------------------------------------------------

export function buildTerrain(hf, palette) {
  const geo = new THREE.PlaneGeometry(BOARD, BOARD, RES, RES);
  geo.rotateX(-Math.PI / 2);
  const pos = geo.attributes.position;
  const n = pos.count;
  const mask = new Float32Array(n * 4);
  const noise = new Float32Array(n);
  for (let v = 0; v < n; v++) {
    const x = pos.getX(v), z = pos.getZ(v);
    const y = hf.h(x, z);
    pos.setY(v, y);
    const pd = hf.pathDist(x, z);
    const wd = hf.waterDist(x, z);
    let meadow = 0;
    for (const c of CLEARINGS) if (c.meadow) meadow = Math.max(meadow, 1 - smooth(c.r * 0.6, c.r * 1.4, Math.hypot(x - c.x, z - c.z)));
    mask[v * 4] = 1 - smooth(0, 1.2, pd);
    mask[v * 4 + 1] = 0; // rock, filled after normals
    mask[v * 4 + 2] = 1 - smooth(0.5, 3.5, wd);
    mask[v * 4 + 3] = meadow;
    noise[v] = fbm(x * 0.08 + 11, z * 0.08 - 4, 3) * 0.5 + 0.5;
  }
  geo.computeVertexNormals();
  const nrm = geo.attributes.normal;
  for (let v = 0; v < n; v++) {
    const y = pos.getY(v);
    mask[v * 4 + 1] = Math.max(smooth(0.86, 0.68, nrm.getY(v)), smooth(26, 40, y) * 0.8);
  }
  geo.setAttribute('aMask', new THREE.BufferAttribute(mask, 4));
  geo.setAttribute('aNoise', new THREE.BufferAttribute(noise, 1));

  const uni = {
    uGrass: { value: new THREE.Color() }, uGrass2: { value: new THREE.Color() }, uMeadow: { value: new THREE.Color() },
    uDirt: { value: new THREE.Color() }, uRock: { value: new THREE.Color() }, uBank: { value: new THREE.Color() },
    uFlowers: { value: 0 }, uLitter: { value: 0 },
  };
  const mat = new THREE.MeshStandardMaterial({ roughness: 0.95, metalness: 0 });
  mat.onBeforeCompile = (sh) => {
    Object.assign(sh.uniforms, uni);
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', `#include <common>
        attribute vec4 aMask; attribute float aNoise; varying vec4 vMask; varying float vNoise; varying vec3 vWP;`)
      .replace('#include <begin_vertex>', `#include <begin_vertex>
        vMask = aMask; vNoise = aNoise; vWP = (modelMatrix * vec4(transformed, 1.0)).xyz;`);
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', `#include <common>
        varying vec4 vMask; varying float vNoise; varying vec3 vWP;
        uniform vec3 uGrass, uGrass2, uMeadow, uDirt, uRock, uBank; uniform float uFlowers, uLitter;
        float hh(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }`)
      .replace('#include <color_fragment>', `#include <color_fragment>
        {
          vec3 c = mix(uGrass2, uGrass, smoothstep(0.25, 0.75, vNoise));
          c = mix(c, uMeadow, vMask.w);
          // speckles: flowers in spring and summer, fallen leaves in autumn
          vec2 cell = floor(vWP.xz * 2.2);
          float r = hh(cell);
          float grassy = (1.0 - vMask.x) * (1.0 - vMask.y) * (1.0 - vMask.z);
          float fl = step(0.93 - 0.12 * vMask.w, r) * uFlowers * grassy;
          vec3 fc = r > 0.975 ? vec3(1.0, 0.92, 0.35) : (r > 0.955 ? vec3(1.0, 0.62, 0.78) : vec3(0.98, 0.98, 1.0));
          c = mix(c, fc, fl);
          float lt = step(0.6, hh(cell + 7.0)) * uLitter * grassy;
          vec3 lc = mix(vec3(0.85, 0.42, 0.16), vec3(0.93, 0.7, 0.2), hh(cell + 3.0));
          c = mix(c, lc, lt * 0.7);
          c = mix(c, uBank, vMask.z);
          c = mix(c, uRock * (0.85 + 0.3 * vNoise), vMask.y);
          c = mix(c, uDirt * (0.92 + 0.16 * vNoise), vMask.x * 0.92);
          diffuseColor.rgb = c;
        }`);
  };
  snowify(mat, { key: 'terrain', snowLo: 0.55, snowHi: 0.8 });
  const mesh = new THREE.Mesh(geo, mat);
  mesh.receiveShadow = true;
  mesh.name = 'terrain';
  mesh.userData.setSeason = (p) => {
    uni.uGrass.value.copy(p.grass);
    uni.uGrass2.value.copy(p.grass2);
    uni.uMeadow.value.copy(p.meadow);
    uni.uDirt.value.copy(p.dirt);
    uni.uRock.value.copy(p.rock);
    uni.uBank.value.copy(p.bank);
    uni.uFlowers.value = p.flowers;
    uni.uLitter.value = p.litter;
  };
  mesh.userData.setSeason(palette);
  return mesh;
}

// Diorama board: cut soil sides and a wooden plinth.
export function buildBoard(hf) {
  const g = new THREE.Group();
  const bottom = -7;
  const positions = [], colors = [], idx = [];
  const strata = [
    [0, new THREE.Color('#6f9a45')],
    [0.6, new THREE.Color('#7a5536')],
    [3, new THREE.Color('#8d6a47')],
    [5, new THREE.Color('#a68a64')],
    [8, new THREE.Color('#7d756c')],
    [40, new THREE.Color('#6e6a66')],
  ];
  const colAt = (depth) => {
    for (let i = 1; i < strata.length; i++)
      if (depth <= strata[i][0]) {
        const k = (depth - strata[i - 1][0]) / (strata[i][0] - strata[i - 1][0]);
        return strata[i - 1][1].clone().lerp(strata[i][1], k);
      }
    return strata[strata.length - 1][1].clone();
  };
  const edges = [
    (t) => [-HALF + t * BOARD, HALF, 0, 0, 1],
    (t) => [HALF, HALF - t * BOARD, 1, 0, 0],
    (t) => [HALF - t * BOARD, -HALF, 0, 0, -1],
    (t) => [-HALF, -HALF + t * BOARD, -1, 0, 0],
  ];
  const N = RES;
  const layers = [0, 0.6, 3, 5, 8];
  for (const edge of edges) {
    const base = positions.length / 3;
    for (let i = 0; i <= N; i++) {
      const [x, z] = edge(i / N);
      const top = hf.h(x, z);
      const ds = [...layers.filter((d) => top - d > bottom), top - bottom];
      const rows = [...layers, top - bottom];
      for (let r = 0; r < rows.length; r++) {
        const d = Math.min(rows[r], top - bottom);
        const wav = r > 0 && r < rows.length - 1 ? Math.sin(i * 0.3 + r) * 0.25 : 0;
        positions.push(x, top - d + wav, z);
        const c = colAt(d);
        colors.push(c.r, c.g, c.b);
      }
      void ds;
    }
    const R = layers.length + 1;
    for (let i = 0; i < N; i++)
      for (let r = 0; r < R - 1; r++) {
        const a = base + i * R + r, b = base + (i + 1) * R + r;
        idx.push(a, b, a + 1, b, b + 1, a + 1);
      }
  }
  const sg = new THREE.BufferGeometry();
  sg.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  sg.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
  sg.setIndex(idx);
  sg.computeVertexNormals();
  const side = new THREE.Mesh(sg, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 1, side: THREE.DoubleSide }));
  side.receiveShadow = true;
  g.add(side);

  const wood = new THREE.MeshStandardMaterial({ color: '#5a3b26', roughness: 0.7 });
  const plinth = new THREE.Mesh(new THREE.BoxGeometry(BOARD + 6, 4, BOARD + 6), wood);
  plinth.position.y = bottom - 2;
  plinth.receiveShadow = true;
  g.add(plinth);
  const trim = new THREE.Mesh(new THREE.BoxGeometry(BOARD + 8, 0.8, BOARD + 8), new THREE.MeshStandardMaterial({ color: '#3e2818', roughness: 0.6 }));
  trim.position.y = bottom - 4.2;
  g.add(trim);
  return g;
}

// ---------------------------------------------------------------------------------------------
// Water: creek ribbon, lake, outflow, waterfall. One shader handles flowing water and ice.

const waterVert = /* glsl */ `
  varying vec2 vUv; varying vec3 vWP; varying float vEdge;
  attribute float aEdge;
  #include <fog_pars_vertex>
  void main(){
    vUv = uv; vEdge = aEdge;
    vec4 wp = modelMatrix * vec4(position, 1.0);
    vWP = wp.xyz;
    vec4 mvPosition = viewMatrix * wp;
    gl_Position = projectionMatrix * mvPosition;
    #include <fog_vertex>
  }`;
const waterFrag = /* glsl */ `
  uniform float uTime, uIce, uFlow, uNight, uFall;
  uniform vec3 uShallow, uDeep, uSky;
  varying vec2 vUv; varying vec3 vWP; varying float vEdge;
  #include <fog_pars_fragment>
  float hh(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
  float vn(vec2 p){ vec2 i=floor(p), f=fract(p); f=f*f*(3.0-2.0*f);
    return mix(mix(hh(i),hh(i+vec2(1,0)),f.x), mix(hh(i+vec2(0,1)),hh(i+vec2(1,1)),f.x), f.y); }
  void main(){
    vec2 p = vWP.xz * 0.35;
    float flow = uTime * uFlow;
    float w;
    if (uFall > 0.5) {
      w = vn(vec2(vUv.x * 24.0, vUv.y * 6.0 + uTime * 3.5));
    } else {
      w = vn(p + vec2(flow * 0.3, flow)) * 0.6 + vn(p * 2.3 - vec2(uTime * 0.21, -uTime * 0.17)) * 0.4;
    }
    vec3 col = mix(uDeep, uShallow, smoothstep(0.0, 1.0, vEdge));
    col = mix(col, uSky, 0.18);
    float spark = smoothstep(0.72, 0.95, w);
    col += spark * 0.22 * (1.0 - uIce);
    if (uFall > 0.5) col = mix(col, vec3(0.92, 0.97, 1.0), smoothstep(0.35, 0.9, w) * (1.0 - uIce));
    // ice: pale, with cracks and frosted rims
    float crack = smoothstep(0.03, 0.0, abs(vn(vWP.xz * 0.18) - 0.5)) * 0.5 + smoothstep(0.02, 0.0, abs(vn(vWP.xz * 0.5 + 9.0) - 0.5)) * 0.25;
    vec3 ice = mix(vec3(0.78, 0.89, 0.95), vec3(0.95, 0.98, 1.0), vn(vWP.xz * 0.6));
    ice = mix(ice, vec3(1.0), smoothstep(0.6, 1.0, vEdge) * 0.6);
    ice -= crack * 0.18;
    col = mix(col, ice, uIce);
    col *= mix(1.0, 0.35, uNight);
    float a = mix(0.9, 0.98, uIce);
    gl_FragColor = vec4(col, a);
    #include <colorspace_fragment>
    #include <fog_fragment>
  }`;

export function buildWater(hf) {
  const g = new THREE.Group();
  const uni = THREE.UniformsUtils.merge([
    THREE.UniformsLib.fog,
    {
      uIce: { value: 0 }, uFlow: { value: 0.6 }, uFall: { value: 0 },
      uShallow: { value: new THREE.Color() }, uDeep: { value: new THREE.Color() }, uSky: { value: new THREE.Color('#bfe3f5') },
    },
  ]);
  uni.uTime = U.uTime;
  uni.uNight = U.uNight;
  const mk = (extra = {}) => {
    const m = new THREE.ShaderMaterial({
      uniforms: { ...uni, ...extra }, vertexShader: waterVert, fragmentShader: waterFrag,
      transparent: true, fog: true, depthWrite: false,
    });
    return m;
  };
  const mat = mk();
  const fallMat = mk({ uFall: { value: 1 }, uFlow: { value: 1 } });

  // creek ribbon
  const ribbon = (line, widthAt, yAt, segs) => {
    const pos = [], uv = [], edge = [], idx = [];
    for (let i = 0; i <= segs; i++) {
      const t = i / segs;
      const p = line.at(t);
      const l = Math.hypot(p.dx, p.dz) || 1;
      const nx = -p.dz / l, nz = p.dx / l;
      const w = widthAt(t);
      const y = yAt(t);
      for (const s of [-1, -0.5, 0, 0.5, 1]) {
        pos.push(p.x + nx * w * s, y, p.z + nz * w * s);
        uv.push(s * 0.5 + 0.5, t * line.total * 0.1);
        edge.push(Math.abs(s));
      }
    }
    for (let i = 0; i < segs; i++)
      for (let s = 0; s < 4; s++) {
        const a = i * 5 + s, b = a + 5;
        idx.push(a, a + 1, b, b, a + 1, b + 1);
      }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    geo.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
    geo.setAttribute('aEdge', new THREE.Float32BufferAttribute(edge, 1));
    geo.setIndex(idx);
    return geo;
  };
  const creek = new THREE.Mesh(
    ribbon(hf.river, (t) => hf.riverWidth(t) + 1.2, (t) => Math.max(hf.bedAt(t) + 0.9, t > 0.9 ? LAKE.level : -99), 220),
    mat
  );
  creek.renderOrder = 2;
  g.add(creek);
  const out = new THREE.Mesh(ribbon(hf.outflow, () => 3.4, (t) => LAKE.level - 0.15 - t * 1.4, 60), mat);
  out.renderOrder = 2;
  g.add(out);

  // lake: ellipse fan with edge attribute
  {
    const pos = [LAKE.x, LAKE.level, LAKE.z], edge = [0], uv = [0.5, 0.5], idx = [];
    const R = 72;
    for (const ring of [0.55, 0.85, 1.14]) {
      for (let i = 0; i < R; i++) {
        const a = (i / R) * Math.PI * 2;
        const wob = 1 + Math.sin(a * 3 + 1) * 0.04;
        pos.push(LAKE.x + Math.cos(a) * LAKE.rx * ring * wob, LAKE.level, LAKE.z + Math.sin(a) * LAKE.rz * ring * wob);
        edge.push(ring / 1.14);
        uv.push(0, 0);
      }
    }
    for (let i = 0; i < R; i++) idx.push(0, 1 + ((i + 1) % R), 1 + i);
    for (let r = 0; r < 2; r++)
      for (let i = 0; i < R; i++) {
        const a = 1 + r * R + i, b = 1 + r * R + ((i + 1) % R), c = a + R, d = b + R;
        idx.push(a, b, c, b, d, c);
      }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    geo.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
    geo.setAttribute('aEdge', new THREE.Float32BufferAttribute(edge, 1));
    geo.setIndex(idx);
    const lake = new THREE.Mesh(geo, mat);
    lake.renderOrder = 2;
    g.add(lake);
  }

  // waterfall pool
  {
    const [px, pz] = WATERFALL.pool;
    const geo = new THREE.CircleGeometry(5.2, 32);
    geo.rotateX(-Math.PI / 2);
    const n = geo.attributes.position.count;
    const e = new Float32Array(n);
    for (let i = 0; i < n; i++) e[i] = Math.hypot(geo.attributes.position.getX(i), geo.attributes.position.getZ(i)) / 5.2;
    geo.setAttribute('aEdge', new THREE.BufferAttribute(e, 1));
    const pool = new THREE.Mesh(geo, mat);
    pool.position.set(px, hf.bed[0] + 0.9, pz);
    pool.renderOrder = 2;
    g.add(pool);
  }

  // waterfall sheet: follows the slope from the top down to the pool
  {
    const [tx, tz] = WATERFALL.top, [px, pz] = WATERFALL.pool;
    const pos = [], uv = [], edge = [], idx = [];
    const S = 24;
    const dx = px - tx, dz = pz - tz, l = Math.hypot(dx, dz);
    const nx = -dz / l, nz = dx / l;
    for (let i = 0; i <= S; i++) {
      const t = i / S;
      const x = lerp(tx, px - dx / l * 3.5, t), z = lerp(tz, pz - dz / l * 3.5, t);
      const y = Math.max(hf.h(x, z) + 0.7, hf.bed[0] + 0.9);
      const w = 1.6 + t * 1.4;
      for (const s of [-1, 0, 1]) {
        pos.push(x + nx * w * s, y, z + nz * w * s);
        uv.push(s * 0.5 + 0.5, -t);
        edge.push(Math.abs(s));
      }
    }
    for (let i = 0; i < S; i++)
      for (let s = 0; s < 2; s++) {
        const a = i * 3 + s, b = a + 3;
        idx.push(a, a + 1, b, b, a + 1, b + 1);
      }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    geo.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
    geo.setAttribute('aEdge', new THREE.Float32BufferAttribute(edge, 1));
    geo.setIndex(idx);
    const fall = new THREE.Mesh(geo, fallMat);
    fall.renderOrder = 3;
    g.add(fall);
  }

  g.userData.setSeason = (p) => {
    for (const m of [mat, fallMat]) {
      m.uniforms.uShallow.value.copy(p.water);
      m.uniforms.uDeep.value.copy(p.waterDeep);
      m.uniforms.uIce.value = p.ice;
      m.uniforms.uSky.value.copy(p.skyBottom);
    }
  };
  return g;
}
