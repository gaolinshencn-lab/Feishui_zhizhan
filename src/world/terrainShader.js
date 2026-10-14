// GLSL injected into MeshStandardMaterial for the sand-table terrain.
// Albedo is procedural (fields, marsh, scrub, rock, snow), water comes from a signed
// distance field, normals + AO from a baked texture. Lighting, shadows and fog stay three.js'.

export const terrainVertexPars = /* glsl */ `
varying vec2 vMapUv;
varying float vElev;
varying vec3 vWPos;
uniform vec2 uMapSize;     // world width, depth
uniform float uYScale;     // world units per metre
`;

export const terrainVertexMain = /* glsl */ `
vWPos = (modelMatrix * vec4(transformed, 1.0)).xyz;
vMapUv = vec2(vWPos.x / uMapSize.x + 0.5, vWPos.z / uMapSize.y + 0.5);
vElev = transformed.y / uYScale;
`;

export const terrainFragmentPars = /* glsl */ `
varying vec2 vMapUv;
varying float vElev;
varying vec3 vWPos;
uniform sampler2D uNormalAO;
uniform sampler2D uWater;
uniform sampler2D uTerritory;
uniform float uHasTerritory;
uniform float uTerritoryMix;
uniform sampler2D uTerritoryB;
uniform vec2 uMapSize;
uniform float uSdfScale;
uniform float uMetresPerWorld;
uniform float uTime;
uniform float uStrategic;
uniform float uContours;
uniform float uContourStep;
uniform float uGrid;
uniform float uGridStep;     // metres
uniform vec3 uSkyColor;
uniform vec4 uHighlight;     // uv, radius (world units), strength
uniform vec4 uRiverTint;     // uv, radius (world units), amount
uniform vec3 uQinColor;
uniform vec3 uJinColor;
uniform float uNight;
uniform vec2 uDivide[10];    // 秦岭—淮河 line in uv space (west → east)

float tHash(vec2 p) {
  vec3 p3 = fract(vec3(p.xyx) * 0.1031);
  p3 += dot(p3, p3.yzx + 33.33);
  return fract((p3.x + p3.y) * p3.z);
}
float tNoise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  vec2 u = f * f * (3.0 - 2.0 * f);
  return mix(mix(tHash(i), tHash(i + vec2(1.0, 0.0)), u.x), mix(tHash(i + vec2(0.0, 1.0)), tHash(i + vec2(1.0, 1.0)), u.x), u.y);
}
float tFbm(vec2 p) {
  float v = 0.0;
  float a = 0.5;
  for (int i = 0; i < 5; i++) {
    v += a * tNoise(p);
    p = p * 2.03 + 17.1;
    a *= 0.5;
  }
  return v;
}

float southness(vec2 uv) {
  float vLine = uDivide[0].y;
  for (int i = 0; i < 9; i++) {
    vec2 a = uDivide[i];
    vec2 b = uDivide[i + 1];
    if (uv.x >= a.x && uv.x <= b.x) {
      vLine = mix(a.y, b.y, (uv.x - a.x) / max(b.x - a.x, 1e-4));
    }
  }
  if (uv.x > uDivide[9].x) vLine = uDivide[9].y;
  return smoothstep(-0.012, 0.03, uv.y - vLine);
}

vec3 albedoTactical(float elev, float slope, float sd, vec2 wm, float pxm) {
  // late-autumn fields around 寿春: stubble, straw, sprouting winter wheat, ploughed soil
  // field systems: each district keeps one orientation (no swirls), districts differ
  float district = tNoise(wm / 4600.0 + 7.3);
  float ang = district < 0.36 ? 0.22 : (district < 0.62 ? -0.38 : 0.95);
  mat2 R = mat2(cos(ang), -sin(ang), sin(ang), cos(ang));
  vec2 g = R * wm / vec2(340.0, 210.0);
  vec2 cell = floor(g);
  vec2 fc = fract(g);
  float rnd = tHash(cell);
  vec3 straw = vec3(0.70, 0.60, 0.38);
  vec3 stubble = vec3(0.60, 0.50, 0.32);
  vec3 wheat = vec3(0.47, 0.53, 0.29);
  vec3 plough = vec3(0.46, 0.36, 0.25);
  vec3 field = rnd < 0.34 ? straw : (rnd < 0.6 ? stubble : (rnd < 0.82 ? wheat : plough));
  field = mix(field, vec3(0.6, 0.53, 0.36), 0.35);
  field *= 0.92 + 0.14 * tNoise(wm / 48.0);
  vec2 edge = min(fc, 1.0 - fc) * vec2(340.0, 210.0);
  float border = 1.0 - smoothstep(0.0, 10.0, min(edge.x, edge.y));
  field = mix(field, field * 0.74, border * 0.55);
  float fieldVis = 1.0 - smoothstep(18.0, 46.0, pxm);
  vec3 broad = vec3(0.62, 0.55, 0.37) * (0.86 + 0.24 * tFbm(wm / 1800.0));
  vec3 plains = mix(broad, field, fieldVis * 0.8);
  // floodplain marsh (the later lakes of 城西湖、焦岗湖、瓦埠湖 were reed flats in the 4th c.)
  float wet = 1.0 - smoothstep(18.0, 20.6, elev);
  wet *= 0.7 + 0.3 * tNoise(wm / 260.0);
  vec3 marsh = mix(vec3(0.40, 0.43, 0.27), vec3(0.55, 0.50, 0.32), tNoise(wm / 70.0));
  plains = mix(plains, marsh, wet * 0.85);
  // hills: oak scrub in autumn colours, bare rock on the steepest slopes
  float hill = smoothstep(30.0, 62.0, elev);
  float n1 = tFbm(wm / 240.0);
  vec3 forest = mix(vec3(0.31, 0.35, 0.19), vec3(0.52, 0.33, 0.17), smoothstep(0.42, 0.72, n1));
  forest = mix(forest, vec3(0.62, 0.50, 0.25), smoothstep(0.62, 0.88, tFbm(wm / 110.0 + 3.1)) * 0.55);
  vec3 rock = vec3(0.57, 0.53, 0.47);
  vec3 hills = mix(forest, rock, smoothstep(0.62, 0.95, slope) * 0.45);
  vec3 col = mix(plains, hills, hill);
  // silt banks along rivers
  float bank = (1.0 - smoothstep(0.0, 140.0, sd)) * step(0.0, sd);
  col = mix(col, vec3(0.72, 0.66, 0.50), bank * 0.55);
  return col;
}

vec3 albedoStrategic(vec2 uv, float elev, float slope, float sd, vec2 wm) {
  float south = southness(uv);
  vec3 northPlain = vec3(0.72, 0.63, 0.44);
  vec3 southPlain = vec3(0.53, 0.57, 0.36);
  vec3 plain = mix(northPlain, southPlain, south);
  plain *= 0.9 + 0.2 * tFbm(wm / 38000.0);
  // loess plateau north of the Wei: brighter ochre
  float loess = (1.0 - south) * smoothstep(500.0, 1100.0, elev) * (1.0 - smoothstep(0.35, 0.7, slope));
  vec3 forest = mix(vec3(0.44, 0.42, 0.29), vec3(0.29, 0.37, 0.22), south);
  forest *= 0.82 + 0.3 * tFbm(wm / 11000.0);
  float hi = smoothstep(200.0, 800.0, elev) * smoothstep(0.12, 0.35, slope + 0.1);
  vec3 col = mix(plain, forest, hi);
  col = mix(col, vec3(0.78, 0.67, 0.45), loess * 0.75);
  vec3 rock = vec3(0.58, 0.54, 0.49);
  col = mix(col, rock, smoothstep(1600.0, 2700.0, elev) * 0.7);
  col = mix(col, rock, smoothstep(0.62, 0.92, slope) * 0.35);
  float snow = smoothstep(2650.0, 3200.0, elev + 350.0 * (tNoise(wm / 5000.0) - 0.5)) * (1.0 - smoothstep(0.55, 0.9, slope));
  col = mix(col, vec3(0.93, 0.93, 0.91), snow);
  float bank = (1.0 - smoothstep(0.0, 2600.0, sd)) * step(0.0, sd);
  col = mix(col, col * 1.08 + vec3(0.02, 0.02, 0.0), bank * 0.5);
  return col;
}
`;

