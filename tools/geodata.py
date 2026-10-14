#!/usr/bin/env python3
"""
Build the terrain and hydrography assets for the Feishui (淝水) battle model.

Outputs (written to src/assets/terrain and src/data/geo):
  <map>-height.webp  lossless RGB: R/G = 16-bit elevation (B unused)
  <map>-water.webp   lossless 8-bit signed distance to the nearest water edge
  <map>.json         projection + encoding metadata, river polylines for labels

Sources:
  * Elevation: AWS Terrain Tiles (Terrarium encoding; SRTM/GMTED/ETOPO1 mosaic)
  * Battlefield rivers: OpenStreetMap (via Overpass, cached in tools/.cache/osm)
  * Strategic rivers/lakes: Natural Earth 10m + hand-traced historical courses
    (lower Huai before 1194, 泗水, 邗沟, 颍水/汝水/涡水 upper reaches, 4th-century
    Jiangsu coastline). Modern reservoirs and post-Song lakes are excluded.

Run:  python3 tools/geodata.py           (uses cached downloads where present)
"""
from __future__ import annotations

import json
import math
import os
import sys
import urllib.request
import concurrent.futures as cf
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "tools" / ".cache"
OUT_TEX = ROOT / "src" / "assets" / "terrain"
OUT_GEO = ROOT / "src" / "data" / "geo"

TILE_URL = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
OVERPASS = "https://maps.mail.ru/osm/tools/overpass/api/interpreter"

# ---------------------------------------------------------------------------
# Map definitions
# ---------------------------------------------------------------------------
MAPS = {
    "tactical": dict(
        bbox=(116.42, 32.38, 117.30, 32.82),  # lon0, lat0, lon1, lat1
        zoom=12,
        nx=1024,
        water_nx=2048,
        sdf_scale=4.0,  # metres per SDF step
        ao_exaggeration=9.0,
        height_step=0.1,
    ),
    "strategic": dict(
        bbox=(107.5, 29.6, 121.0, 36.55),
        zoom=8,
        nx=1350,
        water_nx=2700,
        sdf_scale=60.0,
        ao_exaggeration=7.0,
        height_step=1.0,
    ),
}


def proj_params(bbox):
    lon0, lat0, lon1, lat1 = bbox
    lat_c = (lat0 + lat1) / 2
    lon_c = (lon0 + lon1) / 2
    kx = 111.320 * math.cos(math.radians(lat_c))  # km per degree lon
    kz = 110.574 + 1.11 * (lat_c / 90.0)  # km per degree lat (good to ~0.1%)
    width_km = (lon1 - lon0) * kx
    height_km = (lat1 - lat0) * kz
    return dict(lonC=lon_c, latC=lat_c, kx=kx, kz=kz, widthKm=width_km, heightKm=height_km)


# ---------------------------------------------------------------------------
# Elevation tiles
# ---------------------------------------------------------------------------
def lon2x(lon, z):
    return (np.asarray(lon) + 180.0) / 360.0 * (2 ** z)


def lat2y(lat, z):
    r = np.radians(np.asarray(lat))
    return (1 - np.log(np.tan(r) + 1 / np.cos(r)) / np.pi) / 2 * (2 ** z)


def tile_range(bbox, z):
    lon0, lat0, lon1, lat1 = bbox
    x0, x1 = int(lon2x(lon0, z)), int(lon2x(lon1, z))
    y0, y1 = int(lat2y(lat1, z)), int(lat2y(lat0, z))
    return x0, x1, y0, y1


def fetch_tiles(bbox, z):
    (CACHE / "tiles").mkdir(parents=True, exist_ok=True)
    x0, x1, y0, y1 = tile_range(bbox, z)
    jobs = [(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)]

    def get(xy):
        x, y = xy
        fn = CACHE / "tiles" / f"{z}_{x}_{y}.png"
        if fn.exists() and fn.stat().st_size > 100:
            return
        url = TILE_URL.format(z=z, x=x, y=y)
        last = None
        for _ in range(4):
            try:
                with urllib.request.urlopen(url, timeout=40) as r:
                    fn.write_bytes(r.read())
                return
            except Exception as e:  # pragma: no cover - network
                last = e
        raise last

    with cf.ThreadPoolExecutor(8) as ex:
        list(ex.map(get, jobs))
    return x0, x1, y0, y1


