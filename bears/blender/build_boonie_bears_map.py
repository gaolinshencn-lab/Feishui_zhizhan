# -*- coding: utf-8 -*-
"""
build_boonie_bears_map.py — 熊出没·狗熊岭森林 3D 地图（Blender 自动建模脚本）

用法
  1. Blender 图形界面：Scripting 工作区 → 打开本文件 → Run Script。
     场景会被清空后重建，并保存为脚本同目录（或当前 .blend 所在目录，都没有时为用户主目录）
     下的 boonie_bears_forest_map.blend。
  2. 命令行（无界面）：
       blender -b -P build_boonie_bears_map.py -- --out /path/boonie_bears_forest_map.blend \
               --render /path/preview.png [--render-interior /path/interior.png] [--samples 48]

适用 Blender 4.2 LTS 及以上（在 4.5 LTS 上测试）。全部几何体和材质都由脚本生成，
没有外部图片、字体或贴图路径。

比例：1 Blender unit = 1 m。比例基准：熊大身高 2.0 m。其余尺寸都是估算值，见 REFERENCE_NOTES.md。
参考依据与推测内容的划分也见 REFERENCE_NOTES.md；推测模型带自定义属性 ref_status = "inferred"，
并同时链接进 Reference_Notes/Inferred_Models 集合。

这是非官方同人作品。《熊出没》及其角色版权归华强方特所有；本脚本没有使用任何官方模型或素材。
"""
import bpy
import bmesh
import math
import os
import random
import sys
from mathutils import Vector, Matrix, Euler, noise

SEED = 2014
random.seed(SEED)

# ------------------------------------------------------------------------------------------------
# 命令行参数与输出路径

ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def _arg(name, default=None):
    if name in ARGV:
        i = ARGV.index(name)
        if i + 1 < len(ARGV):
            return ARGV[i + 1]
    return default


def _default_dir():
    here = globals().get("__file__", "")
    if here and os.path.isfile(here):
        return os.path.dirname(os.path.abspath(here))
    if bpy.data.filepath:
        return os.path.dirname(bpy.data.filepath)
    return os.path.expanduser("~")


OUT_BLEND = _arg("--out") or os.path.join(_default_dir(), "boonie_bears_forest_map.blend")
RENDER_PATH = _arg("--render")
RENDER_INTERIOR = _arg("--render-interior")
SAMPLES = int(_arg("--samples", "48"))
RES = tuple(int(v) for v in _arg("--res", "1600x900").split("x"))

# ------------------------------------------------------------------------------------------------
# 基础工具


def lerp(a, b, t):
    return a + (b - a) * t


def clamp(v, a, b):
    return max(a, min(b, v))


def smooth(e0, e1, x):
    t = clamp((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def srgb(hexstr, a=1.0):
    h = hexstr.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    lin = [((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c]
    return (lin[0], lin[1], lin[2], a)


def trs(loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1)):
    return Matrix.LocRotScale(Vector(loc), Euler(rot, "XYZ"), Vector(scale))


def fbm(x, y, octaves=4, seed_off=0.0):
    s, amp, f = 0.0, 0.5, 1.0
    for _ in range(octaves):
        s += amp * noise.noise(Vector((x * f + seed_off, y * f - seed_off * 0.7, seed_off * 0.3)))
        f *= 2.03
        amp *= 0.5
    return s


def dist_to_polyline(x, y, pts):
    best = 1e9
    for (ax, ay), (bx, by) in zip(pts[:-1], pts[1:]):
        dx, dy = bx - ax, by - ay
        l2 = dx * dx + dy * dy or 1.0
        t = clamp(((x - ax) * dx + (y - ay) * dy) / l2, 0, 1)
        qx, qy = ax + dx * t - x, ay + dy * t - y
        best = min(best, qx * qx + qy * qy)
    return math.sqrt(best)


# ------------------------------------------------------------------------------------------------
# 清空场景（可重复运行）


def reset_scene():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)
    for blocks in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.lights,
                   bpy.data.curves, bpy.data.node_groups, bpy.data.images):
        for b in list(blocks):
            if b.users == 0:
                blocks.remove(b)
    t = bpy.data.texts.get("Reference_Notes.md")
    if t:
        bpy.data.texts.remove(t)


# ------------------------------------------------------------------------------------------------
# 集合

COLL = {}


def coll(name, parent=None):
    if name in COLL:
        return COLL[name]
    c = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(c)
    COLL[name] = c
    return c


def setup_collections():
    for n in ["Terrain", "Forest_Trees", "Forest_Plants", "River_and_Rocks", "GuangtouQiang_House_Exterior",
              "GuangtouQiang_House_Interior", "Characters", "Vehicles", "Props", "Lights_and_Cameras",
              "Reference_Notes"]:
        coll(n)
    coll("GQ_House_Roof_Removable", COLL["GuangtouQiang_House_Exterior"])
    coll("Bears_TreeHome", COLL["Forest_Trees"])
    coll("Inferred_Models", COLL["Reference_Notes"])
    coll("Prototypes_Hidden", COLL["Reference_Notes"])
    for n in ["Characters_XiongDa", "Characters_XiongEr", "Characters_GuangtouQiang",
              "Characters_TuTu", "Characters_LuoBoTou", "Characters_BengBeng"]:
        coll(n, COLL["Characters"])


# ------------------------------------------------------------------------------------------------
# 材质（全部程序化，无外部贴图）

MATS = {}


def _set(node, names, value):
    for n in names if isinstance(names, (list, tuple)) else [names]:
        if n in node.inputs:
            node.inputs[n].default_value = value
            return True
    return False


def _new_mat(name):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    return m


def mat(name, color, rough=0.8, metal=0.0, emit=None, emit_strength=0.0, alpha=1.0, transmission=0.0, ior=1.45):
    if name in MATS:
        return MATS[name]
    m = _new_mat(name)
    b = m.node_tree.nodes.get("Principled BSDF")
    _set(b, "Base Color", srgb(color))
    _set(b, "Roughness", rough)
    _set(b, "Metallic", metal)
    _set(b, "IOR", ior)
    if emit:
        _set(b, ["Emission Color", "Emission"], srgb(emit))
        _set(b, "Emission Strength", emit_strength)
    if transmission:
        _set(b, ["Transmission Weight", "Transmission"], transmission)
    if alpha < 1.0:
        _set(b, "Alpha", alpha)
        try:
            m.blend_method = "BLEND"
        except Exception:
            pass
    m.diffuse_color = srgb(color)
    MATS[name] = m
    return m


def _nodes(m):
    return m.node_tree.nodes, m.node_tree.links


def mat_noise(name, c1, c2, scale=6.0, rough=0.85, bump=0.15, detail=4.0, ramp=(0.35, 0.65)):
    """两色噪声材质（树皮、木头、岩石、草地等）。"""
    if name in MATS:
        return MATS[name]
    m = _new_mat(name)
    nodes, links = _nodes(m)
    b = nodes.get("Principled BSDF")
    tc = nodes.new("ShaderNodeTexCoord")
    nz = nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = scale
    nz.inputs["Detail"].default_value = detail
    cr = nodes.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].position = ramp[0]
    cr.color_ramp.elements[1].position = ramp[1]
    cr.color_ramp.elements[0].color = srgb(c1)
    cr.color_ramp.elements[1].color = srgb(c2)
    links.new(tc.outputs["Object"], nz.inputs["Vector"])
    links.new(nz.outputs["Fac"], cr.inputs["Fac"])
    links.new(cr.outputs["Color"], b.inputs["Base Color"])
    _set(b, "Roughness", rough)
    if bump:
        bp = nodes.new("ShaderNodeBump")
        bp.inputs["Strength"].default_value = bump
        links.new(nz.outputs["Fac"], bp.inputs["Height"])
        links.new(bp.outputs["Normal"], b.inputs["Normal"])
    m.diffuse_color = srgb(c1)
    MATS[name] = m
    return m


def mat_birch_bark():
    name = "Bark_Birch"
    if name in MATS:
        return MATS[name]
    m = _new_mat(name)
    nodes, links = _nodes(m)
    b = nodes.get("Principled BSDF")
    tc = nodes.new("ShaderNodeTexCoord")
    mp = nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (6.0, 6.0, 1.5)
    nz = nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 3.0
    cr = nodes.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].position = 0.62
    cr.color_ramp.elements[1].position = 0.66
    cr.color_ramp.elements[0].color = srgb("#efece4")
    cr.color_ramp.elements[1].color = srgb("#2e2a26")
    links.new(tc.outputs["Object"], mp.inputs["Vector"])
    links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    links.new(nz.outputs["Fac"], cr.inputs["Fac"])
    links.new(cr.outputs["Color"], b.inputs["Base Color"])
    _set(b, "Roughness", 0.75)
    m.diffuse_color = srgb("#efece4")
    MATS[name] = m
    return m


def mat_vertex_color(name, attr="Col", rough=0.95, var_scale=0.6, bump=0.25):
    """读取顶点色的地形材质，叠加细小噪声明暗变化和凹凸。"""
    if name in MATS:
        return MATS[name]
    m = _new_mat(name)
    nodes, links = _nodes(m)
    b = nodes.get("Principled BSDF")
    vc = nodes.new("ShaderNodeVertexColor")
    vc.layer_name = attr
    tc = nodes.new("ShaderNodeTexCoord")
    nz = nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = var_scale
    nz.inputs["Detail"].default_value = 6.0
    links.new(tc.outputs["Object"], nz.inputs["Vector"])
    mr = nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = 0.8
    mr.inputs["To Max"].default_value = 1.15
    links.new(nz.outputs["Fac"], mr.inputs["Value"])
    mix = nodes.new("ShaderNodeVectorMath")
    mix.operation = "SCALE"
    links.new(vc.outputs["Color"], mix.inputs[0])
    links.new(mr.outputs["Result"], mix.inputs["Scale"])
    links.new(mix.outputs["Vector"], b.inputs["Base Color"])
    _set(b, "Roughness", rough)
    nz2 = nodes.new("ShaderNodeTexNoise")
    nz2.inputs["Scale"].default_value = 9.0
    links.new(tc.outputs["Object"], nz2.inputs["Vector"])
    bp = nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = bump
    links.new(nz2.outputs["Fac"], bp.inputs["Height"])
    links.new(bp.outputs["Normal"], b.inputs["Normal"])
    m.diffuse_color = srgb("#6aa848")
    MATS[name] = m
    return m


def mat_water(name, color, deep, rough=0.04):
    if name in MATS:
        return MATS[name]
    m = _new_mat(name)
    nodes, links = _nodes(m)
    b = nodes.get("Principled BSDF")
    _set(b, "Base Color", srgb(color))
    _set(b, "Roughness", rough)
    _set(b, "IOR", 1.33)
    _set(b, ["Transmission Weight", "Transmission"], 0.55)
    tc = nodes.new("ShaderNodeTexCoord")
    wv = nodes.new("ShaderNodeTexNoise")
    wv.inputs["Scale"].default_value = 0.35
    wv.inputs["Detail"].default_value = 3.0
    links.new(tc.outputs["Object"], wv.inputs["Vector"])
    bp = nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.08
    links.new(wv.outputs["Fac"], bp.inputs["Height"])
    links.new(bp.outputs["Normal"], b.inputs["Normal"])
    m.diffuse_color = srgb(deep)
    MATS[name] = m
    return m


def mat_waterfall():
    name = "Water_Waterfall"
    if name in MATS:
        return MATS[name]
    m = _new_mat(name)
    nodes, links = _nodes(m)
    b = nodes.get("Principled BSDF")
    tc = nodes.new("ShaderNodeTexCoord")
    mp = nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (8.0, 8.0, 0.6)
    wv = nodes.new("ShaderNodeTexNoise")
    wv.inputs["Scale"].default_value = 2.0
    cr = nodes.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].color = srgb("#8fb4d6")
    cr.color_ramp.elements[1].color = srgb("#f4f8ff")
    links.new(tc.outputs["Object"], mp.inputs["Vector"])
    links.new(mp.outputs["Vector"], wv.inputs["Vector"])
    links.new(wv.outputs["Fac"], cr.inputs["Fac"])
    links.new(cr.outputs["Color"], b.inputs["Base Color"])
    _set(b, "Roughness", 0.2)
    _set(b, ["Emission Color", "Emission"], srgb("#dfe9f5"))
    _set(b, "Emission Strength", 0.6)
    m.diffuse_color = srgb("#cfe0f2")
    MATS[name] = m
    return m


def mat_quilt():
    """U6：蓝底白花被子（程序化花纹 + 紫色补丁）。"""
    name = "Fabric_Quilt_BlueFloral"
    if name in MATS:
        return MATS[name]
    m = _new_mat(name)
    nodes, links = _nodes(m)
    b = nodes.get("Principled BSDF")
    tc = nodes.new("ShaderNodeTexCoord")
    vo = nodes.new("ShaderNodeTexVoronoi")
    vo.inputs["Scale"].default_value = 9.0
    cr = nodes.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].position = 0.12
    cr.color_ramp.elements[1].position = 0.16
    cr.color_ramp.elements[0].color = srgb("#e3ecfb")
    cr.color_ramp.elements[1].color = srgb("#2c4f9e")
    links.new(tc.outputs["Object"], vo.inputs["Vector"])
    links.new(vo.outputs["Distance"], cr.inputs["Fac"])
    # 大块补丁
    vo2 = nodes.new("ShaderNodeTexVoronoi")
    vo2.inputs["Scale"].default_value = 1.6
    cr2 = nodes.new("ShaderNodeValToRGB")
    cr2.color_ramp.interpolation = "CONSTANT"
    cr2.color_ramp.elements[0].position = 0.0
    cr2.color_ramp.elements[1].position = 0.8
    links.new(tc.outputs["Object"], vo2.inputs["Vector"])
    links.new(vo2.outputs["Color"], cr2.inputs["Fac"])
    mix = nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs["B"].default_value = srgb("#4a3d97")
    links.new(cr2.outputs["Color"], mix.inputs["Factor"])
    links.new(cr.outputs["Color"], mix.inputs["A"])
    links.new(mix.outputs["Result"], b.inputs["Base Color"])
    _set(b, "Roughness", 0.9)
    m.diffuse_color = srgb("#2c4f9e")
    MATS[name] = m
    return m


def mat_stripes(name, c1, c2, scale=40.0, axis="X", rough=0.8):
    """竹席、木板条纹。"""
    if name in MATS:
        return MATS[name]
    m = _new_mat(name)
    nodes, links = _nodes(m)
    b = nodes.get("Principled BSDF")
    tc = nodes.new("ShaderNodeTexCoord")
    wv = nodes.new("ShaderNodeTexWave")
    wv.wave_type = "BANDS"
    wv.bands_direction = axis
    wv.inputs["Scale"].default_value = scale
    cr = nodes.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].color = srgb(c1)
    cr.color_ramp.elements[1].color = srgb(c2)
    links.new(tc.outputs["Object"], wv.inputs["Vector"])
    links.new(wv.outputs["Fac"], cr.inputs["Fac"])
    links.new(cr.outputs["Color"], b.inputs["Base Color"])
    _set(b, "Roughness", rough)
    m.diffuse_color = srgb(c1)
    MATS[name] = m
    return m


def mat_stone_floor():
    """U4：灰色不规则石板地面。"""
    name = "Stone_Floor_Tiles"
    if name in MATS:
        return MATS[name]
    m = _new_mat(name)
    nodes, links = _nodes(m)
    b = nodes.get("Principled BSDF")
    tc = nodes.new("ShaderNodeTexCoord")
    vo = nodes.new("ShaderNodeTexVoronoi")
    vo.feature = "DISTANCE_TO_EDGE"
    vo.inputs["Scale"].default_value = 2.2
    cr = nodes.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].position = 0.02
    cr.color_ramp.elements[1].position = 0.05
    cr.color_ramp.elements[0].color = srgb("#4f575d")
    cr.color_ramp.elements[1].color = srgb("#8a959c")
    links.new(tc.outputs["Object"], vo.inputs["Vector"])
    links.new(vo.outputs["Distance"], cr.inputs["Fac"])
    links.new(cr.outputs["Color"], b.inputs["Base Color"])
    bp = nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.4
    links.new(cr.outputs["Color"], bp.inputs["Height"])
    links.new(bp.outputs["Normal"], b.inputs["Normal"])
    _set(b, "Roughness", 0.9)
    m.diffuse_color = srgb("#7f8a92")
    MATS[name] = m
    return m


# ------------------------------------------------------------------------------------------------
# bmesh 几何构件


def _faces(ret):
    fs = set()
    for v in ret["verts"]:
        fs.update(v.link_faces)
    return fs


def _mi(faces, mi):
    for f in faces:
        f.material_index = mi
    return faces


def bm_cube(bm, size, loc=(0, 0, 0), rot=(0, 0, 0), mi=0):
    ret = bmesh.ops.create_cube(bm, size=1.0, matrix=trs(loc, rot, size))
    return _mi(_faces(ret), mi)


def bm_cyl(bm, r1, r2, depth, loc=(0, 0, 0), rot=(0, 0, 0), seg=12, mi=0, caps=True):
    ret = bmesh.ops.create_cone(bm, cap_ends=caps, cap_tris=False, segments=seg, radius1=r1, radius2=r2,
                                depth=depth, matrix=trs(loc, rot))
    return _mi(_faces(ret), mi)


def bm_sphere(bm, radii, loc=(0, 0, 0), rot=(0, 0, 0), seg=16, rings=10, mi=0, deform=None, region=None):
    """变形球体：deform(co) 在单位球空间里改形；region(n) 返回面所用的材质序号。"""
    ret = bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=1.0)
    verts = ret["verts"]
    faces = _faces(ret)
    for f in faces:
        f.material_index = region(f.calc_center_median()) if region else mi
    M = trs(loc, rot, radii)
    for v in verts:
        co = deform(v.co.copy()) if deform else v.co
        v.co = M @ co
    return faces


def bm_ico(bm, r, loc=(0, 0, 0), scale=(1, 1, 1), subdiv=2, mi=0, rough=0.0, seed=0.0):
    ret = bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
    for v in ret["verts"]:
        if rough:
            k = 1.0 + rough * noise.noise(v.co * 1.7 + Vector((seed, seed * 0.3, -seed)))
            v.co *= k
        v.co = trs(loc, (0, 0, 0), (r * scale[0], r * scale[1], r * scale[2])) @ v.co
    return _mi(_faces(ret), mi)


