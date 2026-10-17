# -*- coding: utf-8 -*-
"""渲染剧照对位相机（Lights_and_Cameras/Still_Match_Cameras，以及湖底的 Lake_05_Ref_Still_Match_L1）。

用法：blender -b boonie_bears_forest_map.blend -P render_still_match.py -- <输出目录> [采样数] [相机名关键字,...]
相机的 match_setup 属性写着渲染前要做的临时调整（例如 open_shutters：把正面格子窗扇向外上翻 35°，对照 A45）；clear_near 属性：隐藏相机前这么多米以内挡视线的树。渲染完恢复，不保存文件。
"""
import bpy
import math
import os
import sys
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
out = os.path.abspath(argv[0] if argv else "still_match")
samples = int(argv[1]) if len(argv) > 1 else 24
only = argv[2].split(",") if len(argv) > 2 and argv[2] else []
os.makedirs(out, exist_ok=True)
sc = bpy.context.scene
sc.cycles.samples = samples
sc.render.resolution_x, sc.render.resolution_y = 1280, 740
cams = list(bpy.data.collections["Still_Match_Cameras"].objects)
if "Lake_05_Ref_Still_Match_L1" in bpy.data.objects:
    cams.append(bpy.data.objects["Lake_05_Ref_Still_Match_L1"])
chars = [o for o in bpy.data.collections["Characters"].all_objects if o is not None]
for cam in sorted(cams, key=lambda o: o.name):
    if only and not any(k in cam.name for k in only):
        continue
    undo = []
    if "open_shutters" in cam.get("match_setup", ""):
        for o in bpy.data.objects:
            if o.name.endswith("_Shutter") and "open_rotation_x_deg" in o:
                undo.append((o, tuple(o.rotation_euler)))
                o.rotation_euler.x = math.radians(o["open_rotation_x_deg"])
    for o in chars:
        o.hide_render = True
    hide = [c for c in cam.get("hide_collections", "").split(",") if c in bpy.data.collections]
    for c in hide:
        for o in [o for o in bpy.data.collections[c].all_objects if o is not None]:
            o.hide_render = True
    trees = []
    if cam.get("clear_near"):  # 隐藏相机前方近处的树（剧照里这个位置没有树挡着）
        c = cam.matrix_world.translation
        d = (cam.matrix_world.to_3x3() @ Vector((0, 0, -1))).to_2d().normalized()
        for cn in ("Forest_Trees", "Forest_Plants"):
            for o in [o for o in bpy.data.collections[cn].all_objects if o is not None]:
                if o.name.startswith(("Bears", "BEAR_HOME_", "Tree_HoneyTree", "FOREST_Tree_HoneyTree", "Beehive")):
                    continue
                v = (o.matrix_world.translation - c).to_2d()
                along = v.dot(d)
                if -2 < along < cam["clear_near"] and abs(v.x * d.y - v.y * d.x) < 0.6 * max(along, 0) + 3 and not o.hide_render:
                    o.hide_render = True
                    trees.append(o)
    sc.camera = cam
    sc.render.filepath = os.path.join(out, cam.name + ".png")
    bpy.ops.render.render(write_still=True)
    for o, r in undo:
        o.rotation_euler = r
    for c in hide:
        for o in [o for o in bpy.data.collections[c].all_objects if o is not None]:
            o.hide_render = False
    for o in chars + trees:
        o.hide_render = False
    print("RENDERED", cam.name, flush=True)