// replaces <color_fragment>
export const terrainColorFragment = /* glsl */ `
vec2 tWm = vMapUv * uMapSize * uMetresPerWorld;           // metres from the NW corner
float tPxm = max(length(fwidth(tWm)), 0.001);               // metres per screen pixel
vec4 tNao = texture2D(uNormalAO, vMapUv);
vec3 tNormal = normalize(tNao.xyz * 2.0 - 1.0);
float tAO = tNao.a;
float tSlope = 1.0 - tNormal.y;
tSlope = clamp(tSlope * (uStrategic > 0.5 ? 3.0 : 4.5), 0.0, 1.0);
float tSd = (texture2D(uWater, vMapUv).r * 255.0 - 128.0) * uSdfScale;
float tAaW = max(fwidth(tSd) * 0.9, uSdfScale * 0.5);
float tWater = 1.0 - smoothstep(-tAaW, tAaW, tSd);
vec3 tLand = uStrategic > 0.5 ? albedoStrategic(vMapUv, vElev, tSlope, tSd, tWm) : albedoTactical(vElev, tSlope, tSd, tWm, tPxm);

// contours
float tCF = vElev / uContourStep;
float tCDf = fwidth(tCF);
float tCLine = 1.0 - smoothstep(0.0, tCDf * 1.5, abs(fract(tCF + 0.5) - 0.5));
float tCMajor = 1.0 - step(0.5, mod(floor(tCF + 0.5), 5.0));
float tCVis = uContours * (1.0 - smoothstep(0.18, 0.5, tCDf)) * smoothstep(uStrategic > 0.5 ? 120.0 : 26.0, uStrategic > 0.5 ? 260.0 : 40.0, vElev);
tLand = mix(tLand, tLand * 0.55, tCLine * tCVis * (0.28 + 0.4 * tCMajor));

// kilometre grid (方格)
if (uGrid > 0.0) {
  vec2 tGq = tWm / uGridStep;
  vec2 tGd = abs(fract(tGq + 0.5) - 0.5) / max(fwidth(tGq), vec2(1e-4));
  float tGl = 1.0 - smoothstep(0.0, 1.2, min(tGd.x, tGd.y));
  tLand = mix(tLand, tLand * 0.7 + vec3(0.03, 0.02, 0.0), tGl * uGrid * 0.55);
}

// territory wash (strategic)
if (uHasTerritory > 0.5) {
  vec4 tTerA = texture2D(uTerritory, vMapUv);
  vec4 tTerB = texture2D(uTerritoryB, vMapUv);
  vec4 tTer = mix(tTerA, tTerB, uTerritoryMix);
  vec3 tTint = uQinColor * tTer.r + uJinColor * tTer.g + vec3(0.56, 0.52, 0.6) * tTer.b;
  float tAmt = clamp(tTer.r + tTer.g + tTer.b, 0.0, 1.0);
  tLand = mix(tLand, tLand * (0.62 + 0.75 * tTint), 0.42 * tAmt);
  float tB = tTer.r + tTer.b - tTer.g;
  float tBw = max(fwidth(tB), 1e-4);
  float tBl = 1.0 - smoothstep(tBw * 0.6, tBw * 2.6, abs(tB));
  float tGlow = 1.0 - smoothstep(0.0, 0.22, abs(tB));
  tLand = mix(tLand, vec3(0.55, 0.16, 0.10), tGlow * 0.18 * tAmt);
  tLand = mix(tLand, vec3(0.30, 0.07, 0.05), tBl * 0.85 * step(0.05, tAmt));
}

// water
float tDepthM = max(-tSd, 0.0);
float tDeep = smoothstep(0.0, uStrategic > 0.5 ? 9000.0 : 170.0, tDepthM);
vec3 tWShallow = vec3(0.24, 0.42, 0.44);
vec3 tWDeep = vec3(0.07, 0.20, 0.26);
vec3 tWCol = mix(tWShallow, tWDeep, tDeep);
float tWt = uTime * 0.05;
float tRipple = tNoise(tWm / (uStrategic > 0.5 ? 3200.0 : 42.0) + vec2(tWt * 3.0, tWt * 1.7));
tWCol *= 0.92 + 0.12 * tRipple;
// 肥水为之不流: dark, churned water near the crossing
float tRt = uRiverTint.w * (1.0 - smoothstep(uRiverTint.z * 0.5, uRiverTint.z, distance(vMapUv * uMapSize, uRiverTint.xy * uMapSize)));
tWCol = mix(tWCol, vec3(0.24, 0.15, 0.11), tRt * 0.75);
float tFoam = tWater * (1.0 - smoothstep(0.0, uStrategic > 0.5 ? 1800.0 : 26.0, tDepthM)) * 0.35;
vec3 tAlbedo = mix(tLand, tWCol, tWater);
tAlbedo = mix(tAlbedo, vec3(0.86, 0.84, 0.78), tFoam * 0.4);

// focus tRing
float tHd = distance(vMapUv * uMapSize, uHighlight.xy * uMapSize) / max(uHighlight.z, 1e-3);
float tRing = (1.0 - smoothstep(0.9, 1.0, tHd)) * smoothstep(0.75, 0.97, tHd);
float tDisk = 1.0 - smoothstep(0.0, 1.0, tHd);
tAlbedo = mix(tAlbedo, tAlbedo * 1.12 + vec3(0.03, 0.025, 0.0), tDisk * uHighlight.w * 0.6);
tAlbedo = mix(tAlbedo, vec3(0.95, 0.82, 0.55), tRing * uHighlight.w * 0.35);

diffuseColor.rgb = tAlbedo;
`;

