// Characters of Bear Ridge, modelled from primitives after the show's character sheets:
// Briar (熊大), Bramble (熊二), Logger Vick (光头强), Tiki (吉吉), Babu (毛毛), Warren (蹦蹦),
// Hoo Hoo (涂涂) and Herbert (萝卜头). Shapes are sculpted procedurally (deformed spheres with
// painted vertex colours for fur patches) — fan-made stand-ins, not the official models.
import * as THREE from 'three';
import { CSS2DObject } from 'three/examples/jsm/renderers/CSS2DRenderer.js';
import { Line2 } from './util.js';

const VC = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.82, metalness: 0 });
const GLOSS = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.3, metalness: 0 });
const tmpC = new THREE.Color();

// Deformed sphere. r: radii; taper(y) scales x/z by height (-1..1); paint(nx,ny,nz) returns a colour.
function blob({ r = [1, 1, 1], at = [0, 0, 0], rot = [0, 0, 0], color = '#ffffff', paint, taper, seg = 28, mat = VC, shadow = true }) {
  const g = new THREE.SphereGeometry(1, seg, Math.round(seg * 0.7));
  const p = g.attributes.position;
  const col = new Float32Array(p.count * 3);
  for (let i = 0; i < p.count; i++) {
    const x = p.getX(i), y = p.getY(i), z = p.getZ(i);
    const w = taper ? taper(y) : 1;
    p.setXYZ(i, x * r[0] * w, y * r[1], z * r[2] * w);
    tmpC.set(paint ? paint(x, y, z) : color);
    col.set([tmpC.r, tmpC.g, tmpC.b], i * 3);
  }
  g.setAttribute('color', new THREE.BufferAttribute(col, 3));
  g.computeVertexNormals();
  const m = new THREE.Mesh(g, mat);
  m.position.set(...at);
  m.rotation.set(...rot);
  m.castShadow = shadow;
  return m;
}
// Tapered limb hanging from a pivot along -y.
function limb({ len, r0, r1, color, paint, at = [0, 0, 0] }) {
  const piv = new THREE.Group();
  piv.position.set(...at);
  const g = new THREE.CapsuleGeometry(1, 1, 6, 12);
  const p = g.attributes.position;
  const col = new Float32Array(p.count * 3);
  for (let i = 0; i < p.count; i++) {
    const x = p.getX(i), y = p.getY(i), z = p.getZ(i);
    const t = THREE.MathUtils.clamp((y + 1.5) / 3, 0, 1); // 0 bottom .. 1 top
    const r = r1 + (r0 - r1) * t;
    p.setXYZ(i, x * r, (y / 3) * len - len / 2 - r1 * 0.2, z * r);
    tmpC.set(paint ? paint(t, x, z) : color);
    col.set([tmpC.r, tmpC.g, tmpC.b], i * 3);
  }
  g.setAttribute('color', new THREE.BufferAttribute(col, 3));
  g.computeVertexNormals();
  const m = new THREE.Mesh(g, VC);
  m.castShadow = true;
  piv.add(m);
  piv.userData.end = -len - r1 * 0.2;
  return piv;
}

function eyes(parent, { x, y, z, r, iris = '#2a1a10', irisR = 0.5, look = 0, lid = null, spread = 0.25 }) {
  for (const s of [-1, 1]) {
    const e = new THREE.Group();
    e.position.set(s * x, y, z);
    e.rotation.y = s * spread;
    e.add(blob({ r: [r, r * 1.15, r * 0.7], color: '#ffffff', mat: GLOSS, seg: 16, shadow: false }));
    e.add(blob({ r: [r * irisR, r * irisR * 1.1, r * 0.3], at: [-s * look, 0, r * 0.62], color: iris, mat: GLOSS, seg: 12, shadow: false }));
    e.add(blob({ r: [r * 0.12, r * 0.12, r * 0.08], at: [-s * look + r * 0.15, r * 0.2, r * 0.75], color: '#ffffff', mat: GLOSS, seg: 8, shadow: false }));
    if (lid) e.add(blob({ r: [r * 1.12, r * 0.6, r * 0.85], at: [0, r * 0.75, 0.02], color: lid, seg: 14 }));
    parent.add(e);
  }
}

// ---------------------------------------------------------------------------------------------
// Bears: Asian black bears drawn very stout — pear-shaped body, short legs, long arms.

