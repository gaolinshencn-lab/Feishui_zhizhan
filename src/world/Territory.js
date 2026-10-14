import * as THREE from 'three';

// Approximate frontiers (lon, lat, west → east). North of the line belongs to the first side.
// 383: 前秦 holds 襄阳、淮北、梁益; 东晋 holds 淮南、荆州 and the Yangtze. 385: after 谢玄's
// northern campaign 东晋 reaches the Yellow River; the north splits into 后燕、后秦、西燕 etc.
export const FRONTIER_383 = [
  [106.8, 30.9], [108.4, 31.35], [109.6, 31.2], [110.6, 31.55], [111.3, 31.75], [111.9, 31.72], [112.6, 31.66],
  [113.2, 31.85], [113.9, 31.95], [114.6, 32.1], [115.3, 32.3], [115.9, 32.45], [116.3, 32.47], [116.52, 32.5],
  [116.68, 32.63], [116.76, 32.71], [117.0, 32.73], [117.3, 32.95], [117.75, 32.98], [118.2, 33.12], [118.6, 33.25],
  [118.9, 33.62], [119.3, 33.86], [119.9, 34.16], [121.6, 34.5],
];
export const FRONTIER_385 = [
  [106.8, 33.1], [108.5, 33.55], [109.6, 33.6], [110.6, 33.8], [111.3, 34.08], [112.0, 34.38], [112.45, 34.86],
  [113.0, 34.97], [113.6, 35.02], [114.3, 35.4], [114.8, 35.76], [115.4, 35.92], [116.0, 36.22], [116.7, 36.8],
];

/**
 * Paints territory masks into canvas textures for the strategic terrain shader:
 * R = 前秦, G = 东晋, B = the northern successor states (after the collapse).
 */
export function territoryTexture(proj, frontier, { northChannel = 'r', width = 1024 } = {}) {
  const W = width;
  const H = Math.round((width * proj.depth) / proj.width);
  const cv = document.createElement('canvas');
  cv.width = W;
  cv.height = H;
  const ctx = cv.getContext('2d');
  const toPx = ([lon, lat]) => {
    const [u, v] = proj.geoToUV(lon, lat);
    return [u * W, v * H];
  };
  const pts = frontier.map(toPx);
  const north = { r: '#ff0000', b: '#0000ff' }[northChannel];
  ctx.fillStyle = '#00ff00';
  ctx.fillRect(0, 0, W, H);
  ctx.filter = 'blur(1.5px)';
  ctx.beginPath();
  ctx.moveTo(pts[0][0], pts[0][1]);
  for (const p of pts.slice(1)) ctx.lineTo(p[0], p[1]);
  ctx.lineTo(W + 50, pts[pts.length - 1][1]);
  ctx.lineTo(W + 50, -50);
  ctx.lineTo(-50, -50);
  ctx.lineTo(-50, pts[0][1]);
  ctx.closePath();
  ctx.fillStyle = north;
  ctx.fill();
  const tex = new THREE.CanvasTexture(cv);
  tex.colorSpace = THREE.NoColorSpace;
  tex.flipY = false;
  tex.minFilter = THREE.LinearFilter;
  tex.generateMipmaps = false;
  return tex;
}
