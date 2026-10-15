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
  const skin = mat('#f1c49b'), jacket = mat('#d9672b'), pants = mat('#3f5f8f'), boot = mat('#3a2a1e'), K = mat('#1a1a1a'), W = mat('#ffffff');
  const body = new THREE.Group();
  g.add(body);
  body.add(part(CYL, jacket, 0, 1.55, 0, 0.5, 1.0, 0.38));
  body.add(part(SPH, jacket, 0, 2.05, 0, 0.52, 0.25, 0.4));
  body.add(part(CYL, mat('#5a3a22'), 0, 1.1, 0, 0.52, 0.12, 0.4));
  const head = new THREE.Group();
  head.position.y = 2.75;
  body.add(head);
  head.add(part(SPH, skin, 0, 0, 0, 0.5, 0.58, 0.5));
  head.add(part(SPH, mat('#e0594a'), 0, -0.08, 0.47, 0.13, 0.11, 0.12)); // red nose
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
  // headwear hides the bald head: a hard hat most of the year, an ushanka in winter
  const hardHat = new THREE.Group();
  hardHat.add(part(new THREE.SphereGeometry(0.54, 14, 8, 0, Math.PI * 2, 0, Math.PI / 2), mat('#f2c12e', { roughness: 0.4 }), 0, 0.14, 0));
  hardHat.add(part(CYL, mat('#f2c12e', { roughness: 0.4 }), 0, 0.15, 0.08, 0.66, 0.04, 0.66));
  hardHat.add(part(new THREE.BoxGeometry(0.12, 0.08, 1.0), mat('#e0aa1c'), 0, 0.66, 0));
  head.add(hardHat);
  const fur = mat('#5b4634'), furLight = mat('#d8cbb6');
  const ushanka = new THREE.Group();
  ushanka.add(part(new THREE.SphereGeometry(0.56, 14, 8, 0, Math.PI * 2, 0, Math.PI / 2), fur, 0, 0.1, 0));
  ushanka.add(part(CYL, furLight, 0, 0.18, 0, 0.6, 0.18, 0.6));
  for (const sx of [-1, 1]) ushanka.add(part(new THREE.BoxGeometry(0.1, 0.5, 0.4), furLight, sx * 0.55, -0.1, 0));
  head.add(ushanka);
  scarfG.userData.hat = ushanka;
  scarfG.userData.hardHat = hardHat;
  return { g, body, head, arms, legs, scarf: scarfG };
}

export const CHARACTERS = [
  {
    id: 'briar', name: '熊大', desc: '哥哥，红棕色毛，聪明机智，森林的守护者。常在树洞、木桥和猴王树之间巡山。',
    make: () => bear({ fur: '#86452a', muzzle: '#e6c49a', belly: '#c98f68', big: 1, scarf: '#d83a33' }),
    route: [[28, -4], [20, -3], [8, 1], [-4, 2], [-12, 2], [-24, -5], [-40, -14], [-50, -18]], speed: 2.4, scale: 1.25,
  },
  {
    id: 'bramble', name: '熊二', desc: '弟弟，浅黄棕色毛，更壮实，憨厚力气大，最爱蜂蜜。总在树洞和蜂蜜树之间来回。',
    make: () => bear({ fur: '#c79a5c', muzzle: '#f3e0bb', belly: '#ead1a0', big: 1.25, scarf: '#f2c230' }),
    route: [[27, -2], [31, -8], [34, -12], [38, -18], [41, -22]], speed: 1.5, scale: 1.3,
  },
  {
    id: 'vick', name: '光头强', desc: '秃顶的伐木工，戴安全帽（冬天戴棉帽），穿夹克和牛仔裤，扛着电锯，开卡车进出森林，受李老板雇佣砍树。',
    make: logger,
    route: [[52, 43.5], [49.5, 45.5], [47.5, 39], [52, 47], [60, 45], [65, 38], [70, 33]], speed: 2.0, scale: 1.2,
  },
];

// ---- forest animals --------------------------------------------------------------------------

