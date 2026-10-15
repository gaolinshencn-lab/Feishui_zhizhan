// Landmarks and seasonal props, all modelled from primitives.
import * as THREE from 'three';
import { merge, at } from './flora.js';
import { snowify, stdMat, U } from './shared.js';
import { rng } from './util.js';
import { LAKE, CLEARINGS } from './places.js';

const M = (c, o) => snowify(stdMat(c, o), { key: 'b' });
const MAT = {
  log: M('#8a5a36'), logDark: M('#6a4228'), roof: M('#a3402e'), roofDark: M('#7a2f22'), stone: M('#9a948a'),
  door: M('#5c3a22'), wood: M('#b07a48'), plank: M('#c59160'), white: M('#f2f2ee'), metal: M('#7d8790', { metalness: 0.4, roughness: 0.5 }),
  truck: M('#e2a52a'), truckDark: M('#2f3338'), tire: M('#26282b'), glass: stdMat('#bcd9e8', { roughness: 0.2 }),
  hive: M('#e9a93a'), hiveDark: M('#c9832a'), cut: M('#e6c58e'), hay: M('#e3c063'), pumpkin: M('#ef8a24'),
  green: M('#4f8a35'), red: M('#d8352b'), snow: stdMat('#f7fbff'), coal: stdMat('#222222'), carrot: stdMat('#f07a22'),
  ice: stdMat('#d9f1ff', { transparent: true, opacity: 0.85, roughness: 0.1 }), cloth: M('#3f78c8'), cloth2: M('#e85a5a'),
  lily: M('#4f9c3c'), lotus: stdMat('#ff9ec4'),
};
const win = () => new THREE.MeshStandardMaterial({ color: '#ffe2a0', emissive: '#ffb84a', emissiveIntensity: 0.15, roughness: 0.4 });

function mesh(geo, mat, shadow = true) {
  const m = new THREE.Mesh(geo, mat);
  m.castShadow = shadow;
  m.receiveShadow = true;
  return m;
}
const box = (w, h, d, mat, x = 0, y = 0, z = 0) => {
  const m = mesh(new THREE.BoxGeometry(w, h, d), mat);
  m.position.set(x, y, z);
  return m;
};
const cyl = (rt, rb, h, mat, seg = 8) => mesh(new THREE.CylinderGeometry(rt, rb, h, seg), mat);
const ball = (r, mat, d = 1) => mesh(new THREE.IcosahedronGeometry(r, d), mat);

// ------------------------------------------------------------------------------------------

function cabin(windows) {
  const g = new THREE.Group();
  const W = 8, D = 6, H = 3.4;
  // log walls: stacked horizontal logs
  const logs = [];
  for (let i = 0; i < 8; i++) {
    const y = 0.22 + i * 0.42;
    logs.push(at(new THREE.CylinderGeometry(0.24, 0.24, W + 0.6, 7), 0, y, D / 2, 0, 0, Math.PI / 2));
    logs.push(at(new THREE.CylinderGeometry(0.24, 0.24, W + 0.6, 7), 0, y, -D / 2, 0, 0, Math.PI / 2));
    logs.push(at(new THREE.CylinderGeometry(0.24, 0.24, D + 0.6, 7), W / 2, y + 0.21, 0, Math.PI / 2));
    logs.push(at(new THREE.CylinderGeometry(0.24, 0.24, D + 0.6, 7), -W / 2, y + 0.21, 0, Math.PI / 2));
  }
  g.add(mesh(merge(logs), MAT.log));
  g.add(box(W - 0.2, H, D - 0.2, MAT.logDark, 0, H / 2, 0));
  // gables and roof
  const gable = new THREE.Shape([new THREE.Vector2(-D / 2, 0), new THREE.Vector2(D / 2, 0), new THREE.Vector2(0, 2.2)]);
  for (const sx of [-1, 1]) {
    const gm = mesh(new THREE.ExtrudeGeometry(gable, { depth: 0.3, bevelEnabled: false }), MAT.log);
    gm.rotation.y = Math.PI / 2;
    gm.position.set(sx * (W / 2) - 0.15, H, 0);
    g.add(gm);
  }
  const slope = Math.atan2(2.2, D / 2);
  const len = Math.hypot(2.2, D / 2) + 0.7;
  for (const s of [-1, 1]) {
    const r = box(W + 1.4, 0.28, len, s > 0 ? MAT.roof : MAT.roofDark);
    r.rotation.x = s * slope;
    r.position.set(0, H + 1.1 + 0.18, s * (D / 4 + 0.15));
    g.add(r);
  }
  // chimney
  const ch = box(0.9, 3, 0.9, MAT.stone, 2.4, H + 1.6, -1.2);
  g.add(ch);
  g.userData.chimney = new THREE.Vector3(2.4, H + 3.2, -1.2);
  // door & windows on the front (+z)
  g.add(box(1.2, 2.1, 0.12, MAT.door, -1.6, 1.05, D / 2 + 0.25));
  for (const x of [0.8, 2.8]) {
    const wm = win();
    windows.push(wm);
    g.add(box(1.0, 0.9, 0.1, wm, x, 1.9, D / 2 + 0.26));
    g.add(box(1.2, 0.12, 0.2, MAT.plank, x, 1.4, D / 2 + 0.3));
  }
  const sw = win();
  windows.push(sw);
  g.add(box(0.1, 0.9, 1.0, sw, W / 2 + 0.28, 1.9, 0));
  // porch
  g.add(box(W + 0.4, 0.25, 1.8, MAT.plank, 0, 0.12, D / 2 + 1.1));
  for (const x of [-W / 2, W / 2]) g.add(box(0.2, 2.6, 0.2, MAT.log, x, 1.4, D / 2 + 1.9));
  const awning = box(W + 0.8, 0.15, 2.2, MAT.roofDark, 0, 2.75, D / 2 + 1.1);
  awning.rotation.x = 0.18;
  g.add(awning);
  // icicles under the eaves (winter)
  const ic = [];
  for (let i = 0; i < 26; i++) {
    const x = -W / 2 - 0.4 + (i / 25) * (W + 0.8);
    const l = 0.3 + ((i * 7) % 5) * 0.12;
    ic.push(at(new THREE.ConeGeometry(0.07, l, 4), x, 2.55 - l / 2, D / 2 + 2.15, Math.PI));
  }
  const icicles = mesh(merge(ic), MAT.ice, false);
  g.add(icicles);
  g.userData.icicles = icicles;
  return g;
}

