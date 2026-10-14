import * as THREE from 'three';
import { CSS2DObject } from 'three/examples/jsm/renderers/CSS2DRenderer.js';

const KIND_PRIORITY = { polity: 0, capital: 1, city: 2, fort: 2, camp: 2, ford: 3, mountain: 4, river: 5, site: 6, pass: 6, region: 7 };

/**
 * Place, mountain, river and region names as HTML labels pinned to the table.
 * Labels declutter by priority and fade with zoom level (rank 1 always, 3 only close up).
 */
export class LabelsLayer {
  constructor(resolver, places, { rivers = [], scale = 'tactical', onHover } = {}) {
    this.R = resolver;
    this.proj = resolver.proj;
    this.scale = scale;
    this.onHover = onHover;
    this.group = new THREE.Group();
    this.group.name = 'labels';
    this.items = [];
    this.enabled = true;
    this.modernEnabled = true;
    this.frame = 0;
    for (const p of places) this.addPlace(p);
    for (const r of rivers) this.addRiver(r);
  }

  addPlace(p) {
    const el = document.createElement('div');
    const side = p.side ? ` side-${p.side}` : '';
    el.className = `place place--${p.kind} rank-${p.rank}${side}${p.approx ? ' is-approx' : ''}`;
    if (p.kind === 'mountain') {
      el.innerHTML = `<span class="place__glyph" aria-hidden="true"></span><span class="place__name">${p.name}</span>`;
    } else if (p.kind === 'region' || p.kind === 'polity') {
      el.innerHTML = `<span class="place__name">${p.name}</span>`;
    } else {
      el.innerHTML = `<span class="place__pin" aria-hidden="true"></span><span class="place__text"><span class="place__name">${p.name}${p.approx ? '<i class="place__q">（约）</i>' : ''}</span>${p.modern ? `<span class="place__modern">${p.modern}</span>` : ''}</span>`;
    }
    if (p.note || p.modern) {
      el.classList.add('has-info');
      el.addEventListener('pointerenter', () => this.onHover?.(p, el));
      el.addEventListener('pointerleave', () => this.onHover?.(null, el));
      el.addEventListener('click', () => this.onHover?.(p, el, true));
    }
    const obj = new CSS2DObject(el);
    const [x, z] = this.R.point(p.at);
    const y = Math.max(this.proj.groundY(x, z), 0);
    obj.position.set(x, y, z);
    if (p.kind === 'region' || p.kind === 'polity' || p.kind === 'mountain') obj.center.set(0.5, 0.5);
    else obj.center.set(0, 1);
    this.group.add(obj);
    this.items.push({ obj, el, p, prio: KIND_PRIORITY[p.kind] ?? 6, rank: p.rank ?? 2, w: 0, h: 0 });
  }

  addRiver(r) {
    if (!r.name || !r.labelAt?.length) return;
    const path = this.R.rivers[r.id];
    if (!path) return;
    for (const f of r.labelAt) {
      const el = document.createElement('div');
      el.className = `river-label river--${r.kind}`;
      el.innerHTML = `<span class="river-label__t">${[...r.name].join('<i></i>')}</span>`;
      el.title = r.modern ? `${r.name}（今${r.modern}）` : r.name;
      const s = path.length * f;
      const a = path.at(s, {});
      const b = path.at(Math.min(path.length, s + 0.5), {});
      const obj = new CSS2DObject(el);
      const y = Math.max(this.proj.groundY(a.x, a.z), 0) + 0.05;
      obj.position.set(a.x, y, a.z);
      obj.center.set(0.5, 0.5);
      this.group.add(obj);
      this.items.push({
        obj, el, p: { kind: 'river', rank: r.kind === 'major' ? 1 : r.kind === 'river' ? 2 : 3, name: r.name },
        prio: KIND_PRIORITY.river, rank: r.kind === 'major' ? 1 : r.kind === 'river' ? 2 : 3, river: true,
        a: new THREE.Vector3(a.x, y, a.z), b: new THREE.Vector3(b.x, y, b.z), w: 0, h: 0,
      });
    }
  }

  setVisible(v) {
    this.group.visible = v;
    for (const it of this.items) it.obj.visible = v && this.enabled;
  }

  setEnabled(v) {
    this.enabled = v;
    this.setVisible(this.group.visible);
  }

  setModern(v) {
    this.modernEnabled = v;
    for (const it of this.items) it.el.classList.toggle('hide-modern', !v);
  }

  /** Orient river names and decide which labels the zoom level wants; collisions are global. */
  collect(items, camera, zoom, viewW, viewH) {
    if (!this.group.visible || !this.enabled) return;
    const strategic = this.scale === 'strategic';
    const r2 = strategic ? 95 : 70;
    const r3 = strategic ? 48 : 26;
    const modernOn = this.modernEnabled && zoom < (strategic ? 70 : 34);
    const v = this._v || (this._v = new THREE.Vector3());
    const v2 = this._v2 || (this._v2 = new THREE.Vector3());
    for (const it of this.items) {
      if (it.river) {
        v.copy(it.a).project(camera);
        v2.copy(it.b).project(camera);
        let ang = Math.atan2(-(v2.y - v.y) * viewH, (v2.x - v.x) * viewW);
        if (ang > Math.PI / 2) ang -= Math.PI;
        if (ang < -Math.PI / 2) ang += Math.PI;
        it.el.style.setProperty('--rot', `${ang}rad`);
      }
      let want = it.rank === 1 || (it.rank === 2 && zoom < r2) || (it.rank === 3 && zoom < r3);
      if (it.p.kind === 'polity') want = want && zoom > (strategic ? 40 : 1e9);
      if (it.p.kind === 'region') want = want && zoom > (strategic ? 26 : 12);
      it.el.classList.toggle('show-modern', modernOn);
      const ghost = it.p.kind === 'region' || it.p.kind === 'polity';
      items.push({ el: it.el, obj: it.obj, want, prio: ghost ? 90 : 20 + it.rank * 3 + it.prio * 0.3, ghost });
    }
  }

  refreshHeights() {
    for (const it of this.items) {
      const o = it.obj.position;
      const y = Math.max(this.proj.groundY(o.x, o.z), 0) + (it.river ? 0.05 : 0);
      o.y = y;
      if (it.a) it.a.y = it.b.y = y;
    }
  }
}
