// Uniforms shared by every patched material, and the "snowify" patch that lets snow settle on
// any upward-facing surface (ground, roofs, rocks, pine boughs) as winter arrives.
import * as THREE from 'three';

export const U = {
  uTime: { value: 0 },
  uSnow: { value: 0 },
  uSnowColor: { value: new THREE.Color('#f4f8fc') },
  uNight: { value: 0 },
};

// opts.leaf: { center: THREE.Vector3 } shrinks the geometry toward that point by uLeaf (deciduous crowns)
// opts.sway: amplitude of wind sway, scaled by height above ground
export function snowify(mat, opts = {}) {
  const extra = {};
  if (opts.leaf) extra.uLeaf = opts.leaf.uniform;
  const prev = mat.onBeforeCompile;
  mat.onBeforeCompile = (sh) => {
    prev?.call(mat, sh);
    Object.assign(sh.uniforms, U, extra);
    sh.vertexShader = sh.vertexShader
      .replace(
        '#include <common>',
        `#include <common>
         varying vec3 vSnowN; varying vec3 vSnowP; uniform float uTime;
         ${opts.leaf ? 'uniform float uLeaf;' : ''}`
      )
      .replace(
        '#include <begin_vertex>',
        `#include <begin_vertex>
         ${opts.leaf ? `transformed = mix(vec3(${opts.leaf.center.toArray().map((v) => v.toFixed(3)).join(',')}), transformed, uLeaf);` : ''}
         ${
           opts.sway
             ? `{ vec3 ip = vec3(0.0);
                 #ifdef USE_INSTANCING
                   ip = instanceMatrix[3].xyz;
                 #endif
                 float k = max(transformed.y, 0.0) * ${opts.sway.toFixed(4)};
                 transformed.x += sin(uTime * 1.3 + ip.x * 0.37 + ip.z * 0.21) * k;
                 transformed.z += cos(uTime * 1.1 + ip.z * 0.31) * k * 0.6; }`
             : ''
         }`
      )
      .replace(
        '#include <worldpos_vertex>',
        `#include <worldpos_vertex>
         {
           vec3 wn = objectNormal;
           vec4 wp = vec4(transformed, 1.0);
           #ifdef USE_INSTANCING
             wn = mat3(instanceMatrix) * wn;
             wp = instanceMatrix * wp;
           #endif
           vSnowN = normalize(mat3(modelMatrix) * wn);
           vSnowP = (modelMatrix * wp).xyz;
         }`
      );
    sh.fragmentShader = sh.fragmentShader
      .replace(
        '#include <common>',
        `#include <common>
         varying vec3 vSnowN; varying vec3 vSnowP; uniform float uSnow; uniform vec3 uSnowColor;`
      )
      .replace(
        '#include <alphamap_fragment>',
        `#include <alphamap_fragment>
         {
           float jitter = fract(sin(dot(floor(vSnowP.xz * 2.0), vec2(12.9898, 78.233))) * 43758.5453);
           float sn = uSnow * smoothstep(${(opts.snowLo ?? 0.3).toFixed(2)}, ${(opts.snowHi ?? 0.7).toFixed(2)}, vSnowN.y + jitter * 0.12);
           diffuseColor.rgb = mix(diffuseColor.rgb, uSnowColor, sn);
         }`
      );
  };
  mat.customProgramCacheKey = () => `snow-${opts.leaf ? opts.leaf.center.toArray().join('_') : ''}-${opts.key ?? ''}-${opts.sway ?? 0}-${opts.snowLo ?? 0.3}`;
  return mat;
}

export function stdMat(color, o = {}) {
  const m = new THREE.MeshStandardMaterial({ color, roughness: 0.85, metalness: 0, flatShading: true, ...o });
  return m;
}
