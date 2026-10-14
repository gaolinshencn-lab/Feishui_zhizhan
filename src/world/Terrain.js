import * as THREE from 'three';
import {
  terrainVertexPars,
  terrainVertexMain,
  terrainFragmentPars,
  terrainColorFragment,
  terrainNormalFragment,
  terrainRoughnessFragment,
  terrainEmissiveFragment,
  terrainAOFragment,
} from './terrainShader.js';

// 秦岭—淮河 dividing line (lon, lat), used to green the south on the strategic table.
const DIVIDE = [
  [107.5, 33.75], [108.8, 33.85], [110.2, 33.75], [111.5, 33.45], [112.6, 33.2],
  [113.6, 32.75], [114.8, 32.45], [116.3, 32.45], [117.8, 32.95], [119.9, 34.05],
];

export class Terrain {
  /**
   * @param {import('./MapProjection.js').MapProjection} proj
   * @param {import('./HeightField.js').HeightField} field
   * @param {HTMLImageElement} waterImage
   */
  constructor(proj, field, waterImage, { strategic = false, meshStep = 2, slabDepth = 2.6 } = {}) {
    this.proj = proj;
    this.field = field;
    this.strategic = strategic;
    this.meshStep = meshStep;
    this.slabDepth = slabDepth;
    this.group = new THREE.Group();
    this.group.name = strategic ? 'terrain-strategic' : 'terrain-tactical';

    this.waterTex = new THREE.Texture(waterImage);
    this.waterTex.colorSpace = THREE.NoColorSpace;
    this.waterTex.minFilter = THREE.LinearFilter;
    this.waterTex.magFilter = THREE.LinearFilter;
    this.waterTex.generateMipmaps = false;
    this.waterTex.wrapS = this.waterTex.wrapT = THREE.ClampToEdgeWrapping;
    this.waterTex.flipY = false; // row 0 = north, like the height grid
    this.waterTex.needsUpdate = true;

    const blank = new THREE.DataTexture(new Uint8Array([0, 0, 0, 0]), 1, 1);
    blank.needsUpdate = true;

    this.uniforms = {
      uNormalAO: { value: null },
      uWater: { value: this.waterTex },
      uTerritory: { value: blank },
      uTerritoryB: { value: blank },
      uHasTerritory: { value: 0 },
      uTerritoryMix: { value: 0 },
      uMapSize: { value: new THREE.Vector2(proj.width, proj.depth) },
      uYScale: { value: proj.yScale },
      uSdfScale: { value: proj.meta.sdfScale },
      uMetresPerWorld: { value: 1000 / proj.kmToWorld },
      uTime: { value: 0 },
      uStrategic: { value: strategic ? 1 : 0 },
      uContours: { value: 0.75 },
      uContourStep: { value: strategic ? 200 : 15 },
      uGrid: { value: 0 },
      uGridStep: { value: strategic ? 100000 : 5000 },
      uSkyColor: { value: new THREE.Color(0.55, 0.62, 0.66) },
      uHighlight: { value: new THREE.Vector4(0, 0, 1, 0) },
      uRiverTint: { value: new THREE.Vector4(0, 0, 1, 0) },
      uQinColor: { value: new THREE.Color('#3e5fb0') },
      uJinColor: { value: new THREE.Color('#c8452f') },
      uNight: { value: 0 },
      uDivide: { value: DIVIDE.map(([lon, lat]) => new THREE.Vector2(...proj.geoToUV(lon, lat))) },
    };

    this.bakeNormalAO();
    this.buildMesh();
    this.buildSlab();
  }