function squirrel() {
  const g = new THREE.Group();
  const fur = mat('#c4562a'), cream = mat('#f1dcc0'), K = mat('#1a1a1a'), W = mat('#ffffff');
  const body = new THREE.Group();
  g.add(body);
  body.add(part(SPH, fur, 0, 0.45, 0, 0.32, 0.4, 0.3));
  body.add(part(SPH, cream, 0, 0.42, 0.16, 0.2, 0.28, 0.16));
  const head = new THREE.Group();
  head.position.y = 0.95;
  body.add(head);
  head.add(part(SPH, fur, 0, 0, 0, 0.3, 0.28, 0.28));
  head.add(part(SPH, cream, 0, -0.07, 0.2, 0.15, 0.12, 0.1));
  head.add(part(new THREE.BoxGeometry(0.12, 0.12, 0.03), W, 0, -0.18, 0.27)); // big front teeth
  for (const sx of [-1, 1]) {
    head.add(part(SPH, K, sx * 0.12, 0.06, 0.25, 0.05, 0.06, 0.03));
    const ear = part(new THREE.ConeGeometry(0.08, 0.22, 5), fur, sx * 0.16, 0.3, 0);
    ear.rotation.z = -sx * 0.3;
    head.add(ear);
  }
  const tail = new THREE.Group();
  for (let i = 0; i < 6; i++) {
    const a = i / 5;
    tail.add(part(SPH, fur, 0, 0.3 + Math.sin(a * 2.6) * 0.75, -0.35 - Math.sin(a * 1.6) * 0.35 + a * a * 0.25, 0.22 + a * 0.06, 0.24, 0.22));
  }
  body.add(tail);
  return { g, body, head, tail };
}

function monkey({ fur, face, crown = false }) {
  const g = new THREE.Group();
  const F = mat(fur), Fc = mat(face), K = mat('#1a1a1a');
  const body = new THREE.Group();
  g.add(body);
  body.add(part(SPH, F, 0, 0.7, 0, 0.42, 0.52, 0.38));
  body.add(part(SPH, Fc, 0, 0.65, 0.22, 0.26, 0.34, 0.2));
  const head = new THREE.Group();
  head.position.y = 1.45;
  body.add(head);
  head.add(part(SPH, F, 0, 0, 0, 0.4, 0.38, 0.38));
  head.add(part(SPH, Fc, 0, -0.04, 0.2, 0.3, 0.26, 0.22));
  for (const sx of [-1, 1]) {
    head.add(part(SPH, K, sx * 0.11, 0.05, 0.4, 0.05, 0.07, 0.03));
    head.add(part(SPH, Fc, sx * 0.42, 0.02, 0, 0.12, 0.14, 0.06));
  }
  const arms = [];
  for (const sx of [-1, 1]) {
    const a = limb(F, 0.5, 0.1);
    a.position.set(sx * 0.42, 1.05, 0);
    a.rotation.z = sx * 0.4;
    body.add(a);
    arms.push(a);
  }
  const tail = part(new THREE.TorusGeometry(0.35, 0.06, 5, 12, Math.PI * 1.4), F, 0, 0.5, -0.45);
  tail.rotation.y = Math.PI / 2;
  body.add(tail);
  if (crown) {
    const gold = mat('#f4c22b', { metalness: 0.5, roughness: 0.35 });
    const c = new THREE.Group();
    c.add(part(CYL, gold, 0, 0, 0, 0.26, 0.12, 0.26));
    for (let i = 0; i < 5; i++) {
      const a = (i / 5) * Math.PI * 2;
      c.add(part(new THREE.ConeGeometry(0.06, 0.18, 4), gold, Math.cos(a) * 0.22, 0.13, Math.sin(a) * 0.22));
    }
    c.add(part(SPH, mat('#e0362b'), 0, 0.02, 0.26, 0.05, 0.05, 0.03));
    c.position.y = 0.4;
    head.add(c);
  }
  return { g, body, head, arms };
}