function bear({ fur, furDark, bib, muzzle, nose, belly, plump = 1, scarf }) {
  const g = new THREE.Group();
  const body = new THREE.Group();
  g.add(body);
  const F = new THREE.Color(fur), D = new THREE.Color(furDark);
  const B = bib ? new THREE.Color(bib) : null, Bl = belly ? new THREE.Color(belly) : null;
  const shade = new THREE.Color();
  // torso: wide at the hips; Briar has a white V bib, Bramble a pale belly
  body.add(
    blob({
      r: [0.64 * plump, 0.82, 0.52 * plump], at: [0, 1.12, 0], seg: 36,
      taper: (y) => 1 + 0.16 * -y - 0.1 * Math.max(0, y - 0.6),
      paint: (x, y, z) => {
        if (z > 0.1) {
          if (B && y > -0.3 && y < 0.97 && Math.abs(x) < 0.1 + 0.55 * ((y + 0.3) / 1.27)) return B;
          if (Bl && y < 0.45 && Math.hypot(x * 1.15, (y + 0.1) * 0.85) < 0.62) return Bl;
        }
        return y > 0.5 ? F : shade.copy(F).lerp(D, (0.5 - y) * 0.25);
      },
    })
  );
  body.add(blob({ r: [0.12, 0.12, 0.1], at: [0, 0.75, -0.48 * plump], color: fur })); // tail
  const head = new THREE.Group();
  head.position.set(0, 2.02, 0.12);
  body.add(head);
  head.add(blob({ r: [0.4, 0.36, 0.36], color: fur, seg: 30, taper: (y) => 1 + 0.06 * y }));
  // muzzle with big nose and thick lips
  head.add(blob({ r: [0.27, 0.19, 0.22], at: [0, -0.1, 0.27], color: muzzle, seg: 24 }));
  head.add(blob({ r: [0.14, 0.095, 0.1], at: [0, 0.0, 0.47], color: nose, mat: GLOSS, seg: 18 }));
  const mouth = new THREE.Mesh(new THREE.TorusGeometry(0.11, 0.022, 6, 14, Math.PI), new THREE.MeshStandardMaterial({ color: '#3a1d17' }));
  mouth.rotation.z = Math.PI;
  mouth.position.set(0, -0.12, 0.47);
  head.add(mouth);
  eyes(head, { x: 0.13, y: 0.13, z: 0.3, r: 0.065, iris: '#1d140e', irisR: 0.55 });
  for (const s of [-1, 1]) {
    head.add(blob({ r: [0.11, 0.04, 0.05], at: [s * 0.13, 0.22, 0.31], rot: [0, 0, -s * 0.25], color: furDark, seg: 12 }));
    head.add(blob({ r: [0.12, 0.12, 0.06], at: [s * 0.29, 0.29, -0.02], rot: [0, s * 0.3, 0], color: fur, seg: 16 }));
    head.add(blob({ r: [0.07, 0.07, 0.03], at: [s * 0.29, 0.29, 0.03], rot: [0, s * 0.3, 0], color: muzzle, seg: 12 }));
  }
  const arms = [], legs = [];
  for (const s of [-1, 1]) {
    const a = limb({ len: 0.85, r0: 0.21, r1: 0.16, color: fur, at: [s * 0.62 * plump, 1.6, 0.02] });
    a.rotation.z = s * 0.28;
    a.children[0].add(blob({ r: [0.17, 0.15, 0.17], at: [0, a.userData.end, 0.02], color: furDark }));
    body.add(a);
    arms.push(a);
    const l = limb({ len: 0.32, r0: 0.25, r1: 0.22, color: fur, at: [s * 0.36 * plump, 0.55, 0] });
    l.children[0].add(blob({ r: [0.22, 0.12, 0.3], at: [0, l.userData.end + 0.02, 0.1], color: furDark }));
    g.add(l);
    legs.push(l);
  }
  const sc = new THREE.Group();
  const ring = new THREE.Mesh(new THREE.TorusGeometry(0.42 * plump, 0.12, 8, 20), new THREE.MeshStandardMaterial({ color: scarf, roughness: 0.9 }));
  ring.rotation.x = Math.PI / 2;
  ring.position.y = 1.78;
  ring.scale.set(1, 0.85, 1);
  const end = new THREE.Mesh(new THREE.BoxGeometry(0.24, 0.6, 0.07), ring.material);
  end.position.set(0.22, 1.5, 0.5 * plump);
  end.rotation.z = 0.15;
  sc.add(ring, end);
  body.add(sc);
  return { g, body, head, arms, legs, scarf: sc };
}

// ---------------------------------------------------------------------------------------------
// Logger Vick: skinny, oversized egg-shaped head, big red nose, brown fur ushanka, tan short jacket
// with cream fur trim over a dark-blue sweater, purple trousers, black shoes, chainsaw.

