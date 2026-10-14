import * as THREE from 'three';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import { tentGeometry } from '../army/figures.js';
import { makeFlagTexture } from '../army/flags.js';

const EARTH = '#a48d69';
const EARTH_DARK = '#7d6a4f';
const TILE = '#5f646a';
const TIMBER = '#5b3f27';

function colored(geo, color) {
  const g = geo.index ? geo.toNonIndexed() : geo;
  g.deleteAttribute('uv');
  const c = new THREE.Color(color);
  const n = g.attributes.position.count;
  const arr = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) arr.set([c.r, c.g, c.b], i * 3);
  g.setAttribute('color', new THREE.BufferAttribute(arr, 3));
  return g;
}
function at(geo, x, y, z, ry = 0) {
  geo.rotateY(ry);
  geo.translate(x, y, z);
  return geo;
}
function hipRoof(w, d, h) {
  const g = new THREE.ConeGeometry(Math.SQRT1_2, 1, 4, 1);
  g.rotateY(Math.PI / 4);
  g.scale(w, h, d);
  return g;
}

/** Rammed-earth walled city: walls, gate towers, corner towers and a hall. Origin at ground centre. */
export function walledCity({ w, d, wallH, wallT, detail = 1 }) {
  const parts = [];
  const sink = wallH * 1.5;
  const H = wallH + sink;
  // walls with a darker parapet
  const walls = [
    [0, -d / 2, w, wallT],
    [0, d / 2, w, wallT],
    [-w / 2, 0, wallT, d],
    [w / 2, 0, wallT, d],
  ];
  for (const [x, z, ww, dd] of walls) {
    parts.push(colored(at(new THREE.BoxGeometry(ww, H, dd), x, H / 2 - sink, z), EARTH));
    parts.push(colored(at(new THREE.BoxGeometry(ww + wallT * 0.2, wallH * 0.18, dd + wallT * 0.2), x, wallH + wallH * 0.09, z), EARTH_DARK));
  }
  // gate towers (one per side) and corner towers
  const gt = wallT * 2.6;
  const gates = [
    [0, -d / 2, 0],
    [0, d / 2, 0],
    [-w / 2, 0, Math.PI / 2],
    [w / 2, 0, Math.PI / 2],
  ];
  for (const [x, z, ry] of gates) {
    parts.push(colored(at(new THREE.BoxGeometry(gt * 1.6, wallH * 1.25, gt), x, (wallH * 1.25) / 2, z, ry), EARTH_DARK));
    parts.push(colored(at(new THREE.BoxGeometry(gt * 1.3, wallH * 0.55, gt * 0.8), x, wallH * 1.25 + wallH * 0.27, z, ry), '#8a5b3a'));
    parts.push(colored(at(hipRoof(gt * 2.0, gt * 1.4, wallH * 0.6), x, wallH * 1.8 + wallH * 0.3, z, ry), TILE));
  }
  for (const sx of [-1, 1]) {
    for (const sz of [-1, 1]) {
      parts.push(colored(at(new THREE.BoxGeometry(gt, wallH * 1.35, gt), (sx * w) / 2, (wallH * 1.35) / 2, (sz * d) / 2), EARTH_DARK));
      parts.push(colored(at(hipRoof(gt * 1.3, gt * 1.3, wallH * 0.45), (sx * w) / 2, wallH * 1.35 + wallH * 0.22, (sz * d) / 2), TILE));
    }
  }
  if (detail > 0) {
    // central hall
    parts.push(colored(at(new THREE.BoxGeometry(w * 0.16, wallH * 0.2, d * 0.12), 0, wallH * 0.1, -d * 0.08), '#b7a280'));
    parts.push(colored(at(new THREE.BoxGeometry(w * 0.12, wallH * 0.55, d * 0.08), 0, wallH * 0.2 + wallH * 0.27, -d * 0.08), '#8c3b2a'));
    parts.push(colored(at(hipRoof(w * 0.19, d * 0.13, wallH * 0.55), 0, wallH * 0.75 + wallH * 0.27, -d * 0.08), TILE));
    // streets of houses
    const rnd = mulberry(7);
    const n = Math.round(34 * detail);
    for (let i = 0; i < n; i++) {
      const x = (rnd() - 0.5) * w * 0.82;
      const z = (rnd() - 0.5) * d * 0.82;
      if (Math.abs(x) < w * 0.12 && Math.abs(z + d * 0.08) < d * 0.1) continue;
      const hw = w * (0.035 + rnd() * 0.03);
      const hd = d * (0.03 + rnd() * 0.025);
      const hh = wallH * (0.28 + rnd() * 0.2);
      const ry = rnd() < 0.5 ? 0 : Math.PI / 2;
      parts.push(colored(at(new THREE.BoxGeometry(hw, hh, hd), x, hh / 2, z, ry), rnd() < 0.5 ? '#bba887' : '#a8977a'));
      parts.push(colored(at(hipRoof(hw * 1.25, hd * 1.3, hh * 0.6), x, hh + hh * 0.3, z, ry), rnd() < 0.7 ? TILE : '#5a4a3a'));
    }
  }
  const geo = mergeGeometries(parts);
  geo.computeVertexNormals();
  const mesh = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.85 }));
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  return mesh;
}

