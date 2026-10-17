# -*- coding: utf-8 -*-
"""角色比例测试：把角色临时放到门口、床上、洞口、树枝上，渲染近景，并输出尺寸对比表（不保存文件）。

用法：blender -b boonie_bears_forest_map.blend -P render_scale_tests.py -- <输出目录> [采样数] [场景名关键字,...]

吉吉、毛毛没有角色模型，用灰色的圆柱+球代替（身高是推测值，写在 scale_tests.json 里）。
输出：<输出目录>/<场景>.png 和 scale_tests.json（每个开口的净高/净宽、角色身高、是否能直立通过）。
"""
import bpy
import json
import math
import os
import sys
from mathutils import Vector, Matrix, Euler

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
out = os.path.abspath(argv[0] if argv else "scale_tests")
samples = int(argv[1]) if len(argv) > 1 else 16
only = argv[2].split(",") if len(argv) > 2 and argv[2] else []
os.makedirs(out, exist_ok=True)
sc = bpy.context.scene
sc.cycles.samples = samples
sc.render.resolution_x, sc.render.resolution_y = 1100, 680
PASS = {nm: (root, box) for nm, root, box in json.loads(sc.get("door_passages_json", "[]"))}
CHAR_COLL = bpy.data.collections["Characters"]


def descendants(ob):
    res = [ob]
    for c in ob.children:
        res += descendants(c)
    return res


def world_bbox(obs):
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for o in obs:
        if o.type != "MESH":
            continue
        e = o.evaluated_get(dg)
        pts += [e.matrix_world @ Vector(c) for c in e.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def make_proxy(name, height, color):
    """吉吉/毛毛的临时替身：圆柱身体+球头。"""
    me = bpy.data.meshes.new(name)
    import bmesh
    bm = bmesh.new()
    r = height * 0.18
    bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=r, radius2=r * 0.85, depth=height * 0.62,
                          matrix=Matrix.Translation((0, 0, height * 0.31)))
    bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=10, radius=height * 0.19,
                              matrix=Matrix.Translation((0, 0, height * 0.81)))
    bm.to_mesh(me)
    bm.free()
    m = bpy.data.materials.new(name + "_Mat")
    m.diffuse_color = color
    m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = color
    me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    sc.collection.objects.link(ob)
    return ob


def ground_z(xy, z_from, skip):
    """从 z_from 往下打射线，跳过角色自身和隐藏的布尔切割体，返回落脚高度。"""
    dg = bpy.context.evaluated_depsgraph_get()
    o = Vector((xy.x, xy.y, z_from))
    for _ in range(40):
        ok, loc, n, i, hit, m = sc.ray_cast(dg, o, Vector((0, 0, -1)))
        if not ok:
            return None
        if hit.name in skip or hit.display_type == "WIRE" or hit.hide_render:
            o = loc - Vector((0, 0, 0.002))
            continue
        return loc.z
    return None


def anchor(name):
    return bpy.data.objects[name].matrix_world.copy()


