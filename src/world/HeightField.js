// Elevation and water-distance grids decoded from the packed WebP textures produced by
// tools/geodata.py. Sampling is bilinear in map UV space (u: west→east, v: north→south).

export async function loadImage(url) {
  const img = new Image();
  img.decoding = 'async';
  img.src = url;
  await img.decode();
  return img;
}

export function imageToPixels(img) {
  const canvas = document.createElement('canvas');
  canvas.width = img.naturalWidth;
  canvas.height = img.naturalHeight;
  const ctx = canvas.getContext('2d', { willReadFrequently: true });
  ctx.drawImage(img, 0, 0);
  return ctx.getImageData(0, 0, canvas.width, canvas.height);
}

export class HeightField {
  constructor(meta, heightPixels, waterPixels) {
    this.meta = meta;
    this.nx = heightPixels.width;
    this.ny = heightPixels.height;
    const n = this.nx * this.ny;
    const d = heightPixels.data;
    const h = new Float32Array(n);
    const { heightStep, heightMin } = meta;
    let lo = Infinity;
    let hi = -Infinity;
    for (let i = 0; i < n; i++) {
      const v = (d[i * 4] * 256 + d[i * 4 + 1]) * heightStep + heightMin;
      h[i] = v;
      if (v < lo) lo = v;
      if (v > hi) hi = v;
    }
    this.h = h;
    this.min = lo;
    this.max = hi;

    this.wnx = waterPixels.width;
    this.wny = waterPixels.height;
    const wd = waterPixels.data;
    const sdf = new Float32Array(this.wnx * this.wny);
    for (let i = 0; i < sdf.length; i++) sdf[i] = (wd[i * 4] - 128) * meta.sdfScale;
    this.sdf = sdf;
  }

  static bilinear(arr, w, h, u, v) {
    const x = Math.min(Math.max(u * (w - 1), 0), w - 1.0001);
    const y = Math.min(Math.max(v * (h - 1), 0), h - 1.0001);
    const x0 = x | 0;
    const y0 = y | 0;
    const fx = x - x0;
    const fy = y - y0;
    const i = y0 * w + x0;
    const a = arr[i];
    const b = arr[i + 1];
    const c = arr[i + w];
    const e = arr[i + w + 1];
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + e * fx) * fy;
  }

  /** Elevation in metres. */
  height(u, v) {
    return HeightField.bilinear(this.h, this.nx, this.ny, u, v);
  }

  /** Signed distance to the nearest water edge in metres (negative = in water). */
  water(u, v) {
    return HeightField.bilinear(this.sdf, this.wnx, this.wny, u, v);
  }
}