def bm_tube(bm, pts, radii, seg=8, mi=0, caps=True):
    """沿折线的管子（树干、树枝、四肢、水管、尾巴）。"""
    pts = [Vector(p) for p in pts]
    n = len(pts)
    t0 = (pts[1] - pts[0]).normalized()
    up = Vector((0, 0, 1)) if abs(t0.z) < 0.9 else Vector((1, 0, 0))
    nrm = t0.cross(up).normalized()
    rings = []
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        nrm = (nrm - t * nrm.dot(t)).normalized()
        bi = t.cross(nrm)
        ring = []
        for k in range(seg):
            a = 2 * math.pi * k / seg
            ring.append(bm.verts.new(p + (nrm * math.cos(a) + bi * math.sin(a)) * radii[i]))
        rings.append(ring)
    faces = []
    for i in range(n - 1):
        for k in range(seg):
            f = bm.faces.new((rings[i][k], rings[i][(k + 1) % seg], rings[i + 1][(k + 1) % seg], rings[i + 1][k]))
            f.material_index = mi
            faces.append(f)
    if caps:
        for ring in (rings[0], rings[-1]):
            f = bm.faces.new(ring)
            f.material_index = mi
            faces.append(f)
    return faces


def bm_torus(bm, R, r, loc=(0, 0, 0), rot=(0, 0, 0), seg=24, rseg=8, mi=0, scale=(1, 1, 1), arc=2 * math.pi):
    M = trs(loc, rot, scale)
    closed = arc >= 2 * math.pi - 1e-6
    n = seg if closed else seg + 1
    rings = []
    for i in range(n):
        a = arc * i / seg
        c = Vector((math.cos(a) * R, math.sin(a) * R, 0))
        d = Vector((math.cos(a), math.sin(a), 0))
        rings.append([bm.verts.new(M @ (c + d * math.cos(b) * r + Vector((0, 0, math.sin(b) * r))))
                      for b in [2 * math.pi * k / rseg for k in range(rseg)]])
    faces = []
    for i in range(seg if closed else seg):
        j = (i + 1) % n
        for k in range(rseg):
            f = bm.faces.new((rings[i][k], rings[i][(k + 1) % rseg], rings[j][(k + 1) % rseg], rings[j][k]))
            f.material_index = mi
            faces.append(f)
    return faces


def bm_plane(bm, w, h, loc=(0, 0, 0), rot=(0, 0, 0), mi=0, sub=1):
    M = trs(loc, rot)
    vs = []
    for j in range(sub + 1):
        row = []
        for i in range(sub + 1):
            row.append(bm.verts.new(M @ Vector(((i / sub - 0.5) * w, (j / sub - 0.5) * h, 0))))
        vs.append(row)
    faces = []
    for j in range(sub):
        for i in range(sub):
            f = bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
            f.material_index = mi
            faces.append(f)
    return faces


def new_obj(name, bm, collection, mats, smooth_shade=False, subsurf=0, props=None, recalc=True, parent=None):
    if recalc:
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    if smooth_shade:
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    ob = bpy.data.objects.new(name, me)
    collection.objects.link(ob)
    if subsurf:
        md = ob.modifiers.new("Subdivision", "SUBSURF")
        md.levels = 1
        md.render_levels = subsurf
    if parent:
        ob.parent = parent
    tag(ob, **(props or {}))
    return ob


def linked(proto, name, collection, loc, rot=(0, 0, 0), scale=1.0, props=None):
    ob = bpy.data.objects.new(name, proto.data)
    collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = rot
    ob.scale = (scale, scale, scale) if isinstance(scale, (int, float)) else scale
    tag(ob, **(props or {}))
    return ob


def empty(name, collection, loc=(0, 0, 0), rot=(0, 0, 0), size=0.5, parent=None, props=None):
    e = bpy.data.objects.new(name, None)
    e.empty_display_size = size
    e.empty_display_type = "PLAIN_AXES"
    e.location = loc
    e.rotation_euler = rot
    collection.objects.link(e)
    if parent:
        e.parent = parent
    tag(e, **(props or {}))
    return e


def tag(ob, cn=None, status=None, note=None):
    if cn:
        ob["name_cn"] = cn
    if status:
        ob["ref_status"] = status
        if status == "inferred":
            inf = COLL.get("Inferred_Models")
            if inf and ob.name not in inf.objects:
                inf.objects.link(ob)
    if note:
        ob["ref_note"] = note


# ------------------------------------------------------------------------------------------------
# 布局（阶段 2；推测布局，见 REFERENCE_NOTES.md）

CORE = (160.0, 120.0)
TERRAIN = (240.0, 200.0)
LAKE = dict(x=-50.0, y=-22.0, rx=22.0, ry=14.0, level=0.0)
CLIFF = dict(a0=math.radians(108), a1=math.radians(162), fall=math.radians(134), height=12.0)
MEADOW = (6.0, -6.0, 15.0)
HOUSE = dict(x=34.0, y=-28.0, rot=0.0)  # 正面朝北（+Y）
YARD = (36.0, -20.0, 14.0)
LOGYARD = (49.0, -30.0, 7.0)
BEARHOME = dict(x=20.0, y=18.0, rot=math.radians(-140))  # 树洞门朝西南（空地方向）
HONEYTREE = (29.0, 28.0)

PATHS = [
    dict(name="Path_House_Meadow", w=2.0, pts=[(33, -20.5), (26, -16), (16, -11), (6, -6)]),
    dict(name="Path_Meadow_BearsHome", w=1.8, pts=[(6, -6), (9, 3), (14, 10), (17.5, 14.5)]),
    dict(name="Path_BearsHome_HoneyTree", w=1.3, pts=[(21, 20), (25, 24), (28, 27)]),
    dict(name="Path_Meadow_LakeBeach", w=1.8, pts=[(6, -6), (-6, -14), (-18, -24), (-31, -32)]),
    dict(name="Road_House_East", w=3.6, pts=[(38, -18.5), (50, -16), (64, -13), (82, -11), (125, -9)]),
]
CLEARINGS = [(MEADOW[0], MEADOW[1], MEADOW[2]), (YARD[0], YARD[1], YARD[2]), (LOGYARD[0], LOGYARD[1], LOGYARD[2]),
             (BEARHOME["x"], BEARHOME["y"], 7.5), (HONEYTREE[0], HONEYTREE[1], 4.5)]


def lake_e(x, y):
    return math.hypot((x - LAKE["x"]) / LAKE["rx"], (y - LAKE["y"]) / LAKE["ry"])


def lake_angle(x, y):
    return math.atan2((y - LAKE["y"]) / LAKE["ry"], (x - LAKE["x"]) / LAKE["rx"])


def lake_point(a, e=1.0):
    return (LAKE["x"] + math.cos(a) * LAKE["rx"] * e, LAKE["y"] + math.sin(a) * LAKE["ry"] * e)


def in_cliff_arc(a, pad=0.0):
    return CLIFF["a0"] - pad <= a <= CLIFF["a1"] + pad


def path_dist(x, y):
    return min(dist_to_polyline(x, y, p["pts"]) - p["w"] * 0.5 for p in PATHS)


def _base_height(x, y):
    h = 1.2 + 1.6 * fbm(x * 0.022, y * 0.022, 4, 3.1) + 0.35 * fbm(x * 0.09, y * 0.09, 2, 7.7)
    # 北面山脊
    h += smooth(28, 75, y) * (9 + 7 * fbm(x * 0.025, y * 0.02, 4, 11.0))
    # 地图外圈的山丘：挡住地形边缘
    r = max(abs(x) / (CORE[0] * 0.5), abs(y) / (CORE[1] * 0.5))
    h += smooth(0.9, 1.45, r) * (7 + 4 * fbm(x * 0.03, y * 0.03, 3, 5.0))
    return h


_CLEAR_H = None


def ground(x, y):
    """地形高度（米）。所有摆放都用这个函数贴地。"""
    global _CLEAR_H
    if _CLEAR_H is None:
        _CLEAR_H = [_base_height(cx, cy) for cx, cy, _ in CLEARINGS]
    h = _base_height(x, y)
    for (cx, cy, r), ch in zip(CLEARINGS, _CLEAR_H):
        d = math.hypot(x - cx, y - cy)
        h = lerp(h, ch, (1 - smooth(r * 0.7, r * 1.3, d)) * 0.9)
    # 道路略微下凹
    pd = path_dist(x, y)
    h -= (1 - smooth(-0.5, 1.0, pd)) * 0.06
    # 湖岸石崖后面的高地
    e = lake_e(x, y)
    a = lake_angle(x, y)
    if in_cliff_arc(a, 0.8):
        k = smooth(0.8, 0.0, max(0.0, max(CLIFF["a0"] - a, a - CLIFF["a1"])))
        h = max(h, lerp(h, LAKE["level"] + CLIFF["height"] + 0.5, k * smooth(1.05, 1.3, e) * (1 - smooth(1.9, 3.4, e))))
    # 湖盆与沙滩
    bed = LAKE["level"] - 0.4 - 1.6 * (1 - min(1.0, e) ** 2)
    shore = lerp(bed, h, smooth(0.92, 1.45, e))
    if e < 1.45:
        h = min(h, shore) if not (in_cliff_arc(a, 0.05) and e > 1.0) else h
    return h


# ------------------------------------------------------------------------------------------------
# 阶段 3：地形


def build_terrain():
    W, H = TERRAIN
    step = 1.0
    nx, ny = int(W / step) + 1, int(H / step) + 1
    verts, cols = [], []
    C = {k: Vector(srgb(v)[:3]) for k, v in dict(
        grass="#5f9f43", grass2="#76b24e", meadow="#86bf57", forest="#4b7a36", needles="#6e5a3b",
        dirt="#a98256", road="#98764f", sand="#d9a14a", wetsand="#9c7a4a", rock="#6e6b68", bed="#5e5440").items()}
    for j in range(ny):
        y = -H / 2 + j * step
        for i in range(nx):
            x = -W / 2 + i * step
            z = ground(x, y)
            verts.append((x, y, z))
            # 颜色
            n1 = fbm(x * 0.07, y * 0.07, 3, 21.0) * 0.5 + 0.5
            c = C["grass"].lerp(C["grass2"], smooth(0.35, 0.7, n1))
            dense = smooth(0.0, 0.35, fbm(x * 0.025 + 40, y * 0.025 - 9, 3))
            c = c.lerp(C["forest"], dense * 0.55)
            c = c.lerp(C["needles"], dense * smooth(0.55, 0.8, n1) * 0.5)
            md = math.hypot(x - MEADOW[0], y - MEADOW[1])
            c = c.lerp(C["meadow"], 1 - smooth(MEADOW[2] * 0.6, MEADOW[2] * 1.2, md))
            e = lake_e(x, y)
            a = lake_angle(x, y)
            if e < 1.5 and not (in_cliff_arc(a, 0.08)):
                sand = 1 - smooth(1.12, 1.42 + 0.1 * max(0.0, -math.sin(a)), e)
                c = c.lerp(C["sand"], sand)
                c = c.lerp(C["wetsand"], 1 - smooth(0.96, 1.04, e))
                c = c.lerp(C["bed"], 1 - smooth(0.6, 0.95, e))
            pd = min(dist_to_polyline(x, y, p["pts"]) - p["w"] * 0.5 for p in PATHS[:-1])
            rd = dist_to_polyline(x, y, PATHS[-1]["pts"]) - PATHS[-1]["w"] * 0.5
            c = c.lerp(C["dirt"], 1 - smooth(-0.2, 0.9, pd))
            c = c.lerp(C["road"], 1 - smooth(-0.2, 0.9, rd))
            yd = math.hypot(x - YARD[0], y - YARD[1])
            c = c.lerp(C["dirt"], (1 - smooth(7, 11, yd)) * 0.6)
            cols.append((c, z))
    # 坡度大的地方显示岩石色
    faces = []
    for j in range(ny - 1):
        for i in range(nx - 1):
            a = j * nx + i
            faces.append((a, a + 1, a + nx + 1, a + nx))
    me = bpy.data.meshes.new("Terrain_Ground")
    me.from_pydata(verts, [], faces)
    me.update()
    flat = []
    for idx, (c, z) in enumerate(cols):
        i, j = idx % nx, idx // nx
        zx = verts[min(idx + 1, len(verts) - 1)][2] - verts[max(idx - 1, 0)][2] if 0 < i < nx - 1 else 0
        zy = verts[min(idx + nx, len(verts) - 1)][2] - verts[max(idx - nx, 0)][2] if 0 < j < ny - 1 else 0
        slope = math.hypot(zx, zy) / (2 * step)
        x, y = verts[idx][0], verts[idx][1]
        plateau = in_cliff_arc(lake_angle(x, y), 0.8) and lake_e(x, y) > 1.12
        if not plateau:
            c = c.lerp(C["rock"], smooth(1.3, 2.2, slope))
        else:
            c = c.lerp(C["forest"], smooth(0.6, 1.6, slope) * 0.6)
        flat.extend((c.x, c.y, c.z, 1.0))
    ca = me.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
    ca.data.foreach_set("color", flat)
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    me.materials.append(mat_vertex_color("Terrain_Ground_VertexColor"))
    ob = bpy.data.objects.new("Terrain_Ground", me)
    COLL["Terrain"].objects.link(ob)
    tag(ob, cn="地形（草地、林地、小路、沙滩、湖底）", status="inferred", note="地形起伏与道路布局为推测布局")

    # 远山（U1、第一季片头：远处蓝色群山）
    bm = bmesh.new()
    rnd = random.Random(7)
    for k in range(18):
        ang = 2 * math.pi * k / 18 + rnd.uniform(-0.1, 0.1)
        R = rnd.uniform(185, 240)
        hgt = rnd.uniform(35, 75) * (1.3 if math.sin(ang) > 0.3 else 0.8)
        cx, cy = math.cos(ang) * R, math.sin(ang) * R
        ret = bmesh.ops.create_cone(bm, cap_ends=False, cap_tris=False, segments=9, radius1=rnd.uniform(55, 85),
                                    radius2=0.0, depth=hgt * 2, matrix=trs((cx, cy, -5), (0, 0, rnd.random())))
        for v in ret["verts"]:
            v.co.z += 6 * noise.noise(v.co * 0.05)
    new_obj("Terrain_Backdrop_Mountains", bm, COLL["Terrain"], [mat("Backdrop_Mountains_Haze", "#7e9fb4", rough=1.0)],
            props=dict(cn="远山背景", status="observed", note="U1、第一季片头可见远处蓝色群山；形状为推测"))
    # 远处地面（防止从高处看到地形外边缘）
    bm = bmesh.new()
    bm_cyl(bm, 330, 330, 0.2, loc=(0, 0, -2.5), seg=48)
    new_obj("Terrain_Distant_Ground", bm, COLL["Terrain"], [mat("Distant_Forest_Floor", "#3f6a35", rough=1.0)],
            props=dict(cn="远处地面", status="inferred"))


# ------------------------------------------------------------------------------------------------
# 阶段 3：湖、沙滩、石崖、瀑布、岩石