function owl() {
  const g = new THREE.Group();
  const back = mat('#c99b5f'), face = mat('#f6efe2'), K = mat('#1a1a1a');
  const body = new THREE.Group();
  g.add(body);
  body.add(part(SPH, back, 0, 0.5, 0, 0.36, 0.5, 0.34));
  body.add(part(SPH, face, 0, 0.45, 0.14, 0.26, 0.38, 0.22));
  const head = new THREE.Group();
  head.position.y = 1.08;
  body.add(head);
  head.add(part(SPH, back, 0, 0, 0, 0.36, 0.32, 0.32));
  head.add(part(SPH, face, 0, -0.02, 0.18, 0.28, 0.25, 0.16)); // heart-shaped face disc
  for (const sx of [-1, 1]) head.add(part(SPH, K, sx * 0.1, 0.02, 0.32, 0.06, 0.07, 0.03));
  head.add(part(new THREE.ConeGeometry(0.04, 0.1, 4), mat('#d9a441'), 0, -0.08, 0.34));
  const wings = [];
  for (const sx of [-1, 1]) {
    const piv = new THREE.Group();
    piv.position.set(sx * 0.3, 0.7, 0);
    piv.add(part(SPH, back, sx * 0.45, 0, 0, 0.55, 0.08, 0.28));
    body.add(piv);
    wings.push(piv);
  }
  return { g, body, head, wings };
}

function groundhog() {
  const g = new THREE.Group();
  const fur = mat('#8b6942'), light = mat('#d8bf98'), K = mat('#1a1a1a'), W = mat('#ffffff');
  const body = new THREE.Group();
  g.add(body);
  body.add(part(SPH, fur, 0, 0.5, 0, 0.36, 0.55, 0.34));
  body.add(part(SPH, light, 0, 0.45, 0.16, 0.22, 0.38, 0.2));
  const head = new THREE.Group();
  head.position.y = 1.08;
  body.add(head);
  head.add(part(SPH, fur, 0, 0, 0, 0.32, 0.28, 0.3));
  head.add(part(SPH, light, 0, -0.07, 0.2, 0.17, 0.13, 0.12));
  head.add(part(new THREE.BoxGeometry(0.1, 0.1, 0.03), W, 0, -0.18, 0.29));
  for (const sx of [-1, 1]) {
    head.add(part(SPH, K, sx * 0.12, 0.06, 0.26, 0.05, 0.06, 0.03));
    head.add(part(SPH, fur, sx * 0.24, 0.2, 0, 0.07, 0.07, 0.04));
  }
  return { g, body, head };
}

// Monkey king's platform on the big tree at (-55, -21), scale 1.55 (see buildings.js).
const MK = { x: -55, z: -21, s: 1.55 };
const MEADOW = { x: 12, z: 30 };
const BURROW = { x: 24, z: 21 };

