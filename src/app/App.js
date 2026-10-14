import * as THREE from 'three';
import { Stage } from '../core/Stage.js';
import { CameraRig } from '../core/CameraRig.js';
import { Table } from './Table.js';
import { makeResolver } from './geo.js';
import { EPISODES } from '../data/episodes.js';
import { TACTICAL_PLACES, STRATEGIC_PLACES } from '../data/places.js';
import { TACTICAL_UNITS, STRATEGIC_UNITS } from '../data/units.js';
import { TACTICAL_ROUTES, STRATEGIC_ROUTES } from '../data/routes.js';
import { TACTICAL_EVENTS, STRATEGIC_EVENTS } from '../data/events.js';
import { UnitsLayer } from '../army/Units.js';
import { ArrowsLayer } from '../army/Arrows.js';
import { LabelsLayer } from '../world/Labels.js';
import { MarkersLayer } from '../world/Markers.js';
import { Declutter } from '../world/Declutter.js';
import { PropsLayer } from '../world/Props.js';
import { EffectsLayer } from '../fx/Effects.js';
import { TACTICAL_FX, STRATEGIC_FX, TACTICAL_PROPS, SOUNDSCAPE } from '../data/effects.js';
import { Sound } from '../audio/Sound.js';
import { shouyangHolder } from '../data/events.js';
import { territoryTexture, FRONTIER_383, FRONTIER_385 } from '../world/Territory.js';
import { T as TT } from '../data/episodes.js';
import { UI } from '../ui/UI.js';
import { DISPLAY_FONT } from '../army/flags.js';

import tacticalMeta from '../data/geo/tactical.json';
import strategicMeta from '../data/geo/strategic.json';
import tacticalHeightUrl from '../assets/terrain/tactical-height.webp?url';
import tacticalWaterUrl from '../assets/terrain/tactical-water.webp?url';
import strategicHeightUrl from '../assets/terrain/strategic-height.webp?url';
import strategicWaterUrl from '../assets/terrain/strategic-water.webp?url';

const N = EPISODES.length;
const nextFrame = () => new Promise((r) => requestAnimationFrame(() => r()));

export class App {
  constructor(root) {
    this.root = root;
    this.T = 0;
    this.playing = false;
    this.speed = 1;
    this.activeMap = null;
    this.lastFrame = performance.now();
    this.elapsed = 0;
    this.ready = false;
    this.declutter = new Declutter();
    this.sound = new Sound();
    this.layerState = { places: true, modern: true, arrows: true, markers: true, unitLabels: true, contours: true, grid: false };
  }

  showFatal(err) {
    const el = document.createElement('div');
    el.className = 'fatal';
    el.textContent = `无法启动三维场景：${err?.message || err}。请使用支持 WebGL 2 的浏览器打开。`;
    this.root.appendChild(el);
    this.root.querySelector('.loader')?.classList.add('is-done');
  }

  setStatus(text, frac) {
    if (!this.loader) return;
    this.loader.querySelector('.loader__status').textContent = text;
    this.loader.querySelector('.loader__bar i').style.width = `${Math.round(frac * 100)}%`;
  }