function logger() {
  const g = new THREE.Group();
  const body = new THREE.Group();
  g.add(body);
  const SK = '#eab68c', NAVY = '#26305f', VEST = '#b98242', FUR = '#ecdcb8', PANTS = '#4a3577', SHOE = '#1c1a1a';
  body.add(
    blob({
      r: [0.3, 0.42, 0.21], at: [0, 1.3, 0], seg: 44, taper: (y) => 1 + 0.08 * y,
      paint: (x, y, z) => (y < -0.72 ? '#6b2a24' : z > 0.45 && Math.abs(x) < 0.38 + 0.12 * y ? NAVY : z > 0.3 && Math.abs(x) < 0.5 + 0.12 * y ? FUR : y < -0.6 ? FUR : VEST),
    })
  );
  const collar = new THREE.Mesh(new THREE.TorusGeometry(0.21, 0.07, 8, 18), new THREE.MeshStandardMaterial({ color: FUR, roughness: 1 }));
  collar.rotation.x = Math.PI / 2 - 0.15;
  collar.position.set(0, 1.68, 0.01);
  body.add(collar);
  body.add(blob({ r: [0.09, 0.1, 0.09], at: [0, 1.72, 0], color: SK }));
  const head = new THREE.Group();
  head.position.set(0, 2.2, 0.02);
  head.scale.setScalar(1.3);
  body.add(head);
  head.add(blob({ r: [0.33, 0.4, 0.33], seg: 32, color: SK, taper: (y) => 1 + 0.14 * y - 0.06 * Math.max(0, -y) }));
  head.add(blob({ r: [0.12, 0.1, 0.11], at: [0, -0.04, 0.35], color: '#e2564a', mat: GLOSS, seg: 18 }));
  eyes(head, { x: 0.12, y: 0.07, z: 0.25, r: 0.085, iris: '#2b1d14', irisR: 0.38, lid: SK });
  for (const s of [-1, 1]) {
    head.add(blob({ r: [0.09, 0.025, 0.03], at: [s * 0.13, 0.19, 0.3], rot: [0, 0, -s * 0.2], color: '#3a2618', seg: 10 }));
    head.add(blob({ r: [0.05, 0.1, 0.06], at: [s * 0.33, 0.0, 0.0], color: SK, seg: 12 }));
    head.add(blob({ r: [0.07, 0.015, 0.02], at: [s * 0.07, -0.13, 0.33], rot: [0, 0, s * 0.35], color: '#3a2618', seg: 8 }));
  }
  head.add(blob({ r: [0.15, 0.06, 0.05], at: [0, -0.22, 0.28], color: '#5a1f1f', seg: 14 }));
  head.add(blob({ r: [0.13, 0.025, 0.04], at: [0, -0.19, 0.3], color: '#ffffff', seg: 10 }));
  // brown fur ushanka, flaps tied up
  const hat = new THREE.Group();
  const furHat = '#8d6648', furHatL = '#a98163';
  hat.add(blob({ r: [0.4, 0.28, 0.4], at: [0, 0.36, -0.04], color: furHat, seg: 24 }));
  hat.add(blob({ r: [0.43, 0.12, 0.42], at: [0, 0.27, -0.02], color: furHatL, seg: 22 }));
  for (const s of [-1, 1]) hat.add(blob({ r: [0.09, 0.2, 0.19], at: [s * 0.42, 0.34, -0.02], rot: [0, 0, s * 0.55], color: furHatL, seg: 14 }));
  hat.add(blob({ r: [0.28, 0.13, 0.07], at: [0, 0.44, 0.33], rot: [-0.5, 0, 0], color: furHatL, seg: 14 }));
  head.add(hat);
  const arms = [], legs = [];
  for (const s of [-1, 1]) {
    const a = limb({ len: 0.72, r0: 0.09, r1: 0.075, color: NAVY, at: [s * 0.34, 1.6, 0], paint: (t) => (t > 0.75 ? VEST : t < 0.12 ? FUR : NAVY) });
    a.rotation.z = s * 0.22;
    a.children[0].add(blob({ r: [0.08, 0.09, 0.07], at: [0, a.userData.end - 0.03, 0], color: SK }));
    body.add(a);
    arms.push(a);
    const l = limb({ len: 0.78, r0: 0.11, r1: 0.085, color: PANTS, at: [s * 0.13, 0.92, 0] });
    l.children[0].add(blob({ r: [0.1, 0.07, 0.2], at: [0, l.userData.end - 0.02, 0.07], color: SHOE }));
    g.add(l);
    legs.push(l);
  }
  const saw = new THREE.Group();
  saw.add(new THREE.Mesh(new THREE.BoxGeometry(0.2, 0.24, 0.42), new THREE.MeshStandardMaterial({ color: '#f29a1e', roughness: 0.5 })));
  const bar = new THREE.Mesh(new THREE.BoxGeometry(0.04, 0.12, 0.85), new THREE.MeshStandardMaterial({ color: '#c9d0d6', metalness: 0.7, roughness: 0.3 }));
  bar.position.z = 0.6;
  saw.add(bar);
  saw.position.set(0, arms[1].userData.end - 0.05, 0.15);
  saw.children.forEach((m) => (m.castShadow = true));
  arms[1].children[0].add(saw);
  arms[1].rotation.x = -0.6;
  const sc = new THREE.Group();
  const ring = new THREE.Mesh(new THREE.TorusGeometry(0.2, 0.08, 8, 18), new THREE.MeshStandardMaterial({ color: '#c8443a', roughness: 0.9 }));
  ring.rotation.x = Math.PI / 2;
  ring.position.y = 1.78;
  sc.add(ring);
  body.add(sc);
  return { g, body, head, arms, legs, scarf: sc };
}

