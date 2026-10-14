import * as THREE from 'three';
import { CSS2DObject } from 'three/examples/jsm/renderers/CSS2DRenderer.js';

const ICONS = {
  battle:
    '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 3l8.5 8.5M3 4.2L4.2 3M20 3l-8.5 8.5M21 4.2L19.8 3M6.2 14.6l3.2 3.2M5 20l3.4-3.4M17.8 14.6l-3.2 3.2M19 20l-3.4-3.4M8.6 15.4l7-7M15.4 15.4l-7-7" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>',
  capture:
    '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 21V3" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><path d="M6 4h11l-2.6 3.5L17 11H6z" fill="currentColor"/></svg>',
  death:
    '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2l3 7h-6zM10.3 9h3.4l-.6 13h-2.2z" fill="currentColor"/><path d="M6 9.5h12" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>',
  note:
    '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4" fill="currentColor"/></svg>',
  intercept:
    '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 5l14 14M19 5L5 19" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"/></svg>',
  go:
    '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3.5" y="3.5" width="17" height="17" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.3"/><path d="M3.5 9.2h17M3.5 14.8h17M9.2 3.5v17M14.8 3.5v17" stroke="currentColor" stroke-width="0.9"/><circle cx="9.2" cy="9.2" r="2.2" fill="#111"/><circle cx="14.8" cy="14.8" r="2.2" fill="#f3efe4" stroke="#111" stroke-width=".6"/><circle cx="14.8" cy="9.2" r="2.2" fill="#111"/></svg>',
};

/**
 * Event markers: battles, captures, deaths, speeches and idiom seals. Each is an HTML card
 * on a leader line; battle markers also pulse a ring on the terrain.
 */
export class MarkersLayer {
  constructor(resolver, defs, units, { ringScale = 1 } = {}) {
    this.R = resolver;
    this.proj = resolver.proj;
    this.units = units;
    this.group = new THREE.Group();
    this.group.name = 'markers';
    this.enabled = true;
    this.items = defs.map((d) => this.prepare(d, ringScale));
  }

  prepare(def, ringScale) {
    const el = document.createElement('div');
    const side = def.side ? ` side-${def.side}` : '';
    el.className = `marker marker--${def.kind}${side}`;
    let inner;
    if (def.kind === 'idiom') {
      inner = `<div class="seal" aria-label="${def.title}">${[...def.title].map((c) => `<span>${c}</span>`).join('')}</div>${def.text ? `<div class="seal__note">${def.text}</div>` : ''}`;
    } else if (def.kind === 'speech') {
      inner = `<div class="bubble"><div class="bubble__who">${def.title}</div><div class="bubble__say">“${def.text}”</div></div><div class="stem"></div>`;
    } else {
      inner = `<div class="card"><span class="card__icon">${ICONS[def.kind] || ICONS.note}</span><span class="card__body"><span class="card__title">${def.title}</span>${def.text ? `<span class="card__text">${def.text}</span>` : ''}</span></div><div class="stem"></div>`;
    }
    el.innerHTML = `<div class="marker__in">${inner}</div>`;
    const obj = new CSS2DObject(el);
    obj.center.set(0.5, 1);
    obj.visible = false;
    this.group.add(obj);
    let pos = null;
    if (def.at) {
      const [x, z] = this.R.point(def.at);
      pos = new THREE.Vector3(x, Math.max(this.proj.groundY(x, z), 0), z);
      obj.position.copy(pos);
    }
    let ring = null;
    if (def.kind === 'battle' || def.kind === 'capture' || def.kind === 'death') {
      const r = 0.55 * ringScale;
      const geo = new THREE.RingGeometry(r * 0.82, r, 64);
      geo.rotateX(-Math.PI / 2);
      const color = def.kind === 'battle' ? '#ffb15a' : def.kind === 'death' ? '#e04b3a' : def.side === 'qin' ? '#5b84e6' : '#e86a4a';
      const mat = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0, depthWrite: false, side: THREE.DoubleSide });
      ring = new THREE.Mesh(geo, mat);
      ring.renderOrder = 6;
      if (pos) ring.position.copy(pos).add(new THREE.Vector3(0, 0.03 * ringScale, 0));
      ring.visible = false;
      this.group.add(ring);
    }
    return { def, el, obj, pos, ring, shown: false };
  }

  setVisible(v) {
    this.group.visible = v;
    if (!v) for (const it of this.items) it.obj.visible = false;
  }

  setEnabled(v) {
    this.enabled = v;
  }

  collect(items) {
    // newer events win the space; older overlapping cards step aside
    for (const it of this.items) {
      if (it.shown) items.push({ el: it.el, obj: it.obj, want: true, prio: 5 - it.def.t0 / 3, pad: 4 });
    }
  }

  refreshHeights() {
    for (const it of this.items) {
      if (!it.pos) continue;
      it.pos.y = Math.max(this.proj.groundY(it.pos.x, it.pos.z), 0);
      it.obj.position.copy(it.pos);
    }
  }

  update(T, time) {
    for (const it of this.items) {
      const { def } = it;
      let on = this.enabled && this.group.visible && T >= def.t0 && T < def.t1;
      let p = it.pos;
      if (on && def.unit) {
        const a = this.units?.anchor(def.unit);
        if (!a) on = false;
        else p = a;
      }
      if (on && p) it.obj.position.set(p.x, p.y + (def.unit ? this.units.opts.bannerScale * 1.05 : 0), p.z);
      if (on !== it.shown) {
        it.shown = on;
        it.obj.visible = on;
        if (on) {
          it.el.classList.remove('is-in');
          void it.el.offsetWidth;
          it.el.classList.add('is-in');
        }
      }
      if (it.ring) {
        it.ring.visible = on;
        if (on) {
          const ph = (time * 0.6) % 1;
          const s = 0.6 + ph * 1.2;
          it.ring.scale.set(s, 1, s);
          it.ring.material.opacity = (1 - ph) * 0.75;
          if (p) it.ring.position.set(p.x, p.y + 0.02, p.z);
        }
      }
    }
  }
}
