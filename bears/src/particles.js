// GPU particle layers: spring petals, summer fireflies, autumn leaves, winter snow,
// plus chimney smoke, bees around the honey tree and mist at the foot of the waterfall.
import * as THREE from 'three';
import { rng } from './util.js';
import { BOARD, WATERFALL, LAKE, CLIFF, lakePoint } from './places.js';
import { U } from './shared.js';

const vert = /* glsl */ `
  attribute vec4 aSeed;
  uniform float uTime, uSize, uFall, uDrift, uHeight, uMode, uPix;
  varying float vSeed; varying float vAlpha; varying float vRot;
  void main(){
    vec3 p = position;
    float s = aSeed.x, s2 = aSeed.y;
    float t = uTime * (0.6 + s * 0.8);
    vAlpha = 1.0;
    if (uMode < 0.5) {               // falling: snow, petals, leaves
      p.y = position.y + uHeight - mod(uTime * uFall * (0.6 + s * 0.8) + s2 * uHeight, uHeight);
      p.x += sin(t * 0.9 + s * 30.0) * uDrift + uTime * uDrift * 0.4;
      p.z += cos(t * 0.7 + s2 * 20.0) * uDrift;
      p.x = mod(p.x + ${(BOARD / 2).toFixed(1)}, ${BOARD.toFixed(1)}) - ${(BOARD / 2).toFixed(1)};
      vAlpha = smoothstep(0.0, 3.0, p.y - position.y) * smoothstep(uHeight, uHeight - 6.0, p.y - position.y);
    } else if (uMode < 1.5) {        // hovering: fireflies, bees
      p.x += sin(t * 1.3 + s * 40.0) * uDrift;
      p.y += sin(t * 1.7 + s2 * 30.0) * uDrift * 0.4;
      p.z += cos(t * 1.1 + s2 * 50.0) * uDrift;
      vAlpha = 0.4 + 0.6 * pow(0.5 + 0.5 * sin(uTime * (2.0 + s * 3.0) + s2 * 40.0), 3.0);
    } else {                          // rising: smoke, mist
      float life = fract(uTime * uFall * (0.5 + s * 0.5) + s2);
      p += vec3(aSeed.z - 0.5, 0.0, aSeed.w - 0.5) * life * uDrift;
      p.y += life * uHeight;
      p.x += life * life * uDrift * 0.8;
      vAlpha = smoothstep(0.0, 0.15, life) * (1.0 - life);
    }
    vSeed = s; vRot = t * (s - 0.5) * 3.0;
    vec4 mv = modelViewMatrix * vec4(p, 1.0);
    float sz = uSize * (0.6 + aSeed.z * 0.8);
    if (uMode > 1.5) sz *= 1.0 + fract(uTime * uFall * (0.5 + s * 0.5) + s2) * 2.5;
    gl_PointSize = sz * uPix / -mv.z;
    gl_Position = projectionMatrix * mv;
  }`;

const frag = /* glsl */ `
  uniform float uAmount, uShape; uniform vec3 uColA, uColB;
  varying float vSeed; varying float vAlpha; varying float vRot;
  void main(){
    vec2 q = gl_PointCoord - 0.5;
    float c = cos(vRot), s = sin(vRot);
    q = mat2(c, -s, s, c) * q;
    float a;
    if (uShape < 0.5) a = smoothstep(0.5, 0.2, length(q));                       // soft disc
    else if (uShape < 1.5) a = step(length(q * vec2(1.0, 2.2)), 0.42);            // petal
    else if (uShape < 2.5) a = step(abs(q.x) * 1.6 + abs(q.y), 0.42);             // leaf
    else a = pow(smoothstep(0.5, 0.0, length(q)), 2.0);                          // glow
    vec3 col = mix(uColA, uColB, fract(vSeed * 7.31));
    if (uShape > 1.5 && uShape < 2.5) col *= 0.85 + 0.3 * step(abs(q.x), 0.03);
    float alpha = a * vAlpha * uAmount;
    if (alpha < 0.02) discard;
    gl_FragColor = vec4(col, alpha);
    #include <colorspace_fragment>
  }`;