function truck() {
  const g = new THREE.Group();
  g.add(box(2.4, 1.0, 5.6, MAT.truckDark, 0, 1.0, 0));
  g.add(box(2.4, 1.6, 1.9, MAT.truck, 0, 2.2, 1.7));
  g.add(box(2.42, 0.7, 0.05, MAT.glass, 0, 2.5, 2.66));
  g.add(box(2.4, 0.9, 1.0, MAT.truck, 0, 1.6, 2.9));
  g.add(box(0.15, 1.6, 3.6, MAT.truck, 1.15, 2.1, -1.0));
  g.add(box(0.15, 1.6, 3.6, MAT.truck, -1.15, 2.1, -1.0));
  for (const [x, z] of [[1.25, 2.1], [-1.25, 2.1], [1.25, -1.8], [-1.25, -1.8]]) {
    const w = cyl(0.55, 0.55, 0.4, MAT.tire, 12);
    w.rotation.z = Math.PI / 2;
    w.position.set(x, 0.55, z);
    g.add(w);
  }
  // logs on the bed
  for (let i = 0; i < 5; i++) {
    const l = cyl(0.36, 0.36, 3.6, MAT.wood, 8);
    l.rotation.x = Math.PI / 2;
    l.position.set(-0.75 + (i % 3) * 0.75 + (i > 2 ? 0.37 : 0), 1.85 + (i > 2 ? 0.62 : 0), -1);
    g.add(l);
  }
  return g;
}

function logPile(n = 3) {
  const parts = [], ends = [];
  let k = 0;
  for (let row = 0; row < n; row++)
    for (let i = 0; i < n - row; i++) {
      const x = (i - (n - row - 1) / 2) * 0.8, y = 0.38 + row * 0.66;
      parts.push(at(new THREE.CylinderGeometry(0.38, 0.38, 4, 8), x, y, 0, Math.PI / 2));
      ends.push(at(new THREE.CircleGeometry(0.36, 8), x, y, 2.01), at(new THREE.CircleGeometry(0.36, 8), x, y, -2.01, 0, Math.PI));
      k++;
    }
  const g = new THREE.Group();
  g.add(mesh(merge(parts), MAT.log));
  g.add(mesh(merge(ends), MAT.cut, false));
  return g;
}

function stump(r = 0.5) {
  const g = new THREE.Group();
  const body = cyl(r, r * 1.25, 0.7, MAT.log, 8);
  body.position.y = 0.35;
  g.add(body);
  const top = mesh(new THREE.CircleGeometry(r * 0.98, 8), MAT.cut, false);
  top.rotation.x = -Math.PI / 2;
  top.position.y = 0.71;
  g.add(top);
  return g;
}