  async start(resume = {}) {
    this.root.innerHTML = `
      <div class="viewport" id="viewport"></div>
      <div class="loader" id="loader">
        <h1 class="loader__title">淝水之战</h1>
        <p class="loader__sub">三维战场态势沙盘</p>
        <div class="loader__bar"><i></i></div>
        <div class="loader__status">展开沙盘</div>
      </div>`;
    this.loader = this.root.querySelector('#loader');
    this.viewport = this.root.querySelector('#viewport');
    await nextFrame();

    this.stage = new Stage(this.viewport);
    this.rig = new CameraRig(this.stage);
    this.setStatus('载入地形高程', 0.12);

    this.tables = {
      strategic: new Table('strategic', strategicMeta, { height: strategicHeightUrl, water: strategicWaterUrl }, { exaggeration: 10, meshStep: 2, slabDepth: 3.2 }),
      tactical: new Table('tactical', tacticalMeta, { height: tacticalHeightUrl, water: tacticalWaterUrl }, { exaggeration: 5, meshStep: 2, slabDepth: 2.6 }),
    };
    const fontReady = Promise.race([
      document.fonts?.load(`64px ${DISPLAY_FONT}`, '淝水之战秦晋谢苻').catch(() => null),
      new Promise((r) => setTimeout(r, 2500)),
    ]);
    await this.tables.strategic.load();
    this.setStatus('烘焙山川光影', 0.42);
    await nextFrame();
    await this.tables.tactical.load();
    this.setStatus('布置两军阵势', 0.7);
    await fontReady;
    await nextFrame();

    for (const t of Object.values(this.tables)) this.stage.scene.add(t.group);
    this.ui = new UI(this, this.root);
    const S = this.tables.strategic;
    const Tt = this.tables.tactical;
    S.resolver = makeResolver(S, STRATEGIC_PLACES);
    Tt.resolver = makeResolver(Tt, TACTICAL_PLACES);
    const hover = (p, el) => this.ui.showTooltip(p, el);

    Tt.add('props', new PropsLayer(Tt.resolver, TACTICAL_PLACES, { scale: 'tactical', holder: shouyangHolder, schedule: TACTICAL_PROPS }));
    S.add('props', new PropsLayer(S.resolver, STRATEGIC_PLACES, { scale: 'strategic' }));
    Tt.add('units', new UnitsLayer(Tt.resolver, TACTICAL_UNITS, { figScale: 0.068, spacing: 0.092, bannerScale: 0.62, boatScale: 2.4 }));
    S.add('units', new UnitsLayer(S.resolver, STRATEGIC_UNITS, { figScale: 0.46, spacing: 0.62, bannerScale: 3.4, boatScale: 2.0, shadows: false }));
    Tt.add('arrows', new ArrowsLayer(Tt.resolver, TACTICAL_ROUTES, Tt.layers.units, { width: 0.24, offset: 0.025, step: 0.05, nearFade: [3.5, 11] }));
    S.add('arrows', new ArrowsLayer(S.resolver, STRATEGIC_ROUTES, S.layers.units, { width: 1.0, offset: 0.12, step: 0.3, nearFade: [14, 45] }));
    Tt.add('labels', new LabelsLayer(Tt.resolver, TACTICAL_PLACES, { rivers: Tt.meta.rivers, scale: 'tactical', onHover: hover }));
    S.add('labels', new LabelsLayer(S.resolver, STRATEGIC_PLACES, { rivers: S.meta.rivers, scale: 'strategic', onHover: hover }));
    Tt.add('markers', new MarkersLayer(Tt.resolver, TACTICAL_EVENTS, Tt.layers.units, { ringScale: 1 }));
    S.add('markers', new MarkersLayer(S.resolver, STRATEGIC_EVENTS, S.layers.units, { ringScale: 5 }));
    Tt.add('fx', new EffectsLayer(Tt.resolver, TACTICAL_FX, { units: Tt.layers.units, props: Tt.layers.props, terrain: Tt.terrain, scale: 1 }));
    S.add('fx', new EffectsLayer(S.resolver, STRATEGIC_FX, { units: S.layers.units, terrain: S.terrain, scale: 6 }));
    S.terrain.setTerritory(territoryTexture(S.proj, FRONTIER_383), territoryTexture(S.proj, FRONTIER_385, { northChannel: 'b' }), 0);
    this.setStatus('就绪', 1);

    this.setQuality('medium');
    const resumeT = Number.isFinite(resume.T) ? resume.T : null;
    this.setTime(resumeT ?? 0, { snap: true });
    if (resumeT === null) {
      // opening: descend onto the strategic table, then start the story
      this.rig.from = { target: new THREE.Vector3(0, 0, 0), dist: 230, yaw: 0, pitch: 72 };
      this.rig.flyT = 0;
      this.rig.flyDur = 3.6;
      setTimeout(() => {
        if (!this.userTouched) this.play();
      }, 2600);
    } else {
      this.userTouched = true;
    }
    this.ready = true;
    this.loop();
    setTimeout(() => this.loader.classList.add('is-done'), 250);
    this.stage.renderer.domElement.addEventListener('pointerdown', () => (this.userTouched = true), { once: true });
  }

  // ---------------------------------------------------------------------------
  get episodeIndex() {
    return Math.min(Math.floor(this.T), N - 1);
  }

  get episode() {
    return EPISODES[this.episodeIndex];
  }

  get progress() {
    return THREE.MathUtils.clamp(this.T - this.episodeIndex, 0, 1);
  }