def sample_elevation(bbox, z, nx, ny):
    x0, x1, y0, y1 = fetch_tiles(bbox, z)
    W, H = (x1 - x0 + 1) * 256, (y1 - y0 + 1) * 256
    mosaic = np.zeros((H, W), np.float32)
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            a = np.asarray(Image.open(CACHE / "tiles" / f"{z}_{x}_{y}.png").convert("RGB")).astype(np.float32)
            mosaic[(y - y0) * 256:(y - y0 + 1) * 256, (x - x0) * 256:(x - x0 + 1) * 256] = (
                a[..., 0] * 256 + a[..., 1] + a[..., 2] / 256 - 32768
            )
    lon0, lat0, lon1, lat1 = bbox
    lons = np.linspace(lon0, lon1, nx)
    lats = np.linspace(lat1, lat0, ny)  # row 0 = north
    px = (lon2x(lons, z) - x0) * 256 - 0.5
    py = (lat2y(lats, z) - y0) * 256 - 0.5
    PX, PY = np.meshgrid(px, py)
    return ndimage.map_coordinates(mosaic, [PY, PX], order=1, mode="nearest").astype(np.float32)


# ---------------------------------------------------------------------------
# Geometry helpers (lon/lat <-> pixel grid)
# ---------------------------------------------------------------------------
class Grid:
    def __init__(self, bbox, nx, ny):
        self.bbox, self.nx, self.ny = bbox, nx, ny
        lon0, lat0, lon1, lat1 = bbox
        self.lon0, self.lat0, self.lon1, self.lat1 = lon0, lat0, lon1, lat1
        p = proj_params(bbox)
        self.px_m = p["widthKm"] * 1000 / (nx - 1)  # metres per pixel (x)
        self.py_m = p["heightKm"] * 1000 / (ny - 1)

    def to_px(self, lon, lat):
        x = (lon - self.lon0) / (self.lon1 - self.lon0) * (self.nx - 1)
        y = (self.lat1 - lat) / (self.lat1 - self.lat0) * (self.ny - 1)
        return x, y


def chaikin(pts, iterations=2):
    pts = list(pts)
    for _ in range(iterations):
        if len(pts) < 3:
            return pts
        out = [pts[0]]
        for a, b in zip(pts[:-1], pts[1:]):
            out.append((0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]))
            out.append((0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1]))
        out.append(pts[-1])
        pts = out
    return pts


def simplify(pts, tol):
    """Douglas–Peucker on (lon, lat) tuples; tol in degrees."""
    if len(pts) < 3:
        return list(pts)
    a, b = np.array(pts[0]), np.array(pts[-1])
    ab = b - a
    L = np.hypot(*ab) or 1e-12
    best, idx = -1.0, 0
    for i in range(1, len(pts) - 1):
        p = np.array(pts[i])
        d = abs(ab[0] * (a[1] - p[1]) - ab[1] * (a[0] - p[0])) / L
        if d > best:
            best, idx = d, i
    if best > tol:
        return simplify(pts[: idx + 1], tol)[:-1] + simplify(pts[idx:], tol)
    return [pts[0], pts[-1]]


def clip_to_bbox(pts, bbox, margin=0.02):
    lon0, lat0, lon1, lat1 = bbox
    keep = [
        (lon, lat)
        for lon, lat in pts
        if lon0 - margin <= lon <= lon1 + margin and lat0 - margin <= lat <= lat1 + margin
    ]
    return keep


# ---------------------------------------------------------------------------
# OSM rivers for the battlefield map
# ---------------------------------------------------------------------------
def load_osm_tactical():
    fn = CACHE / "osm" / "tactical_rivers.json"
    if not fn.exists():
        fn.parent.mkdir(parents=True, exist_ok=True)
        q = (
            '[out:json][timeout:100];(way["waterway"~"river|canal"](32.30,116.30,33.00,117.40);'
            'relation["waterway"="river"](32.30,116.30,33.00,117.40););out geom;'
        )
        req = urllib.request.Request(
            OVERPASS,
            data=("data=" + urllib.parse.quote(q)).encode(),
            headers={"User-Agent": "feishui-model/1.0"},
        )
        with urllib.request.urlopen(req, timeout=180) as r:
            fn.write_bytes(r.read())
    d = json.loads(fn.read_text())
    ways = {}
    for e in d["elements"]:
        if e["type"] == "way":
            ways[e["id"]] = [(p["lon"], p["lat"]) for p in e["geometry"]]
    return ways


