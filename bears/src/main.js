import './style.css';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { CSS2DRenderer } from 'three/examples/jsm/renderers/CSS2DRenderer.js';
import { SEASONS, blendSeason } from './seasons.js';
import { U } from './shared.js';
import { HeightField, buildTerrain, buildBoard, buildWater } from './terrain.js';
import { buildFlora } from './flora.js';
import { buildLandmarks } from './buildings.js';
import { buildCharacters } from './characters.js';
import { buildParticles } from './particles.js';
import { UI } from './ui.js';
import { PLACES } from './places.js';

const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);

const skyVert = `varying vec3 vP; void main(){ vP = position; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }`;
const skyFrag = `
  uniform vec3 uTop, uBottom; uniform float uNight; varying vec3 vP;
  float hh(vec3 p){ return fract(sin(dot(p, vec3(12.9898,78.233,37.719))) * 43758.5453); }
  void main(){
    vec3 d = normalize(vP);
    vec3 c = mix(uBottom, uTop, smoothstep(-0.05, 0.55, d.y));
    vec3 night = mix(vec3(0.05,0.08,0.16), vec3(0.01,0.02,0.06), smoothstep(0.0, 0.6, d.y));
    c = mix(c, night, uNight);
    vec3 cell = floor(d * 260.0);
    float star = step(0.9975, hh(cell)) * smoothstep(0.05, 0.3, d.y) * uNight;
    c += star * 0.9;
    gl_FragColor = vec4(c, 1.0);
    #include <colorspace_fragment>
  }`;

class App {
  constructor(el) {
    this.el = el;
    this.season = 0; // continuous
    this.target = 0;
    this.auto = true;
    this.autoTimer = 0;
    this.AUTO_PERIOD = 16;
    this.night = 0;
    this.nightTarget = 0;
    this.palette = blendSeason(0);
    this.ready = false;
  }

