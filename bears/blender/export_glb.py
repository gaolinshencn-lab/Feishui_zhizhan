# -*- coding: utf-8 -*-
"""P5：按区域导出 .glb（修改器和布尔开洞都应用到网格上；自定义属性 cn/status/note 写进 glTF extras）。

用法：blender -b boonie_bears_forest_map.blend -P export_glb.py -- <输出目录>

每个区域一个文件，另外导出一个不含森林的总图（树木太多，单独成文件）。相机、灯光、隐藏的原型和布尔切割体不导出。
体积材质（湖水体积、瀑布水雾）在 glTF 里没有对应，只导出网格外形。
"""
import bpy
import json
import os
import sys

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
out = os.path.abspath(argv[0] if argv else "glb")
os.makedirs(out, exist_ok=True)

GROUPS = {
    "HOUSE_and_WAREHOUSE": ["GuangtouQiang_House_Exterior", "GuangtouQiang_House_Interior", "GuangtouQiang_Warehouse", "Props", "Vehicles"],
    "BEAR_HOME": ["Bears_TreeHome"],
    "MONKEY_CAVE": ["MonkeyCave"],
    "SQUIRREL_NEST": ["SquirrelNest"],
    "LAKE": ["River_and_Rocks"],
    "TERRAIN": ["Terrain"],
    "FOREST": ["Forest_Trees", "Forest_Plants", "SEASON_AUTUMN"],
    "CHARACTERS": ["Characters"],
}
SKIP_COLL = {"Bears_TreeHome"}  # 熊洞在 Forest_Trees 下面，导出森林时跳过它（它有自己的文件）


def objects_of(names, skip=()):
    res = set()

    def walk(c):
        if c.name in skip:
            return
        for o in c.objects:
            res.add(o)
        for ch in c.children:
            walk(ch)
    for n in names:
        if n in bpy.data.collections:
            walk(bpy.data.collections[n])
    keep = []
    for o in res:
        if o.type not in ("MESH", "EMPTY", "ARMATURE"):
            continue
        if o.display_type == "WIRE" or o.hide_render or o.name.startswith("Proto_"):
            continue  # 布尔切割体、隐藏物体、原型
        keep.append(o)
    return keep


def export(name, obs):
    bpy.ops.object.select_all(action="DESELECT")
    n = 0
    for o in obs:
        try:
            o.hide_set(False)
            o.select_set(True)
            n += 1
        except RuntimeError:
            pass  # 不在当前视图层（被排除的集合）
    path = os.path.join(out, name + ".glb")
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_apply=True,
                              export_extras=True, export_cameras=False, export_lights=False, export_yup=True)
    size = os.path.getsize(path)
    dg = bpy.context.evaluated_depsgraph_get()
    tris = 0
    for o in obs:
        if o.type == "MESH":
            me = o.evaluated_get(dg).to_mesh()
            me.calc_loop_triangles()
            tris += len(me.loop_triangles)
            o.evaluated_get(dg).to_mesh_clear()
    print("EXPORTED", name, n, f"{size / 1e6:.1f} MB", f"{tris} tris", flush=True)
    return dict(file=name + ".glb", objects=n, mb=round(size / 1e6, 2), triangles=tris)


report = {}
for g, cols in GROUPS.items():
    report[g] = export(g, objects_of(cols, SKIP_COLL if g == "FOREST" else ()))
with open(os.path.join(out, "glb_export_report.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=1)