// ---------------------------------------------------------------------------------------------
// Forest animals

function tiki() {
  // brown monkey, pale belly and face, pineapple crown, leaf necklace, curved staff with a pine cone
  const g = new THREE.Group();
  const FUR = '#7b4b2a', PALE = '#d9ad7c';
  const body = new THREE.Group();
  g.add(body);
  body.add(blob({ r: [0.42, 0.5, 0.38], at: [0, 0.78, 0], paint: (x, y, z) => (z > 0.2 && y < 0.5 && Math.abs(x) < 0.7 ? PALE : FUR) }));
  const head = new THREE.Group();
  head.position.set(0, 1.5, 0.05);
  body.add(head);
  head.add(blob({ r: [0.36, 0.33, 0.33], color: FUR }));
  head.add(blob({ r: [0.28, 0.24, 0.2], at: [0, -0.06, 0.2], color: PALE }));
  head.add(blob({ r: [0.2, 0.12, 0.14], at: [0, -0.15, 0.3], color: PALE }));
  head.add(blob({ r: [0.14, 0.035, 0.03], at: [0, -0.2, 0.43], color: '#ffffff' }));
  eyes(head, { x: 0.1, y: 0.04, z: 0.33, r: 0.05, iris: '#140c06', irisR: 0.6 });
  for (const s of [-1, 1]) head.add(blob({ r: [0.09, 0.1, 0.04], at: [s * 0.36, 0, 0], color: PALE }));
  const pin = new THREE.Group();
  pin.add(blob({ r: [0.16, 0.13, 0.16], paint: (x, y, z) => ((Math.round(Math.atan2(z, x) * 4) + Math.round(y * 5)) % 2 ? '#c99a3a' : '#9b6f22') }));
  const leafMat = new THREE.MeshStandardMaterial({ color: '#3d9a3a' });
  for (let i = 0; i < 6; i++) {
    const leaf = new THREE.Mesh(new THREE.ConeGeometry(0.05, 0.36, 4), leafMat);
    const a = (i / 6) * Math.PI * 2;
    leaf.position.set(Math.cos(a) * 0.04, 0.26, Math.sin(a) * 0.04);
    leaf.rotation.set(Math.sin(a) * 0.5, 0, -Math.cos(a) * 0.5);
    pin.add(leaf);
  }
  pin.position.y = 0.38;
  head.add(pin);
  for (let i = 0; i < 12; i++) {
    const a = (i / 12) * Math.PI * 2;
    body.add(blob({ r: [0.08, 0.12, 0.02], at: [Math.sin(a) * 0.3, 1.17 - Math.cos(a) * 0.04, Math.cos(a) * 0.27], rot: [0.3, a, 0], color: i % 2 ? '#5bb043' : '#3f9136', seg: 8 }));
  }
  const arms = [], legs = [];
  for (const s of [-1, 1]) {
    const a = limb({ len: 0.7, r0: 0.1, r1: 0.08, color: FUR, at: [s * 0.4, 1.12, 0] });
    a.rotation.z = s * 0.35;
    body.add(a);
    arms.push(a);
    const l = limb({ len: 0.4, r0: 0.12, r1: 0.09, color: FUR, at: [s * 0.2, 0.42, 0] });
    l.children[0].add(blob({ r: [0.1, 0.05, 0.16], at: [0, l.userData.end, 0.05], color: PALE }));
    g.add(l);
    legs.push(l);
  }
  const tail = new THREE.Mesh(new THREE.TorusGeometry(0.35, 0.05, 6, 16, Math.PI * 1.3), new THREE.MeshStandardMaterial({ color: FUR }));
  tail.position.set(0, 0.45, -0.55);
  tail.rotation.set(0, Math.PI / 2, -0.6);
  body.add(tail);
  const staff = new THREE.Group();
  const pts = [];
  for (let i = 0; i <= 10; i++) pts.push(new THREE.Vector3(0, i * 0.2, 0));
  pts.push(new THREE.Vector3(0.08, 2.15, 0), new THREE.Vector3(0.2, 2.2, 0), new THREE.Vector3(0.26, 2.1, 0));
  const stick = new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 24, 0.035, 6), new THREE.MeshStandardMaterial({ color: '#b78a55' }));
  stick.castShadow = true;
  staff.add(stick);
  staff.add(blob({ r: [0.07, 0.11, 0.07], at: [0.26, 1.95, 0], paint: (x, y) => (Math.round(y * 6) % 2 ? '#8a3b28' : '#6d2a1c') }));
  staff.position.set(0, arms[1].userData.end - 1.0, 0.05);
  arms[1].rotation.z = 0.1;
  staff.rotation.z = -0.1;
  arms[1].children[0].add(staff);
  return { g, body, head, arms, legs };
}

