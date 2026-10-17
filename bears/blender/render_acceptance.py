# -*- coding: utf-8 -*-
"""渲染验收图（Lights_and_Cameras/Acceptance_Cameras 里的相机）。

用法：blender -b boonie_bears_forest_map.blend -P render_acceptance.py -- <输出目录> [采样数] [分辨率百分比] [相机名关键字,...] [相机集合]
相机集合默认是 Acceptance_Cameras；湖泊检查图用 Lake_Check_Cameras。
每台相机的 hide_collections 属性列出渲染时要隐藏的集合（例如拆掉屋顶看室内），渲染完恢复；acc_res 是分辨率。
"""
import bpy
import os
import sys
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
out = os.path.abspath(argv[0] if argv else "acceptance")
samples = int(argv[1]) if len(argv) > 1 else 32
pct = int(argv[2]) if len(argv) > 2 else 100
only = argv[3].split(",") if len(argv) > 3 and argv[3] else []
cam_coll = argv[4] if len(argv) > 4 else "Acceptance_Cameras"
os.makedirs(out, exist_ok=True)
sc = bpy.context.scene
sc.cycles.samples = samples
sc.render.resolution_percentage = pct


def set_hidden(names, hidden):
    for n in names:
        c = bpy.data.collections.get(n)
        if not c:
            continue
        objs = [o for o in c.all_objects if o is not None]
        c.hide_render = hidden
        for o in objs:
            o.hide_render = hidden


def clear_trees(cam, hidden):
    """隐藏相机和目标之间的树木、灌木（clear_trees=True 的室外相机），避免近处树挡住建筑。"""
    if not cam.get("clear_trees") or "view_target" not in cam:
        return []
    c = cam.matrix_world.translation
    t = Vector(cam["view_target"])
    d = (t - c).to_2d()
    L = d.length
    d.normalize()
    out = []
    for cn in ("Forest_Trees", "Forest_Plants"):
        for o in bpy.data.collections[cn].all_objects:
            if o is None or o.name.startswith(("Bears", "Tree_HoneyTree", "Beehive")):
                continue
            v = (o.matrix_world.translation - c).to_2d()
            along = v.dot(d)
            lat = abs(v.x * d.y - v.y * d.x)
            if 0 < along < L - 4 and lat < 0.5 * along + 4:
                o.hide_render = hidden
                out.append(o)
    return out


cams = sorted(bpy.data.collections[cam_coll].objects, key=lambda o: o.name)
for cam in cams:
    if only and not any(k in cam.name for k in only):
        continue
    w, h = (int(v) for v in cam.get("acc_res", "1600x1000").split("x"))
    sc.render.resolution_x, sc.render.resolution_y = w, h
    hide = [n for n in cam.get("hide_collections", "").split(",") if n]
    set_hidden(hide, True)
    trees = clear_trees(cam, True)
    sc.camera = cam
    sc.render.filepath = os.path.join(out, cam.name + ".png")
    bpy.ops.render.render(write_still=True)
    set_hidden(hide, False)
    for o in trees:
        o.hide_render = False
    print("RENDERED", cam.name, flush=True)
sc.camera = bpy.data.objects["Cam_Map_Overview"]
