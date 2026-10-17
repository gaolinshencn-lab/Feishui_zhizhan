# -*- coding: utf-8 -*-
"""地理布局审核图（A–E）。两步：
  1. blender -b boonie_bears_forest_map.blend -P layout_review.py -- render <输出目录> [采样数]
     临时建相机渲染，并把标注点投影成画面坐标写进 <名字>.labels.json（不保存 .blend）。
  2. python3 layout_review.py draw <输出目录>
     用 Pillow 画标注：绿色=原版截图确认，蓝色=其他版本辅助，紫色=玩家复刻参考，橙色=缺少证据的推测。
标注说明的是“位置/布局”的依据，不是模型外观的依据（外观依据见各 *_AUDIT.md 和 REFERENCE_CATALOG.md）。
"""
import json
import math
import os
import sys

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
mode, out = argv[0], os.path.abspath(argv[1])
os.makedirs(out, exist_ok=True)
HERE = os.path.dirname(os.path.abspath(__file__))
COLORS = {"orig": (20, 130, 50), "other": (30, 90, 200), "player": (140, 60, 170), "infer": (215, 110, 0)}
NAMES = {"orig": "原版截图确认", "other": "其他版本辅助", "player": "玩家复刻参考", "infer": "缺少证据的推测"}

if mode == "render":
    import bpy
    import importlib.util
    from mathutils import Vector, Matrix
    from bpy_extras.object_utils import world_to_camera_view
    spec = importlib.util.spec_from_file_location("bbm", os.path.join(HERE, "build_boonie_bears_map.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    sc = bpy.context.scene
    sc.cycles.samples = int(argv[2]) if len(argv) > 2 else 12
    O = bpy.data.objects
    hr, wr = O["HOUSE_Root"], O["WAREHOUSE_Root"]
    H = hr.matrix_world

    def hw(x, y, z=0.0):
        return H @ Vector((x, y, z))

    def cam_top(name, center, scale, res, z=200.0, rot=0.0):
        cd = bpy.data.cameras.new(name)
        cd.type = "ORTHO"
        cd.ortho_scale = scale
        cd.clip_start, cd.clip_end = 1.0, 400.0
        co = bpy.data.objects.new(name, cd)
        sc.collection.objects.link(co)
        co.location = (center[0], center[1], z)
        co.rotation_euler = (0, 0, rot)
        return co, res

    def cam_section(name, root, axis_from, look_dir, center_local, scale, res, depth=9.0, D=60.0):
        cd = bpy.data.cameras.new(name)
        cd.type = "ORTHO"
        cd.ortho_scale = scale
        cd.clip_start, cd.clip_end = D, D + depth
        co = bpy.data.objects.new(name, cd)
        sc.collection.objects.link(co)
        M = root.matrix_world
        c = M @ Vector(center_local)
        d = (M.to_3x3() @ Vector(look_dir)).normalized()
        co.location = c - d * D
        co.rotation_euler = d.to_track_quat("-Z", "Z" if abs(d.z) > 0.9 else "Y").to_euler()
        return co, res

    def hide(names, state):
        objs = []
        for n in names:
            c = bpy.data.collections.get(n)
            if c:
                objs += [o for o in c.all_objects if o is not None]
        for o in objs:
            o.hide_render = state

    def render(co, res, labels, hide_c=(), lines=None, title=""):
        w, h = (int(v) for v in res.split("x"))
        sc.render.resolution_x, sc.render.resolution_y = w, h
        sc.render.resolution_percentage = 100
        sc.camera = co
        hide(hide_c, True)
        sc.render.filepath = os.path.join(out, co.name + ".png")
        bpy.ops.render.render(write_still=True)
        hide(hide_c, False)
        L = []
        for (text, p, st, big) in labels:
            q = world_to_camera_view(sc, co, Vector(p))
            L.append(dict(text=text, x=q.x, y=q.y, status=st, big=big))
        PL = []
        for (text, pts, st) in (lines or []):
            PL.append(dict(text=text, status=st, pts=[list(world_to_camera_view(sc, co, Vector(p)))[:2] for p in pts]))
        ppm = w / co.data.ortho_scale if co.data.type == "ORTHO" else None
        json.dump(dict(labels=L, lines=PL, title=title, px_per_m=ppm), open(os.path.join(out, co.name + ".labels.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print("RENDERED", co.name, flush=True)

    def loc(n, dz=0.0):
        return O[n].matrix_world.translation + Vector((0, 0, dz))
    g = m.ground
    L = m.LAKE
    cliff = m.lake_point(m.CLIFF["fall"], 1.15)
    beach = m.lake_point(math.radians(-62), 1.3)
    paths = [(p["name"], [(x, y, g(x, y) + 0.3) for x, y in p["pts"]]) for p in m.PATHS]
    path_cn = {"Path_House_Meadow": "木屋—空地小路", "Path_Meadow_BearsHome": "空地—熊洞小路", "Path_BearsHome_HoneyTree": "熊洞—蜂蜜树",
               "Path_Meadow_LakeBeach": "空地—湖边沙滩小路", "Path_Meadow_MonkeyCave": "空地—猴洞小路", "Path_To_SquirrelTree": "去松鼠窝的岔路",
               "Path_House_Warehouse": "木屋—仓库院内小路", "Road_House_East": "皮卡土路（向东）"}
    # A：全图俯视
    big = [("光头强木屋和院子", loc("HOUSE_Root"), "infer", True), ("独立仓库", loc("WAREHOUSE_Root"), "infer", True),
           ("森林湖泊", (L["x"], L["y"], 0), "infer", True), ("石崖和瀑布", (cliff[0], cliff[1], 8), "orig", False),
           ("沙滩（涂涂、萝卜头、蹦蹦）", (beach[0], beach[1], 1), "orig", False),
           ("空地（熊大熊二）", (m.MEADOW[0], m.MEADOW[1], 0), "infer", True), ("熊大熊二树洞", loc("BEAR_HOME_Root"), "infer", True),
           ("蜂蜜树", (m.HONEYTREE[0], m.HONEYTREE[1], 0), "other", False), ("吉吉毛毛山洞", loc("MONKEY_CAVE_Root"), "infer", True),
           ("蹦蹦松鼠窝", loc("SQUIRREL_NEST_Tree_Root"), "infer", True), ("北面山脊", (0, 55, 15), "infer", False)]
    co, res = cam_top("Review_A_Map_Top", (-8, 4), 185, "1600x1200")
    render(co, res, big, lines=[(path_cn.get(n, n), pts, "infer") for n, pts in paths], title="A 狗熊岭整体正射俯视（位置依据见颜色）")
    # E：去掉树木的地形、湖泊和道路
    co, res = cam_top("Review_E_Terrain_Lake_Roads", (-8, 4), 185, "1600x1200")
    render(co, res, big, hide_c=("Forest_Trees", "Forest_Plants", "Characters"),
           lines=[(path_cn.get(n, n), pts, "infer") for n, pts in paths], title="E 地形、湖泊和连接道路（隐藏树木）")
    # B：院子俯视
    F = dict(x0=-10.0, x1=15.0, y0=-22.0, y1=12.0)
    yard = [("木屋主屋", hw(0, 0, 5), "orig", True), ("卫生间侧翼", hw(-5.75, -0.6, 4), "orig", False),
            ("正门楼梯", hw(-0.2, 5.6, 1), "orig", False), ("带蓝顶的院门", hw(7.8, 12, 2), "orig", True),
            ("独立仓库（整栋推测）", loc("WAREHOUSE_Root", 5), "infer", True), ("仓库大门", loc("WAREHOUSE_Barn_Door_North", 1), "infer", False),
            ("轮胎堆", loc("PROPS_Tire_Stack"), "orig", False), ("院里原木堆", loc("PROPS_Log_Pile_Yard"), "orig", False),
            ("铁皮盆、铁桶", loc("PROPS_Washtub_Galvanized"), "other", False), ("木墩和斧头", loc("PROPS_Chopping_Block"), "other", False),
            ("水缸", loc("PROPS_Water_Jar_Clay"), "orig", False), ("木桶", loc("PROPS_Wooden_Barrel"), "other", False),
            ("皮卡", loc("PROPS_Pickup_Root"), "other", False), ("车道缺口", hw(12.75, 12, 0), "infer", False),
            ("栅栏（正面一段 R1 可见）", hw(-3.5, 12.3, 0), "orig", False), ("栅栏（东侧）", hw(15.4, -5, 0), "infer", False),
            ("栅栏（后面）", hw(5, -22.4, 0), "infer", False), ("栅栏（西侧）", hw(-10.4, 3, 0), "infer", False)]
    yl = [(path_cn[n], pts, "infer") for n, pts in paths if n in ("Path_House_Meadow", "Path_House_Warehouse", "Road_House_East")]
    yl.append(("栅栏一整圈", [hw(x, y, 0.5) for x, y in ((F["x0"], F["y1"]), (F["x1"], F["y1"]), (F["x1"], F["y0"]), (F["x0"], F["y0"]), (F["x0"], F["y1"]))], "infer"))
    c = hw(2.5, -5)
    co, res = cam_top("Review_B_Yard_Top", (c.x, c.y), 46, "1600x1300")
    render(co, res, yard, hide_c=("Forest_Trees",), lines=yl, title="B 木屋院落俯视：一整圈栅栏、院门、木屋、独立仓库")
    # C：木屋室内俯视（拆屋顶）
    rooms = [("客厅 / 厨房 / 餐厅", hw(-1.6, 1.6, 2), "other", True), ("卧室", hw(2.9, -1.4, 2), "other", True), ("卫生间", hw(-5.75, -1.4, 2), "other", True),
             ("正门", hw(-0.2, 3.0, 1), "orig", False), ("卧室门", hw(1.3, -1.8, 1), "orig", False), ("卫生间门", hw(-4.5, -0.15, 1), "infer", False)]
    for o in bpy.data.collections["GuangtouQiang_House_Interior"].all_objects:
        if o.type == "MESH" and o.get("name_cn") and o.get("floor_item"):
            st = "orig" if (o.get("ref_status") == "observed" and o.get("position_status") == "observed") else ("infer" if o.get("ref_status") == "inferred" or o.get("position_status") == "inferred" else "other")
            rooms.append((o["name_cn"].split("（")[0], o.matrix_world.translation + Vector((0, 0, 1.5)), st, False))
    c = hw(-1.2, 0.4)
    co, res = cam_top("Review_C_House_Interior_Top", (c.x, c.y), 13.6, "1600x1050")
    render(co, res, rooms, hide_c=("GQ_House_Roof_Removable", "Characters"), title="C 木屋室内俯视（拆掉屋顶）：三个功能空间和家具")
    # D：三个住所的剖面
    br = O["BEAR_HOME_Root"]
    co, res = cam_section("Review_D1_Section_Bears_TreeHome", br, None, (1, 0, 0), (0, 0, 5.0), 21, "1400x1400", depth=10)
    render(co, res, [("天然洞口（正面）", br.matrix_world @ Vector((0, -3.6, 1.2)), "player", False),
                     ("后壁拱形圆洞", br.matrix_world @ Vector((0, 3.6, 2.0)), "orig", False),
                     ("树根状内壁、穹顶", br.matrix_world @ Vector((0, 0, 5.2)), "orig", False),
                     ("长条灰色石板床", loc("BEAR_HOME_Stone_Bed", 0.6), "orig", False),
                     ("熊二的树叶铺（推测）", loc("BEAR_HOME_Leaf_Bed_XiongEr", 0.4), "infer", False),
                     ("橙色螺旋叠圈物", br.matrix_world @ Vector((0, 0.6, 1.4)), "orig", False),
                     ("上段树干和树冠", br.matrix_world @ Vector((0, 0, 12)), "infer", False)],
           hide_c=("Characters",), title="D1 熊大熊二树洞剖面（沿洞口方向切开）")
    mr = O["MONKEY_CAVE_Root"]
    co, res = cam_section("Review_D2_Section_MonkeyCave", mr, None, (1, 0, 0), (0, -1.5, 2.5), 17, "1500x1000", depth=12)
    render(co, res, [("洞口（不规则，乱石门框）", mr.matrix_world @ Vector((0, -3.6, 1.3)), "orig", False),
                     ("洞室（推测）", mr.matrix_world @ Vector((0, 1.8, 2.0)), "infer", False),
                     ("洞前石板平台", mr.matrix_world @ Vector((0, -5.5, 0.5)), "orig", False),
                     ("木图腾柱", mr.matrix_world @ Vector((0, -7.4, 1.5)), "orig", False),
                     ("洞口上方石刻", mr.matrix_world @ Vector((0, -4.0, 3.3)), "orig", False),
                     ("吉吉的石座（推测）", loc("MONKEY_CAVE_JiJi_Stone_Seat", 0.5), "infer", False),
                     ("毛毛的草窝（推测）", loc("MONKEY_CAVE_MaoMao_Straw_Nest", 0.3), "infer", False)],
           hide_c=("Characters",), title="D2 吉吉毛毛山洞剖面（沿洞口方向切开）")
    sr = O["SQUIRREL_NEST_Tree_Root"]
    co, res = cam_section("Review_D3_Section_SquirrelNest", sr, None, (0, 1, 0), (1.2, 0, 4.9), 4.2, "1200x1200", depth=6)
    render(co, res, [("候选洞口 A（树枝和树干相接处）", sr.matrix_world @ Vector((0.85, 0, 4.75)), "infer", False),
                     ("粗树枝（S1 可见）", sr.matrix_world @ Vector((2.5, 0, 4.35)), "orig", False),
                     ("小洞室（推测）", sr.matrix_world @ Vector((0.1, 0, 5.2)), "infer", False),
                     ("松果堆（第一季，其他版本）", loc("SQUIRREL_NEST_Pinecone_Pile", 0.2), "other", False),
                     ("睡窝（推测）", loc("SQUIRREL_NEST_Leaf_Bed", 0.1), "infer", False),
                     ("候选洞口 B（只是标记）", loc("SQUIRREL_NEST_Candidate_Entrance_B"), "infer", False)],
           hide_c=("Characters",), title="D3 蹦蹦松鼠窝剖面（沿树枝方向切开）")
    sys.exit(0)

# ---------------- 画标注 ----------------
from PIL import Image, ImageDraw, ImageFont  # noqa: E402


def font(size):
    for f in ("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", "C:/Windows/Fonts/msyh.ttc", "/System/Library/Fonts/PingFang.ttc"):
        if os.path.exists(f):
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


for fn in sorted(os.listdir(out)):
    if not fn.endswith(".labels.json"):
        continue
    d = json.load(open(os.path.join(out, fn), encoding="utf-8"))
    im = Image.open(os.path.join(out, fn.replace(".labels.json", ".png"))).convert("RGB")
    W, H = im.size
    canvas = Image.new("RGB", (W, H + 110), "white")
    canvas.paste(im, (0, 0))
    dr = ImageDraw.Draw(canvas)
    small = W < 1300 and "Interior" in fn
    Fs, Fb, Ft = font(16 if small else 19), font(26), font(26)
    for ln in d["lines"]:
        pts = [(x * W, (1 - y) * H) for x, y in ln["pts"]]
        dr.line(pts, fill=(250, 240, 120), width=6)
        dr.line(pts, fill=COLORS[ln["status"]], width=3)
        mx, my = pts[len(pts) // 2]
        t = ln["text"]
        bb = dr.textbbox((mx + 6, my + 4), t, font=Fs)
        dr.rectangle(bb, fill=(255, 255, 240))
        dr.text((mx + 6, my + 4), t, fill=COLORS[ln["status"]], font=Fs)
    seen = set()
    boxes = []
    for lab in sorted(d["labels"], key=lambda l: not l["big"]):
        if lab["text"] in seen:
            continue
        seen.add(lab["text"])
        x, y = lab["x"] * W, (1 - lab["y"]) * H
        if not (0 <= x <= W and 0 <= y <= H):
            continue
        col = COLORS[lab["status"]]
        f = Fb if lab["big"] else Fs
        r = 9 if lab["big"] else 6
        dr.ellipse((x - r, y - r, x + r, y + r), fill=col, outline=(255, 255, 255), width=2)
        tx, ty = x + 12, y - 12
        bb = dr.textbbox((tx, ty), lab["text"], font=f)
        for _ in range(12):  # 避开已经画过的标注
            if not any(bb[0] < o[2] and bb[2] > o[0] and bb[1] < o[3] and bb[3] > o[1] for o in boxes):
                break
            ty += bb[3] - bb[1] + 6
            bb = dr.textbbox((tx, ty), lab["text"], font=f)
        if ty != y - 12:
            dr.line([(x, y), (tx - 2, ty + 10)], fill=col, width=2)
        boxes.append(bb)
        dr.rectangle((bb[0] - 3, bb[1] - 2, bb[2] + 3, bb[3] + 2), fill=(255, 255, 255))
        dr.text((tx, ty), lab["text"], fill=col, font=f)
    dr.text((14, H + 10), d["title"], fill=(0, 0, 0), font=Ft)
    lx = 14
    for k in ("orig", "other", "player", "infer"):
        dr.ellipse((lx, H + 56, lx + 18, H + 74), fill=COLORS[k])
        dr.text((lx + 24, H + 52), NAMES[k], fill=(0, 0, 0), font=font(20))
        lx += 210
    if d.get("px_per_m"):
        L = 10 if d["px_per_m"] * 10 < W * 0.3 else 1
        while d["px_per_m"] * L < 60:
            L *= 2
        x0 = W - 30 - d["px_per_m"] * L
        dr.rectangle((x0, H + 88, W - 30, H + 94), fill=(0, 0, 0))
        dr.text((x0 - 50, H + 80), f"{L} m", fill=(0, 0, 0), font=font(18))
    dr.text((lx + 10, H + 52), "颜色说明的是位置的依据；剖面图里黑色是被切开的实体", fill=(90, 90, 90), font=font(18))
    canvas.save(os.path.join(out, fn.replace(".labels.json", "_labeled.jpg")), quality=90)
    print("DREW", fn)
