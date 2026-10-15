// Forest: instanced pines, broadleaf trees, birches, bushes, rocks and spring flowers.
// Crown colours follow the season per instance; deciduous crowns shrink away in winter.
import * as THREE from 'three';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import { rng, fbm, smooth } from './util.js';
import { BOARD, CLEARINGS } from './places.js';
import { snowify, stdMat } from './shared.js';

export const ni = (g) => (g.index ? g.toNonIndexed() : g);
export function merge(parts) {
  return mergeGeometries(parts.map((g) => {
    g = ni(g);
    for (const k of Object.keys(g.attributes)) if (!['position', 'normal', 'uv'].includes(k)) g.deleteAttribute(k);
    if (!g.attributes.uv) g.setAttribute('uv', new THREE.Float32BufferAttribute(new Float32Array(g.attributes.position.count * 2), 2));
    return g;
  }));
}
export const at = (g, x, y, z, rx = 0, ry = 0, rz = 0, s = 1) => {
  g.scale(s, s, s);
  g.rotateX(rx);
  g.rotateY(ry);
  g.rotateZ(rz);
  g.translate(x, y, z);
  return g;
};

function pineGeo() {
  const trunk = at(new THREE.CylinderGeometry(0.22, 0.34, 1.8, 6), 0, 0.9, 0);
  const crown = merge([
    at(new THREE.ConeGeometry(1.9, 2.8, 7), 0, 2.7, 0),
    at(new THREE.ConeGeometry(1.45, 2.4, 7), 0, 4.1, 0, 0, 0.4),
    at(new THREE.ConeGeometry(0.95, 2.0, 7), 0, 5.4, 0, 0, 0.8),
  ]);
  return { trunk: merge([trunk]), crown, center: new THREE.Vector3(0, 3.8, 0) };
}

function broadGeo() {
  const trunk = merge([
    at(new THREE.CylinderGeometry(0.26, 0.42, 3.4, 6), 0, 1.7, 0),
    at(new THREE.CylinderGeometry(0.07, 0.14, 2.0, 5), 0.55, 3.6, 0, 0, 0, -0.75),
    at(new THREE.CylinderGeometry(0.07, 0.14, 1.9, 5), -0.5, 3.8, 0.2, 0.2, 0, 0.7),
    at(new THREE.CylinderGeometry(0.06, 0.12, 1.7, 5), 0, 3.9, -0.55, -0.8, 0, 0),
    at(new THREE.CylinderGeometry(0.06, 0.12, 1.6, 5), 0.1, 4.2, 0.5, 0.7, 0, 0),
  ]);
  const crown = merge([
    at(new THREE.IcosahedronGeometry(1.9, 1), 0, 4.6, 0),
    at(new THREE.IcosahedronGeometry(1.35, 1), 1.2, 4.0, 0.4),
    at(new THREE.IcosahedronGeometry(1.3, 1), -1.1, 4.2, -0.5),
    at(new THREE.IcosahedronGeometry(1.2, 0), 0.2, 5.8, 0.3),
  ]);
  return { trunk, crown, center: new THREE.Vector3(0, 4.4, 0) };
}

function birchGeo() {
  const trunk = merge([
    at(new THREE.CylinderGeometry(0.15, 0.22, 5.2, 6), 0, 2.6, 0),
    at(new THREE.CylinderGeometry(0.04, 0.08, 1.4, 4), 0.35, 4.4, 0, 0, 0, -0.6),
    at(new THREE.CylinderGeometry(0.04, 0.08, 1.2, 4), -0.3, 4.9, 0, 0, 0, 0.6),
  ]);
  const crown = merge([
    at(new THREE.IcosahedronGeometry(1.25, 1).scale(1, 1.45, 1), 0, 5.2, 0),
    at(new THREE.IcosahedronGeometry(0.85, 0), 0.6, 4.6, 0.3),
  ]);
  return { trunk, crown, center: new THREE.Vector3(0, 5.6, 0) };
}

function bushGeo() {
  const crown = merge([
    at(new THREE.IcosahedronGeometry(0.9, 0), 0, 0.55, 0),
    at(new THREE.IcosahedronGeometry(0.65, 0), 0.7, 0.4, 0.2),
    at(new THREE.IcosahedronGeometry(0.6, 0), -0.6, 0.4, -0.2),
  ]);
  return { crown, center: new THREE.Vector3(0, 0.2, 0) };
}