function babu() {
  // small golden monkey, huge pink round ears, big green eyes, ringed tail
  const g = new THREE.Group();
  const FUR = '#c69a52', PALE = '#ead2a2';
  const body = new THREE.Group();
  g.add(body);
  body.add(blob({ r: [0.22, 0.32, 0.2], at: [0, 0.65, 0], paint: (x, y, z) => (z > 0.6 && y < 0.4 ? PALE : FUR) }));
  const head = new THREE.Group();
  head.position.set(0, 1.18, 0.03);
  body.add(head);
  head.add(blob({ r: [0.3, 0.27, 0.27], color: FUR }));
  head.add(blob({ r: [0.22, 0.18, 0.15], at: [0, -0.05, 0.17], color: PALE }));
  eyes(head, { x: 0.1, y: 0.04, z: 0.26, r: 0.075, iris: '#4f9a3a', irisR: 0.55 });
  for (const s of [-1, 1]) {
    head.add(blob({ r: [0.24, 0.24, 0.05], at: [s * 0.42, 0.08, -0.04], rot: [0, -s * 0.35, 0], color: FUR }));
    head.add(blob({ r: [0.19, 0.19, 0.03], at: [s * 0.43, 0.08, 0.0], rot: [0, -s * 0.35, 0], color: '#eba79c' }));
  }
  const arms = [], legs = [];
  for (const s of [-1, 1]) {
    const a = limb({ len: 0.5, r0: 0.05, r1: 0.04, color: FUR, at: [s * 0.21, 0.88, 0] });
    a.rotation.z = s * 0.3;
    body.add(a);
    arms.push(a);
    const l = limb({ len: 0.38, r0: 0.06, r1: 0.045, color: FUR, at: [s * 0.1, 0.38, 0] });
    g.add(l);
    legs.push(l);
  }
  for (let i = 0; i < 14; i++) {
    const t = i / 13;
    body.add(blob({ r: [0.045, 0.045, 0.045], at: [0, 0.4 + Math.sin(t * 3) * 0.55, -0.22 - t * 0.45], color: i % 2 ? '#7a5426' : PALE, seg: 8 }));
  }
  return { g, body, head, arms, legs };
}