// Briar and Bramble live inside a huge old hollow tree (树洞). Door at the foot of the trunk, +z side.
function bearHome(windows) {
  const g = bigTree(1.5, '#5aa83e');
  const inner = new THREE.Group();
  inner.scale.setScalar(1 / 1.5); // build in world units inside the scaled tree
  g.add(inner);
  // fat, slightly gnarled trunk and buttress roots
  const trunk = mesh(new THREE.CylinderGeometry(2.1, 2.9, 8.5, 10, 3), MAT.log);
  trunk.position.y = 4.25;
  inner.add(trunk);
  const roots = [];
  for (let i = 0; i < 7; i++) {
    const a = (i / 7) * Math.PI * 2 + 0.3;
    if (Math.abs(Math.atan2(Math.sin(a - Math.PI / 2), Math.cos(a - Math.PI / 2))) < 0.5) continue; // keep the doorway clear
    roots.push(at(new THREE.ConeGeometry(0.9, 3.4, 6), Math.cos(a) * 2.9, 0.6, Math.sin(a) * 2.9, Math.sin(a) * 1.15, 0, -Math.cos(a) * 1.15));
  }
  inner.add(mesh(merge(roots), MAT.logDark));
  // dark hollow, arched wooden door with frame
  const hole = mesh(new THREE.CircleGeometry(1.25, 16, 0, Math.PI), MAT.coal, false);
  hole.position.set(0, 1.2, 2.88);
  inner.add(hole);
  inner.add(box(2.5, 1.2, 0.05, MAT.coal, 0, 0.6, 2.88));
  const door = mesh(new THREE.CylinderGeometry(1.1, 1.1, 0.16, 16, 1, false, -Math.PI / 2, Math.PI), MAT.door);
  door.rotation.x = Math.PI / 2;
  door.position.set(0, 1.25, 2.95);
  inner.add(door);
  inner.add(box(2.2, 1.25, 0.16, MAT.door, 0, 0.62, 2.95));
  for (const x of [-0.6, 0, 0.6]) inner.add(box(0.06, 2.2, 0.05, MAT.logDark, x, 1.15, 3.05));
  const frame = mesh(new THREE.TorusGeometry(1.25, 0.16, 5, 16, Math.PI), MAT.wood);
  frame.position.set(0, 1.2, 2.95);
  inner.add(frame);
  inner.add(box(0.3, 1.25, 0.3, MAT.wood, -1.25, 0.6, 2.95), box(0.3, 1.25, 0.3, MAT.wood, 1.25, 0.6, 2.95));
  const knob = ball(0.12, MAT.hive, 0);
  knob.position.set(0.7, 1.0, 3.1);
  inner.add(knob);
  // round window higher up the trunk
  const wm = win();
  windows.push(wm);
  const w = mesh(new THREE.CircleGeometry(0.55, 12), wm, false);
  w.position.set(1.1, 4.6, 2.62);
  w.rotation.y = 0.4;
  inner.add(w);
  const wf = mesh(new THREE.TorusGeometry(0.6, 0.1, 5, 12), MAT.wood);
  wf.position.copy(w.position);
  wf.rotation.y = 0.4;
  inner.add(wf);
  // doorstep, mailbox, firewood, honey pots
  inner.add(box(2.8, 0.2, 1.4, MAT.stone, 0, 0.1, 3.7));
  inner.add(box(0.15, 1.3, 0.15, MAT.wood, -3.4, 0.65, 4.0));
  inner.add(box(0.7, 0.5, 0.45, MAT.red, -3.4, 1.45, 4.0));
  const fw = logPile(3);
  fw.scale.setScalar(0.45);
  fw.rotation.y = 0.3;
  fw.position.set(-3.8, 0, 1.8);
  inner.add(fw);
  for (let i = 0; i < 3; i++) {
    const pot = ball(0.35, MAT.hiveDark, 1);
    pot.scale.y = 1.1;
    pot.position.set(2.4 + i * 0.7, 0.35, 3.6 + (i % 2) * 0.4);
    inner.add(pot);
    const lid = cyl(0.2, 0.25, 0.12, MAT.cloth2);
    lid.position.set(pot.position.x, 0.78, pot.position.z);
    inner.add(lid);
  }
  return g;
}