def build_lake_and_rocks():
    C = COLL["River_and_Rocks"]
    # 湖面
    bm = bmesh.new()
    seg = 72
    center = bm.verts.new((LAKE["x"], LAKE["y"], LAKE["level"]))
    ring = []
    for k in range(seg):
        a = 2 * math.pi * k / seg
        x, y = lake_point(a, 1.08)
        ring.append(bm.verts.new((x, y, LAKE["level"])))
    for k in range(seg):
        bm.faces.new((center, ring[k], ring[(k + 1) % seg]))
    new_obj("Lake_Water", bm, C, [mat_water("Water_Lake", "#4f8fc0", "#2d6a96")], recalc=False,
            props=dict(cn="林中大湖", status="observed", note="U1：大湖；湖的完整轮廓为推测"))

    # 石崖：成排的深灰色多棱柱状岩体，前面陡直、顶部参差（U1）
    bm = bmesh.new()
    rnd = random.Random(31)
    n = 22
    for i in range(n + 1):
        a = CLIFF["a0"] + (CLIFF["a1"] - CLIFF["a0"]) * i / n
        for layer in range(3):
            if layer < 2 and abs(a - CLIFF["fall"]) < 0.09:
                continue  # 瀑布的缺口
            x, y = lake_point(a + rnd.uniform(-0.015, 0.015), 1.08 + layer * 0.09 + rnd.uniform(-0.02, 0.02))
            k = 0.55 + 0.45 * math.sin((i + 0.5) / (n + 1) * math.pi)
            hgt = CLIFF["height"] * k * (0.85 + 0.25 * layer) * rnd.uniform(0.85, 1.1) + 1.0
            r = rnd.uniform(1.6, 2.6)
            ret = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=rnd.choice((5, 6, 7)),
                                        radius1=r, radius2=r * rnd.uniform(0.7, 0.9), depth=hgt,
                                        matrix=trs((x, y, LAKE["level"] - 1.0 + hgt / 2), (rnd.uniform(-0.04, 0.04), rnd.uniform(-0.04, 0.04), rnd.uniform(0, 6.3))))
            for v in ret["verts"]:
                v.co += Vector((noise.noise(v.co * 0.4) * 0.35, noise.noise(v.co * 0.4 + Vector((5, 1, 2))) * 0.35, 0))
            _mi(_faces(ret), rnd.randrange(2))
            # 顶上的碎石帽
            bm_ico(bm, r * 0.9, loc=(x, y, LAKE["level"] - 1.0 + hgt), scale=(1, 1, 0.45), subdiv=1, rough=0.2, seed=i + layer, mi=rnd.randrange(2))
    ob = new_obj("Lake_Cliff_Rock", bm, C, [mat_noise("Rock_Cliff_Dark", "#3c3b40", "#57565c", scale=1.2, bump=0.5),
                                            mat_noise("Rock_Cliff_Darker", "#2f2e33", "#47464c", scale=1.5, bump=0.5)],
                 props=dict(cn="湖边石崖", status="observed", note="U1：深灰色大石崖；背面与高度为推测"))
    # 瀑布：从崖顶落入湖中（U1）
    bm = bmesh.new()
    tx, ty = lake_point(CLIFF["fall"], 1.2)
    bx, by = lake_point(CLIFF["fall"], 0.99)
    rows = []
    S = 16
    for i in range(S + 1):
        t = i / S
        z = LAKE["level"] + CLIFF["height"] * (1 - t) + 0.2
        out = math.sin(t * math.pi * 0.5) * 0.35 + t * 0.1
        cx, cy = lerp(tx, bx, out), lerp(ty, by, out)
        w = 1.8 + t * 1.2
        dx, dy = -math.sin(CLIFF["fall"]), math.cos(CLIFF["fall"])
        rows.append([bm.verts.new((cx + dx * w * s, cy + dy * w * s, z)) for s in (-1, -0.5, 0, 0.5, 1)])
    for i in range(S):
        for k in range(4):
            bm.faces.new((rows[i][k], rows[i][k + 1], rows[i + 1][k + 1], rows[i + 1][k]))
    new_obj("Lake_Waterfall", bm, C, [mat_waterfall()], recalc=False,
            props=dict(cn="湖边瀑布", status="observed", note="U1：细长瀑布从崖顶直落湖中"))
    # 瀑布脚下的水花
    bm = bmesh.new()
    for k in range(9):
        bm_ico(bm, rnd.uniform(0.5, 1.0), loc=(bx + rnd.uniform(-1.5, 1.5), by + rnd.uniform(-1.2, 1.2), LAKE["level"] + 0.1),
               scale=(1, 1, 0.45), subdiv=1, rough=0.2, seed=k)
    new_obj("Lake_Waterfall_Foam", bm, C, [mat("Water_Foam", "#f2f6fa", rough=0.6)], smooth_shade=True,
            props=dict(cn="瀑布水花", status="inferred"))

    # 岩石原型 + 散布
    protos = []
    for k in range(5):
        bm = bmesh.new()
        bm_ico(bm, 1.0, scale=(1.2, 1.0, 0.7), subdiv=2, rough=0.25, seed=k * 7.3)
        protos.append(new_obj(f"Proto_Rock_{k}", bm, COLL["Prototypes_Hidden"],
                              [mat_noise("Rock_Grey", "#6f6c69", "#8e8a85", scale=2.5, bump=0.35)]))
    placed = 0
    for i in range(700):
        x = rnd.uniform(-110, 110)
        y = rnd.uniform(-90, 90)
        e = lake_e(x, y)
        want = 0.05 + smooth(30, 60, y) * 0.5 + (0.6 if 1.0 < e < 1.25 else 0.0)
        if rnd.random() > want or e < 1.02 or path_dist(x, y) < 1.0 or any(math.hypot(x - cx, y - cy) < r for cx, cy, r in CLEARINGS):
            continue
        s = rnd.uniform(0.25, 1.4) * (1.6 if y > 35 else 1.0)
        linked(rnd.choice(protos), f"Rock_{placed:03d}", C, (x, y, ground(x, y) - s * 0.25), (0, 0, rnd.uniform(0, 6.3)), s,
               props=dict(cn="岩石", status="inferred"))
        placed += 1


# ------------------------------------------------------------------------------------------------
# 阶段 3：森林（树木原型 + 关联复制）


def spruce_proto(name, h, seed):
    """云杉：略弯的红褐色树干、树根、8–12 层下垂的枝层（第一季截图中森林的主体）。"""
    rnd = random.Random(seed)
    bm = bmesh.new()
    pts, rad = [], []
    for i in range(8):
        t = i / 7
        pts.append((math.sin(t * 2.2 + seed) * 0.12 * h / 14, math.cos(t * 1.7) * 0.08 * h / 14 - 0.08, t * h * 0.97))
        rad.append(lerp(0.32, 0.04, t) * h / 14)
    bm_tube(bm, pts, rad, seg=8, mi=0)
    for k in range(5):
        a = 2 * math.pi * k / 5 + rnd.random()
        bm_tube(bm, [(0, 0, 0.5), (math.cos(a) * 0.7, math.sin(a) * 0.7, 0.12), (math.cos(a) * 1.2, math.sin(a) * 1.2, -0.05)],
                [0.16 * h / 14, 0.09, 0.03], seg=6, mi=0)
    tiers = int(h / 1.35)
    for i in range(tiers):
        t = i / max(1, tiers - 1)
        z = lerp(h * 0.16, h * 0.9, t)
        R = lerp(h * 0.24, h * 0.055, t ** 0.9) * rnd.uniform(0.9, 1.08)
        th = lerp(h * 0.17, h * 0.1, t)
        segs = 14
        top = bm.verts.new((pts[0][0] + 0, 0, z + th))
        rim, inner = [], []
        for k in range(segs):
            a = 2 * math.pi * k / segs + i * 0.4
            rr = R * (1.0 if k % 2 == 0 else 0.8) * (1 + 0.12 * noise.noise(Vector((k * 0.7, i, seed))))
            droop = -th * 0.35 * (1.0 if k % 2 == 0 else 0.6)
            rim.append(bm.verts.new((math.cos(a) * rr, math.sin(a) * rr, z + droop)))
            inner.append(bm.verts.new((math.cos(a) * rr * 0.45, math.sin(a) * rr * 0.45, z + th * 0.05)))
        mi = 1 if i % 3 else 2
        for k in range(segs):
            k2 = (k + 1) % segs
            bm.faces.new((top, rim[k], rim[k2])).material_index = mi
            bm.faces.new((rim[k2], rim[k], inner[k], inner[k2])).material_index = mi
    tip = bm.verts.new((0, 0, h * 1.02))
    base = [bm.verts.new((math.cos(a) * 0.35, math.sin(a) * 0.35, h * 0.86)) for a in [2 * math.pi * k / 6 for k in range(6)]]
    for k in range(6):
        bm.faces.new((tip, base[k], base[(k + 1) % 6])).material_index = 2
    return new_obj(name, bm, COLL["Prototypes_Hidden"],
                   [mat_noise("Bark_Spruce", "#5e3524", "#7d4a33", scale=8, bump=0.3),
                    mat_noise("Foliage_Spruce", "#24563a", "#2f6a46", scale=3, bump=0.2),
                    mat_noise("Foliage_Spruce_Light", "#2e6a45", "#3c7d52", scale=3, bump=0.2)], recalc=False)


def broadleaf_proto(name, h, seed, foliage_mat, bark=None, slender=1.0):
    """阔叶树/白桦：弯曲树干、3–4 根主枝、团状树冠。"""
    rnd = random.Random(seed)
    bm = bmesh.new()
    r0 = 0.28 * h / 10 * slender
    pts = [(0, 0, 0), (0.15, 0.05, h * 0.2), (0.05, -0.1, h * 0.4), (0.25, 0.0, h * 0.55)]
    bm_tube(bm, pts, [r0 * 1.25, r0, r0 * 0.85, r0 * 0.6], seg=8, mi=0)
    for k in range(4):
        a = 2 * math.pi * k / 4 + rnd.random()
        bm_tube(bm, [(0, 0, 0.35), (math.cos(a) * 0.6, math.sin(a) * 0.6, 0.08), (math.cos(a) * 1.0, math.sin(a) * 1.0, -0.05)],
                [r0 * 0.7, r0 * 0.35, r0 * 0.12], seg=6, mi=0)
    tips = []
    for k in range(4):
        a = 2 * math.pi * k / 4 + rnd.uniform(-0.3, 0.3)
        sx, sy, sz = 0.2, 0.0, h * 0.5
        ex, ey, ez = math.cos(a) * h * 0.22, math.sin(a) * h * 0.22, h * rnd.uniform(0.68, 0.8)
        bm_tube(bm, [(sx, sy, sz), ((sx + ex) / 2, (sy + ey) / 2, (sz + ez) / 2 - 0.2), (ex, ey, ez)],
                [r0 * 0.5, r0 * 0.32, r0 * 0.12], seg=6, mi=0)
        tips.append((ex, ey, ez))
    tips.append((0.2, 0, h * 0.86))
    for (x, y, z) in tips:
        for j in range(2):
            rr = h * rnd.uniform(0.13, 0.19)
            bm_ico(bm, rr, loc=(x + rnd.uniform(-0.6, 0.6), y + rnd.uniform(-0.6, 0.6), z + rnd.uniform(-0.3, 0.6)),
                   scale=(1, 1, 0.85), subdiv=2, rough=0.22, seed=seed + x + j, mi=1)
    return new_obj(name, bm, COLL["Prototypes_Hidden"],
                   [bark or mat_noise("Bark_Broadleaf", "#5b4030", "#77553d", scale=7, bump=0.3), foliage_mat],
                   smooth_shade=True, recalc=False)


def bush_proto(name, seed, color_mat):
    rnd = random.Random(seed)
    bm = bmesh.new()
    for k in range(rnd.randint(4, 6)):
        r = rnd.uniform(0.35, 0.7)
        bm_ico(bm, r, loc=(rnd.uniform(-0.6, 0.6), rnd.uniform(-0.6, 0.6), r * 0.7), scale=(1, 1, 0.8), subdiv=2,
               rough=0.25, seed=seed + k)
    return new_obj(name, bm, COLL["Prototypes_Hidden"], [color_mat], smooth_shade=True, recalc=False)


def fern_proto(name, seed):
    rnd = random.Random(seed)
    bm = bmesh.new()
    n = 9
    for k in range(n):
        a = 2 * math.pi * k / n + rnd.uniform(-0.2, 0.2)
        L = rnd.uniform(0.6, 0.95)
        dx, dy = math.cos(a), math.sin(a)
        px, py = -dy, dx
        prev = None
        steps = 8
        for s in range(steps + 1):
            t = s / steps
            cx, cy = dx * L * t, dy * L * t
            cz = math.sin(t * math.pi * 0.75) * 0.45 * L
            w = 0.09 * math.sin(t * math.pi) * (1.3 if s % 2 else 0.7)
            row = (bm.verts.new((cx + px * w, cy + py * w, cz)), bm.verts.new((cx - px * w, cy - py * w, cz)))
            if prev:
                bm.faces.new((prev[0], prev[1], row[1], row[0]))
            prev = row
    ob = new_obj(name, bm, COLL["Prototypes_Hidden"], [mat("Plant_Fern", "#4c8a3a", rough=0.7)], smooth_shade=True,
                 recalc=False)
    return ob


