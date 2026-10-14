import { Path } from '../army/Path.js';

/**
 * Resolves data coordinates on one table: [lon, lat] pairs, place ids, and river references
 * of the form { river: 'huai', from: [lon, lat], to: [lon, lat] } that follow a river course.
 */
export function makeResolver(table, places) {
  const proj = table.proj;
  const rivers = {};
  for (const r of table.meta.rivers) {
    rivers[r.id] = new Path(r.pts.map(([lon, lat]) => proj.geoToWorld(lon, lat)));
  }
  const placeIndex = Object.fromEntries(places.map((p) => [p.id, p]));

  function point(p) {
    if (typeof p === 'string') {
      const pl = placeIndex[p];
      if (!pl) throw new Error(`unknown place ${p}`);
      return proj.geoToWorld(pl.at[0], pl.at[1]);
    }
    return proj.geoToWorld(p[0], p[1]);
  }

  function riverPts(ref) {
    const R = rivers[ref.river];
    if (!R) throw new Error(`unknown river ${ref.river}`);
    const a = point(ref.from);
    const b = point(ref.to);
    const s0 = R.closestS(a[0], a[1]);
    const s1 = R.closestS(b[0], b[1]);
    if (s0 <= s1) return R.slice(s0, s1).pts;
    return R.slice(s1, s0).pts.slice().reverse();
  }

  /** Expand a waypoint list into world points; `smooth` rounds coarse corners. */
  function path(list, { smooth = true } = {}) {
    const out = [];
    let hasRiver = false;
    for (const item of list) {
      if (item && item.river) {
        hasRiver = true;
        out.push(...riverPts(item));
      } else {
        out.push(point(item));
      }
    }
    return smooth && !hasRiver ? Path.smooth(out, 2) : out;
  }

  return { proj, rivers, point, path, places: placeIndex };
}
