import * as THREE from 'three';

export const DISPLAY_FONT = '"Ma Shan Zheng", "STKaiti", "KaiTi", "Kaiti SC", "BiauKai", serif';

const LIVERY = {
  jin: { field: ['#d2513a', '#9e2c1d'], edge: '#5a140c', text: '#f6e2a8', teeth: '#e2b866' },
  qin: { field: ['#4565b4', '#253a73'], edge: '#111b38', text: '#f1efe6', teeth: '#c9ccd6' },
  imperial: { field: ['#e0b04f', '#a8761f'], edge: '#4a2f08', text: '#3a1e05', teeth: '#f3d68c' },
  neutral: { field: ['#8a8f96', '#555a61'], edge: '#202328', text: '#f4f1ea', teeth: '#c9ccd6' },
};

/** Swallow-tailed war banner (牙旗) with the commander's name written vertically. */
export function makeFlagTexture(text, side, style) {
  const liv = LIVERY[style] || LIVERY[side] || LIVERY.neutral;
  const chars = [...text];
  const W = 128;
  const H = chars.length > 1 ? 210 : 150;
  const cv = document.createElement('canvas');
  cv.width = W;
  cv.height = H;
  const ctx = cv.getContext('2d');
  // body with toothed fly edge
  const teeth = 5;
  const bodyW = W - 18;
  ctx.beginPath();
  ctx.moveTo(0, 0);
  ctx.lineTo(bodyW, 0);
  for (let i = 0; i < teeth; i++) {
    const y0 = (i / teeth) * H;
    const y1 = ((i + 0.5) / teeth) * H;
    const y2 = ((i + 1) / teeth) * H;
    ctx.lineTo(bodyW, y0);
    ctx.lineTo(W, y1);
    ctx.lineTo(bodyW, y2);
  }
  ctx.lineTo(0, H);
  ctx.closePath();
  const grad = ctx.createLinearGradient(0, 0, 0, H);
  grad.addColorStop(0, liv.field[0]);
  grad.addColorStop(1, liv.field[1]);
  ctx.fillStyle = grad;
  ctx.fill();
  ctx.lineWidth = 6;
  ctx.strokeStyle = liv.teeth;
  ctx.stroke();
  // inner frame
  ctx.lineWidth = 3;
  ctx.strokeStyle = liv.edge;
  ctx.strokeRect(9, 9, bodyW - 18, H - 18);
  // characters
  const n = Math.max(1, chars.length);
  const size = n > 1 ? Math.min(82, (H - 30) / n) : 92;
  ctx.font = `${size}px ${DISPLAY_FONT}`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.lineJoin = 'round';
  chars.forEach((ch, i) => {
    const y = H / 2 + (i - (n - 1) / 2) * size * 0.98 + 2;
    ctx.lineWidth = 7;
    ctx.strokeStyle = liv.edge;
    ctx.strokeText(ch, bodyW / 2, y);
    ctx.fillStyle = liv.text;
    ctx.fillText(ch, bodyW / 2, y);
  });
  const tex = new THREE.CanvasTexture(cv);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 4;
  return tex;
}
