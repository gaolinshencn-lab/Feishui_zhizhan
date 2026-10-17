# -*- coding: utf-8 -*-
"""渲染所有检查视图（Lights_and_Cameras/Check_Cameras 里的正交相机）。

用法：blender -b boonie_bears_forest_map.blend -P render_checks.py -- <输出目录> [采样数]
渲染室内平面图时会临时隐藏 GQ_House_Roof_Removable（可拆屋顶），渲染完恢复。
拼图：python3 make_check_sheets.py <输出目录>（需要 Pillow）。
"""
import bpy
import json
import os
import sys
from bpy_extras.object_utils import world_to_camera_view

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
out = os.path.abspath(argv[0] if argv else "check_views")
samples = int(argv[1]) if len(argv) > 1 else 24
os.makedirs(out, exist_ok=True)
sc = bpy.context.scene
sc.cycles.samples = samples
roof = bpy.data.collections["GQ_House_Roof_Removable"]
cams = sorted(bpy.data.collections["Check_Cameras"].objects, key=lambda o: o.name)
for cam in cams:
    w, h = (int(v) for v in cam.get("check_res", "800x800").split("x"))
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.camera = cam
    interior = "Interior_Plan" in cam.name
    roof.hide_render = interior
    for o in [o for o in roof.all_objects if o is not None]:
        o.hide_render = interior
    if interior:
        # 室内平面图的家具标注：每个家具在画面里的位置（0–1）和中文名
        labels = []
        for o in bpy.data.collections["GuangtouQiang_House_Interior"].all_objects:
            if o.type == "MESH" and o.get("name_cn") and not any(k in o.name for k in ("Wall", "Floor", "Partition", "Door", "Lamp", "Chili", "Corn")):
                p = world_to_camera_view(sc, cam, o.matrix_world.translation)
                labels.append(dict(name=o.name, cn=o["name_cn"], x=p.x, y=p.y, status=o.get("position_status", o.get("ref_status", ""))))
        json.dump(labels, open(os.path.join(out, cam.name + ".labels.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    sc.render.filepath = os.path.join(out, cam.name + ".png")
    bpy.ops.render.render(write_still=True)
    roof.hide_render = False
    for o in [o for o in roof.all_objects if o is not None]:
        o.hide_render = False
    print("RENDERED", cam.name, flush=True)
sc.camera = bpy.data.objects["Cam_Map_Overview"]