def build_forest():
    T = COLL["Forest_Trees"]
    P = COLL["Forest_Plants"]
    foliage_green = mat_noise("Foliage_Broadleaf_Green", "#3f8a35", "#5aa443", scale=2.5, bump=0.25)
    foliage_dark = mat_noise("Foliage_Broadleaf_Dark", "#2f6f2f", "#4a8a3a", scale=2.5, bump=0.25)
    foliage_gold = mat_noise("Foliage_Birch_Golden", "#d9a62c", "#f0c94a", scale=2.5, bump=0.25)
    spruces = [spruce_proto(f"Proto_Spruce_{i}", h, 11 + i * 5) for i, h in enumerate((11, 14, 17, 20))]
    broads = [broadleaf_proto(f"Proto_Broadleaf_{i}", h, 40 + i, m) for i, (h, m) in
              enumerate(((9, foliage_green), (11, foliage_dark), (12, foliage_green)))]
    birch_bark = mat_birch_bark()
    birches = [broadleaf_proto(f"Proto_Birch_{i}", h, 70 + i, m, bark=birch_bark, slender=0.6) for i, (h, m) in
               enumerate(((10, foliage_gold), (12, foliage_gold), (11, foliage_green)))]
    bushes = [bush_proto(f"Proto_Bush_{i}", 90 + i, m) for i, m in
              enumerate((mat_noise("Plant_Bush", "#3d7a32", "#559a40", scale=3), foliage_dark, foliage_green))]
    ferns = [fern_proto(f"Proto_Fern_{i}", 120 + i) for i in range(2)]

    rnd = random.Random(5)
    W, H = TERRAIN
    step = 4.6
    n_trees = 0
    y = -H / 2 + 4
    while y < H / 2 - 4:
        x = -W / 2 + 4
        while x < W / 2 - 4:
            px, py = x + rnd.uniform(-1.8, 1.8), y + rnd.uniform(-1.8, 1.8)
            x += step
            dens = 0.55 + 0.45 * fbm(px * 0.025 + 40, py * 0.025 - 9, 3) * 2
            if rnd.random() > dens:
                continue
            e = lake_e(px, py)
            a = lake_angle(px, py)
            if e < 1.5 or (in_cliff_arc(a, 0.12) and e < 1.42):
                continue
            if path_dist(px, py) < 2.2:
                continue
            if any(math.hypot(px - cx, py - cy) < r * 1.05 for cx, cy, r in CLEARINGS):
                continue
            if math.hypot(px - HOUSE["x"], py - HOUSE["y"]) < 12:
                continue
            gz = ground(px, py)
            near_lake = smooth(2.6, 1.6, e)
            r = rnd.random()
            if r < near_lake * 0.75:
                proto = birches[0 if rnd.random() < 0.45 else 1] if rnd.random() < 0.8 else birches[2]
                kind = "Birch"
            elif r < 0.68 + smooth(25, 55, py) * 0.3:
                proto = rnd.choice(spruces)
                kind = "Spruce"
            else:
                proto = rnd.choice(broads)
                kind = "Broadleaf"
            s = rnd.uniform(0.8, 1.2)
            linked(proto, f"Tree_{kind}_{n_trees:04d}", T, (px, py, gz - 0.15), (0, 0, rnd.uniform(0, 6.28)), s,
                   props=dict(cn={"Spruce": "云杉", "Birch": "白桦", "Broadleaf": "阔叶树"}[kind], status="observed",
                              note="第一季截图：云杉为主，夹杂圆冠阔叶树；U1：湖边金黄色白桦"))
            n_trees += 1
        y += step
    # 灌木、蕨类：沿路边、空地边缘、林下
    n_b = 0
    for i in range(1800):
        x, y = rnd.uniform(-100, 100), rnd.uniform(-80, 80)
        if lake_e(x, y) < 1.4 or math.hypot(x - HOUSE["x"], y - HOUSE["y"]) < 8:
            continue
        pd = path_dist(x, y)
        edge = any(abs(math.hypot(x - cx, y - cy) - r) < 2.0 for cx, cy, r in CLEARINGS)
        if not ((1.3 < pd < 4.5) or edge or rnd.random() < 0.18):
            continue
        if pd < 1.3 or any(math.hypot(x - cx, y - cy) < r * 0.9 for cx, cy, r in CLEARINGS):
            continue
        if rnd.random() < 0.55:
            linked(rnd.choice(bushes), f"Bush_{n_b:04d}", P, (x, y, ground(x, y) - 0.1), (0, 0, rnd.uniform(0, 6.3)),
                   rnd.uniform(0.6, 1.3), props=dict(cn="灌木", status="inferred"))
        else:
            linked(rnd.choice(ferns), f"Fern_{n_b:04d}", P, (x, y, ground(x, y) - 0.03), (0, 0, rnd.uniform(0, 6.3)),
                   rnd.uniform(0.7, 1.3), props=dict(cn="蕨类", status="inferred"))
        n_b += 1
    # 草丛和野花：按 40 m 分块合并成网格（减少物体数量）
    grass_m = mat("Plant_Grass", "#5f9f3f", rough=0.8)
    flower_ms = [mat("Plant_Flower_Yellow", "#f2cf3a"), mat("Plant_Flower_White", "#f4f2ea"), mat("Plant_Flower_Pink", "#ef9ab8")]
    tiles = {}
    for i in range(9000):
        x, y = rnd.uniform(-100, 100), rnd.uniform(-80, 80)
        if lake_e(x, y) < 1.3 or path_dist(x, y) < 0.6 or math.hypot(x - HOUSE["x"], y - HOUSE["y"]) < 6.5:
            continue
        md = math.hypot(x - MEADOW[0], y - MEADOW[1])
        if md > MEADOW[2] * 1.3 and rnd.random() < 0.6:
            continue
        key = (int((x + 120) // 40), int((y + 100) // 40))
        bm = tiles.setdefault(key, bmesh.new())
        z = ground(x, y)
        if md < MEADOW[2] * 1.1 and rnd.random() < 0.35:
            # 野花
            fm = rnd.randrange(3) + 1
            bm_cyl(bm, 0.012, 0.012, 0.35, loc=(x, y, z + 0.17), seg=4, mi=0)
            bm_cyl(bm, 0.07, 0.0, 0.05, loc=(x, y, z + 0.37), seg=6, mi=fm)
        else:
            for b in range(7):
                a = rnd.uniform(0, 6.28)
                hgt = rnd.uniform(0.2, 0.45)
                bx, by = x + math.cos(a) * 0.08, y + math.sin(a) * 0.08
                lean = rnd.uniform(0.05, 0.15)
                v1 = bm.verts.new((bx - 0.025, by, z))
                v2 = bm.verts.new((bx + 0.025, by, z))
                v3 = bm.verts.new((bx + math.cos(a) * lean, by + math.sin(a) * lean, z + hgt))
                bm.faces.new((v1, v2, v3))
    for (i, j), bm in tiles.items():
        new_obj(f"GrassAndFlowers_Patch_{i}_{j}", bm, P, [grass_m] + flower_ms, recalc=False,
                props=dict(cn="草丛与野花", status="inferred"))
    # 倒木、树桩
    log_bark = mat_noise("Bark_Log", "#5d3f2a", "#7b573c", scale=6, bump=0.3)
    cut = mat_noise("Wood_Cut_End", "#d7b07a", "#e6c696", scale=12, bump=0.1)
    for k in range(14):
        x, y = rnd.uniform(-90, 90), rnd.uniform(-70, 70)
        if lake_e(x, y) < 1.5 or path_dist(x, y) < 2.5 or any(math.hypot(x - cx, y - cy) < r for cx, cy, r in CLEARINGS):
            continue
        bm = bmesh.new()
        L = rnd.uniform(3, 6)
        r = rnd.uniform(0.22, 0.4)
        bm_cyl(bm, r, r * 0.9, L, rot=(0, math.pi / 2, 0), seg=10, mi=0, caps=False)
        bm_cyl(bm, r * 0.98, r * 0.98, 0.02, loc=(L / 2, 0, 0), rot=(0, math.pi / 2, 0), seg=10, mi=1)
        bm_cyl(bm, r * 0.88, r * 0.88, 0.02, loc=(-L / 2, 0, 0), rot=(0, math.pi / 2, 0), seg=10, mi=1)
        ob = new_obj(f"Fallen_Log_{k:02d}", bm, P, [log_bark, cut], smooth_shade=True,
                     props=dict(cn="倒木", status="inferred"))
        ob.location = (x, y, ground(x, y) + r * 0.6)
        ob.rotation_euler = (0, 0, rnd.uniform(0, 6.3))
    return n_trees


# ------------------------------------------------------------------------------------------------
# 阶段 4：光头强的小木屋（外观、室内、可拆屋顶）

W_HOUSE, D_HOUSE, H_WALL, FOUND = 9.0, 6.0, 3.0, 0.35


def board_wall(bm, L, H, holes, n_shades, rnd, board=0.3, depth=0.1, z0=0.0, mi_base=0):
    """横木板墙：逐条木板生成，跳过门窗洞，木板随机分到 n_shades 种木色。"""
    y = 0.0
    while y < H - 1e-3:
        bh = min(board, H - y) - 0.02
        yc = y + bh / 2
        segs = [(-L / 2, L / 2)]
        for (x0, x1, y0, y1) in holes:
            if yc < y0 or yc > y1:
                continue
            nxt = []
            for s0, s1 in segs:
                if x1 <= s0 or x0 >= s1:
                    nxt.append((s0, s1))
                    continue
                if x0 > s0:
                    nxt.append((s0, x0))
                if x1 < s1:
                    nxt.append((x1, s1))
            segs = nxt
        for s0, s1 in segs:
            if s1 - s0 > 0.03:
                bm_cube(bm, (s1 - s0, depth, bh), loc=((s0 + s1) / 2, rnd.uniform(-0.01, 0.01), z0 + yc),
                        mi=mi_base + rnd.randrange(n_shades))
        y += board


def build_house():
    EXT = COLL["GuangtouQiang_House_Exterior"]
    ROOF = COLL["GQ_House_Roof_Removable"]
    INT = COLL["GuangtouQiang_House_Interior"]
    hx, hy = HOUSE["x"], HOUSE["y"]
    gz = max(ground(hx + sx * W_HOUSE / 2, hy + sy * D_HOUSE / 2) for sx in (-1, 1) for sy in (-1, 1))
    root = empty("GQ_House_Root", EXT, (hx, hy, gz), (0, 0, HOUSE["rot"]), size=1.5,
                 props=dict(cn="光头强的小木屋（根）", note="子物体都挂在这里，移动它即可整体移动木屋"))
    rnd = random.Random(12)
    W, D, H, B = W_HOUSE, D_HOUSE, H_WALL, FOUND
    wood = [mat_noise(f"Wood_Plank_Exterior_{i}", c1, c2, scale=9, bump=0.15) for i, (c1, c2) in enumerate(
        (("#c4853f", "#d39a55"), ("#b0703a", "#c4874a"), ("#d8a05c", "#e3b06e"), ("#a3653a", "#b97b47")))]
    inner = [mat_noise(f"Wood_Plank_Interior_BlueGrey_{i}", c1, c2, scale=9, bump=0.1) for i, (c1, c2) in enumerate(
        (("#5c7486", "#68808f"), ("#4f6676", "#5d7484"), ("#667d8b", "#71889a")))]
    yellow = mat("Paint_Yellow_Trim", "#e2c048", rough=0.6)
    lattice_m = mat("Wood_Lattice_Dark", "#4a3424", rough=0.7)
    glass = mat("Glass_Window_Warm", "#ffe2a0", rough=0.3, emit="#ffc46a", emit_strength=0.6)
    stone = mat_noise("Stone_Foundation", "#7c7872", "#9a958d", scale=4, bump=0.4)

    # 地基
    bm = bmesh.new()
    bm_cube(bm, (W + 0.3, D + 0.3, B + 0.6), loc=(0, 0, B / 2 - 0.3))
    new_obj("GQ_House_Foundation", bm, EXT, [stone], parent=root,
            props=dict(cn="石头地基", status="inferred"))

    # 门窗洞（墙体局部坐标：x 沿墙长，z 自地基顶起）
    door = (-0.85, 0.85, 0.0, 2.1)
    win_l, win_r = (-3.4, -2.7, 1.9, 2.6), (2.7, 3.4, 1.9, 2.6)
    win_back = (1.6, 2.6, 1.4, 2.4)  # 圆窗外框所在洞
    win_side = (-0.4, 0.4, 1.9, 2.6)
    walls = [
        ("Front", W, [door, win_l, win_r], Matrix.Translation((0, D / 2 - 0.05, B))),
        ("Back", W, [(-win_back[1], -win_back[0], win_back[2], win_back[3])], Matrix.Translation((0, -D / 2 + 0.05, B)) @ Matrix.Rotation(math.pi, 4, "Z")),
        ("Right", D, [win_side], Matrix.Translation((W / 2 - 0.05, 0, B)) @ Matrix.Rotation(-math.pi / 2, 4, "Z")),
        ("Left", D, [], Matrix.Translation((-W / 2 + 0.05, 0, B)) @ Matrix.Rotation(math.pi / 2, 4, "Z")),
    ]
    for wname, L, holes, M in walls:
        bm = bmesh.new()
        board_wall(bm, L, H, holes, 4, rnd, depth=0.1)
        bmesh.ops.transform(bm, matrix=M, verts=bm.verts[:])
        new_obj(f"GQ_Wall_{wname}_Exterior_Boards", bm, EXT, wood, parent=root,
                props=dict(cn=f"外墙木板（{wname}）", status="observed" if wname == "Front" else "inferred",
                           note="U3：橙黄深浅不一的横木板" if wname == "Front" else "侧面和背面不可见，按正面推测"))
        bm = bmesh.new()
        board_wall(bm, L - 0.3, H, holes, 3, rnd, board=0.26, depth=0.05)
        bmesh.ops.transform(bm, matrix=M @ Matrix.Translation((0, -0.11, 0)) if wname != "Front" else M @ Matrix.Translation((0, -0.11, 0)), verts=bm.verts[:])
        new_obj(f"GQ_Wall_{wname}_Interior_Boards", bm, INT, inner, parent=root,
                props=dict(cn=f"室内墙板（{wname}，蓝灰色）", status="observed", note="U5–U7：蓝灰色木板内墙"))

    # 黄色包角、门框、窗框（U3）
    bm = bmesh.new()
    for sx in (-1, 1):
        for sy in (-1, 1):
            bm_cube(bm, (0.26, 0.26, H), loc=(sx * W / 2, sy * D / 2, B + H / 2))
    bm_cube(bm, (W + 0.3, 0.2, 0.18), loc=(0, D / 2 + 0.02, B + H - 0.05))

    def frame(o, M):
        x0, x1, y0, y1 = o
        w, h = x1 - x0, y1 - y0
        cx, cz = (x0 + x1) / 2, (y0 + y1) / 2
        for (sx, sz, px, pz) in ((w + 0.24, 0.12, cx, y1 + 0.06), (w + 0.24, 0.12, cx, y0 - 0.06),
                                 (0.12, h, x0 - 0.06, cz), (0.12, h, x1 + 0.06, cz)):
            fs = bm_cube(bm, (sx, 0.18, sz), loc=(px, 0.02, B + pz))
            bmesh.ops.transform(bm, matrix=M, verts=list({v for f in fs for v in f.verts}))

    front_M = Matrix.Translation((0, D / 2 - 0.02, 0))
    for o in (door, win_l, win_r):
        frame(o, front_M)
    frame(win_side, Matrix.Translation((W / 2 - 0.02, 0, 0)) @ Matrix.Rotation(-math.pi / 2, 4, "Z"))
    new_obj("GQ_Yellow_Trim_and_Frames", bm, EXT, [yellow], parent=root,
            props=dict(cn="黄色包角板和门窗框", status="observed", note="U3"))

    # 小方窗：玻璃 + 深色格子（U3）
    for wn, o, M in (("Front_Left", win_l, front_M), ("Front_Right", win_r, front_M),
                     ("Right_Side", win_side, Matrix.Translation((W / 2 - 0.02, 0, 0)) @ Matrix.Rotation(-math.pi / 2, 4, "Z"))):
        x0, x1, y0, y1 = o
        w, h = x1 - x0, y1 - y0
        cx, cz = (x0 + x1) / 2, B + (y0 + y1) / 2
        bm = bmesh.new()
        bm_cube(bm, (w, 0.02, h), loc=(cx, 0, cz), mi=0)
        for t in (-0.25, 0.25):
            bm_cube(bm, (w, 0.04, 0.035), loc=(cx, 0.03, cz + t * h), mi=1)
            bm_cube(bm, (0.035, 0.04, h), loc=(cx + t * w, 0.03, cz), mi=1)
        bm_cube(bm, (w * 0.5, 0.04, 0.035), loc=(cx, 0.035, cz), mi=1)
        bm_cube(bm, (0.035, 0.04, h * 0.5), loc=(cx, 0.035, cz), mi=1)
        bmesh.ops.transform(bm, matrix=M, verts=bm.verts[:])
        new_obj(f"GQ_Window_{wn}", bm, EXT, [glass, lattice_m], parent=root,
                props=dict(cn="小方格窗", status="observed" if wn != "Right_Side" else "inferred", note="U3：黄框、深色格子"))

    # 黄色对开门，向外打开（U3）
    for side in (-1, 1):
        bm = bmesh.new()
        dw = 0.85
        bm_cube(bm, (dw, 0.06, 2.08), loc=(side * dw / 2, 0, 1.04), mi=0)
        for i in (1, 2):
            bm_cube(bm, (0.04, 0.03, 0.9), loc=(side * dw * i / 3, 0.04, 1.5), mi=1)
        bm_cube(bm, (dw * 0.9, 0.03, 0.04), loc=(side * dw / 2, 0.04, 1.05), mi=1)
        ob = new_obj(f"GQ_Door_Leaf_{'Left' if side < 0 else 'Right'}", bm, EXT, [yellow, lattice_m], parent=root,
                     props=dict(cn="黄色木门（可旋转开合）", status="observed", note="U3：对开黄门，向外开"))
        # 铰链在门洞两侧：左扇铰链在左、右扇铰链在右，都向屋外（+Y）打开 75°
        ob.location = ((door[0] if side < 0 else door[1]), D / 2 + 0.06, B)
        ob.data.transform(Matrix.Translation((dw if side < 0 else -dw, 0, 0)))
        ob.rotation_euler = (0, 0, math.radians(75) * -side)
    # 门前台阶
    bm = bmesh.new()
    bm_cube(bm, (2.2, 0.8, 0.22), loc=(0, D / 2 + 0.5, B - 0.11))
    new_obj("GQ_Door_Step", bm, EXT, [mat_noise("Wood_Step", "#a3784a", "#b8895a", scale=8)], parent=root,
            props=dict(cn="门前台阶", status="inferred"))

    # 屋顶（可隐藏）：山墙、石板瓦、屋脊、烟囱、室内顶板
    top = B + H
    rise = 1.8
    bm = bmesh.new()
    for sx in (-1, 1):
        v = [bm.verts.new((sx * (W / 2 - 0.02), -D / 2, top)), bm.verts.new((sx * (W / 2 - 0.02), D / 2, top)),
             bm.verts.new((sx * (W / 2 - 0.02), 0, top + rise))]
        bm.faces.new(v)
    new_obj("GQ_Roof_Gables", bm, ROOF, [wood[1]], parent=root, recalc=False,
            props=dict(cn="山墙", status="inferred", note="U3 中屋顶被积雪遮住，屋顶形状为推测"))
    slope = math.atan2(rise, D / 2)
    L = math.hypot(rise, D / 2) + 0.7
    bm = bmesh.new()
    for side in (-1, 1):
        rows, cols = 6, 10
        for r in range(rows):
            u = (r + 0.5) / rows
            for c in range(cols):
                x = -W / 2 - 0.5 + (c + 0.5 + (r % 2) * 0.5) / cols * (W + 1.0)
                fs = bm_cube(bm, ((W + 1.0) / cols + 0.1, L / rows + 0.22, 0.08),
                             loc=(0, 0, 0), mi=rnd.randrange(3))
                M = (Matrix.Translation((x, side * u * L * math.cos(slope), top + rise + 0.12 - u * L * math.sin(slope)))
                     @ Matrix.Rotation(side * -slope + rnd.uniform(-0.04, 0.04), 4, "X"))
                bmesh.ops.transform(bm, matrix=M, verts=list({v for f in fs for v in f.verts}))
    bm_cube(bm, (W + 1.2, 0.35, 0.22), loc=(0, 0, top + rise + 0.12), mi=2)
    new_obj("GQ_Roof_Slabs", bm, ROOF, [mat_noise("Roof_Slab_BlueGrey_A", "#5d7089", "#6c8098", scale=5),
                                        mat_noise("Roof_Slab_BlueGrey_B", "#4f6178", "#5f7189", scale=5),
                                        mat_noise("Roof_Slab_BlueGrey_C", "#6b7f96", "#7a8ea4", scale=5)], parent=root,
            props=dict(cn="灰蓝色石板瓦屋顶（可隐藏）", status="inferred",
                       note="屋顶材料没有清楚的剧照；参照另一张合影里的灰蓝色石板瓦"))
    bm = bmesh.new()
    bm_cube(bm, (0.8, 0.8, 2.6), loc=(2.8, -1.2, top + 1.5))
    bm_cube(bm, (0.95, 0.95, 0.15), loc=(2.8, -1.2, top + 2.85))
    new_obj("GQ_Chimney", bm, ROOF, [stone], parent=root, props=dict(cn="烟囱", status="inferred"))
    bm = bmesh.new()
    for side in (-1, 1):
        for k in range(12):
            x = -W / 2 + 0.3 + k * (W - 0.6) / 11
            fs = bm_cube(bm, (0.12, D / 2 / math.cos(slope) + 0.1, 0.14), loc=(0, 0, 0))
            M = Matrix.Translation((x, side * D / 4, top + rise / 2 - 0.12)) @ Matrix.Rotation(side * -slope, 4, "X")
            bmesh.ops.transform(bm, matrix=M, verts=list({v for f in fs for v in f.verts}))
    new_obj("GQ_Roof_Rafters_Interior", bm, ROOF, [mat_noise("Wood_Rafter", "#6e5440", "#85674d", scale=8)], parent=root,
            props=dict(cn="室内椽子", status="observed", note="U7：室内可见斜屋顶木板"))

    build_house_interior(root, INT, inner, B)
    build_yard(root)
    return root


def build_house_interior(root, INT, inner, B):
    W, D = W_HOUSE, D_HOUSE

    def obj(name, cn, mats, build, loc=(0, 0, 0), rot=(0, 0, 0), status="observed", note=None, smooth_shade=False):
        bm = bmesh.new()
        build(bm)
        ob = new_obj(name, bm, INT, mats, smooth_shade=smooth_shade, parent=root,
                     props=dict(cn=cn, status=status, note=note))
        ob.location = (loc[0], loc[1], B + loc[2])
        ob.rotation_euler = rot
        return ob

    # 地面：灰色不规则石板（U4）
    obj("GQ_Int_Floor_StoneTiles", "石板地面", [mat_stone_floor()],
        lambda bm: bm_plane(bm, W - 0.3, D - 0.3, loc=(0, 0, 0.01), sub=4), note="U4")
    # 土炕（U6）：木框、竹席、蓝底白花被子、红棕枕头；炕边红拖鞋
    kx, ky = -2.95, -1.95

    def kang(bm):
        bm_cube(bm, (2.8, 1.9, 0.62), loc=(0, 0, 0.31), mi=0)
        bm_cube(bm, (2.9, 0.1, 0.12), loc=(0, 0.98, 0.62), mi=1)
        bm_cube(bm, (0.1, 1.95, 0.12), loc=(1.42, 0, 0.62), mi=1)
    obj("GQ_Int_Kang_Base", "土炕", [mat_noise("Kang_Brick_Plaster", "#8c6a52", "#9b7a60", scale=4),
                                    mat_noise("Wood_Kang_Edge", "#6b4a34", "#7d5940", scale=8)], kang, loc=(kx, ky, 0),
        note="U6：木框土炕；尺寸为估算")
    obj("GQ_Int_Kang_BambooMat", "竹席（绿边）", [mat_stripes("Bamboo_Mat", "#c7b36a", "#a8934e", scale=60, axis="X"),
                                              mat("Bamboo_Mat_Green_Edge", "#4f8a3a")],
        lambda bm: (bm_plane(bm, 2.7, 1.8, loc=(0, 0, 0), mi=0), bm_cube(bm, (2.75, 0.1, 0.01), loc=(0, 0.88, 0.003), mi=1),
                    bm_cube(bm, (2.75, 0.1, 0.01), loc=(0, -0.88, 0.003), mi=1)), loc=(kx, ky, 0.63), note="U6")

    def quilt(bm):
        ret = bmesh.ops.create_grid(bm, x_segments=14, y_segments=12, size=1.0)
        for v in ret["verts"]:
            x, y = v.co.x * 0.85, v.co.y * 0.9
            edge = min(1.0, (1 - abs(v.co.x)) * 6, (1 - abs(v.co.y)) * 6)
            v.co = Vector((x, y, 0.06 + 0.22 * edge + 0.05 * math.sin(x * 6) * math.cos(y * 5)))
        bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=0.03)
    obj("GQ_Int_Kang_Quilt", "蓝底白花打补丁的被子", [mat_quilt()], quilt, loc=(kx - 0.35, ky + 0.05, 0.63),
        smooth_shade=True, note="U6：蓝底白花，带蓝色、紫色补丁")
    obj("GQ_Int_Kang_Pillow", "红棕色枕头", [mat("Fabric_Pillow_Red", "#8e2f2a", rough=0.85)],
        lambda bm: bm_cube(bm, (0.32, 0.65, 0.18), loc=(0, 0, 0.09)), loc=(kx + 0.95, ky + 0.05, 0.63), note="U6")
    obj("GQ_Int_Slippers_Red", "红拖鞋", [mat("Rubber_Slipper_Red", "#c4322b", rough=0.6)],
        lambda bm: (bm_cube(bm, (0.11, 0.27, 0.04), loc=(-0.08, 0, 0.02)), bm_cube(bm, (0.11, 0.27, 0.04), loc=(0.1, 0.03, 0.02))),
        loc=(kx + 0.6, ky + 1.25, 0), note="U6")

    # 绿冰箱（U5）：圆角、上门冷冻室、白把手、门上两张纸条；地上易拉罐、陶罐
    fx, fy = -1.05, -2.55

    def fridge(bm):
        ret = bmesh.ops.create_cube(bm, size=1.0)
        for v in ret["verts"]:
            v.co = Vector((v.co.x * 0.7, v.co.y * 0.62, v.co.z * 1.7 + 0.85))
        bmesh.ops.bevel(bm, geom=[e for e in bm.edges], offset=0.09, segments=4, affect="EDGES")
        bm_cube(bm, (0.69, 0.02, 0.012), loc=(0, 0.315, 1.18), mi=1)
        bm_cube(bm, (0.035, 0.05, 0.28), loc=(0.27, 0.34, 1.42), mi=2)
        bm_cube(bm, (0.035, 0.05, 0.36), loc=(0.27, 0.34, 0.8), mi=2)
        bm_cube(bm, (0.12, 0.005, 0.15), loc=(-0.08, 0.316, 0.95), rot=(0, 0.3, 0), mi=3)
        bm_cube(bm, (0.13, 0.005, 0.13), loc=(0.1, 0.316, 0.7), rot=(0, -0.2, 0), mi=3)
    obj("GQ_Int_Fridge_Green", "绿色冰箱", [mat("Paint_Fridge_Mint", "#7fb5a5", rough=0.45), mat("Fridge_Seam", "#5d8f80"),
                                         mat("Plastic_Handle_White", "#f0efe8", rough=0.4), mat("Paper_Note", "#ece6d2")],
        fridge, loc=(fx, fy, 0), smooth_shade=True, note="U5；尺寸为估算")

    def cans(bm):
        rnd = random.Random(4)
        for i in range(7):
            lay = i in (2, 5)
            bm_cyl(bm, 0.035, 0.035, 0.12, loc=(rnd.uniform(-0.25, 0.25), rnd.uniform(-0.15, 0.15), 0.035 if lay else 0.06),
                   rot=((math.pi / 2, 0, rnd.uniform(0, 3)) if lay else (0, 0, 0)), seg=10, mi=i % 2)
    obj("GQ_Int_Cans_On_Floor", "地上的易拉罐", [mat("Can_Red", "#c8302a", rough=0.35, metal=0.4), mat("Can_Silver", "#c9cdd2", rough=0.3, metal=0.8)],
        cans, loc=(fx + 0.15, fy + 0.65, 0), note="U5、U7")
    obj("GQ_Int_Clay_Jar", "陶罐（酸菜缸）", [mat_noise("Clay_Jar", "#5e4a3a", "#6f594a", scale=5)],
        lambda bm: bm_sphere(bm, (0.25, 0.25, 0.3), loc=(0, 0, 0.3), seg=16, rings=10), loc=(fx - 0.6, fy + 0.1, 0),
        smooth_shade=True, note="U5：冰箱旁的陶罐")

    # 青绿色灶台（U7）：橱柜、灶面、炒锅、汤锅、灰色水盆、柜里的小木桶
    cx, cy = 2.25, -2.6

    def kitchen(bm):
        bm_cube(bm, (3.6, 0.62, 0.82), loc=(0, 0, 0.41), mi=0)
        bm_cube(bm, (3.7, 0.7, 0.07), loc=(0, 0, 0.85), mi=1)
        for x in (-1.2, -0.4, 0.4):
            bm_cube(bm, (0.72, 0.02, 0.6), loc=(x, 0.32, 0.4), mi=1)
        bm_cube(bm, (0.72, 0.02, 0.6), loc=(1.25, 0.32, 0.4), mi=4)  # 开口
    obj("GQ_Int_Kitchen_Counter_Teal", "青绿色灶台橱柜", [mat("Paint_Kitchen_Teal", "#4e9c93", rough=0.55),
                                                     mat("Paint_Kitchen_Teal_Dark", "#3f857d", rough=0.55),
                                                     mat("Steel_Pot", "#8f969c", metal=0.7, rough=0.35),
                                                     mat("Iron_Wok", "#26272a", metal=0.5, rough=0.45),
                                                     mat("Shadow_Opening", "#1c1c1c", rough=1.0)],
        kitchen, loc=(cx, cy, 0), note="U7")
    obj("GQ_Int_Wok", "黑色炒锅", [MATS["Iron_Wok"]],
        lambda bm: (bm_sphere(bm, (0.36, 0.36, 0.16), loc=(0, 0, 0.16), seg=20, rings=8,
                              deform=lambda co: Vector((co.x, co.y, min(co.z, 0.0)))),
                    bm_cyl(bm, 0.025, 0.025, 0.3, loc=(0.48, 0, 0.18), rot=(0, math.pi / 2, 0), seg=6)),
        loc=(cx + 0.55, cy, 0.89), smooth_shade=True, note="U7")
    obj("GQ_Int_Pot", "汤锅", [MATS["Steel_Pot"]], lambda bm: bm_cyl(bm, 0.2, 0.18, 0.26, loc=(0, 0, 0.13), seg=16),
        loc=(cx - 0.3, cy, 0.89), smooth_shade=True, note="U7")
    obj("GQ_Int_Water_Basin", "灰色水盆", [MATS["Steel_Pot"]],
        lambda bm: bm_cyl(bm, 0.36, 0.3, 0.28, loc=(0, 0, 0.14), seg=18), loc=(cx - 1.3, cy, 0.89), smooth_shade=True,
        note="U7：冰箱旁的灰色水盆")
    obj("GQ_Int_Small_Barrel", "橱柜里的小木桶", [mat_noise("Wood_Barrel", "#8a5a33", "#a06b3f", scale=10)],
        lambda bm: bm_sphere(bm, (0.2, 0.2, 0.26), loc=(0, 0, 0.26), seg=14, rings=8,
                             deform=lambda co: Vector((co.x, co.y, clamp(co.z, -0.8, 0.8)))),
        loc=(cx + 1.25, cy + 0.42, 0.0), smooth_shade=True, note="U7：橱柜开口处的小木桶")
    # 圆形格子窗（U7）：后墙灶台上方
    bm = bmesh.new()
    bm_cyl(bm, 0.5, 0.5, 0.02, rot=(math.pi / 2, 0, 0), seg=24, mi=0)
    bm_torus(bm, 0.55, 0.07, rot=(math.pi / 2, 0, 0), seg=28, rseg=6, mi=1)
    for t in (-0.25, 0, 0.25):
        bm_cube(bm, (0.035, 0.04, 1.0 * math.sqrt(max(0.0, 1 - (t / 0.5) ** 2))), loc=(t, 0.02, 0), mi=1)
        bm_cube(bm, (1.0 * math.sqrt(max(0.0, 1 - (t / 0.5) ** 2)), 0.04, 0.035), loc=(0, 0.02, t), mi=1)
    ob = new_obj("GQ_Int_Round_Lattice_Window", bm, INT, [mat("Glass_Sky", "#bfe3f7", rough=0.2, emit="#cfe9ff", emit_strength=0.8),
                                                            mat_noise("Wood_Window_Frame_Orange", "#a5622f", "#b9733a", scale=10)],
                 parent=root, props=dict(cn="圆形格子窗", status="observed", note="U7"))
    ob.location = (2.1, -D / 2 + 0.06, B + 1.9)
    # 挂着的辣椒串和玉米（U7、U4）
    obj("GQ_Int_Chili_String", "红辣椒串", [mat("Chili_Red", "#c8241c", rough=0.45)],
        lambda bm: [bm_cyl(bm, 0.045, 0.0, 0.18, loc=(math.sin(i * 1.7) * 0.05, 0, -i * 0.11), rot=(math.pi, 0, 0), seg=6)
                    for i in range(12)], loc=(1.2, -D / 2 + 0.25, 2.85), note="U7")

    def corn(bm):
        for i in range(7):
            a = (i - 3) * 0.12
            bm_sphere(bm, (0.06, 0.06, 0.2), loc=(math.sin(a) * 0.3, 0, -0.25 - abs(i - 3) * 0.03), rot=(0, a, 0), seg=10, rings=8)
    obj("GQ_Int_Corn_Bunch", "挂着的玉米", [mat("Corn_Yellow", "#f0c943", rough=0.6)], corn,
        loc=(3.15, -D / 2 + 0.25, 2.9), smooth_shade=True, note="U7、U4")
    # 墙上碗架（U7）和储物木架、碗柜（U4，浅木色）
    shelf_m = mat_noise("Wood_Shelf_Light", "#c19a6b", "#d2ac7d", scale=8)

    def wall_shelf(bm):
        for z in (0.0, 0.45):
            bm_cube(bm, (1.2, 0.28, 0.04), loc=(0, 0, z), mi=0)
        for i in range(4):
            bm_sphere(bm, (0.1, 0.1, 0.06), loc=(-0.4 + i * 0.26, 0, 0.08), seg=10, rings=6, mi=1,
                      deform=lambda co: Vector((co.x, co.y, max(co.z, -0.2))))
        bm_cyl(bm, 0.07, 0.09, 0.22, loc=(0.3, 0, 0.56), seg=10, mi=2)
    obj("GQ_Int_Wall_Shelf_Bowls", "墙上碗架", [shelf_m, mat("Ceramic_Bowl", "#f2efe6", rough=0.3), mat("Ceramic_Jar_Blue", "#7d98a6")],
        wall_shelf, loc=(W / 2 - 0.3, -1.4, 1.6), rot=(0, 0, math.pi / 2), note="U7")

    def storage_shelf(bm):
        for z in (0.0, 0.6, 1.2, 1.8):
            bm_cube(bm, (1.4, 0.4, 0.04), loc=(0, 0, z + 0.3), mi=0)
        for x in (-0.68, 0.68):
            bm_cube(bm, (0.05, 0.4, 2.1), loc=(x, 0, 1.05), mi=0)
        for i in range(6):
            bm_cube(bm, (0.08, 0.25, 0.3), loc=(-0.5 + i * 0.1, 0, 1.07), mi=1 + i % 3)
        bm_cyl(bm, 0.11, 0.13, 0.3, loc=(0.4, 0, 0.47), seg=12, mi=4)
        bm_cyl(bm, 0.09, 0.09, 0.2, loc=(0.3, 0, 1.67), seg=12, mi=4)
    obj("GQ_Int_Storage_Shelf", "储物木架（书和罐子）", [shelf_m, mat("Book_Red", "#8a3a2a"), mat("Book_Blue", "#3b5a7a"),
                                                       mat("Book_Tan", "#c9b07a"), mat("Jar_Grey_Green", "#8aa3a0")],
        storage_shelf, loc=(-W / 2 + 0.35, 1.2, 0), rot=(0, 0, -math.pi / 2), status="observed",
        note="U4：储物架；它在屋里的位置为推测")

    def cupboard(bm):
        bm_cube(bm, (1.1, 0.55, 1.7), loc=(0, 0, 0.85), mi=0)
        for x in (-0.27, 0.27):
            bm_cube(bm, (0.5, 0.03, 1.1), loc=(x, 0.29, 1.0), mi=1)
            bm_cube(bm, (0.04, 0.04, 0.12), loc=(x * 0.2, 0.32, 1.0), mi=1)
    obj("GQ_Int_Cupboard", "碗柜", [mat_noise("Wood_Cupboard", "#c9a77a", "#d6b88c", scale=8), mat_noise("Wood_Cupboard_Door", "#b8956a", "#c9a77a", scale=8)],
        cupboard, loc=(W / 2 - 0.4, 2.1, 0), rot=(0, 0, math.pi / 2), status="observed", note="U4；位置为推测")
    # 门内柴火堆（U3：门里能看到柴火）

    def firewood(bm):
        rnd = random.Random(9)
        for row in range(4):
            for i in range(5 - row):
                bm_cyl(bm, 0.1, 0.1, 0.7, loc=(-0.4 + i * 0.2 + row * 0.1, 0, 0.1 + row * 0.18),
                       rot=(math.pi / 2, 0, rnd.uniform(-0.05, 0.05)), seg=8, mi=0)
    obj("GQ_Int_Firewood_Stack", "门内柴火堆", [MATS.get("Bark_Log") or mat_noise("Bark_Log", "#5d3f2a", "#7b573c", scale=6)],
        firewood, loc=(1.6, D / 2 - 0.55, 0), note="U3")
    # 马灯（U4）
    obj("GQ_Int_Lantern", "马灯", [mat("Lantern_Metal", "#5a5f62", metal=0.6, rough=0.4), mat("Lantern_Glow", "#ffd38a", emit="#ffb44a", emit_strength=3.0)],
        lambda bm: (bm_cyl(bm, 0.09, 0.09, 0.03, loc=(0, 0, 0), seg=10, mi=0), bm_cyl(bm, 0.07, 0.07, 0.18, loc=(0, 0, 0.11), seg=10, mi=1),
                    bm_cyl(bm, 0.09, 0.03, 0.06, loc=(0, 0, 0.23), seg=10, mi=0)), loc=(-0.5, 0.3, 2.55), note="U4")
    # 室内补光
    li = bpy.data.lights.new("GQ_Int_Light_Warm", "POINT")
    li.energy = 120
    li.color = (1.0, 0.82, 0.6)
    li.shadow_soft_size = 0.4
    lo = bpy.data.objects.new("GQ_Int_Light_Warm", li)
    INT.objects.link(lo)
    lo.parent = root
    lo.location = (-0.5, 0.3, B + 2.35)
    la = bpy.data.lights.new("GQ_Int_Light_Fill", "AREA")
    la.energy = 220
    la.size = 3.0
    lao = bpy.data.objects.new("GQ_Int_Light_Fill", la)
    INT.objects.link(lao)
    lao.parent = root
    lao.location = (0.5, 0.0, B + 2.9)


def build_yard(root):
    """U3/U4 门前和院子里的东西：铁盆、木桶、木墩和斧头、原木、轮胎、绿水管、原木堆；围栏为推测。"""
    P = COLL["Props"]
    hx, hy = HOUSE["x"], HOUSE["y"]
    log_bark = MATS.get("Bark_Log") or mat_noise("Bark_Log", "#5d3f2a", "#7b573c", scale=6)
    cut = MATS.get("Wood_Cut_End") or mat_noise("Wood_Cut_End", "#d7b07a", "#e6c696", scale=12)
    metal = mat("Metal_Galvanized", "#9aa1a6", metal=0.7, rough=0.4)

    def put(name, cn, mats, build, x, y, rot=0.0, status="observed", note=None, smooth_shade=False, sink=0.02):
        bm = bmesh.new()
        build(bm)
        ob = new_obj(name, bm, P, mats, smooth_shade=smooth_shade, props=dict(cn=cn, status=status, note=note))
        ob.location = (x, y, ground(x, y) - sink)
        ob.rotation_euler = (0, 0, rot)
        return ob

    put("Prop_Washtub_Galvanized", "铁皮洗衣盆", [metal],
        lambda bm: bm_cyl(bm, 0.45, 0.38, 0.32, loc=(0, 0, 0.16), seg=20), hx - 3.6, hy + 4.0, note="U3：门左侧")
    put("Prop_Bucket_Galvanized", "铁桶（倒放）", [metal],
        lambda bm: bm_cyl(bm, 0.18, 0.15, 0.36, loc=(0, 0, 0.18), rot=(0, 0, 0), seg=16), hx - 2.9, hy + 4.6, rot=0.3, note="U3")
    put("Prop_Wooden_Barrel", "木桶", [mat_noise("Wood_Barrel", "#8a5a33", "#a06b3f", scale=10), metal],
        lambda bm: (bm_sphere(bm, (0.34, 0.34, 0.45), loc=(0, 0, 0.45), seg=16, rings=10,
                              deform=lambda co: Vector((co.x, co.y, clamp(co.z, -0.85, 0.85)))),
                    bm_torus(bm, 0.36, 0.02, loc=(0, 0, 0.2), mi=1), bm_torus(bm, 0.36, 0.02, loc=(0, 0, 0.7), mi=1)),
        hx + 3.5, hy + 3.7, smooth_shade=True, note="U3：门右侧")
    # 木墩 + 斧头
    blk = put("Prop_Chopping_Block", "劈柴木墩", [log_bark, cut],
              lambda bm: (bm_cyl(bm, 0.36, 0.4, 0.55, loc=(0, 0, 0.275), seg=12, mi=0), bm_cyl(bm, 0.355, 0.355, 0.01, loc=(0, 0, 0.555), seg=12, mi=1)),
              hx + 5.2, hy + 5.0, note="U3")
    put("Prop_Axe", "斧头", [mat_noise("Wood_Axe_Handle", "#9b7347", "#b08455", scale=10), mat("Steel_Axe_Head", "#9fa6ab", metal=0.8, rough=0.3)],
        lambda bm: (bm_cyl(bm, 0.025, 0.03, 0.75, loc=(0, 0, 0.6 + 0.3), rot=(0, 0.45, 0), seg=8, mi=0),
                    bm_cube(bm, (0.2, 0.04, 0.12), loc=(-0.12, 0, 0.56), rot=(0, 0.45, 0), mi=1)),
        hx + 5.2, hy + 5.0, sink=0.0 - 0.0, note="U3：斧头插在木墩上")
    # 门前的原木、原木堆
    put("Prop_Logs_Front", "门前的原木", [log_bark, cut],
        lambda bm: [(bm_cyl(bm, 0.16, 0.16, 1.6, loc=(0, i * 0.34, 0.16), rot=(0, math.pi / 2, 0), seg=10, mi=0)) for i in range(3)],
        hx + 4.6, hy + 6.6, rot=0.2, note="U3")

    def log_pile(bm, n=5, L=4.0, r=0.3):
        for row in range(n):
            for i in range(n - row):
                x = (i - (n - row - 1) / 2) * r * 2.05
                z = r + row * r * 1.75
                bm_cyl(bm, r, r, L, loc=(x, 0, z), rot=(math.pi / 2, 0, 0), seg=10, mi=0, caps=False)
                bm_cyl(bm, r * 0.97, r * 0.97, 0.02, loc=(x, L / 2, z), rot=(math.pi / 2, 0, 0), seg=10, mi=1)
                bm_cyl(bm, r * 0.97, r * 0.97, 0.02, loc=(x, -L / 2, z), rot=(math.pi / 2, 0, 0), seg=10, mi=1)
    put("Prop_Log_Pile_A", "原木堆", [log_bark, cut], lambda bm: log_pile(bm, 5), LOGYARD[0], LOGYARD[1], rot=0.4,
        note="U4：窗外能看到原木堆")
    put("Prop_Log_Pile_B", "原木堆", [log_bark, cut], lambda bm: log_pile(bm, 4, 3.4, 0.26), LOGYARD[0] + 3.5, LOGYARD[1] + 5.0, rot=1.2,
        note="U4")
    rnd = random.Random(17)
    for k in range(8):
        a = rnd.uniform(0, 6.28)
        r = rnd.uniform(2.5, 6.0)
        x, y = LOGYARD[0] + math.cos(a) * r, LOGYARD[1] + math.sin(a) * r
        rr = rnd.uniform(0.3, 0.5)
        put(f"Prop_Stump_{k}", "树桩", [log_bark, cut],
            lambda bm, rr=rr: (bm_cyl(bm, rr, rr * 1.2, 0.5, loc=(0, 0, 0.25), seg=12, mi=0), bm_cyl(bm, rr * 0.98, rr * 0.98, 0.01, loc=(0, 0, 0.505), seg=12, mi=1)),
            x, y, status="inferred")
    # 轮胎堆和绿色水管（U4 窗外）
    tire = mat("Rubber_Tire", "#232426", rough=0.9)
    put("Prop_Tire_Stack", "轮胎堆", [tire],
        lambda bm: [bm_torus(bm, 0.36, 0.14, loc=(0, 0, 0.14 + i * 0.27), seg=20, rseg=8) for i in range(3)],
        hx - 6.2, hy - 1.0, smooth_shade=True, note="U4")

    def hose(bm):
        pts = []
        for i in range(60):
            a = i * 0.42
            r = 0.32 + i * 0.002
            pts.append((math.cos(a) * r, math.sin(a) * r, 0.03 + (i % 15) * 0.0))
        bm_tube(bm, pts, [0.025] * len(pts), seg=6, mi=0)
    put("Prop_Garden_Hose_Green", "绿色水管", [mat("Rubber_Hose_Green", "#2f8a4e", rough=0.5)], hose, hx - 5.4, hy + 1.2,
        smooth_shade=True, note="U4")
    # 围栏（推测：合影背景里有木栅栏，但那张图与四季篇木屋有冲突）
    rail = mat_noise("Wood_Fence", "#9b7650", "#ae8960", scale=8)
    pts = [(hx - 8, hy + 8), (hx - 8, hy - 5), (hx + 6, hy - 6), (hx + 10, hy - 3)]
    for i, ((ax, ay), (bx, by)) in enumerate(zip(pts[:-1], pts[1:])):
        L = math.hypot(bx - ax, by - ay)
        n = max(1, int(L / 1.8))
        bm = bmesh.new()
        ang = math.atan2(by - ay, bx - ax)
        for k in range(n + 1):
            t = k / n
            x, y = ax + (bx - ax) * t, ay + (by - ay) * t
            bm_cube(bm, (0.12, 0.12, 1.3), loc=(x, y, ground(x, y) + 0.5))
        for k in range(n):
            t = (k + 0.5) / n
            x, y = ax + (bx - ax) * t, ay + (by - ay) * t
            for zz in (0.45, 0.95):
                bm_cube(bm, (L / n + 0.1, 0.06, 0.1), loc=(x, y, ground(x, y) + zz), rot=(0, 0, ang))
        new_obj(f"Prop_Fence_Segment_{i}", bm, P, [rail], props=dict(cn="木栅栏", status="inferred",
                                                                   note="合影背景有木栅栏，但该图与 U3 木屋有冲突，按推测处理"))


# ------------------------------------------------------------------------------------------------
# 熊大熊二的树洞（推测）与蜂巢树


def build_bears_home():
    C = COLL["Bears_TreeHome"]
    x, y = BEARHOME["x"], BEARHOME["y"]
    gz = ground(x, y)
    root = empty("Bears_TreeHome_Root", C, (x, y, gz - 0.2), (0, 0, BEARHOME["rot"]), size=2.0,
                 props=dict(cn="熊大熊二的树洞（推测模型）", status="inferred",
                            note="资料：住在树洞里；片头只能看到树洞内部，外观为推测"))
    bark = mat_noise("Bark_Big_Tree", "#5a3c28", "#77543a", scale=3, bump=0.5)
    bm = bmesh.new()
    rnd = random.Random(3)
    pts = [(0, 0, -0.5), (0, 0, 2), (0.2, 0.1, 5), (0.1, -0.1, 8), (0.3, 0, 10.5)]
    bm_tube(bm, pts, [2.6, 2.1, 1.8, 1.5, 1.1], seg=14, mi=0)
    for k in range(7):
        a = 2 * math.pi * k / 7 + 0.2
        if abs(math.atan2(math.sin(a + math.pi / 2), math.cos(a + math.pi / 2))) < 0.55:
            continue  # 门洞前不放树根
        bm_tube(bm, [(math.cos(a) * 1.6, math.sin(a) * 1.6, 1.4), (math.cos(a) * 2.8, math.sin(a) * 2.8, 0.3), (math.cos(a) * 3.6, math.sin(a) * 3.6, -0.3)],
                [0.75, 0.5, 0.2], seg=8, mi=0)
    for k in range(5):
        a = 2 * math.pi * k / 5 + 0.5
        bm_tube(bm, [(0.2, 0, 9.5), (math.cos(a) * 2.5, math.sin(a) * 2.5, 11.5), (math.cos(a) * 4.5, math.sin(a) * 4.5, 12.5)],
                [0.6, 0.4, 0.15], seg=8, mi=0)
    new_obj("Bears_TreeHome_Trunk", bm, C, [bark], smooth_shade=True, parent=root,
            props=dict(cn="树洞大树树干", status="inferred"))
    bm = bmesh.new()
    for k in range(9):
        a = 2 * math.pi * k / 9
        r = rnd.uniform(3.0, 4.2)
        bm_ico(bm, r, loc=(math.cos(a) * 4, math.sin(a) * 4, 13 + rnd.uniform(-0.5, 1.5)), scale=(1, 1, 0.8), subdiv=2, rough=0.2, seed=k)
    bm_ico(bm, 4.5, loc=(0, 0, 15), scale=(1, 1, 0.8), subdiv=2, rough=0.2, seed=20)
    new_obj("Bears_TreeHome_Canopy", bm, C, [MATS["Foliage_Broadleaf_Dark"]], smooth_shade=True, parent=root,
            props=dict(cn="树冠", status="inferred"))
    # 门：拱形木门（门朝局部 -Y）
    wood = mat_noise("Wood_BearDoor", "#6a4528", "#80573a", scale=8)
    bm = bmesh.new()
    bm_cube(bm, (1.5, 0.15, 1.3), loc=(0, 0, 0.65), mi=0)
    bm_cyl(bm, 0.75, 0.75, 0.15, loc=(0, 0, 1.3), rot=(math.pi / 2, 0, 0), seg=20, mi=0)
    for xx in (-0.4, 0, 0.4):
        bm_cube(bm, (0.05, 0.18, 1.9), loc=(xx, -0.02, 0.95), mi=1)
    bm_sphere(bm, (0.07, 0.07, 0.07), loc=(0.5, -0.12, 1.0), mi=2)
    ob = new_obj("Bears_TreeHome_Door", bm, C, [wood, mat_noise("Wood_BearDoor_Planks", "#4f331e", "#5f3d25", scale=8),
                                                 mat("Brass_Knob", "#d8a63a", metal=0.7, rough=0.3)], parent=root,
                 props=dict(cn="树洞木门（推测）", status="inferred"))
    ob.location = (0, -2.25, 0.2)
    bm = bmesh.new()
    bm_cyl(bm, 0.4, 0.4, 0.1, rot=(math.pi / 2, 0, 0), seg=16, mi=0)
    bm_torus(bm, 0.43, 0.07, rot=(math.pi / 2, 0, 0), seg=18, rseg=6, mi=1)
    ob = new_obj("Bears_TreeHome_Window", bm, C, [mat("Glass_Window_Warm2", "#ffe2a0", rough=0.3, emit="#ffc46a", emit_strength=0.6), wood],
                 parent=root, props=dict(cn="树洞圆窗（推测）", status="inferred"))
    ob.location = (0.9, -1.75, 4.3)
    ob.rotation_euler = (0, 0, 0.45)

    # 蜂巢树 + 叠圈蜂巢（第一季片头可见）
    hx, hy = HONEYTREE
    tr = linked(bpy.data.objects["Proto_Broadleaf_1"], "Tree_HoneyTree", COLL["Forest_Trees"], (hx, hy, ground(hx, hy) - 0.15),
                (0, 0, 0.7), 1.15, props=dict(cn="蜂蜜树", status="inferred"))
    hive_m = [mat_noise("Beehive_Tan", "#c9a066", "#d9b47a", scale=6), mat("Beehive_Hole", "#2a1d12")]
    for k, (dx, dy, dz) in enumerate(((2.6, 0.6, 6.2), (-1.8, 1.9, 6.6))):
        bm = bmesh.new()
        for i in range(6):
            r = 0.38 - abs(i - 2.2) * 0.07
            bm_torus(bm, r, 0.11, loc=(0, 0, -i * 0.17), seg=16, rseg=6, mi=0)
        bm_sphere(bm, (0.3, 0.3, 0.45), loc=(0, 0, -0.45), seg=12, rings=8, mi=0)
        bm_sphere(bm, (0.08, 0.04, 0.08), loc=(0, -0.32, -0.6), seg=8, rings=6, mi=1)
        bm_cyl(bm, 0.03, 0.03, 0.5, loc=(0, 0, 0.25), seg=6, mi=0)
        ob = new_obj(f"Prop_Beehive_{k}", bm, COLL["Props"], hive_m, smooth_shade=True,
                     props=dict(cn="蜂巢", status="observed", note="第一季片头：一圈圈叠起来的蜂巢挂在树枝上"))
        ob.location = (hx + dx, hy + dy, ground(hx, hy) + dz)


# ------------------------------------------------------------------------------------------------
# 阶段 5：皮卡（第一季截图；四季篇是否同一辆车不确定 → 推测）


def build_pickup():
    V = COLL["Vehicles"]
    x, y, rot = 41.5, -18.5, math.radians(-100)
    root = empty("Vehicle_Pickup_Root", V, (x, y, ground(x, y)), (0, 0, rot), size=1.5,
                 props=dict(cn="光头强的蓝色皮卡", status="inferred",
                            note="第一季截图：蓝色四驱皮卡；四季篇是否同一辆车无法确认"))
    blue = mat("Paint_Pickup_Blue", "#2f63b9", rough=0.35, metal=0.2)
    dark = mat("Pickup_Chassis_Dark", "#2b2e33", rough=0.6)
    chrome = mat("Chrome", "#d5dbe0", metal=0.9, rough=0.2)
    glass = mat("Glass_Car", "#9fc0d4", rough=0.08, transmission=0.6)
    seat = mat("Seat_Orange", "#d9742c", rough=0.7)
    plate = mat("Plate_Yellow", "#f2c521", rough=0.5)
    tail = mat("Light_Tail_Red", "#d8261e", emit="#ff2010", emit_strength=0.5)
    head = mat("Light_Head", "#f6f3e4", emit="#fff8e0", emit_strength=0.4)
    tire = MATS.get("Rubber_Tire") or mat("Rubber_Tire", "#232426", rough=0.9)
    rim = mat("Rim_Silver", "#b9c0c6", metal=0.7, rough=0.3)
    L, Wd = 5.2, 2.0
    wr = 0.48  # 轮胎半径
    zb = wr + 0.35  # 底盘高（越野抬高）

    def part(name, cn, mats, build, smooth_shade=False):
        bm = bmesh.new()
        build(bm)
        return new_obj(name, bm, V, mats, smooth_shade=smooth_shade, parent=root, props=dict(cn=cn, status="inferred"))

    def body(bm):
        bm_cube(bm, (Wd * 0.9, L * 0.95, 0.25), loc=(0, 0, zb), mi=1)  # 车架
        bm_cube(bm, (Wd, 1.75, 0.7), loc=(0, L / 2 - 0.9, zb + 0.45), mi=0)  # 引擎盖
        bm_cube(bm, (Wd, 1.7, 0.8), loc=(0, 0.45, zb + 0.5), mi=0)  # 驾驶室下部
        bm_cube(bm, (Wd * 0.96, 1.45, 0.65), loc=(0, 0.35, zb + 1.22), mi=0)  # 驾驶室上部
        bm_cube(bm, (Wd * 0.96, 1.5, 0.07), loc=(0, 0.35, zb + 1.57), mi=0)  # 车顶
        bm_cube(bm, (Wd, 2.2, 0.15), loc=(0, -1.55, zb + 0.18), mi=0)  # 车斗底
        for sx in (-1, 1):
            bm_cube(bm, (0.08, 2.2, 0.62), loc=(sx * Wd / 2, -1.55, zb + 0.55), mi=0)
        bm_cube(bm, (Wd, 0.08, 0.62), loc=(0, -2.62, zb + 0.55), mi=0)
        # 轮拱
        for sy in (L / 2 - 1.0, -1.7):
            for sx in (-1, 1):
                bm_torus(bm, wr + 0.12, 0.08, loc=(sx * (Wd / 2 + 0.02), sy, wr), rot=(0, math.pi / 2, 0), seg=16, rseg=6,
                         arc=math.pi, mi=0)
    part("Vehicle_Pickup_Body", "车身", [blue, dark], body)
    part("Vehicle_Pickup_Windows", "车窗", [glass], lambda bm: (
        bm_cube(bm, (Wd * 0.98, 0.04, 0.55), loc=(0, 1.08, zb + 1.2), rot=(-0.35, 0, 0)),
        bm_cube(bm, (Wd * 0.98, 1.2, 0.5), loc=(0, 0.3, zb + 1.22)),
        bm_cube(bm, (Wd * 0.9, 0.04, 0.45), loc=(0, -0.38, zb + 1.22))))
    part("Vehicle_Pickup_Seats", "橙色座椅", [seat], lambda bm: bm_cube(bm, (Wd * 0.85, 0.5, 0.75), loc=(0, 0.0, zb + 0.95)))
    part("Vehicle_Pickup_Grille_BullBar", "镀铬格栅和护杠", [chrome], lambda bm: (
        bm_cube(bm, (1.3, 0.05, 0.42), loc=(0, L / 2 - 0.02, zb + 0.5)),
        [bm_cube(bm, (0.04, 0.07, 0.4), loc=(-0.55 + i * 0.11, L / 2, zb + 0.5)) for i in range(11)],
        bm_cyl(bm, 0.06, 0.06, Wd * 1.05, loc=(0, L / 2 + 0.25, zb + 0.05), rot=(0, math.pi / 2, 0), seg=10),
        bm_cyl(bm, 0.05, 0.05, Wd * 0.85, loc=(0, L / 2 + 0.28, zb + 0.6), rot=(0, math.pi / 2, 0), seg=10),
        [bm_cyl(bm, 0.05, 0.05, 0.6, loc=(sx * 0.6, L / 2 + 0.26, zb + 0.32), seg=8) for sx in (-1, 1)]), smooth_shade=True)
    part("Vehicle_Pickup_Lights", "车灯", [head, tail], lambda bm: (
        [bm_cyl(bm, 0.14, 0.14, 0.05, loc=(sx * 0.78, L / 2 + 0.0, zb + 0.58), rot=(math.pi / 2, 0, 0), seg=14, mi=0) for sx in (-1, 1)],
        [bm_cube(bm, (0.2, 0.05, 0.28), loc=(sx * 0.88, -2.67, zb + 0.6), mi=1) for sx in (-1, 1)]))
    part("Vehicle_Pickup_Plates", "黄色车牌", [plate], lambda bm: (
        bm_cube(bm, (0.55, 0.03, 0.17), loc=(0, L / 2 + 0.03, zb + 0.16)),
        bm_cube(bm, (0.55, 0.03, 0.17), loc=(0, -2.68, zb + 0.3))))
    part("Vehicle_Pickup_Mirrors", "后视镜", [dark], lambda bm: [
        bm_cube(bm, (0.08, 0.2, 0.16), loc=(sx * (Wd / 2 + 0.12), 1.05, zb + 1.15)) for sx in (-1, 1)])
    # 四个独立车轮
    for wi, (sx, sy) in enumerate(((-1, L / 2 - 1.0), (1, L / 2 - 1.0), (-1, -1.7), (1, -1.7))):
        bm = bmesh.new()
        bm_cyl(bm, wr, wr, 0.42, rot=(0, math.pi / 2, 0), seg=20, mi=0)
        for k in range(16):
            a = 2 * math.pi * k / 16
            bm_cube(bm, (0.44, 0.1, 0.06), loc=(0, math.cos(a) * wr, math.sin(a) * wr), rot=(a, 0, 0), mi=0)
        bm_cyl(bm, wr * 0.55, wr * 0.55, 0.44, rot=(0, math.pi / 2, 0), seg=10, mi=1)
        ob = new_obj(f"Vehicle_Pickup_Wheel_{['FL', 'FR', 'RL', 'RR'][wi]}", bm, V, [tire, rim], smooth_shade=False, parent=root,
                     props=dict(cn="越野轮胎（银色轮毂）", status="observed", note="第一季截图：大越野胎、银色轮毂"))
        ob.location = (sx * (Wd / 2 - 0.05), sy, wr)
    # 车斗里的原木
    part("Vehicle_Pickup_Bed_Logs", "车斗里的原木", [MATS["Bark_Log"], MATS["Wood_Cut_End"]], lambda bm: [
        (bm_cyl(bm, 0.22, 0.22, 2.0, loc=(-0.55 + i * 0.55, -1.55, zb + 0.48), rot=(math.pi / 2, 0, 0), seg=10, mi=0)) for i in range(3)])


# ------------------------------------------------------------------------------------------------
# 阶段 5：角色


def mat_fur_patch(name, fur, patch, kind, oval=(0.0, 0.82, 0.47, 0.5), front_y=-0.12):
    """毛色分区材质：用物体坐标在着色器里画出平滑边界的色块。
    kind='bib'：熊大胸前的 V 字；kind='belly'：熊二的椭圆肚皮。坐标与角色身体网格一致（正面为 -Y）。"""
    if name in MATS:
        return MATS[name]
    m = _new_mat(name)
    nodes, links = _nodes(m)
    b = nodes.get("Principled BSDF")
    tc = nodes.new("ShaderNodeTexCoord")
    sep = nodes.new("ShaderNodeSeparateXYZ")
    links.new(tc.outputs["Object"], sep.inputs[0])

    def math_node(op, a, bval=None, clamp_=False):
        n = nodes.new("ShaderNodeMath")
        n.operation = op
        n.use_clamp = clamp_
        for i, v in enumerate((a, bval)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                links.new(v, n.inputs[i])
        return n.outputs[0]

    def soft(v, width):  # 0 → 1 平滑过渡
        n = nodes.new("ShaderNodeMapRange")
        n.interpolation_type = "SMOOTHSTEP"
        n.inputs["From Min"].default_value = -width
        n.inputs["From Max"].default_value = width
        links.new(v, n.inputs["Value"])
        return n.outputs["Result"]
    X, Y, Z = sep.outputs["X"], sep.outputs["Y"], sep.outputs["Z"]
    front = soft(math_node("SUBTRACT", front_y, Y), 0.04)  # y < front_y
    if kind == "bib":
        # |x| < 0.05 + 0.34 * (z - 0.74)，且 0.74 < z < 1.72
        lim = math_node("ADD", math_node("MULTIPLY", math_node("SUBTRACT", Z, 0.74), 0.34), 0.05)
        v = soft(math_node("SUBTRACT", lim, math_node("ABSOLUTE", X)), 0.012)
        top = soft(math_node("SUBTRACT", 1.72, Z), 0.02)
        mask = math_node("MULTIPLY", math_node("MULTIPLY", v, top), front)
    else:
        # (x/0.47)^2 + ((z-0.82)/0.5)^2 < 1
        ox, oz, orx, orz = oval
        ex = math_node("POWER", math_node("DIVIDE", math_node("SUBTRACT", X, ox), orx), 2.0)
        ez = math_node("POWER", math_node("DIVIDE", math_node("SUBTRACT", Z, oz), orz), 2.0)
        oval = soft(math_node("SUBTRACT", 1.0, math_node("ADD", ex, ez)), 0.06)
        mask = math_node("MULTIPLY", oval, front)
    mix = nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs["A"].default_value = srgb(fur)
    mix.inputs["B"].default_value = srgb(patch)
    links.new(mask, mix.inputs["Factor"])
    links.new(mix.outputs["Result"], b.inputs["Base Color"])
    _set(b, "Roughness", 0.75)
    m.diffuse_color = srgb(fur)
    MATS[name] = m
    return m


def char_mats(prefix, d):
    return {k: mat(f"{prefix}_{k}", v, rough=0.75 if k not in ("Nose", "Eye_White", "Pupil") else 0.3) for k, v in d.items()}


EYE = dict(Eye_White="#ffffff", Pupil="#16110d", Mouth="#4a1d18", Teeth="#fbf8f0")


def part_blob(root, C, name, cn, mats, radii, loc, rot=(0, 0, 0), region=None, deform=None, seg=20, rings=14, subsurf=2):
    bm = bmesh.new()
    bm_sphere(bm, radii, loc=loc, rot=rot, seg=seg, rings=rings, region=region, deform=deform, mi=0)
    return new_obj(name, bm, C, mats, smooth_shade=True, subsurf=subsurf, parent=root, props=dict(cn=cn))


def part_limb(root, C, name, cn, mats, p0, p1, r0, r1, subsurf=1):
    """四肢：两端圆头的锥形管。"""
    bm = bmesh.new()
    p0, p1 = Vector(p0), Vector(p1)
    pts, rad = [], []
    n = 8
    for i in range(n + 1):
        t = i / n
        pts.append(p0.lerp(p1, t))
        r = lerp(r0, r1, t)
        end = min(t, 1 - t) * n
        rad.append(r * (math.sin(min(1.0, end / 2.0) * math.pi / 2) * 0.7 + 0.3) if end < 2 else r)
    bm_tube(bm, pts, rad, seg=12, mi=0)
    return new_obj(name, bm, C, mats, smooth_shade=True, subsurf=subsurf, parent=root, props=dict(cn=cn))


def eyes_pair(root, C, prefix, M, x, y, z, r, iris=None, ring=None):
    for s, sn in ((-1, "L"), (1, "R")):
        part_blob(root, C, f"{prefix}_Eye_{sn}", "眼白", [M["Eye_White"]], (r, r * 0.7, r * 1.15), (s * x, y, z), seg=14, rings=10, subsurf=1)
        part_blob(root, C, f"{prefix}_Pupil_{sn}", "眼珠", [iris or M["Pupil"]], (r * 0.5, r * 0.25, r * 0.55), (s * x, y - r * 0.62, z),
                  seg=12, rings=8, subsurf=1)


def bear(name_en, cn, C, pos, rot, fur, fur_dark, bib, belly, muzzle, nose, plump=1.0):
    gz = ground(*pos)
    root = empty(f"{name_en}_Root", C, (pos[0], pos[1], gz), (0, 0, rot), size=0.6,
                 props=dict(cn=cn, status="observed", note="高 2.0 m（比例基准）"))
    M = char_mats(name_en, dict(Fur=fur, FurDark=fur_dark, Chest=bib or belly, Muzzle=muzzle, Nose=nose, **EYE))
    rx, ry, rz = 0.62 * plump, 0.5 * plump, 0.8

    def body_region(c):
        # 面中心在单位球空间：-Y 为正面
        if c.y < -0.15:
            if bib and -0.35 < c.z < 0.95 and abs(c.x) < 0.08 + 0.5 * ((c.z + 0.35) / 1.3):
                return 1
            if not bib and c.z < 0.45 and math.hypot(c.x * 1.15, (c.z + 0.1) * 0.85) < 0.62:
                return 1
        return 0
    body_mat = mat_fur_patch(f"{name_en}_Fur_With_{'Bib' if bib else 'Belly'}", fur, bib or belly, "bib" if bib else "belly")
    part_blob(root, C, f"{name_en}_Body", "身体（梨形，胸前毛色分区）", [body_mat], (rx, ry, rz), (0, 0, 1.0), deform=lambda co: Vector((co.x * (1 + 0.16 * -co.z), co.y * (1 + 0.12 * -co.z), co.z)),
              seg=48, rings=32)
    hz = 1.68
    part_blob(root, C, f"{name_en}_Head", "头", [M["Fur"]], (0.4, 0.37, 0.34), (0, -0.06, hz),
              deform=lambda co: Vector((co.x * (1 + 0.06 * co.z), co.y, co.z)))
    part_blob(root, C, f"{name_en}_Muzzle", "口鼻", [M["Muzzle"]], (0.26, 0.2, 0.19), (0, -0.33, hz - 0.08))
    part_blob(root, C, f"{name_en}_Nose", "鼻子", [M["Nose"]], (0.14, 0.1, 0.095), (0, -0.53, hz + 0.0), subsurf=1)
    part_blob(root, C, f"{name_en}_Mouth", "嘴", [M["Mouth"]], (0.12, 0.05, 0.035), (0, -0.5, hz - 0.15), subsurf=1)
    eyes_pair(root, C, name_en, M, 0.13, -0.36, hz + 0.12, 0.065)
    for s, sn in ((-1, "L"), (1, "R")):
        part_blob(root, C, f"{name_en}_Brow_{sn}", "眉毛", [M["FurDark"]], (0.1, 0.05, 0.035), (s * 0.13, -0.37, hz + 0.21),
                  rot=(0, s * 0.25, 0), subsurf=1)
        part_blob(root, C, f"{name_en}_Ear_{sn}", "耳朵", [M["Fur"]], (0.12, 0.06, 0.12), (s * 0.29, -0.02, hz + 0.29),
                  rot=(0, 0, s * 0.3), subsurf=1)
        part_blob(root, C, f"{name_en}_EarInner_{sn}", "耳朵内侧", [M["Muzzle"]], (0.07, 0.03, 0.07), (s * 0.29, -0.06, hz + 0.29),
                  rot=(0, 0, s * 0.3), subsurf=1)
        # 手臂、手掌
        sh = Vector((s * 0.6 * plump, -0.02, 1.45))
        hand = Vector((s * 0.8 * plump, -0.12, 0.72))
        part_limb(root, C, f"{name_en}_Arm_{sn}", "手臂", [M["Fur"]], sh, hand, 0.2, 0.15)
        part_blob(root, C, f"{name_en}_Paw_{sn}", "手掌", [M["FurDark"]], (0.15, 0.13, 0.15), (hand.x, hand.y, hand.z - 0.08))
        # 腿、脚掌（脚底在 z=0）
        part_limb(root, C, f"{name_en}_Leg_{sn}", "腿", [M["Fur"]], (s * 0.33 * plump, 0, 0.6), (s * 0.34 * plump, -0.02, 0.14), 0.26, 0.22)
        part_blob(root, C, f"{name_en}_Foot_{sn}", "脚掌", [M["FurDark"]], (0.21, 0.3, 0.1), (s * 0.34 * plump, -0.12, 0.1), subsurf=1)
    part_blob(root, C, f"{name_en}_Tail", "尾巴", [M["Fur"]], (0.12, 0.1, 0.12), (0, 0.5 * plump, 0.62), subsurf=1)
    return root


def guangtouqiang(C, pos, rot):
    gz = ground(*pos)
    root = empty("GuangtouQiang_Root", C, (pos[0], pos[1], gz), (0, 0, rot), size=0.5,
                 props=dict(cn="光头强（四季篇造型）", status="observed",
                            note="U3/U4 + 四季篇海报：护耳棉帽、深蓝外衣、毛边短夹克、紫色白条运动裤；高 1.55 m（估算）"))
    M = char_mats("GuangtouQiang", dict(Skin="#eab68c", Nose="#d9483d", Sweater="#26305f", Vest="#b98242", Trim="#ecdcb8",
                                        Pants="#4a3577", Stripe="#eeeeee", Shoe="#1c1a1a", Belt="#6b2a24", Hat="#8d6648",
                                        HatLight="#a98163", Brow="#3a2618", **EYE))
    for s, sn in ((-1, "L"), (1, "R")):
        part_limb(root, C, f"GuangtouQiang_Leg_{sn}", "裤腿（紫色运动裤）", [M["Pants"]], (s * 0.1, 0, 0.78), (s * 0.11, 0, 0.12), 0.075, 0.062)
        bm = bmesh.new()
        bm_cube(bm, (0.012, 0.03, 0.62), loc=(s * 0.172, 0, 0.45), rot=(0, s * -0.02, 0))
        new_obj(f"GuangtouQiang_Pants_Stripe_{sn}", bm, C, [M["Stripe"]], parent=root, props=dict(cn="裤子侧边白条", note="U4"))
        part_blob(root, C, f"GuangtouQiang_Shoe_{sn}", "黑鞋", [M["Shoe"]], (0.075, 0.15, 0.06), (s * 0.11, -0.05, 0.06), subsurf=1)
    part_blob(root, C, "GuangtouQiang_Belt", "腰带", [M["Belt"]], (0.19, 0.14, 0.04), (0, 0, 0.76), subsurf=1)
    part_blob(root, C, "GuangtouQiang_Torso_Sweater", "深蓝毛衣", [M["Sweater"]], (0.2, 0.14, 0.27), (0, 0, 0.98),
              deform=lambda co: Vector((co.x * (1 + 0.08 * co.z), co.y, co.z)))
    # 毛边短夹克：比身体略大的外壳，前面敞开
    bm = bmesh.new()
    bm_sphere(bm, (0.215, 0.155, 0.255), loc=(0, 0, 0.99), seg=24, rings=14)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.calc_center_median().y < -0.08 and abs(f.calc_center_median().x) < 0.075
                                or f.calc_center_median().z < 0.8], context="FACES")
    ob = new_obj("GuangtouQiang_Vest_Jacket", bm, C, [M["Vest"]], smooth_shade=True, parent=root, recalc=False,
                 props=dict(cn="黄棕色毛边短夹克"))
    sd = ob.modifiers.new("Solidify", "SOLIDIFY")
    sd.thickness = 0.02
    for nm, loc, R, sc in (("Collar", (0, 0, 1.2), 0.15, (1.0, 0.85, 1)), ("Hem", (0, 0, 0.8), 0.19, (1.05, 0.78, 1))):
        bm = bmesh.new()
        bm_torus(bm, R, 0.03, loc=loc, seg=22, rseg=8, scale=sc)
        new_obj(f"GuangtouQiang_Fur_Trim_{nm}", bm, C, [M["Trim"]], smooth_shade=True, parent=root, props=dict(cn="奶白色毛边"))
    for s, sn in ((-1, "L"), (1, "R")):
        sh = Vector((s * 0.21, 0, 1.16))
        wr = Vector((s * 0.3, -0.03, 0.74))
        part_limb(root, C, f"GuangtouQiang_Arm_{sn}", "深蓝袖子", [M["Sweater"]], sh, wr, 0.06, 0.05)
        bm = bmesh.new()
        bm_torus(bm, 0.055, 0.022, loc=(wr.x, wr.y, wr.z + 0.04), seg=14, rseg=6)
        new_obj(f"GuangtouQiang_Cuff_{sn}", bm, C, [M["Trim"]], smooth_shade=True, parent=root, props=dict(cn="毛边袖口"))
        part_blob(root, C, f"GuangtouQiang_Hand_{sn}", "手", [M["Skin"]], (0.05, 0.045, 0.06), (wr.x, wr.y, wr.z - 0.03), subsurf=1)
    part_blob(root, C, "GuangtouQiang_Neck", "脖子", [M["Skin"]], (0.06, 0.06, 0.06), (0, 0, 1.25), subsurf=1)
    hz = 1.42
    part_blob(root, C, "GuangtouQiang_Head", "大脑袋（光头）", [M["Skin"]], (0.2, 0.19, 0.24), (0, -0.01, hz),
              deform=lambda co: Vector((co.x * (1 + 0.14 * co.z), co.y * (1 + 0.1 * co.z), co.z)))
    part_blob(root, C, "GuangtouQiang_Nose", "红鼻子", [M["Nose"]], (0.065, 0.055, 0.055), (0, -0.21, hz - 0.02), subsurf=1)
    eyes_pair(root, C, "GuangtouQiang", M, 0.075, -0.16, hz + 0.05, 0.045)
    for s, sn in ((-1, "L"), (1, "R")):
        part_blob(root, C, f"GuangtouQiang_Brow_{sn}", "眉毛", [M["Brow"]], (0.05, 0.015, 0.015), (s * 0.08, -0.19, hz + 0.115),
                  rot=(0, s * 0.2, 0), subsurf=1)
        part_blob(root, C, f"GuangtouQiang_Ear_{sn}", "耳朵", [M["Skin"]], (0.03, 0.05, 0.06), (s * 0.2, 0.0, hz), subsurf=1)
        part_blob(root, C, f"GuangtouQiang_Moustache_{sn}", "小胡子", [M["Brow"]], (0.04, 0.01, 0.009), (s * 0.04, -0.215, hz - 0.075),
                  rot=(0, s * 0.35, 0), subsurf=0)
    part_blob(root, C, "GuangtouQiang_Mouth", "咧嘴笑", [M["Mouth"]], (0.08, 0.03, 0.025), (0, -0.18, hz - 0.13), subsurf=1)
    part_blob(root, C, "GuangtouQiang_Teeth", "牙齿", [M["Teeth"]], (0.065, 0.02, 0.012), (0, -0.2, hz - 0.115), subsurf=1)
    # 护耳棉帽（耳朵翻上去）
    part_blob(root, C, "GuangtouQiang_Hat_Crown", "护耳棉帽（帽顶）", [M["Hat"]], (0.23, 0.23, 0.13), (0, 0, hz + 0.19))
    bm = bmesh.new()
    bm_torus(bm, 0.21, 0.06, loc=(0, 0, hz + 0.14), seg=24, rseg=8, scale=(1.0, 1.0, 1.0))
    new_obj("GuangtouQiang_Hat_FurBand", bm, C, [M["HatLight"]], smooth_shade=True, parent=root, props=dict(cn="帽檐毛边"))
    for s, sn in ((-1, "L"), (1, "R")):
        part_blob(root, C, f"GuangtouQiang_Hat_EarFlap_{sn}", "翻起的护耳", [M["HatLight"]], (0.05, 0.11, 0.1),
                  (s * 0.24, 0, hz + 0.2), rot=(0, s * 0.6, 0), subsurf=1)
    part_blob(root, C, "GuangtouQiang_Hat_FrontFlap", "翻起的前檐", [M["HatLight"]], (0.15, 0.04, 0.07), (0, -0.21, hz + 0.24),
              rot=(0.5, 0, 0), subsurf=1)
    # 电锯（右手）
    bm = bmesh.new()
    bm_cube(bm, (0.13, 0.28, 0.16), loc=(0, 0, 0), mi=0)
    bm_cube(bm, (0.025, 0.55, 0.08), loc=(0, -0.4, -0.01), mi=1)
    bm_torus(bm, 0.06, 0.012, loc=(0, 0.04, 0.11), rot=(0, math.pi / 2, 0), seg=12, rseg=6, mi=2)
    ob = new_obj("GuangtouQiang_Chainsaw", bm, C, [mat("Chainsaw_Orange", "#f29a1e", rough=0.5), mat("Chainsaw_Bar_Steel", "#c9d0d6", metal=0.8, rough=0.3),
                                                    mat("Chainsaw_Handle_Black", "#202020")], parent=root,
                 props=dict(cn="电锯", status="observed", note="四季篇海报、第一季截图"))
    ob.location = (0.32, -0.12, 0.66)
    return root


