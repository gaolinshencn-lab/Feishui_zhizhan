# -*- coding: utf-8 -*-
"""剧照对位相机的验收渲染：画幅和参考图完全相同（相机属性 ref_size，例如 "1248x720"），可以出灰模。

用法：blender -b boonie_bears_forest_map.blend -P render_match.py -- <输出目录> <相机名,...> [clay|material] [采样数]
  clay：所有物体用同一种浅灰材质（只看轮廓、比例、遮挡关系）；material：正常材质。
  相机的 hide_collections、clear_near、match_setup 属性和 render_still_match.py 一样处理；角色隐藏。
"""
import bpy
import math
import os
import sys
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
out = os.path.abspath(argv[0])
names = argv[1].split(",")
clay = len(argv) > 2 and argv[2] == "clay"
sc = bpy.context.scene
sc.cycles.samples = int(argv[3]) if len(argv) > 3 else 16
os.makedirs(out, exist_ok=True)
vl = bpy.context.view_layer
if clay:
    m = bpy.data.materials.new("Clay_Grey")
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.62, 0.62, 0.62, 1)
    b.inputs["Roughness"].default_value = 0.8
    vl.material_override = m
chars = [o for o in bpy.data.collections["Characters"].all_objects if o is not None]
for o in chars:
    o.hide_render = True
for n in names:
    cam = bpy.data.objects[n]
    w, h = (int(v) for v in cam.get("ref_size", "1280x740").split("x"))
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = w, h, 100
    hidden = []
    for cn in [c for c in cam.get("hide_collections", "").split(",") if c in bpy.data.collections]:
        for o in list(bpy.data.collections[cn].all_objects):
            if o and not o.hide_render:
                o.hide_render = True
                hidden.append(o)
    if cam.get("clear_near"):
        c = cam.matrix_world.translation
        d = (cam.matrix_world.to_3x3() @ Vector((0, 0, -1))).to_2d().normalized()
        for cn in ("Forest_Trees", "Forest_Plants"):
            for o in list(bpy.data.collections[cn].all_objects):
                if o is None or o.hide_render or o.name.startswith(("BEAR_HOME", "Bears")):
                    continue
                v = (o.matrix_world.translation - c).to_2d()
                along = v.dot(d)
                if -2 < along < cam["clear_near"] and abs(v.x * d.y - v.y * d.x) < 0.6 * max(along, 0) + 3:
                    o.hide_render = True
                    hidden.append(o)
    undo = []
    if "open_shutters" in cam.get("match_setup", ""):
        for o in bpy.data.objects:
            if o.name.endswith("_Shutter") and "open_rotation_x_deg" in o:
                undo.append((o, tuple(o.rotation_euler)))
                o.rotation_euler.x = math.radians(o["open_rotation_x_deg"])
    sc.camera = cam
    sc.render.filepath = os.path.join(out, n + ("_clay" if clay else "") + ".png")
    bpy.ops.render.render(write_still=True)
    for o in hidden:
        o.hide_render = False
    for o, r in undo:
        o.rotation_euler = r
    print("RENDERED", n, w, h, flush=True)