# 每个场景：anchor 根物体；actors = (角色根或替身, 局部 x, y, 射线起点局部 z, 局部朝向角, 姿势)；
# camera = 现有相机名，或 (局部位置, 局部目标, 焦距)；opening = 对应的门洞名（来自 door_passages_json）
PROXIES = {"Proxy_JiJi": (1.3, (0.55, 0.42, 0.3, 1)), "Proxy_MaoMao": (0.7, (0.75, 0.7, 0.62, 1))}
SCENES = [
    dict(name="ST01_TreeHome_Door_Bears", anchor="Bears_TreeHome_Root", opening="熊洞洞口",
         actors=[("XiongDa_Root", -0.3, -3.0, 1.85, 0.0, "stand"), ("XiongEr_Root", 0.35, -4.4, 1.85, 0.2, "stand")],
         camera=((1.2, -10.5, 1.5), (0.0, -3.0, 1.1), 30)),
    dict(name="ST02_TreeHome_Bed_XiongDa", anchor="Bears_TreeHome_Root",
         actors=[("XiongDa_Root", 1.0, 1.3, 2.4, -0.35 - math.pi / 2, "lie")], camera="SM_B1_TreeHome_Interior"),
    dict(name="ST03_Squirrel_Slot_BengBeng", anchor="SquirrelNest_Tree_Root", opening="松鼠窝洞口 A",
         opening_size=dict(clear_width_at_mid=0.2, clear_height=0.44, source="Entrance_A_Slot 切割体尺寸"),
         actors=[("BengBeng_Root", 1.3, 0.0, 5.6, 0.25, "stand")],
         camera=((1.5, -3.4, 5.0), (0.85, 0.0, 4.85), 35)),
    dict(name="ST04_Squirrel_From_Ground", anchor="SquirrelNest_Tree_Root",
         actors=[("BengBeng_Root", 1.3, 0.0, 5.6, 0.25, "stand"),
                 ("XiongEr_Root", 3.2, -5.2, 3.0, 0.4, "stand")],
         camera=((5.5, -10.5, 1.7), (1.0, 0.0, 4.4), 24)),
    dict(name="ST05_MonkeyCave_Door_JiJi_MaoMao", anchor="MonkeyCave_Root", opening="猴洞洞口",
         actors=[("Proxy_JiJi", -0.25, -4.6, 1.6, 0.0, "stand"), ("Proxy_MaoMao", 0.45, -5.6, 1.6, 0.0, "stand"),
                 ("XiongDa_Root", 1.9, -6.2, 1.6, -0.3, "stand")],
         camera=((2.4, -13.5, 2.2), (0.0, -4.5, 1.4), 30)),
    dict(name="ST06_MonkeyCave_Chamber", anchor="MonkeyCave_Root",
         actors=[("Proxy_JiJi", -0.4, 0.4, 2.6, math.pi, "stand"), ("Proxy_MaoMao", 0.6, -0.1, 2.6, math.pi, "stand")],
         camera=((0.0, -4.4, 1.5), (0.0, 0.8, 1.0), 16)),
    dict(name="ST07_House_Front_Door_GTQ", anchor="GQ_House_Root", opening="正门",
         actors=[("GuangtouQiang_Root", None, None, None, math.pi, "door_out")], camera="door_front"),
    dict(name="ST08_Warehouse_Door_GTQ", anchor="Warehouse_Root", opening="仓库大门",
         actors=[("GuangtouQiang_Root", None, None, None, math.pi, "door_out")], camera="door_front", cam_dist=4.6, lens=18),
]


def place(actor, A, lx, ly, lz, yaw, pose, opening):
    ob = bpy.data.objects[actor]
    rot_a = A.to_euler().z
    if pose == "door_out":
        root_name, (x0, x1, y0, y1, z0, z1) = PASS[opening]
        lx, ly, lz = (x0 + x1) / 2, y1 - 0.45, z1
    p = A @ Vector((lx, ly, lz))
    skip = {o.name for o in descendants(ob)} | {o.name for o in CHAR_COLL.all_objects if o}
    for pr in PROXIES:
        if pr in bpy.data.objects:
            skip.add(pr)
    gz = ground_z(p, p.z, skip)
    ob.rotation_euler = (0, 0, rot_a + yaw)
    if pose == "lie":
        ob.rotation_euler = Euler((-math.pi / 2, 0, rot_a + yaw), "XYZ")  # 仰面躺下，头朝局部 +Y 经 yaw 转到床的长边
    ob.location = (p.x, p.y, gz if gz is not None else p.z)
    bpy.context.view_layer.update()
    lo, hi = world_bbox(descendants(ob))
    if pose == "lie":
        c = (lo + hi) / 2
        ob.location += Vector((p.x - c.x, p.y - c.y, (gz or p.z) - lo.z))
        bpy.context.view_layer.update()
        lo, hi = world_bbox(descendants(ob))
    return dict(actor=actor, foot_z=round(gz, 3) if gz is not None else None, height=round(hi.z - lo.z, 3),
                width=round(max(hi.x - lo.x, hi.y - lo.y), 3) if pose != "lie" else None,
                length_lying=round(max(hi.x - lo.x, hi.y - lo.y), 3) if pose == "lie" else None)