// A big tree whose crown follows the season (used for the honey tree and the monkey king's tree).
function bigTree(scale, leafColor) {
  const g = new THREE.Group();
  const trunk = cyl(0.55, 0.95, 6.5, MAT.log, 8);
  trunk.position.y = 3.25;
  g.add(trunk);
  const br = [];
  for (let i = 0; i < 6; i++) {
    const a = (i / 6) * Math.PI * 2;
    br.push(at(new THREE.CylinderGeometry(0.1, 0.25, 3.2, 5), Math.cos(a) * 1.1, 6.4 + (i % 2) * 0.6, Math.sin(a) * 1.1, Math.sin(a) * 0.9, 0, -Math.cos(a) * 0.9));
  }
  g.add(mesh(merge(br), MAT.log));
  const leafU = { value: 1 };
  const center = new THREE.Vector3(0, 7.6, 0);
  const crownMat = snowify(stdMat(leafColor), { key: 'big', leaf: { center, uniform: leafU }, sway: 0.004, snowLo: 0.2 });
  const crown = mesh(
    merge([
      at(new THREE.IcosahedronGeometry(3.2, 1), 0, 8.2, 0),
      at(new THREE.IcosahedronGeometry(2.3, 1), 2.4, 7.2, 0.6),
      at(new THREE.IcosahedronGeometry(2.2, 1), -2.3, 7.4, -0.4),
      at(new THREE.IcosahedronGeometry(2.0, 1), 0.3, 7.0, 2.3),
      at(new THREE.IcosahedronGeometry(2.0, 1), -0.4, 7.3, -2.4),
    ]),
    crownMat
  );
  g.add(crown);
  g.scale.setScalar(scale);
  g.userData.crown = crown;
  g.userData.leafU = leafU;
  return g;
}

function beehive() {
  const g = new THREE.Group();
  for (let i = 0; i < 4; i++) {
    const r = 0.55 - Math.abs(i - 1.3) * 0.12;
    const t = mesh(new THREE.TorusGeometry(r, 0.17, 6, 12), i % 2 ? MAT.hive : MAT.hiveDark);
    t.rotation.x = Math.PI / 2;
    t.position.y = -i * 0.28;
    g.add(t);
  }
  const core = ball(0.5, MAT.hiveDark, 1);
  core.scale.y = 1.25;
  core.position.y = -0.45;
  g.add(core);
  const hole = mesh(new THREE.CircleGeometry(0.13, 8), MAT.coal, false);
  hole.position.set(0, -0.6, 0.62);
  g.add(hole);
  return g;
}

function bridge(len, w) {
  const g = new THREE.Group();
  const planks = [];
  const n = Math.round(len / 0.5);
  for (let i = 0; i < n; i++) {
    const t = i / (n - 1) - 0.5;
    const y = Math.cos(t * Math.PI) * 0.7;
    planks.push(at(new THREE.BoxGeometry(w, 0.15, 0.42), 0, y, t * len, -Math.sin(t * Math.PI) * 0.25 * Math.sign(t) * 0, 0, 0));
  }
  g.add(mesh(merge(planks), MAT.plank));
  const rails = [];
  for (const sx of [-1, 1]) {
    for (let i = 0; i <= 6; i++) {
      const t = i / 6 - 0.5;
      const y = Math.cos(t * Math.PI) * 0.7;
      rails.push(at(new THREE.BoxGeometry(0.14, 1.1, 0.14), sx * (w / 2), y + 0.55, t * len));
    }
    const pts = [];
    for (let i = 0; i <= 12; i++) {
      const t = i / 12 - 0.5;
      pts.push(new THREE.Vector3(sx * (w / 2), Math.cos(t * Math.PI) * 0.7 + 1.1, t * len));
    }
    rails.push(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 16, 0.08, 5));
  }
  g.add(mesh(merge(rails), MAT.wood));
  return g;
}

function boat() {
  const g = new THREE.Group();
  const hull = new THREE.Shape();
  hull.moveTo(-1.6, 0);
  hull.quadraticCurveTo(0, -1.4, 1.6, 0);
  hull.lineTo(-1.6, 0);
  const h = mesh(new THREE.ExtrudeGeometry(hull, { depth: 1.3, bevelEnabled: false }), MAT.wood);
  h.position.set(0, 0.55, -0.65);
  h.scale.set(1, 0.5, 1);
  g.add(h);
  g.add(box(0.3, 0.1, 1.3, MAT.plank, 0, 0.5, 0));
  const oar = box(0.08, 0.08, 2.6, MAT.plank, 0.4, 0.6, 0);
  oar.rotation.y = 1.2;
  g.add(oar);
  return g;
}