function flowerGeo() {
  return merge([
    at(new THREE.CylinderGeometry(0.03, 0.03, 0.5, 3), 0, 0.25, 0),
    at(new THREE.ConeGeometry(0.2, 0.22, 6), 0, 0.55, 0, Math.PI),
  ]);
}

const tmpM = new THREE.Matrix4(), tmpQ = new THREE.Quaternion(), tmpS = new THREE.Vector3(), tmpP = new THREE.Vector3(), tmpC = new THREE.Color();

export function buildFlora(hf, palette) {
  const group = new THREE.Group();
  const R = rng(7);
  const half = BOARD / 2 - 2;
  const spots = { pine: [], broad: [], birch: [], bush: [], rock: [], flower: [] };

  const blocked = (x, z, pad = 0) => {
    for (const c of CLEARINGS) if (Math.hypot(x - c.x, z - c.z) < c.r + pad) return true;
    return false;
  };

  const step = 3.3;
  for (let z = -half; z < half; z += step)
    for (let x = -half; x < half; x += step) {
      const px = x + (R() - 0.5) * step * 1.1, pz = z + (R() - 0.5) * step * 1.1;
      const dens = (fbm(px * 0.025 + 40, pz * 0.025 - 9, 3) * 0.9 + 0.5) * 0.78;
      if (R() > dens) continue;
      const y = hf.h(px, pz);
      if (y > 34 + fbm(px * 0.1, pz * 0.1) * 4) continue;
      if (hf.normalY(px, pz) < 0.72) continue;
      if (hf.waterDist(px, pz) < 2.2) continue;
      if (hf.pathDist(px, pz) < 1.6) continue;
      if (blocked(px, pz)) continue;
      const north = smooth(-30, -60, pz);
      const birchZone = smooth(25, 5, Math.hypot(px + 82, pz - 22)) + smooth(14, 3, hf.waterDist(px, pz)) * 0.35;
      const r = R();
      let kind;
      if (r < 0.15 + north * 0.75 + smooth(18, 30, y) * 0.5) kind = 'pine';
      else if (R() < birchZone) kind = 'birch';
      else kind = 'broad';
      spots[kind].push({ x: px, y, z: pz, s: 0.75 + R() * 0.6, ry: R() * Math.PI * 2, v: R() });
    }

  // bushes along paths and clearing rims
  for (let i = 0; i < 900; i++) {
    const x = (R() - 0.5) * BOARD * 0.96, z = (R() - 0.5) * BOARD * 0.96;
    const pd = hf.pathDist(x, z);
    const nearC = CLEARINGS.some((c) => Math.abs(Math.hypot(x - c.x, z - c.z) - c.r * 1.05) < 2);
    if (!((pd > 1.4 && pd < 4) || nearC)) continue;
    if (hf.waterDist(x, z) < 1.5 || blocked(x, z, -1) || hf.h(x, z) > 30) continue;
    spots.bush.push({ x, y: hf.h(x, z), z, s: 0.6 + R() * 0.7, ry: R() * 6.28, v: R() });
  }
  // rocks: on the mountain, on creek banks, a few in the woods
  for (let i = 0; i < 1400 && spots.rock.length < 420; i++) {
    const x = (R() - 0.5) * BOARD * 0.97, z = (R() - 0.5) * BOARD * 0.97;
    const y = hf.h(x, z);
    const wd = hf.waterDist(x, z);
    const want = smooth(14, 30, y) * 0.8 + (wd > 0 && wd < 2.5 ? 0.6 : 0) + 0.05;
    if (R() > want || wd < 0.2 || blocked(x, z) || hf.pathDist(x, z) < 1) continue;
    spots.rock.push({ x, y, z, s: 0.4 + R() * (y > 20 ? 1.8 : 0.8), ry: R() * 6.28, v: R() });
  }
  // flowers: meadow and lakeside
  for (let i = 0; i < 6000 && spots.flower.length < 1600; i++) {
    const x = (R() - 0.5) * BOARD * 0.96, z = (R() - 0.5) * BOARD * 0.96;
    const meadow = CLEARINGS.some((c) => c.meadow && Math.hypot(x - c.x, z - c.z) < c.r * 1.25);
    const ok = meadow || (R() < 0.12 && hf.h(x, z) < 14);
    if (!ok || hf.pathDist(x, z) < 0.8 || hf.waterDist(x, z) < 0.6) continue;
    if (!meadow && blocked(x, z)) continue;
    spots.flower.push({ x, y: hf.h(x, z), z, s: 0.7 + R() * 0.7, ry: R() * 6.28, v: R() });
  }

  const sets = [];
  const mkSet = (name, list, geo, trunkColor, opts = {}) => {
    const leafU = { value: 1 };
    const crownMat = snowify(stdMat('#ffffff'), {
      key: name, sway: opts.sway ?? 0.012, snowLo: opts.snowLo ?? 0.2, snowHi: opts.snowHi ?? 0.6,
      leaf: opts.shrink ? { center: geo.center, uniform: leafU } : null,
    });
    const crown = new THREE.InstancedMesh(geo.crown, crownMat, list.length);
    crown.castShadow = true;
    crown.receiveShadow = true;
    let trunk = null;
    if (geo.trunk) {
      trunk = new THREE.InstancedMesh(geo.trunk, snowify(stdMat(trunkColor), { key: name + 't', sway: opts.sway ?? 0.012, snowLo: 0.5 }), list.length);
      trunk.castShadow = true;
    }
    list.forEach((t, i) => {
      tmpQ.setFromAxisAngle(THREE.Object3D.DEFAULT_UP, t.ry);
      tmpS.setScalar(t.s);
      tmpP.set(t.x, t.y - 0.15, t.z);
      tmpM.compose(tmpP, tmpQ, tmpS);
      crown.setMatrixAt(i, tmpM);
      trunk?.setMatrixAt(i, tmpM);
      crown.setColorAt(i, tmpC.set('#ffffff'));
    });
    group.add(crown);
    if (trunk) group.add(trunk);
    const set = { name, list, crown, trunk, leafU, ...opts };
    sets.push(set);
    return set;
  };

  mkSet('pine', spots.pine, pineGeo(), '#6b4a2f', { color: (p) => p.pine, sway: 0.008, snowLo: 0.3, snowHi: 0.75 });
  mkSet('broad', spots.broad, broadGeo(), '#6e4c33', { color: (p, v) => p.leaf[v < 0.45 ? 0 : v < 0.8 ? 1 : 2], shrink: true, leafKey: 'leafScale' });
  mkSet('birch', spots.birch, birchGeo(), '#ece8de', { color: (p) => p.birch, shrink: true, leafKey: 'leafScale' });
  mkSet('bush', spots.bush, bushGeo(), null, { color: (p, v) => p.leaf[v < 0.6 ? 0 : 1].clone().multiplyScalar(0.8), shrink: true, leafKey: 'bush', sway: 0.02 });
  mkSet('flower', spots.flower, { crown: flowerGeo(), center: new THREE.Vector3(0, -0.1, 0) }, null, {
    color: (p, v) => tmpC.set(['#ff8fb8', '#ffd84a', '#ffffff', '#b98cff', '#ff6a5a'][Math.floor(v * 5)]),
    shrink: true, leafKey: 'flowers', sway: 0.06, snowLo: 2, snowHi: 3,
  });
  {
    const rockGeo = merge([new THREE.DodecahedronGeometry(1, 0).scale(1, 0.7, 1)]);
    const rocks = mkSet('rock', spots.rock, { crown: rockGeo }, null, { color: (p, v) => p.rock.clone().multiplyScalar(0.85 + v * 0.3), sway: 0, snowLo: 0.3 });
    rocks.crown.castShadow = true;
  }

  const setSeason = (p) => {
    for (const s of sets) {
      const n = s.list.length;
      for (let i = 0; i < n; i++) {
        const v = s.list[i].v;
        tmpC.copy(s.color(p, v));
        if (s.name !== 'flower') tmpC.multiplyScalar(0.88 + v * 0.24);
        s.crown.setColorAt(i, tmpC);
      }
      if (s.crown.instanceColor) s.crown.instanceColor.needsUpdate = true;
      if (s.leafKey === 'leafScale') s.leafU.value = Math.max(0, p.leafScale);
      if (s.leafKey === 'bush') s.leafU.value = 0.55 + 0.45 * Math.min(1, p.leafScale);
      if (s.leafKey === 'flowers') s.leafU.value = Math.min(1, p.flowers * 1.2);
      s.crown.visible = s.leafU.value > 0.01 || !s.shrink;
    }
  };
  setSeason(palette);
  group.userData.setSeason = setSeason;
  group.userData.counts = Object.fromEntries(Object.entries(spots).map(([k, v]) => [k, v.length]));
  return group;
}