def opening_clearance(opening):
    """沿门洞中线向上、向两侧打射线，量出实际净高、净宽（局部坐标）。"""
    root_name, (x0, x1, y0, y1, z0, z1) = PASS[opening]
    A = anchor(root_name)
    dg = bpy.context.evaluated_depsgraph_get()
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    skip = {o.name for o in CHAR_COLL.all_objects if o} | set(PROXIES)
    res = {}

    def cast(o_local, d_local):
        o = A @ Vector(o_local)
        d = (A.to_3x3() @ Vector(d_local)).normalized()
        dist = 0.0
        for _ in range(40):
            ok, loc, n, i, hit, m = sc.ray_cast(dg, o, d, distance=20)
            if not ok:
                return None
            if hit.name in skip or hit.display_type == "WIRE" or hit.hide_render:
                dist += (loc - o).length + 0.002
                o = loc + d * 0.002
                continue
            return dist + (loc - o).length
        return None
    zmid = z0 + 0.3
    floor = cast((cx, cy, z1), (0, 0, -1))
    fz = z1 - floor if floor is not None else z0
    res["floor_local_z"] = round(fz, 3)
    up = cast((cx, cy, fz + 0.05), (0, 0, 1))
    res["clear_height"] = round(up + 0.05, 3) if up is not None else None
    zmid = fz + min(0.5, (res["clear_height"] or 1) / 2)
    l = cast((cx, cy, zmid), (-1, 0, 0))
    r = cast((cx, cy, zmid), (1, 0, 0))
    res["clear_width_at_mid"] = round(l + r, 3) if l is not None and r is not None else None
    return res


def look(cam_ob, loc, tgt):
    cam_ob.location = loc
    cam_ob.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()


def run():
    for nm, (h, col) in PROXIES.items():
        make_proxy(nm, h, col)
    cd = bpy.data.cameras.new("Tmp_Scale_Cam")
    co = bpy.data.objects.new("Tmp_Scale_Cam", cd)
    sc.collection.objects.link(co)
    movable = ["XiongDa_Root", "XiongEr_Root", "GuangtouQiang_Root", "BengBeng_Root"] + list(PROXIES)
    saved = {n: bpy.data.objects[n].matrix_world.copy() for n in movable}
    report = dict(note="吉吉 1.3 m、毛毛 0.7 m 是推测身高（D 级），只用于检查洞口是否合理", scenes=[])
    for S in SCENES:
        if only and not any(k in S["name"] for k in only):
            continue
        for n in movable:
            bpy.data.objects[n].matrix_world = saved[n]
        far = Vector((0, 0, -500))
        for n in PROXIES:
            bpy.data.objects[n].location = far
        A = anchor(S["anchor"])
        used = []
        for actor, lx, ly, lz, yaw, pose in S["actors"]:
            used.append(place(actor, A, lx, ly, lz, yaw, pose, S.get("opening")))
        # 不参加本场景的角色藏起来，避免出现在画面里
        hidden = []
        names = {a[0] for a in S["actors"]}
        for n in movable:
            if n not in names:
                for o in descendants(bpy.data.objects[n]):
                    if not o.hide_render:
                        o.hide_render = True
                        hidden.append(o)
        cam = S["camera"]
        if cam == "door_front":
            root_name, (x0, x1, y0, y1, z0, z1) = PASS[S["opening"]]
            cx = (x0 + x1) / 2
            look(co, A @ Vector((cx + 1.2, y1 + S.get("cam_dist", 7.5), z0 + 1.4)), A @ Vector((cx, y1 - 0.6, z0 + 1.1)))
            cd.lens = S.get("lens", 32)
            sc.camera = co
        elif isinstance(cam, str):
            sc.camera = bpy.data.objects[cam]
        else:
            loc, tgt, lens = cam
            look(co, A @ Vector(loc), A @ Vector(tgt))
            cd.lens = lens
            sc.camera = co
        cd.clip_start = 0.05
        entry = dict(scene=S["name"], anchor=S["anchor"], actors=used)
        if S.get("opening"):
            entry["opening"] = S["opening"]
            # 很小的洞口（松鼠窝）射线量不准，直接用切割体的尺寸
            entry["clearance"] = S.get("opening_size") or opening_clearance(S["opening"])
            ch = entry["clearance"].get("clear_height")
            entry["upright_fit"] = {u["actor"]: (ch is not None and u["height"] < ch) for u in used if u["height"]}
        report["scenes"].append(entry)
        sc.render.filepath = os.path.join(out, S["name"] + ".png")
        bpy.ops.render.render(write_still=True)
        for o in hidden:
            o.hide_render = False
        print("RENDERED", S["name"], json.dumps(entry, ensure_ascii=False), flush=True)
    for n in movable:
        bpy.data.objects[n].matrix_world = saved[n]
    with open(os.path.join(out, "scale_tests.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)


run()