def chain(ways, ids, joins=()):
    pts = []
    for wid in ids:
        seg = ways[wid]
        if pts and np.hypot(pts[-1][0] - seg[-1][0], pts[-1][1] - seg[-1][1]) < np.hypot(
            pts[-1][0] - seg[0][0], pts[-1][1] - seg[0][1]
        ):
            seg = seg[::-1]
        pts.extend(seg if not pts else seg[1:])
    return pts


def tactical_rivers():
    w = load_osm_tactical()
    huai = chain(w, [695876608, 652019347, 652019350, 50193933, 652019366, 652019369, 773008630, 652019377, 652019374, 36888121])
    ying = chain(w, [652019362, 161687846])
    fei = chain(w, [50218312, 395742007])
    # 洛涧: 洛河 from the east joins 窑河 which flows north to 洛口 on the Huai.
    luo_lower = chain(w, [1056917816, 1040665114])
    luo_east = chain(w, [263791446])
    gaotang_out = chain(w, [447386969, 203777195])
    pi = chain(w, [50212773])
    xifei = chain(w, [50196600, 50239479])

    rivers = [
        dict(id="huai", name="淮水", modern="淮河", pts=huai, width=(420, 520), kind="major", label_at=[0.36, 0.78]),
        dict(id="ying", name="颍水", modern="沙颍河", pts=ying, width=(200, 220), kind="river", label_at=[0.4]),
        dict(id="fei", name="淝水", modern="东淝河", pts=fei, width=(150, 230), kind="river", label_at=[0.62, 0.93]),
        dict(id="luojian", name="洛涧", modern="窑河", pts=luo_lower, width=(120, 170), kind="river", label_at=[0.55]),
        dict(id="luojian_e", name="洛涧", modern="洛河", pts=luo_east, width=(70, 110), kind="minor", label_at=[]),
        dict(id="gaotang", name="", modern="窑河上游", pts=gaotang_out + [luo_lower[0]], width=(70, 90), kind="minor", label_at=[]),
        dict(id="pi", name="沘水", modern="淠河", pts=pi, width=(130, 160), kind="river", label_at=[0.5]),
        dict(id="xifei", name="夏肥水", modern="西淝河", pts=xifei, width=(90, 120), kind="minor", label_at=[0.6]),
    ]
    return rivers


# ---------------------------------------------------------------------------
# Strategic hydrography
# ---------------------------------------------------------------------------
def load_ne_rivers():
    import shapefile

    r = shapefile.Reader(str(CACHE / "ne" / "rivers" / "ne_10m_rivers_lake_centerlines.shp"))
    flds = [f[0] for f in r.fields[1:]]
    out = {}
    for sr in r.iterShapeRecords():
        rec = dict(zip(flds, sr.record))
        name = rec.get("name")
        parts = list(sr.shape.parts) + [len(sr.shape.points)]
        for a, b in zip(parts[:-1], parts[1:]):
            out.setdefault(name, []).append([tuple(p) for p in sr.shape.points[a:b]])
    return out


def load_ne_lakes(names):
    import shapefile

    r = shapefile.Reader(str(CACHE / "ne" / "lakes" / "ne_10m_lakes.shp"))
    flds = [f[0] for f in r.fields[1:]]
    out = []
    for sr in r.iterShapeRecords():
        rec = dict(zip(flds, sr.record))
        if rec.get("name") in names:
            parts = list(sr.shape.parts) + [len(sr.shape.points)]
            rings = [[tuple(p) for p in sr.shape.points[a:b]] for a, b in zip(parts[:-1], parts[1:])]
            out.append(dict(name=names[rec["name"]], rings=rings))
    return out