function warren() {
  // orange-brown squirrel, cream face and belly, buck teeth, huge striped brown tail
  const g = new THREE.Group();
  const OR = '#c8642c', CREAM = '#f2d892', TOP = '#9a3f1f';
  const body = new THREE.Group();
  g.add(body);
  body.add(blob({ r: [0.24, 0.36, 0.22], at: [0, 0.48, 0], paint: (x, y, z) => (z > 0.15 && Math.abs(x) < 0.75 ? CREAM : OR) }));
  const head = new THREE.Group();
  head.position.set(0, 1.0, 0.05);
  body.add(head);
  head.add(blob({ r: [0.27, 0.27, 0.27], paint: (x, y, z) => (y > 0.45 ? TOP : z > 0.1 && y < 0.35 ? CREAM : OR) }));
  head.add(blob({ r: [0.16, 0.11, 0.12], at: [0, -0.1, 0.2], color: CREAM }));
  head.add(blob({ r: [0.04, 0.03, 0.03], at: [0, -0.04, 0.32], color: '#4a2416' }));
  const toothMat = new THREE.MeshStandardMaterial({ color: '#ffffff' });
  for (const s of [-1, 1]) {
    const tooth = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.09, 0.02), toothMat);
    tooth.position.set(s * 0.033, -0.2, 0.29);
    head.add(tooth);
  }
  eyes(head, { x: 0.1, y: 0.07, z: 0.21, r: 0.085, iris: '#7a8a2a', irisR: 0.45 });
  for (const s of [-1, 1]) head.add(blob({ r: [0.06, 0.11, 0.04], at: [s * 0.18, 0.27, -0.02], rot: [0, 0, -s * 0.35], color: '#7a3a1c' }));
  const arms = [], legs = [];
  for (const s of [-1, 1]) {
    const a = limb({ len: 0.3, r0: 0.045, r1: 0.035, color: OR, at: [s * 0.2, 0.68, 0.06] });
    a.rotation.z = s * 0.4;
    body.add(a);
    arms.push(a);
    const l = limb({ len: 0.22, r0: 0.07, r1: 0.05, color: OR, at: [s * 0.1, 0.22, 0] });
    g.add(l);
    legs.push(l);
  }
  const tail = new THREE.Group();
  for (let i = 0; i < 9; i++) {
    const t = i / 8;
    tail.add(blob({ r: [0.2 + t * 0.06, 0.2 + t * 0.06, 0.18], at: [0, 0.25 + Math.sin(t * 2.7) * 0.85, -0.3 - Math.sin(t * 1.5) * 0.4 + t * t * 0.35], color: i % 3 === 1 ? '#ead39a' : '#6c4630', seg: 14 }));
  }
  body.add(tail);
  return { g, body, head, arms, legs, tail };
}

function hoohoo() {
  // round owl: cream body and face, rust-red head and wings, green eyes, yellow beak and feet, blue-grey beret
  const g = new THREE.Group();
  const CREAM = '#f3ead6', RUST = '#b4513a';
  const body = new THREE.Group();
  g.add(body);
  body.add(blob({ r: [0.36, 0.42, 0.34], at: [0, 0.5, 0], paint: (x, y, z) => (z > -0.1 ? CREAM : '#d9b89a') }));
  const head = new THREE.Group();
  head.position.set(0, 1.02, 0.02);
  body.add(head);
  head.add(blob({ r: [0.34, 0.3, 0.32], paint: (x, y, z) => (z > 0.25 && y < 0.55 ? CREAM : RUST) }));
  eyes(head, { x: 0.12, y: 0.03, z: 0.24, r: 0.1, iris: '#4f9a3a', irisR: 0.5, spread: 0.3 });
  head.add(blob({ r: [0.05, 0.07, 0.05], at: [0, -0.1, 0.33], color: '#f1b62e' }));
  head.add(blob({ r: [0.3, 0.09, 0.3], at: [-0.06, 0.29, -0.02], rot: [0, 0, 0.25], color: '#5f7795' }));
  const wings = [];
  for (const s of [-1, 1]) {
    const piv = new THREE.Group();
    piv.position.set(s * 0.3, 0.68, 0);
    piv.add(blob({ r: [0.42, 0.08, 0.24], at: [s * 0.36, -0.05, 0], color: RUST }));
    body.add(piv);
    wings.push(piv);
    g.add(blob({ r: [0.07, 0.04, 0.1], at: [s * 0.12, 0.08, 0.06], color: '#f1b62e' }));
  }
  return { g, body, head, wings };
}

function herbert() {
  // gopher: brown, cream face and belly band, buck teeth, whiskers
  const g = new THREE.Group();
  const BR = '#94653a', CREAM = '#efdcb4';
  const body = new THREE.Group();
  g.add(body);
  body.add(blob({ r: [0.34, 0.5, 0.3], at: [0, 0.5, 0], paint: (x, y, z) => (z > 0.2 && Math.abs(x) < 0.7 ? CREAM : BR) }));
  const head = new THREE.Group();
  head.position.set(0, 1.08, 0.05);
  body.add(head);
  head.add(blob({ r: [0.3, 0.26, 0.28], paint: (x, y, z) => (z > 0.3 && y < 0.3 ? CREAM : BR) }));
  head.add(blob({ r: [0.05, 0.04, 0.04], at: [0, -0.02, 0.3], color: '#4a2a18' }));
  const tooth = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.1, 0.02), new THREE.MeshStandardMaterial({ color: '#ffffff' }));
  tooth.position.set(0, -0.15, 0.27);
  head.add(tooth);
  eyes(head, { x: 0.1, y: 0.08, z: 0.22, r: 0.06, iris: '#b5781e', irisR: 0.5 });
  const whiskerMat = new THREE.MeshBasicMaterial({ color: '#2a1a10' });
  for (const s of [-1, 1]) {
    head.add(blob({ r: [0.06, 0.06, 0.03], at: [s * 0.22, 0.2, -0.02], color: '#d6b46a' }));
    for (const dy of [-0.02, 0.02]) {
      const w = new THREE.Mesh(new THREE.CylinderGeometry(0.004, 0.004, 0.32, 3), whiskerMat);
      w.rotation.z = Math.PI / 2 + s * dy * 6;
      w.position.set(s * 0.2, -0.04 + dy, 0.27);
      head.add(w);
    }
  }
  const arms = [];
  for (const s of [-1, 1]) {
    const a = limb({ len: 0.32, r0: 0.07, r1: 0.06, color: BR, at: [s * 0.3, 0.75, 0.05] });
    a.rotation.z = s * 0.5;
    body.add(a);
    arms.push(a);
  }
  return { g, body, head, arms };
}

