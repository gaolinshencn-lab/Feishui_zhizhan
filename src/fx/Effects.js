import * as THREE from 'three';
import { infantryGeometry } from '../army/figures.js';

const smoothstep = (a, b, x) => {
  const t = Math.min(1, Math.max(0, (x - a) / (b - a)));
  return t * t * (3 - 2 * t);
};
/** 0 → 1 → 0 envelope over [t0, t1] with soft edges (in timeline units). */
function envelope(T, t0, t1, edge = 0.04) {
  if (T < t0 || T > t1) return 0;
  return Math.min(smoothstep(t0, t0 + edge, T), 1 - smoothstep(t1 - edge, t1, T));
}
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

const POINT_VERT = /* glsl */ `
attribute float aSize;
attribute float aAlpha;
attribute vec3 aColor;
uniform float uScale;
varying float vAlpha;
varying vec3 vColor;
void main() {
  vAlpha = aAlpha;
  vColor = aColor;
  vec4 mv = modelViewMatrix * vec4(position, 1.0);
  gl_PointSize = aSize * uScale / max(-mv.z, 0.01);
  gl_Position = projectionMatrix * mv;
}`;
const POINT_FRAG = /* glsl */ `
varying float vAlpha;
varying vec3 vColor;
uniform float uSoft;
void main() {
  vec2 d = gl_PointCoord - 0.5;
  float r = length(d) * 2.0;
  float a = 1.0 - smoothstep(uSoft, 1.0, r);
  if (a < 0.01) discard;
  gl_FragColor = vec4(vColor, a * vAlpha);
}`;

class Points {
  constructor(max, additive, soft) {
    this.max = max;
    const g = new THREE.BufferGeometry();
    this.pos = new Float32Array(max * 3);
    this.size = new Float32Array(max);
    this.alpha = new Float32Array(max);
    this.color = new Float32Array(max * 3);
    g.setAttribute('position', new THREE.BufferAttribute(this.pos, 3).setUsage(THREE.DynamicDrawUsage));
    g.setAttribute('aSize', new THREE.BufferAttribute(this.size, 1).setUsage(THREE.DynamicDrawUsage));
    g.setAttribute('aAlpha', new THREE.BufferAttribute(this.alpha, 1).setUsage(THREE.DynamicDrawUsage));
    g.setAttribute('aColor', new THREE.BufferAttribute(this.color, 3).setUsage(THREE.DynamicDrawUsage));
    g.setDrawRange(0, 0);
    this.uniforms = { uScale: { value: 800 }, uSoft: { value: soft } };
    const m = new THREE.ShaderMaterial({
      uniforms: this.uniforms,
      vertexShader: POINT_VERT,
      fragmentShader: POINT_FRAG,
      transparent: true,
      depthWrite: false,
      blending: additive ? THREE.AdditiveBlending : THREE.NormalBlending,
    });
    this.obj = new THREE.Points(g, m);
    this.obj.frustumCulled = false;
    this.obj.renderOrder = additive ? 9 : 8;
    this.n = 0;
  }
  begin() {
    this.n = 0;
  }
  push(x, y, z, size, alpha, r, g, b) {
    if (this.n >= this.max) return;
    const i = this.n++;
    this.pos[i * 3] = x;
    this.pos[i * 3 + 1] = y;
    this.pos[i * 3 + 2] = z;
    this.size[i] = size;
    this.alpha[i] = alpha;
    this.color[i * 3] = r;
    this.color[i * 3 + 1] = g;
    this.color[i * 3 + 2] = b;
  }
  end() {
    const g = this.obj.geometry;
    g.setDrawRange(0, this.n);
    for (const k of ['position', 'aSize', 'aAlpha', 'aColor']) g.attributes[k].needsUpdate = true;
  }
}

const KIND = {
  smoke: { life: [3.2, 5.5], size: [0.35, 1.5], rise: [0.12, 0.28], drift: 0.08, alpha: 0.32, color: [0.33, 0.31, 0.3] },
  dust: { life: [1.8, 3.2], size: [0.25, 0.8], rise: [0.02, 0.07], drift: 0.12, alpha: 0.28, color: [0.6, 0.52, 0.38] },
  fire: { life: [0.5, 1.1], size: [0.22, 0.06], rise: [0.3, 0.6], drift: 0.03, alpha: 0.95, color: [1.0, 0.5, 0.14], glow: true },
};