  setTime(T, { snap = false } = {}) {
    const prevIdx = this._lastIdx ?? -1;
    this.T = THREE.MathUtils.clamp(T, 0, N - 1e-4);
    const ep = this.episode;
    const idx = this.episodeIndex;
    if (ep.map !== this.activeMap) {
      this.switchMap(ep.map, !snap && this.ready);
      if (snap || !this.ready) this.rig.snapTo(ep, this.progress);
    } else if (snap) {
      this.rig.snapTo(ep, this.progress);
    } else if (idx !== prevIdx) {
      this.rig.beginFly();
    }
    if (idx !== prevIdx) {
      this._lastIdx = idx;
      this.stage.setLight(ep.light);
      this.ui?.setEpisode(idx);
      if (this.ready && !snap && !this.scrubbing) {
        this.ui?.showCaption(idx);
        this.sound.phrase(idx);
      }
    }
    if (snap) this.stage.snapLight();
    this.ui?.setTime(this.T);
  }

  switchMap(name, animated) {
    const apply = () => {
      for (const [k, t] of Object.entries(this.tables)) t.setVisible(k === name);
      this.table = this.tables[name];
      this.rig.setProjection(this.table.proj);
      this.ui?.setMap(name);
      this.ui?.renderPlaces(name === 'tactical' ? TACTICAL_PLACES : STRATEGIC_PLACES);
    };
    this.activeMap = name;
    if (!animated) {
      apply();
      return;
    }
    this.ui.fadeMap(true);
    clearTimeout(this._fadeTimer);
    this._fadeTimer = setTimeout(() => {
      apply();
      const ep = this.episode;
      // start a little higher and drift in
      const p = this.rig.poseFrom(ep.camera);
      this.rig._programmatic = true;
      this.rig.apply({ ...p, dist: p.dist * 1.6, pitch: Math.min(75, p.pitch + 14) });
      this.rig._programmatic = false;
      this.rig.beginFly(2.6);
      this.ui.fadeMap(false);
    }, 420);
  }

  play() {
    if (this.T >= N - 0.01) this.setTime(0, { snap: true });
    if (this.T - this.episodeIndex < 0.02) {
      this.ui.showCaption(this.episodeIndex);
      this.sound.phrase(this.episodeIndex);
    }
    this.playing = true;
    this.ui.setPlaying(true);
  }

  pause() {
    this.playing = false;
    this.ui.setPlaying(false);
  }

  togglePlay() {
    this.userTouched = true;
    if (this.playing) this.pause();
    else this.play();
  }

  jumpTo(i) {
    this.userTouched = true;
    this.rig.setAuto(true);
    this.setTime(i + 0.001);
    this.rig.beginFly(2.0);
  }

  stepEpisode(d) {
    const i = THREE.MathUtils.clamp(this.episodeIndex + d, 0, N - 1);
    this.jumpTo(i);
  }

  scrubTo(T) {
    this.userTouched = true;
    this.scrubbing = true;
    this.setTime(T);
    this.scrubbing = false;
  }

  flyToPlace(id) {
    const t = this.table;
    const p = t.resolver.places[id];
    if (!p) return;
    const [x, z] = t.resolver.point(id);
    const y = Math.max(t.proj.groundY(x, z), 0);
    this.rig.flyToPoint(x, y, z, t.name === 'tactical' ? 12 : 38);
    const el = t.layers.labels?.items.find((it) => it.p.id === id)?.el;
    if (el) setTimeout(() => this.ui.showTooltip(p, el), 1900);
    setTimeout(() => this.ui.showTooltip(null), 7000);
  }

  soundLevels() {
    const env = (list) => {
      let v = 0;
      for (const [a, b, lvl] of list) {
        if (this.T < a || this.T > b) continue;
        const e = Math.min(1, (this.T - a) / 0.05, (b - this.T) / 0.05);
        v = Math.max(v, lvl * e);
      }
      return v;
    };
    return { drums: this.playing ? env(SOUNDSCAPE.drums) : 0, wind: env(SOUNDSCAPE.wind) };
  }

  showMap(name) {
    if (this.episode.map === name) return;
    const i = EPISODES.findIndex((e) => e.map === name);
    this.jumpTo(i);
  }

  setLayer(key, v) {
    this.layerState[key] = v;
    for (const t of Object.values(this.tables)) {
      const L = t.layers;
      if (key === 'places') L.labels?.setEnabled(v);
      if (key === 'modern') L.labels?.setModern(v);
      if (key === 'arrows') L.arrows?.setEnabled(v);
      if (key === 'markers') L.markers?.setEnabled(v);
      if (key === 'unitLabels') L.units?.setLabelsVisible(v);
      if (key === 'contours') t.terrain.uniforms.uContours.value = v ? 0.75 : 0;
      if (key === 'grid') t.terrain.uniforms.uGrid.value = v ? 1 : 0;
    }
  }