// ---------------------------------------------------------------------------------------------
// Where everyone lives (see buildings.js for the homes).
export const HOMES = {
  cave: { x: -74, z: -8 }, // Tiki and Babu's cave, mouth facing east
  owl: { x: -6, z: 24 }, // Hoo Hoo's tree house
  squirrel: { x: -25, z: -11 }, // Warren's pine-cone tree hollow
  burrow: { x: 24, z: 21 }, // Herbert's burrow and radish patch
};
const MEADOW = { x: 12, z: 30 };

export const CHARACTERS = [
  {
    id: 'briar', name: '熊大', desc: '哥哥，红棕色毛，胸前一大片白色 V 字毛，红鼻子厚嘴唇，聪明勇敢，带头保护森林。常在树洞家、木桥和吉吉的山洞之间巡山。',
    make: () => bear({ fur: '#9b4f2e', furDark: '#7c3a20', bib: '#f4ece0', muzzle: '#f1e2cf', nose: '#d4424a', scarf: '#d83a33' }),
    route: [[28, -4], [20, -3], [8, 1], [-4, 2], [-12, 2], [-24, -5], [-40, -10], [-56, -10], [-68, -8]], speed: 2.4, scale: 1.2, tagY: 2.75,
  },
  {
    id: 'bramble', name: '熊二', desc: '弟弟，金黄色毛，灰蓝色大鼻子，比哥哥更胖更壮，憨厚贪吃，最爱蜂蜜和鱼。总在树洞家和蜂蜜树之间来回。',
    make: () => bear({ fur: '#d6a356', furDark: '#b9853c', belly: '#ecca8c', muzzle: '#f2ddb0', nose: '#5e6683', plump: 1.15, scarf: '#f2c230' }),
    route: [[27, -2], [31, -8], [34, -12], [38, -18], [41, -22]], speed: 1.5, scale: 1.25, tagY: 2.75,
  },
  {
    id: 'vick', name: '光头强', desc: '秃顶的伐木工，大脑袋、红鼻子，戴棕色毛皮护耳帽遮秃，深蓝毛衣外套黄棕色毛边短夹克，紫色裤子，拿电锯，开一辆蓝色皮卡，受李老板雇佣砍树。',
    make: logger,
    route: [[52, 43.5], [49.5, 45.5], [47.5, 39], [52, 47], [60, 45], [65, 38], [70, 33]], speed: 2.0, scale: 1.2, tagY: 2.75,
  },
];