function layer({ n, seed, spawn, size, fall = 0, drift = 0, height = 40, mode = 0, shape = 0, colA, colB, additive = false }) {
  const R = rng(seed);
  const pos = new Float32Array(n * 3), sd = new Float32Array(n * 4);
  for (let i = 0; i < n; i++) {
    const [x, y, z] = spawn(R);
    pos.set([x, y, z], i * 3);
    sd.set([R(), R(), R(), R()], i * 4);
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  geo.setAttribute('aSeed', new THREE.BufferAttribute(sd, 4));
  geo.boundingSphere = new THREE.Sphere(new THREE.Vector3(0, 20, 0), BOARD);
  const m = new THREE.ShaderMaterial({
    uniforms: {
      uTime: U.uTime, uSize: { value: size }, uFall: { value: fall }, uDrift: { value: drift }, uHeight: { value: height },
      uMode: { value: mode }, uShape: { value: shape }, uAmount: { value: 0 }, uPix: { value: 600 },
      uColA: { value: new THREE.Color(colA) }, uColB: { value: new THREE.Color(colB ?? colA) },
    },
    vertexShader: vert, fragmentShader: frag, transparent: true, depthWrite: false,
    blending: additive ? THREE.AdditiveBlending : THREE.NormalBlending,
  });
  const pts = new THREE.Points(geo, m);
  pts.frustumCulled = false;
  return pts;
}

export function buildParticles(hf, chimney) {
  const g = new THREE.Group();
  const sky = (R) => {
    const x = (R() - 0.5) * BOARD, z = (R() - 0.5) * BOARD;
    return [x, hf.h(x, z), z];
  };
  const snow = layer({ n: 9000, seed: 1, spawn: sky, size: 0.55, fall: 3.2, drift: 1.6, height: 45, shape: 0, colA: '#ffffff' });
  const petals = layer({ n: 1800, seed: 2, spawn: sky, size: 0.6, fall: 1.4, drift: 2.4, height: 30, shape: 1, colA: '#ffb3cf', colB: '#fff0f5' });
  const leaves = layer({ n: 3200, seed: 3, spawn: sky, size: 0.85, fall: 1.8, drift: 2.2, height: 26, shape: 2, colA: '#e8792a', colB: '#f2c13a' });
  const flies = layer({
    n: 900, seed: 4, size: 0.5, drift: 1.6, mode: 1, shape: 3, colA: '#d9ff7a', colB: '#fff3a0', additive: true,
    spawn: (R) => {
      const x = (R() - 0.5) * BOARD * 0.9, z = (R() - 0.5) * BOARD * 0.6 + 15;
      return [x, hf.h(x, z) + 0.8 + R() * 3.5, z];
    },
  });
  const smoke = layer({
    n: 110, seed: 5, size: 1.3, fall: 0.16, drift: 2.2, height: 10, mode: 2, shape: 0, colA: '#d7d7d7', colB: '#f2f2f2',
    spawn: () => [chimney.x, chimney.y, chimney.z],
  });
  const bees = layer({
    n: 60, seed: 6, size: 0.35, drift: 2.6, mode: 1, shape: 3, colA: '#ffcc22', colB: '#3a2a00',
    spawn: (R) => [43 + (R() - 0.5) * 7, hf.h(43, -26) + 5 + R() * 3, -26 + (R() - 0.5) * 7],
  });
  const [px, pz] = WATERFALL.pool;
  const mist = layer({
    n: 160, seed: 7, size: 1.3, fall: 0.35, drift: 2.5, height: 4, mode: 2, shape: 0, colA: '#ffffff',
    spawn: (R) => [px + (R() - 0.5) * 4, hf.bed[0] + 1, pz + (R() - 0.5) * 3 - 1.5],
  });
  const [fx, fz] = lakePoint(CLIFF.fallAngle, 0.97);
  const mist2 = layer({
    n: 160, seed: 8, size: 1.3, fall: 0.3, drift: 2.5, height: 4, mode: 2, shape: 0, colA: '#ffffff',
    spawn: (R) => [fx + (R() - 0.5) * 4, LAKE.level, fz + (R() - 0.5) * 3],
  });
  const all = [snow, petals, leaves, flies, smoke, bees, mist, mist2];
  g.add(...all);

  const setSeason = (p, night) => {
    const w = p.weights;
    snow.material.uniforms.uAmount.value = w[3];
    petals.material.uniforms.uAmount.value = w[0];
    leaves.material.uniforms.uAmount.value = w[2];
    flies.material.uniforms.uAmount.value = w[1] * (0.15 + night * 0.85);
    smoke.material.uniforms.uAmount.value = 0.35 + w[3] * 0.4 + w[2] * 0.2 + night * 0.2;
    bees.material.uniforms.uAmount.value = (w[0] + w[1] + w[2] * 0.5) * (1 - night * 0.8);
    mist.material.uniforms.uAmount.value = 0.3 * (1 - p.ice);
    mist2.material.uniforms.uAmount.value = 0.3 * (1 - p.ice);
    for (const o of all) o.visible = o.material.uniforms.uAmount.value > 0.01;
  };
  const setPixelScale = (px) => {
    for (const o of all) o.material.uniforms.uPix.value = px;
  };
  return { group: g, setSeason, setPixelScale };
}
