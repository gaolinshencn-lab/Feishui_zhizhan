// Geographic ↔ world coordinates for one sand table.
// The table is centred on the origin, north = −Z, east = +X, up = +Y.
// Horizontal: equirectangular around the map centre. Vertical: metres × exaggeration.

export class MapProjection {
  constructor(meta, { worldWidth = 100, exaggeration = 8 } = {}) {
    this.meta = meta;
    const [lon0, lat0, lon1, lat1] = meta.bbox;
    Object.assign(this, { lon0, lat0, lon1, lat1 });
    this.kmToWorld = worldWidth / meta.widthKm;
    this.width = worldWidth;
    this.depth = meta.heightKm * this.kmToWorld;
    this.exaggeration = exaggeration;
    this.field = null; // HeightField, attached later
  }

  setExaggeration(e) {
    this.exaggeration = e;
  }

  /** world units per metre of elevation */
  get yScale() {
    return (this.kmToWorld / 1000) * this.exaggeration;
  }

  geoToUV(lon, lat) {
    return [(lon - this.lon0) / (this.lon1 - this.lon0), (this.lat1 - lat) / (this.lat1 - this.lat0)];
  }

  uvToWorld(u, v) {
    return [(u - 0.5) * this.width, (v - 0.5) * this.depth];
  }

  worldToUV(x, z) {
    return [x / this.width + 0.5, z / this.depth + 0.5];
  }

  geoToWorld(lon, lat) {
    const [u, v] = this.geoToUV(lon, lat);
    return this.uvToWorld(u, v);
  }

  worldToGeo(x, z) {
    const [u, v] = this.worldToUV(x, z);
    return [this.lon0 + u * (this.lon1 - this.lon0), this.lat1 - v * (this.lat1 - this.lat0)];
  }

  kmToWorldLen(km) {
    return km * this.kmToWorld;
  }

  /** Terrain elevation (metres) at a world position. */
  elevationAt(x, z) {
    const [u, v] = this.worldToUV(x, z);
    return this.field.height(u, v);
  }

  /** Terrain surface height (world Y) at a world position. */
  groundY(x, z) {
    return this.elevationAt(x, z) * this.yScale;
  }

  /** Signed distance to water in metres (negative inside water). */
  waterAt(x, z) {
    const [u, v] = this.worldToUV(x, z);
    return this.field.water(u, v);
  }

  inBounds(x, z, margin = 0) {
    return Math.abs(x) <= this.width / 2 - margin && Math.abs(z) <= this.depth / 2 - margin;
  }
}