  init() {
    const el = this.el;
    const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
    const small = Math.min(window.innerWidth, window.innerHeight) < 700;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, small ? 1.5 : 2));
    renderer.setSize(el.clientWidth, el.clientHeight);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.05;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.domElement.className = 'gl';
    el.appendChild(renderer.domElement);
    this.renderer = renderer;

    const labels = new CSS2DRenderer();
    labels.setSize(el.clientWidth, el.clientHeight);
    labels.domElement.className = 'labels';
    el.appendChild(labels.domElement);
    this.labels = labels;

    const scene = new THREE.Scene();
    this.scene = scene;
    scene.fog = new THREE.Fog('#d9eef7', 320, 900);
    const camera = new THREE.PerspectiveCamera(36, el.clientWidth / el.clientHeight, 0.5, 3000);
    this.camera = camera;
    this.home = { pos: new THREE.Vector3(85, 175, 250), target: new THREE.Vector3(2, 0, 12) };
    camera.position.copy(this.home.pos);
    const controls = new OrbitControls(camera, labels.domElement);
    controls.target.copy(this.home.target);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.maxPolarAngle = Math.PI * 0.46;
    controls.minDistance = 8;
    controls.maxDistance = 520;
    controls.addEventListener('start', () => {
      this.fly = null;
      this.follow = null;
      this.ui?.setFollow(null);
    });
    this.controls = controls;

    // sky dome
    this.skyU = { uTop: { value: new THREE.Color() }, uBottom: { value: new THREE.Color() }, uNight: U.uNight };
    const sky = new THREE.Mesh(
      new THREE.SphereGeometry(1500, 32, 16),
      new THREE.ShaderMaterial({ uniforms: this.skyU, vertexShader: skyVert, fragmentShader: skyFrag, side: THREE.BackSide, depthWrite: false, fog: false })
    );
    scene.add(sky);

    // lights
    this.hemi = new THREE.HemisphereLight('#cfe8ff', '#6b5a3c', 1);
    scene.add(this.hemi);
    const sun = new THREE.DirectionalLight('#fff4e0', 2.6);
    sun.position.set(-90, 150, 70);
    sun.castShadow = true;
    sun.shadow.mapSize.set(small ? 2048 : 4096, small ? 2048 : 4096);
    const sc = sun.shadow.camera;
    sc.left = sc.bottom = -125;
    sc.right = sc.top = 125;
    sc.near = 20;
    sc.far = 420;
    sun.shadow.bias = -0.0006;
    sun.shadow.normalBias = 0.6;
    scene.add(sun, sun.target);
    this.sun = sun;
    const moon = new THREE.Mesh(new THREE.SphereGeometry(14, 24, 16), new THREE.MeshBasicMaterial({ color: '#fff8dd', fog: false, transparent: true }));
    moon.position.set(260, 330, -700);
    scene.add(moon);
    this.moon = moon;

    // world
    const hf = new HeightField();
    this.hf = hf;
    this.terrain = buildTerrain(hf, this.palette);
    this.board = buildBoard(hf);
    this.water = buildWater(hf);
    this.flora = buildFlora(hf, this.palette);
    this.marks = buildLandmarks(hf);
    this.chars = buildCharacters(hf);
    this.parts = buildParticles(hf, this.marks.chimney);
    const lantern = new THREE.PointLight('#ffb35a', 0, 26, 1.6);
    lantern.position.set(54, hf.h(55, 42) + 3, 43);
    this.lantern = lantern;
    scene.add(this.terrain, this.board, this.water, this.flora, this.marks.root, this.chars.group, this.parts.group, lantern);

    this.ui = new UI(this);
    this.applySeason(true);
    this.applyNight();
    this.clock = new THREE.Clock();
    window.addEventListener('resize', () => this.resize());
    this.resize();
    renderer.setAnimationLoop(() => this.frame());
    this.ready = true;
  }

  resize() {
    const w = this.el.clientWidth, h = this.el.clientHeight;
    this.renderer.setSize(w, h);
    this.labels.setSize(w, h);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    // keep the whole board in view on narrow screens
    this.fit = Math.max(1, 1.4 / Math.max(0.4, w / h));
    this.controls.maxDistance = 520 * this.fit;
    this.scene.fog.near = 320 * this.fit;
    this.scene.fog.far = 900 * this.fit;
    const homeDir = new THREE.Vector3(85, 175, 250);
    this.home.pos.copy(homeDir.multiplyScalar(this.fit));
    if (!this.started) {
      this.camera.position.copy(this.home.pos);
      this.started = true;
    }
    const pr = this.renderer.getPixelRatio();
    this.parts.setPixelScale((h * pr * 0.5) / Math.tan(THREE.MathUtils.degToRad(this.camera.fov / 2)));
  }

  // --- season control -------------------------------------------------------------------
  setSeason(i, { snap = false, user = true } = {}) {
    const n = SEASONS.length;
    const cur = Math.round(this.target);
    let d = (((i - cur) % n) + n) % n;
    this.target = cur + d; // always move forward through the year
    if (user) this.autoTimer = 0;
    if (snap) {
      this.season = this.target;
      this.applySeason();
    }
    this.ui?.sync();
  }
  nextSeason() {
    this.setSeason((Math.round(this.target) + 1) % SEASONS.length, { user: false });
  }
  setAuto(on) {
    this.auto = on;
    this.autoTimer = 0;
    this.ui.sync();
  }
  setNight(on, snap = false) {
    this.nightTarget = on ? 1 : 0;
    if (snap) {
      this.night = this.nightTarget;
      this.applyNight();
    }
    this.ui.sync();
  }
  get seasonIndex() {
    return ((Math.round(this.target) % 4) + 4) % 4;
  }

  applySeason() {
    const p = blendSeason(this.season, this.palette);
    U.uSnow.value = p.snow;
    this.terrain.userData.setSeason(p);
    this.water.userData.setSeason(p);
    this.flora.userData.setSeason(p);
    this.marks.setSeason(p);
    this.applyNight();
  }

  applyNight() {
    const p = this.palette, n = this.night;
    U.uNight.value = n;
    this.skyU.uTop.value.copy(p.skyTop);
    this.skyU.uBottom.value.copy(p.skyBottom);
    const fog = p.fog.clone().lerp(new THREE.Color('#0b1424'), n);
    this.scene.fog.color.copy(fog);
    this.sun.color.copy(p.sun).lerp(new THREE.Color('#9fb6ff'), n);
    this.sun.intensity = THREE.MathUtils.lerp(p.sunI, 0.55, n);
    const az = THREE.MathUtils.lerp(-0.9, 0.6, n);
    this.sun.position.set(Math.sin(az) * 110, THREE.MathUtils.lerp(150, 170, n), Math.cos(az) * 110);
    this.hemi.intensity = THREE.MathUtils.lerp(p.hemiI, 0.35, n);
    this.hemi.color.set('#cfe8ff').lerp(new THREE.Color('#5068a8'), n);
    this.hemi.groundColor.set(p.weights[3] > 0.5 ? '#9aa3ad' : '#6b5a3c').lerp(new THREE.Color('#1b2030'), n);
    this.renderer.toneMappingExposure = THREE.MathUtils.lerp(1.05, 1.3, n);
    this.moon.material.opacity = n;
    this.el.classList.toggle('night', n > 0.5);
    this.moon.visible = n > 0.02;
    this.marks.setNight(n);
    this.lantern.intensity = n * 60;
    this.parts.setSeason(p, n);
  }

  // --- camera -------------------------------------------------------------------------------
  flyTo(target, dist = 40, { pitch = 0.75, yaw = null } = {}) {
    dist *= Math.min(1.8, this.fit || 1);
    const c = this.camera.position, t0 = this.controls.target.clone();
    const dir = c.clone().sub(t0);
    const cy = yaw ?? Math.atan2(dir.x, dir.z);
    const pos = new THREE.Vector3(Math.sin(cy) * Math.cos(pitch), Math.sin(pitch), Math.cos(cy) * Math.cos(pitch)).multiplyScalar(dist).add(target);
    this.fly = { t: 0, from: { p: c.clone(), t: t0 }, to: { p: pos, t: target.clone() } };
  }
  focusPlace(id) {
    const pl = PLACES.find((p) => p.id === id);
    if (!pl) return;
    const y = this.hf.h(pl.x, pl.z) + (pl.y || 0) * 0.4;
    const inside = pl.kind === 'interior';
    const dist = inside ? 15 : pl.kind === 'mountain' ? 90 : pl.kind === 'forest' || pl.kind === 'water' ? 60 : 38;
    this.follow = null;
    this.marks.setCutaway(inside);
    this.flyTo(new THREE.Vector3(pl.x, y + (inside ? 1.5 : 0), pl.z), dist, { pitch: inside ? 0.95 : pl.kind === 'mountain' ? 0.5 : 0.62, yaw: inside ? 0.25 : null });
  }
  followChar(id) {
    const c = this.chars.list.find((c) => c.id === id);
    if (!c) return;
    this.marks.setCutaway(false);
    this.follow = c;
    this.flyTo(c.holder.position.clone().add(new THREE.Vector3(0, 2, 0)), 22, { pitch: 0.45 });
    this.ui.setFollow(c);
  }
  resetView() {
    this.marks.setCutaway(false);
    this.follow = null;
    this.ui.setFollow(null);
    this.fly = { t: 0, from: { p: this.camera.position.clone(), t: this.controls.target.clone() }, to: { p: this.home.pos.clone(), t: this.home.target.clone() } };
  }

  frame() {
    const dt = Math.min(0.05, this.clock.getDelta());
    U.uTime.value += dt;
    const t = U.uTime.value;

    if (this.auto && !this.ui.hidden) {
      this.autoTimer += dt;
      if (this.autoTimer > this.AUTO_PERIOD) {
        this.autoTimer = 0;
        this.nextSeason();
      }
    }
    let changed = false;
    if (Math.abs(this.target - this.season) > 1e-4) {
      const k = Math.min(1, dt * 1.1);
      const d = this.target - this.season;
      this.season += Math.sign(d) * Math.min(Math.abs(d), Math.max(Math.abs(d) * k, dt * 0.15));
      changed = true;
    }
    if (Math.abs(this.nightTarget - this.night) > 1e-4) {
      this.night += Math.sign(this.nightTarget - this.night) * Math.min(Math.abs(this.nightTarget - this.night), dt * 0.7);
      this.applyNight();
    }
    if (changed) {
      this.applySeason();
      this.ui.onSeasonProgress();
    }

    for (const a of this.marks.animated) a(t);
    this.chars.update(dt, t, this.palette);

    if (this.fly) {
      this.fly.t = Math.min(1, this.fly.t + dt / 1.6);
      const e = ease(this.fly.t);
      const to = this.follow ? this.follow.holder.position.clone().add(new THREE.Vector3(0, 2, 0)) : this.fly.to.t;
      this.camera.position.lerpVectors(this.fly.from.p, this.fly.to.p.clone().add(to).sub(this.fly.to.t), e);
      this.controls.target.lerpVectors(this.fly.from.t, to, e);
      if (this.fly.t >= 1) this.fly = null;
    } else if (this.follow) {
      const want = this.follow.holder.position.clone().add(new THREE.Vector3(0, 2, 0));
      const delta = want.sub(this.controls.target);
      this.controls.target.add(delta);
      this.camera.position.add(delta);
    }
    this.controls.update();
    this.ui.frame(dt);
    this.renderer.render(this.scene, this.camera);
    this.labels.render(this.scene, this.camera);
  }
}

const app = new App(document.getElementById('app'));
window.__bears = app;
requestAnimationFrame(() =>
  requestAnimationFrame(() => {
    try {
      app.init();
      document.getElementById('loader')?.classList.add('done');
    } catch (err) {
      console.error(err);
      const l = document.getElementById('loader');
      if (l) l.textContent = '加载失败：' + (err?.message || err) + '。需要支持 WebGL 2 的浏览器。';
    }
  })
);