def merge_parts(parts, bbox, start, tol=0.08):
    """Chain Natural Earth parts into one polyline, starting from the part nearest `start`.

    Parts are attached only when their endpoints meet (within `tol` degrees), which keeps
    unrelated rivers with the same name (e.g. the Korean Han) and stray side channels out.
    """
    lon0, lat0, lon1, lat1 = bbox
    pool = [p for p in parts if len(p) >= 5]
    pool = [p for p in pool if any(lon0 - 3 <= x <= lon1 + 3 and lat0 - 3 <= y <= lat1 + 3 for x, y in p)]

    def dist(a, b):
        return math.hypot(a[0] - b[0], a[1] - b[1])

    first = min(pool, key=lambda p: min(dist(p[0], start), dist(p[-1], start)))
    pool.remove(first)
    line = first if dist(first[0], start) <= dist(first[-1], start) else first[::-1]
    while pool:
        cand = None
        for p in pool:
            for q in (p, p[::-1]):
                d = dist(line[-1], q[0])
                if d < tol and (cand is None or d < cand[0]):
                    cand = (d, p, q)
        if cand is None:
            break
        pool.remove(cand[1])
        line = line + cand[2][1:]
    return clip_to_bbox(line, bbox, margin=0.6)


def strategic_rivers():
    ne = load_ne_rivers()
    bbox = MAPS["strategic"]["bbox"]
    # Yellow River: NE from the Ordos loop down the 晋陕 canyon to 潼关, east to 荥阳 (石门),
    # then the Eastern-Han (王景) course used until 1048 instead of the modern channel.
    huang_ne = merge_parts(ne["Huang"], bbox, start=(97.76, 35.09))
    huang_west = [p for p in huang_ne if p[0] <= 113.45]
    huang_hist = [
        (113.45, 34.93), (113.70, 35.00), (113.95, 35.10), (114.20, 35.28), (114.42, 35.48),
        (114.55, 35.60), (114.80, 35.70), (115.05, 35.76), (115.35, 35.85), (115.65, 35.98),
        (115.95, 36.16), (116.20, 36.36), (116.40, 36.62),
    ]
    huang = huang_west + huang_hist

    wei = merge_parts(ne["Wei"], bbox, start=(104.06, 35.0))
    jing = merge_parts(ne["Jing"], bbox, start=(106.42, 35.56))
    han = merge_parts(ne["Han"], bbox, start=(106.4, 33.07))
    yangtze = merge_parts(ne["Chang Jiang"] + ne["Yangtze"], bbox, start=(103.85, 28.67))
    yangtze = [p for p in yangtze if p[0] <= 119.62]

    huai_ne = merge_parts(ne["Huai"], bbox, start=(113.72, 32.42))
    huai_ne = [p for p in huai_ne if p[0] < 116.50]
    osm = load_osm_tactical()
    huai_mid = chain(osm, [652019350, 50193933, 652019366, 652019369, 773008630, 652019377, 652019374, 36888121])
    huai_mid = [p for p in huai_mid if p[0] >= 116.50]
    huai_low = [  # course before the Yellow River captured the Huai (1194): through the later Hongze basin to the sea
        (118.05, 33.06), (118.30, 33.00), (118.52, 33.00), (118.68, 33.14), (118.80, 33.32),
        (118.92, 33.50), (119.02, 33.60), (119.16, 33.64), (119.30, 33.77), (119.48, 33.92),
        (119.66, 34.04), (119.86, 34.13),
    ]
    huai = huai_ne + huai_mid + huai_low

    ying_ne = merge_parts(ne["Ying"], bbox, start=(115.56, 33.2))
    ying_up = [
        (113.02, 34.46), (113.22, 34.33), (113.48, 34.16), (113.72, 33.98), (113.95, 33.82),
        (114.25, 33.76), (114.52, 33.73), (114.66, 33.62), (114.86, 33.50), (115.10, 33.40),
        (115.36, 33.27),
    ]
    ying = ying_up + [p for p in ying_ne if p[0] > 115.40]

    ru = [  # 汝水 (northern Ru + ancient lower course to 汝口)
        (112.10, 34.14), (112.45, 34.20), (112.84, 34.17), (113.20, 33.97), (113.48, 33.85),
        (113.75, 33.70), (114.00, 33.58), (114.18, 33.38), (114.30, 33.18), (114.40, 33.00),
        (114.70, 32.86), (114.98, 32.74), (115.20, 32.58), (115.40, 32.47),
    ]
    guo = [  # 涡水
        (114.45, 34.62), (114.66, 34.40), (114.85, 34.10), (115.18, 33.95), (115.48, 33.86),
        (115.78, 33.85), (116.00, 33.68), (116.22, 33.50), (116.48, 33.30), (116.75, 33.18),
        (117.00, 33.05), (117.19, 32.96),
    ]
    si = [  # 泗水 (pre-Yellow-River-capture course)
        (116.92, 35.60), (116.80, 35.30), (116.85, 35.00), (116.93, 34.72), (117.05, 34.48),
        (117.19, 34.27), (117.42, 34.15), (117.70, 34.06), (117.95, 34.05), (118.28, 33.95),
        (118.62, 33.76), (118.92, 33.60),
    ]
    luo = [  # 洛水 through Luoyang
        (110.80, 34.05), (111.15, 34.15), (111.62, 34.38), (112.10, 34.50), (112.45, 34.65),
        (112.80, 34.73), (113.02, 34.80), (113.08, 34.86),
    ]
    hangou = [  # 邗沟 (canal Guangling → 末口)
        (119.43, 32.33), (119.44, 32.55), (119.45, 32.78), (119.38, 33.02), (119.31, 33.24),
        (119.22, 33.45), (119.16, 33.62),
    ]
    fei = [  # 淝水 (strategic, simplified)
        (117.27, 31.86), (117.12, 32.02), (116.98, 32.22), (116.92, 32.40), (116.88, 32.52),
        (116.82, 32.585), (116.76, 32.61), (116.742, 32.626),
    ]
    shi = [(117.27, 31.86), (117.36, 31.76), (117.45, 31.66)]  # 施水 合肥→巢湖
    ruxu = [(117.85, 31.55), (117.92, 31.42), (118.02, 31.30)]  # 濡须水 巢湖→江

    rivers = [
        dict(id="huang", name="河", modern="黄河", pts=huang, width=(3600, 4200), kind="major", label_at=[0.2, 0.62]),
        dict(id="yangtze", name="江", modern="长江", pts=yangtze, width=(4200, 6500), kind="major", label_at=[0.3, 0.78]),
        dict(id="huai", name="淮水", modern="淮河", pts=huai, width=(2600, 3600), kind="major", label_at=[0.25, 0.83]),
        dict(id="han", name="沔水", modern="汉水", pts=han, width=(2000, 2800), kind="river", label_at=[0.3, 0.75]),
        dict(id="wei", name="渭水", modern="渭河", pts=wei, width=(1600, 2000), kind="river", label_at=[0.45]),
        dict(id="jing", name="泾水", modern="泾河", pts=jing, width=(1100, 1300), kind="minor", label_at=[]),
        dict(id="luo", name="洛水", modern="洛河", pts=luo, width=(1200, 1400), kind="river", label_at=[0.4]),
        dict(id="ying", name="颍水", modern="颍河", pts=ying, width=(1400, 1900), kind="river", label_at=[0.42]),
        dict(id="ru", name="汝水", modern="汝河", pts=ru, width=(1200, 1600), kind="river", label_at=[0.55]),
        dict(id="guo", name="涡水", modern="涡河", pts=guo, width=(1200, 1600), kind="river", label_at=[0.5]),
        dict(id="si", name="泗水", modern="泗河故道", pts=si, width=(1200, 1700), kind="river", label_at=[0.35]),
        dict(id="hangou", name="邗沟", modern="里运河", pts=hangou, width=(900, 1000), kind="canal", label_at=[0.5]),
        dict(id="fei", name="淝水", modern="东淝河", pts=fei, width=(1000, 1200), kind="minor", label_at=[0.45]),
        dict(id="shi", name="施水", modern="南淝河", pts=shi, width=(900, 1000), kind="minor", label_at=[]),
        dict(id="ruxu", name="濡须水", modern="裕溪河", pts=ruxu, width=(900, 1000), kind="minor", label_at=[]),
    ]
    lakes = load_ne_lakes({"Chao Hu": "巢湖", "Tai Hu": "太湖", "Shijiu Hu": "丹阳湖"})
    # 芍陂 (安丰塘) — the Chu-era reservoir south of Shouchun, "周百二十许里"
    cx, cy = 116.70, 32.30
    shaopi = [(cx + 0.075 * math.cos(t) - 0.02 * math.sin(t) ** 3, cy + 0.052 * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 40)]
    lakes.append(dict(name="芍陂", rings=[shaopi]))
    return rivers, lakes


