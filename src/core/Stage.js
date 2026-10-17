import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { CSS2DRenderer } from 'three/examples/jsm/renderers/CSS2DRenderer.js';
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/examples/jsm/postprocessing/OutputPass.js';
import { ShaderPass } from 'three/examples/jsm/postprocessing/ShaderPass.js';

// Lighting presets: sun direction (azimuth°, elevation°), colours, intensities.
export const LIGHT_PRESETS = {
  day: {
    sunAz: 205, sunEl: 36, sun: '#fff0d8', sunI: 2.3, hemiSky: '#b9c9d6', hemiGround: '#5b4a33', hemiI: 0.85,
    bgTop: '#39424b', bgBottom: '#121418', fog: '#1d2228', sky: '#8fa5b3', exposure: 0.95, night: 0,
  },
  dusk: {
    sunAz: 248, sunEl: 17, sun: '#ffc08a', sunI: 2.5, hemiSky: '#a3a3b8', hemiGround: '#55402f', hemiI: 1.0,
    bgTop: '#3a2d2c', bgBottom: '#0e0b0c', fog: '#241c1c', sky: '#c49480', exposure: 1.05, night: 0.1,
  },
  night: {
    sunAz: 150, sunEl: 34, sun: '#a9bfff', sunI: 0.95, hemiSky: '#46588a', hemiGround: '#17171d', hemiI: 0.62,
    bgTop: '#152036', bgBottom: '#05070b', fog: '#0b0f18', sky: '#3c4f78', exposure: 1.25, night: 1,
  },
  dawn: {
    sunAz: 120, sunEl: 10, sun: '#ffc9a0', sunI: 1.8, hemiSky: '#97a4bd', hemiGround: '#4b4036', hemiI: 0.8,
    bgTop: '#33333d', bgBottom: '#0d0d10', fog: '#1f1f26', sky: '#b7a39b', exposure: 1.0, night: 0.1,
  },
};