function mulberry(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function flagPole(text, side, scale) {
  const g = new THREE.Group();
  const poleH = scale;
  const pole = new THREE.Mesh(new THREE.CylinderGeometry(scale * 0.012, scale * 0.016, poleH, 5), new THREE.MeshStandardMaterial({ color: '#3b2a1a' }));
  pole.position.y = poleH / 2;
  g.add(pole);
  const tex = makeFlagTexture(text, side);
  const fw = scale * 0.38;
  const fh = scale * 0.44;
  const geo = new THREE.PlaneGeometry(fw, fh);
  geo.translate(fw / 2, 0, 0);
  const flag = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ map: tex, side: THREE.DoubleSide, transparent: true, alphaTest: 0.4 }));
  flag.position.y = poleH - fh / 2;
  g.add(flag);
  g.userData.flag = flag;
  return g;
}

/**
 * Static and scheduled scenery for one table: cities, forts, camps, the palisade across the
 * Huai and forests. `schedule` maps prop ids to [t0, t1] visibility windows.
 */
export class PropsLayer {
  constructor(resolver, places, { scale, holder, schedule = {} } = {}) {
    this.R = resolver;
    this.proj = resolver.proj;
    this.scale = scale;
    this.holder = holder;
    this.schedule = schedule;
    this.group = new THREE.Group();
    this.group.name = 'props';
    this.timed = [];
    this.flags = [];
    if (scale === 'tactical') this.buildTactical(places);
    else this.buildStrategic(places);
  }

  place(obj, lonlat, { sink = true, footprint = 0.5 } = {}) {
    const [x, z] = this.R.point(lonlat);
    let y = this.proj.groundY(x, z);
    if (sink) {
      for (const [dx, dz] of [
        [-1, -1],
        [1, -1],
        [-1, 1],
        [1, 1],
      ]) {
        y = Math.min(y, this.proj.groundY(x + dx * footprint, z + dz * footprint));
      }
    }
    obj.position.set(x, Math.max(y, 0), z);
    this.group.add(obj);
    return obj;
  }

  buildStrategic(places) {
    for (const p of places) {
      if (p.kind !== 'city' && p.kind !== 'capital') continue;
      const cap = p.kind === 'capital';
      const size = cap ? 1.25 : p.rank === 1 ? 0.85 : 0.65;
      const city = walledCity({ w: size, d: size * 0.85, wallH: cap ? 0.26 : 0.2, wallT: size * 0.1, detail: cap ? 0.6 : 0.25 });
      this.place(city, p.at, { footprint: size * 0.5 });
    }
  }