# Historical coastline (approx. 4th century): sea lay roughly along the later 范公堤 line,
# with the Huai mouth near 云梯关 and 郁洲 (云台山) still an island.
EXTRA_SEA = [
    (119.20, 34.88), (119.30, 34.70), (119.42, 34.52), (119.62, 34.30), (119.80, 34.15),
    (119.90, 34.05), (119.84, 33.85), (119.92, 33.66), (120.08, 33.48), (120.18, 33.30),
    (120.27, 33.08), (120.31, 32.86), (120.40, 32.66), (120.52, 32.45), (120.68, 32.25),
    (120.84, 32.08), (121.30, 31.95), (121.60, 32.00), (121.60, 35.20), (119.20, 35.20),
]
YUZHOU_ISLAND = [(119.22, 34.66), (119.35, 34.73), (119.48, 34.70), (119.43, 34.60), (119.30, 34.58)]


# ---------------------------------------------------------------------------
# Rasterisation
# ---------------------------------------------------------------------------
def polyline_sdf(rivers, grid: Grid):
    """Signed distance (metres) to the union of variable-width river ribbons."""
    nx, ny = grid.nx, grid.ny
    center = np.zeros((ny, nx), bool)
    width_r = np.zeros((ny, nx), np.float32)
    img_w = Image.new("F", (nx, ny), 0.0)
    img_c = Image.new("1", (nx, ny), 0)
    dw = ImageDraw.Draw(img_w)
    dc = ImageDraw.Draw(img_c)
    for r in rivers:
        pts = chaikin(r["pts"], 2)
        n = len(pts)
        w0, w1 = r["width"]
        for i in range(n - 1):
            a = grid.to_px(*pts[i])
            b = grid.to_px(*pts[i + 1])
            w = w0 + (w1 - w0) * (i / max(1, n - 2))
            dw.line([a, b], fill=float(w), width=1)
            dc.line([a, b], fill=1, width=1)
    center = np.asarray(img_c, dtype=bool)
    width_r = np.asarray(img_w, dtype=np.float32)
    if not center.any():
        return np.full((ny, nx), 1e6, np.float32)
    # anisotropic pixel sizes
    dist, inds = ndimage.distance_transform_edt(~center, sampling=(grid.py_m, grid.px_m), return_indices=True)
    w = width_r[inds[0], inds[1]]
    return (dist - w / 2).astype(np.float32)


