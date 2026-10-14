import * as THREE from 'three';
import { MapProjection } from '../world/MapProjection.js';
import { HeightField, loadImage, imageToPixels } from '../world/HeightField.js';
import { Terrain } from '../world/Terrain.js';

/**
 * One sand table (strategic overview or battlefield): projection, terrain and everything
 * placed on it. Only one table is visible at a time.
 */
export class Table {
  constructor(name, meta, urls, opts) {
    this.name = name;
    this.meta = meta;
    this.urls = urls;
    this.opts = opts;
    this.group = new THREE.Group();
    this.group.name = `table-${name}`;
    this.group.visible = false;
    this.layers = {};
  }

  async load() {
    const [hImg, wImg] = await Promise.all([loadImage(this.urls.height), loadImage(this.urls.water)]);
    const field = new HeightField(this.meta, imageToPixels(hImg), imageToPixels(wImg));
    this.field = field;
    this.proj = new MapProjection(this.meta, { worldWidth: 100, exaggeration: this.opts.exaggeration });
    this.proj.field = field;
    this.terrain = new Terrain(this.proj, field, wImg, {
      strategic: this.name === 'strategic',
      meshStep: this.opts.meshStep ?? 2,
      slabDepth: this.opts.slabDepth ?? 2.6,
    });
    this.group.add(this.terrain.group);
    return this;
  }

  add(name, layer) {
    this.layers[name] = layer;
    if (layer.group) this.group.add(layer.group);
    return layer;
  }

  setVisible(v) {
    this.group.visible = v;
    for (const layer of Object.values(this.layers)) layer.setVisible?.(v);
  }
}