  // ---------------------------------------------------------------------------
  bakeNormalAO() {
    const { nx, ny, h } = this.field;
    const ys = this.proj.yScale;
    const sx = this.proj.width / (nx - 1);
    const sz = this.proj.depth / (ny - 1);
    const data = this.naoData || new Uint8Array(nx * ny * 4);
    for (let j = 0; j < ny; j++) {
      const jt = j > 0 ? j - 1 : j;
      const jb = j < ny - 1 ? j + 1 : j;
      for (let i = 0; i < nx; i++) {
        const il = i > 0 ? i - 1 : i;
        const ir = i < nx - 1 ? i + 1 : i;
        const dx = ((h[j * nx + ir] - h[j * nx + il]) * ys) / ((ir - il) * sx);
        const dz = ((h[jb * nx + i] - h[jt * nx + i]) * ys) / ((jb - jt) * sz);
        const inv = 1 / Math.sqrt(dx * dx + 1 + dz * dz);
        const k = (j * nx + i) * 4;
        data[k] = (-dx * inv * 0.5 + 0.5) * 255;
        data[k + 1] = (inv * 0.5 + 0.5) * 255;
        data[k + 2] = (-dz * inv * 0.5 + 0.5) * 255;
      }
    }
    // horizon-based ambient occlusion at half resolution, then upsampled
    const step = 2;
    const ax = Math.ceil(nx / step);
    const az = Math.ceil(ny / step);
    const ao = new Float32Array(ax * az);
    const dirs = 10;
    const radii = [1, 2, 3, 5, 8, 12, 18, 26, 36];
    const cosT = [];
    const sinT = [];
    for (let d = 0; d < dirs; d++) {
      cosT.push(Math.cos((d / dirs) * Math.PI * 2));
      sinT.push(Math.sin((d / dirs) * Math.PI * 2));
    }
    const strength = this.strategic ? 1.25 : 1.5;
    for (let j = 0; j < az; j++) {
      const py = Math.min(j * step, ny - 1);
      for (let i = 0; i < ax; i++) {
        const px = Math.min(i * step, nx - 1);
        const h0 = h[py * nx + px] * ys;
        let occ = 0;
        for (let d = 0; d < dirs; d++) {
          let maxT = 0;
          for (let r = 0; r < radii.length; r++) {
            const qx = Math.round(px + cosT[d] * radii[r]);
            const qy = Math.round(py + sinT[d] * radii[r]);
            if (qx < 0 || qy < 0 || qx >= nx || qy >= ny) break;
            const dist = Math.hypot((qx - px) * sx, (qy - py) * sz);
            const t = (h[qy * nx + qx] * ys - h0) / dist;
            if (t > maxT) maxT = t;
          }
          occ += maxT / Math.sqrt(1 + maxT * maxT); // sin(horizon angle)
        }
        ao[j * ax + i] = Math.max(0.2, 1 - strength * (occ / dirs));
      }
    }
    for (let j = 0; j < ny; j++) {
      const fy = j / step;
      const j0 = Math.min(fy | 0, az - 1);
      const j1 = Math.min(j0 + 1, az - 1);
      const ty = fy - j0;
      for (let i = 0; i < nx; i++) {
        const fx = i / step;
        const i0 = Math.min(fx | 0, ax - 1);
        const i1 = Math.min(i0 + 1, ax - 1);
        const tx = fx - i0;
        const a = ao[j0 * ax + i0] * (1 - tx) + ao[j0 * ax + i1] * tx;
        const b = ao[j1 * ax + i0] * (1 - tx) + ao[j1 * ax + i1] * tx;
        data[(j * nx + i) * 4 + 3] = (a * (1 - ty) + b * ty) * 255;
      }
    }
    this.naoData = data;
    if (!this.naoTex) {
      this.naoTex = new THREE.DataTexture(data, nx, ny, THREE.RGBAFormat, THREE.UnsignedByteType);
      this.naoTex.colorSpace = THREE.NoColorSpace;
      this.naoTex.minFilter = THREE.LinearMipmapLinearFilter;
      this.naoTex.magFilter = THREE.LinearFilter;
      this.naoTex.generateMipmaps = true;
      this.naoTex.anisotropy = 4;
      this.naoTex.flipY = false;
      this.uniforms.uNormalAO.value = this.naoTex;
    }
    this.naoTex.needsUpdate = true;
  }