def polygon_mask(polys, grid: Grid, holes=()):
    img = Image.new("L", (grid.nx, grid.ny), 0)
    d = ImageDraw.Draw(img)
    for ring in polys:
        d.polygon([grid.to_px(*p) for p in ring], fill=255)
    for ring in holes:
        d.polygon([grid.to_px(*p) for p in ring], fill=0)
    return np.asarray(img) > 127


def mask_sdf(mask, grid: Grid):
    if not mask.any():
        return np.full(mask.shape, 1e6, np.float32)
    outside = ndimage.distance_transform_edt(~mask, sampling=(grid.py_m, grid.px_m))
    inside = ndimage.distance_transform_edt(mask, sampling=(grid.py_m, grid.px_m))
    return (outside - inside).astype(np.float32)


def resample(a, ny, nx, order=1):
    zy, zx = ny / a.shape[0], nx / a.shape[1]
    return ndimage.zoom(a, (zy, zx), order=order)


def ambient_occlusion(h, px_m, py_m, exaggeration, radius_px=24, dirs=12):
    he = h * exaggeration
    ny, nx = h.shape
    occ = np.zeros_like(h)
    for k in range(dirs):
        ang = 2 * math.pi * k / dirs
        dx, dy = math.cos(ang), math.sin(ang)
        horizon = np.full_like(h, -1e9)
        for s in (1, 2, 3, 4, 6, 8, 11, 15, 20, 24, 32, 40):
            if s > radius_px * 1.7:
                break
            ox, oy = dx * s, dy * s
            shifted = ndimage.shift(he, (-oy, -ox), order=1, mode="nearest")
            dist = math.hypot(ox * px_m, oy * py_m)
            horizon = np.maximum(horizon, (shifted - he) / dist)
        occ += np.clip(np.arctan(horizon) / (math.pi / 2), 0, 1)
    occ /= dirs
    ao = 1.0 - 1.6 * occ
    return np.clip(ao, 0.25, 1.0)


