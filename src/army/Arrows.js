import * as THREE from 'three';
import { CSS2DObject } from 'three/examples/jsm/renderers/CSS2DRenderer.js';
import { Path } from './Path.js';

export const ARROW_COLORS = {
  jin: '#d8472f',
  qin: '#3d63c4',
  gold: '#e3b55b',
  ink: '#2b211b',
};
const STYLE = { advance: 0, retreat: 1, rout: 1, envoy: 2, courier: 2, plan: 3, naval: 4 };

const vert = /* glsl */ `
attribute float aS;
attribute float aV;
attribute float aHead;
varying float vS;
varying float vV;
varying float vHead;
void main() {
  vS = aS; vV = aV; vHead = aHead;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}`;

const frag = /* glsl */ `
uniform vec3 uColor;
uniform float uTime;
uniform float uStyle;
uniform float uOpacity;
uniform float uWidth;
varying float vS;
varying float vV;
varying float vHead;
void main() {
  float av = abs(vV);
  vec3 col = uColor;
  float a = 1.0 - smoothstep(0.86, 1.0, av);
  // dark rim and soft inner highlight, like a painted war-map arrow
  col = mix(col * 0.5, col, smoothstep(1.0, 0.72, av));
  col = mix(col, col * 1.3 + 0.04, (1.0 - smoothstep(0.0, 0.55, av)) * 0.35 * (1.0 - vHead));
  if (uStyle < 0.5 || uStyle > 3.5) {
    float period = uWidth * (uStyle > 3.5 ? 1.6 : 2.4);
    float ph = fract((vS - av * uWidth * 0.6 - uTime * uWidth * 1.4) / period);
    float chev = smoothstep(0.0, 0.07, ph) * (1.0 - smoothstep(0.26, 0.36, ph));
    col = mix(col, col * 1.5 + 0.1, chev * 0.5 * (1.0 - vHead));
    if (uStyle > 3.5) {
      // naval: twin stripes
      float st = smoothstep(0.18, 0.24, av) * (1.0 - smoothstep(0.34, 0.4, av));
      col = mix(col, vec3(0.95, 0.92, 0.82), st * 0.5 * (1.0 - vHead));
    }
  } else if (uStyle < 1.5) {
    float d = fract(vS / (uWidth * 1.7));
    if (d > 0.6 && vHead < 0.5) discard;
  } else if (uStyle < 2.5) {
    float d = fract(vS / (uWidth * 1.15) - uTime * 0.6);
    float dotd = length(vec2((d - 0.5) * 2.2, vV * 1.0));
    if (vHead < 0.5) {
      if (dotd > 0.75) discard;
      a *= 1.0 - smoothstep(0.55, 0.75, dotd);
    }
  } else {
    float d = fract(vS / (uWidth * 1.4));
    if (vHead < 0.5 && (av < 0.55 || d > 0.62)) discard;
  }
  a *= smoothstep(0.0, uWidth * 2.2, vS);
  gl_FragColor = vec4(col, a * uOpacity);
}`;

export class ArrowsLayer {
  /**
   * @param resolver
   * @param defs arrow definitions
   * @param units UnitsLayer (for arrows bound to a unit's movement)
   * @param opts { width, offset, step }
   */
  constructor(resolver, defs, units, opts) {
    this.R = resolver;
    this.proj = resolver.proj;
    this.units = units;
    this.opts = Object.assign({ width: 0.34, offset: 0.03, step: 0.08 }, opts);
    this.group = new THREE.Group();
    this.group.name = 'arrows';
    this.enabled = true;
    this.arrows = defs.map((d) => this.prepare(d)).filter(Boolean);
  }

  prepare(def) {
    let path;
    let t0 = def.t0;
    let t1 = def.t1;
    if (def.unit) {
      const u = this.units.byId[def.unit];
      if (!u) throw new Error(`arrow ${def.id}: unknown unit ${def.unit}`);
      const key = u.keys[def.key];
      if (!key?.path) throw new Error(`arrow ${def.id}: unit ${def.unit} key ${def.key} has no path`);
      path = key.path;
      if (t0 === undefined) t0 = u.keys[def.key - 1].t;
      if (t1 === undefined) t1 = key.t;
      if (def.trimEnd) path = path.slice(0, path.length - this.proj.kmToWorldLen(def.trimEnd));
      if (def.trimStart) path = path.slice(this.proj.kmToWorldLen(def.trimStart), path.length);
    } else {
      path = new Path(this.R.path(def.path, { smooth: def.smooth !== false }));
    }
    if (def.lateral) {
      // shift sideways (km) so parallel marches along one road stay readable
      const d = this.proj.kmToWorldLen(def.lateral);
      const p = { x: 0, z: 0, tx: 0, tz: 1 };
      const pts = path.pts.map((_, i) => {
        path.at(path.cum[i], p);
        return [p.x - p.tz * d, p.z + p.tx * d];
      });
      path = new Path(Path.smooth(pts, 1));
    }
    const width = this.opts.width * (def.width ?? 1);
    const color = new THREE.Color(ARROW_COLORS[def.color || def.side] || ARROW_COLORS.ink);
    const uniforms = {
      uColor: { value: color },
      uTime: { value: 0 },
      uStyle: { value: STYLE[def.style || 'advance'] ?? 0 },
      uOpacity: { value: 0 },
      uWidth: { value: width },
    };
    const mat = new THREE.ShaderMaterial({
      uniforms,
      vertexShader: vert,
      fragmentShader: frag,
      transparent: true,
      depthWrite: false,
      side: THREE.DoubleSide,
      polygonOffset: true,
      polygonOffsetFactor: -2,
      polygonOffsetUnits: -4,
    });
    const mesh = new THREE.Mesh(new THREE.BufferGeometry(), mat);
    mesh.renderOrder = 5;
    mesh.frustumCulled = false;
    mesh.visible = false;
    this.group.add(mesh);
    let label = null;
    if (def.label) {
      const el = document.createElement('div');
      el.className = `arrow-label side-${def.color || def.side}`;
      el.textContent = def.label;
      label = new CSS2DObject(el);
      label.center.set(0.5, 0.5);
      const s = path.length * (def.labelAt ?? 0.55);
      const p = path.at(s, {});
      label.position.set(p.x, Math.max(this.proj.groundY(p.x, p.z), 0) + this.opts.offset * 4, p.z);
      label.visible = false;
      this.group.add(label);
    }
    return { def, path, width, uniforms, mesh, label, t0, t1, hide: def.hide ?? Math.floor(t1) + 1, built: -1 };
  }

