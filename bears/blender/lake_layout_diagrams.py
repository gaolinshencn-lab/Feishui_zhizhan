# -*- coding: utf-8 -*-
"""湖泊结构草图：平面图（等深线）和“沙滩—湖心—石崖”剖面图。数据直接取自建模脚本的 ground()/lake_bed()，和 .blend 一致。

两步：
  1. blender -b --factory-startup -P lake_layout_diagrams.py -- sample <输出目录>   （在 Blender 里采样地形，写 lake_samples.json）
  2. python3 lake_layout_diagrams.py draw <输出目录>                                （用 Pillow 画图，需要中文字体）
"""
import json
import math
import os
import sys

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
mode, out = argv[0], os.path.abspath(argv[1])
os.makedirs(out, exist_ok=True)
HERE = os.path.dirname(os.path.abspath(__file__))

if mode == "sample":
    import importlib.util
    spec = importlib.util.spec_from_file_location("bbm", os.path.join(HERE, "build_boonie_bears_map.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    L, CL = m.LAKE, m.CLIFF
    pad, st = 7.0, 0.25
    x0, x1 = L["x"] - L["rx"] - pad, L["x"] + L["rx"] + pad
    y0, y1 = L["y"] - L["ry"] - pad, L["y"] + L["ry"] + pad
    nx, ny = int((x1 - x0) / st) + 1, int((y1 - y0) / st) + 1
    grid = [[round(m.ground(x0 + i * st, y0 + j * st), 3) for i in range(nx)] for j in range(ny)]
    ux, uy = math.cos(CL["fall"]) * L["rx"], math.sin(CL["fall"]) * L["ry"]
    n = math.hypot(ux, uy)
    ux, uy = ux / n, uy / n
    sec = [(round(s, 2), round(m.ground(L["x"] + ux * s, L["y"] + uy * s), 3)) for s in [k * 0.1 - 34 for k in range(681)]]
    pts = lambda a, e: list(m.lake_point(a, e))
    data = dict(
        lake=L, x0=x0, y0=y0, step=st, nx=nx, ny=ny, grid=grid, section=sec, axis=(ux, uy),
        outline=[pts(2 * math.pi * k / 120, 1.0) for k in range(121)],
        cliff=[pts(CL["a0"] + (CL["a1"] - CL["a0"]) * k / 30, 1.12) for k in range(31)],
        waterfall=pts(CL["fall"], 1.0), beach_group=pts(math.radians(-62), 1.33), entry=pts(math.radians(-50), 1.0),
        path=[p for p in m.PATHS if p["name"] == "Path_Meadow_LakeBeach"][0]["pts"], house=(m.HOUSE["x"], m.HOUSE["y"]),
        depth=m.LAKE_DEPTH)
    json.dump(data, open(os.path.join(out, "lake_samples.json"), "w"))
    print("SAMPLED", nx, ny)
    sys.exit(0)

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

d = json.load(open(os.path.join(out, "lake_samples.json")))


def font(size):
    for f in ("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", "C:/Windows/Fonts/msyh.ttc", "/System/Library/Fonts/PingFang.ttc"):
        if os.path.exists(f):
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


F, FS, FB = font(22), font(17), font(30)
lv = d["lake"]["level"]
# ---------------- 平面图 ----------------
PX = 26  # 像素/米
W, H = int(d["nx"] * d["step"] * PX), int(d["ny"] * d["step"] * PX)
M = 60
im = Image.new("RGB", (W + 2 * M, H + 2 * M + 150), "white")
dr = ImageDraw.Draw(im)


def to_px(x, y):
    return M + (x - d["x0"]) * PX, M + H - (y - d["y0"]) * PX


def depth_col(dp):
    t = max(0.0, min(1.0, dp / 8.0))
    a, b = (190, 225, 240), (25, 70, 120)
    return tuple(int(a[k] + (b[k] - a[k]) * t) for k in range(3))


st = d["step"]
for j in range(d["ny"]):
    for i in range(d["nx"]):
        z = d["grid"][j][i]
        x, y = d["x0"] + i * st, d["y0"] + j * st
        px, py = to_px(x, y)
        c = depth_col(lv - z) if z < lv else ((215, 190, 140) if z < lv + 0.6 else (150, 185, 120) if z < lv + 4 else (120, 120, 118))
        dr.rectangle((px, py - st * PX, px + st * PX, py), fill=c)
# 等深线：每 1 m
for j in range(d["ny"] - 1):
    for i in range(d["nx"] - 1):
        z, zr, zu = d["grid"][j][i], d["grid"][j][i + 1], d["grid"][j + 1][i]
        for zz in (zr, zu):
            a_, b_ = lv - z, lv - zz
            if a_ > 0 and b_ > 0 and math.floor(a_) != math.floor(b_):
                px, py = to_px(d["x0"] + i * st, d["y0"] + j * st)
                dr.rectangle((px, py - 2, px + 2, py), fill=(255, 255, 255))
dr.line([to_px(*p) for p in d["outline"]], fill=(20, 40, 80), width=3)
dr.line([to_px(*p) for p in d["cliff"]], fill=(50, 50, 55), width=12)
cxp = to_px(*d["cliff"][15])
dr.text((cxp[0] - 120, cxp[1] - 60), "石崖（U1 可见）", fill=(30, 30, 30), font=F)
wx, wy = to_px(*d["waterfall"])
dr.ellipse((wx - 10, wy - 10, wx + 10, wy + 10), fill=(255, 255, 255), outline=(0, 0, 0), width=3)
dr.text((wx + 14, wy - 12), "瀑布（U1）", fill=(0, 0, 0), font=F)
pp = [to_px(*p) for p in d["path"]]
dr.line(pp, fill=(140, 100, 60), width=8)
dr.text((pp[-2][0] - 10, pp[-2][1] + 8), "小路：去空地、木屋", fill=(100, 70, 40), font=FS)
bx, by = to_px(*d["beach_group"])
dr.text((bx - 40, by + 6), "沙滩（U1、U2）", fill=(120, 80, 20), font=F)
ex, ey = to_px(*d["entry"])
dr.polygon([(ex, ey - 14), (ex - 12, ey + 10), (ex + 12, ey + 10)], fill=(220, 60, 40))
dr.text((ex + 16, ey - 10), "入水点（推测）", fill=(200, 40, 30), font=F)
# 暂定分区（虚线圈，等截图确认）
cx0, cy0 = d["lake"]["x"], d["lake"]["y"]
ux, uy = d["axis"]


def dashed_circle(cx, cy, r, col, label):
    px, py = to_px(cx, cy)
    for k in range(0, 360, 12):
        a0, a1 = math.radians(k), math.radians(k + 7)
        dr.line([(px + r * PX * math.cos(a0), py - r * PX * math.sin(a0)), (px + r * PX * math.cos(a1), py - r * PX * math.sin(a1))], fill=col, width=3)
    dr.text((px - r * PX * 0.7, py - 12), label, fill=col, font=FS)


dashed_circle(cx0 + ux * 6, cy0 + uy * 6, 4.5, (250, 210, 60), "岩石区？（暂定）")
dashed_circle(cx0 - ux * 9, cy0 - uy * 9, 3.5, (120, 220, 120), "水草带？（暂定）")
dashed_circle(cx0 - uy * 7, cy0 + ux * 7, 4.0, (255, 140, 120), "螃蟹活动区？（暂定）")
# 剖面线
a = to_px(cx0 - ux * 30, cy0 - uy * 30)
b = to_px(cx0 + ux * 30, cy0 + uy * 30)
dr.line([a, b], fill=(200, 0, 120), width=3)
dr.text((a[0] + 6, a[1] - 30), "A", fill=(200, 0, 120), font=FB)
dr.text((b[0] + 6, b[1] - 6), "B", fill=(200, 0, 120), font=FB)
# 比例尺、指北针、图例
sx, sy = M, M + H + 30
dr.rectangle((sx, sy, sx + 10 * PX, sy + 10), fill=(0, 0, 0))
dr.text((sx, sy + 14), "10 m", fill=(0, 0, 0), font=FS)
dr.text((W + M - 40, M + 4), "北 ↑", fill=(0, 0, 0), font=F)
lx = sx + 10 * PX + 60
for k, dp in enumerate((0.5, 1.5, 3, 5, 7)):
    dr.rectangle((lx + k * 90, sy, lx + k * 90 + 30, sy + 24), fill=depth_col(dp))
    dr.text((lx + k * 90 + 34, sy + 2), f"{dp:g} m", fill=(0, 0, 0), font=FS)
dr.text((sx, sy + 48), "白点为每 1 m 等深线。湖岸轮廓、石崖、瀑布、沙滩依据 U1/U2；湖底深度、入水点和黄/绿/红虚线分区全部为推测，", fill=(0, 0, 0), font=FS)
dr.text((sx, sy + 74), "等第 30 集《湖底历险记》截图核对后再定。", fill=(0, 0, 0), font=FS)
dr.text((M, 14), "湖泊结构草图：平面与等深线（数据取自 .blend 的地形函数）", fill=(0, 0, 0), font=F)
im.save(os.path.join(out, "lake_plan_sketch.png"))

# ---------------- 剖面图 ----------------
sec = d["section"]
PXs = 34
zmin, zmax = -10.0, 6.0
Ws, Hs = int((sec[-1][0] - sec[0][0]) * PXs), int((zmax - zmin) * PXs)
M2 = 70
im = Image.new("RGB", (Ws + 2 * M2, Hs + 2 * M2 + 60), "white")
dr = ImageDraw.Draw(im)
sp = lambda s, z: (M2 + (s - sec[0][0]) * PXs, M2 + (zmax - z) * PXs)
water = [sp(s, lv) for s, z in sec if z < lv]
poly_w = [sp(s, max(min(z, lv), zmin)) for s, z in sec]
# 水体
for s, z in sec:
    if z < lv:
        x, ytop = sp(s, lv)
        _, ybot = sp(s, z)
        dr.line([(x, ytop), (x, ybot)], fill=(150, 200, 230), width=4)
# 地面
ground_poly = [sp(s, max(z, zmin)) for s, z in sec] + [sp(sec[-1][0], zmin), sp(sec[0][0], zmin)]
dr.polygon(ground_poly, fill=(165, 140, 100))
dr.line([sp(s, max(z, zmin)) for s, z in sec], fill=(80, 60, 40), width=3)
dr.line([sp(sec[0][0], lv), sp(sec[-1][0], lv)], fill=(30, 90, 170), width=2)
# 刻度
for zz in range(int(zmin), int(zmax) + 1, 2):
    x, y = sp(sec[0][0], zz)
    dr.line([(x - 8, y), (x, y)], fill=(0, 0, 0), width=2)
    dr.text((x - 50, y - 10), f"{zz - lv:+.0f} m", fill=(0, 0, 0), font=FS)
for ss in range(-30, 31, 10):
    x, y = sp(ss, zmin)
    dr.line([(x, y), (x, y + 8)], fill=(0, 0, 0), width=2)
    dr.text((x - 12, y + 10), f"{ss}", fill=(0, 0, 0), font=FS)
# 最深点、2 m 熊大比例
deep = min(sec, key=lambda t: t[1])
x, y = sp(*deep)
dr.text((x - 60, y + 8), f"最深 {lv - deep[1]:.1f} m（推测）", fill=(255, 255, 255), font=F)
for s_ in (-14.0, 4.0):
    zb = [z for s, z in sec if abs(s - s_) < 0.06][0]
    x0_, y0_ = sp(s_, zb)
    x1_, y1_ = sp(s_ + 0.9, zb + 2.0)
    dr.rectangle((x0_, y1_, x1_, y0_), outline=(150, 70, 40), width=3)
    dr.text((x0_ - 20, y1_ - 26), "熊大 2 m", fill=(150, 70, 40), font=FS)
dr.text((sp(sec[0][0], 0)[0] + 10, M2 + 10), "A：东南沙滩", fill=(200, 0, 120), font=F)
dr.text((sp(sec[-1][0], 0)[0] - 420, M2 + 10), "B：西北石崖", fill=(200, 0, 120), font=F)
dr.text((M2, Hs + M2 + 34), "横纵比例 1:1（不夸大）。湖底形状与深度为推测：浅滩约 1.4 m → 陡坎 → 湖心约 5–6 m → 石崖下最深约 7.5–8 m。", fill=(0, 0, 0), font=FS)
dr.text((M2, 10), "湖泊结构草图：A–B 剖面（沿“沙滩—湖心—石崖”方向）", fill=(0, 0, 0), font=F)
im.save(os.path.join(out, "lake_section_sketch.png"))
print("DREW", out)