function snowman(s = 1) {
  const g = new THREE.Group();
  const b1 = ball(0.9, MAT.snow, 1);
  b1.position.y = 0.8;
  const b2 = ball(0.62, MAT.snow, 1);
  b2.position.y = 2.0;
  const b3 = ball(0.44, MAT.snow, 1);
  b3.position.y = 2.85;
  g.add(b1, b2, b3);
  const nose = mesh(new THREE.ConeGeometry(0.08, 0.5, 6), MAT.carrot);
  nose.rotation.x = Math.PI / 2;
  nose.position.set(0, 2.85, 0.6);
  g.add(nose);
  for (const x of [-0.15, 0.15]) {
    const e = ball(0.06, MAT.coal, 0);
    e.position.set(x, 3.0, 0.4);
    g.add(e);
  }
  const hat = cyl(0.32, 0.32, 0.5, MAT.red);
  hat.position.y = 3.35;
  g.add(hat);
  const scarf = mesh(new THREE.TorusGeometry(0.48, 0.12, 6, 12), MAT.cloth2);
  scarf.rotation.x = Math.PI / 2;
  scarf.position.y = 2.45;
  g.add(scarf);
  for (const sx of [-1, 1]) {
    const arm = cyl(0.04, 0.05, 1.2, MAT.logDark, 4);
    arm.rotation.z = sx * 1.0;
    arm.position.set(sx * 0.95, 2.2, 0);
    g.add(arm);
  }
  g.scale.setScalar(s);
  return g;
}

function haystack() {
  const g = new THREE.Group();
  const h = mesh(new THREE.ConeGeometry(1.4, 2.6, 9), MAT.hay);
  h.position.y = 1.3;
  g.add(h);
  const b = cyl(1.45, 1.5, 0.6, MAT.hay, 9);
  b.position.y = 0.3;
  g.add(b);
  return g;
}

function pumpkin(s = 1) {
  const g = new THREE.Group();
  const p = ball(0.5, MAT.pumpkin, 1);
  p.scale.set(1.2, 0.8, 1.2);
  p.position.y = 0.4;
  g.add(p);
  const st = cyl(0.05, 0.07, 0.25, MAT.green, 5);
  st.position.y = 0.85;
  g.add(st);
  g.scale.setScalar(s);
  return g;
}

function mushroom(s = 1, cap = MAT.red) {
  const g = new THREE.Group();
  const st = cyl(0.12, 0.16, 0.5, MAT.white, 6);
  st.position.y = 0.25;
  const c = mesh(new THREE.SphereGeometry(0.4, 8, 5, 0, Math.PI * 2, 0, Math.PI / 2), cap);
  c.position.y = 0.48;
  g.add(st, c);
  g.scale.setScalar(s);
  return g;
}

function kite() {
  const g = new THREE.Group();
  const shape = new THREE.Shape([new THREE.Vector2(0, 1.1), new THREE.Vector2(0.7, 0), new THREE.Vector2(0, -1.3), new THREE.Vector2(-0.7, 0)]);
  const k = mesh(new THREE.ShapeGeometry(shape), new THREE.MeshStandardMaterial({ color: '#ff5a5a', side: THREE.DoubleSide }), false);
  g.add(k);
  const tail = [];
  for (let i = 0; i < 5; i++) tail.push(at(new THREE.PlaneGeometry(0.3, 0.2), 0, -1.5 - i * 0.45, 0, 0, 0, (i % 2 ? 1 : -1) * 0.5));
  g.add(mesh(merge(tail), new THREE.MeshStandardMaterial({ color: '#ffd84a', side: THREE.DoubleSide }), false));
  return g;
}

function clothesline() {
  const g = new THREE.Group();
  for (const x of [-2.5, 2.5]) g.add(box(0.12, 2.2, 0.12, MAT.wood, x, 1.1, 0));
  const line = cyl(0.02, 0.02, 5, MAT.white, 4);
  line.rotation.z = Math.PI / 2;
  line.position.y = 2.1;
  g.add(line);
  const cols = [MAT.cloth, MAT.cloth2, MAT.white, MAT.cloth];
  cols.forEach((c, i) => g.add(box(0.8, 1.0 - (i % 2) * 0.3, 0.05, c, -1.6 + i * 1.05, 1.55 + (i % 2) * 0.15, 0)));
  return g;
}

function signpost(labels) {
  const g = new THREE.Group();
  g.add(box(0.2, 2.8, 0.2, MAT.wood, 0, 1.4, 0));
  labels.forEach((rot, i) => {
    const b = box(1.8, 0.4, 0.08, MAT.plank, 0.7, 2.4 - i * 0.55, 0);
    const piv = new THREE.Group();
    piv.rotation.y = rot;
    piv.add(b);
    g.add(piv);
  });
  return g;
}

function fence(points, hf) {
  const parts = [];
  for (let i = 0; i < points.length - 1; i++) {
    const [ax, az] = points[i], [bx, bz] = points[i + 1];
    const L = Math.hypot(bx - ax, bz - az);
    const n = Math.max(1, Math.round(L / 1.6));
    const ang = Math.atan2(bx - ax, bz - az);
    for (let k = 0; k <= n; k++) {
      const x = ax + ((bx - ax) * k) / n, z = az + ((bz - az) * k) / n;
      parts.push(at(new THREE.BoxGeometry(0.16, 1.2, 0.16), x, hf.h(x, z) + 0.5, z));
    }
    for (let k = 0; k < n; k++) {
      const x = ax + ((bx - ax) * (k + 0.5)) / n, z = az + ((bz - az) * (k + 0.5)) / n;
      const y = hf.h(x, z);
      for (const yy of [0.5, 0.9]) parts.push(at(new THREE.BoxGeometry(0.08, 0.12, L / n + 0.1), x, y + yy, z, 0, ang));
    }
  }
  return mesh(merge(parts), MAT.wood);
}

