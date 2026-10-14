import * as THREE from 'three';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';

// Low-poly miniature figures, ~1 unit tall, facing +Z. Vertex colours carry the livery.

export const SIDE_COLORS = {
  jin: { robe: '#7f1f17', armor: '#b8432e', shield: '#d4553a', trim: '#e2b866', sail: '#c8452f' },
  qin: { robe: '#2b3d6b', armor: '#4a6ab8', shield: '#6189dc', trim: '#d5d8e2', sail: '#4467bf' },
};
const SKIN = '#c79a73';
const WOOD = '#6b4a2b';
const STEEL = '#c9c9c4';
const HORSE = '#5a3d27';
const HORSE_DARK = '#2e2219';

function paint(geo, color) {
  const c = new THREE.Color(color);
  const n = geo.attributes.position.count;
  const arr = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) {
    arr[i * 3] = c.r;
    arr[i * 3 + 1] = c.g;
    arr[i * 3 + 2] = c.b;
  }
  geo.setAttribute('color', new THREE.BufferAttribute(arr, 3));
  return geo;
}

function part(geo, color, { x = 0, y = 0, z = 0, rx = 0, ry = 0, rz = 0, sx = 1, sy = 1, sz = 1 } = {}) {
  const g = geo.index ? geo.toNonIndexed() : geo;
  g.deleteAttribute('uv');
  const m = new THREE.Matrix4().compose(
    new THREE.Vector3(x, y, z),
    new THREE.Quaternion().setFromEuler(new THREE.Euler(rx, ry, rz)),
    new THREE.Vector3(sx, sy, sz)
  );
  g.applyMatrix4(m);
  return paint(g, color);
}

export function infantryGeometry(side) {
  const c = SIDE_COLORS[side];
  const parts = [
    part(new THREE.CylinderGeometry(0.17, 0.25, 0.56, 6), c.robe, { y: 0.28 }),
    part(new THREE.CylinderGeometry(0.16, 0.19, 0.32, 6), c.armor, { y: 0.71 }),
    part(new THREE.CylinderGeometry(0.21, 0.17, 0.08, 6), c.trim, { y: 0.84 }),
    part(new THREE.IcosahedronGeometry(0.11, 0), SKIN, { y: 0.97 }),
    part(new THREE.ConeGeometry(0.13, 0.16, 6), c.armor, { y: 1.1 }),
    part(new THREE.BoxGeometry(0.3, 0.4, 0.05), c.shield, { y: 0.6, z: 0.21, x: -0.05 }),
    part(new THREE.BoxGeometry(0.03, 1.55, 0.03), WOOD, { x: 0.22, y: 0.8, z: 0.05, rx: 0.12 }),
    part(new THREE.ConeGeometry(0.04, 0.16, 4), STEEL, { x: 0.22, y: 1.63, z: 0.15, rx: 0.12 }),
  ];
  const g = mergeGeometries(parts);
  g.computeVertexNormals();
  return g;
}

export function cavalryGeometry(side) {
  const c = SIDE_COLORS[side];
  const parts = [
    // horse
    part(new THREE.BoxGeometry(0.34, 0.36, 0.95), HORSE, { y: 0.66 }),
    part(new THREE.BoxGeometry(0.22, 0.42, 0.24), HORSE, { y: 0.92, z: 0.5, rx: -0.55 }),
    part(new THREE.BoxGeometry(0.16, 0.16, 0.34), HORSE_DARK, { y: 1.08, z: 0.68, rx: 0.25 }),
    part(new THREE.BoxGeometry(0.08, 0.5, 0.08), HORSE_DARK, { x: 0.12, y: 0.25, z: 0.36 }),
    part(new THREE.BoxGeometry(0.08, 0.5, 0.08), HORSE_DARK, { x: -0.12, y: 0.25, z: 0.36 }),
    part(new THREE.BoxGeometry(0.08, 0.5, 0.08), HORSE_DARK, { x: 0.12, y: 0.25, z: -0.36 }),
    part(new THREE.BoxGeometry(0.08, 0.5, 0.08), HORSE_DARK, { x: -0.12, y: 0.25, z: -0.36 }),
    part(new THREE.BoxGeometry(0.06, 0.08, 0.36), HORSE_DARK, { y: 0.72, z: -0.62, rx: 0.6 }),
    part(new THREE.BoxGeometry(0.4, 0.06, 0.5), c.robe, { y: 0.86 }),
    // rider
    part(new THREE.CylinderGeometry(0.14, 0.18, 0.4, 6), c.armor, { y: 1.12 }),
    part(new THREE.IcosahedronGeometry(0.1, 0), SKIN, { y: 1.4 }),
    part(new THREE.ConeGeometry(0.12, 0.15, 6), c.armor, { y: 1.52 }),
    part(new THREE.BoxGeometry(0.03, 0.03, 1.15), WOOD, { x: 0.2, y: 1.2, z: 0.2, rx: -0.35 }),
    part(new THREE.ConeGeometry(0.04, 0.16, 4), STEEL, { x: 0.2, y: 1.42, z: 0.75, rx: Math.PI / 2 - 0.35 }),
  ];
  const g = mergeGeometries(parts);
  g.computeVertexNormals();
  return g;
}

export function boatGeometry(side) {
  const c = SIDE_COLORS[side];
  const hull = new THREE.BoxGeometry(0.5, 0.22, 1.6, 1, 1, 4);
  const p = hull.attributes.position;
  for (let i = 0; i < p.count; i++) {
    const z = p.getZ(i);
    const y = p.getY(i);
    const taper = 1 - Math.pow(Math.abs(z) / 0.8, 2.2) * 0.85;
    p.setX(i, p.getX(i) * taper * (y < 0 ? 0.7 : 1));
    if (Math.abs(z) > 0.6) p.setY(i, y + (Math.abs(z) - 0.6) * 0.35);
  }
  hull.computeVertexNormals();
  const parts = [
    part(hull, WOOD, { y: 0.12 }),
    part(new THREE.BoxGeometry(0.34, 0.22, 0.5), '#8c6a43', { y: 0.32, z: -0.25 }),
    part(new THREE.BoxGeometry(0.4, 0.05, 0.56), c.robe, { y: 0.45, z: -0.25 }),
    part(new THREE.CylinderGeometry(0.025, 0.03, 1.2, 5), WOOD, { y: 0.75, z: 0.15 }),
    part(new THREE.BoxGeometry(0.02, 0.6, 0.5), c.sail, { y: 0.92, z: 0.18, ry: 0.15 }),
    part(new THREE.BoxGeometry(0.62, 0.02, 0.04), WOOD, { y: 0.2, z: 0.35 }),
  ];
  const g = mergeGeometries(parts);
  g.computeVertexNormals();
  return g;
}

export function tentGeometry(side) {
  const c = SIDE_COLORS[side];
  const parts = [
    part(new THREE.ConeGeometry(0.5, 0.6, 6), '#d8ccb0', { y: 0.3 }),
    part(new THREE.CylinderGeometry(0.02, 0.02, 0.4, 4), WOOD, { y: 0.75 }),
    part(new THREE.BoxGeometry(0.02, 0.12, 0.2), c.sail, { y: 0.88, z: 0.1 }),
  ];
  const g = mergeGeometries(parts);
  g.computeVertexNormals();
  return g;
}