  buildTactical(places) {
    // 寿阳 (寿春): the walled city on the south bank of the 淝水
    const shou = walledCity({ w: 2.15, d: 1.75, wallH: 0.075, wallT: 0.06, detail: 1.4 });
    this.place(shou, [116.786, 32.5775], { footprint: 1.1 });
    this.shou = shou;
    // flags over the north gate: 晋 / 秦
    const fJin = flagPole('晋', 'jin', 0.42);
    const fQin = flagPole('秦', 'qin', 0.42);
    for (const f of [fJin, fQin]) {
      f.position.set(shou.position.x + 0.0, shou.position.y + 0.15, shou.position.z - 1.75 / 2);
      this.group.add(f);
    }
    this.flags.push({ jin: fJin, qin: fQin });

    // 硖石 two forts on the hills either side of the gorge
    for (const ll of [
      [116.7445, 32.6905],
      [116.7275, 32.7035],
    ]) {
      const fort = walledCity({ w: 0.42, d: 0.36, wallH: 0.06, wallT: 0.04, detail: 0 });
      this.place(fort, ll, { footprint: 0.2 });
    }
    // 下蔡
    const xc = walledCity({ w: 0.8, d: 0.65, wallH: 0.06, wallT: 0.045, detail: 0.4 });
    this.place(xc, [116.704, 32.716], { footprint: 0.4 });

    // camps
    this.camp('jincamp', [117.222, 32.702], 'jin', 1.05, 0.8, 34);
    this.camp('liangcamp', [117.116, 32.737], 'qin', 0.95, 0.7, 30);
    this.camp('qincamp_w', [116.748, 32.567], 'qin', 0.9, 0.62, 26);
    this.camp('qincamp_s', [116.80, 32.562], 'qin', 0.7, 0.5, 18);
    this.palisade('palisade', [117.0935, 32.7775], 0.95);
    this.forest();
  }