def tutu(C, pos, rot):
    root = empty("TuTu_Root", C, (pos[0], pos[1], ground(*pos)), (0, 0, rot), size=0.3,
                 props=dict(cn="涂涂（猫头鹰）", status="observed", note="U2；高 0.55 m（估算）"))
    M = char_mats("TuTu", dict(Red="#b8452f", Cream="#f3ead6", Feather="#e5c9a8", Ring="#a8382a", Beak="#f1b62e", Iris="#4f9a3a", **EYE))
    part_blob(root, C, "TuTu_Body", "身体（红色，奶白胸口）",
              [mat_fur_patch("TuTu_Red_With_Chest", "#b8452f", "#f3ead6", "oval", oval=(0, 0.2, 0.13, 0.16), front_y=-0.05)],
              (0.18, 0.17, 0.2), (0, 0, 0.22))
    part_blob(root, C, "TuTu_Head", "头", [M["Red"]], (0.17, 0.155, 0.15), (0, -0.01, 0.45))
    part_blob(root, C, "TuTu_FaceDisc", "奶白色脸盘", [M["Cream"]], (0.14, 0.05, 0.11), (0, -0.12, 0.44))
    for s, sn in ((-1, "L"), (1, "R")):
        bm = bmesh.new()
        bm_torus(bm, 0.06, 0.013, loc=(s * 0.06, -0.165, 0.455), rot=(math.pi / 2, 0, 0), seg=16, rseg=6)
        new_obj(f"TuTu_EyeRing_{sn}", bm, C, [M["Ring"]], smooth_shade=True, parent=root, props=dict(cn="眼睛周围的红圈"))
        part_blob(root, C, f"TuTu_Eye_{sn}", "眼白", [M["Eye_White"]], (0.045, 0.025, 0.05), (s * 0.06, -0.165, 0.455), subsurf=1)
        part_blob(root, C, f"TuTu_Iris_{sn}", "绿眼珠", [M["Iris"]], (0.025, 0.012, 0.028), (s * 0.06, -0.19, 0.455), subsurf=1)
        part_blob(root, C, f"TuTu_Wing_{sn}", "翅膀", [M["Red"]], (0.04, 0.12, 0.16), (s * 0.18, 0.02, 0.24), rot=(0, s * 0.2, 0))
        part_blob(root, C, f"TuTu_Foot_{sn}", "黄色爪子", [M["Beak"]], (0.04, 0.05, 0.02), (s * 0.06, -0.04, 0.02), subsurf=1)
    part_blob(root, C, "TuTu_Beak", "黄嘴", [M["Beak"]], (0.025, 0.03, 0.035), (0, -0.19, 0.41), subsurf=1)
    return root