def encode_height(h, lo, step):
    v = np.clip(np.round((h - lo) / step), 0, 65535).astype(np.uint32)
    return (v >> 8).astype(np.uint8), (v & 255).astype(np.uint8)


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
def water_level_along(rivers, h, grid: Grid, base=None):
    """Assign each river vertex a smoothed, non-increasing water level (m)."""
    for r in rivers:
        pts = chaikin(r["pts"], 1)
        lv = []
        for lon, lat in pts:
            x, y = grid.to_px(lon, lat)
            xi, yi = int(round(x)), int(round(y))
            r_px = 3
            y0, y1 = max(0, yi - r_px), min(grid.ny, yi + r_px + 1)
            x0, x1 = max(0, xi - r_px), min(grid.nx, xi + r_px + 1)
            if y0 >= y1 or x0 >= x1:
                lv.append(np.nan)
                continue
            lv.append(float(np.percentile(h[y0:y1, x0:x1], 15)))
        lv = np.array(lv)
        if np.all(np.isnan(lv)):
            lv[:] = base if base is not None else 0
        lv = np.where(np.isnan(lv), np.nanmedian(lv), lv)
        lv = np.minimum.accumulate(lv)  # rivers do not flow uphill
        lv = ndimage.uniform_filter1d(lv, size=9, mode="nearest")
        r["_pts1"] = pts
        r["_levels"] = lv


