// Low-poly figures of Briar (熊大), Bramble (熊二) and Logger Vick (光头强) that stroll their usual
// routes. These are simple fan-made stand-ins built from primitives, not the official character models.
import * as THREE from 'three';
import { CSS2DObject } from 'three/examples/jsm/renderers/CSS2DRenderer.js';
import { Line2 } from './util.js';

const mat = (c, o = {}) => new THREE.MeshStandardMaterial({ color: c, roughness: 0.75, ...o });
function part(geo, m, x = 0, y = 0, z = 0, sx = 1, sy = 1, sz = 1) {
  const o = new THREE.Mesh(geo, m);
  o.position.set(x, y, z);
  o.scale.set(sx, sy, sz);
  o.castShadow = true;
  return o;
}
const SPH = new THREE.SphereGeometry(1, 16, 12);
const CAP = new THREE.CapsuleGeometry(0.22, 0.5, 4, 8);
const CYL = new THREE.CylinderGeometry(1, 1, 1, 12);

function limb(m, len, r) {
  const piv = new THREE.Group();
  const l = part(new THREE.CapsuleGeometry(r, len, 4, 8), m, 0, -len / 2 - r * 0.5, 0);
  piv.add(l);
  return piv;
}

function bear({ fur, muzzle, belly, big = 1, scarf }) {
  const g = new THREE.Group();
  const F = mat(fur), Mz = mat(muzzle), B = mat(belly), K = mat('#1d1712'), W = mat('#ffffff');
  const body = new THREE.Group();
  g.add(body);
  body.add(part(SPH, F, 0, 1.35, 0, 0.92 * big, 1.05, 0.82 * big));
  body.add(part(SPH, B, 0, 1.25, 0.42 * big, 0.62 * big, 0.75, 0.42));
  const head = new THREE.Group();
  head.position.y = 2.55;
  body.add(head);
  head.add(part(SPH, F, 0, 0, 0, 0.78, 0.72, 0.72));
  head.add(part(SPH, Mz, 0, -0.18, 0.55, 0.38, 0.28, 0.28));
  head.add(part(SPH, K, 0, -0.06, 0.82, 0.12, 0.09, 0.08));
  for (const s of [-1, 1]) {
    head.add(part(SPH, W, s * 0.26, 0.16, 0.6, 0.13, 0.15, 0.08));
    head.add(part(SPH, K, s * 0.26, 0.15, 0.67, 0.07, 0.09, 0.05));
    head.add(part(SPH, F, s * 0.55, 0.55, -0.05, 0.22, 0.22, 0.12));
    head.add(part(SPH, Mz, s * 0.55, 0.55, 0.04, 0.12, 0.12, 0.06));
  }
  const arms = [], legs = [];
  for (const s of [-1, 1]) {
    const a = limb(F, 0.7, 0.24);
    a.position.set(s * 0.85 * big, 1.9, 0.05);
    a.rotation.z = s * 0.35;
    body.add(a);
    arms.push(a);
    const l = limb(F, 0.35, 0.28);
    l.position.set(s * 0.42 * big, 0.75, 0);
    g.add(l);
    legs.push(l);
    l.add(part(SPH, Mz, 0, -0.78, 0.12, 0.26, 0.12, 0.32));
  }
  const sc = new THREE.Mesh(new THREE.TorusGeometry(0.55 * big, 0.16, 8, 18), mat(scarf));
  sc.rotation.x = Math.PI / 2;
  sc.position.y = 2.12;
  const tail = part(new THREE.BoxGeometry(0.3, 0.7, 0.08), mat(scarf), 0.35, 1.85, 0.62);
  tail.rotation.z = 0.2;
  const scarfG = new THREE.Group();
  scarfG.add(sc, tail);
  body.add(scarfG);
  return { g, body, head, arms, legs, scarf: scarfG };
}