def luobotou(C, pos, rot):
    root = empty("LuoBoTou_Root", C, (pos[0], pos[1], ground(*pos)), (0, 0, rot), size=0.3,
                 props=dict(cn="萝卜头（地鼠）", status="observed", note="U2；高 0.65 m（估算）"))
    M = char_mats("LuoBoTou", dict(Brown="#94653a", Cream="#efdcb4", Nose="#d9868a", **EYE))
    part_blob(root, C, "LuoBoTou_Body", "身体（棕色，奶白肚皮）",
              [mat_fur_patch("LuoBoTou_Brown_With_Belly", "#94653a", "#efdcb4", "oval", oval=(0, 0.24, 0.13, 0.22), front_y=-0.04)],
              (0.17, 0.15, 0.23), (0, 0, 0.25))
    part_blob(root, C, "LuoBoTou_Head", "宽脸（大片奶白色）", [M["Brown"], M["Cream"]], (0.17, 0.15, 0.13), (0, -0.02, 0.53),
              region=lambda c: 1 if c.y < 0.0 and c.z < 0.55 - abs(c.x) * 0.4 else 0)
    part_blob(root, C, "LuoBoTou_Nose", "粉鼻子", [M["Nose"]], (0.035, 0.025, 0.025), (0, -0.17, 0.53), subsurf=1)
    part_blob(root, C, "LuoBoTou_Teeth", "大门牙", [M["Teeth"]], (0.03, 0.01, 0.035), (0, -0.155, 0.45), subsurf=0)
    eyes_pair(root, C, "LuoBoTou", M, 0.055, -0.12, 0.58, 0.03)
    for s, sn in ((-1, "L"), (1, "R")):
        part_blob(root, C, f"LuoBoTou_Ear_{sn}", "耳朵", [M["Brown"]], (0.03, 0.02, 0.03), (s * 0.13, 0, 0.64), subsurf=1)
        # 双手抱胸（U2）
        part_limb(root, C, f"LuoBoTou_Arm_{sn}", "抱胸的手臂", [M["Brown"]], (s * 0.15, -0.02, 0.38), (-s * 0.06, -0.15, 0.32), 0.04, 0.035)
        part_blob(root, C, f"LuoBoTou_Foot_{sn}", "脚", [M["Cream"]], (0.05, 0.07, 0.025), (s * 0.08, -0.05, 0.025), subsurf=1)
    return root