/** Smoke, dust and fire, unit torches and campfires, 草木皆兵 ghosts, 风声鹤唳 cranes and wind. */
export class EffectsLayer {
  constructor(resolver, fx, { units, props, terrain, scale = 1 }) {
    this.R = resolver;
    this.proj = resolver.proj;
    this.fx = fx;
    this.units = units;
    this.props = props;
    this.terrain = terrain;
    this.scale = scale;
    this.group = new THREE.Group();
    this.group.name = 'effects';
    this.smoke = new Points(1800, false, 0.15);
    this.glow = new Points(2200, true, 0.0);
    this.group.add(this.smoke.obj, this.glow.obj);
    this.parts = [];
    this.rand = rng(4242);
    this.emitters = (fx.emitters || []).map((e) => {
      const [x, z] = this.R.point(e.at);
      return { ...e, x, z, acc: 0 };
    });
    if (fx.ghosts) this.buildGhosts(fx.ghosts);
    if (fx.gaze) this.buildGaze(fx.gaze);
    if (fx.cranes) this.buildCranes(fx.cranes);
    if (fx.wind) this.buildWind(fx.wind);
  }

  // ---------------------------------------------------------------------------
  buildGhosts(g) {
    const [lon0, lat0, lon1, lat1] = g.bbox;
    const [x0, z1] = this.proj.geoToWorld(lon0, lat0);
    const [x1, z0] = this.proj.geoToWorld(lon1, lat1);
    let pts = (this.props?.treePositions || []).filter(([x, , z]) => x > x0 && x < x1 && z > z0 && z < z1);
    const r = rng(77);
    pts = pts.sort(() => r() - 0.5).slice(0, g.n);
    const mesh = new THREE.InstancedMesh(
      infantryGeometry('jin'),
      new THREE.MeshBasicMaterial({ color: '#ffffff', transparent: true, opacity: 1, blending: THREE.AdditiveBlending, depthWrite: false }),
      Math.max(1, pts.length)
    );
    const m = new THREE.Matrix4();
    const q = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), Math.PI);
    this.ghostPhase = [];
    pts.forEach(([x, y, z], i) => {
      const s = 0.12 + r() * 0.06;
      m.compose(new THREE.Vector3(x, y + 0.02, z), q, new THREE.Vector3(s, s, s));
      mesh.setMatrixAt(i, m);
      mesh.setColorAt(i, new THREE.Color(0, 0, 0));
      this.ghostPhase.push(r() * Math.PI * 2);
    });
    mesh.renderOrder = 7;
    mesh.frustumCulled = false;
    mesh.visible = false;
    this.ghosts = mesh;
    this.group.add(mesh);
  }

  buildGaze(g) {
    const [ax, az] = this.R.point(g.from);
    const ay = this.proj.groundY(ax, az) + 0.35;
    const pts = g.to.map((p) => {
      const [x, z] = this.R.point(p);
      return [x, this.proj.groundY(x, z) + 0.45, z];
    });
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.Float32BufferAttribute([ax, ay, az, ...pts[0], ...pts[1]], 3));
    geo.setAttribute('aT', new THREE.Float32BufferAttribute([0, 1, 1], 1));
    this.gazeU = { uOpacity: { value: 0 }, uTime: { value: 0 } };
    const mat = new THREE.ShaderMaterial({
      uniforms: this.gazeU,
      vertexShader: `attribute float aT; varying float vT; void main(){ vT = aT; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }`,
      fragmentShader: `uniform float uOpacity; uniform float uTime; varying float vT;
        void main(){ float band = 0.5 + 0.5 * sin(vT * 30.0 - uTime * 3.0); gl_FragColor = vec4(1.0, 0.86, 0.6, uOpacity * (0.18 + 0.12 * band) * (1.0 - vT * 0.6)); }`,
      transparent: true,
      depthWrite: false,
      side: THREE.DoubleSide,
      blending: THREE.AdditiveBlending,
    });
    this.gaze = new THREE.Mesh(geo, mat);
    this.gaze.visible = false;
    this.gaze.frustumCulled = false;
    this.group.add(this.gaze);
  }

  buildCranes(c) {
    // body, neck and two wings; x encodes distance from the body for the flap
    const verts = [];
    const cols = [];
    const tri = (a, b, d, col) => {
      verts.push(...a, ...b, ...d);
      for (let i = 0; i < 3; i++) cols.push(...col);
    };
    const white = [0.96, 0.95, 0.92];
    const black = [0.08, 0.08, 0.09];
    const red = [0.8, 0.12, 0.1];
    // wings (left/right) with black tips
    tri([0, 0, 0.12], [-0.45, 0, 0.0], [0, 0, -0.12], white);
    tri([-0.45, 0, 0.0], [-0.75, 0, -0.1], [-0.42, 0, -0.08], black);
    tri([0, 0, 0.12], [0, 0, -0.12], [0.45, 0, 0.0], white);
    tri([0.45, 0, 0.0], [0.42, 0, -0.08], [0.75, 0, -0.1], black);
    // body + neck + head + legs
    tri([-0.06, 0, 0.18], [0.06, 0, 0.18], [0, 0.02, -0.22], white);
    tri([-0.02, 0, 0.18], [0.02, 0, 0.18], [0, 0.0, 0.48], black);
    tri([-0.03, 0, 0.46], [0.03, 0, 0.46], [0, 0, 0.56], red);
    tri([-0.015, 0, -0.2], [0.015, 0, -0.2], [0, -0.01, -0.5], black);
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.Float32BufferAttribute(verts, 3));
    geo.setAttribute('color', new THREE.Float32BufferAttribute(cols, 3));
    geo.computeVertexNormals();
    const count = c.flocks.length * c.n;
    const mat = new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.DoubleSide, transparent: true, opacity: 1 });
    const u = { uTime: { value: 0 } };
    mat.onBeforeCompile = (sh) => {
      sh.uniforms.uTime = u.uTime;
      sh.vertexShader = sh.vertexShader
        .replace('#include <common>', '#include <common>\nuniform float uTime;')
        .replace(
          '#include <begin_vertex>',
          `#include <begin_vertex>
float wingSpan = abs(position.x);
float ph = uTime * 6.5 + float(gl_InstanceID) * 1.7;
transformed.y += sin(ph) * wingSpan * 0.75;`
        );
    };
    mat.customProgramCacheKey = () => 'crane';
    this.craneU = u;
    const mesh = new THREE.InstancedMesh(geo, mat, count);
    mesh.frustumCulled = false;
    mesh.visible = false;
    this.cranes = mesh;
    this.craneData = c;
    const r = rng(9);
    this.craneOff = [];
    for (let i = 0; i < count; i++) {
      const k = i % c.n;
      const side = k % 2 === 0 ? 1 : -1;
      const rank = Math.ceil(k / 2);
      this.craneOff.push([side * rank * 0.55 + (r() - 0.5) * 0.2, -rank * 0.5 + (r() - 0.5) * 0.2, (r() - 0.5) * 0.4, r() * 6]);
    }
    this.flockPts = c.flocks.map(([a, b]) => [this.R.point(a), this.R.point(b)]);
    this.group.add(mesh);
  }

  buildWind(w) {
    const geo = new THREE.PlaneGeometry(1.4, 0.012);
    geo.rotateX(-Math.PI / 2);
    const mat = new THREE.MeshBasicMaterial({ color: '#f3ead6', transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false });
    const mesh = new THREE.InstancedMesh(geo, mat, w.n);
    mesh.frustumCulled = false;
    mesh.visible = false;
    this.wind = mesh;
    const [cx, cz] = this.R.point(w.at);
    this.windC = [cx, cz];
    const r = rng(31);
    this.windSeeds = Array.from({ length: w.n }, () => [r(), r(), r(), r()]);
    this.group.add(mesh);
  }

  // ---------------------------------------------------------------------------
  spawn(e, kind) {
    const k = KIND[kind];
    const r = this.rand;
    const a = r() * Math.PI * 2;
    const d = Math.sqrt(r()) * e.radius;
    const x = e.x + Math.cos(a) * d;
    const z = e.z + Math.sin(a) * d;
    const s = (e.scale ?? 1) * this.scale;
    this.parts.push({
      x,
      y: this.proj.groundY(x, z) + 0.03 * s,
      z,
      vx: (r() - 0.3) * k.drift * s,
      vz: (r() - 0.7) * k.drift * s,
      vy: (k.rise[0] + r() * (k.rise[1] - k.rise[0])) * s,
      age: 0,
      life: k.life[0] + r() * (k.life[1] - k.life[0]),
      kind,
      s,
    });
  }

  setVisible(v) {
    this.group.visible = v;
    if (!v) this.parts.length = 0;
  }

  update(T, time, dt, camera, viewH) {
    if (!this.group.visible) return;
    const scaleUniform = viewH / (2 * Math.tan((camera.fov * Math.PI) / 360));
    this.smoke.uniforms.uScale.value = scaleUniform;
    this.glow.uniforms.uScale.value = scaleUniform;

    // emitters
    for (const e of this.emitters) {
      const env = envelope(T, e.t0, e.t1, 0.03);
      if (env <= 0) continue;
      e.acc += dt * e.rate * env;
      while (e.acc >= 1) {
        e.acc -= 1;
        this.spawn(e, e.kind);
        if (e.kind === 'fire' && this.rand() < 0.35) this.spawn(e, 'smoke');
      }
    }
    // simulate
    this.smoke.begin();
    this.glow.begin();
    const keep = [];
    for (const p of this.parts) {
      p.age += dt;
      if (p.age >= p.life) continue;
      p.x += p.vx * dt;
      p.y += p.vy * dt;
      p.z += p.vz * dt;
      const k = KIND[p.kind];
      const f = p.age / p.life;
      const size = (k.size[0] + (k.size[1] - k.size[0]) * f) * p.s;
      const alpha = k.alpha * Math.min(1, f * 6) * (1 - f);
      if (k.glow) {
        const g = 1 - f;
        this.glow.push(p.x, p.y, p.z, size, alpha, k.color[0], k.color[1] * (0.6 + 0.6 * g), k.color[2] * g);
      } else {
        this.smoke.push(p.x, p.y, p.z, size, alpha, k.color[0], k.color[1], k.color[2]);
      }
      keep.push(p);
    }
    this.parts = keep;

    // torches carried by marching units at night
    const tor = this.fx.torches;
    if (tor && this.units) {
      const env = envelope(T, tor.t0, tor.t1, 0.02);
      if (env > 0) {
        for (const id of tor.units) {
          const u = this.units.byId[id];
          if (!u || !u.visible) continue;
          const fs = this.units.opts.figScale;
          for (let i = 0; i < u.N; i += tor.every) {
            if (T >= u.deathT[i]) continue;
            const x = u.pos[i * 2];
            const z = u.pos[i * 2 + 1];
            const y = this.proj.groundY(x, z) + fs * 1.7;
            const fl = 0.75 + 0.25 * Math.sin(time * 13 + i * 2.1) * Math.sin(time * 7.3 + i);
            this.glow.push(x, y, z, fs * 1.9 * fl, 0.9 * env, 1.0, 0.62, 0.22);
            this.glow.push(x, y, z, fs * 5.5, 0.12 * env, 1.0, 0.45, 0.15);
          }
        }
      }
    }
    for (const cf of this.fx.campfires || []) {
      const env = envelope(T, cf.t0, cf.t1, 0.02);
      if (env <= 0) continue;
      if (!cf.pts) {
        const [cx, cz] = this.R.point(cf.at);
        const r = rng(cf.n * 13);
        cf.pts = Array.from({ length: cf.n }, () => {
          const a = r() * Math.PI * 2;
          const d = Math.sqrt(r()) * cf.radius;
          const x = cx + Math.cos(a) * d;
          const z = cz + Math.sin(a) * d;
          return [x, this.proj.groundY(x, z) + 0.04, z];
        });
      }
      cf.pts.forEach(([x, y, z], i) => {
        const fl = 0.8 + 0.2 * Math.sin(time * 11 + i * 3.7);
        this.glow.push(x, y, z, 0.14 * fl, 0.95 * env, 1.0, 0.6, 0.2);
        this.glow.push(x, y + 0.02, z, 0.6, 0.18 * env, 1.0, 0.45, 0.12);
      });
    }
    this.smoke.end();
    this.glow.end();

    // 草木皆兵
    if (this.ghosts) {
      const g = this.fx.ghosts;
      const env = envelope(T, g.t0, g.t1, 0.05);
      this.ghosts.visible = env > 0;
      if (env > 0) {
        const c = new THREE.Color();
        for (let i = 0; i < this.ghostPhase.length; i++) {
          const s = Math.max(0, Math.sin(time * 1.4 + this.ghostPhase[i]));
          const v = env * (0.1 + 0.42 * s * s);
          c.setRGB(0.62 * v, 0.68 * v, 0.82 * v);
          this.ghosts.setColorAt(i, c);
        }
        this.ghosts.instanceColor.needsUpdate = true;
      }
    }
    if (this.gaze) {
      const env = envelope(T, this.fx.gaze.t0, this.fx.gaze.t1, 0.06);
      this.gaze.visible = env > 0;
      this.gazeU.uOpacity.value = env;
      this.gazeU.uTime.value = time;
    }
    // 风声鹤唳
    if (this.cranes) {
      const c = this.craneData;
      const env = envelope(T, c.t0, c.t1, 0.04);
      this.cranes.visible = env > 0;
      if (env > 0) {
        this.craneU.uTime.value = time;
        const f = (T - c.t0) / (c.t1 - c.t0);
        const m = new THREE.Matrix4();
        const q = new THREE.Quaternion();
        const up = new THREE.Vector3(0, 1, 0);
        const scl = 0.32 * this.scale * Math.min(1, env * 2);
        const sv = new THREE.Vector3(scl, scl, scl);
        for (let fi = 0; fi < this.flockPts.length; fi++) {
          const [[ax, az], [bx, bz]] = this.flockPts[fi];
          const dx = bx - ax;
          const dz = bz - az;
          const L = Math.hypot(dx, dz);
          const fx = dx / L;
          const fz = dz / L;
          const yaw = Math.atan2(fx, fz);
          q.setFromAxisAngle(up, yaw);
          const ff = Math.min(1, Math.max(0, f * 1.15 - fi * 0.08));
          for (let k = 0; k < c.n; k++) {
            const i = fi * c.n + k;
            const [ox, oz, oy, ph] = this.craneOff[i];
            const cx = ax + dx * ff + (-fz * ox + fx * oz) * scl * 2.2;
            const cz = az + dz * ff + (fx * ox + fz * oz) * scl * 2.2;
            const gy = Math.max(this.proj.groundY(cx, cz), 0);
            const y = gy + c.height * this.scale + oy + Math.sin(time * 1.3 + ph) * 0.08;
            m.compose(new THREE.Vector3(cx, y, cz), q, sv);
            this.cranes.setMatrixAt(i, m);
          }
        }
        this.cranes.instanceMatrix.needsUpdate = true;
      }
    }
    if (this.wind) {
      const w = this.fx.wind;
      const env = envelope(T, w.t0, w.t1, 0.05);
      this.wind.visible = env > 0;
      if (env > 0) {
        this.wind.material.opacity = 0.22 * env;
        const m = new THREE.Matrix4();
        const q = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), 0.5);
        const R = w.radius;
        this.windSeeds.forEach(([a, b, c, d], i) => {
          const speed = 1.6 + d * 1.4;
          const t = (time * speed * 0.25 + a) % 1;
          const x = this.windC[0] + (t - 0.5) * R * 2 * -0.88 + (b - 0.5) * R * 0.6;
          const z = this.windC[1] + (t - 0.5) * R * 2 * -0.48 + (c - 0.5) * R;
          const y = Math.max(this.proj.groundY(x, z), 0) + 0.25 + d * 0.9;
          const s = Math.sin(t * Math.PI);
          m.compose(new THREE.Vector3(x, y, z), q, new THREE.Vector3(0.5 + s, 1, 1));
          this.wind.setMatrixAt(i, m);
        });
        this.wind.instanceMatrix.needsUpdate = true;
      }
    }
    // 肥水为之不流
    const rt = this.fx.riverTint;
    if (rt && this.terrain) {
      let amt = 0;
      const ks = rt.keys;
      if (T >= ks[0][0] && T <= ks[ks.length - 1][0]) {
        for (let i = 0; i < ks.length - 1; i++) {
          if (T >= ks[i][0] && T <= ks[i + 1][0]) {
            const f = (T - ks[i][0]) / (ks[i + 1][0] - ks[i][0]);
            amt = ks[i][1] + (ks[i + 1][1] - ks[i][1]) * f;
          }
        }
      }
      const [u, v] = this.proj.geoToUV(rt.at[0], rt.at[1]);
      this.terrain.uniforms.uRiverTint.value.set(u, v, rt.radius, amt);
    }
  }
}