  camp(id, lonlat, side, rx, rz, tents) {
    const g = new THREE.Group();
    const posts = new THREE.InstancedMesh(
      new THREE.CylinderGeometry(0.012, 0.014, 0.12, 4),
      new THREE.MeshStandardMaterial({ color: TIMBER, roughness: 0.9 }),
      140
    );
    const [cx, cz] = this.R.point(lonlat);
    const m = new THREE.Matrix4();
    for (let i = 0; i < 140; i++) {
      const a = (i / 140) * Math.PI * 2;
      const x = cx + Math.cos(a) * rx;
      const z = cz + Math.sin(a) * rz;
      m.makeTranslation(x, Math.max(this.proj.groundY(x, z), 0) + 0.05, z);
      posts.setMatrixAt(i, m);
    }
    posts.castShadow = true;
    g.add(posts);
    const tentGeo = tentGeometry(side);
    const tentMesh = new THREE.InstancedMesh(tentGeo, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.85 }), tents);
    const rnd = mulberry(id.length * 31);
    const q = new THREE.Quaternion();
    const sc = new THREE.Vector3(0.11, 0.11, 0.11);
    for (let i = 0; i < tents; i++) {
      const r = Math.sqrt(rnd()) * 0.78;
      const a = rnd() * Math.PI * 2;
      const x = cx + Math.cos(a) * rx * r;
      const z = cz + Math.sin(a) * rz * r;
      q.setFromAxisAngle(new THREE.Vector3(0, 1, 0), rnd() * Math.PI);
      m.compose(new THREE.Vector3(x, Math.max(this.proj.groundY(x, z), 0), z), q, sc);
      tentMesh.setMatrixAt(i, m);
    }
    tentMesh.castShadow = true;
    g.add(tentMesh);
    this.group.add(g);
    this.timed.push({ id, obj: g });
  }

  palisade(id, lonlat, length) {
    // posts across the river, perpendicular to the nearest reach
    const [cx, cz] = this.R.point(lonlat);
    let best = null;
    let bd = Infinity;
    for (const r of Object.values(this.R.rivers)) {
      const s = r.closestS(cx, cz);
      const p = r.at(s, {});
      const d = (p.x - cx) ** 2 + (p.z - cz) ** 2;
      if (d < bd) {
        bd = d;
        best = p;
      }
    }
    const n = 46;
    const mesh = new THREE.InstancedMesh(
      new THREE.CylinderGeometry(0.01, 0.013, 0.16, 5),
      new THREE.MeshStandardMaterial({ color: '#4a321e', roughness: 0.9 }),
      n
    );
    const m = new THREE.Matrix4();
    const nx = -best.tz;
    const nz = best.tx;
    for (let i = 0; i < n; i++) {
      const f = (i / (n - 1) - 0.5) * length;
      const x = best.x + nx * f + (i % 2) * 0.012;
      const z = best.z + nz * f;
      const y = this.proj.groundY(x, z);
      m.makeRotationZ(((i * 37) % 7) * 0.03 - 0.09);
      m.setPosition(x, y + 0.06, z);
      mesh.setMatrixAt(i, m);
    }
    mesh.castShadow = true;
    // a boom chain between the posts
    const chain = new THREE.Mesh(
      new THREE.CylinderGeometry(0.006, 0.006, length, 4),
      new THREE.MeshStandardMaterial({ color: '#2b2520', roughness: 0.6, metalness: 0.4 })
    );
    chain.rotation.z = Math.PI / 2;
    chain.rotation.y = -Math.atan2(nz, nx);
    chain.position.set(best.x, this.proj.groundY(best.x, best.z) + 0.1, best.z);
    const g = new THREE.Group();
    g.add(mesh, chain);
    this.group.add(g);
    this.timed.push({ id, obj: g });
  }

  forest() {
    // autumn oak and pine scrub on the hills (八公山、舜耕山、上窑山…)
    const f = this.proj.field;
    const cands = [];
    const rnd = mulberry(1983);
    const N = 5200;
    let tries = 0;
    while (cands.length < N && tries < N * 30) {
      tries++;
      const u = rnd();
      const v = rnd();
      const h = f.height(u, v);
      if (h < 38) continue;
      const p = Math.min(1, (h - 38) / 50);
      if (rnd() > p * 0.9) continue;
      if (f.water(u, v) < 60) continue;
      cands.push([u, v, h]);
    }
    const trunk = colored(new THREE.CylinderGeometry(0.08, 0.1, 0.5, 5).translate(0, 0.25, 0), '#4b3424');
    const crown = colored(new THREE.IcosahedronGeometry(0.42, 0).scale(1, 1.25, 1).translate(0, 0.8, 0), '#ffffff');
    const geo = mergeGeometries([trunk, crown]);
    geo.computeVertexNormals();
    const mesh = new THREE.InstancedMesh(geo, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.95 }), cands.length);
    const m = new THREE.Matrix4();
    const q = new THREE.Quaternion();
    const palette = ['#5b6534', '#6f6a33', '#8a5a2b', '#9b7a35', '#4e5a30', '#7d4a26', '#a38d4a'].map((c) => new THREE.Color(c));
    this.treePositions = [];
    cands.forEach(([u, v], i) => {
      const [x, z] = this.proj.uvToWorld(u, v);
      const y = this.proj.groundY(x, z);
      const s = 0.07 + rnd() * 0.06;
      q.setFromAxisAngle(new THREE.Vector3(0, 1, 0), rnd() * 6.28);
      m.compose(new THREE.Vector3(x, y - 0.01, z), q, new THREE.Vector3(s, s * (0.9 + rnd() * 0.4), s));
      mesh.setMatrixAt(i, m);
      mesh.setColorAt(i, palette[Math.floor(rnd() * palette.length)]);
      this.treePositions.push([x, y, z]);
    });
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    mesh.name = 'forest';
    this.group.add(mesh);
    this.forestMesh = mesh;
  }

  setVisible(v) {
    this.group.visible = v;
  }

  update(T) {
    for (const t of this.timed) {
      const w = this.schedule[t.id];
      t.obj.visible = !w || (T >= w[0] && T < w[1]);
    }
    if (this.holder && this.flags.length) {
      const h = this.holder(T);
      for (const f of this.flags) {
        f.jin.visible = h === 'jin';
        f.qin.visible = h === 'qin';
      }
    }
  }
}
