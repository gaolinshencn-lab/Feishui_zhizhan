import * as THREE from 'three';

/**
 * One screen-space collision pass over every HTML label on the active table.
 * Lower `prio` wins; `sticky` items (event markers) always show but still claim space.
 * A label whose middle falls under one of the `blocked` boxes (the UI panels) is hidden too.
 */
export class Declutter {
  constructor() {
    this.v = new THREE.Vector3();
    this.frame = 0;
  }

  run(items, camera, w, h, blocked = []) {
    this.frame++;
    if (this.frame % 2 !== 0 && this.frame > 12) return;
    const placed = [];
    items.sort((a, b) => a.prio - b.prio);
    const v = this.v;
    for (const it of items) {
      const el = it.el;
      if (!it.want) {
        el.classList.add('is-culled');
        continue;
      }
      it.obj.getWorldPosition(v);
      v.project(camera);
      if (v.z > 1 || Math.abs(v.x) > 1.05 || Math.abs(v.y) > 1.05) {
        el.classList.add('is-culled');
        continue;
      }
      const ww = el.offsetWidth || 40;
      const hh = el.offsetHeight || 16;
      const sx = (v.x * 0.5 + 0.5) * w;
      const sy = (-v.y * 0.5 + 0.5) * h;
      const cx = it.obj.center.x;
      const cy = it.obj.center.y;
      const box = [sx - ww * cx, sy - hh * cy, sx + ww * (1 - cx), sy + hh * (1 - cy)];
      const pad = it.pad ?? 2;
      let hit = false;
      if (!it.sticky) {
        const mx = (box[0] + box[2]) / 2;
        const my = (box[1] + box[3]) / 2;
        for (const b of blocked) {
          if (mx > b[0] && mx < b[2] && my > b[1] && my < b[3]) {
            hit = true;
            break;
          }
        }
      }
      if (!it.sticky && !hit) {
        for (const b of placed) {
          if (box[0] - pad < b[2] && box[2] + pad > b[0] && box[1] - pad < b[3] && box[3] + pad > b[1]) {
            hit = true;
            break;
          }
        }
      }
      el.classList.toggle('is-culled', hit);
      if (!hit && !it.ghost) placed.push(box);
    }
  }
}