// ------------------------------------------------------------------------------------------

export function buildLandmarks(hf) {
  const root = new THREE.Group();
  const windows = [];
  const seasonal = []; // { obj, w: (p) => weight }
  const animated = [];
  const R = rng(99);
  const place = (obj, x, z, ry = 0, dy = 0) => {
    obj.position.set(x, hf.h(x, z) + dy, z);
    obj.rotation.y = ry;
    root.add(obj);
    return obj;
  };
  const season = (obj, w) => seasonal.push({ obj, w, s0: obj.scale.x });

  // Logger Vick's cabin
  const cab = place(cabin(windows), 55, 38, 0.15, -0.1);
  season(cab.userData.icicles, (p) => p.weights[3]);
  const chimney = cab.localToWorld(cab.userData.chimney.clone());
  place(truck(), 62.5, 47, 0.95);
  place(logPile(4), 47, 34, 1.4);
  place(stump(0.55), 50.5, 45);
  const axe = box(0.08, 0.9, 0.08, MAT.wood);
  axe.position.set(50.5, hf.h(50.5, 45) + 1.1, 45);
  axe.rotation.z = 0.4;
  root.add(axe);
  root.add(fence([[46, 48], [46, 32], [52, 30], [62, 30], [64, 34]], hf));
  season(place(clothesline(), 60, 33, 0.3), (p) => p.weights[1] + p.weights[0] * 0.5);
  for (let i = 0; i < 6; i++) season(place(pumpkin(0.8 + R() * 0.6), 48 + R() * 4, 44 + R() * 3, R() * 6), (p) => p.weights[2]);
  season(place(snowman(1.1), 51, 47, -0.4), (p) => p.weights[3]);
  place(signpost([0.2, -0.6, 2.4]), 59.5, 50.5);

  // Log yard
  for (let i = 0; i < 16; i++) {
    const a = R() * Math.PI * 2, r = 2 + R() * 7.5;
    place(stump(0.35 + R() * 0.35), 70 + Math.cos(a) * r, 32 + Math.sin(a) * r, R() * 6);
  }
  place(logPile(5), 74, 28, 0.6);
  place(logPile(3), 66, 26, 2.2);

  // Bears' home: tucked into the hill, door facing the path to the bridge
  const home = place(bearHome(windows), 30, -7, -0.95, -0.2);
  season(place(snowman(0.9), 25.5, -2.5, 0.8), (p) => p.weights[3]);
  for (let i = 0; i < 9; i++) {
    const a = R() * 6.28, r = 3 + R() * 6;
    season(place(mushroom(0.6 + R() * 0.8, R() < 0.5 ? MAT.red : MAT.hiveDark), 25 + Math.cos(a) * r, -1 + Math.sin(a) * r * 0.6, R() * 6), (p) => p.weights[2] + p.weights[1] * 0.3);
  }

  // Honey tree with hives
  const honey = place(bigTree(0.95, '#5aa83e'), 43, -26, 0.4, -0.2);
  for (const [x, y, z] of [[2.0, 5.6, 0.6], [-1.6, 5.9, 1.2], [0.6, 6.2, -1.8]]) {
    const h = beehive();
    h.position.set(x, y, z);
    honey.add(h);
  }

  // Monkey king's tree with a platform, ladder and throne
  const mk = place(bigTree(1.55, '#4f9c3c'), -55, -21, 0, -0.3);
  {
    const plat = new THREE.Group();
    const deck = cyl(3.2, 3.2, 0.25, MAT.plank, 12);
    plat.add(deck);
    for (let i = 0; i < 12; i++) {
      const a = (i / 12) * Math.PI * 2;
      plat.add(box(0.1, 0.8, 0.1, MAT.wood, Math.cos(a) * 3.1, 0.45, Math.sin(a) * 3.1));
    }
    const ring = mesh(new THREE.TorusGeometry(3.1, 0.06, 4, 24), MAT.wood);
    ring.rotation.x = Math.PI / 2;
    ring.position.y = 0.85;
    plat.add(ring);
    const throne = new THREE.Group();
    throne.add(box(1.0, 0.5, 0.9, MAT.red, 0, 0.4, 0));
    throne.add(box(1.0, 1.2, 0.2, MAT.red, 0, 0.9, -0.4));
    throne.add(box(1.1, 0.12, 0.25, MAT.hive, 0, 1.55, -0.4));
    throne.position.set(0, 0, 1.9);
    plat.add(throne);
    const flagPole = box(0.08, 2.4, 0.08, MAT.wood, -2.2, 1.3, -1.2);
    plat.add(flagPole);
    const flag = box(0.9, 0.55, 0.03, MAT.hive, -1.75, 2.2, -1.2);
    plat.add(flag);
    plat.position.y = 2.7;
    mk.add(plat);
    const ladder = [];
    for (let i = 0; i < 6; i++) ladder.push(at(new THREE.BoxGeometry(0.8, 0.07, 0.07), 0, 0.3 + i * 0.45, 0));
    ladder.push(at(new THREE.BoxGeometry(0.07, 2.8, 0.07), -0.4, 1.4, 0), at(new THREE.BoxGeometry(0.07, 2.8, 0.07), 0.4, 1.4, 0));
    const lad = mesh(merge(ladder), MAT.wood);
    lad.position.set(0, 0, 1.05);
    lad.rotation.x = -0.12;
    mk.add(lad);
  }
  const bigTrees = [honey, mk, home];

  // Bridge across the creek
  {
    const r = hf.river.closest(-12, 2);
    const p = hf.river.at(r.t);
    const ang = Math.atan2(p.dx, p.dz) + Math.PI / 2;
    const y = hf.bedAt(r.t) + 1.4;
    const b = bridge(hf.riverWidth(r.t) * 2 + 5, 2.0);
    b.position.set(p.x, y, p.z);
    b.rotation.y = ang;
    root.add(b);
  }
  // A second small footbridge near the falls path
  {
    const r = hf.river.closest(2, -20);
    const p = hf.river.at(r.t);
    const b = bridge(hf.riverWidth(r.t) * 2 + 4, 1.4);
    b.position.set(p.x, hf.bedAt(r.t) + 1.3, p.z);
    b.rotation.y = Math.atan2(p.dx, p.dz) + Math.PI / 2;
    root.add(b);
  }

  // Lake: dock, boat (summer), lily pads (summer), skating marks are part of the ice shader
  {
    const dock = new THREE.Group();
    const planks = [];
    for (let i = 0; i < 12; i++) planks.push(at(new THREE.BoxGeometry(1.8, 0.12, 0.42), 0, 0, -i * 0.5));
    dock.add(mesh(merge(planks), MAT.plank));
    for (const [x, z] of [[-0.85, 0], [0.85, 0], [-0.85, -5.5], [0.85, -5.5]]) dock.add(box(0.18, 1.6, 0.18, MAT.log, x, -0.6, z));
    dock.position.set(-31, LAKE.level + 0.45, 46);
    dock.rotation.y = -Math.PI / 2 - 0.35;
    root.add(dock);
    const b = boat();
    b.position.set(-48, LAKE.level - 0.05, 50);
    root.add(b);
    season(b, (p) => p.weights[1] + p.weights[0] * 0.6 + p.weights[2] * 0.6);
    animated.push((t) => {
      const a = t * 0.05;
      b.position.x = LAKE.x + Math.cos(a) * LAKE.rx * 0.45;
      b.position.z = LAKE.z + Math.sin(a) * LAKE.rz * 0.45;
      b.rotation.y = -a;
      b.position.y = LAKE.level - 0.05 + Math.sin(t * 1.4) * 0.05;
    });
    const pads = [], lotus = [];
    for (let i = 0; i < 46; i++) {
      const a = R() * Math.PI * 2, r = 0.6 + R() * 0.32;
      const x = LAKE.x + Math.cos(a) * LAKE.rx * r, z = LAKE.z + Math.sin(a) * LAKE.rz * r;
      pads.push(at(new THREE.CircleGeometry(0.5 + R() * 0.4, 9, 0.4, Math.PI * 1.8), x, LAKE.level + 0.05, z, -Math.PI / 2, 0, R() * 6));
      if (R() < 0.3) lotus.push(at(new THREE.ConeGeometry(0.22, 0.35, 6), x + 0.2, LAKE.level + 0.2, z));
    }
    const padM = mesh(merge(pads), MAT.lily, false);
    const lotM = mesh(merge(lotus), MAT.lotus, false);
    const lilies = new THREE.Group();
    lilies.add(padM, lotM);
    root.add(lilies);
    season(lilies, (p) => p.weights[1] + p.weights[0] * 0.3 + p.weights[2] * 0.4);
  }

  // Meadow: kite (spring), haystacks (autumn), snowmen (winter)
  const m = CLEARINGS.find((c) => c.meadow);
  {
    const k = kite();
    root.add(k);
    season(k, (p) => p.weights[0] + p.weights[1] * 0.3);
    const anchor = new THREE.Vector3(m.x + 2, hf.h(m.x + 2, m.z + 3) + 1, m.z + 3);
    const string = new THREE.Line(new THREE.BufferGeometry().setFromPoints([anchor, anchor]), new THREE.LineBasicMaterial({ color: '#ffffff' }));
    root.add(string);
    animated.push((t) => {
      k.position.set(m.x - 6 + Math.sin(t * 0.4) * 2, anchor.y + 14 + Math.sin(t * 0.9) * 1.2, m.z - 4 + Math.cos(t * 0.3) * 1.5);
      k.rotation.set(0.2, Math.sin(t * 0.5) * 0.4, Math.sin(t * 1.1) * 0.25);
      const a = string.geometry.attributes.position;
      a.setXYZ(1, k.position.x, k.position.y - 1.2, k.position.z);
      a.needsUpdate = true;
      string.visible = k.visible;
    });
    for (let i = 0; i < 5; i++) {
      const a = (i / 5) * Math.PI * 2 + 0.3, r = 7 + R() * 4;
      season(place(haystack(), m.x + Math.cos(a) * r, m.z + Math.sin(a) * r, R() * 6), (p) => p.weights[2]);
    }
    season(place(snowman(1.3), m.x + 3, m.z - 2, 0.3), (p) => p.weights[3]);
    season(place(snowman(0.9), m.x - 2, m.z + 4, -0.6), (p) => p.weights[3]);
    place(signpost([0.9, -1.4, 2.6]), m.x - 3, m.z - 6.5);
  }

  // Scattered mushrooms in autumn woods
  for (let i = 0; i < 60; i++) {
    const x = (R() - 0.5) * 180, z = -30 + R() * 110;
    if (hf.waterDist(x, z) < 2 || hf.pathDist(x, z) < 1) continue;
    season(place(mushroom(0.5 + R() * 0.7, R() < 0.6 ? MAT.red : MAT.hiveDark), x, z, R() * 6), (p) => p.weights[2] + p.weights[1] * 0.25);
  }

  // Luo Bo Tou's burrow and radish patch, east edge of the meadow
  {
    const bx = 24, bz = 21;
    const ring = mesh(new THREE.TorusGeometry(0.95, 0.35, 6, 14), M('#8a6440'));
    ring.rotation.x = Math.PI / 2;
    ring.scale.z = 0.6;
    place(ring, bx, bz, 0, 0.05);
    const hole = mesh(new THREE.CircleGeometry(0.85, 14), MAT.coal, false);
    hole.rotation.x = -Math.PI / 2;
    place(hole, bx, bz, 0, 0.08);
    const leaves = [], roots = [];
    for (let r = 0; r < 4; r++)
      for (let i = 0; i < 6; i++) {
        const x = bx + 2.5 + i * 0.9, z = bz - 2.5 + r * 1.2, y = hf.h(x, z);
        roots.push(at(new THREE.SphereGeometry(0.22, 6, 5), x, y + 0.08, z));
        for (let k = 0; k < 3; k++) leaves.push(at(new THREE.ConeGeometry(0.12, 0.6, 4), x, y + 0.4, z, 0.35, (k / 3) * Math.PI * 2, 0));
      }
    const patch = new THREE.Group();
    patch.add(mesh(merge(leaves), MAT.green, false), mesh(merge(roots), M('#e04a5a'), false));
    root.add(patch);
    season(patch, (p) => 1 - p.weights[3]);
  }

  // Road gate at the edge of the board
  {
    const g = new THREE.Group();
    for (const x of [-3, 3]) g.add(box(0.5, 5, 0.5, MAT.log, x, 2.5, 0));
    g.add(box(7.6, 1.1, 0.35, MAT.plank, 0, 4.6, 0));
    g.add(box(7.9, 0.25, 0.6, MAT.roof, 0, 5.3, 0));
    place(g, 93, 65.3, Math.atan2(12, 6) + Math.PI / 2);
  }

  const setSeason = (p) => {
    for (const s of seasonal) {
      const w = Math.min(1, s.w(p));
      const e = w * w * (3 - 2 * w);
      s.obj.scale.setScalar(Math.max(0.0001, e * s.s0));
      s.obj.visible = e > 0.01;
    }
    for (const t of bigTrees) {
      t.userData.leafU.value = p.leafScale;
      t.userData.crown.visible = p.leafScale > 0.01;
      t.userData.crown.material.color.copy(p.leaf[0]);
    }
  };
  const setNight = (n) => {
    for (const w of windows) w.emissiveIntensity = 0.15 + n * 2.6;
  };
  return { root, setSeason, setNight, animated, chimney };
}