def build_map(name, rivers, lakes, extra_sea=None, sea_holes=()):
    cfg = MAPS[name]
    bbox = cfg["bbox"]
    p = proj_params(bbox)
    nx = cfg["nx"]
    ny = int(round(nx * p["heightKm"] / p["widthKm"]))
    print(f"[{name}] grid {nx}x{ny}, {p['widthKm']:.1f} x {p['heightKm']:.1f} km")
    h = sample_elevation(bbox, cfg["zoom"], nx, ny)
    grid = Grid(bbox, nx, ny)

    # --- clean-up -----------------------------------------------------------
    if name == "tactical":
        med = ndimage.median_filter(h, size=25)
        pits = h < med - 3.0  # mining subsidence lakes, quarries
        h = np.where(pits, med - 0.5, h)
        smooth = ndimage.gaussian_filter(h, 3.5)
        light = ndimage.gaussian_filter(h, 1.0)
        plain = np.clip((h - 30.0) / 25.0, 0, 1)  # 0 on the plain, 1 on hills
        h = smooth * (1 - plain) + light * plain
    else:
        h = ndimage.gaussian_filter(h, 0.7)

    # --- water ------------------------------------------------------------------
    wgrid = Grid(bbox, cfg["water_nx"], int(round(cfg["water_nx"] * ny / nx)))
    sd_r = polyline_sdf(rivers, wgrid)
    lake_rings = [ring for lk in lakes for ring in lk["rings"]]
    sd_l = mask_sdf(polygon_mask(lake_rings, wgrid), wgrid) if lake_rings else np.full_like(sd_r, 1e6)
    sd = np.minimum(sd_r, sd_l)
    sea_low = None
    if name == "strategic":
        # sea = low elevation connected to the eastern ocean + historical additions
        hw = resample(h, wgrid.ny, wgrid.nx)
        low = hw < 0.5
        lab, _ = ndimage.label(low)
        ocean_ids = set(np.unique(lab[:, -1])) | set(np.unique(lab[-1, -40:]))
        ocean_ids.discard(0)
        sea = np.isin(lab, list(ocean_ids))
        if extra_sea:
            sea |= polygon_mask([extra_sea], wgrid, holes=sea_holes)
        sea = ndimage.binary_opening(sea, iterations=2)
        sd = np.minimum(sd, mask_sdf(sea, wgrid))
        sea_low = resample(sea.astype(np.float32), ny, nx) > 0.5

    # --- carve channels into the heightmap ---------------------------------------
    sd_h = resample(sd, ny, nx)
    water_level_along(rivers, h, grid)
    # nearest-vertex level map
    lv_img = np.zeros((ny, nx), np.float32)
    has = np.zeros((ny, nx), bool)
    for r in rivers:
        for (lon, lat), lv in zip(r["_pts1"], r["_levels"]):
            x, y = grid.to_px(lon, lat)
            xi, yi = int(round(x)), int(round(y))
            if 0 <= xi < nx and 0 <= yi < ny:
                lv_img[yi, xi] = lv
                has[yi, xi] = True
    if has.any():
        _, inds = ndimage.distance_transform_edt(~has, return_indices=True)
        level = lv_img[inds[0], inds[1]]
    else:
        level = np.zeros_like(h)
    if name == "strategic":
        level = np.where(sea_low, 0.0, level)
        lake_level = ndimage.minimum_filter(h, size=5)
        level = np.where(sd_h < 0, np.minimum(level, lake_level + 0.0), level)
    bank = 5.0 * grid.px_m if name == "tactical" else 2.0 * grid.px_m
    depth = 4.0 if name == "tactical" else 25.0
    carve_in = level - depth * np.clip(-sd_h / 300.0 if name == "tactical" else -sd_h / 2000.0, 0.25, 1.0)
    carve_bank = level - 0.3 + np.clip(sd_h, 0, None) / bank * np.maximum(h - level, 0)
    h = np.where(sd_h < 0, np.minimum(h, carve_in), np.where(sd_h < bank, np.minimum(h, carve_bank), h))
    if name == "strategic":
        h = np.where(sea_low, np.minimum(h, -8.0), h)

    # --- encode -------------------------------------------------------------------
    lo = math.floor(float(h.min())) - 1
    hi = math.ceil(float(h.max())) + 1
    step = max(cfg["height_step"], (hi - lo) / 65000.0)
    R, G = encode_height(h, lo, step)
    OUT_TEX.mkdir(parents=True, exist_ok=True)
    # lossless WebP is ~40% smaller than PNG for this data; B is left empty (AO is baked on the GPU)
    Image.fromarray(np.dstack([R, G, np.zeros_like(R)]), "RGB").save(
        OUT_TEX / f"{name}-height.webp", lossless=True, quality=100, method=6
    )
    sdv = np.clip(np.round(128 + sd / cfg["sdf_scale"]), 0, 255).astype(np.uint8)
    Image.fromarray(np.dstack([sdv, sdv, sdv]), "RGB").save(
        OUT_TEX / f"{name}-water.webp", lossless=True, quality=100, method=6
    )

    meta = dict(
        name=name,
        bbox=bbox,
        nx=nx,
        ny=ny,
        waterNx=wgrid.nx,
        waterNy=wgrid.ny,
        heightMin=lo,
        heightStep=step,
        elevationRange=[float(h.min()), float(h.max())],
        sdfScale=cfg["sdf_scale"],
        **p,
        rivers=[
            dict(
                id=r["id"],
                name=r["name"],
                modern=r["modern"],
                kind=r["kind"],
                width=r["width"],
                labelAt=r["label_at"],
                pts=[[round(a, 5), round(b, 5)] for a, b in simplify(chaikin(r["pts"], 1), 0.0015 if name == "tactical" else 0.02)],
            )
            for r in rivers
        ],
        lakes=[dict(name=lk["name"], center=list(np.mean(np.array(lk["rings"][0]), axis=0).round(4))) for lk in lakes],
    )
    OUT_GEO.mkdir(parents=True, exist_ok=True)
    (OUT_GEO / f"{name}.json").write_text(json.dumps(meta, ensure_ascii=False, separators=(",", ":")))
    sizes = {f: os.path.getsize(OUT_TEX / f) for f in (f"{name}-height.webp", f"{name}-water.webp")}
    print(f"[{name}] elevation {h.min():.1f}..{h.max():.1f} m, files {sizes}")
    return h, sd


def main():
    import urllib.parse  # noqa: F401  (used by load_osm_tactical)

    which = sys.argv[1:] or ["tactical", "strategic"]
    if "tactical" in which:
        build_map("tactical", tactical_rivers(), [])
    if "strategic" in which:
        rivers, lakes = strategic_rivers()
        build_map("strategic", rivers, lakes, extra_sea=EXTRA_SEA, sea_holes=[YUZHOU_ISLAND])


if __name__ == "__main__":
    import urllib.parse

    main()