const VignetteShader = {
  uniforms: { tDiffuse: { value: null }, uAmount: { value: 0.55 }, uGrain: { value: 0.035 }, uTime: { value: 0 }, uWarm: { value: 0.0 } },
  vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }`,
  fragmentShader: `
    uniform sampler2D tDiffuse; uniform float uAmount; uniform float uGrain; uniform float uTime; uniform float uWarm;
    varying vec2 vUv;
    float h(vec2 p){ return fract(sin(dot(p, vec2(12.9898,78.233))) * 43758.5453); }
    void main(){
      vec4 c = texture2D(tDiffuse, vUv);
      vec2 d = vUv - 0.5;
      float v = smoothstep(0.85, 0.2, length(d * vec2(1.0, 1.15)));
      c.rgb *= mix(1.0 - uAmount, 1.0, v);
      c.rgb += (h(vUv * 1000.0 + uTime) - 0.5) * uGrain;
      c.rgb = mix(c.rgb, c.rgb * vec3(1.06, 1.0, 0.9), uWarm);
      gl_FragColor = c;
    }`,
};

export class Stage {
  constructor(container) {
    this.container = container;
    const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance', alpha: false });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.0;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFShadowMap;
    renderer.domElement.className = 'gl';
    container.appendChild(renderer.domElement);
    this.renderer = renderer;

    const labels = new CSS2DRenderer();
    labels.sortObjects = false; // stacking is set per label kind in CSS (events above places)
    labels.setSize(container.clientWidth, container.clientHeight);
    labels.domElement.className = 'labels';
    container.appendChild(labels.domElement);
    this.labelRenderer = labels;

    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(34, container.clientWidth / container.clientHeight, 0.05, 2000);
    this.camera.position.set(0, 80, 90);

    this.controls = new OrbitControls(this.camera, renderer.domElement);
    // map-style: dragging moves across the table, right-drag (or Ctrl / Shift / ⌘ + drag) turns and
    // tilts, the wheel zooms toward the pointer; on touch one finger moves, two fingers zoom and turn
    this.controls.mouseButtons = { LEFT: THREE.MOUSE.PAN, MIDDLE: THREE.MOUSE.DOLLY, RIGHT: THREE.MOUSE.ROTATE };
    this.controls.touches = { ONE: THREE.TOUCH.PAN, TWO: THREE.TOUCH.DOLLY_ROTATE };
    this.controls.zoomToCursor = true;
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.08;
    this.controls.screenSpacePanning = false;
    this.controls.maxPolarAngle = Math.PI * 0.47;
    this.controls.minDistance = 2;
    this.controls.maxDistance = 260;
    this.controls.zoomSpeed = 0.9;
    this.controls.rotateSpeed = 0.55;

    // background gradient dome
    this.bgUniforms = { uTop: { value: new THREE.Color('#2a3036') }, uBottom: { value: new THREE.Color('#0d0f12') } };
    const bg = new THREE.Mesh(
      new THREE.SphereGeometry(900, 32, 16),
      new THREE.ShaderMaterial({
        side: THREE.BackSide,
        depthWrite: false,
        uniforms: this.bgUniforms,
        vertexShader: `varying vec3 vP; void main(){ vP = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
        fragmentShader: `uniform vec3 uTop; uniform vec3 uBottom; varying vec3 vP;
          void main(){ float t = smoothstep(-0.35, 0.65, vP.y); gl_FragColor = vec4(mix(uBottom, uTop, t), 1.0); }`,
      })
    );
    bg.renderOrder = -1;
    bg.frustumCulled = false;
    this.scene.add(bg);
    this.background = bg;

    this.scene.fog = new THREE.Fog('#1b1f24', 260, 900);

    this.hemi = new THREE.HemisphereLight('#c9d6df', '#6b5a40', 1.1);
    this.scene.add(this.hemi);
    this.sun = new THREE.DirectionalLight('#fff1dc', 2.6);
    this.sun.castShadow = true;
    this.sun.shadow.mapSize.set(2048, 2048);
    this.sun.shadow.bias = -0.0004;
    this.sun.shadow.normalBias = 0.02;
    this.sun.shadow.camera.near = 1;
    this.sun.shadow.camera.far = 400;
    this.scene.add(this.sun);
    this.scene.add(this.sun.target);

    // post-processing
    const composer = new EffectComposer(renderer);
    composer.addPass(new RenderPass(this.scene, this.camera));
    this.bloom = new UnrealBloomPass(new THREE.Vector2(container.clientWidth, container.clientHeight), 0.35, 0.6, 0.86);
    composer.addPass(this.bloom);
    composer.addPass(new OutputPass());
    this.vignette = new ShaderPass(VignetteShader);
    composer.addPass(this.vignette);
    this.composer = composer;

    this.preset = { ...LIGHT_PRESETS.day };
    this.presetTarget = LIGHT_PRESETS.day;
    this._tmpA = new THREE.Color();
    this._tmpB = new THREE.Color();

    this.onResize = this.onResize.bind(this);
    window.addEventListener('resize', this.onResize);
    if (window.ResizeObserver) new ResizeObserver(this.onResize).observe(container);
  }

  /** Screen space covered by side panels; the view centre shifts into the free area. */
  setInsets({ right = 0, bottom = 0 } = {}) {
    const r = Math.round(right);
    const b = Math.round(bottom);
    if (this.insets && this.insets.right === r && this.insets.bottom === b) return;
    this.insets = { right: r, bottom: b };
    this.onResize();
  }

  onResize() {
    const w = this.container.clientWidth;
    const h = this.container.clientHeight;
    if (!w || !h) return;
    const { right = 0, bottom = 0 } = this.insets || {};
    const dx = Math.round(right / 2);
    const dy = Math.round(bottom / 2);
    if (dx || dy) {
      this.camera.aspect = (w + 2 * dx) / (h + 2 * dy);
      this.camera.setViewOffset(w + 2 * dx, h + 2 * dy, 2 * dx, 2 * dy, w, h);
    } else {
      this.camera.clearViewOffset();
      this.camera.aspect = w / h;
    }
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(w, h);
    this.labelRenderer.setSize(w, h);
    this.composer.setSize(w, h);
    this.bloom.setSize(w, h);
  }

  setLight(name) {
    this.presetTarget = LIGHT_PRESETS[name] || LIGHT_PRESETS.day;
  }

  snapLight() {
    this.preset = { ...this.presetTarget };
  }

  /** Smoothly blend lighting toward the target preset. */
  updateLight(dt, sunFocus, focusRadius) {
    const k = 1 - Math.exp(-dt * 1.6);
    const p = this.preset;
    const t = this.presetTarget;
    for (const key of ['sunAz', 'sunEl', 'sunI', 'hemiI', 'exposure', 'night']) p[key] += (t[key] - p[key]) * k;
    for (const key of ['sun', 'hemiSky', 'hemiGround', 'bgTop', 'bgBottom', 'fog', 'sky']) {
      this._tmpA.set(p[key]);
      this._tmpB.set(t[key]);
      this._tmpA.lerp(this._tmpB, k);
      p[key] = '#' + this._tmpA.getHexString();
    }
    this.sun.color.set(p.sun);
    this.sun.intensity = p.sunI;
    this.hemi.color.set(p.hemiSky);
    this.hemi.groundColor.set(p.hemiGround);
    this.hemi.intensity = p.hemiI;
    this.bgUniforms.uTop.value.set(p.bgTop);
    this.bgUniforms.uBottom.value.set(p.bgBottom);
    this.scene.fog.color.set(p.fog);
    this.renderer.toneMappingExposure = p.exposure;

    // keep the shadow frustum fitted around what the camera looks at
    const az = THREE.MathUtils.degToRad(p.sunAz);
    const el = THREE.MathUtils.degToRad(p.sunEl);
    const dir = new THREE.Vector3(Math.sin(az) * Math.cos(el), Math.sin(el), -Math.cos(az) * Math.cos(el));
    const r = Math.max(4, Math.min(focusRadius, 90));
    this.sun.target.position.copy(sunFocus);
    this.sun.position.copy(sunFocus).addScaledVector(dir, 150);
    const cam = this.sun.shadow.camera;
    cam.left = -r;
    cam.right = r;
    cam.top = r;
    cam.bottom = -r;
    cam.near = 50;
    cam.far = 260;
    cam.updateProjectionMatrix();
    return p;
  }

  render(time) {
    this.vignette.uniforms.uTime.value = time % 100;
    this.composer.render();
    this.labelRenderer.render(this.scene, this.camera);
  }
}