export const CRITTERS = [
  {
    id: 'jiji', name: '吉吉国王', desc: '自封为王的棕色猴子，头顶菠萝当王冠，脖子挂树叶项链，手拿挂着松果的弯木杖。和毛毛住在熊大熊二帮他们建的山洞里。',
    make: tiki, scale: 1.3, tagY: 2.3,
    tick(c, dt, t, hf) {
      const x = HOMES.cave.x + 3.6, z = HOMES.cave.z - 1.2;
      c.holder.position.set(x, hf.h(x, z) + 0.6, z);
      c.holder.rotation.y = Math.PI / 2 + Math.sin(t * 0.4) * 0.3;
      c.rig.head.rotation.y = Math.sin(t * 0.7) * 0.4;
      c.rig.arms[0].rotation.z = -0.8 - Math.sin(t * 2.5) * 0.3;
    },
  },
  {
    id: 'maomao', name: '毛毛', desc: '吉吉国王的跟班，金色小猴子，一对粉色大圆耳朵，绿色大眼睛，尾巴一圈圈的。',
    make: babu, scale: 1.3, tagY: 2.0,
    tick(c, dt, t, hf) {
      const a = t * 0.9;
      const x = HOMES.cave.x + 4.2 + Math.cos(a) * 1.4, z = HOMES.cave.z + 1.6 + Math.sin(a) * 1.4;
      c.holder.position.set(x, hf.h(x, z) + Math.abs(Math.sin(t * 6)) * 0.35, z);
      c.holder.rotation.y = -a;
      c.rig.legs[0].rotation.x = Math.sin(t * 12) * 0.6;
      c.rig.legs[1].rotation.x = -Math.sin(t * 12) * 0.6;
    },
  },
  {
    id: 'bangbang', name: '蹦蹦', desc: '松鼠，橙黄色毛，两颗大门牙，巨大的棕色条纹尾巴，爱松果，胆小机灵，常帮熊兄弟打探消息。住在堆满松果的树洞里。',
    make: warren, scale: 1.4, tagY: 1.6,
    tick(c, dt, t, hf) {
      const a = Math.sin(t * 0.5) * 1.2;
      const x = HOMES.squirrel.x + Math.sin(a) * 3, z = HOMES.squirrel.z + 2.6 + Math.cos(a) * 1.5;
      c.holder.position.set(x, hf.h(x, z) + Math.abs(Math.sin(t * 5)) * 0.5, z);
      c.holder.rotation.y = Math.cos(t * 0.5) > 0 ? Math.PI / 2 : -Math.PI / 2;
      c.rig.tail.rotation.x = Math.sin(t * 5) * 0.12;
    },
  },
  {
    id: 'tutu', name: '涂涂', desc: '猫头鹰，红白相间的羽毛，绿眼睛黄嘴，戴一顶灰蓝色贝雷帽，健忘爱打瞌睡，飞着飞着都能睡着。住在树屋里，常在草甸上空盘旋。',
    make: hoohoo, scale: 1.4, tagY: 1.8,
    tick(c, dt, t, hf) {
      const a = t * 0.22;
      const x = MEADOW.x - 6 + Math.cos(a) * 18, z = MEADOW.z - 2 + Math.sin(a) * 12;
      c.holder.position.set(x, hf.h(MEADOW.x, MEADOW.z) + 12 + Math.sin(t * 0.9) * 1.5, z);
      c.holder.rotation.y = Math.atan2(-Math.sin(a) * 18, Math.cos(a) * 12);
      c.holder.rotation.z = 0.25;
      const f = Math.sin(t * 7) * 0.7;
      c.rig.wings[0].rotation.z = f;
      c.rig.wings[1].rotation.z = -f;
    },
  },
  {
    id: 'luobotou', name: '萝卜头', desc: '地鼠，棕色毛、白肚皮、大门牙，脾气急，打洞飞快，爱囤萝卜。洞口就在花海草甸东边的萝卜地旁。',
    make: herbert, scale: 1.4, tagY: 1.7,
    tick(c, dt, t, hf) {
      const cyc = (t * 0.25) % 1;
      const up = Math.min(1, Math.max(0, Math.min(cyc * 6, (0.75 - cyc) * 6)));
      c.holder.position.set(HOMES.burrow.x, hf.h(HOMES.burrow.x, HOMES.burrow.z) - 1.6 + up * 1.5, HOMES.burrow.z);
      c.holder.rotation.y = Math.sin(t * 0.5) * 0.8;
      c.tag.visible = up > 0.5;
    },
  },
];
export const ALL_CHARACTERS = [...CHARACTERS, ...CRITTERS];

export function buildCharacters(hf) {
  const group = new THREE.Group();
  const make = (c) => {
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
    return { rig, holder, tag, div };
  };
  const list = CHARACTERS.map((c, i) => ({ ...c, ...make(c), line: new Line2(c.route, 80), s: (i * 0.37) % 1, dir: 1, pause: 0, phase: 0 }));
  for (const c of CRITTERS) list.push({ ...c, ...make(c), critter: true });

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
      c.rig.body.position.y = walking ? Math.abs(Math.cos(c.phase)) * 0.1 : Math.sin(t * 2) * 0.03;
      c.rig.body.rotation.z = walking ? Math.sin(c.phase) * 0.05 : 0;
      c.rig.head.rotation.y = walking ? 0 : Math.sin(t * 0.8 + c.s * 9) * 0.5;
      const w = season.weights[3] + season.weights[2] * 0.15;
      c.rig.scarf.visible = w > 0.05;
      c.rig.scarf.scale.setScalar(Math.max(0.01, Math.min(1, w)));
    }
  };
  return { group, list, update };
}