function logger() {
  const g = new THREE.Group();
  const skin = mat('#f1c49b'), jacket = mat('#d9672b'), pants = mat('#3c4a63'), boot = mat('#3a2a1e'), K = mat('#1a1a1a'), W = mat('#ffffff');
  const body = new THREE.Group();
  g.add(body);
  body.add(part(CYL, jacket, 0, 1.55, 0, 0.5, 1.0, 0.38));
  body.add(part(SPH, jacket, 0, 2.05, 0, 0.52, 0.25, 0.4));
  body.add(part(CYL, mat('#5a3a22'), 0, 1.1, 0, 0.52, 0.12, 0.4));
  const head = new THREE.Group();
  head.position.y = 2.75;
  body.add(head);
  head.add(part(SPH, skin, 0, 0, 0, 0.5, 0.58, 0.5));
  head.add(part(SPH, skin, 0, -0.08, 0.45, 0.12, 0.1, 0.12)); // nose
  for (const s of [-1, 1]) {
    head.add(part(SPH, W, s * 0.18, 0.08, 0.42, 0.1, 0.11, 0.06));
    head.add(part(SPH, K, s * 0.18, 0.08, 0.47, 0.05, 0.06, 0.03));
    const brow = part(new THREE.BoxGeometry(0.3, 0.08, 0.06), K, s * 0.19, 0.24, 0.45);
    brow.rotation.z = -s * 0.25;
    head.add(brow);
    head.add(part(SPH, skin, s * 0.5, 0, 0, 0.08, 0.14, 0.1)); // ears
  }
  head.add(part(new THREE.BoxGeometry(0.22, 0.04, 0.05), mat('#8a3b2b'), 0, -0.28, 0.44)); // mouth
  const arms = [], legs = [];
  for (const s of [-1, 1]) {
    const a = limb(jacket, 0.75, 0.15);
    a.position.set(s * 0.6, 2.1, 0);
    a.rotation.z = s * 0.15;
    a.children[0].add(part(SPH, skin, 0, -0.55, 0, 0.14, 0.14, 0.14));
    body.add(a);
    arms.push(a);
    const l = limb(pants, 0.7, 0.17);
    l.position.set(s * 0.22, 1.05, 0);
    l.children[0].add(part(new THREE.BoxGeometry(0.3, 0.2, 0.45), boot, 0, -0.5, 0.08));
    g.add(l);
    legs.push(l);
  }
  // chainsaw in the right hand
  const saw = new THREE.Group();
  saw.add(part(new THREE.BoxGeometry(0.3, 0.32, 0.55), mat('#f0a321'), 0, 0, 0));
  saw.add(part(new THREE.BoxGeometry(0.06, 0.16, 0.95), mat('#9aa3ab', { metalness: 0.6, roughness: 0.4 }), 0, -0.02, 0.7));
  saw.position.set(0, -1.0, 0.3);
  arms[1].children[0].add(saw);
  arms[1].rotation.x = -0.5;
  const sc = new THREE.Mesh(new THREE.TorusGeometry(0.42, 0.13, 8, 18), mat('#2f6fb8'));
  sc.rotation.x = Math.PI / 2;
  sc.position.y = 2.25;
  const scarfG = new THREE.Group();
  scarfG.add(sc);
  body.add(scarfG);
  const hat = part(new THREE.SphereGeometry(0.52, 12, 8, 0, Math.PI * 2, 0, Math.PI / 2), mat('#2f6fb8'), 0, 0.12, 0);
  head.add(hat);
  scarfG.userData.hat = hat;
  return { g, body, head, arms, legs, scarf: scarfG };
}