def bengbeng(C, pos, rot):
    root = empty("BengBeng_Root", C, (pos[0], pos[1], ground(*pos)), (0, 0, rot), size=0.3,
                 props=dict(cn="蹦蹦（松鼠）", status="observed", note="U2；高 0.5 m（估算）"))
    M = char_mats("BengBeng", dict(Orange="#c8642c", Cream="#f2d892", Top="#9a3f1f", TailBrown="#6c4630", Iris="#7a8a2a", **EYE))
    part_blob(root, C, "BengBeng_Body", "身体（橙色，奶黄肚皮）",
              [mat_fur_patch("BengBeng_Orange_With_Belly", "#c8642c", "#f2d892", "oval", oval=(0, 0.17, 0.075, 0.14), front_y=-0.02)],
              (0.1, 0.09, 0.15), (0, 0, 0.17))
    part_blob(root, C, "BengBeng_Head", "头", [M["Orange"], M["Cream"], M["Top"]], (0.11, 0.1, 0.1), (0, -0.01, 0.38),
              region=lambda c: 2 if c.z > 0.5 else (1 if c.y < -0.1 and c.z < 0.35 else 0))
    part_blob(root, C, "BengBeng_Snout", "口鼻", [M["Cream"]], (0.06, 0.05, 0.045), (0, -0.09, 0.35), subsurf=1)
    part_blob(root, C, "BengBeng_Teeth", "大门牙", [M["Teeth"]], (0.025, 0.008, 0.03), (0, -0.13, 0.31), subsurf=0)
    eyes_pair(root, C, "BengBeng", M, 0.045, -0.08, 0.42, 0.035, iris=M["Iris"])
    for s, sn in ((-1, "L"), (1, "R")):
        part_blob(root, C, f"BengBeng_Ear_{sn}", "棕色耳朵", [M["Top"]], (0.025, 0.015, 0.045), (s * 0.07, 0, 0.48), rot=(0, s * 0.35, 0), subsurf=1)
        part_limb(root, C, f"BengBeng_Arm_{sn}", "手臂", [M["Orange"]], (s * 0.08, -0.03, 0.25), (s * 0.11, -0.07, 0.15), 0.02, 0.016)
        part_blob(root, C, f"BengBeng_Foot_{sn}", "脚", [M["Orange"]], (0.03, 0.05, 0.02), (s * 0.05, -0.03, 0.02), subsurf=1)
    # 大尾巴：一串球，棕色夹奶白色条纹
    for i in range(8):
        t = i / 7
        part_blob(root, C, f"BengBeng_Tail_{i}", "棕色条纹大尾巴", [M["Cream"] if i % 3 == 1 else M["TailBrown"]],
                  (0.08 + t * 0.03, 0.08 + t * 0.03, 0.08), (0, 0.12 + math.sin(t * 1.6) * 0.18 - t * t * 0.1, 0.12 + math.sin(t * 2.7) * 0.4),
                  seg=12, rings=8, subsurf=1)
    return root