export const CRITTERS = [
  {
    id: 'bangbang', name: '蹦蹦', desc: '松鼠，大门牙，爱装死，消息灵通。在小溪木桥西边的林子里蹦来蹦去。',
    make: squirrel, scale: 1.3, tagY: 1.9,
    tick(c, dt, t, hf) {
      const a = t * 0.6;
      const x = -22 + Math.cos(a) * 3, z = -9 + Math.sin(a) * 3;
      const hop = Math.abs(Math.sin(t * 5));
      c.holder.position.set(x, hf.h(x, z) + hop * 0.6, z);
      c.holder.rotation.y = -a;
      c.rig.tail.rotation.x = Math.sin(t * 5) * 0.15;
    },
  },
  {
    id: 'jiji', name: '吉吉国王', desc: '自称“吉吉国王”的猴子，带着猴子们住在西边的大树上，平台上有他的宝座。',
    make: () => monkey({ fur: '#7a5636', face: '#e9c9a0', crown: true }), scale: 1.3, tagY: 2.9,
    tick(c, dt, t, hf) {
      const top = hf.h(MK.x, MK.z) - 0.3 + 2.85 * MK.s;
      c.holder.position.set(MK.x, top + 0.35 * MK.s, MK.z + 1.85 * MK.s);
      c.rig.head.rotation.y = Math.sin(t * 0.7) * 0.5;
      c.rig.arms[1].rotation.z = 1.6 + Math.sin(t * 3) * 0.3;
    },
  },
  {
    id: 'maomao', name: '毛毛', desc: '金色的小猴子，吉吉国王的跟班，总是站在国王旁边。',
    make: () => monkey({ fur: '#e2a93c', face: '#f6dfb4' }), scale: 0.95, tagY: 2.2,
    tick(c, dt, t, hf) {
      const top = hf.h(MK.x, MK.z) - 0.3 + 2.85 * MK.s;
      c.holder.position.set(MK.x + 1.2 * MK.s, top + Math.abs(Math.sin(t * 2.2)) * 0.25, MK.z + 1.6 * MK.s);
      c.holder.rotation.y = -0.6;
      c.rig.arms[0].rotation.z = -1.2 - Math.sin(t * 4) * 0.4;
    },
  },
  {
    id: 'tutu', name: '涂涂', desc: '猫头鹰，森林里唯一会飞的角色，有时会突然健忘、迷迷糊糊。在花海草甸上空盘旋。',
    make: owl, scale: 1.3, tagY: 2.2,
    tick(c, dt, t, hf) {
      const a = t * 0.25;
      const x = MEADOW.x + Math.cos(a) * 16, z = MEADOW.z + Math.sin(a) * 12;
      c.holder.position.set(x, hf.h(MEADOW.x, MEADOW.z) + 13 + Math.sin(t * 0.9) * 1.5, z);
      c.holder.rotation.y = Math.atan2(-Math.sin(a) * 16, Math.cos(a) * 12);
      c.holder.rotation.z = 0.25;
      const f = Math.sin(t * 7) * 0.7;
      c.rig.wings[0].rotation.z = f;
      c.rig.wings[1].rotation.z = -f;
    },
  },
  {
    id: 'luobotou', name: '萝卜头', desc: '地鼠，脾气急，擅长打洞，爱囤大萝卜。洞口就在花海草甸东边的萝卜地旁。',
    make: groundhog, scale: 1.3, tagY: 1.9,
    tick(c, dt, t, hf) {
      const cyc = (t * 0.25) % 1;
      const up = Math.min(1, Math.max(0, Math.min(cyc * 6, (0.75 - cyc) * 6)));
      c.holder.position.set(BURROW.x, hf.h(BURROW.x, BURROW.z) - 1.5 + up * 1.4, BURROW.z);
      c.holder.rotation.y = Math.sin(t * 0.5) * 0.8;
      c.tag.visible = up > 0.5;
    },
  },
];
export const ALL_CHARACTERS = [...CHARACTERS, ...CRITTERS];

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
  for (const c of CRITTERS) {
    const rig = c.make();
    rig.g.scale.setScalar(c.scale);
    const holder = new THREE.Group();
    holder.add(rig.g);
    group.add(holder);
    const div = document.createElement('div');
    div.className = 'char-tag';
    div.textContent = c.name;
    const tag = new CSS2DObject(div);
    tag.position.set(0, c.tagY * c.scale, 0);
    holder.add(tag);
    list.push({ ...c, rig, holder, tag, div, critter: true });
  }

  const yAt = (x, z) => {
    let y = hf.h(x, z);
    const r = hf.river.closest(x, z);
    if (r.d < hf.riverWidth(r.t) + 3) y = Math.max(y, hf.bedAt(r.t) + 2.0);
    return y;
  };

  const update = (dt, t, season) => {
    for (const c of list) {
      if (c.critter) {
        c.tick(c, dt, t, hf);
        continue;
      }
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
      if (c.rig.scarf.userData.hat) {
        c.rig.scarf.userData.hat.visible = season.weights[3] > 0.5;
        c.rig.scarf.userData.hardHat.visible = season.weights[3] <= 0.5;
      }
    }
  };
  return { group, list, update };
}