  build(a, progress) {
    const L = a.path.length * progress;
    const w = a.width;
    const headLen = Math.min(w * 2.4, Math.max(L * 0.5, w * 0.6));
    const headW = w * 2.1;
    const step = Math.max(this.opts.step, w * 0.35);
    const bodyEnd = Math.max(0, L - headLen);
    const pos = [];
    const aS = [];
    const aV = [];
    const aH = [];
    const idx = [];
    const off = this.opts.offset;
    const gy = (x, z) => Math.max(this.proj.groundY(x, z), 0) + off;
    const p = { x: 0, z: 0, tx: 0, tz: 1 };
    const pushRow = (s, half, head) => {
      a.path.at(s, p);
      const nx = -p.tz;
      const nz = p.tx;
      const lx = p.x + nx * half;
      const lz = p.z + nz * half;
      const rx = p.x - nx * half;
      const rz = p.z - nz * half;
      pos.push(lx, gy(lx, lz), lz, rx, gy(rx, rz), rz);
      aS.push(s, s);
      aV.push(-1, 1);
      aH.push(head, head);
    };
    let rows = 0;
    const n = Math.max(1, Math.ceil(bodyEnd / step));
    for (let i = 0; i <= n; i++) {
      const s = (bodyEnd * i) / n;
      const taper = 0.45 + 0.55 * Math.min(1, s / (w * 3));
      pushRow(s, (w / 2) * taper, 0);
      if (i > 0) {
        const b = (rows - 1) * 2;
        idx.push(b, b + 1, b + 2, b + 2, b + 1, b + 3);
      }
      rows++;
    }
    // arrow head: flared base then a draped triangle to the tip
    const hs = 5;
    const baseRow = rows;
    for (let i = 0; i <= hs; i++) {
      const s = bodyEnd + (headLen * i) / hs;
      const half = (headW / 2) * (1 - i / hs) + 0.0001;
      pushRow(s, half, 1);
      if (i > 0) {
        const b = (baseRow + i - 1) * 2;
        idx.push(b, b + 1, b + 2, b + 2, b + 1, b + 3);
      }
      rows++;
    }
    const g = a.mesh.geometry;
    g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    g.setAttribute('aS', new THREE.Float32BufferAttribute(aS, 1));
    g.setAttribute('aV', new THREE.Float32BufferAttribute(aV, 1));
    g.setAttribute('aHead', new THREE.Float32BufferAttribute(aH, 1));
    g.setIndex(idx);
    g.computeBoundingSphere();
    a.built = progress;
  }

  setVisible(v) {
    this.group.visible = v;
    if (!v) for (const a of this.arrows) if (a.label) a.label.visible = false;
  }

  setEnabled(v) {
    this.enabled = v;
  }

  collect(items) {
    for (const a of this.arrows) {
      if (a.label && a.label.visible) items.push({ el: a.label.element, obj: a.label, want: true, prio: 10 });
    }
  }

  refreshHeights() {
    for (const a of this.arrows) {
      a.built = -1;
      if (a.label) {
        const p = a.label.position;
        p.y = Math.max(this.proj.groundY(p.x, p.z), 0) + this.opts.offset * 4;
      }
    }
  }

  update(T, time, camDist = 100) {
    // arrows are a map device: thin them out when the camera is down among the figures
    const near = this.opts.nearFade ? Math.min(1, Math.max(0, (camDist - this.opts.nearFade[0]) / (this.opts.nearFade[1] - this.opts.nearFade[0]))) : 1;
    const closeFactor = 0.32 + 0.68 * near * near * (3 - 2 * near);
    for (const a of this.arrows) {
      let progress = 0;
      let opacity = 0;
      if (this.enabled && T >= a.t0) {
        const f = Math.min(1, (T - a.t0) / Math.max(1e-6, a.t1 - a.t0));
        progress = f < 1 ? 1 - Math.pow(1 - f, 2) : 1;
        opacity = Math.min(1, (T - a.t0) / 0.02);
        if (T > a.hide) opacity *= Math.max(0, 1 - (T - a.hide) / 0.12);
      }
      const visible = opacity > 0.001 && progress > 0.002;
      a.mesh.visible = visible;
      if (a.label) a.label.visible = visible && this.group.visible && progress > (a.def.labelAt ?? 0.55);
      if (!visible) continue;
      if (Math.abs(progress - a.built) > 0.002) this.build(a, progress);
      a.uniforms.uOpacity.value = opacity * (a.def.opacity ?? 0.92) * closeFactor;
      a.uniforms.uTime.value = time;
    }
  }
}