def build_characters():
    CH = COLL
    m = MEADOW
    bear("XiongDa", "熊大", CH["Characters_XiongDa"], (m[0] - 1.6, m[1] + 2.0), math.radians(10),
         fur="#9b4f2e", fur_dark="#7c3a20", bib="#efdcc2", belly=None, muzzle="#f1e2cf", nose="#d4424a")
    bear("XiongEr", "熊二", CH["Characters_XiongEr"], (m[0] + 1.6, m[1] + 1.6), math.radians(-12),
         fur="#d6a356", fur_dark="#b9853c", bib=None, belly="#ecca8c", muzzle="#f2ddb0", nose="#5e6683", plump=1.15)
    guangtouqiang(CH["Characters_GuangtouQiang"], (HOUSE["x"] + 1.8, HOUSE["y"] + 5.4), math.radians(160))
    bx, by = lake_point(math.radians(-62), 1.33)
    tutu(CH["Characters_TuTu"], (bx - 0.75, by), math.radians(-12))
    luobotou(CH["Characters_LuoBoTou"], (bx, by + 0.15), math.radians(0))
    bengbeng(CH["Characters_BengBeng"], (bx + 0.75, by), math.radians(14))
    # 螃蟹（U1 沙滩）
    shell = mat("Crab_Shell", "#7d8c7a", rough=0.6)
    rnd = random.Random(23)
    for k in range(9):
        a = math.radians(rnd.uniform(-110, -15))
        x, y = lake_point(a, rnd.uniform(1.06, 1.3))
        bm = bmesh.new()
        bm_sphere(bm, (0.16, 0.12, 0.05), loc=(0, 0, 0.08), seg=12, rings=8)
        for s in (-1, 1):
            for j in range(3):
                bm_cube(bm, (0.16, 0.015, 0.015), loc=(s * 0.18, -0.06 + j * 0.06, 0.04), rot=(0, s * 0.4, 0))
            bm_sphere(bm, (0.04, 0.05, 0.03), loc=(s * 0.12, -0.15, 0.08), seg=8, rings=6)
        ob = new_obj(f"Prop_Crab_{k}", bm, COLL["Props"], [shell], smooth_shade=True, props=dict(cn="沙滩上的螃蟹", status="observed", note="U1"))
        ob.location = (x, y, ground(x, y))
        ob.rotation_euler = (0, 0, rnd.uniform(0, 6.3))


# ------------------------------------------------------------------------------------------------
# 阶段 6：灯光、世界、相机


def look_at(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def build_lights_cameras():
    LC = COLL["Lights_and_Cameras"]
    sun = bpy.data.lights.new("Sun_Main", "SUN")
    sun.energy = 3.6
    sun.angle = math.radians(2.5)
    sun.color = (1.0, 0.94, 0.84)
    so = bpy.data.objects.new("Sun_Main", sun)
    LC.objects.link(so)
    so.rotation_euler = (math.radians(48), 0, math.radians(35))
    # 世界：天空渐变 + 环境光
    w = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = w
    w.name = "World_Sky_Gradient"
    try:
        w.use_nodes = True
    except Exception:
        pass
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    cr = nt.nodes.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].position = 0.0
    cr.color_ramp.elements[0].color = srgb("#dcebf2")
    cr.color_ramp.elements[1].position = 0.45
    cr.color_ramp.elements[1].color = srgb("#5fa6dc")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], cr.inputs["Fac"])
    nt.links.new(cr.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 1.0
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    # Generated 坐标的 Z 从 0（下）到 1（上）；把渐变中心放在地平线
    mp = nt.nodes.new("ShaderNodeMapRange")
    mp.inputs["From Min"].default_value = 0.45
    mp.inputs["From Max"].default_value = 1.0
    nt.links.new(sep.outputs["Z"], mp.inputs["Value"])
    nt.links.new(mp.outputs["Result"], cr.inputs["Fac"])

    def cam(name, cn, loc, target, lens):
        cd = bpy.data.cameras.new(name)
        cd.lens = lens
        cd.clip_end = 2000
        co = bpy.data.objects.new(name, cd)
        LC.objects.link(co)
        co.location = loc
        look_at(co, target)
        co["name_cn"] = cn
        return co
    ov = cam("Cam_Map_Overview", "地图总览", (34, -88, 118), (-6, -2, 0), 28)
    hx, hy = HOUSE["x"], HOUSE["y"]
    gz = ground(hx, hy)
    cam("Cam_House_Interior", "木屋室内（看炕、冰箱、灶台）", (hx + 3.6, hy + 2.5, gz + FOUND + 2.1),
        (hx - 1.8, hy - 2.4, gz + FOUND + 0.7), 16)
    cam("Cam_House_Exterior", "木屋正面（参照 U3）", (hx + 3.0, hy + 15.0, gz + 2.4), (hx, hy, gz + 2.0), 28)
    lx, ly = lake_point(math.radians(-55), 1.35)
    cx, cy = lake_point(CLIFF["fall"], 1.1)
    cam("Cam_Lake_Beach", "湖边沙滩看石崖瀑布（参照 U1）", (lx, ly, ground(lx, ly) + 2.2), (cx, cy, 5.0), 26)
    m = MEADOW
    cam("Cam_Characters_Meadow", "空地上的熊大熊二", (m[0] + 0.5, m[1] - 8.5, ground(m[0], m[1]) + 1.6),
        (m[0], m[1] + 1.8, ground(m[0], m[1]) + 1.1), 35)
    bx, by = lake_point(math.radians(-62), 1.33)
    cam("Cam_TuTu_LuoBoTou_BengBeng", "涂涂、萝卜头、蹦蹦（参照 U2）", (bx + 0.4, by - 3.2, ground(bx, by) + 0.8),
        (bx, by, ground(bx, by) + 0.35), 40)
    cam("Cam_Pickup_Yard", "院子和皮卡", (hx + 16, hy + 10, gz + 3.5), (hx + 6, hy + 8, gz + 1.0), 28)
    bpy.context.scene.camera = ov


# ------------------------------------------------------------------------------------------------
# 参考说明、检查、保存、渲染


def write_reference_text():
    here = _default_dir()
    p = os.path.join(here, "REFERENCE_NOTES.md")
    body = open(p, encoding="utf-8").read() if os.path.isfile(p) else "见 REFERENCE_NOTES.md"
    t = bpy.data.texts.new("Reference_Notes.md")
    t.write(body)
    e = empty("Reference_Notes_README", COLL["Reference_Notes"], (0, -70, 2), size=3)
    e["说明"] = "参考清单在文本编辑器的 Reference_Notes.md；推测模型都在 Reference_Notes/Inferred_Models 集合里，带 ref_status=inferred。"
    e["scale"] = "1 BU = 1 m；比例基准：熊大身高 2.0 m"


def quality_checks():
    report = []
    # 悬空检查：角色、车辆、道具相对地面
    for c_name in ("Characters", "Vehicles", "Props"):
        for ob in COLL[c_name].all_objects:
            if ob.type != "EMPTY" or not ob.name.endswith("_Root"):
                continue
            gz = ground(ob.location.x, ob.location.y)
            if abs(ob.location.z - gz) > 0.3:
                report.append(f"可能悬空/埋地: {ob.name} dz={ob.location.z - gz:.2f}")
    for ob in COLL["Props"].objects:
        if ob.type == "MESH" and ob.parent is None and not ob.name.startswith("Prop_Beehive"):
            gz = ground(ob.location.x, ob.location.y)
            if ob.location.z - gz > 0.6:
                report.append(f"可能悬空: {ob.name} dz={ob.location.z - gz:.2f}")
    # 空集合
    for c in bpy.data.collections:
        if not c.all_objects:
            report.append(f"空集合: {c.name}")
    # 黑色材质
    for m in bpy.data.materials:
        r, g, b, _ = m.diffuse_color
        if max(r, g, b) < 0.003 and m.name not in ("Shadow_Opening",):
            report.append(f"近黑色材质: {m.name}")
    # 地图范围
    for ob in bpy.data.objects:
        if ob.parent is None and ob.type in ("MESH", "EMPTY") and not ob.name.startswith(("Terrain_", "Proto_")):
            if abs(ob.location.x) > TERRAIN[0] / 2 or abs(ob.location.y) > TERRAIN[1] / 2:
                report.append(f"超出地图: {ob.name}")
    return report


def finalize_and_save():
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    sc.unit_settings.length_unit = "METERS"
    sc.render.engine = "CYCLES"
    try:
        sc.cycles.device = "CPU"
        sc.cycles.samples = SAMPLES
        sc.cycles.use_denoising = True
        sc.cycles.max_bounces = 6
    except Exception:
        pass
    sc.render.resolution_x, sc.render.resolution_y = RES
    sc.render.resolution_percentage = 100
    try:
        sc.view_settings.look = "None"
    except Exception:
        pass
    COLL["Prototypes_Hidden"].hide_render = True
    COLL["Prototypes_Hidden"].hide_viewport = True
    os.makedirs(os.path.dirname(os.path.abspath(OUT_BLEND)), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(OUT_BLEND), compress=True)
    print("SAVED", OUT_BLEND)


def render(path, camera_name):
    sc = bpy.context.scene
    sc.camera = bpy.data.objects[camera_name]
    sc.render.filepath = os.path.abspath(path)
    bpy.ops.render.render(write_still=True)
    print("RENDERED", path)
    sc.camera = bpy.data.objects["Cam_Map_Overview"]


def main():
    import time
    t0 = time.time()

    def step(label, fn, *a):
        t = time.time()
        r = fn(*a)
        print(f"[{time.time() - t0:6.1f}s] {label} ({time.time() - t:.1f}s)", flush=True)
        return r
    step("reset", reset_scene)
    step("collections", setup_collections)
    step("terrain", build_terrain)
    step("lake and rocks", build_lake_and_rocks)
    n = step("forest", build_forest)
    print("  trees:", n, flush=True)
    step("house", build_house)
    step("bears home", build_bears_home)
    step("pickup", build_pickup)
    step("characters", build_characters)
    step("lights and cameras", build_lights_cameras)
    step("reference notes", write_reference_text)
    issues = step("quality checks", quality_checks)
    print("QA issues:", len(issues), flush=True)
    for s in issues[:80]:
        print("  -", s, flush=True)
    step("save", finalize_and_save)
    if RENDER_PATH:
        step("render overview", render, RENDER_PATH, "Cam_Map_Overview")
    if RENDER_INTERIOR:
        step("render interior", render, RENDER_INTERIOR, "Cam_House_Interior")


if __name__ == "__main__":
    main()