  // ---------------------------------------------------------------------------
  buildMesh() {
    const { nx, ny } = this.field;
    const step = this.meshStep;
    const sx = Math.floor((nx - 1) / step);
    const sz = Math.floor((ny - 1) / step);
    this.segX = sx;
    this.segZ = sz;
    const count = (sx + 1) * (sz + 1);
    const pos = new Float32Array(count * 3);
    for (let j = 0; j <= sz; j++) {
      for (let i = 0; i <= sx; i++) {
        const u = i / sx;
        const v = j / sz;
        const k = (j * (sx + 1) + i) * 3;
        pos[k] = (u - 0.5) * this.proj.width;
        pos[k + 2] = (v - 0.5) * this.proj.depth;
      }
    }
    const idx = new Uint32Array(sx * sz * 6);
    let p = 0;
    for (let j = 0; j < sz; j++) {
      for (let i = 0; i < sx; i++) {
        const a = j * (sx + 1) + i;
        const b = a + 1;
        const c = a + (sx + 1);
        const d = c + 1;
        idx[p++] = a;
        idx[p++] = c;
        idx[p++] = b;
        idx[p++] = b;
        idx[p++] = c;
        idx[p++] = d;
      }
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    geo.setIndex(new THREE.BufferAttribute(idx, 1));
    this.geometry = geo;
    this.updateHeights();

    const mat = new THREE.MeshStandardMaterial({ roughness: 0.93, metalness: 0.0, color: 0xffffff });
    mat.onBeforeCompile = (shader) => {
      Object.assign(shader.uniforms, this.uniforms);
      shader.vertexShader = shader.vertexShader
        .replace('#include <common>', `#include <common>\n${terrainVertexPars}`)
        .replace('#include <project_vertex>', `#include <project_vertex>\n${terrainVertexMain}`);
      shader.fragmentShader = shader.fragmentShader
        .replace('#include <common>', `#include <common>\n${terrainFragmentPars}`)
        .replace('#include <color_fragment>', terrainColorFragment)
        .replace('#include <normal_fragment_maps>', terrainNormalFragment)
        .replace('#include <roughnessmap_fragment>', terrainRoughnessFragment)
        .replace('#include <emissivemap_fragment>', `#include <emissivemap_fragment>\n${terrainEmissiveFragment}`)
        .replace('#include <aomap_fragment>', `#include <aomap_fragment>\n${terrainAOFragment}`);
    };
    mat.customProgramCacheKey = () => 'terrain-v1';
    this.material = mat;
    this.mesh = new THREE.Mesh(geo, mat);
    this.mesh.receiveShadow = true;
    this.mesh.castShadow = false;
    this.mesh.name = 'terrain';
    this.group.add(this.mesh);
  }

  updateHeights() {
    const pos = this.geometry.attributes.position.array;
    const sx = this.segX;
    const sz = this.segZ;
    const ys = this.proj.yScale;
    for (let j = 0; j <= sz; j++) {
      for (let i = 0; i <= sx; i++) {
        const k = (j * (sx + 1) + i) * 3;
        pos[k + 1] = this.field.height(i / sx, j / sz) * ys;
      }
    }
    this.geometry.attributes.position.needsUpdate = true;
    this.geometry.computeVertexNormals();
    this.geometry.computeBoundingSphere();
    this.geometry.computeBoundingBox();
    this.uniforms.uYScale.value = ys;
  }

  // ---------------------------------------------------------------------------
  // The cut sides of the sand table: soil strata, a lacquered base and a brass rim.
  buildSlab() {
    const W = this.proj.width;
    const D = this.proj.depth;
    const base = -this.slabDepth;
    const n = 400;
    const ys = () => this.proj.yScale;
    const edges = [
      (t) => [(t - 0.5) * W, -D / 2, t, 0], // north
      (t) => [W / 2, (t - 0.5) * D, 1, t], // east
      (t) => [(0.5 - t) * W, D / 2, 1 - t, 1], // south
      (t) => [-W / 2, (0.5 - t) * D, 0, 1 - t], // west
    ];
    const verts = [];
    const tops = [];
    const idx = [];
    let vi = 0;
    for (const edge of edges) {
      for (let k = 0; k <= n; k++) {
        const [x, z, u, v] = edge(k / n);
        const top = Math.max(this.field.height(u, v), this.strategic ? 0 : -1e9) * ys();
        verts.push(x, top, z, x, base, z);
        tops.push(top, top);
        if (k < n) {
          idx.push(vi, vi + 1, vi + 2, vi + 2, vi + 1, vi + 3);
        }
        vi += 2;
      }
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.Float32BufferAttribute(verts, 3));
    geo.setAttribute('aTop', new THREE.Float32BufferAttribute(tops, 1));
    geo.setIndex(idx);
    geo.computeVertexNormals();
    const strataUniforms = { uBase: { value: base }, uStrategic: { value: this.strategic ? 1 : 0 } };
    const mat = new THREE.MeshStandardMaterial({ roughness: 0.95, metalness: 0, side: THREE.DoubleSide });
    mat.onBeforeCompile = (shader) => {
      Object.assign(shader.uniforms, strataUniforms);
      shader.vertexShader = shader.vertexShader
        .replace('#include <common>', '#include <common>\nattribute float aTop;\nvarying float vTop;\nvarying vec3 vSPos;')
        .replace('#include <project_vertex>', '#include <project_vertex>\nvTop = aTop;\nvSPos = (modelMatrix * vec4(transformed, 1.0)).xyz;');
      shader.fragmentShader = shader.fragmentShader
        .replace(
          '#include <common>',
          `#include <common>
varying float vTop;
varying vec3 vSPos;
uniform float uBase;
uniform float uStrategic;
float sHash(float n) { return fract(sin(n) * 43758.5453); }
float sNoise(float x) { float i = floor(x); float f = fract(x); return mix(sHash(i), sHash(i + 1.0), f * f * (3.0 - 2.0 * f)); }`
        )
        .replace(
          '#include <color_fragment>',
          `
float depthBelow = vTop - vSPos.y;
float along = vSPos.x + vSPos.z;
float wav = (sNoise(along * 0.35) - 0.5) * 0.12 + (sNoise(along * 1.7) - 0.5) * 0.04;
float d = depthBelow + wav;
vec3 c = vec3(0.36, 0.30, 0.22);
c = mix(c, vec3(0.47, 0.38, 0.26), smoothstep(0.08, 0.1, d) * (1.0 - smoothstep(0.42, 0.45, d)));
c = mix(c, vec3(0.58, 0.48, 0.33), smoothstep(0.45, 0.48, d) * (1.0 - smoothstep(0.82, 0.86, d)));
c = mix(c, vec3(0.44, 0.36, 0.27), smoothstep(0.86, 0.9, d) * (1.0 - smoothstep(1.35, 1.4, d)));
c = mix(c, vec3(0.52, 0.45, 0.34), smoothstep(1.4, 1.45, d));
c *= 0.85 + 0.25 * sNoise(along * 9.0 + floor(d * 18.0) * 3.1);
c = mix(c, vec3(0.30, 0.45, 0.47), (1.0 - step(0.0, vTop - 0.0001)) * 0.0);
// topsoil band
c = mix(vec3(0.30, 0.27, 0.17), c, smoothstep(0.0, 0.06, d));
// lacquered plinth at the bottom
float plinth = 1.0 - smoothstep(0.38, 0.42, vSPos.y - uBase);
c = mix(c, vec3(0.13, 0.07, 0.05), plinth);
float rim = 1.0 - smoothstep(0.0, 0.035, abs(vSPos.y - uBase - 0.42));
c = mix(c, vec3(0.78, 0.6, 0.32), rim * 0.9);
diffuseColor.rgb = c;
`
        );
    };
    mat.customProgramCacheKey = () => 'slab-v1';
    this.slab = new THREE.Mesh(geo, mat);
    this.slab.receiveShadow = true;
    this.slab.name = 'slab';
    this.group.add(this.slab);

    // bottom plate
    const bottom = new THREE.Mesh(
      new THREE.PlaneGeometry(W, D),
      new THREE.MeshStandardMaterial({ color: 0x1a0f0b, roughness: 0.6, metalness: 0.1 })
    );
    bottom.rotation.x = Math.PI / 2;
    bottom.position.y = base;
    this.bottom = bottom;
    this.group.add(bottom);
    if (!this.floor) this.buildFloor(base);
  }

  // A dark lacquered table top under the model, lit by a soft pool of light, with a contact shadow.
  buildFloor(base) {
    const W = this.proj.width;
    const D = this.proj.depth;
    const geo = new THREE.PlaneGeometry(900, 900, 1, 1);
    geo.rotateX(-Math.PI / 2);
    const mat = new THREE.ShaderMaterial({
      uniforms: { uHalf: { value: new THREE.Vector2(W / 2, D / 2) } },
      vertexShader: `varying vec3 vP; void main(){ vP = position; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
      fragmentShader: `
        uniform vec2 uHalf; varying vec3 vP;
        float h(vec2 p){ return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
        float n(vec2 p){ vec2 i = floor(p); vec2 f = fract(p); f = f*f*(3.0-2.0*f);
          return mix(mix(h(i), h(i+vec2(1,0)), f.x), mix(h(i+vec2(0,1)), h(i+vec2(1,1)), f.x), f.y); }
        void main(){
          vec2 p = vP.xz;
          float grain = n(vec2(p.x * 0.6, p.y * 0.035)) * 0.6 + n(vec2(p.x * 2.3, p.y * 0.12)) * 0.4;
          vec3 wood = mix(vec3(0.085, 0.060, 0.046), vec3(0.13, 0.092, 0.066), grain);
          float r = length(p / vec2(1.35, 1.0));
          float pool = 1.0 - smoothstep(30.0, 175.0, r);
          vec3 col = wood * (0.28 + 0.95 * pool);
          vec2 q = abs(p) - uHalf;
          float d = length(max(q, 0.0)) + min(max(q.x, q.y), 0.0);
          col *= 1.0 - 0.75 * exp(-max(d, 0.0) / 1.6);
          gl_FragColor = vec4(col, 1.0);
        }`,
      depthWrite: true,
    });
    const floor = new THREE.Mesh(geo, mat);
    floor.position.y = base - 0.01;
    floor.renderOrder = -0.5;
    this.floor = floor;
    this.group.add(floor);
  }

  setExaggeration(e) {
    this.proj.setExaggeration(e);
    this.updateHeights();
    this.bakeNormalAO();
    this.group.remove(this.slab, this.bottom);
    this.slab.geometry.dispose();
    this.bottom.geometry.dispose();
    this.buildSlab();
  }

  setTerritory(texA, texB, mix = 0) {
    this.uniforms.uTerritory.value = texA;
    this.uniforms.uTerritoryB.value = texB || texA;
    this.uniforms.uTerritoryMix.value = mix;
    this.uniforms.uHasTerritory.value = texA ? 1 : 0;
  }

  update(time) {
    this.uniforms.uTime.value = time;
  }
}