  setExaggeration(e) {
    const tt = this.tables.tactical;
    const ss = this.tables.strategic;
    tt.terrain.setExaggeration(e);
    ss.terrain.setExaggeration(e * 2);
    for (const t of [tt, ss]) {
      t.layers.labels?.refreshHeights?.();
      t.layers.arrows?.refreshHeights?.();
      t.layers.markers?.refreshHeights?.();
    }
  }

  setQuality(q) {
    const st = this.stage;
    const dpr = window.devicePixelRatio || 1;
    const ratio = q === 'high' ? Math.min(dpr, 2) : q === 'medium' ? Math.min(dpr, 1.5) : 1;
    st.renderer.setPixelRatio(ratio);
    st.composer.setPixelRatio?.(ratio);
    st.renderer.shadowMap.enabled = q !== 'low';
    st.sun.castShadow = q !== 'low';
    const size = q === 'high' ? 4096 : 2048;
    st.sun.shadow.mapSize.set(size, size);
    if (st.sun.shadow.map) {
      st.sun.shadow.map.dispose();
      st.sun.shadow.map = null;
    }
    st.bloom.enabled = q !== 'low';
    st.onResize();
    this.quality = q;
  }

  // ---------------------------------------------------------------------------
  /** Drop to the light preset once if the machine cannot keep ~24 fps. */
  watchPerformance(rawDt) {
    if (this.qualityLocked || document.hidden) return;
    this.frameEMA = this.frameEMA === undefined ? rawDt : this.frameEMA * 0.95 + rawDt * 0.05;
    this.perfFrames = (this.perfFrames || 0) + 1;
    if (this.perfFrames > 150 && this.frameEMA > 1 / 24 && this.quality !== 'low') {
      this.setQuality(this.quality === 'high' ? 'medium' : 'low');
      const sel = this.root.querySelector('#lay-quality');
      if (sel) sel.value = this.quality;
      this.perfFrames = 0;
      this.frameEMA = undefined;
    }
  }

  loop() {
    const now = performance.now();
    const rawDt = (now - this.lastFrame) / 1000;
    const dt = Math.min(rawDt, 0.1);
    this.lastFrame = now;
    this.elapsed += dt;
    this.watchPerformance(rawDt);
    if (this.playing) {
      const ep = this.episode;
      const next = this.T + (dt * this.speed) / ep.duration;
      if (next >= N - 1e-4) {
        this.setTime(N - 1e-4);
        this.pause();
      } else {
        this.setTime(next);
      }
    }
    this.rig.update(dt, this.episode, this.progress);
    const st = this.stage;
    const focus = st.controls.target;
    const dist = st.camera.position.distanceTo(focus);
    const p = st.updateLight(dt, focus, dist * 0.9);
    const t = this.table;
    if (t) {
      t.terrain.uniforms.uNight.value = p.night;
      t.terrain.uniforms.uSkyColor.value.set(p.sky);
      t.terrain.update(this.elapsed);
      if (t === this.tables.strategic) {
        const a = TT('epilogue', 0.28);
        const b = TT('epilogue', 0.72);
        const f = THREE.MathUtils.clamp((this.T - a) / (b - a), 0, 1);
        t.terrain.uniforms.uTerritoryMix.value = f * f * (3 - 2 * f);
      }
      t.layers.props?.update(this.T);
      t.layers.units?.update(this.T, this.elapsed);
      t.layers.arrows?.update(this.T, this.elapsed, dist);
      t.layers.markers?.update(this.T, this.elapsed);
      const w = st.container.clientWidth;
      const h = st.container.clientHeight;
      t.layers.fx?.update(this.T, this.elapsed, dt, st.camera, h * st.renderer.getPixelRatio());
      const items = [];
      t.layers.markers?.collect(items);
      t.layers.arrows?.collect(items);
      t.layers.labels?.collect(items, st.camera, dist, w, h);
      t.layers.units?.collect(items);
      this.declutter.run(items, st.camera, w, h, this.ui.chrome);
      this.ui.updateHud(st.camera, st.controls, t.proj);
    }
    if (this.sound.enabled) this.sound.update(dt, this.soundLevels());
    st.render(this.elapsed);
    requestAnimationFrame(() => this.loop());
  }
}
