# -*- coding: utf-8 -*-
"""渲染某一集的单集资产（EPISODE_OVERRIDES/<集合>，平时隐藏）：临时打开这个集合，用集合里的相机渲染，不保存文件。

用法：blender -b boonie_bears_forest_map.blend -P render_episode.py -- <输出目录> <集合名，例如 EP_S1E01_赏花大会> [采样数]
"""
import bpy
import os
import sys

argv = sys.argv[sys.argv.index("--") + 1:]
out, cname = os.path.abspath(argv[0]), argv[1]
os.makedirs(out, exist_ok=True)
sc = bpy.context.scene
sc.cycles.samples = int(argv[2]) if len(argv) > 2 else 16
sc.render.resolution_x, sc.render.resolution_y = 1280, 740
for n in ("EPISODE_OVERRIDES", cname):
    bpy.data.collections[n].hide_render = False
for o in [o for o in bpy.data.collections["Characters"].all_objects if o]:
    o.hide_render = True
for cam in [o for o in bpy.data.collections[cname].objects if o.type == "CAMERA"]:
    sc.camera = cam
    sc.render.filepath = os.path.join(out, cam.name + ".png")
    bpy.ops.render.render(write_still=True)
    print("RENDERED", cam.name, flush=True)