export const CHARACTERS = [
  {
    id: 'briar', name: '熊大', desc: '哥哥，机智勇敢，是森林的守护者。常在熊窝、木桥和猴王树之间巡山。',
    make: () => bear({ fur: '#7b4a2b', muzzle: '#e0bd8f', belly: '#c69a6a', big: 1, scarf: '#d83a33' }),
    route: [[28, -4], [20, -3], [8, 1], [-4, 2], [-12, 2], [-24, -5], [-40, -14], [-50, -18]], speed: 2.4, scale: 1.25,
  },
  {
    id: 'bramble', name: '熊二', desc: '弟弟，憨厚贪吃，最爱蜂蜜。总在熊窝和蜂蜜树之间来回。',
    make: () => bear({ fur: '#a8723d', muzzle: '#f0d6a8', belly: '#e1bd86', big: 1.18, scarf: '#f2c230' }),
    route: [[27, -2], [31, -8], [34, -12], [38, -18], [41, -22]], speed: 1.5, scale: 1.3,
  },
  {
    id: 'vick', name: '光头强', desc: '伐木工，住在森林东南的木屋里，总想着砍树完成老板的任务。',
    make: logger,
    route: [[52, 43.5], [49.5, 45.5], [47.5, 39], [52, 47], [60, 45], [65, 38], [70, 33]], speed: 2.0, scale: 1.2,
  },
];

export function buildCharacters(hf) {
  const group = new THREE.Group();
  const list = CHARACTERS.map((c, i) => {
    const rig = c.make();
    rig.g.scale.setScalar(c.scale);
    const holder = new THREE.Group();
    holder.add(rig.g);
    group.add(holder);
    const div = document.createElement('div');
    div.className = 'char-tag';
    div.textContent = c.name;
    const tag = new CSS2DObject(div);
    tag.position.set(0, 4.4 * c.scale, 0);
    holder.add(tag);
    const line = new Line2(c.route, 80);
    return { ...c, rig, holder, tag, div, line, s: (i * 0.37) % 1, dir: 1, pause: 0, phase: 0 };
  });

  const yAt = (x, z) => {
    let y = hf.h(x, z);
    const r = hf.river.closest(x, z);
    if (r.d < hf.riverWidth(r.t) + 3) y = Math.max(y, hf.bedAt(r.t) + 2.0);
    return y;
  };

  const update = (dt, t, season) => {
    for (const c of list) {
      if (c.pause > 0) c.pause -= dt;
      else {
        c.s += (c.dir * c.speed * dt) / c.line.total;
        if (c.s >= 1 || c.s <= 0) {
          c.s = Math.min(1, Math.max(0, c.s));
          c.dir *= -1;
          c.pause = 2.5 + Math.random() * 3;
        }
      }
      const p = c.line.at(c.s);
      const walking = c.pause <= 0;
      c.holder.position.set(p.x, yAt(p.x, p.z), p.z);
      const target = Math.atan2(p.dx * c.dir, p.dz * c.dir);
      let d = target - c.holder.rotation.y;
      d = Math.atan2(Math.sin(d), Math.cos(d));
      c.holder.rotation.y += d * Math.min(1, dt * 6);
      c.phase += dt * (walking ? c.speed * 3.2 : 0);
      const sw = walking ? Math.sin(c.phase) : 0;
      c.rig.legs[0].rotation.x = sw * 0.6;
      c.rig.legs[1].rotation.x = -sw * 0.6;
      c.rig.arms[0].rotation.x = -sw * 0.5;
      if (c.id !== 'vick') c.rig.arms[1].rotation.x = sw * 0.5;
      c.rig.body.position.y = walking ? Math.abs(Math.cos(c.phase)) * 0.12 : Math.sin(t * 2) * 0.03;
      c.rig.head.rotation.y = walking ? 0 : Math.sin(t * 0.8 + c.s * 9) * 0.5;
      const w = season.weights[3] + season.weights[2] * 0.15;
      c.rig.scarf.visible = w > 0.05;
      c.rig.scarf.scale.setScalar(Math.max(0.01, Math.min(1, w)));
      if (c.rig.scarf.userData.hat) c.rig.scarf.userData.hat.visible = season.weights[3] > 0.3;
    }
  };
  return { group, list, update };
}