// replaces <normal_fragment_maps>
export const terrainNormalFragment = /* glsl */ `
vec3 tWn = tNormal;
if (tWater > 0.01) {
  float s = uStrategic > 0.5 ? 2600.0 : 30.0;
  vec2 tQ = tWm / s + vec2(uTime * 0.11, uTime * 0.07);
  float tE = 0.35;
  float tN0 = tNoise(tQ);
  float tNx = tNoise(tQ + vec2(tE, 0.0));
  float tNz = tNoise(tQ + vec2(0.0, tE));
  vec3 tWN = normalize(vec3((tN0 - tNx) * 0.35, 1.0, (tN0 - tNz) * 0.35));
  tWn = normalize(mix(tWn, tWN, tWater));
}
normal = normalize((viewMatrix * vec4(tWn, 0.0)).xyz);
`;

// replaces <roughnessmap_fragment>
export const terrainRoughnessFragment = /* glsl */ `
float roughnessFactor = mix(roughness, 0.32, tWater);
`;

// replaces <emissivemap_fragment>
export const terrainEmissiveFragment = /* glsl */ `
vec3 tViewDir = normalize(cameraPosition - vWPos);
float tFres = pow(1.0 - clamp(dot(tViewDir, vec3(0.0, 1.0, 0.0)), 0.0, 1.0), 3.0);
totalEmissiveRadiance += uSkyColor * tWater * (0.02 + 0.22 * tFres) * (1.0 - uNight * 0.6);
totalEmissiveRadiance += vec3(1.0, 0.8, 0.45) * tRing * uHighlight.w * 0.18;
`;

// after <aomap_fragment>
export const terrainAOFragment = /* glsl */ `
reflectedLight.indirectDiffuse *= mix(tAO, 1.0, tWater);
reflectedLight.directDiffuse *= mix(mix(0.55, 1.0, tAO), 1.0, tWater);
`;
