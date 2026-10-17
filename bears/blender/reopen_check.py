# -*- coding: utf-8 -*-
"""重新打开 .blend 后做完整检查：缺失贴图、重复物体、家具悬空/陷地、家具互相穿插、门洞被挡、空集合。

用法：blender -b boonie_bears_forest_map.blend -P reopen_check.py
"""
import bpy
import json
import os
import re
from collections import Counter
from mathutils import Vector

report = []
print("物体", len(bpy.data.objects), "网格", len(bpy.data.meshes), "材质", len(bpy.data.materials), "贴图", len(bpy.data.images))
# 缺失贴图（场景全部是程序化材质，应为 0 张外部贴图）
for im in bpy.data.images:
    if im.source == "FILE" and not os.path.isfile(bpy.path.abspath(im.filepath)):
        report.append(f"缺失贴图: {im.name} {im.filepath}")
# 重复物体：Blender 自动加 .001 后缀的名字，或位置、网格完全相同的两个物体
for o in bpy.data.objects:
    if re.search(r"\.\d{3}$", o.name):
        report.append(f"重复命名: {o.name}")
seen = Counter((o.data.name if o.data else "", tuple(round(v, 3) for v in o.matrix_world.translation)) for o in bpy.data.objects
               if o.type == "MESH")
for k, n in seen.items():
    if n > 1:
        report.append(f"重复物体（同网格同位置）: {k[0]} ×{n}")
# 空集合
for c in bpy.data.collections:
    if not c.all_objects:
        report.append(f"空集合: {c.name}")


def wbox(ob):
    cs = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return [f(c[i] for c in cs) for i in range(3) for f in (min, max)]


items = [o for o in bpy.data.objects if o.get("floor_item")]
boxes = {o.name: wbox(o) for o in items}
for o in items:
    dz = boxes[o.name][4] - o["floor_z_world"]
    if abs(dz) > 0.03:
        report.append(f"家具悬空或陷入地板: {o.name} dz={dz:.3f}")
for i, a in enumerate(items):
    for b in items[i + 1:]:
        if a["room"] != b["room"] or not (a.get("overlap_check") and b.get("overlap_check")):
            continue
        A, B = boxes[a.name], boxes[b.name]
        if min(A[1], B[1]) - max(A[0], B[0]) > 0.02 and min(A[3], B[3]) - max(A[2], B[2]) > 0.02:
            report.append(f"家具互相穿插: {a.name} / {b.name}")
for nm, root, (x0, x1, y0, y1, z0, z1) in json.loads(bpy.context.scene.get("door_passages_json", "[]")):
    M = bpy.data.objects[root].matrix_world
    cs = [M @ Vector((x, y, z)) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
    P = [f(c[i] for c in cs) for i in range(3) for f in (min, max)]
    for o in bpy.data.objects:
        if o.type == "MESH" and (o.get("floor_item") or "Leaf" in o.name or "Barn_Door" in o.name):
            A = boxes.get(o.name) or wbox(o)
            if all(min(A[2 * k + 1], P[2 * k + 1]) - max(A[2 * k], P[2 * k]) > 0 for k in range(3)):
                report.append(f"门洞被挡住: {nm} ← {o.name}")
rooms = Counter(o.get("room") for o in items)
print("各房间落地家具数:", dict(rooms))
print("门洞检查:", [p[0] for p in json.loads(bpy.context.scene.get("door_passages_json", "[]"))])
print("检查问题数:", len(report))
for r in report:
    print("  -", r)
