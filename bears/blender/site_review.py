# -*- coding: utf-8 -*-
"""湖—仓库—木屋同框审核图（俯视 + 斜俯视）：完整湖岸、仓库、木屋、栅栏、连接道路，
推测的距离、方位、门朝向直接标在图上。

两步：
  1. blender -b boonie_bears_forest_map.blend -P site_review.py -- render <输出目录> [采样数]
     临时建相机渲染（隐藏树木，看清地面关系），量距离，把要标注的点和线投影成画面坐标写进 site_review.json。
  2. python3 site_review.py draw <输出目录>     用 Pillow 画标注，输出 *_annotated.jpg。
"""
import json
import math
import os
import sys

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
mode, out = argv[0], os.path.abspath(argv[1])
os.makedirs(out, exist_ok=True)
HERE = os.path.dirname(os.path.abspath(__file__))

if mode == "render":
    import bpy
    import importlib.util
    from mathutils import Vector
    from bpy_extras.object_utils import world_to_camera_view
    spec = importlib.util.spec_from_file_location("bbm", os.path.join(HERE, "build_boonie_bears_map.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    sc = bpy.context.scene
    sc.cycles.samples = int(argv[2]) if len(argv) > 2 else 16
    O = bpy.data.objects
    w, h = O["WAREHOUSE_Root"], O["HOUSE_Root"]
    wp, hp = w.matrix_world.translation.copy(), h.matrix_world.translation.copy()
    g = m.ground
    door = (w.matrix_world.to_3x3() @ Vector((0, 1, 0))).normalized()
    D = m.WAREHOUSE["D"]
    shore = [m.lake_point(2 * math.pi * k / 360, 1.0) for k in range(360)]
    near = min(shore, key=lambda p: math.hypot(p[0] - wp.x, p[1] - wp.y))
    lc = Vector((m.LAKE["x"], m.LAKE["y"], 0))
    bearing_door = math.degrees(math.atan2(door.x, door.y)) % 360
    bearing_wh = math.degrees(math.atan2(wp.x - lc.x, wp.y - lc.y)) % 360
    meas = dict(house_wh=(wp - hp).to_2d().length, wh_shore=math.hypot(near[0] - wp.x, near[1] - wp.y),
                door_bearing=bearing_door, wh_bearing_from_lake=bearing_wh)
    Hm = h.matrix_world
    F = dict(x0=-10.0, x1=15.0, y0=-6.0, y1=12.0)
    fence = [Hm @ Vector((x, y, 0)) for x, y in ((F["x0"], F["y1"]), (F["x1"], F["y1"]), (F["x1"], F["y0"]), (F["x0"], F["y0"]), (F["x0"], F["y1"]))]
    gate = Hm @ Vector((6.6, 12.0, 0))
    lines = [("湖岸（形状推测）", [(x, y, 0.2) for x, y in shore] + [(shore[0][0], shore[0][1], 0.2)], "lake")]
    lines.append(("院子栅栏（只围木屋）", [(p.x, p.y, g(p.x, p.y) + 0.8) for p in fence], "fence"))
    for p in m.PATHS:
        if p["name"] in ("Path_Lake_Warehouse", "Path_Meadow_LakeBeach", "Path_House_Meadow"):
            nm = {"Path_Lake_Warehouse": "仓库—湖边小路（推测）", "Path_Meadow_LakeBeach": "空地—沙滩小路（推测）", "Path_House_Meadow": "木屋—空地小路（推测）"}[p["name"]]
            lines.append((nm, [(x, y, g(x, y) + 0.4) for x, y in p["pts"]], "path"))
    dims = [(f"木屋—仓库 {meas['house_wh']:.0f} m（推测）", (hp.x, hp.y, g(hp.x, hp.y) + 1), (wp.x, wp.y, g(wp.x, wp.y) + 1)),
            (f"仓库中心—湖岸 {meas['wh_shore']:.0f} m（推测）", (wp.x, wp.y, g(wp.x, wp.y) + 1), (near[0], near[1], 0.4))]
    door_arrow = ((wp.x + door.x * D / 2, wp.y + door.y * D / 2, g(wp.x, wp.y) + 1), (wp.x + door.x * (D / 2 + 7), wp.y + door.y * (D / 2 + 7), g(wp.x, wp.y) + 1))
    cliff = m.lake_point(m.CLIFF["fall"], 1.12)
    beach = m.lake_point(math.radians(-62), 1.25)
    pts = [("仓库（用户线索：在湖边；位置待画面验证）", (wp.x, wp.y, g(wp.x, wp.y) + 4), "user"),
           ("光头强木屋（位置推测）", (hp.x, hp.y, g(hp.x, hp.y) + 5), "infer"),
           ("院门（R1：正对木屋时在画面左侧）", (gate.x, gate.y, g(gate.x, gate.y) + 2), "orig"),
           ("湖（U1、L1）", (lc.x, lc.y, 0.3), "orig"),
           ("石崖和瀑布（U1）", (cliff[0], cliff[1], 8), "orig"),
           ("沙滩（U1、U2）", (beach[0], beach[1], 1), "orig"),
           ("旧候选：木屋背后（已撤销）", tuple(Hm @ Vector((2.0, -15.0, 1))), "old")]
    notes = [f"仓库在湖心的方位约 {meas['wh_bearing_from_lake']:.0f}°（东偏北；+Y 约定为北，不是原作证据）",
             f"仓库大门朝 {meas['door_bearing']:.0f}°（约定南偏东，朝湖边小路岔口；推测）",
             f"木屋—仓库直线 {meas['house_wh']:.1f} m、仓库中心到湖岸 {meas['wh_shore']:.1f} m：都是模型里的推测距离，不是原作数据"]
    hide = [o for c in ("Forest_Trees", "Forest_Plants", "Characters", "SEASON_AUTUMN") for o in bpy.data.collections[c].all_objects if o and not o.hide_render]
    for o in hide:
        o.hide_render = True
    views = {}

    def shoot(name, setup, res):
        cd = bpy.data.cameras.new(name)
        co = bpy.data.objects.new(name, cd)
        sc.collection.objects.link(co)
        setup(cd, co)
        sc.camera = co
        sc.render.resolution_x, sc.render.resolution_y = res
        sc.render.resolution_percentage = 100
        sc.render.filepath = os.path.join(out, name + ".png")
        bpy.context.view_layer.update()
        bpy.ops.render.render(write_still=True)

        def P(p):
            v = world_to_camera_view(sc, co, Vector(p))
            return [v.x * res[0], (1 - v.y) * res[1], v.z]
        views[name] = dict(res=res, points=[(t, P(p), k) for t, p, k in pts], lines=[(t, [P(q) for q in ql], k) for t, ql, k in lines],
                           dims=[(t, P(a), P(b)) for t, a, b in dims], door=[P(door_arrow[0]), P(door_arrow[1])])
        if cd.type == "ORTHO":
            views[name]["px_per_m"] = res[0] / cd.ortho_scale
        print("RENDERED", name, flush=True)
    cx, cy = (m.LAKE["x"] - m.LAKE["rx"] * 1.2 + hp.x + 18) / 2, (m.LAKE["y"] + hp.y) / 2 + 2

    def top(cd, co):
        cd.type = "ORTHO"
        cd.ortho_scale = 132
        cd.clip_start, cd.clip_end = 1, 400
        co.location = (cx, cy, 200)
        co.rotation_euler = (0, 0, 0)
    shoot("Site_Top_Lake_Warehouse_House", top, (2400, 1300))

    def oblique(cd, co):
        cd.lens = 22
        cd.clip_start, cd.clip_end = 1, 1500
        co.location = (cx + 25, cy - 72, 62)
        t = Vector((cx - 2, cy + 4, 0))
        co.rotation_euler = (t - co.location).to_track_quat("-Z", "Y").to_euler()
    shoot("Site_Oblique_Lake_Warehouse_House", oblique, (2400, 1350))
    for o in hide:
        o.hide_render = False
    with open(os.path.join(out, "site_review.json"), "w", encoding="utf-8") as f:
        json.dump(dict(views=views, notes=notes, meas=meas), f, ensure_ascii=False)
    sys.exit(0)

from PIL import Image, ImageDraw, ImageFont  # noqa: E402


def font(s):
    return ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", s)


COL = {"orig": (20, 130, 50), "infer": (215, 110, 0), "user": (200, 30, 120), "old": (130, 130, 130),
       "lake": (20, 90, 160), "fence": (120, 70, 20), "path": (215, 110, 0)}
d = json.load(open(os.path.join(out, "site_review.json"), encoding="utf-8"))
for name, v in d["views"].items():
    im = Image.open(os.path.join(out, name + ".png")).convert("RGB")
    W, H = im.size
    canvas = Image.new("RGB", (W, H + 200), "white")
    canvas.paste(im, (0, 0))
    dr = ImageDraw.Draw(canvas)
    F, Fs, Ft = font(30), font(24), font(34)
    for t, pl, k in v["lines"]:
        q = [(p[0], p[1]) for p in pl if p[2] > 0]
        if len(q) < 2:
            continue
        dash = k == "path"
        if dash:
            for a, b in zip(q, q[1:]):
                n = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) / 14))
                for i in range(0, n, 2):
                    dr.line((a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n, a[0] + (b[0] - a[0]) * (i + 1) / n, a[1] + (b[1] - a[1]) * (i + 1) / n), fill=COL[k], width=5)
        else:
            dr.line(q, fill=COL[k], width=5)
        if dash and not v.get("px_per_m"):
            continue  # 斜俯视里道路标签挤在一起，只在俯视图上标
        mx, my = q[len(q) // 3]
        tw = dr.textlength(t, font=Fs)
        mx = min(max(mx, 0), W - tw - 20)
        dr.rectangle((mx + 8, my + 6, mx + 14 + tw, my + 36), fill=(255, 255, 255))
        dr.text((mx + 11, my + 8), t, fill=COL[k], font=Fs)
    for t, a, b in v["dims"]:
        dr.line((a[0], a[1], b[0], b[1]), fill=(40, 40, 40), width=4)
        for p in (a, b):
            dr.ellipse((p[0] - 7, p[1] - 7, p[0] + 7, p[1] + 7), fill=(40, 40, 40))
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        tw = dr.textlength(t, font=F)
        dr.rectangle((mx - tw / 2 - 6, my - 44, mx + tw / 2 + 6, my - 6), fill=(255, 255, 230), outline=(40, 40, 40))
        dr.text((mx - tw / 2, my - 42), t, fill=(0, 0, 0), font=F)
    (ax, ay, _), (bx, by, _) = v["door"]
    dr.line((ax, ay, bx, by), fill=COL["user"], width=7)
    ang = math.atan2(by - ay, bx - ax)
    dr.polygon([(bx, by), (bx - 26 * math.cos(ang - 0.4), by - 26 * math.sin(ang - 0.4)), (bx - 26 * math.cos(ang + 0.4), by - 26 * math.sin(ang + 0.4))], fill=COL["user"])
    t = "大门朝向（推测）"
    dr.rectangle((bx + 10, by - 4, bx + 18 + dr.textlength(t, font=Fs), by + 28), fill=(255, 255, 255))
    dr.text((bx + 14, by - 2), t, fill=COL["user"], font=Fs)
    for t, p, k in v["points"]:
        if p[2] <= 0:
            continue
        x, y = p[0], p[1]
        dr.ellipse((x - 12, y - 12, x + 12, y + 12), fill=COL[k], outline=(255, 255, 255), width=3)
        tw = dr.textlength(t, font=F)
        tx = min(max(x + 18, 10), W - tw - 16)
        ty = y - 52 if y > 70 else y + 18
        dr.rectangle((tx - 6, ty - 2, tx + tw + 6, ty + 38), fill=(255, 255, 255), outline=COL[k], width=2)
        dr.text((tx, ty), t, fill=COL[k], font=F)
    if v.get("px_per_m"):
        L = 20
        x0, y0 = W - 40 - v["px_per_m"] * L, H - 40
        dr.rectangle((x0 - 10, y0 - 40, W - 25, y0 + 15), fill=(255, 255, 255))
        dr.line((x0, y0, x0 + v["px_per_m"] * L, y0), fill=(0, 0, 0), width=6)
        dr.text((x0, y0 - 36), "20 m（模型尺寸）", fill=(0, 0, 0), font=Fs)
        dr.line((60, 110, 60, 40), fill=(0, 0, 0), width=5)
        dr.polygon([(48, 52), (72, 52), (60, 28)], fill=(0, 0, 0))
        dr.rectangle((80, 50, 80 + dr.textlength("+Y（约定“北”）", font=Fs) + 8, 84), fill=(255, 255, 255))
        dr.text((84, 52), "+Y（约定“北”）", fill=(0, 0, 0), font=Fs)
    title = "湖—仓库—木屋同框（" + ("正射俯视" if v.get("px_per_m") else "斜俯视") + "，隐藏树木）"
    dr.text((20, H + 12), title, fill=(0, 0, 0), font=Ft)
    for i, n in enumerate(d["notes"]):
        dr.text((20, H + 60 + i * 38), "· " + n, fill=(90, 90, 90), font=Fs)
    lx = W - 980
    for k, t in (("orig", "原作画面有依据"), ("user", "用户线索，待画面验证"), ("infer", "推测"), ("old", "已撤销")):
        dr.ellipse((lx, H + 22, lx + 22, H + 44), fill=COL[k])
        dr.text((lx + 30, H + 16), t, fill=(0, 0, 0), font=Fs)
        lx += 50 + dr.textlength(t, font=Fs)
    canvas.save(os.path.join(out, name + "_annotated.jpg"), quality=90)
    print("DREW", name)
