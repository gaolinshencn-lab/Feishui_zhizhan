# -*- coding: utf-8 -*-
"""大螃蟹与熊大、熊二、光头强的比例检查图：临时把螃蟹骨骼根移到空地上的熊旁边，正交正面渲染，然后放回原处（不保存文件）。

用法：blender -b boonie_bears_forest_map.blend -P render_crab_scale.py -- <输出 png> [采样数]
"""
import bpy
import math
import sys
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
out = argv[0] if argv else "crab_scale.png"
sc = bpy.context.scene
sc.cycles.samples = int(argv[1]) if len(argv) > 1 else 24
crab = bpy.data.objects["LAKE_Crab_Rig"]
da, de, gq = (bpy.data.objects[n] for n in ("XiongDa_Root", "XiongEr_Root", "GuangtouQiang_Root"))
old = crab.matrix_world.copy()
rz = da.rotation_euler.z
right = Matrix.Rotation(rz, 3, "Z") @ Vector((1, 0, 0))
fwd = Matrix.Rotation(rz, 3, "Z") @ Vector((0, -1, 0))
mid = (da.location + de.location) / 2
crab.location = de.location + right * 2.6
crab.location.z = de.location.z
crab.rotation_euler = (0, 0, rz)
gq_old = gq.matrix_world.copy()
gq.location = da.location - right * 1.4
gq.rotation_euler = (0, 0, rz)
cd = bpy.data.cameras.new("Tmp_Crab_Scale")
cd.type = "ORTHO"
cd.ortho_scale = 10.0
co = bpy.data.objects.new("Tmp_Crab_Scale", cd)
sc.collection.objects.link(co)
tgt = (da.location + crab.location) / 2 + Vector((0, 0, 1.2))
co.location = tgt + fwd * 25
co.rotation_euler = (fwd * -1).to_track_quat("-Z", "Y").to_euler()
cd.clip_start, cd.clip_end = 18, 32
sc.camera = co
sc.render.resolution_x, sc.render.resolution_y = 1600, 900
sc.render.filepath = out
bpy.ops.render.render(write_still=True)
crab.matrix_world = old
gq.matrix_world = gq_old
print("RENDERED", out)
