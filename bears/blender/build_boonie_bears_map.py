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
    for n in ("GQ_Room_Kitchen_Dining", "GQ_Room_Bedroom", "GQ_Room_Bathroom"):
        coll(n, COLL["GuangtouQiang_House_Interior"])
    coll("GuangtouQiang_Warehouse")
    coll("WH_Roof_Removable", COLL["GuangtouQiang_Warehouse"])
    coll("WH_Interior", COLL["GuangtouQiang_Warehouse"])
    coll("Bears_TreeHome", COLL["Forest_Trees"])
    coll("MonkeyCave")
    coll("SquirrelNest")
    for n in ("Lake_Water", "Lake_Bottom", "Lake_Rocks", "Lake_Weeds", "Lake_Crab", "Lake_Shore"):
        coll(n, COLL["River_and_Rocks"])
    coll("LW_Surface", COLL["Lake_Water"])
    coll("LW_Volume", COLL["Lake_Water"])
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


def mat_noise(name, c1, c2, scale=6.0, rough=0.85, bump=0.15, detail=4.0, ramp=(0.35, 0.65), stretch=None):
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
    if stretch:
        mp = nodes.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = stretch
        links.new(tc.outputs["Object"], mp.inputs["Vector"])
        links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    else:
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


def mat_vertex_color(name, attr="Col", rough=0.95, var_scale=0.6, bump=0.25, caustics=False):
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
    out_col = mix.outputs["Vector"]
    if caustics:  # 湖底光斑（假焦散）：沃罗诺伊边线提亮
        vo = nodes.new("ShaderNodeTexVoronoi")
        vo.feature = "DISTANCE_TO_EDGE"
        vo.inputs["Scale"].default_value = 1.3
        links.new(tc.outputs["Object"], vo.inputs["Vector"])
        cr = nodes.new("ShaderNodeMapRange")
        cr.inputs["From Min"].default_value = 0.0
        cr.inputs["From Max"].default_value = 0.08
        cr.inputs["To Min"].default_value = 1.28
        cr.inputs["To Max"].default_value = 1.0
        links.new(vo.outputs["Distance"], cr.inputs["Value"])
        sc2 = nodes.new("ShaderNodeVectorMath")
        sc2.operation = "SCALE"
        links.new(out_col, sc2.inputs[0])
        links.new(cr.outputs["Result"], sc2.inputs["Scale"])
        out_col = sc2.outputs["Vector"]
    links.new(out_col, b.inputs["Base Color"])
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
LOGYARD = (60.0, -25.0, 6.0)  # 院子栅栏外东侧
BEARHOME = dict(x=20.0, y=18.0, rot=math.radians(-140))  # 树洞门朝西南（空地方向）
HONEYTREE = (29.0, 28.0)
MONKEYCAVE = dict(x=-14.0, y=44.0, rot=0.38)  # 推测：北面山坡；洞口朝东南的空地方向
SQUIRRELTREE = dict(x=4.0, y=28.0, rot=0.3)   # 推测

PATHS = [
    dict(name="Path_House_Meadow", w=2.0, pts=[(34.0, -20.4), (39.6, -18.4), (41.8, -15.0), (38, -10.5), (26, -8.5), (16, -7.0), (6, -6)]),
    dict(name="Path_Meadow_BearsHome", w=1.8, pts=[(6, -6), (9, 3), (14, 10), (17.5, 14.5)]),
    dict(name="Path_BearsHome_HoneyTree", w=1.3, pts=[(21, 20), (25, 24), (28, 27)]),
    dict(name="Path_Meadow_LakeBeach", w=1.8, pts=[(6, -6), (-6, -14), (-18, -24), (-31, -32)]),
    dict(name="Path_Meadow_MonkeyCave", w=1.4, pts=[(8, 2), (4, 14), (-4, 28), (-10.3, 34.6)]),
    dict(name="Path_To_SquirrelTree", w=1.0, pts=[(4, 14), (4.5, 20), (4.2, 25.6)]),
    dict(name="Path_House_Warehouse", w=1.5, pts=[(34.0, -20.6), (40.5, -23.0), (41.6, -32.0), (37.0, -37.5)]),
    dict(name="Road_House_East", w=3.6, pts=[(46.8, -14.5), (52, -15.0), (64, -13), (82, -11), (125, -9)]),
]
CLEARINGS = [(MEADOW[0], MEADOW[1], MEADOW[2]), (YARD[0], YARD[1], YARD[2]), (LOGYARD[0], LOGYARD[1], LOGYARD[2]),
             (BEARHOME["x"], BEARHOME["y"], 7.5), (HONEYTREE[0], HONEYTREE[1], 4.5),
             (36.0, -43.0, 9.0), (55.0, -15.0, 6.0),  # 屋后仓库、院外皮卡
             (MONKEYCAVE["x"], MONKEYCAVE["y"], 10.0), (SQUIRRELTREE["x"], SQUIRRELTREE["y"], 5.0)]


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
LAKE_DEPTH = dict(shelf=1.4, basin=6.5, cliff_extra=3.0, rock_floor=8.8)  # 推测：按熊大身高 2 m 和 L1 剧照里岩石塔高度估算


def lake_rock_frame():
    """湖底岩石区的局部坐标：原点 R 在湖心往石崖方向 5 m；f 指向石崖（从入水的沙滩看过去的方向），r 是 f 的右手边。
    L1 剧照（爱奇艺“强哥被螃蟹追”）的构图：中间巨大的岩石塔，左后方层叠的石板岩，右后方带孔洞的岩石。"""
    ux, uy = math.cos(CLIFF["fall"]) * LAKE["rx"], math.sin(CLIFF["fall"]) * LAKE["ry"]
    n = math.hypot(ux, uy)
    f = Vector((ux / n, uy / n, 0.0))
    r = Vector((f.y, -f.x, 0.0))
    R = Vector((LAKE["x"], LAKE["y"], 0.0)) + f * 5.0
    return R, f, r


def lake_bed(x, y, e=None, a=None):
    """湖底高度（推测，等待《湖底历险记》截图核对）。
    东南沙滩一侧是缓坡浅滩（约 1.4 m），往里有一道陡坎，湖心盆地约 5 m，靠西北石崖一侧最深约 7.5 m。"""
    e = lake_e(x, y) if e is None else e
    a = lake_angle(x, y) if a is None else a
    c = max(0.0, math.cos(a - CLIFF["fall"])) ** 2  # 1 = 朝石崖方向，0 = 朝沙滩方向
    c = lerp(0.35, c, smooth(0.0, 0.6, e))  # 湖心附近方向没有意义，平滑过渡，避免出现台阶
    D = LAKE_DEPTH
    r_out = lerp(0.8, 0.96, c)
    r_in = r_out - lerp(0.32, 0.14, c)
    d = D["shelf"] * (1 - smooth(0.8, 1.0, e))
    d += (D["basin"] + D["cliff_extra"] * c - D["shelf"]) * (1 - smooth(r_in, r_out, e))
    d += 0.3 * fbm(x * 0.07, y * 0.07, 3, 13.0) * (1 - smooth(0.6, 0.9, e))
    # 岩石区周围是平缓的细沙地（L1 剧照）
    R, _, _ = lake_rock_frame()
    k = 1 - smooth(7.0, 12.0, math.hypot(x - R.x, y - R.y))
    d = lerp(d, D["rock_floor"] + 0.15 * fbm(x * 0.2, y * 0.2, 2, 5.0), k)
    return LAKE["level"] - 0.3 - d


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
    bed = lake_bed(x, y, e, a)
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
            le = lake_e(x, y)
            if le < 1.0:  # 湖底细网格 Lake_Bottom_Terrain 盖在上面；这里稍微压低，避免两层重叠闪烁
                z -= 0.05 + 0.35 * (1 - smooth(0.9, 0.99, le))
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
    # 做成圆环（内半径 100 m）：中间留空，避免盖住比它更深的湖底
    bm = bmesh.new()
    seg = 64
    inner = [bm.verts.new((math.cos(2 * math.pi * k / seg) * 100, math.sin(2 * math.pi * k / seg) * 100, -2.5)) for k in range(seg)]
    outer = [bm.verts.new((math.cos(2 * math.pi * k / seg) * 330, math.sin(2 * math.pi * k / seg) * 330, -2.5)) for k in range(seg)]
    for k in range(seg):
        bm.faces.new((inner[k], outer[k], outer[(k + 1) % seg], inner[(k + 1) % seg]))
    new_obj("Terrain_Distant_Ground", bm, COLL["Terrain"], [mat("Distant_Forest_Floor", "#3f6a35", rough=1.0)],
            props=dict(cn="远处地面", status="inferred"))


# ------------------------------------------------------------------------------------------------
# 阶段 3：湖、沙滩、石崖、瀑布、岩石


def build_lake_bottom():
    """可编辑的湖底细网格（0.4 m 网格），高度来自 lake_bed() 加细小起伏；颜色按水深从浅滩沙色过渡到深处的淤泥色。
    整个湖底形状为推测：第 30 集《湖底历险记》的画面没能读取（见 LAKE_AUDIT.md）。"""
    LB = COLL["Lake_Bottom"]
    step = 0.4
    x0, x1 = LAKE["x"] - LAKE["rx"], LAKE["x"] + LAKE["rx"]
    y0, y1 = LAKE["y"] - LAKE["ry"], LAKE["y"] + LAKE["ry"]
    nx, ny = int((x1 - x0) / step) + 1, int((y1 - y0) / step) + 1
    bm = bmesh.new()
    col = bm.loops.layers.color.new("Col")
    grid = {}
    C = {k: Vector(srgb(v)[:3]) for k, v in dict(sand="#c9a565", mid="#a2a17e", silt="#8fb0a4", dark="#82a69a", algae="#5d7e4c").items()}
    vcol = {}
    for j in range(ny):
        for i in range(nx):
            x, y = x0 + i * step, y0 + j * step
            e = lake_e(x, y)
            if e > 1.0:
                continue
            k = 1 - smooth(0.85, 0.99, e)
            z = ground(x, y) + k * (0.12 * noise.noise(Vector((x * 0.6, y * 0.6, 3.1))) + 0.04 * noise.noise(Vector((x * 2.5, y * 2.5, 7.7))))
            grid[(i, j)] = bm.verts.new((x, y, z))
            depth = LAKE["level"] - z
            c = C["sand"].lerp(C["mid"], smooth(0.8, 2.0, depth)).lerp(C["silt"], smooth(2.5, 5.0, depth)).lerp(C["dark"], smooth(5.5, 7.5, depth))
            c = c.lerp(C["algae"], 0.35 * smooth(0.2, 0.6, fbm(x * 0.15, y * 0.15, 2, 4.0)) * smooth(1.0, 2.5, depth))
            vcol[(i, j)] = c
    for (i, j), v in grid.items():
        q = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
        if all(k in grid for k in q):
            f = bm.faces.new([grid[k] for k in q])
            for loop, k in zip(f.loops, q):
                c = vcol[k]
                loop[col] = (c.x, c.y, c.z, 1.0)
    ob = new_obj("Lake_Bottom_Terrain", bm, LB, [mat_vertex_color("Lake_Bed_Silt_VertexColor", rough=0.95, bump=0.3, caustics=True)], smooth_shade=True,
                 props=dict(cn="湖底地形（浅滩、陡坎、湖心盆地）", status="inferred",
                            note="形状与深度为推测：浅滩约 1.4 m，湖心约 5 m，石崖下最深约 7.5 m；等待第 30 集截图核对"))
    ob["max_depth_m"] = round(LAKE["level"] - min(v.co.z for v in ob.data.vertices), 2)
    # 入水点（推测）：从空地来的小路到达东南沙滩的位置
    ex, ey = lake_point(math.radians(-50), 1.0)
    empty("Lake_Entry_Point_Inferred", COLL["Lake_Shore"], (ex, ey, ground(ex, ey)), size=1.2,
          props=dict(cn="角色入水点（推测）", status="inferred", note="剧中入水地点没有画面；暂放在小路到达的沙滩"))


def mat_lake_rock(name, base1, base2, algae="#4fae4a", speck="#d9efe8", algae_amt=0.5, speck_amt=1.0):
    """湖底岩石（L1）：蓝绿色底色、成片的绿色藻斑、白色小点。"""
    if name in MATS:
        return MATS[name]
    m = _new_mat(name)
    nodes, links = _nodes(m)
    b = nodes.get("Principled BSDF")
    tc = nodes.new("ShaderNodeTexCoord")
    n1 = nodes.new("ShaderNodeTexNoise")
    n1.inputs["Scale"].default_value = 1.6
    n1.inputs["Detail"].default_value = 6.0
    links.new(tc.outputs["Object"], n1.inputs["Vector"])
    r1 = nodes.new("ShaderNodeValToRGB")
    r1.color_ramp.elements[0].color = srgb(base1)
    r1.color_ramp.elements[1].color = srgb(base2)
    links.new(n1.outputs["Fac"], r1.inputs["Fac"])
    n2 = nodes.new("ShaderNodeTexNoise")
    n2.inputs["Scale"].default_value = 1.3
    n2.inputs["Detail"].default_value = 4.0
    links.new(tc.outputs["Object"], n2.inputs["Vector"])
    r2 = nodes.new("ShaderNodeValToRGB")
    r2.color_ramp.elements[0].position = 0.62 - 0.08 * algae_amt
    r2.color_ramp.elements[1].position = 0.66 - 0.08 * algae_amt
    links.new(n2.outputs["Fac"], r2.inputs["Fac"])
    mx1 = nodes.new("ShaderNodeMix")
    mx1.data_type = "RGBA"
    mx1.inputs["B"].default_value = srgb(algae)
    links.new(r2.outputs["Color"], mx1.inputs["Factor"])
    links.new(r1.outputs["Color"], mx1.inputs["A"])
    vo = nodes.new("ShaderNodeTexVoronoi")
    vo.inputs["Scale"].default_value = 16.0
    links.new(tc.outputs["Object"], vo.inputs["Vector"])
    r3 = nodes.new("ShaderNodeValToRGB")
    r3.color_ramp.elements[0].position = 0.06
    r3.color_ramp.elements[1].position = 0.1
    r3.color_ramp.elements[0].color = (speck_amt, speck_amt, speck_amt, 1)
    r3.color_ramp.elements[1].color = (0, 0, 0, 1)
    links.new(vo.outputs["Distance"], r3.inputs["Fac"])
    mx2 = nodes.new("ShaderNodeMix")
    mx2.data_type = "RGBA"
    mx2.inputs["B"].default_value = srgb(speck)
    links.new(r3.outputs["Color"], mx2.inputs["Factor"])
    links.new(mx1.outputs["Result"], mx2.inputs["A"])
    links.new(mx2.outputs["Result"], b.inputs["Base Color"])
    bp = nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.45
    links.new(n1.outputs["Fac"], bp.inputs["Height"])
    links.new(bp.outputs["Normal"], b.inputs["Normal"])
    _set(b, "Roughness", 0.8)
    m.diffuse_color = srgb(base2)
    MATS[name] = m
    return m


def _roughen(bm, verts, amp, freq, seed):
    for v in verts:
        p = v.co * freq + Vector((seed, seed * 0.7, -seed))
        v.co += Vector((noise.noise(p), noise.noise(p + Vector((3.1, 0, 0))), noise.noise(p + Vector((0, 5.3, 0))))) * amp


def build_lake_rocks():
    """湖底岩石（推测位置，形状依据 L1 剧照）：中间巨大的蓝绿色岩石塔（由一团团圆钝的岩块叠成，上窄下宽）、
    左后方层叠的石板岩、右后方带孔洞和拱洞的岩石、周围的小圆石。每块大岩石是独立网格，便于单独修改。"""
    LR = COLL["Lake_Rocks"]
    R, f, r = lake_rock_frame()
    up = Vector((0, 0, 1))
    rnd = random.Random(77)

    def at(a, b):  # 局部 (沿 r, 沿 f) → 世界坐标和该处湖底高度
        p = R + r * a + f * b
        return p, ground(p.x, p.y)

    def blobs(name, cn, mats, items, note, center, rough=0.32, subdiv=3, extra_amp=0.12):
        bm = bmesh.new()
        for (rad, (a, b, z), sc, mi) in items:
            p = R + r * a + f * b - center
            p.z = z
            ret = bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
            seed = rnd.uniform(0, 50)
            for v in ret["verts"]:
                k = 1.0 + rough * noise.noise(v.co * 1.4 + Vector((seed, seed * 0.3, -seed)))
                k += 0.08 * noise.noise(v.co * 4.0 + Vector((-seed, seed, 0)))
                v.co = Vector((v.co.x * rad * sc[0] * k, v.co.y * rad * sc[1] * k, v.co.z * rad * sc[2] * k)) + p
            for fc in _faces(ret):
                fc.material_index = mi
        _roughen(bm, bm.verts, extra_amp, 0.6, rnd.uniform(0, 9))
        ob = new_obj(name, bm, LR, mats, smooth_shade=True, props=dict(cn=cn, status="observed", note=note))
        ob.location = center
        ob["position_status"] = "inferred"
        return ob
    teal = mat_lake_rock("Rock_Lake_Teal_Algae", "#2b7782", "#3d95a0")
    teal_dark = mat_lake_rock("Rock_Lake_Teal_Dark", "#1f5866", "#2c6e7a", algae_amt=0.2, speck_amt=0.6)
    blue_grey = mat_lake_rock("Rock_Lake_BlueGrey", "#3c6f80", "#4f8494", algae_amt=0.1, speck_amt=0.4)
    # 1. 岩石塔
    c0, zf = at(0, 0)
    c0.z = zf - 0.4
    tower = [(2.7, (0.0, 0.0, 0.7), (1.15, 1.05, 0.55), 0), (2.35, (0.4, 0.3, 1.9), (1.0, 0.95, 0.6), 0),
             (2.0, (-0.35, -0.2, 3.0), (0.95, 0.9, 0.62), 0), (1.75, (0.25, 0.2, 4.1), (0.95, 0.95, 0.62), 0),
             (1.45, (-0.2, 0.1, 5.1), (0.9, 0.9, 0.66), 0), (1.15, (0.15, -0.1, 6.0), (0.9, 0.85, 0.72), 0),
             (1.3, (1.9, -0.7, 1.2), (1.0, 0.9, 0.85), 0), (1.1, (-2.1, 0.5, 0.9), (1.0, 0.9, 0.8), 0),
             (0.95, (1.3, 0.9, 3.4), (1.0, 0.9, 0.9), 0), (0.85, (-1.4, -0.6, 4.3), (1.0, 0.9, 0.9), 0)]
    blobs("Lake_Rock_Tower_Main", "湖底巨大的蓝绿色岩石塔", [teal], tower,
          "L1：画面中央巨大的蓝绿色岩石，表面有绿色藻斑和白色小点，上窄下宽，高出画面（≥3 个熊身高）；高度约 6.5 m 为估算", c0)
    # 2. 左后方层叠石板岩（两组）
    for g, (a, b, n) in enumerate(((-6.5, 4.5, 5), (-9.5, 1.0, 3))):
        c, zf = at(a, b)
        c.z = zf - 0.3
        items = []
        z = 0.3
        for k in range(n):
            rad = 2.3 - 0.28 * k + rnd.uniform(-0.15, 0.15)
            items.append((rad, (a + rnd.uniform(-0.5, 0.5), b + rnd.uniform(-0.4, 0.4), z), (1.55, 1.0, 0.32), 0))
            z += rad * 0.55
        blobs(f"Lake_Rock_Ledges_Layered_{g + 1}", "左后方层叠的石板岩", [teal_dark], items,
              "L1：画面左后方一层层的扁平岩块", c, rough=0.2, extra_amp=0.08)
    # 3. 右后方带孔洞的岩石：一大块粗糙岩体，用布尔“差集”修改器挖出几个贯通的孔洞（切割体保留在场景里，可移动改孔洞）
    c, zf = at(7.8, 2.6)
    c.z = zf - 0.3
    items = [(2.4, (7.8, 2.6, 1.6), (1.15, 0.85, 0.9), 0), (1.9, (8.6, 3.4, 3.6), (1.0, 0.85, 0.9), 0),
             (1.5, (7.0, 2.2, 4.4), (0.95, 0.9, 0.85), 0), (1.4, (9.6, 2.0, 1.4), (0.9, 1.0, 1.0), 0)]
    ob = blobs("Lake_Rock_Porous_Holes", "右后方带孔洞的岩石", [blue_grey], items,
               "L1：画面右后方有大孔洞的岩石；孔洞的数量和位置为推测（布尔修改器，切割体 Lake_Rock_Porous_Cutter_*）", c, rough=0.28)
    for k, (rad, (a, b, z), rot) in enumerate(((0.95, (7.6, 2.6, 1.8), 0.2), (0.7, (8.8, 3.3, 3.8), -0.5),
                                                (0.6, (6.9, 2.0, 4.3), 0.9), (0.55, (9.7, 1.8, 1.6), 1.3))):
        bm = bmesh.new()
        p = R + r * a + f * b
        bm_ico(bm, 1.0, scale=(rad, 3.5, rad * 1.15), subdiv=2, rough=0.15, seed=k)
        cut = new_obj(f"Lake_Rock_Porous_Cutter_{k + 1}", bm, LR, [], props=dict(cn="孔洞切割体（渲染时隐藏）", status="inferred"))
        cut.location = (p.x, p.y, zf - 0.3 + z)
        cut.rotation_euler = (0, 0, math.atan2(f.y, f.x) - math.pi / 2 + rot)
        cut.hide_render = True
        cut.display_type = "WIRE"
        cut["helper"] = True
        md = ob.modifiers.new(f"Hole_{k + 1}", "BOOLEAN")
        md.operation = "DIFFERENCE"
        md.solver = "EXACT"
        md.use_self = True
        md.object = cut


def build_lake_water_volume():
    """水体（预览版）：湖面以下的椭圆柱体积，青绿色散射和吸收，让水下远处变暗（L1：蓝绿色水体）。最终水下效果在第五步再调。"""
    bm = bmesh.new()
    seg = 64
    zb = LAKE["level"] - 12.0
    top = LAKE["level"] - 0.02
    lo = [bm.verts.new((*lake_point(2 * math.pi * k / seg, 1.0), zb)) for k in range(seg)]
    hi = [bm.verts.new((*lake_point(2 * math.pi * k / seg, 1.0), top)) for k in range(seg)]
    for k in range(seg):
        bm.faces.new((lo[k], lo[(k + 1) % seg], hi[(k + 1) % seg], hi[k]))
    bm.faces.new(lo[::-1])
    bm.faces.new(hi)
    m = _new_mat("Water_Lake_Volume_Teal")
    nodes, links = _nodes(m)
    out = nodes.get("Material Output")
    nodes.remove(nodes.get("Principled BSDF"))
    pv = nodes.new("ShaderNodeVolumePrincipled")
    pv.inputs["Color"].default_value = srgb("#3fa8a8")
    pv.inputs["Density"].default_value = 0.07
    pv.inputs["Absorption Color"].default_value = srgb("#e08070")  # 红光吸收多，水呈青绿色
    pv.inputs["Anisotropy"].default_value = 0.3
    links.new(pv.outputs["Volume"], out.inputs["Volume"])
    m.diffuse_color = srgb("#2f8f96")
    MATS[m.name] = m
    # 水面透下来的柔光（卡通片里湖底很亮，L1）：湖面下方一盏朝下的大面积灯，只照湖里
    R, f, r = lake_rock_frame()
    la = bpy.data.lights.new("Lake_Underwater_Skylight", "AREA")
    la.shape = "ELLIPSE"
    la.size, la.size_y = 2 * LAKE["rx"] * 0.9, 2 * LAKE["ry"] * 0.9
    la.energy = 9000
    la.color = (0.75, 1.0, 0.95)
    lo = bpy.data.objects.new("Lake_Underwater_Skylight", la)
    COLL["LW_Volume"].objects.link(lo)
    lo.location = (LAKE["x"], LAKE["y"], LAKE["level"] - 0.3)
    lo["name_cn"] = "水面透下来的光（预览）"
    new_obj("Lake_Water_Volume", bm, COLL["LW_Volume"], [m], props=dict(cn="湖水体积（预览）", status="observed",
                                                                         note="L1：青绿色水体；浓度和颜色为预览值，第五步再按剧照调"))


def _blade(bm, base, length, width, heading, bend, twist, segs=7, mi=0):
    """一片水草叶：从 base 往上，沿 heading 方向弯曲，越往上越窄，带扭转。真实 3D 几何（不是贴图片）。"""
    base = Vector(base)
    hx, hy = math.cos(heading), math.sin(heading)
    prev = None
    for i in range(segs + 1):
        t = i / segs
        c = base + Vector((hx * bend * t * t * length, hy * bend * t * t * length, length * t * (1 - 0.25 * bend * t)))
        a = heading + math.pi / 2 + twist * t
        w = width * (1 - t) ** 0.6 + 0.004
        d = Vector((math.cos(a), math.sin(a), 0)) * w / 2
        pair = (bm.verts.new(c - d), bm.verts.new(c + d))
        if prev:
            f = bm.faces.new((prev[0], prev[1], pair[1], pair[0]))
            f.material_index = mi
        prev = pair


def build_scatter_gn(name, target, vgroup, protos_coll, density, scale_rng, seed):
    """Geometry Nodes 散布：在 target 网格上按顶点组 vgroup（可在权重绘制模式里手动修改）的密度撒点，
    从 protos_coll 随机挑原型实例化，随机朝向和大小。"""
    ng = bpy.data.node_groups.new(name + "_GN", "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    N, L = ng.nodes, ng.links
    gout = N.new("NodeGroupOutput")
    N.new("NodeGroupInput")
    oi = N.new("GeometryNodeObjectInfo")
    oi.inputs["Object"].default_value = target
    oi.transform_space = "RELATIVE"
    na = N.new("GeometryNodeInputNamedAttribute")
    na.data_type = "FLOAT"
    na.inputs["Name"].default_value = vgroup
    dp = N.new("GeometryNodeDistributePointsOnFaces")  # 随机模式：密度字段 = 顶点组权重 × density
    dp.inputs["Seed"].default_value = seed
    mul = N.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    mul.inputs[1].default_value = density
    L.new(na.outputs["Attribute"], mul.inputs[0])
    L.new(mul.outputs[0], dp.inputs[4])
    L.new(oi.outputs["Geometry"], dp.inputs["Mesh"])
    ci = N.new("GeometryNodeCollectionInfo")
    ci.inputs["Collection"].default_value = protos_coll
    ci.inputs["Separate Children"].default_value = True
    ci.inputs["Reset Children"].default_value = True
    ip = N.new("GeometryNodeInstanceOnPoints")
    ip.inputs["Pick Instance"].default_value = True
    L.new(dp.outputs["Points"], ip.inputs["Points"])
    L.new(ci.outputs["Instances"], ip.inputs["Instance"])
    ri = N.new("FunctionNodeRandomValue")
    ri.data_type = "INT"
    ri.inputs[4].default_value = 0  # 整数的 Min/Max（同名的第一个插口是向量）
    ri.inputs[5].default_value = len(protos_coll.objects) - 1
    ri.inputs["Seed"].default_value = seed + 1
    L.new(ri.outputs[2], ip.inputs["Instance Index"])
    rr = N.new("FunctionNodeRandomValue")
    rr.data_type = "FLOAT_VECTOR"
    rr.inputs["Min"].default_value = (0, 0, 0)
    rr.inputs["Max"].default_value = (0.12, 0.12, 6.283)
    rr.inputs["Seed"].default_value = seed + 2
    L.new(rr.outputs["Value"], ip.inputs["Rotation"])
    rs = N.new("FunctionNodeRandomValue")
    rs.data_type = "FLOAT"
    rs.inputs[2].default_value = scale_rng[0]
    rs.inputs[3].default_value = scale_rng[1]
    rs.inputs["Seed"].default_value = seed + 3
    L.new(rs.outputs[1], ip.inputs["Scale"])
    L.new(ip.outputs["Instances"], gout.inputs["Geometry"])
    me = bpy.data.meshes.new(name)
    ob = bpy.data.objects.new(name, me)
    md = ob.modifiers.new("Scatter", "NODES")
    md.node_group = ng
    return ob


def build_lake_weeds_and_pebbles():
    """湖底水草和小碎石（L1：细长、稀疏的水草，长在岩石附近和画面左侧；蓝灰色小圆石）。
    分布用 Geometry Nodes；密度来自湖底网格上的顶点组 Weed_Density / Pebble_Density，可以在权重绘制模式里手动改。"""
    LW = COLL["Lake_Weeds"]
    PR = coll("Lake_Scatter_Prototypes", COLL["Reference_Notes"])
    bottom = bpy.data.objects["Lake_Bottom_Terrain"]
    R, f, r = lake_rock_frame()
    # 顶点组：水草——岩石区外圈（3–9 m）、岩石区左侧，以及 1.5–3.5 m 深的浅坡带；碎石——岩石区周围
    vw = bottom.vertex_groups.new(name="Weed_Density")
    vp = bottom.vertex_groups.new(name="Pebble_Density")
    for v in bottom.data.vertices:
        p = bottom.matrix_world @ v.co
        d = math.hypot(p.x - R.x, p.y - R.y)
        side = (p - R).dot(r)
        depth = LAKE["level"] - p.z
        w = (smooth(2.8, 4.0, d) * (1 - smooth(8.0, 11.0, d))) * (0.6 + 0.4 * smooth(0.0, -6.0, side))
        w = max(w, 0.35 * smooth(1.2, 1.8, depth) * (1 - smooth(3.0, 3.8, depth)))
        w *= 0.55 + 0.45 * smooth(-0.2, 0.4, noise.noise(Vector((p.x * 0.18, p.y * 0.18, 1.7))))
        if w > 0.01:
            vw.add([v.index], min(1.0, w), "REPLACE")
        pw = smooth(2.5, 3.5, d) * (1 - smooth(9.0, 12.0, d))
        if pw > 0.01:
            vp.add([v.index], pw, "REPLACE")
    weed = mat("Plant_Waterweed_Green", "#3f9a52", rough=0.6)
    weed_lt = mat("Plant_Waterweed_Light", "#68b85a", rough=0.6)
    rnd = random.Random(55)
    protos = []
    for k, (n_bl, L0, L1, wdt, bend) in enumerate(((6, 0.7, 1.4, 0.035, 0.35), (3, 1.4, 2.1, 0.03, 0.25), (12, 0.18, 0.4, 0.03, 0.6),
                                                     (8, 0.35, 0.7, 0.07, 0.5))):
        bm = bmesh.new()
        for i in range(n_bl):
            a = rnd.uniform(0, 6.283)
            _blade(bm, (math.cos(a) * 0.05, math.sin(a) * 0.05, -0.03), rnd.uniform(L0, L1), wdt * rnd.uniform(0.8, 1.2), a,
                   rnd.uniform(0.2, 1.0) * bend, rnd.uniform(-1.5, 1.5), mi=i % 2)
        ob = new_obj(f"Proto_Waterweed_{('LongCluster', 'TallStrands', 'ShortTuft', 'BroadLeaf')[k]}", bm, PR, [weed, weed_lt],
                     smooth_shade=True, recalc=False, props=dict(cn="水草原型", status="observed", note="L1：细长水草"))
        protos.append(ob)
    pk = mat_noise("Pebble_BlueGrey", "#5f8796", "#7b9fac", scale=4)
    for k in range(4):
        bm = bmesh.new()
        bm_ico(bm, 1.0, scale=(1.2, 1.0, 0.6), subdiv=2, rough=0.25, seed=k * 3.3)
        PRp = coll("Lake_Pebble_Prototypes", COLL["Reference_Notes"])
        new_obj(f"Proto_Pebble_{k}", bm, PRp, [pk], smooth_shade=True, props=dict(cn="碎石原型", status="observed", note="L1：蓝灰色圆石"))
    PRp = COLL["Lake_Pebble_Prototypes"]
    for C in (PR, PRp):
        C.hide_render = True
        C.hide_viewport = True
    ob = build_scatter_gn("Lake_Weeds_Scatter", bottom, "Weed_Density", PR, 1.6, (0.7, 1.3), 11)
    LW.objects.link(ob)
    tag(ob, cn="湖底水草（Geometry Nodes 散布）", status="observed",
        note="形状依据 L1；分布为推测，改湖底网格的顶点组 Weed_Density 即可增减")
    ob = build_scatter_gn("Lake_Pebbles_Scatter", bottom, "Pebble_Density", PRp, 0.22, (0.08, 0.24), 21)
    COLL["Lake_Rocks"].objects.link(ob)
    tag(ob, cn="湖底小碎石（Geometry Nodes 散布）", status="observed", note="L1：蓝灰色小圆石；分布为推测，顶点组 Pebble_Density")
    # 悬浮微粒：岩石区附近的水里一些很小的亮点
    bm = bmesh.new()
    for k in range(400):
        p = R + r * rnd.uniform(-14, 14) + f * rnd.uniform(-12, 10)
        zf = ground(p.x, p.y)
        bm_ico(bm, rnd.uniform(0.008, 0.02), loc=(p.x, p.y, rnd.uniform(zf + 0.3, LAKE["level"] - 0.5)), subdiv=0)
    new_obj("Lake_Water_Particles", bm, COLL["LW_Volume"], [mat("Water_Particle_Glint", "#dff6f2", emit="#cff4ee", emit_strength=0.6)],
            props=dict(cn="水中悬浮微粒", status="inferred"))


def build_lake_crab():
    """《湖底历险记》的大螃蟹（形状依据 L1；背面、侧面为推测）。
    卡通造型：米色宽蟹壳，正面一张大嘴和两排白牙，蟹壳下方前面两只灰色圆眼长在眼柄上，橙粉色步足每侧 4 条（向上翘、尖头），一对大蟹钳。
    尺寸按 L1 和熊的比例估算：蟹壳宽约 1.4 m，蟹钳展开约 3.6 m。
    骨骼 Crab_Rig：每个部件是独立物体，挂在对应的骨头上，可以单独摆动蟹钳、步足、眼睛和身体。局部 -Y 为正面。"""
    C = COLL["Lake_Crab"]
    R, f, r = lake_rock_frame()
    pos = R - f * 3.0
    gz = ground(pos.x, pos.y)
    yaw = math.atan2(-f.x, f.y)  # 局部 +Y 朝 f，嘴（局部 -Y）朝 -f，也就是朝着 L1 的镜头
    shell = mat_noise("Crab_Shell_Cream", "#e6cfa2", "#efdcb4", scale=4, bump=0.1)
    under = mat("Crab_Shell_Salmon", "#e49a72", rough=0.5)
    leg_m = mat_noise("Crab_Leg_Salmon", "#e6a183", "#efb498", scale=6, bump=0.05)
    tip_m = mat("Crab_Leg_Tip", "#c98466", rough=0.5)
    mouth_m = mat("Crab_Mouth_Inner", "#a8343a", rough=0.6)
    tongue = mat("Crab_Mouth_Tongue", "#d85a62", rough=0.6)
    teeth = mat("Crab_Teeth_White", "#f6f3ea", rough=0.3)
    eye_m = mat("Crab_Eye_Grey", "#a9a9a6", rough=0.2, metal=0.1)
    pupil = mat("Crab_Eye_Pupil", "#2a2a2a", rough=0.3)
    BZ = 0.62  # 身体中心离地高度

    # ---- 骨骼
    ad = bpy.data.armatures.new("Crab_Rig")
    arm = bpy.data.objects.new("Crab_Rig", ad)
    C.objects.link(arm)
    arm.location = (pos.x, pos.y, gz)
    arm.rotation_euler = (0, 0, yaw)
    arm.show_in_front = True
    tag(arm, cn="大螃蟹骨骼（根）", status="observed", note="L1；动作和关节位置为推测")
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    E = ad.edit_bones

    def bone(name, head, tail, parent=None):
        b = E.new(name)
        b.head, b.tail = head, tail
        if parent:
            b.parent = E[parent]
        return b
    bone("Root", (0, 0, 0), (0, 0.4, 0))
    bone("Body", (0, 0.1, BZ), (0, -0.4, BZ), "Root")
    for s, side in ((-1, "L"), (1, "R")):
        bone(f"Eye_{side}", (s * 0.22, -0.4, BZ - 0.1), (s * 0.26, -0.62, BZ - 0.42), "Body")
        bone(f"Claw_Upper_{side}", (s * 0.6, -0.25, BZ - 0.05), (s * 1.15, -0.5, BZ - 0.2), "Body")
        bone(f"Claw_Lower_{side}", (s * 1.15, -0.5, BZ - 0.2), (s * 1.45, -0.95, BZ - 0.38), f"Claw_Upper_{side}")
        bone(f"Claw_Hand_{side}", (s * 1.45, -0.95, BZ - 0.38), (s * 1.2, -1.55, BZ - 0.42), f"Claw_Lower_{side}")
        bone(f"Claw_Finger_{side}", (s * 1.33, -1.25, BZ - 0.3), (s * 1.08, -1.75, BZ - 0.36), f"Claw_Hand_{side}")
        for k in range(4):
            y = -0.15 + k * 0.2
            knee = (s * (0.95 + 0.1 * k), y + 0.12 * k, BZ + 0.4 - 0.04 * k)  # L1：步足沿身体两侧散开，向外上方翘起
            tip = (s * (1.15 + 0.32 * k), y + 0.3 * k, BZ + 0.95 - 0.16 * k)
            bone(f"Leg{k + 1}_Upper_{side}", (s * 0.62, y, BZ), knee, "Body")
            bone(f"Leg{k + 1}_Lower_{side}", knee, tip, f"Leg{k + 1}_Upper_{side}")
    bpy.ops.object.mode_set(mode="OBJECT")
    arm.select_set(False)

    def part(name, cn, mats, build, bone_name, smooth_shade=True):
        bm = bmesh.new()
        build(bm)
        ob = new_obj(name, bm, C, mats, smooth_shade=smooth_shade, props=dict(cn=cn, status="observed", note="L1"))
        b = ad.bones[bone_name]
        ob.parent = arm
        ob.parent_type = "BONE"
        ob.parent_bone = bone_name
        ob.matrix_parent_inverse = (b.matrix_local @ Matrix.Translation((0, b.length, 0))).inverted()
        return ob

    def body(bm):
        bm_sphere(bm, (0.72, 0.52, 0.24), loc=(0, 0.02, BZ + 0.04), seg=32, rings=16, mi=0,
                  deform=lambda co: Vector((co.x, co.y, co.z * (1.0 if co.z > 0 else 0.6))))
        bm_sphere(bm, (0.66, 0.46, 0.16), loc=(0, 0.04, BZ - 0.1), seg=28, rings=12, mi=1)
        for s in (-1, 1):  # 蟹壳两侧的尖角
            bm_cyl(bm, 0.07, 0.0, 0.22, loc=(s * 0.78, -0.12, BZ + 0.05), rot=(0, s * math.pi / 2, 0), seg=8, mi=0)
        # 大嘴：深红口腔、舌头、上下两排白牙、嘴唇
        bm_sphere(bm, (0.36, 0.1, 0.12), loc=(0, -0.47, BZ + 0.0), seg=24, rings=10, mi=2)
        bm_sphere(bm, (0.2, 0.06, 0.05), loc=(0, -0.5, BZ - 0.06), seg=16, rings=8, mi=3)
        for row, z in ((1, 0.065), (-1, -0.07)):
            for i in range(9):
                x = -0.3 + i * 0.075
                bm_cube(bm, (0.062, 0.04, 0.05), loc=(x, -0.535 - 0.01 * (1 - abs(x) / 0.35), BZ + z), mi=4)
        bm_torus(bm, 0.36, 0.035, loc=(0, -0.5, BZ), rot=(math.pi / 2, 0, 0), seg=28, rseg=6, mi=0, scale=(1.0, 0.36, 1.0))
    part("Crab_Body_Shell_Mouth", "蟹壳、下壳和大嘴", [shell, under, mouth_m, tongue, teeth], body, "Body")
    for s, side in ((-1, "L"), (1, "R")):
        def eye(bm, s=s):
            bm_tube(bm, [(s * 0.22, -0.4, BZ - 0.1), (s * 0.24, -0.52, BZ - 0.26), (s * 0.26, -0.6, BZ - 0.36)], [0.035, 0.03, 0.03], seg=8, mi=0)
            bm_sphere(bm, (0.15, 0.15, 0.15), loc=(s * 0.27, -0.64, BZ - 0.46), seg=20, rings=12, mi=1)
            bm_sphere(bm, (0.05, 0.02, 0.05), loc=(s * 0.27, -0.785, BZ - 0.47), seg=10, rings=6, mi=2)
        part(f"Crab_Eye_{side}", "眼柄和灰色圆眼", [under, eye_m, pupil], eye, f"Eye_{side}")

        def seg(bm, a, b, r0, r1, s=s, mi=0):
            bm_tube(bm, [a, b], [r0, r1], seg=10, mi=mi)
            bm_sphere(bm, (r0 * 1.1, r0 * 1.1, r0 * 1.1), loc=a, seg=10, rings=6, mi=mi)
        part(f"Crab_Claw_Upper_{side}", "蟹钳上段", [leg_m],
             lambda bm, s=s: seg(bm, (s * 0.6, -0.25, BZ - 0.05), (s * 1.15, -0.5, BZ - 0.2), 0.1, 0.12), f"Claw_Upper_{side}")
        part(f"Crab_Claw_Lower_{side}", "蟹钳中段", [leg_m],
             lambda bm, s=s: seg(bm, (s * 1.15, -0.5, BZ - 0.2), (s * 1.45, -0.95, BZ - 0.38), 0.12, 0.15), f"Claw_Lower_{side}")

        def hand(bm, s=s):
            bm_sphere(bm, (0.2, 0.36, 0.17), loc=(s * 1.36, -1.18, BZ - 0.4), rot=(0, 0, s * -0.4), seg=20, rings=12, mi=0)
            bm_tube(bm, [(s * 1.25, -1.45, BZ - 0.45), (s * 1.12, -1.68, BZ - 0.46), (s * 1.0, -1.78, BZ - 0.44)], [0.08, 0.05, 0.015], seg=10, mi=0)
            bm_sphere(bm, (0.03, 0.03, 0.03), loc=(s * 1.0, -1.78, BZ - 0.44), seg=8, rings=4, mi=1)
        part(f"Crab_Claw_Hand_{side}", "蟹钳（固定指）", [leg_m, tip_m], hand, f"Claw_Hand_{side}")
        part(f"Crab_Claw_Finger_{side}", "蟹钳（活动指）", [leg_m, tip_m],
             lambda bm, s=s: (bm_tube(bm, [(s * 1.33, -1.25, BZ - 0.3), (s * 1.22, -1.5, BZ - 0.28), (s * 1.08, -1.72, BZ - 0.33)], [0.07, 0.045, 0.012], seg=10, mi=0),
                              bm_sphere(bm, (0.03, 0.03, 0.03), loc=(s * 1.08, -1.72, BZ - 0.33), seg=8, rings=4, mi=1)), f"Claw_Finger_{side}")
        for k in range(4):
            y = -0.15 + k * 0.2
            knee = (s * (0.95 + 0.1 * k), y + 0.12 * k, BZ + 0.4 - 0.04 * k)  # L1：步足沿身体两侧散开，向外上方翘起
            tip = (s * (1.15 + 0.32 * k), y + 0.3 * k, BZ + 0.95 - 0.16 * k)
            part(f"Crab_Leg{k + 1}_Upper_{side}", f"第 {k + 1} 对步足上段", [leg_m],
                 lambda bm, s=s, y=y, knee=knee: seg(bm, (s * 0.62, y, BZ), knee, 0.06, 0.05), f"Leg{k + 1}_Upper_{side}")
            part(f"Crab_Leg{k + 1}_Lower_{side}", f"第 {k + 1} 对步足下段（尖头）", [leg_m, tip_m],
                 lambda bm, knee=knee, tip=tip: (bm_tube(bm, [knee, Vector(knee).lerp(Vector(tip), 0.7), tip], [0.05, 0.035, 0.004], seg=10, mi=0),
                                                 bm_sphere(bm, (0.055, 0.055, 0.055), loc=knee, seg=10, rings=6, mi=1)), f"Leg{k + 1}_Lower_{side}")


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
    new_obj("Lake_Water_Surface", bm, COLL["LW_Surface"], [mat_water("Water_Lake", "#3dbdb6", "#1f8f94")], recalc=False,
            props=dict(cn="湖面", status="observed", note="U1：大湖；第 30 集小帧、第 41 集 056s/072s：湖水是青绿色；湖的完整轮廓为推测"))
    build_lake_bottom()
    build_lake_rocks()
    build_lake_water_volume()
    build_lake_weeds_and_pebbles()
    build_lake_crab()

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
            z_base = min(LAKE["level"] - 1.0, ground(*lake_point(a, 0.96)) - 0.6)  # 柱体伸到湖底（水下崖壁为推测）
            hgt = CLIFF["height"] * k * (0.85 + 0.25 * layer) * rnd.uniform(0.85, 1.1) + (LAKE["level"] - z_base)
            r = rnd.uniform(1.6, 2.6)
            ret = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=rnd.choice((5, 6, 7)),
                                        radius1=r, radius2=r * rnd.uniform(0.7, 0.9), depth=hgt,
                                        matrix=trs((x, y, z_base + hgt / 2), (rnd.uniform(-0.04, 0.04), rnd.uniform(-0.04, 0.04), rnd.uniform(0, 6.3))))
            for v in ret["verts"]:
                v.co += Vector((noise.noise(v.co * 0.4) * 0.35, noise.noise(v.co * 0.4 + Vector((5, 1, 2))) * 0.35, 0))
            _mi(_faces(ret), rnd.randrange(2))
            # 顶上的碎石帽
            bm_ico(bm, r * 0.9, loc=(x, y, z_base + hgt), scale=(1, 1, 0.45), subdiv=1, rough=0.2, seed=i + layer, mi=rnd.randrange(2))
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
        if k < 3:  # S1E1-3/5/12：长满苔藓的圆石
            for f in bm.faces:
                if f.normal.z > 0.45 + 0.1 * noise.noise(f.calc_center_median() * 2.0):
                    f.material_index = 1
        protos.append(new_obj(f"Proto_Rock_{k}", bm, COLL["Prototypes_Hidden"],
                              [mat_noise("Rock_Grey", "#6f6c69", "#8e8a85", scale=2.5, bump=0.35),
                               mat_noise("Moss_Green", "#4f7d32", "#6a9a3e", scale=6, bump=0.3)]))
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
    """云杉：粗壮略弯的红褐色树干，下部约 1/4 没有枝条（第一季第 1 集《新邻居》里林间能看到高高的光树干），
    树根外露，上面 8–12 层下垂的枝层。"""
    rnd = random.Random(seed)
    bm = bmesh.new()
    pts, rad = [], []
    for i in range(8):
        t = i / 7
        pts.append((math.sin(t * 2.2 + seed) * 0.12 * h / 14, math.cos(t * 1.7) * 0.08 * h / 14 - 0.08, t * h * 0.97))
        rad.append(lerp(0.42, 0.05, t ** 0.8) * h / 14)
    bm_tube(bm, pts, rad, seg=8, mi=0)
    for k in range(5):
        a = 2 * math.pi * k / 5 + rnd.random()
        bm_tube(bm, [(0, 0, 0.6), (math.cos(a) * 0.8, math.sin(a) * 0.8, 0.15), (math.cos(a) * 1.5, math.sin(a) * 1.5, -0.05)],
                [0.22 * h / 14, 0.12, 0.04], seg=6, mi=0)
    tiers = int(h / 1.35)
    for i in range(tiers):
        t = i / max(1, tiers - 1)
        z = lerp(h * 0.26, h * 0.9, t)
        R = lerp(h * 0.22, h * 0.055, t ** 0.9) * rnd.uniform(0.9, 1.08)
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
                   [mat_noise("Bark_Spruce", "#4f2e20", "#80513a", scale=5, bump=0.8, stretch=(3.0, 3.0, 0.35), ramp=(0.4, 0.6)),
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


def leafy_plant_proto(name, seed):
    """S1E1-71/72：地面上的大叶植物（宽叶片，向外弯垂）。"""
    rnd = random.Random(seed)
    bm = bmesh.new()
    for k in range(7):
        a = 2 * math.pi * k / 7 + rnd.uniform(-0.2, 0.2)
        L = rnd.uniform(0.6, 0.9)
        dx, dy = math.cos(a), math.sin(a)
        px, py = -dy, dx
        prev = None
        for s_ in range(7):
            t = s_ / 6
            w = 0.22 * math.sin(t * math.pi) + 0.02
            cx, cy = dx * L * t, dy * L * t
            cz = 0.55 * math.sin(t * math.pi * 0.55) - 0.2 * t * t
            row = (bm.verts.new((cx + px * w, cy + py * w, cz - w * 0.3)), bm.verts.new((cx, cy, cz)),
                   bm.verts.new((cx - px * w, cy - py * w, cz - w * 0.3)))
            if prev:
                bm.faces.new((prev[0], prev[1], row[1], row[0]))
                bm.faces.new((prev[1], prev[2], row[2], row[1]))
            prev = row
    return new_obj(name, bm, COLL["Prototypes_Hidden"], [mat("Plant_BigLeaf", "#3f8a36", rough=0.55)], smooth_shade=True, recalc=False)


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
    ferns.append(leafy_plant_proto("Proto_BigLeaf_Plant", 140))

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
# 阶段 4：光头强的木屋（四季篇改版：红棕色木墙、蓝灰色木板屋顶）和独立仓库。逐项依据见 HOUSE_WAREHOUSE_AUDIT.md。
# 木屋局部坐标：+Y 为正面（北），+X 为东（站在门前看在左手边），原点在主屋中心、四角地面最高点的高度。
# 布局：主屋 = 客厅/厨房/餐厅（西）+ 卧室（东，隔墙 PART_X）；卫生间是西侧单独的一翼（站在门前看在右手边）。

W_HOUSE, D_HOUSE, H_WALL, FOUND = 9.0, 6.0, 3.0, 1.0
WING = dict(x0=-7.0, x1=-4.5, y0=-3.0, y1=1.8, h=2.5, rise=1.4)
ROOF_RISE, ROOF_OV = 2.0, 0.8
PART_X = 1.3
DECK_Y = 4.75
DOOR_X = (-0.9, 0.5)
WIN_FRONT = ((-3.55, -2.25), (2.25, 3.55))
WIN_Z = (0.95, 2.05)
BED_DOOR = (-2.25, -1.35)
BATH_DOOR = (-0.6, 0.3)
ROUND_WIN = (-1.6, 1.75, 0.5)
IN_X, IN_Y = W_HOUSE / 2 - 0.155, D_HOUSE / 2 - 0.155
WAREHOUSE = dict(lx=2.0, ly=-15.0, rot=0.0, W=6.0, D=8.0, H=3.2, rise=2.0, floor=0.45)  # 屋后（R1、H2 院门一侧没有其他建筑）；位置为推测
DOOR_PASSAGES = []  # (名称, 根物体名, 局部 AABB (x0, x1, y0, y1, z0, z1))：质量检查时门洞里不能有家具


def _cut(segs, holes, zc):
    for (x0, x1, z0, z1) in holes:
        if zc < z0 or zc > z1:
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
    return segs


def board_wall(bm, L, H, holes, n_shades, rnd, board=0.3, depth=0.1, z0=0.0, mi_base=0):
    """横木板墙（室内蓝灰色墙板）：逐条木板生成，跳过门窗洞。"""
    y = 0.0
    while y < H - 1e-3:
        bh = min(board, H - y) - 0.02
        yc = y + bh / 2
        for s0, s1 in _cut([(-L / 2, L / 2)], holes, yc):
            if s1 - s0 > 0.03:
                bm_cube(bm, (s1 - s0, depth, bh), loc=((s0 + s1) / 2, rnd.uniform(-0.01, 0.01), z0 + yc),
                        mi=mi_base + rnd.randrange(n_shades))
        y += board


def log_wall(bm, L, H, holes, n_shades, rnd, board=0.27, depth=0.1, z0=0.0, round_frac=0.3):
    """外墙（R1、R2）：高低不一的红棕色横木板夹着圆木，木板略有倾斜。圆木只向墙外（局部 -Y）凸出。"""
    z = 0.0
    while z < H - 0.02:
        bh = min(board * rnd.uniform(0.75, 1.25), H - z)
        zc = z + bh / 2
        for s0, s1 in _cut([(-L / 2, L / 2)], holes, zc):
            if s1 - s0 < 0.04:
                continue
            mi = rnd.randrange(n_shades)
            if rnd.random() < round_frac and bh > 0.2:
                r = bh / 2
                bm_cyl(bm, r, r, s1 - s0, loc=((s0 + s1) / 2, -(r - depth / 2), z0 + zc), rot=(0, math.pi / 2, 0), seg=10, mi=mi)
            else:
                bm_cube(bm, (s1 - s0, depth, bh - 0.025), loc=((s0 + s1) / 2, rnd.uniform(-0.015, 0.015), z0 + zc),
                        rot=(rnd.uniform(-0.04, 0.04), 0, 0), mi=mi)
        z += bh


def gable_boards(bm, half, rise, n_shades, rnd, board=0.27, depth=0.1, z0=0.0, inset=0.0):
    """山墙三角：一层层变短的横木板。"""
    z = 0.0
    while z < rise - 0.05:
        bh = min(board * rnd.uniform(0.8, 1.2), rise - z)
        zc = z + bh / 2
        L = 2 * (half - inset) * (1 - zc / rise)
        if L > 0.08:
            bm_cube(bm, (L, depth, bh - 0.02), loc=(rnd.uniform(-0.03, 0.03), rnd.uniform(-0.01, 0.01), z0 + zc), mi=rnd.randrange(n_shades))
        z += bh


def vplank_wall(bm, L, H, holes, n_shades, rnd, plank=0.24, depth=0.06, z0=0.0, top=None):
    """竖木板墙（仓库，推测）。top(x) 给出山墙顶边。"""
    x = -L / 2
    while x < L / 2 - 0.02:
        w = min(plank * rnd.uniform(0.8, 1.2), L / 2 - x)
        xc = x + w / 2
        zt = H if top is None else top(xc)
        segs = [(0.0, zt)]
        for (h0, h1, a, b) in holes:
            if xc < h0 or xc > h1:
                continue
            nxt = []
            for s0, s1 in segs:
                if b <= s0 or a >= s1:
                    nxt.append((s0, s1))
                    continue
                if a > s0:
                    nxt.append((s0, a))
                if b < s1:
                    nxt.append((b, s1))
            segs = nxt
        for s0, s1 in segs:
            if s1 - s0 > 0.03:
                bm_cube(bm, (w - 0.018, depth, s1 - s0), loc=(xc, rnd.uniform(-0.01, 0.01), z0 + (s0 + s1) / 2),
                        rot=(0, rnd.uniform(-0.01, 0.01), 0), mi=rnd.randrange(n_shades))
        x += w


def surf_box(bm, P, ua, ub, va, vb, thick, nu=3, nv=2, mi=0):
    """沿曲面 P(u, v) 的一块木板（底面贴曲面，向 +Z 加厚）。用于上翘的屋顶木板、坡道。"""
    gb = [[bm.verts.new(P(lerp(ua, ub, i / nu), lerp(va, vb, j / nv))) for j in range(nv + 1)] for i in range(nu + 1)]
    gt = [[bm.verts.new(v.co + Vector((0, 0, thick))) for v in row] for row in gb]
    faces = []

    def q(a, b, c, d):
        f = bm.faces.new((a, b, c, d))
        f.material_index = mi
        faces.append(f)
    for i in range(nu):
        for j in range(nv):
            q(gb[i][j], gb[i][j + 1], gb[i + 1][j + 1], gb[i + 1][j])
            q(gt[i][j], gt[i + 1][j], gt[i + 1][j + 1], gt[i][j + 1])
    for i in range(nu):
        q(gb[i][0], gb[i + 1][0], gt[i + 1][0], gt[i][0])
        q(gb[i][nv], gt[i][nv], gt[i + 1][nv], gb[i + 1][nv])
    for j in range(nv):
        q(gb[0][j], gt[0][j], gt[0][j + 1], gb[0][j + 1])
        q(gb[nu][j], gb[nu][j + 1], gt[nu][j + 1], gt[nu][j])
    return faces


def roof_surface(x0, x1, y_ridge, half, ov, top, rise, lift_hi, lift_lo, curl=0.16):
    """屋顶坡面 S(x, side, u)：u=0 屋脊，u=1 檐口。两端上翘（R2：屋檐两端翘起，左右不对称），檐口外缘再微微上卷。"""
    xc, xh = (x0 + x1) / 2, (x1 - x0) / 2

    def S(x, side, u):
        d = u * (half + ov)
        z = top + rise - d * rise / half
        xm = (x - xc) / xh
        k = lift_hi if xm > 0 else lift_lo
        z += k * (max(0.0, abs(xm) - 0.87) / 0.13) ** 2
        z += curl * (max(0.0, u - 0.82) / 0.18) ** 2 * (0.4 + 0.6 * abs(xm))
        return Vector((x, y_ridge + side * d, z))
    return S


def roof_boards(bm, S, x0, x1, rnd, n_mats, tiers=3, thick=0.05, wmin=0.32, wmax=0.5):
    """一条条顺坡铺的木板，分几层，上层压住下层（R2）。"""
    for side in (-1, 1):
        x = x0
        while x < x1 - 0.05:
            w = min(rnd.uniform(wmin, wmax), x1 - x)
            xa, xb = x + 0.012, x + w - 0.012
            for t in range(tiers):
                ua = 0.0 if t == 0 else t / tiers - 0.05
                ub = 1.0 + rnd.uniform(-0.03, 0.03) if t == tiers - 1 else (t + 1) / tiers + rnd.uniform(0.0, 0.04)
                dz = 0.03 + (tiers - 1 - t) * 0.035 + rnd.uniform(0, 0.02)
                tilt = rnd.uniform(-0.05, 0.05)
                xm = (xa + xb) / 2
                surf_box(bm, lambda u, xx, side=side, dz=dz, tilt=tilt, xm=xm: S(xx, side, u) + Vector((0, 0, dz + (xx - xm) * tilt)),
                         ua, ub, xa, xb, thick, nu=4, nv=1, mi=rnd.randrange(n_mats))
            x += w


def roof_extras(bm_patch, bm_moss, S, x0, x1, rnd, n_patch, tiers=3, n_moss=30, n_twig=6, mi_twig=1):
    """补丁木板、苔藓、草和落下的树枝（R1、R2、R8-a41）。"""
    base = 0.03 + tiers * 0.035 + 0.05
    for k in range(n_patch):
        side = rnd.choice((-1, 1))
        u0 = rnd.uniform(0.05, 0.75)
        L = rnd.uniform(0.25, 0.45)
        xa = rnd.uniform(x0 + 0.3, x1 - 1.0)
        w = rnd.uniform(0.25, 0.55)
        skew = rnd.uniform(-0.6, 0.6)
        surf_box(bm_patch, lambda u, xx, side=side, skew=skew, u0=u0: S(xx + (u - u0) * skew * 3, side, u) + Vector((0, 0, base)),
                 u0, min(1.0, u0 + L), xa, xa + w, 0.045, nu=3, nv=1, mi=k % 3)
    for k in range(n_moss):
        side = rnd.choice((-1, 1))
        p = S(rnd.uniform(x0 + 0.2, x1 - 0.2), side, rnd.uniform(0.05, 0.95)) + Vector((0, 0, base - 0.03))
        if rnd.random() < 0.6:
            bm_ico(bm_moss, rnd.uniform(0.12, 0.3), loc=p, scale=(1.3, 1.0, 0.3), subdiv=1, rough=0.3, seed=k, mi=0)
        else:
            for g in range(5):
                a = g * 1.26
                bm_cyl(bm_moss, 0.02, 0.0, rnd.uniform(0.18, 0.32), loc=p + Vector((math.cos(a) * 0.05, math.sin(a) * 0.05, 0.12)),
                       rot=(math.cos(a) * 0.35, math.sin(a) * 0.35, 0), seg=4, mi=0)
    for k in range(n_twig):
        side = rnd.choice((-1, 1))
        x, u = rnd.uniform(x0 + 0.5, x1 - 1.5), rnd.uniform(0.1, 0.7)
        pts = [S(x + i * 0.35, side, u + i * rnd.uniform(-0.04, 0.06)) + Vector((0, 0, base + 0.03)) for i in range(4)]
        bm_tube(bm_moss, pts, [0.03, 0.025, 0.02, 0.012], seg=5, mi=mi_twig)
        bm_tube(bm_moss, [pts[1], pts[1] + Vector((0.2, 0.25 * side, 0.03))], [0.015, 0.008], seg=4, mi=mi_twig)


def rounded_rect_path(w, h, r, n=5):
    pts = []
    for cx, cz, a0 in ((w / 2 - r, h / 2 - r, 0.0), (-w / 2 + r, h / 2 - r, math.pi / 2),
                       (-w / 2 + r, -h / 2 + r, math.pi), (w / 2 - r, -h / 2 + r, 1.5 * math.pi)):
        for i in range(n + 1):
            a = a0 + (math.pi / 2) * i / n
            pts.append((cx + math.cos(a) * r, 0.0, cz + math.sin(a) * r))
    return pts + [pts[0], pts[1]]


def paper_cut(bm, y, r=0.17, mi=0):
    """红色窗花：八瓣团花（R2）。"""
    bm_cyl(bm, r * 0.35, r * 0.35, 0.012, loc=(0, y, 0), rot=(math.pi / 2, 0, 0), seg=12, mi=mi)
    for i in range(8):
        a = i * math.pi / 4
        bm_sphere(bm, (r * 0.32, 0.006, r * 0.17), loc=(math.cos(a) * r * 0.62, y, math.sin(a) * r * 0.62), rot=(0, -a, 0), seg=8, rings=4, mi=mi)


def lattice_window(bm, w, h, depth=0.24, mi_frame=0, mi_paper=1, mi_lat=2, mi_red=3, r=0.22, parts="all"):
    """圆角方框格子窗（R2、R4）：圆角木框、窗纸、木格、两面红色窗花；窗洞四周有木衬板。中心在原点，XZ 平面。
    parts="frame" 只要窗框，"shutter" 只要窗扇（窗纸、木格、窗花），"all" 两者都要。"""
    if parts == "shutter":
        bm_cube(bm, (w - 0.12, 0.02, h - 0.12), loc=(0, 0, 0), mi=mi_paper)
        for t in (-0.25, 0.0, 0.25):
            bm_cube(bm, (0.035, 0.06, h - 0.1), loc=(t * w, 0, 0), mi=mi_lat)
        for t in (-0.22, 0.22):
            bm_cube(bm, (w - 0.1, 0.06, 0.035), loc=(0, 0, t * h), mi=mi_lat)
        bm_cube(bm, (w - 0.08, 0.07, 0.05), loc=(0, 0, h / 2 - 0.07), mi=mi_lat)
        bm_cube(bm, (w - 0.08, 0.07, 0.05), loc=(0, 0, -h / 2 + 0.07), mi=mi_lat)
        for y in (-0.035, 0.035):
            paper_cut(bm, y, r=min(w, h) * 0.17, mi=mi_red)
        return
    pts = rounded_rect_path(w, h, r)
    for y in (-depth / 2 + 0.02, depth / 2 - 0.02):
        bm_tube(bm, [(p[0], y, p[2]) for p in pts], [0.065] * len(pts), seg=6, mi=mi_frame, caps=False)
    for sx, sz, px, pz in ((w + 0.12, 0.06, 0, h / 2 + 0.03), (w + 0.12, 0.06, 0, -h / 2 - 0.03),
                           (0.06, h + 0.12, w / 2 + 0.03, 0), (0.06, h + 0.12, -w / 2 - 0.03, 0)):
        bm_cube(bm, (sx, depth, sz), loc=(px, 0, pz), mi=mi_frame)
    if parts == "frame":
        return
    bm_cube(bm, (w - 0.12, 0.02, h - 0.12), loc=(0, 0, 0), mi=mi_paper)
    for t in (-0.25, 0.0, 0.25):
        bm_cube(bm, (0.035, 0.06, h - 0.1), loc=(t * w, 0, 0), mi=mi_lat)
    for t in (-0.22, 0.22):
        bm_cube(bm, (w - 0.1, 0.06, 0.035), loc=(0, 0, t * h), mi=mi_lat)
    for y in (-0.035, 0.035):
        paper_cut(bm, y, r=min(w, h) * 0.17, mi=mi_red)


def round_window(bm, r, half, depth, mi_frame=0, mi_glass=1, mi_lat=2, mi_fill=3, seg=28):
    """后墙圆形格子窗（R3、U7）：圆框、玻璃、橙色木格；方形窗洞的四角用木板补齐。"""
    bm_cyl(bm, r, r, 0.02, rot=(math.pi / 2, 0, 0), seg=seg, mi=mi_glass)
    for y in (-depth / 2 + 0.03, depth / 2 - 0.03):
        bm_torus(bm, r + 0.04, 0.06, loc=(0, y, 0), rot=(math.pi / 2, 0, 0), seg=seg, rseg=6, mi=mi_frame)
    bm_tube(bm, [(0, -depth / 2, 0), (0, depth / 2, 0)], [r + 0.02, r + 0.02], seg=seg, mi=mi_frame, caps=False)
    for t in (-0.5, 0.0, 0.5):
        ln = 2 * r * math.sqrt(max(0.0, 1 - t * t))
        bm_cube(bm, (0.035, 0.05, ln), loc=(t * r, 0, 0), mi=mi_lat)
        bm_cube(bm, (ln, 0.05, 0.035), loc=(0, 0, t * r), mi=mi_lat)
    # 四角补板：从方洞角点到圆弧的扇形面
    for qx, qz in ((1, 1), (-1, 1), (-1, -1), (1, -1)):
        a0 = math.atan2(qz, qx) - math.pi / 4
        for y in (-depth / 2, depth / 2):
            c = bm.verts.new((qx * half, y, qz * half))
            arc = [bm.verts.new((math.cos(a0 + k * (math.pi / 2) / 8) * (r + 0.03), y, math.sin(a0 + k * (math.pi / 2) / 8) * (r + 0.03)))
                   for k in range(9)]
            for k in range(8):
                f = bm.faces.new((c, arc[k], arc[k + 1]))
                f.material_index = mi_fill


def wall_run(name, cn, a, b, z0, H, holes, rnd, C_ext, C_int, root, ext_mats=None, int_mats=None, offsets=(0.13,), shrink=0.3,
             gable=None, status="observed", note=None, int_name=None, round_frac=0.3, int_cn=None):
    """一段墙：从 a 走到 b，左手边是室内。holes 用墙所在轴的坐标 (c0, c1, z0, z1)。
    外层红棕色木板/圆木（ext_mats），内层蓝灰色木板（int_mats，offsets 为距墙中线的距离）。gable=(half, rise) 时在墙顶加山墙。"""
    ax, ay = a
    bx, by = b
    L = math.hypot(bx - ax, by - ay)
    M = Matrix.Translation(((ax + bx) / 2, (ay + by) / 2, 0)) @ Matrix.Rotation(math.atan2(by - ay, bx - ax), 4, "Z")
    axis = 0 if abs(bx - ax) > abs(by - ay) else 1
    a0, sgn = a[axis], (1 if b[axis] > a[axis] else -1)
    lh = []
    for (c0, c1, hz0, hz1) in holes:
        s0, s1 = sorted(((c0 - a0) * sgn, (c1 - a0) * sgn))
        lh.append((s0 - L / 2, s1 - L / 2, hz0, hz1))
    out = []
    if ext_mats:
        bm = bmesh.new()
        log_wall(bm, L, H, lh, len(ext_mats), rnd, z0=z0, round_frac=round_frac)
        if gable:
            gable_boards(bm, gable[0], gable[1], len(ext_mats), rnd, z0=z0 + H)
        bmesh.ops.transform(bm, matrix=M, verts=bm.verts[:])
        out.append(new_obj(name + "_Exterior", bm, C_ext, ext_mats, parent=root, props=dict(cn=cn, status=status, note=note)))
    if int_mats:
        for k, off in enumerate(offsets):
            bm = bmesh.new()
            board_wall(bm, L - shrink, H, lh, len(int_mats), rnd, board=0.26, depth=0.05, z0=z0)
            if gable:
                gable_boards(bm, gable[0], gable[1], len(int_mats), rnd, board=0.26, depth=0.05, z0=z0 + H, inset=0.3)
            bmesh.ops.transform(bm, matrix=M @ Matrix.Translation((0, off, 0)), verts=bm.verts[:])
            nm = (int_name or name + "_Interior") + ("" if len(offsets) == 1 else ("_A", "_B")[k])
            out.append(new_obj(nm, bm, C_int, int_mats, parent=root,
                               props=dict(cn=int_cn or cn + "（室内蓝灰色墙板）", status="observed", note="R3、R4、U5–U7：室内是蓝灰色木板墙")))
    return out


def build_house():
    EXT = COLL["GuangtouQiang_House_Exterior"]
    ROOF = COLL["GQ_House_Roof_Removable"]
    INT = COLL["GuangtouQiang_House_Interior"]
    hx, hy = HOUSE["x"], HOUSE["y"]
    corners = [(WING["x0"], -D_HOUSE / 2), (WING["x0"], WING["y1"]), (-W_HOUSE / 2, D_HOUSE / 2), (W_HOUSE / 2, D_HOUSE / 2),
               (W_HOUSE / 2, -D_HOUSE / 2), (0, DECK_Y)]
    gz = max(ground(hx + x, hy + y) for x, y in corners)
    root = empty("GQ_House_Root", EXT, (hx, hy, gz), (0, 0, HOUSE["rot"]), size=1.5,
                 props=dict(cn="光头强的小木屋（根）", note="子物体都挂在这里，移动它即可整体移动木屋；局部 +Y 为正面"))
    rnd = random.Random(12)
    W, D, H, B = W_HOUSE, D_HOUSE, H_WALL, FOUND
    top = B + H

    def lg(x, y):
        """木屋局部坐标处的地面高度（相对根物体）。"""
        return ground(hx + x, hy + y) - gz

    # 材质（R1、R2：红棕色木墙；R3–R6：蓝灰色室内墙；R1、R2：蓝灰色木板屋顶）
    wood = [mat_noise(f"Wood_Wall_RedBrown_{i}", c1, c2, scale=9, bump=0.2, stretch=(0.25, 1.0, 1.0)) for i, (c1, c2) in enumerate(
        (("#8a3f2e", "#9a4b37"), ("#7a3527", "#8a4130"), ("#a0523b", "#b0614a"), ("#6e3226", "#7d3c2e"), ("#94503f", "#a35d4a")))]
    inner = [mat_noise(f"Wood_Plank_Interior_BlueGrey_{i}", c1, c2, scale=9, bump=0.1, stretch=(0.25, 1.0, 1.0)) for i, (c1, c2) in enumerate(
        (("#5c7486", "#68808f"), ("#4f6676", "#5d7484"), ("#667d8b", "#71889a")))]
    roof_m = [mat_noise(f"Roof_Board_BlueGrey_{i}", c1, c2, scale=7, bump=0.2, stretch=(0.3, 1.0, 1.0)) for i, (c1, c2) in enumerate(
        (("#4f7896", "#5d86a2"), ("#5e88a6", "#6b94b0"), ("#44697f", "#527790"), ("#6a90a8", "#7a9db3")))]
    patch_m = [mat_noise("Roof_Patch_Pale_Blue", "#8fb2c6", "#a0c0d2", scale=7), mat_noise("Roof_Patch_Tan_Wood", "#9b7350", "#ad8460", scale=8),
               mat_noise("Roof_Patch_Grey", "#7c8a92", "#8c99a0", scale=7)]
    moss_m = [mat_noise("Roof_Moss_Grass", "#5f9a3a", "#77b04a", scale=10), mat_noise("Roof_Twig", "#5a4330", "#6b5038", scale=10)]
    log_m = mat_noise("Bark_Log_Light", "#8a6a4a", "#9e7c58", scale=8, stretch=(0.3, 1.0, 1.0))
    cut_m = MATS.get("Wood_Cut_End") or mat_noise("Wood_Cut_End", "#d7b07a", "#e6c696", scale=12)
    post_m = mat_noise("Wood_Post_Dark", "#5e3a2a", "#6e4634", scale=8, stretch=(1.0, 1.0, 0.25))
    rail_m = mat_noise("Wood_Branch_Rail_Tan", "#c49a62", "#d4ad74", scale=9)
    stone_ms = [mat_noise("Stone_Base_GreyGreen", "#6f817c", "#83958f", scale=4, bump=0.4),
                mat_noise("Stone_Base_Grey", "#7d8384", "#91979a", scale=4, bump=0.4)]
    core_m = mat_noise("Stone_Base_Core", "#5d6466", "#6c7375", scale=5, bump=0.3)
    green = mat("Paint_Door_Frame_Green", "#3f7a58", rough=0.6)
    door_red = mat_noise("Wood_Door_DarkRed", "#6e2620", "#7c2e26", scale=9, stretch=(1.0, 1.0, 0.3))
    slat_red = mat("Wood_Door_Slat_Red", "#9a463a", rough=0.7)
    dark = mat("Shadow_Opening", "#1c1c1c", rough=1.0)
    frame_tan = mat_noise("Wood_Window_Frame_Tan", "#b48a5a", "#c49a68", scale=9)
    paper = mat("Paper_Window_Lattice", "#eee0bf", rough=0.9, emit="#ffe6b0", emit_strength=0.15)
    lat_m = mat("Wood_Lattice_Brown", "#7a5434", rough=0.7)
    red_paper = mat("Paper_Red_Cut", "#c8231d", rough=0.7)
    brick = mat_brick("Brick_Chimney_Red", "#9a3b2c", "#b04a36", "#8a7f72", scale=3.0)
    cap_m = mat_noise("Stone_Chimney_Cap", "#9aa3a0", "#adb5b2", scale=6)
    metal = mat("Metal_Antenna", "#a7adb1", metal=0.8, rough=0.35)
    chili = MATS.get("Chili_Red") or mat("Chili_Red", "#c8241c", rough=0.45)
    corn_m = MATS.get("Corn_Yellow") or mat("Corn_Yellow", "#f0c943", rough=0.6)
    husk = mat("Corn_Husk", "#d9c08a", rough=0.8)

    # ---- 石头基座（R1：木屋坐在青灰色石头矮墙上，比院子高）
    bm = bmesh.new()
    for (x0, x1, y0, y1, zt) in ((-W / 2 - 0.05, W / 2 + 0.05, -D / 2 - 0.05, D / 2, B - 0.04),
                                 (WING["x0"] - 0.05, -W / 2, WING["y0"] - 0.05, WING["y1"] + 0.05, B - 0.04),
                                 (-W / 2 - 0.2, W / 2 + 0.2, D / 2, DECK_Y - 0.12, B - 0.27)):
        zb = min(lg(x, y) for x in (x0, x1) for y in (y0, y1)) - 0.6
        bm_cube(bm, (x1 - x0, y1 - y0, zt - zb), loc=((x0 + x1) / 2, (y0 + y1) / 2, (zt + zb) / 2))
    new_obj("GQ_Stone_Base_Core", bm, EXT, [core_m], parent=root, props=dict(cn="石头基座（内芯）", status="observed", note="R1、R8-a41：青灰色石头基座"))
    bm = bmesh.new()
    loop = [(W / 2, -D / 2), (W / 2, D / 2), (W / 2 + 0.2, D / 2), (W / 2 + 0.2, DECK_Y - 0.12), (-W / 2 - 0.2, DECK_Y - 0.12), (-W / 2 - 0.2, D / 2), (-W / 2, D / 2), (-W / 2, WING["y1"]),
            (WING["x0"], WING["y1"]), (WING["x0"], WING["y0"]), (W / 2, -D / 2)]
    for (ax, ay), (bx, by) in zip(loop[:-1], loop[1:]):
        L = math.hypot(bx - ax, by - ay)
        n = max(1, int(L / 0.55))
        along_x = abs(bx - ax) > abs(by - ay)
        nx, ny = ((by - ay) / L, -(bx - ax) / L)  # 走向的右手边 = 墙外
        for i in range(n + 1):
            t = i / n
            px, py = ax + (bx - ax) * t + nx * 0.06, ay + (by - ay) * t + ny * 0.06
            zt = B - (0.3 if py > D / 2 + 0.01 else 0.1)
            zb = lg(px, py) - 0.15
            rows = max(1, int((zt - zb) / 0.36 + 0.5))
            for r in range(rows):
                s = rnd.uniform(0.22, 0.32)
                off = (0.27 if r % 2 else 0.0) * (1 if along_x else 0)
                offy = (0.27 if r % 2 else 0.0) * (0 if along_x else 1)
                z = zb + (r + 0.5) * (zt - zb) / rows
                sc = (1.25, 0.55, 0.75) if along_x else (0.55, 1.25, 0.75)
                bm_ico(bm, s, loc=(px + off, py + offy, z), scale=sc, subdiv=1, rough=0.25, seed=i * 7 + r, mi=rnd.randrange(2))
    new_obj("GQ_Stone_Base", bm, EXT, stone_ms, parent=root, props=dict(cn="石头基座（外圈石块）", status="observed", note="R1、R2"))

    # ---- 地板（室内各房间的地板在 build_house_interior 里；这里是主屋和侧翼的地板龙骨）
    # ---- 外墙（主屋逆时针：后 → 东 → 前 → 西；左手边是室内）
    ext_note = "R1、R2：红棕色原木和木板墙，深浅不一"
    hole_door = (DOOR_X[0], DOOR_X[1], 0.0, 2.1)
    holes_front = [hole_door] + [(x0, x1, WIN_Z[0], WIN_Z[1]) for x0, x1 in WIN_FRONT]
    rx, rz, rr = ROUND_WIN
    hole_round = (rx - 0.6, rx + 0.6, rz - 0.6, rz + 0.6)
    hole_bath = (BATH_DOOR[0], BATH_DOOR[1], 0.0, 2.05)
    wall_run("GQ_Wall_Back", "后墙", (-W / 2, -D / 2), (W / 2, -D / 2), B, H, [hole_round], rnd, EXT, INT, root, wood, inner,
             note="R1 只看到正面；后墙按正面材料推测，圆窗依据 R3", status="inferred")
    wall_run("GQ_Wall_East", "东山墙（卧室一侧）", (W / 2, -D / 2), (W / 2, D / 2), B, H, [], rnd, EXT, INT, root, wood, inner,
             gable=(D / 2, ROOF_RISE), note="R8-a41/a42：山墙上露出圆木头；东墙不开窗为推测", status="inferred")
    wall_run("GQ_Wall_Front", "正面墙", (W / 2, D / 2), (-W / 2, D / 2), B, H, holes_front, rnd, EXT, INT, root, wood, inner, note=ext_note)
    wall_run("GQ_Wall_West", "西山墙（客厅与卫生间之间）", (-W / 2, D / 2), (-W / 2, -D / 2), B, H, [hole_bath], rnd, EXT, INT, root, wood, inner,
             gable=(D / 2, ROOF_RISE), note="卫生间门开在这面墙上（R6、R8-a52 积木布局）", status="inferred", round_frac=0.0)
    # 侧翼（卫生间）：逆时针 后 → … ；东侧借用主屋西墙
    bath_int = [mat_noise(f"Wood_Plank_Bathroom_LightBlue_{i}", c1, c2, scale=9, bump=0.1, stretch=(0.25, 1.0, 1.0)) for i, (c1, c2) in enumerate(
        (("#7d99aa", "#8aa5b5"), ("#7090a2", "#7e9cad")))]
    Cb = COLL["GQ_Room_Bathroom"]
    hw = WING["h"]
    wing_win = (-1.0, -0.3, 1.2, 1.9)
    wall_run("GQ_Wing_Wall_Back", "卫生间侧翼后墙", (WING["x0"], WING["y0"]), (WING["x1"], WING["y0"]), B, hw, [], rnd, EXT, Cb, root, wood, bath_int,
             status="inferred", note="R1 只看到侧翼正面")
    wall_run("GQ_Wing_Wall_Front", "卫生间侧翼正面墙（挂玉米）", (WING["x1"], WING["y1"]), (WING["x0"], WING["y1"]), B, hw, [], rnd, EXT, Cb, root, wood, bath_int,
             note="R1、R8-a41：侧翼正面挂三串玉米")
    wall_run("GQ_Wing_Wall_West", "卫生间侧翼西山墙（小窗）", (WING["x0"], WING["y1"]), (WING["x0"], WING["y0"]), B, hw, [wing_win], rnd, EXT, Cb, root, wood, bath_int,
             gable=((WING["y1"] - WING["y0"]) / 2, WING["rise"]), note="R8-a42：侧翼山墙有格子窗，山墙上露出圆木头")
    wall_run("GQ_Bathroom_Wall_East", "卫生间东墙（主屋西墙的卫生间一侧）", (-W / 2, WING["y0"]), (-W / 2, WING["y1"]), B, hw,
             [hole_bath], rnd, EXT, Cb, root, None, bath_int, offsets=(0.13,), int_name="GQ_Bathroom_Wall_East_Boards",
             int_cn="卫生间东墙（浅蓝灰色墙板）")
    # 卧室隔墙（两面都是蓝灰色木板，开门洞）
    wall_run("GQ_Partition_Bedroom", "客厅与卧室之间的隔墙", (PART_X, -IN_Y), (PART_X, IN_Y), B, H, [(BED_DOOR[0], BED_DOOR[1], 0.0, 2.05)],
             rnd, EXT, COLL["GQ_Room_Bedroom"], root, None, inner, offsets=(-0.06, 0.06), shrink=0.0, int_name="GQ_Partition_Bedroom_Boards",
             int_cn="卧室隔墙（蓝灰色木板，两面）")

    # ---- 转角交叉圆木头和正面粗细不一的木柱（R1、R2）
    bm = bmesh.new()
    for (cx, cy, h) in ((W / 2, -D / 2, H), (W / 2, D / 2, H), (WING["x0"], WING["y0"], hw), (WING["x0"], WING["y1"], hw)):
        z = B + 0.15
        k = 0
        while z < B + h - 0.05:
            r = rnd.uniform(0.12, 0.15)
            ext_len = rnd.uniform(0.25, 0.4)
            if k % 2 == 0:
                bm_cyl(bm, r, r, 0.6 + ext_len, loc=(cx + math.copysign(ext_len / 2, cx), cy, z), rot=(0, math.pi / 2, 0), seg=10, mi=0)
                bm_cyl(bm, r * 0.95, r * 0.95, 0.01, loc=(cx + math.copysign(ext_len + 0.3, cx), cy, z), rot=(0, math.pi / 2, 0), seg=10, mi=1)
            else:
                bm_cyl(bm, r, r, 0.6 + ext_len, loc=(cx, cy + math.copysign(ext_len / 2, cy), z), rot=(math.pi / 2, 0, 0), seg=10, mi=0)
                bm_cyl(bm, r * 0.95, r * 0.95, 0.01, loc=(cx, cy + math.copysign(ext_len + 0.3, cy), z), rot=(math.pi / 2, 0, 0), seg=10, mi=1)
            z += 2 * r + 0.02
            k += 1
    new_obj("GQ_Corner_LogEnds", bm, EXT, [log_m, cut_m], parent=root,
            props=dict(cn="转角交叉的圆木头", status="inferred", note="R1 侧翼转角可见圆木头；其余转角按此推测"))
    bm = bmesh.new()
    for x, r0, lean in ((4.32, 0.17, 0.03), (1.75, 0.13, -0.025), (-1.75, 0.15, 0.02), (-4.38, 0.19, -0.03)):
        bm_tube(bm, [(x, D / 2 + 0.16, B - 0.05), (x + lean * 0.5, D / 2 + 0.16, B + 1.6), (x + lean, D / 2 + 0.16, top - 0.15)],
                [r0 * 1.08, r0, r0 * 0.94], seg=10, mi=0)
    new_obj("GQ_Posts_Irregular", bm, EXT, [post_m], parent=root, smooth_shade=True,
            props=dict(cn="正面粗细不一、略倾斜的木柱", status="observed", note="R2：门窗两侧深色粗木柱；根数为估算"))

    # ---- 门：绿色门框里的深红色对开门，上部竖条窗（R2）；门向外打开，可以进入
    bm = bmesh.new()
    for x in (DOOR_X[0] - 0.06, DOOR_X[1] + 0.06):
        bm_cube(bm, (0.12, 0.26, 2.16), loc=(x, D / 2 + 0.02, B + 1.08))
    bm_cube(bm, (DOOR_X[1] - DOOR_X[0] + 0.24, 0.26, 0.12), loc=((DOOR_X[0] + DOOR_X[1]) / 2, D / 2 + 0.02, B + 2.16))
    bm_cube(bm, (DOOR_X[1] - DOOR_X[0], 0.24, 0.04), loc=((DOOR_X[0] + DOOR_X[1]) / 2, D / 2 + 0.02, B + 0.02))
    new_obj("GQ_Door_Front_Frame_Green", bm, EXT, [green], parent=root, props=dict(cn="正门绿色门框", status="observed", note="R2"))
    dw = (DOOR_X[1] - DOOR_X[0]) / 2
    for side, hinge, ang in (("East", DOOR_X[1], -1.0), ("West", DOOR_X[0], 1.0)):
        bm = bmesh.new()
        s = -1 if side == "East" else 1  # 门扇从铰链向门洞中间延伸的方向
        bm_cube(bm, (dw - 0.01, 0.06, 2.08), loc=(s * dw / 2, 0, 1.04), mi=0)
        bm_cube(bm, (dw - 0.16, 0.065, 0.62), loc=(s * dw / 2, 0, 1.62), mi=2)
        for i in range(5):
            bm_cube(bm, (0.045, 0.075, 0.62), loc=(s * (0.12 + i * (dw - 0.24) / 4), 0, 1.62), mi=1)
        for z in (0.35, 0.8, 1.2):
            bm_cube(bm, (dw - 0.06, 0.08, 0.06), loc=(s * dw / 2, 0, z), mi=1)
        bm_torus(bm, 0.04, 0.008, loc=(s * (dw - 0.1), 0.05, 1.05), rot=(math.pi / 2, 0, 0), seg=10, rseg=4, mi=3)
        ob = new_obj(f"GQ_Door_Front_Leaf_{side}", bm, EXT, [door_red, slat_red, dark, metal], parent=root,
                     props=dict(cn="深红色对开木门（上部竖条窗，已打开）", status="observed", note="R2；门扇内侧细节为推测"))
        ob.location = (hinge, D / 2 + 0.16, B)
        ob.rotation_euler = (0, 0, ang * math.radians(100))
    DOOR_PASSAGES.append(("正门", "GQ_House_Root", (DOOR_X[0] + 0.1, DOOR_X[1] - 0.1, D / 2 - 1.2, D / 2 + 1.0, B + 0.05, B + 2.0)))

    # ---- 正面两扇圆角格子窗，贴红窗花（R2）；卫生间小格子窗（R8-a42）
    for nm, (x0, x1) in zip(("West_LivingRoom", "East_Bedroom"), WIN_FRONT):
        bm = bmesh.new()
        ww, wh = x1 - x0, WIN_Z[1] - WIN_Z[0]
        lattice_window(bm, ww, wh, depth=0.34, parts="frame")
        bmesh.ops.transform(bm, matrix=Matrix.Translation(((x0 + x1) / 2, D / 2, B + (WIN_Z[0] + WIN_Z[1]) / 2)), verts=bm.verts[:])
        new_obj(f"GQ_Window_Front_{nm}", bm, EXT, [frame_tan, paper, lat_m, red_paper], parent=root,
                props=dict(cn="圆角方框窗框", status="observed", note="R2：门两侧各一扇"))
        # 窗扇单独一个物体，原点在上沿的铰链：R2 里是关着的；A45 里窗扇向外上翻、用弧形木撑撑住（绕 X 轴转 +35° 即打开）
        bm = bmesh.new()
        lattice_window(bm, ww, wh, parts="shutter")
        bmesh.ops.transform(bm, matrix=Matrix.Translation((0, -0.06, -wh / 2)), verts=bm.verts[:])
        sh = new_obj(f"GQ_Window_Front_{nm}_Shutter", bm, EXT, [frame_tan, paper, lat_m, red_paper], parent=root,
                     props=dict(cn="格子窗扇（贴红窗花，上沿铰链，可向外上翻）", status="observed",
                                note="R2：关着；A45：向外上翻打开。绕局部 X 轴旋转 +35° 打开"))
        sh.location = ((x0 + x1) / 2, D / 2 + 0.06, B + WIN_Z[1])
        sh["open_rotation_x_deg"] = 35.0
    bm = bmesh.new()
    lattice_window(bm, 0.7, 0.7, r=0.14)
    bmesh.ops.transform(bm, matrix=Matrix.Translation((WING["x0"], -0.65, B + 1.55)) @ Matrix.Rotation(math.pi / 2, 4, "Z"), verts=bm.verts[:])
    new_obj("GQ_Window_Bathroom_West", bm, EXT, [frame_tan, paper, lat_m, red_paper], parent=root,
            props=dict(cn="卫生间格子小窗", status="inferred", note="R8-a42 积木侧翼山墙下有格子窗；动画里看不到"))
    bm = bmesh.new()
    round_window(bm, rr, 0.6, 0.26)
    bmesh.ops.transform(bm, matrix=Matrix.Translation((rx, -D / 2 + 0.065, B + rz)), verts=bm.verts[:])
    new_obj("GQ_Window_Back_Round_Kitchen", bm, EXT, [mat_noise("Wood_Window_Frame_Orange", "#a5622f", "#b9733a", scale=10),
                                                    mat("Glass_Clear", "#cfe6f2", rough=0.05, transmission=0.9),
                                                    mat("Wood_Lattice_Orange", "#c4772f", rough=0.6), frame_tan], parent=root,
            props=dict(cn="厨房圆形格子窗", status="observed", note="R3、U7：水槽右侧的圆形格子窗"))

    # ---- 正面露台：一排顺着前后方向的原木，前沿露出原木端头（R2）；窗下石头矮墙（R2）
    bm = bmesh.new()
    x = -W / 2 - 0.2 + 0.13
    while x < W / 2 + 0.2:
        r = rnd.uniform(0.12, 0.14)
        bm_cyl(bm, r, r, DECK_Y - D / 2 + 0.05, loc=(x, (D / 2 + DECK_Y) / 2, B - r), rot=(math.pi / 2, 0, 0), seg=10, mi=0)
        bm_cyl(bm, r * 0.95, r * 0.95, 0.01, loc=(x, DECK_Y + 0.03, B - r), rot=(math.pi / 2, 0, 0), seg=10, mi=1)
        x += 0.265
    new_obj("GQ_Front_Deck_Logs", bm, EXT, [log_m, cut_m], parent=root,
            props=dict(cn="门前原木露台（前沿露出原木端头）", status="observed", note="R2"))
    bm = bmesh.new()
    mortar = mat_noise("Stone_Mortar_Grey", "#566262", "#606c6c", scale=6)
    for x0, x1 in ((-W / 2 + 0.25, DOOR_X[0] - 0.35), (DOOR_X[1] + 0.35, W / 2 - 0.25)):
        bm_cube(bm, (x1 - x0, 0.36, WIN_Z[0] - 0.02), loc=((x0 + x1) / 2, D / 2 + 0.3, B + (WIN_Z[0] - 0.02) / 2), mi=2)
        n = max(2, int((x1 - x0) / 0.62))
        for rrow in range(2):
            for i in range(n + (rrow % 2)):
                xx = x0 + (i + (0.5 if rrow % 2 == 0 else 0.0)) * (x1 - x0) / n
                if not (x0 + 0.1 < xx < x1 - 0.1):
                    continue
                bm_ico(bm, rnd.uniform(0.27, 0.33), loc=(xx, D / 2 + 0.44, B + 0.24 + rrow * 0.44), scale=(1.15, 0.45, 0.75), subdiv=2, rough=0.12,
                       seed=i + 10 * rrow, mi=rnd.randrange(2))
    new_obj("GQ_Front_Stone_Planters", bm, EXT, stone_ms + [mortar], parent=root, smooth_shade=True,
            props=dict(cn="窗下青灰色大圆石矮墙（从露台到窗台）", status="observed", note="R2、A45：窗下是一道大圆石砌的矮墙，顶面和窗台齐平"))

    # ---- 中间木楼梯 + 树枝扶手（R1、R2）
    sx0, sx1 = DOOR_X[0] - 0.1, DOOR_X[1] + 0.1
    zf = lg((sx0 + sx1) / 2, DECK_Y + 1.8)
    n_steps = max(3, int(round((B - zf) / 0.19)))
    rise = (B - zf) / n_steps
    zf = lg((sx0 + sx1) / 2, DECK_Y + n_steps * 0.3)
    rise = (B - zf) / n_steps
    y_end = DECK_Y + n_steps * 0.3
    bm = bmesh.new()
    for k in range(1, n_steps + 1):
        ztop = B - k * rise
        y0 = DECK_Y + (k - 1) * 0.3
        bm_cube(bm, (sx1 - sx0, 0.34, 0.07), loc=((sx0 + sx1) / 2, y0 + 0.15, ztop - 0.035), rot=(0, rnd.uniform(-0.01, 0.01), 0), mi=0)
        bm_cube(bm, (sx1 - sx0 - 0.1, 0.3, max(0.05, ztop - 0.07 - zf + 0.2)), loc=((sx0 + sx1) / 2, y0 + 0.15, (ztop - 0.07 + zf - 0.2) / 2), mi=1)
    for x in (sx0 - 0.05, sx1 + 0.05):
        bm_tube(bm, [(x, DECK_Y - 0.05, B - 0.1), (x, y_end + 0.05, zf - 0.05)], [0.11, 0.11], seg=10, mi=2)
    new_obj("GQ_Front_Stairs", bm, EXT, [mat_noise("Wood_Stair_Tread", "#a8825a", "#b9926a", scale=8), mat_noise("Wood_Stair_Riser", "#6a4a34", "#7a573e", scale=8), log_m],
            parent=root, props=dict(cn=f"正门木楼梯（{n_steps} 级）", status="observed", note="R1、R2：露台中间一道木楼梯；级数按地面高差计算"))

    def branch(bm, p0, p1, r, wob=0.03):
        p0, p1 = Vector(p0), Vector(p1)
        n = 4
        pts = [p0.lerp(p1, i / n) + (Vector((rnd.uniform(-wob, wob), rnd.uniform(-wob, wob), rnd.uniform(-wob, wob))) if 0 < i < n else Vector())
               for i in range(n + 1)]
        bm_tube(bm, pts, [r * rnd.uniform(0.9, 1.1) for _ in pts], seg=8)
    bm = bmesh.new()
    yr = DECK_Y - 0.1
    hr = 0.95
    posts = [(-W / 2 - 0.1, yr), (-3.1, yr), (sx0 - 0.05, yr), (sx1 + 0.05, yr), (2.0, yr), (W / 2 + 0.1, yr),
             (-W / 2 - 0.1, D / 2 + 0.7), (W / 2 + 0.1, D / 2 + 0.7)]
    for (px, py) in posts:
        branch(bm, (px, py, B - 0.1), (px, py, B + hr), rnd.uniform(0.07, 0.1), wob=0.015)
        bm_sphere(bm, (0.1, 0.1, 0.08), loc=(px, py, B + hr + 0.02), seg=10, rings=6)
    for (a, b) in ((0, 1), (1, 2), (3, 4), (4, 5), (0, 6), (5, 7)):
        (ax, ay), (bx, by) = posts[a], posts[b]
        branch(bm, (ax, ay, B + hr - 0.05), (bx, by, B + hr - 0.05), 0.065)
        branch(bm, (ax, ay, B + 0.45), (bx, by, B + 0.5), 0.045)
    for x in (sx0 - 0.05, sx1 + 0.05):
        branch(bm, (x, y_end - 0.1, zf - 0.1), (x, y_end - 0.1, zf + hr), 0.085, wob=0.015)
        bm_sphere(bm, (0.1, 0.1, 0.08), loc=(x, y_end - 0.1, zf + hr + 0.02), seg=10, rings=6)
        branch(bm, (x, yr, B + hr - 0.05), (x, y_end - 0.1, zf + hr - 0.05), 0.065)
        branch(bm, (x, yr, B + 0.45), (x, y_end - 0.1, zf + 0.45), 0.045)
    new_obj("GQ_Deck_Stair_Railings", bm, EXT, [rail_m], parent=root, smooth_shade=True,
            props=dict(cn="露台和楼梯的天然树枝扶手", status="observed", note="R1、R2：浅色树枝扶手，立柱顶端圆头"))
    DOOR_PASSAGES.append(("正门楼梯", "GQ_House_Root", (sx0 + 0.2, sx1 - 0.2, DECK_Y - 0.3, y_end, zf + 0.3, B + 2.0)))

    # ---- 屋檐下的装饰：辣椒串、玉米串、葫芦、圆形小牌（R1、R2）
    bm = bmesh.new()
    for x, n in ((3.85, 15), (1.45, 13), (-1.4, 9)):
        for i in range(n):
            bm_cyl(bm, 0.05, 0.0, 0.22, loc=(x + math.sin(i * 1.9) * 0.06, D / 2 + 0.24 + math.cos(i * 1.3) * 0.04, top - 0.15 - i * 0.1),
                   rot=(math.pi + math.sin(i) * 0.3, 0, 0), seg=6)
    new_obj("GQ_Eave_Chili_Strings", bm, EXT, [chili], parent=root, props=dict(cn="屋檐下的红辣椒串", status="observed", note="R2：门边、窗边"))
    bm = bmesh.new()
    for x in (-6.45, -5.75, -5.05):
        for i in range(6):
            a = (i - 2.5) * 0.25
            bm_sphere(bm, (0.075, 0.075, 0.22), loc=(x + math.sin(a) * 0.14, WING["y1"] + 0.2, B + hw - 0.7 - abs(i - 2.5) * 0.06),
                      rot=(0, a, 0), seg=10, rings=8, mi=0)
            bm_cyl(bm, 0.03, 0.06, 0.18, loc=(x + math.sin(a) * 0.05, WING["y1"] + 0.2, B + hw - 0.45), rot=(0, a * 0.6, 0), seg=6, mi=1)
        bm_cyl(bm, 0.01, 0.01, 0.25, loc=(x, WING["y1"] + 0.2, B + hw - 0.27), seg=4, mi=1)
    bm_sphere(bm, (0.12, 0.12, 0.16), loc=(-1.75, D / 2 + 0.3, B + 1.85), seg=12, rings=8, mi=0)
    bm_sphere(bm, (0.16, 0.16, 0.2), loc=(-1.75, D / 2 + 0.3, B + 1.55), seg=12, rings=8, mi=0)
    new_obj("GQ_Eave_Corn_And_Gourd", bm, EXT, [corn_m, husk], parent=root, smooth_shade=True,
            props=dict(cn="侧翼墙上的三串玉米、门边的葫芦", status="observed", note="R1、R8-a41：侧翼正面三串玉米；R2：右窗左侧黄色葫芦"))
    bm = bmesh.new()
    for x, z, r in ((-1.25, 2.45, 0.11), (-1.25, 2.1, 0.07), (1.2, 2.5, 0.09)):
        bm_cyl(bm, r, r, 0.03, loc=(x, D / 2 + 0.14, B + z), rot=(math.pi / 2, 0, 0), seg=16)
    new_obj("GQ_Wall_Plaques", bm, EXT, [mat("Metal_Plaque_Grey", "#9aa5a6", metal=0.5, rough=0.4)], parent=root,
            props=dict(cn="门边墙上的圆形小牌", status="observed", note="R2"))

    # ---- 屋顶（可隐藏）：主屋 + 侧翼。木板顺坡铺、分三层、两端上翘（东端翘得更高），补丁、苔藓、树枝（R1、R2、R8-a41）
    x0m, x1m = -W / 2 - 0.7, W / 2 + 0.7
    S = roof_surface(x0m, x1m, 0.0, D / 2, ROOF_OV, top, ROOF_RISE, lift_hi=0.65, lift_lo=0.4)
    bm = bmesh.new()
    roof_boards(bm, S, x0m, x1m, rnd, len(roof_m))
    for side in (-1, 1):
        surf_box(bm, lambda u, xx, side=side: S(xx, side, u) + Vector((0, 0, 0.15)), 0.0, 0.07, x0m - 0.1, x1m + 0.1, 0.05, nu=1, nv=12, mi=2)
    new_obj("GQ_Roof_Main_Boards", bm, COLL["GQ_House_Roof_Removable"], roof_m, parent=root,
            props=dict(cn="主屋顶：蓝灰色木板（可隐藏）", status="observed", note="R1、R2：蓝灰色长短不一的木板；背面坡看不到，按正面推测"))
    bm_p, bm_m = bmesh.new(), bmesh.new()
    roof_extras(bm_p, bm_m, S, x0m, x1m, rnd, 16, n_moss=34, n_twig=7)
    new_obj("GQ_Roof_Patches", bm_p, ROOF, patch_m, parent=root, props=dict(cn="屋顶补丁木板", status="observed", note="R1、R2：浅色补丁板、斜放的木板"))
    new_obj("GQ_Roof_Moss_Twigs", bm_m, ROOF, moss_m, parent=root, props=dict(cn="屋顶苔藓、草和树枝", status="observed", note="R2"))
    under = mat_noise("Wood_Ceiling_Underside", "#6e5a4a", "#7d6957", scale=8, stretch=(0.3, 1.0, 1.0))
    bm = bmesh.new()
    for side in (-1, 1):
        surf_box(bm, lambda u, xx, side=side: S(xx, side, u) - Vector((0, 0, 0.1)), 0.0, 1.0, x0m, x1m, 0.04, nu=16, nv=40, mi=0)
    # 檩条：顺屋脊方向的圆木，伸出山墙，端头露在上翘的屋檐下（R2、R8-a41/a42）
    for side in (-1, 1):
        for u in ((0.0, 0.17, 0.34, 0.51, 0.68, 0.86) if side > 0 else (0.17, 0.34, 0.51, 0.68, 0.86)):  # R2：山墙上一排粗圆木端头
            p = S(0.0, side, u)
            r = rnd.uniform(0.2, 0.26)
            bm_cyl(bm, r, r, x1m - x0m + 0.5, loc=(0, p.y, p.z - r - 0.03), rot=(0, math.pi / 2, 0), seg=12, mi=1)
            for ex in (x0m - 0.25, x1m + 0.25 + rnd.uniform(0.0, 0.35)):
                bm_cyl(bm, r * 0.95, r * 0.95, 0.01, loc=(ex + math.copysign(0.005, ex), p.y, p.z - r - 0.03), rot=(0, math.pi / 2, 0), seg=12, mi=2)
    # 室内横梁（R4：屋里看得到横梁）
    for x in (-3.0, -0.9, 3.0):
        bm_cyl(bm, 0.12, 0.12, D, loc=(x, 0, top + 0.05), rot=(math.pi / 2, 0, 0), seg=10, mi=1)
    new_obj("GQ_Roof_Underside_Purlins_Beams", bm, ROOF, [under, log_m, cut_m], parent=root,
            props=dict(cn="屋顶内衬板、檩条（端头露出山墙）和室内横梁", status="observed", note="R3、R4：室内能看到斜屋顶木板和横梁"))
    # 侧翼屋顶（卫生间）：屋脊也顺东西向，西端翘起，屋脊比主屋檐低
    wy = (WING["y0"] + WING["y1"]) / 2
    whalf = (WING["y1"] - WING["y0"]) / 2
    x0w, x1w = WING["x0"] - 0.6, -W / 2 - 0.05
    Sw = roof_surface(x0w, x1w, wy, whalf, 0.6, B + hw, WING["rise"], lift_hi=0.0, lift_lo=0.45)
    bm = bmesh.new()
    roof_boards(bm, Sw, x0w, x1w, rnd, len(roof_m), tiers=2)
    for side in (-1, 1):
        surf_box(bm, lambda u, xx, side=side: Sw(xx, side, u) + Vector((0, 0, 0.12)), 0.0, 0.08, x0w - 0.1, x1w, 0.05, nu=1, nv=6, mi=2)
        surf_box(bm, lambda u, xx, side=side: Sw(xx, side, u) - Vector((0, 0, 0.1)), 0.0, 1.0, x0w, x1w, 0.04, nu=16, nv=16, mi=len(roof_m))
    for side, u in ((1, 0.0), (1, 0.5), (-1, 0.5), (1, 0.95), (-1, 0.95)):
        p = Sw(-6.0, side, u)
        bm_cyl(bm, 0.12, 0.12, x1w - x0w + 0.3, loc=((x0w + x1w) / 2 - 0.15, p.y, p.z - 0.15), rot=(0, math.pi / 2, 0), seg=10, mi=len(roof_m) + 1)
        bm_cyl(bm, 0.115, 0.115, 0.01, loc=(x0w - 0.31, p.y, p.z - 0.15), rot=(0, math.pi / 2, 0), seg=10, mi=len(roof_m) + 2)
    new_obj("GQ_Roof_Wing_Boards", bm, ROOF, roof_m + [under, log_m, cut_m], parent=root,
            props=dict(cn="卫生间侧翼屋顶（可隐藏）", status="observed", note="R1、R8-a41：右侧较低的副屋顶，山墙露出圆木头"))
    bm_p, bm_m = bmesh.new(), bmesh.new()
    roof_extras(bm_p, bm_m, Sw, x0w, x1w, rnd, 4, tiers=2, n_moss=10, n_twig=2)
    new_obj("GQ_Roof_Wing_Patches", bm_p, ROOF, patch_m, parent=root, props=dict(cn="侧翼屋顶补丁", status="observed", note="R1"))
    new_obj("GQ_Roof_Wing_Moss", bm_m, ROOF, moss_m, parent=root, props=dict(cn="侧翼屋顶苔藓", status="inferred"))
    # 红砖烟囱 + 灰色烟囱帽（R1、R2：高高的红砖烟囱，在主屋顶靠侧翼一侧、屋脊后面）
    bm = bmesh.new()
    cxh, cyh = -3.4, -2.3
    z = top + 0.2
    lean = 0.0
    while z < top + 4.3:
        lean += rnd.uniform(-0.006, 0.01)
        bm_cube(bm, (0.72 + rnd.uniform(-0.02, 0.02), 0.72 + rnd.uniform(-0.02, 0.02), 0.2), loc=(cxh + lean, cyh + rnd.uniform(-0.01, 0.01), z + 0.1), mi=0)
        z += 0.2
    bm_cube(bm, (0.86, 0.86, 0.12), loc=(cxh + lean, cyh, z + 0.06), mi=1)
    bm_cube(bm, (0.62, 0.62, 0.3), loc=(cxh + lean, cyh, z + 0.27), mi=1)
    bm_cube(bm, (0.92, 0.92, 0.1), loc=(cxh + lean, cyh, z + 0.47), mi=1)
    new_obj("GQ_Chimney_RedBrick", bm, ROOF, [brick, cap_m], parent=root,
            props=dict(cn="红砖烟囱和灰色烟囱帽", status="observed", note="R1、R2；烟囱根部被屋顶挡住，为推测"))
    # 电视天线（R1、R8-a41：侧翼屋顶上）
    bm = bmesh.new()
    pz = Sw(-5.35, 1, 0.0).z + 0.1
    bm_cyl(bm, 0.025, 0.02, 1.9, loc=(-5.35, wy, pz + 0.95), seg=8)
    for k, (zz, ln) in enumerate(((1.2, 1.0), (1.5, 0.8), (1.75, 0.6))):
        bm_cyl(bm, 0.012, 0.012, ln, loc=(-5.35, wy, pz + zz), rot=(0, math.pi / 2, 0.5), seg=6)
        for s in (-1, 1):
            bm_cyl(bm, 0.008, 0.008, 0.28, loc=(-5.35 + s * ln * 0.44 * math.cos(0.5), wy + s * ln * 0.44 * math.sin(0.5), pz + zz + 0.12), rot=(0.25 * s, 0, 0), seg=4)
    new_obj("GQ_TV_Antenna", bm, ROOF, [metal], parent=root, props=dict(cn="电视天线", status="observed", note="R1、R8-a41"))

    build_house_interior(root, gz)
    build_yard(root, lg, y_end)
    return root


def build_house_interior(root, gz):
    """三个室内空间：A 客厅/厨房/餐厅（开放）、B 卧室（隔墙后）、C 卫生间（侧翼，有自己的墙和门）。"""
    B = FOUND
    ROOM = {"Kitchen": COLL["GQ_Room_Kitchen_Dining"], "Bedroom": COLL["GQ_Room_Bedroom"], "Bathroom": COLL["GQ_Room_Bathroom"]}

    def obj(room, name, cn, mats, build, loc=(0, 0, 0), rot=(0, 0, 0), status="observed", note=None, smooth_shade=False,
            floor=False, pos="observed", overlap=True):
        bm = bmesh.new()
        build(bm)
        ob = new_obj(name, bm, ROOM[room], mats, smooth_shade=smooth_shade, parent=root, props=dict(cn=cn, status=status, note=note))
        ob["room"] = room
        ob["position_status"] = pos
        if floor:
            ob["floor_item"] = True
            ob["floor_z_world"] = gz + B
            ob["overlap_check"] = overlap
        ob.location = (loc[0], loc[1], B + loc[2])
        ob.rotation_euler = rot
        return ob

    def soft(ob, w=0.04, seg=2):
        md = ob.modifiers.new("Bevel_Soft", "BEVEL")
        md.width = w
        md.segments = seg
        return ob

    def legs(bm, w, d, h, t=0.05, mi=0):
        for sx in (-1, 1):
            for sy in (-1, 1):
                bm_cube(bm, (t, t, h), loc=(sx * (w / 2 - t / 2 - 0.02), sy * (d / 2 - t / 2 - 0.02), h / 2), mi=mi)

    def chair(bm, mi=0):
        bm_cube(bm, (0.44, 0.42, 0.04), loc=(0, 0, 0.45), mi=mi)
        legs(bm, 0.44, 0.42, 0.43, 0.045, mi)
        for sx in (-1, 1):
            bm_cube(bm, (0.045, 0.045, 0.5), loc=(sx * 0.19, -0.19, 0.72), mi=mi)
        for z in (0.68, 0.92):
            bm_cube(bm, (0.42, 0.03, 0.1), loc=(0, -0.19, z), mi=mi)

    def chili_string(bm, n, mi=0, dx=0.05):
        for i in range(n):
            bm_cyl(bm, 0.045, 0.0, 0.2, loc=(math.sin(i * 1.7) * dx, math.cos(i * 1.3) * 0.04, -i * 0.1), rot=(math.pi, 0, 0), seg=6, mi=mi)

    wood_furn = mat_noise("Wood_Furniture_Brown", "#8a5a3a", "#9c6a46", scale=8)
    wood_light = mat_noise("Wood_Shelf_Light", "#c19a6b", "#d2ac7d", scale=8)
    steel = mat("Steel_Pot", "#8f969c", metal=0.7, rough=0.35)
    iron = mat("Iron_Wok", "#26272a", metal=0.5, rough=0.45)
    white = mat("Ceramic_White", "#f1efe8", rough=0.25)
    blue = mat("Paint_Kitchen_Blue", "#3f8fc0", rough=0.55)
    blue_d = mat("Paint_Kitchen_Blue_Dark", "#2f76a4", rough=0.55)
    green_furn = mat("Fabric_Armchair_Green", "#3f9a5c", rough=0.8)
    chili = MATS["Chili_Red"]
    corn_m = MATS["Corn_Yellow"]
    glow = mat("Lantern_Glow", "#ffd38a", emit="#ffb44a", emit_strength=3.0)
    lamp_metal = mat("Lantern_Metal", "#5a5f62", metal=0.6, rough=0.4)

    # =============== A. 客厅 / 厨房 / 餐厅（开放空间）x ∈ [-IN_X, PART_X]，依据 R3、R6、R8-a52/a56–a61 ===============
    kx0, kx1 = -IN_X, PART_X - 0.075

    def planks(bm, x0, x1, y0, y1, w=0.24, along="Y"):
        rr = random.Random(int(x0 * 100 + y0 * 10))
        if along == "Y":
            x = x0
            while x < x1 - 0.01:
                ww = min(w, x1 - x)
                bm_cube(bm, (ww - 0.008, y1 - y0, 0.05), loc=(x + ww / 2, (y0 + y1) / 2, -0.025), mi=rr.randrange(3))
                x += w
        else:
            y = y0
            while y < y1 - 0.01:
                ww = min(w, y1 - y)
                bm_cube(bm, (x1 - x0, ww - 0.008, 0.05), loc=((x0 + x1) / 2, y + ww / 2, -0.025), mi=rr.randrange(3))
                y += w
    floor_wood = [mat_noise(f"Wood_Floor_Plank_{i}", c1, c2, scale=8, stretch=(1.0, 0.25, 1.0)) for i, (c1, c2) in enumerate(
        (("#8a6c50", "#98795a"), ("#7c5f45", "#8b6c50"), ("#977a5c", "#a68869")))]
    obj("Kitchen", "GQ_Kitchen_Floor_Cement", "客厅/厨房灰色水泥地面", [mat_noise("Floor_Cement_Grey_Beige", "#a8a397", "#b6b1a5", scale=3, bump=0.05)],
        lambda bm: bm_cube(bm, (kx1 - kx0, 2 * IN_Y, 0.05), loc=((kx0 + kx1) / 2, 0, -0.025)), note="R3：厨房地面是灰米色、比较平整的地面，散落纸屑")
    rnd_p = random.Random(13)
    obj("Kitchen", "GQ_Kitchen_Paper_Scraps", "地上的纸屑", [mat("Paper_Scrap", "#e8e4da", rough=0.9)],
        lambda bm: [bm_cube(bm, (rnd_p.uniform(0.06, 0.14), rnd_p.uniform(0.04, 0.1), 0.003), loc=(rnd_p.uniform(-1.6, 1.0), rnd_p.uniform(-2.2, 0.0), 0.0015),
                            rot=(0, 0, rnd_p.uniform(0, 3))) for _ in range(14)], loc=(0, 0, 0), note="R3")
    # 冰箱（R3、U5）：薄荷绿双门、上冷冻下冷藏、白把手、门上纸条，顶上放纸箱
    fx, fy = 0.78, -IN_Y + 0.33

    def fridge(bm):
        ret = bmesh.ops.create_cube(bm, size=1.0)
        for v in ret["verts"]:
            v.co = Vector((v.co.x * 0.66, v.co.y * 0.6, v.co.z * 1.65 + 0.825))
        bmesh.ops.bevel(bm, geom=[e for e in bm.edges], offset=0.08, segments=3, affect="EDGES")
        bm_cube(bm, (0.64, 0.02, 0.014), loc=(0, 0.3, 1.12), mi=1)
        for z, hgt in ((1.38, 0.24), (0.8, 0.34)):
            bm_cube(bm, (0.035, 0.05, hgt), loc=(-0.25, 0.33, z), mi=2)
        bm_cube(bm, (0.12, 0.005, 0.14), loc=(0.12, 0.302, 1.35), rot=(0, 0.25, 0), mi=3)
        bm_cube(bm, (0.12, 0.005, 0.12), loc=(0.15, 0.302, 0.85), rot=(0, -0.15, 0), mi=3)
        bm_cube(bm, (0.36, 0.3, 0.22), loc=(-0.12, -0.05, 1.76), rot=(0, 0, 0.1), mi=4)
        bm_cube(bm, (0.24, 0.2, 0.3), loc=(0.17, 0.0, 1.8), mi=5)
    obj("Kitchen", "GQ_Kitchen_Fridge_Green_TwoDoor", "绿色双门冰箱（顶上放纸箱）",
        [mat("Paint_Fridge_Mint", "#7fb5a5", rough=0.45), mat("Fridge_Seam", "#5d8f80"), mat("Plastic_Handle_White", "#f0efe8", rough=0.4),
         mat("Paper_Note", "#ece6d2"), mat("Cardboard_Box_Red", "#8a3b2c", rough=0.8), mat("Cardboard_Box_Green", "#6f8a3c", rough=0.8)],
        fridge, loc=(fx, fy, 0), smooth_shade=False, floor=True, note="R3、U5：冰箱在卧室门洞旁、靠后墙")
    obj("Kitchen", "GQ_Kitchen_Clay_Jar", "陶罐", [mat_noise("Clay_Jar", "#7c6a58", "#8d7a66", scale=5)],
        lambda bm: (bm_sphere(bm, (0.2, 0.2, 0.24), loc=(0, 0, 0.24), seg=16, rings=10), bm_cyl(bm, 0.09, 0.11, 0.08, loc=(0, 0, 0.5), seg=12)),
        loc=(0.1, -IN_Y + 0.3, 0), smooth_shade=True, floor=True, note="R3：冰箱和水槽之间地上的陶罐")

    def cans(bm, n=7, seed=4):
        rr = random.Random(seed)
        for i in range(n):
            lay = i in (2, 5)
            bm_cyl(bm, 0.035, 0.035, 0.12, loc=(rr.uniform(-0.25, 0.25), rr.uniform(-0.15, 0.15), 0.035 if lay else 0.06),
                   rot=((math.pi / 2, 0, rr.uniform(0, 3)) if lay else (0, 0, 0)), seg=10, mi=i % 2)
    can_ms = [mat("Can_Red", "#c8302a", rough=0.35, metal=0.4), mat("Can_Silver", "#c9cdd2", rough=0.3, metal=0.8)]
    obj("Kitchen", "GQ_Kitchen_Cans_On_Floor", "地上的易拉罐", can_ms, cans, loc=(0.2, -1.95, 0), floor=True, overlap=False, note="R3、U5")
    # 挂墙式白色水槽 + 水龙头 + 下水管 + 墙上旧报纸（R3）
    sx = -0.5

    def sink(bm):
        bm_cube(bm, (0.62, 0.42, 0.26), loc=(0, 0, 0.0), mi=0)
        bm_cube(bm, (0.52, 0.32, 0.2), loc=(0, 0.0, 0.05), mi=3)
        bm_cyl(bm, 0.025, 0.025, 0.55, loc=(0.05, -0.05, -0.4), seg=8, mi=1)
        bm_cyl(bm, 0.015, 0.015, 0.25, loc=(0, -0.12, 0.3), seg=8, mi=1)
        bm_cyl(bm, 0.012, 0.012, 0.14, loc=(0, -0.06, 0.42), rot=(math.pi / 2, 0, 0), seg=8, mi=1)
        bm_cube(bm, (0.06, 0.03, 0.03), loc=(0, -0.17, 0.32), mi=1)
        bm_cube(bm, (0.62, 0.012, 0.5), loc=(0.05, -0.2, 0.85), rot=(0, 0.04, 0), mi=2)
        bm_cube(bm, (0.42, 0.012, 0.32), loc=(-0.15, -0.195, 0.45), rot=(0, -0.2, 0), mi=2)
    soft(obj("Kitchen", "GQ_Kitchen_Sink_WallMounted", "挂墙式白色水槽和水龙头（墙上贴旧报纸）",
             [white, steel, mat("Paper_Newspaper", "#cfccc2", rough=0.9), mat("Ceramic_Sink_Inner", "#dcdad2", rough=0.2)],
             sink, loc=(sx, -IN_Y + 0.22, 0.72), note="R3"), 0.02)
    obj("Kitchen", "GQ_Kitchen_Brick_Dado_Under_Sink", "水槽下的砖墙裙", [mat_brick("Brick_Dado_Dark", "#4c4f5a", "#585b66", "#3a3c44", scale=4.0)],
        lambda bm: bm_cube(bm, (0.9, 0.04, 0.55), loc=(0, 0, 0.275)), loc=(sx, -IN_Y + 0.02, 0), note="R3：水槽下方深色砖")
    # 圆窗下的挂杆和炊具（R3）
    obj("Kitchen", "GQ_Kitchen_Utensil_Rail", "窗下挂杆上的锅铲、勺子、杯子", [wood_furn, steel, mat("Cup_Green", "#3f8a4a", rough=0.4)],
        lambda bm: (bm_cube(bm, (0.9, 0.05, 0.05), loc=(0, 0, 0)),
                    [bm_cube(bm, (0.04, 0.01, 0.3), loc=(-0.3 + i * 0.2, 0.03, -0.17), mi=1) for i in range(3)],
                    bm_cyl(bm, 0.045, 0.04, 0.1, loc=(0.32, 0.05, -0.1), seg=10, mi=2)),
        loc=(-1.6, -IN_Y + 0.04, 1.02), note="R3")
    # 蓝色橱柜台面 + 吊柜（R3 画面右侧蓝色橱柜；R8-a57/a59：吊柜、微波炉、案板）
    cx0, cx1 = -IN_X, -2.25
    cy = -IN_Y + 0.32

    def counter(bm):
        L = cx1 - cx0
        bm_cube(bm, (L, 0.62, 0.82), loc=(0, 0, 0.41), mi=0)
        bm_cube(bm, (L + 0.04, 0.66, 0.05), loc=(0, 0.01, 0.845), mi=2)
        n = 3
        for i in range(n):
            x = -L / 2 + (i + 0.5) * L / n
            bm_cube(bm, (L / n - 0.05, 0.02, 0.6), loc=(x, 0.315, 0.42), mi=1)
            bm_cube(bm, (0.12, 0.03, 0.025), loc=(x, 0.33, 0.66), mi=3)
    obj("Kitchen", "GQ_Kitchen_Counter_Blue", "蓝色橱柜台面", [blue, blue_d, wood_light, steel], counter,
        loc=((cx0 + cx1) / 2, cy, 0), floor=True, note="R3、R8-a56")

    def wall_cab(bm):
        for xa, xb in ((-IN_X + 0.02, -3.85), (-2.95, -2.27)):
            w = xb - xa
            bm_cube(bm, (w, 0.34, 0.62), loc=((xa + xb) / 2, 0, 0), mi=0)
            for i in range(2):
                bm_cube(bm, (w / 2 - 0.03, 0.02, 0.56), loc=(xa + (i + 0.5) * w / 2, 0.18, 0), mi=1)
        for i in range(4):
            bm_sphere(bm, (0.09, 0.09, 0.05), loc=(-2.85 + i * 0.17, 0.0, 0.36), seg=10, rings=6, mi=2,
                      deform=lambda co: Vector((co.x, co.y, max(co.z, -0.2))))
    obj("Kitchen", "GQ_Kitchen_Wall_Cabinets_Blue", "蓝色吊柜（柜顶放碗）", [blue, blue_d, mat("Ceramic_Bowl", "#f2efe6", rough=0.3)],
        wall_cab, loc=(0, -IN_Y + 0.18, 1.95), status="inferred", note="R8-a57 积木有吊柜；动画画面里没拍到这一段墙")
    obj("Kitchen", "GQ_Kitchen_Microwave", "微波炉", [white, mat("Glass_Dark", "#2a3036", rough=0.2), steel],
        lambda bm: (bm_cube(bm, (0.48, 0.36, 0.28), loc=(0, 0, 0.14), mi=0), bm_cube(bm, (0.3, 0.01, 0.2), loc=(-0.06, 0.18, 0.15), mi=1),
                    bm_cube(bm, (0.08, 0.01, 0.2), loc=(0.17, 0.18, 0.15), mi=2)),
        loc=(-IN_X + 0.3, cy, 0.87), status="inferred", note="R8-a59 积木有微波炉")

    def stove(bm):
        bm_cube(bm, (0.66, 0.46, 0.08), loc=(0, 0, 0.04), mi=0)
        for x in (-0.17, 0.17):
            bm_torus(bm, 0.1, 0.015, loc=(x, 0, 0.09), seg=14, rseg=4, mi=1)
        bm_sphere(bm, (0.24, 0.24, 0.1), loc=(-0.17, 0, 0.2), seg=18, rings=8, mi=0, deform=lambda co: Vector((co.x, co.y, min(co.z, 0.0))))
        bm_cyl(bm, 0.02, 0.02, 0.25, loc=(-0.45, 0, 0.18), rot=(0, math.pi / 2, 0), seg=6, mi=2)
        bm_cyl(bm, 0.14, 0.13, 0.2, loc=(0.17, 0, 0.2), seg=14, mi=1)
        bm_cyl(bm, 0.145, 0.145, 0.02, loc=(0.17, 0, 0.31), seg=14, mi=1)
    obj("Kitchen", "GQ_Kitchen_Stove_Wok_Pot", "灶台、黑炒锅、汤锅", [iron, steel, wood_furn], stove, loc=(-3.4, cy - 0.02, 0.87), note="R8-a56：灶；U7：炒锅、汤锅")
    obj("Kitchen", "GQ_Kitchen_Stove_Hood_Pipe", "灶上铁皮烟罩和烟管（通到烟囱）", [steel],
        lambda bm: (bm_cyl(bm, 0.36, 0.08, 0.35, loc=(0, 0, 0.0), seg=12), bm_cyl(bm, 0.075, 0.075, 1.8, loc=(0, 0, 1.05), seg=10)),
        loc=(-3.4, -IN_Y + 0.4, 1.75), status="inferred", note="烟囱位置依据 R1、R2；烟罩为推测")
    obj("Kitchen", "GQ_Kitchen_CuttingBoard_Knife", "案板和菜刀", [wood_light, steel, wood_furn],
        lambda bm: (bm_cube(bm, (0.45, 0.3, 0.04), loc=(0, 0, 0.02), mi=0), bm_cube(bm, (0.2, 0.08, 0.008), loc=(0.02, 0.0, 0.05), mi=1),
                    bm_cube(bm, (0.1, 0.03, 0.025), loc=(-0.12, 0.0, 0.055), mi=2)), loc=(-2.75, cy, 0.87), note="R8-a59；U7：菜刀")
    obj("Kitchen", "GQ_Kitchen_Bowls_Cups", "碗、杯子", [mat("Ceramic_Bowl", "#f2efe6", rough=0.3), mat("Cup_Green", "#3f8a4a", rough=0.4)],
        lambda bm: ([bm_sphere(bm, (0.1, 0.1, 0.05), loc=(0, 0, 0.05 + i * 0.035), seg=12, rings=6, mi=0,
                               deform=lambda co: Vector((co.x, co.y, min(co.z, 0.0)))) for i in range(3)],
                    bm_cyl(bm, 0.04, 0.035, 0.1, loc=(0.0, 0.17, 0.05), seg=10, mi=1)), loc=(-2.42, cy - 0.05, 0.87), note="R8-a59")
    obj("Kitchen", "GQ_Kitchen_Kettle_On_Counter", "水壶", [steel],
        lambda bm: (bm_sphere(bm, (0.12, 0.12, 0.1), loc=(0, 0, 0.1), seg=14, rings=8), bm_cyl(bm, 0.015, 0.01, 0.15, loc=(0.13, 0, 0.12), rot=(0, 0.9, 0), seg=6),
                    bm_torus(bm, 0.07, 0.01, loc=(0, 0, 0.22), rot=(math.pi / 2, 0, 0), seg=12, rseg=4, arc=math.pi)),
        loc=(-3.88, cy + 0.12, 0.87 + 0.29), smooth_shade=True, note="R4/R8：水壶")
    obj("Kitchen", "GQ_Kitchen_Chili_Strings_Window", "圆窗边的红辣椒串", [chili],
        lambda bm: (chili_string(bm, 12), [bm_cyl(bm, 0.045, 0.0, 0.2, loc=(0.18 + math.sin(i * 1.3) * 0.05, 0.02, -i * 0.1), rot=(math.pi, 0, 0), seg=6) for i in range(10)]),
        loc=(-0.95, -IN_Y + 0.15, 2.8), note="R3：窗左上方挂两串辣椒")
    obj("Kitchen", "GQ_Kitchen_Corn_Hanging", "挂着的玉米", [corn_m],
        lambda bm: [bm_sphere(bm, (0.06, 0.06, 0.2), loc=(math.sin((i - 3) * 0.12) * 0.3, 0, -0.25 - abs(i - 3) * 0.03), rot=(0, (i - 3) * 0.12, 0), seg=10, rings=8)
                    for i in range(7)], loc=(-2.35, -IN_Y + 0.2, 2.85), smooth_shade=True, note="U7：窗右上挂玉米")
    # 餐桌椅（R8-a52/a61：客厅中间木桌、木椅；R3 前景木椅）
    tx, ty = -2.1, 0.55

    def table(bm):
        bm_cube(bm, (1.3, 0.8, 0.05), loc=(0, 0, 0.75), mi=0)
        legs(bm, 1.3, 0.8, 0.73, 0.07, 0)
        bm_cube(bm, (1.15, 0.05, 0.08), loc=(0, 0.33, 0.66), mi=0)
        bm_cube(bm, (1.15, 0.05, 0.08), loc=(0, -0.33, 0.66), mi=0)
    obj("Kitchen", "GQ_Dining_Table", "餐桌", [wood_furn], table, loc=(tx, ty, 0), floor=True, note="R8-a52；动画里未拍到餐桌全貌，尺寸为估算")
    chair_m = mat_noise("Wood_Chair_Reddish", "#8a5440", "#9b634c", scale=8)
    for i, (x, y, a) in enumerate(((tx - 0.35, ty - 0.68, 0.0), (tx + 0.35, ty - 0.66, 0.05), (tx, ty + 0.68, math.pi))):
        obj("Kitchen", f"GQ_Dining_Chair_{i + 1}", "木椅", [chair_m], chair, loc=(x, y, 0), rot=(0, 0, a), floor=True, note="R3 前景木椅")
    obj("Kitchen", "GQ_Dining_Table_Items", "桌上的暖水瓶、啤酒瓶、碗和筷子",
        [mat("Thermos_Red", "#c23a2c", rough=0.4), mat("Glass_Beer_Green", "#2f6e3a", rough=0.15, transmission=0.3), mat("Ceramic_Bowl", "#f2efe6", rough=0.3), wood_light],
        lambda bm: (bm_cyl(bm, 0.07, 0.07, 0.36, loc=(-0.4, 0.15, 0.18), seg=12, mi=0), bm_cyl(bm, 0.04, 0.03, 0.06, loc=(-0.4, 0.15, 0.39), seg=10, mi=0),
                    [(bm_cyl(bm, 0.035, 0.035, 0.18, loc=(0.25 + k * 0.1, 0.18, 0.09), seg=10, mi=1),
                      bm_cyl(bm, 0.012, 0.015, 0.08, loc=(0.25 + k * 0.1, 0.18, 0.22), seg=8, mi=1)) for k in range(2)],
                    bm_sphere(bm, (0.11, 0.11, 0.05), loc=(0.0, -0.12, 0.05), seg=12, rings=6, mi=2, deform=lambda co: Vector((co.x, co.y, min(co.z, 0.0)))),
                    [bm_cube(bm, (0.008, 0.22, 0.008), loc=(0.15 + k * 0.02, -0.12, 0.01), mi=3) for k in range(2)]),
        loc=(tx, ty, 0.775), note="R8-a61：桌上暖水瓶")
    obj("Kitchen", "GQ_Dining_Ceiling_Lamp", "餐桌上方吊灯", [lamp_metal, glow],
        lambda bm: (bm_cyl(bm, 0.008, 0.008, 0.9, loc=(0, 0, 0.45), seg=4, mi=0), bm_cyl(bm, 0.26, 0.04, 0.14, loc=(0, 0, -0.04), seg=16, mi=0),
                    bm_sphere(bm, (0.06, 0.06, 0.06), loc=(0, 0, -0.1), seg=10, rings=6, mi=1)), loc=(tx, ty, 2.55), status="inferred")
    # 入口东侧小柜：篮子、南瓜（R8-a61：入口小柜和篮子）；门边墙上马灯（R3）
    obj("Kitchen", "GQ_Entrance_Small_Cabinet_Basket", "入口小柜和篮子", [wood_furn, mat_noise("Wicker_Basket", "#b88a4a", "#c99b58", scale=20)],
        lambda bm: (bm_cube(bm, (0.6, 0.45, 0.78), loc=(0, 0, 0.39), mi=0), bm_cube(bm, (0.26, 0.02, 0.5), loc=(-0.14, 0.235, 0.4), mi=0),
                    bm_cube(bm, (0.26, 0.02, 0.5), loc=(0.14, 0.235, 0.4), mi=0),
                    bm_cyl(bm, 0.17, 0.13, 0.16, loc=(0.0, 0, 0.86), seg=14, mi=1),
                    bm_torus(bm, 0.14, 0.012, loc=(0, 0, 0.98), rot=(math.pi / 2, 0, 0), seg=14, rseg=4, mi=1, arc=math.pi)),
        loc=(0.86, IN_Y - 0.25, 0), rot=(0, 0, math.pi), floor=True, status="observed", pos="inferred", note="R8-a61 积木")
    obj("Kitchen", "GQ_Lantern_Bracket_BedroomDoor", "卧室门边墙上的马灯", [lamp_metal, glow, mat("Copper_Dish", "#b7643a", metal=0.6, rough=0.4)],
        lambda bm: (bm_cube(bm, (0.3, 0.03, 0.03), loc=(-0.15, 0, 0.3), mi=0), bm_cyl(bm, 0.12, 0.1, 0.06, loc=(-0.25, 0, -0.05), seg=12, mi=2),
                    bm_cyl(bm, 0.07, 0.07, 0.18, loc=(-0.25, 0, 0.09), seg=10, mi=1), bm_cyl(bm, 0.08, 0.03, 0.06, loc=(-0.25, 0, 0.21), seg=10, mi=0)),
        loc=(PART_X - 0.09, -1.0, 1.6), note="R3：卧室门洞左边挂马灯")
    pump = mat("Pumpkin_Orange", "#d9822b", rough=0.6)
    obj("Kitchen", "GQ_Kitchen_Log_Slice_Table", "树墩切片矮桌（上面一个南瓜）", [MATS.get("Bark_Log") or mat_noise("Bark_Log", "#5d3f2a", "#7b573c", scale=6),
                                                                      MATS["Wood_Cut_End"], pump],
        lambda bm: (bm_cyl(bm, 0.5, 0.52, 0.42, loc=(0, 0, 0.21), seg=20, mi=0), bm_cyl(bm, 0.49, 0.49, 0.01, loc=(0, 0, 0.425), seg=20, mi=1),
                    bm_sphere(bm, (0.17, 0.17, 0.13), loc=(-0.1, 0.05, 0.55), seg=14, rings=8, mi=2)),
        loc=(0.65, 0.1, 0), floor=True, pos="inferred", note="R3：画面左前方一块树墩切片当桌子，上面放南瓜")
    obj("Kitchen", "GQ_Kitchen_Pumpkins", "南瓜", [pump, mat("Pumpkin_Stem", "#5a6a2a")],
        lambda bm: (bm_sphere(bm, (0.2, 0.2, 0.15), loc=(0, 0, 0.15), seg=14, rings=8), bm_cyl(bm, 0.02, 0.02, 0.06, loc=(0, 0, 0.32), seg=6, mi=1),
                    bm_sphere(bm, (0.14, 0.14, 0.11), loc=(0.3, 0.2, 0.11), seg=14, rings=8)),
        loc=(0.6, -0.95, 0), smooth_shade=True, floor=True, note="R3：地上南瓜")
    # 西北角烧水炉 + 柴火（R8 文字：客厅进门角落有烧水炉）；西墙碗柜（U4）；西墙碗架（U7）
    obj("Kitchen", "GQ_Living_Kettle_Stove", "烧水炉（铁炉、水壶、烟管）", [iron, steel],
        lambda bm: (bm_cyl(bm, 0.27, 0.27, 0.62, loc=(0, 0, 0.36), seg=16, mi=0), legs(bm, 0.4, 0.4, 0.06, 0.05, 0),
                    bm_cyl(bm, 0.29, 0.29, 0.04, loc=(0, 0, 0.69), seg=16, mi=0),
                    bm_sphere(bm, (0.15, 0.15, 0.12), loc=(0.05, 0, 0.82), seg=14, rings=8, mi=1),
                    bm_cyl(bm, 0.02, 0.012, 0.16, loc=(0.2, 0, 0.84), rot=(0, 0.9, 0), seg=6, mi=1),
                    bm_tube(bm, [(-0.12, 0, 0.6), (-0.12, 0, 2.3), (-0.3, 0, 2.6), (-0.3, 0, 3.4)], [0.06] * 4, seg=10, mi=0)),
        loc=(-IN_X + 0.4, IN_Y - 0.42, 0), floor=True, status="observed", pos="inferred", note="R8 文字：进门角落的烧水炉（授权积木依据）")
    obj("Kitchen", "GQ_Living_Firewood_Stack", "柴火堆", [MATS.get("Bark_Log") or mat_noise("Bark_Log", "#5d3f2a", "#7b573c", scale=6)],
        lambda bm: [bm_cyl(bm, 0.07, 0.07, 0.55, loc=(-0.24 + i * 0.15 + row * 0.07, 0, 0.07 + row * 0.13), rot=(math.pi / 2, 0, 0), seg=8)
                    for row in range(3) for i in range(4 - row)], loc=(-3.15, IN_Y - 0.32, 0), floor=True, note="U3：门内柴火")

    def cupboard(bm):
        bm_cube(bm, (1.0, 0.5, 1.7), loc=(0, 0, 0.85), mi=0)
        for x in (-0.25, 0.25):
            bm_cube(bm, (0.46, 0.03, 1.0), loc=(x, 0.26, 1.05), mi=1)
            bm_cube(bm, (0.46, 0.03, 0.4), loc=(x, 0.26, 0.3), mi=1)
    obj("Kitchen", "GQ_Living_Cupboard", "碗柜", [mat_noise("Wood_Cupboard", "#c9a77a", "#d6b88c", scale=8), mat_noise("Wood_Cupboard_Door", "#b8956a", "#c9a77a", scale=8)],
        cupboard, loc=(-IN_X + 0.26, 1.3, 0), rot=(0, 0, -math.pi / 2), floor=True, pos="inferred", note="U4：碗柜；位置为推测")

    def wall_shelf(bm):
        for z in (0.0, 0.45):
            bm_cube(bm, (1.0, 0.26, 0.04), loc=(0, 0, z), mi=0)
        for i in range(4):
            bm_sphere(bm, (0.09, 0.09, 0.055), loc=(-0.35 + i * 0.23, 0, 0.075), seg=10, rings=6, mi=1, deform=lambda co: Vector((co.x, co.y, max(co.z, -0.2))))
        for i in range(3):
            bm_cyl(bm, 0.04, 0.035, 0.1, loc=(-0.3 + i * 0.25, 0, 0.52), seg=10, mi=2)
        for i in range(8):
            bm_sphere(bm, (0.05, 0.05, 0.045), loc=(0.42, 0.05, -0.05 - i * 0.08), seg=8, rings=5, mi=3)
    obj("Kitchen", "GQ_Living_Wall_Shelf_Bowls_Cups", "墙上碗架（碗、杯子、蒜辫）",
        [wood_light, mat("Ceramic_Bowl", "#f2efe6", rough=0.3), mat("Cup_Green", "#3f8a4a", rough=0.4), mat("Garlic_White", "#ece6da", rough=0.6)],
        wall_shelf, loc=(-IN_X + 0.15, -1.55, 1.55), rot=(0, 0, -math.pi / 2), pos="inferred", note="U7：碗架、蒜头")
    DOOR_PASSAGES.append(("卧室门", "GQ_House_Root", (PART_X - 0.5, PART_X + 0.5, BED_DOOR[0] + 0.15, BED_DOOR[1] - 0.1, B + 0.05, B + 1.9)))
    DOOR_PASSAGES.append(("卫生间门", "GQ_House_Root", (-W_HOUSE / 2 - 0.5, -W_HOUSE / 2 + 0.5, BATH_DOOR[0] + 0.1, BATH_DOOR[1] - 0.15, B + 0.05, B + 1.9)))

    # =============== B. 卧室（隔墙东侧）依据 R4、E44、R8-a62–a68 ===============
    bx0, bx1 = PART_X + 0.075, IN_X
    obj("Bedroom", "GQ_Bedroom_Floor_StoneTiles", "卧室方形石板地面", [mat_stone_floor()],
        lambda bm: bm_cube(bm, (bx1 - bx0, 2 * IN_Y, 0.05), loc=((bx0 + bx1) / 2, 0, -0.025)), note="R4、E44：方形石板地")
    # 卧室门：绿色门框、红色格子门扇，开向卧室（R3 左侧门洞）
    bm = bmesh.new()
    for y in BED_DOOR:
        bm_cube(bm, (0.24, 0.1, 2.1), loc=(PART_X, y + math.copysign(0.05, y - sum(BED_DOOR) / 2), B + 1.05))
    bm_cube(bm, (0.24, BED_DOOR[1] - BED_DOOR[0] + 0.2, 0.1), loc=(PART_X, sum(BED_DOOR) / 2, B + 2.1))
    ob = new_obj("GQ_Bedroom_Door_Frame_Green", bm, ROOM["Bedroom"], [MATS["Paint_Door_Frame_Green"]], parent=root,
                 props=dict(cn="卧室门绿色门框", status="observed", note="R3"))
    dwb = BED_DOOR[1] - BED_DOOR[0] - 0.04

    def bed_door(bm):
        bm_cube(bm, (0.05, dwb, 0.95), loc=(0, dwb / 2, 0.48), mi=0)
        for z in (1.0, 2.0):
            bm_cube(bm, (0.06, dwb, 0.07), loc=(0, dwb / 2, z), mi=1)
        for y in (0.03, dwb - 0.03):
            bm_cube(bm, (0.06, 0.07, 1.05), loc=(0, y, 1.5), mi=1)
        bm_cube(bm, (0.015, dwb - 0.06, 1.0), loc=(0, dwb / 2, 1.5), mi=2)
        for t in (0.25, 0.5, 0.75):
            bm_cube(bm, (0.05, 0.03, 1.0), loc=(0, dwb * t, 1.5), mi=1)
        for z in (1.25, 1.5, 1.75):
            bm_cube(bm, (0.05, dwb - 0.06, 0.03), loc=(0, dwb / 2, z), mi=1)
        for xx in (-0.03, 0.03):
            old = set(bm.verts)
            paper_cut(bm, 0.0, r=0.16, mi=3)
            bmesh.ops.transform(bm, matrix=Matrix.Translation((xx, dwb / 2, 1.5)) @ Matrix.Rotation(math.pi / 2, 4, "Z"),
                                verts=[v for v in bm.verts if v not in old])
    bm = bmesh.new()
    bed_door(bm)
    ob = new_obj("GQ_Bedroom_Door_Leaf_RedLattice", bm, ROOM["Bedroom"], [mat("Wood_Door_Pink_Red", "#a8574c", rough=0.7),
                                                                            mat("Wood_Lattice_Red", "#8e3a30", rough=0.6), MATS["Paper_Window_Lattice"],
                                                                            MATS["Paper_Red_Cut"]],
                 parent=root, props=dict(cn="卧室红色格子门（已打开，开向卧室）", status="observed", note="R3：门洞里红色格子门、贴红窗花"))
    ob.location = (PART_X + 0.08, BED_DOOR[0] + 0.02, B)
    ob.rotation_euler = (0, 0, math.radians(-90))
    # 土炕（R4：窗下，砖砌炕身，前面两级砖台阶；被子是叠好的格子被）
    k0, k1, ky0 = 2.2, IN_X, 1.2
    brick_k = mat_brick("Brick_Kang_Tan", "#b48a5e", "#a27a50", "#7e6a55", scale=2.6)

    def kang(bm):
        bm_cube(bm, (k1 - k0, IN_Y - ky0, 0.6), loc=(0, 0, 0.3), mi=0)
        bm_cube(bm, (k1 - k0 + 0.02, 0.1, 0.08), loc=(0, -(IN_Y - ky0) / 2 + 0.05, 0.64), mi=1)
        bm_cube(bm, (k1 - k0 - 0.1, IN_Y - ky0 - 0.1, 0.02), loc=(0, 0.05, 0.61), mi=2)
    obj("Bedroom", "GQ_Bedroom_Kang_Brick", "土炕（砖砌炕身、炕沿、炕席）",
        [brick_k, mat_noise("Wood_Kang_Edge", "#6b4a34", "#7d5940", scale=8), mat_stripes("Bamboo_Mat", "#c7b36a", "#a8934e", scale=60, axis="X")],
        kang, loc=((k0 + k1) / 2, (IN_Y + ky0) / 2, 0), floor=True, note="R4：窗下土炕、砖砌；U6：竹席")
    obj("Bedroom", "GQ_Bedroom_Kang_Steps", "炕前两级砖台阶", [brick_k],
        lambda bm: [bm_cube(bm, (0.9, 0.3, h), loc=(0, -0.15 - i * 0.3, h / 2)) for i, h in enumerate((0.4, 0.2))],
        loc=(3.12, ky0, 0), floor=True, note="R4：炕前砖台阶")
    plaid = mat_checker("Fabric_Quilt_Plaid_Purple", "#5e3f62", "#b8a4b6", scale=14)
    obj("Bedroom", "GQ_Bedroom_Kang_Quilt_Folded", "叠好的格子被", [plaid, mat_quilt()],
        lambda bm: (bm_cube(bm, (0.9, 0.55, 0.12), loc=(0, 0, 0.06), mi=0), bm_cube(bm, (0.88, 0.53, 0.12), loc=(0.01, 0, 0.18), mi=0),
                    bm_cube(bm, (0.86, 0.52, 0.11), loc=(0, 0, 0.295), mi=1)), loc=(k1 - 0.55, IN_Y - 0.45, 0.62), note="R4：炕上叠着紫色格子被；U6 蓝花被")
    obj("Bedroom", "GQ_Bedroom_Kang_Pillow", "枕头", [mat("Fabric_Pillow_Red", "#8e2f2a", rough=0.85)],
        lambda bm: bm_cube(bm, (0.32, 0.6, 0.16), loc=(0, 0, 0.08)), loc=(k1 - 0.25, 1.75, 0.62), note="U6；E44：枕头一头靠墙")
    obj("Bedroom", "GQ_Bedroom_Kang_Tea_Table", "炕桌、白茶壶、茶杯", [wood_furn, white],
        lambda bm: (bm_cube(bm, (0.8, 0.45, 0.04), loc=(0, 0, 0.3), mi=0), legs(bm, 0.8, 0.45, 0.28, 0.05, 0),
                    bm_sphere(bm, (0.11, 0.11, 0.1), loc=(-0.15, 0, 0.42), seg=14, rings=8, mi=1),
                    bm_cyl(bm, 0.03, 0.04, 0.05, loc=(-0.15, 0, 0.53), seg=10, mi=1),
                    bm_cyl(bm, 0.015, 0.01, 0.12, loc=(-0.03, 0, 0.44), rot=(0, 0.9, 0), seg=6, mi=1),
                    [bm_cyl(bm, 0.03, 0.025, 0.05, loc=(0.1 + k * 0.09, 0.05, 0.345), seg=10, mi=1) for k in range(3)]),
        loc=(2.9, IN_Y - 0.35, 0.62), smooth_shade=False, note="R4：窗前炕桌上白茶壶、茶杯")
    obj("Bedroom", "GQ_Bedroom_Slippers", "炕台阶上的拖鞋", [mat("Rubber_Slipper_Brown", "#6a4a2a", rough=0.6)],
        lambda bm: (bm_cube(bm, (0.11, 0.26, 0.04), loc=(-0.08, 0, 0.02)), bm_cube(bm, (0.11, 0.26, 0.04), loc=(0.1, 0.03, 0.02))),
        loc=(3.0, ky0 - 0.15, 0.4), note="R4：台阶上的拖鞋")
    # 炕边铁炉 + 水壶 + 烟管（R4）
    obj("Bedroom", "GQ_Bedroom_Iron_Stove_Kettle", "炕边铁炉、水壶和烟管", [iron, steel],
        lambda bm: (bm_cyl(bm, 0.3, 0.28, 0.72, loc=(0, 0, 0.4), seg=16, mi=0), legs(bm, 0.4, 0.4, 0.06, 0.05, 0),
                    bm_cyl(bm, 0.32, 0.32, 0.04, loc=(0, 0, 0.78), seg=16, mi=0),
                    bm_sphere(bm, (0.17, 0.17, 0.12), loc=(0.03, 0, 0.92), seg=14, rings=8, mi=1),
                    bm_cyl(bm, 0.02, 0.012, 0.18, loc=(0.2, 0, 0.95), rot=(0, 0.9, 0), seg=6, mi=1),
                    bm_tube(bm, [(-0.12, -0.05, 0.75), (-0.12, -0.05, 3.6)], [0.06, 0.06], seg=10, mi=0)),
        loc=(1.82, IN_Y - 0.55, 0), floor=True, note="R4：炕边带烟管的铁炉，上面坐着水壶")
    # 床头柜 + 绿色电话、水杯（E44）；炕头墙上日历、旧衣服、辣椒串、蒜辫（E44）
    obj("Bedroom", "GQ_Bedroom_Bedside_Table_Phone", "床头柜、绿色电话和水杯",
        [wood_furn, mat("Phone_Teal", "#3e9a86", rough=0.4), mat("Glass_Cup", "#d8e6ea", rough=0.1, transmission=0.6)],
        lambda bm: (bm_cube(bm, (0.45, 0.42, 0.55), loc=(0, 0, 0.275), mi=0), bm_cube(bm, (0.22, 0.17, 0.08), loc=(-0.05, 0, 0.59), mi=1),
                    bm_cube(bm, (0.2, 0.05, 0.05), loc=(-0.05, -0.04, 0.655), rot=(0.4, 0, 0), mi=1),
                    bm_cyl(bm, 0.035, 0.03, 0.11, loc=(0.13, 0.08, 0.605), seg=10, mi=2)),
        loc=(IN_X - 0.25, ky0 - 0.32, 0), floor=True, status="observed", pos="inferred", note="E44：炕头边的绿色电话和水杯；R8-a64 积木床头柜")
    ew = IN_X - 0.03
    obj("Bedroom", "GQ_Bedroom_Wall_Calendar_Clothes", "炕头墙上的日历和旧衣服",
        [mat_noise("Wood_Calendar_Board", "#9b7a52", "#ab8a60", scale=8), mat("Paper_Calendar", "#efe8d6"), mat_noise("Fabric_Old_Grey", "#9aa0a6", "#b0b5ba", scale=12)],
        lambda bm: (bm_cube(bm, (0.03, 0.42, 0.55), loc=(0, -0.5, 0), mi=0), bm_cube(bm, (0.012, 0.36, 0.4), loc=(-0.02, -0.5, -0.04), mi=1),
                    bm_cube(bm, (0.06, 0.42, 0.9), loc=(-0.02, 0.35, -0.05), mi=2), bm_cube(bm, (0.05, 0.12, 0.8), loc=(-0.02, 0.09, -0.03), mi=2),
                    bm_cube(bm, (0.05, 0.12, 0.8), loc=(-0.02, 0.61, -0.03), mi=2)),
        loc=(ew, 1.75, 1.75), note="E44：炕头那面墙挂日历、旧衣服")
    obj("Bedroom", "GQ_Bedroom_Wall_Chili_Garlic", "炕头墙上的辣椒串和蒜辫", [chili, mat("Garlic_White", "#ece6da", rough=0.6)],
        lambda bm: (chili_string(bm, 13), [bm_sphere(bm, (0.06, 0.06, 0.055), loc=(math.sin(i * 2.1) * 0.03, 0.35, -i * 0.11), seg=10, rings=6, mi=1) for i in range(11)]),
        loc=(ew - 0.05, 0.45, 2.55), note="E44")
    # 绿色单人沙发朝电视，红地毯（R4）
    soft(obj("Bedroom", "GQ_Bedroom_Armchair_Green", "绿色单人沙发", [green_furn],
             lambda bm: (bm_cube(bm, (0.8, 0.78, 0.42), loc=(0, 0, 0.21)), bm_cube(bm, (0.8, 0.2, 0.62), loc=(0, -0.3, 0.72)),
                         [bm_cube(bm, (0.17, 0.78, 0.26), loc=(sx * 0.36, 0, 0.55)) for sx in (-1, 1)]),
             loc=(2.3, -0.55, 0), rot=(0, 0, -math.pi / 2), floor=True, note="R4：绿沙发放在红地毯上，对着电视"), 0.06, 3)
    obj("Bedroom", "GQ_Bedroom_Rug_Red", "红地毯", [mat_noise("Fabric_Rug_Red", "#b8473a", "#c85a48", scale=14)],
        lambda bm: bm_cube(bm, (2.0, 1.4, 0.015), loc=(0, 0, 0.0075)), loc=(3.0, -0.55, 0), floor=True, overlap=False, note="R4")
    obj("Bedroom", "GQ_Bedroom_TV_On_Stand", "木架上的老电视", [wood_furn, mat("Plastic_TV_Red", "#8a3a33", rough=0.5), mat("Screen_TV", "#3a4a46", emit="#8fb8a8", emit_strength=0.4), steel],
        lambda bm: (bm_cube(bm, (0.5, 0.75, 0.04), loc=(0, 0, 0.55), mi=0), legs(bm, 0.5, 0.75, 0.53, 0.05, 0),
                    bm_cube(bm, (0.45, 0.6, 0.48), loc=(0.02, 0, 0.81), mi=1), bm_cube(bm, (0.02, 0.48, 0.36), loc=(-0.215, -0.03, 0.82), mi=2),
                    bm_cyl(bm, 0.006, 0.006, 0.45, loc=(0.05, 0.12, 1.2), rot=(0.4, 0, 0), seg=4, mi=3),
                    bm_cyl(bm, 0.006, 0.006, 0.45, loc=(0.05, -0.12, 1.2), rot=(-0.4, 0, 0), seg=4, mi=3)),
        loc=(IN_X - 0.3, -0.55, 0), floor=True, note="R4：木架上的红色老电视，带天线")
    obj("Bedroom", "GQ_Bedroom_Cans", "电视边的易拉罐", can_ms, lambda bm: cans(bm, 5, 8), loc=(3.7, 0.4, 0), floor=True, overlap=False, note="R4")
    # 衣柜（推测）、红木箱（E44）
    obj("Bedroom", "GQ_Bedroom_Wardrobe", "衣柜（推测）", [mat_noise("Wood_Wardrobe", "#9a6a44", "#a97a52", scale=8), wood_furn],
        lambda bm: (bm_cube(bm, (1.15, 0.55, 1.95), loc=(0, 0, 0.975), mi=0),
                    [bm_cube(bm, (0.54, 0.02, 1.7), loc=(sx * 0.285, 0.285, 1.0), mi=1) for sx in (-1, 1)],
                    [bm_cube(bm, (0.03, 0.03, 0.2), loc=(sx * 0.04, 0.3, 1.05), mi=0) for sx in (-1, 1)]),
        loc=(3.05, -IN_Y + 0.3, 0), floor=True, status="inferred", pos="inferred", note="剧照里没有衣柜；按本轮要求补做，标为推测")
    obj("Bedroom", "GQ_Bedroom_Chest_Red", "红棕色木箱", [mat_noise("Wood_Chest_Red", "#7a3328", "#8c3e30", scale=8), steel],
        lambda bm: (bm_cube(bm, (0.7, 0.42, 0.48), loc=(0, 0, 0.24), mi=0), bm_cube(bm, (0.08, 0.02, 0.06), loc=(0, 0.22, 0.38), mi=1)),
        loc=(IN_X - 0.24, -IN_Y + 0.5, 0), rot=(0, 0, math.pi / 2), floor=True, pos="inferred", note="E44：红棕色木箱；R4 左下角也有红箱子")
    # 隔墙一侧（A65：带抽屉的书桌，桌上两根支架托着老式喇叭口火枪，旁边子弹、红书、小马灯；墙上弓、相框、旧报纸；
    # 绿沙发背后玻璃门书柜。R4：书桌在画面左前方，飞镖靶在左墙更靠里）
    def desk(bm):
        bm_cube(bm, (0.5, 1.1, 0.05), loc=(0, 0, 0.745), mi=0)
        for yy in (-0.53, 0.53):
            bm_cube(bm, (0.46, 0.04, 0.72), loc=(0, yy, 0.36), mi=0)
        bm_cube(bm, (0.04, 1.02, 0.6), loc=(-0.22, 0, 0.42), mi=0)
        for yy in (-0.26, 0.26):
            bm_cube(bm, (0.03, 0.48, 0.2), loc=(0.24, yy, 0.6), mi=1)
            bm_sphere(bm, (0.025, 0.025, 0.025), loc=(0.265, yy, 0.6), seg=8, rings=4, mi=2)
        bm_cube(bm, (0.03, 1.02, 0.04), loc=(0.24, 0, 0.12), mi=0)
    obj("Bedroom", "GQ_Bedroom_Desk_Drawers", "带抽屉的木书桌", [wood_furn, mat_noise("Wood_Desk_Drawer", "#7d5236", "#8d603f", scale=8), MATS["Steel_Pot"]],
        desk, loc=(bx0 + 0.25, -0.05, 0), floor=True, pos="inferred", note="A65：带两个抽屉的木书桌，旁边是绿沙发；靠哪面墙依据 R4 左前方的桌子推测")

    def gun(bm):
        for yy in (-0.22, 0.18):
            bm_cyl(bm, 0.05, 0.06, 0.01, loc=(0, yy, 0.005), seg=10, mi=1)
            bm_cyl(bm, 0.012, 0.012, 0.26, loc=(0, yy, 0.135), seg=6, mi=1)
            bm_cube(bm, (0.05, 0.02, 0.03), loc=(0, yy, 0.27), mi=1)
        bm_tube(bm, [(0, -0.48, 0.25), (0, -0.3, 0.29), (0, -0.12, 0.3)], [0.045, 0.035, 0.03], seg=8, mi=0)
        bm_tube(bm, [(0, -0.12, 0.3), (0, 0.3, 0.3), (0, 0.42, 0.3)], [0.022, 0.024, 0.028], seg=10, mi=1)
        bm_cyl(bm, 0.028, 0.06, 0.1, loc=(0, 0.47, 0.3), rot=(-math.pi / 2, 0, 0), seg=14, mi=1)
        bm_torus(bm, 0.03, 0.008, loc=(0, -0.2, 0.25), rot=(0, math.pi / 2, 0), seg=10, rseg=4, mi=1)
    obj("Bedroom", "GQ_Bedroom_Blunderbuss_On_Stands", "书桌上支架托着的老式喇叭口火枪", [mat_noise("Wood_Gun_Stock", "#7a3f26", "#8c4a2e", scale=10), MATS["Steel_Pot"]],
        gun, loc=(bx0 + 0.3, -0.05, 0.77), note="A65：枪托红棕色木头、枪管银灰色、枪口喇叭形，架在两根金属支架上")
    brass = mat("Brass_Cartridge", "#d0a040", metal=0.8, rough=0.3)
    obj("Bedroom", "GQ_Bedroom_Desk_Items", "书桌上的子弹、红书、小马灯", [brass, mat("Book_Red_Cover", "#a8302a", rough=0.6), mat("Paper_Book_Edge", "#efe6d0"),
                                                               MATS["Lantern_Metal"], MATS["Lantern_Glow"]],
        lambda bm: ([bm_cyl(bm, 0.012, 0.012, 0.07, loc=(0.05 + (k % 2) * 0.03, -0.42 + k * 0.035, 0.035), seg=8, mi=0) for k in range(4)],
                    bm_cube(bm, (0.2, 0.28, 0.035), loc=(0.02, 0.3, 0.018), rot=(0, 0, 0.1), mi=1), bm_cube(bm, (0.19, 0.26, 0.035), loc=(0.03, 0.31, 0.053), rot=(0, 0, -0.05), mi=1),
                    bm_cube(bm, (0.18, 0.005, 0.03), loc=(0.03, 0.18, 0.053), mi=2),
                    bm_cyl(bm, 0.05, 0.05, 0.02, loc=(-0.12, -0.55, 0.01), seg=10, mi=3), bm_cyl(bm, 0.04, 0.04, 0.1, loc=(-0.12, -0.55, 0.07), seg=10, mi=4),
                    bm_cyl(bm, 0.05, 0.015, 0.04, loc=(-0.12, -0.55, 0.14), seg=10, mi=3)),
        loc=(bx0 + 0.25, -0.05, 0.77), note="A65：铜色子弹、两本红书、桌角小马灯")
    obj("Bedroom", "GQ_Bedroom_Wall_Bow", "墙上挂的弓", [mat_noise("Wood_Bow", "#c89a5a", "#d8aa6a", scale=10), mat("Bow_String", "#e8e0d0")],
        lambda bm: (bm_torus(bm, 0.7, 0.018, loc=(0, 0, 0), rot=(0, math.pi / 2, 0), seg=20, rseg=5, mi=0, arc=1.6, scale=(1, 1, 1)),
                    bm_cyl(bm, 0.003, 0.003, 1.0, loc=(0, 0.0, 0.0), seg=4, mi=1)),
        loc=(bx0 + 0.04, -0.5, 1.75), rot=(0, 0, 0), note="A65：书桌上方墙上挂着弓")
    obj("Bedroom", "GQ_Bedroom_Portrait_Frame", "相框", [wood_furn, mat("Photo_Sepia", "#c9a97a")],
        lambda bm: (bm_cube(bm, (0.03, 0.42, 0.5), loc=(0, 0, 0), mi=0), bm_cube(bm, (0.012, 0.34, 0.42), loc=(0.02, 0, 0), mi=1)),
        loc=(bx0 + 0.03, 0.05, 1.95), note="A65：书桌上方的相框")
    obj("Bedroom", "GQ_Bedroom_Wall_Newspaper", "墙上的旧报纸", [mat("Paper_Newspaper", "#cfccc2", rough=0.9)],
        lambda bm: bm_cube(bm, (0.01, 0.42, 0.55), loc=(0, 0, 0), rot=(0.12, 0, 0)), loc=(bx0 + 0.02, 0.45, 1.55), note="A65：相框右下方贴着旧报纸")
    glass = mat("Glass_Bookcase", "#cfe2e8", rough=0.05, transmission=0.85)

    def bookcase(bm):
        bm_cube(bm, (0.4, 0.62, 1.8), loc=(0, 0, 0.9), mi=0)
        bm_cube(bm, (0.02, 0.52, 1.0), loc=(0.205, 0, 1.25), mi=1)
        for z in (0.85, 1.25, 1.62):
            bm_cube(bm, (0.36, 0.56, 0.02), loc=(0.0, 0, z), mi=0)
        for k in range(8):
            bm_cube(bm, (0.24, 0.05, rnd_b.uniform(0.22, 0.32)), loc=(0.0, -0.22 + k * 0.06, 0.86 + 0.14), mi=2 + k % 2)
    rnd_b = random.Random(8)
    obj("Bedroom", "GQ_Bedroom_Glass_Bookcase", "玻璃门书柜", [wood_light, glass, mat("Book_Grey", "#8a8a90"), mat("Book_Red", "#8a3a2a")], bookcase,
        loc=(bx0 + 0.2, -0.95, 0), floor=True, pos="inferred", note="A65：绿沙发背后有一个玻璃门书柜")
    obj("Bedroom", "GQ_Bedroom_Dartboard", "飞镖靶", [wood_light, mat("Target_Red", "#b83228"), white],
        lambda bm: (bm_cube(bm, (0.03, 0.42, 0.5), loc=(0, 0, 0), mi=0),
                    [bm_cyl(bm, r, r, 0.012, loc=(0.02 + k * 0.003, 0, 0), rot=(0, math.pi / 2, 0), seg=20, mi=1 + k % 2) for k, r in enumerate((0.17, 0.13, 0.09, 0.05))]),
        loc=(bx0 + 0.03, 1.25, 1.6), pos="inferred", note="R4：画面左墙上的飞镖靶，比书桌更靠里")
    obj("Bedroom", "GQ_Bedroom_Hanging_Lamp_Green", "绿色灯罩吊灯", [mat("Lamp_Shade_Green", "#3f7a62", rough=0.4), glow, lamp_metal],
        lambda bm: (bm_cyl(bm, 0.006, 0.006, 0.9, loc=(0, 0, 0.45), seg=4, mi=2),
                    bm_sphere(bm, (0.26, 0.26, 0.12), loc=(0, 0, 0), seg=16, rings=8, mi=0, deform=lambda co: Vector((co.x, co.y, max(co.z, 0.0)))),
                    bm_sphere(bm, (0.06, 0.06, 0.06), loc=(0, 0, -0.02), seg=10, rings=6, mi=1)), loc=(3.0, 0.3, 2.6), note="R4：天花板吊下的绿色灯罩")
    obj("Bedroom", "GQ_Bedroom_Window_Curtains", "卧室窗帘（推测）", [mat_noise("Fabric_Curtain_Floral", "#c8b07a", "#b89a62", scale=12), wood_furn],
        lambda bm: (bm_cyl(bm, 0.015, 0.015, 1.7, loc=(0, 0, 0.0), rot=(0, math.pi / 2, 0), seg=6, mi=1),
                    [bm_cyl(bm, 0.035, 0.045, 1.05, loc=(sx * (0.66 + k * 0.06), 0.0, -0.53), seg=8, mi=0) for sx in (-1, 1) for k in range(4)]),
        loc=(sum(WIN_FRONT[1]) / 2, IN_Y - 0.06, WIN_Z[1] + 0.12), smooth_shade=True, status="inferred", note="剧照里没看到窗帘，按要求补做，收在两侧")

    # =============== C. 卫生间（侧翼，单独的墙和门）依据 R5、R8 文字 ===============
    wx0, wx1, wy0, wy1 = WING["x0"] + 0.155, -W_HOUSE / 2 - 0.155, WING["y0"] + 0.155, WING["y1"] - 0.155
    floor_bath = [mat_noise(f"Wood_Floor_Bathroom_{i}", c1, c2, scale=8, stretch=(1.0, 0.25, 1.0)) for i, (c1, c2) in enumerate(
        (("#b9996e", "#c8a87c"), ("#a8885e", "#b7976c"), ("#c2a57c", "#d0b38a")))]
    obj("Bathroom", "GQ_Bathroom_Floor_Planks", "卫生间木地板", floor_bath, lambda bm: planks(bm, wx0, wx1, wy0, wy1, along="X"), note="R5：浅木色地面")
    bm = bmesh.new()
    dwb2 = BATH_DOOR[1] - BATH_DOOR[0] - 0.04
    bm_cube(bm, (0.04, dwb2, 2.0), loc=(0, -dwb2 / 2, 1.0), mi=0)
    for z in (0.35, 1.0, 1.65):
        bm_cube(bm, (0.05, dwb2 - 0.06, 0.1), loc=(-0.03, -dwb2 / 2, z), mi=1)
    bm_cube(bm, (0.05, 0.08, 0.95), loc=(-0.03, -dwb2 / 2, 0.68), rot=(-0.62, 0, 0), mi=1)
    bm_cyl(bm, 0.025, 0.025, 0.06, loc=(0.04, -dwb2 + 0.08, 1.0), rot=(0, math.pi / 2, 0), seg=8, mi=2)
    ob = new_obj("GQ_Bathroom_Door_Leaf", bm, ROOM["Bathroom"], [mat_noise("Wood_Door_Bathroom", "#b08356", "#c09264", scale=8, stretch=(1.0, 1.0, 0.3)),
                                                                mat_noise("Wood_Door_Batten", "#8a6644", "#9a7450", scale=8), steel],
                 parent=root, props=dict(cn="卫生间木板门（已打开，开向卫生间）", status="inferred", note="R8 积木：卫生间单独有门；门的样子为推测"))
    ob.location = (-W_HOUSE / 2 - 0.12, BATH_DOOR[1] - 0.02, B)
    ob.rotation_euler = (0, 0, math.radians(-88))
    bm = bmesh.new()
    for y in BATH_DOOR:
        bm_cube(bm, (0.36, 0.08, 2.1), loc=(-W_HOUSE / 2, y + math.copysign(0.04, y - sum(BATH_DOOR) / 2), B + 1.05))
    bm_cube(bm, (0.36, BATH_DOOR[1] - BATH_DOOR[0] + 0.16, 0.08), loc=(-W_HOUSE / 2, sum(BATH_DOOR) / 2, B + 2.09))
    new_obj("GQ_Bathroom_Door_Frame", bm, ROOM["Bathroom"], [mat_noise("Wood_Door_Frame_Plain", "#7a5a3e", "#8a6a4a", scale=8)], parent=root,
            props=dict(cn="卫生间门框", status="inferred"))

    def toilet(bm):
        bm_cyl(bm, 0.14, 0.18, 0.38, loc=(0, 0.05, 0.19), seg=16, mi=0)
        bm_sphere(bm, (0.2, 0.25, 0.08), loc=(0, 0.1, 0.4), seg=16, rings=8, mi=0)
        bm_sphere(bm, (0.19, 0.24, 0.02), loc=(0, 0.1, 0.48), seg=16, rings=6, mi=1)
        bm_cube(bm, (0.42, 0.18, 0.4), loc=(0, -0.2, 0.62), mi=0)
        bm_cube(bm, (0.44, 0.2, 0.04), loc=(0, -0.2, 0.84), mi=0)
        bm_cube(bm, (0.06, 0.02, 0.02), loc=(0.14, -0.1, 0.78), mi=2)
    obj("Bathroom", "GQ_Bathroom_Toilet", "马桶", [white, mat("Plastic_Seat_Wood", "#b88a5a", rough=0.5), steel], toilet,
        loc=(-5.75, wy0 + 0.3, 0), smooth_shade=True, floor=True, note="R5：大马桶")
    obj("Bathroom", "GQ_Bathroom_Corner_Sink_Mirror", "墙角小洗手池和镜子", [white, steel, mat("Mirror", "#dfe8ee", metal=1.0, rough=0.05), wood_furn],
        lambda bm: (bm_cyl(bm, 0.05, 0.07, 0.7, loc=(0, 0, 0.35), seg=10, mi=0), bm_sphere(bm, (0.24, 0.2, 0.1), loc=(0, 0, 0.78), seg=16, rings=8, mi=0),
                    bm_cyl(bm, 0.012, 0.012, 0.18, loc=(-0.15, 0, 0.92), seg=6, mi=1), bm_cyl(bm, 0.01, 0.01, 0.12, loc=(-0.1, 0, 1.0), rot=(0, math.pi / 2, 0), seg=6, mi=1),
                    bm_cube(bm, (0.02, 0.42, 0.55), loc=(-0.24, 0, 1.45), mi=3), bm_cube(bm, (0.022, 0.36, 0.48), loc=(-0.225, 0, 1.45), mi=2)),
        loc=(wx0 + 0.25, wy1 - 0.45, 0), smooth_shade=False, floor=True, note="R5：角落小洗手池；镜子为推测")
    obj("Bathroom", "GQ_Bathroom_Towel_Bar", "毛巾杆和毛巾", [steel, mat("Fabric_Towel_Striped", "#d8574a", rough=0.9)],
        lambda bm: (bm_cyl(bm, 0.012, 0.012, 0.55, loc=(0, 0, 0), rot=(0, math.pi / 2, 0), seg=6, mi=0),
                    bm_cube(bm, (0.4, 0.03, 0.55), loc=(0, 0.0, -0.26), mi=1)), loc=(-5.6, wy1 - 0.05, 1.35), note="R5：墙上毛巾")
    obj("Bathroom", "GQ_Bathroom_Toilet_Paper", "厕纸", [white, wood_furn],
        lambda bm: (bm_cube(bm, (0.04, 0.16, 0.03), loc=(0, 0, 0.07), mi=1), bm_cyl(bm, 0.055, 0.055, 0.1, loc=(0.06, 0, 0.0), rot=(math.pi / 2, 0, 0), seg=12, mi=0)),
        loc=(wx0 + 0.02, wy0 + 0.75, 0.68), note="R5：墙上厕纸")
    obj("Bathroom", "GQ_Bathroom_Wooden_Cabinet", "木柜（放清洁用品）", [wood_furn, mat("Bottle_Blue", "#3a6fb0", rough=0.3), mat("Bottle_Yellow", "#e0b83a", rough=0.3)],
        lambda bm: (bm_cube(bm, (0.42, 0.7, 0.9), loc=(0, 0, 0.45), mi=0), bm_cube(bm, (0.02, 0.32, 0.7), loc=(0.215, -0.17, 0.45), mi=0),
                    bm_cube(bm, (0.02, 0.32, 0.7), loc=(0.215, 0.17, 0.45), mi=0),
                    bm_cyl(bm, 0.05, 0.05, 0.22, loc=(0, -0.2, 1.01), seg=10, mi=1), bm_cyl(bm, 0.045, 0.045, 0.18, loc=(0.0, 0.0, 0.99), seg=10, mi=2),
                    bm_cyl(bm, 0.04, 0.05, 0.16, loc=(0.02, 0.2, 0.98), seg=10, mi=1)),
        loc=(wx0 + 0.22, -1.6, 0), floor=True, note="R5：木柜；柜上的清洁瓶子为推测")
    obj("Bathroom", "GQ_Bathroom_Broom", "门口的扫帚", [wood_light, mat_noise("Broom_Straw", "#c9a75a", "#d8b86a", scale=20)],
        lambda bm: (bm_cyl(bm, 0.018, 0.018, 1.2, loc=(0, 0, 0.75), seg=6, mi=0), bm_cyl(bm, 0.05, 0.14, 0.32, loc=(0, 0, 0.16), seg=10, mi=1)),
        loc=(wx1 - 0.18, -1.0, 0.0), rot=(0, 0.12, 0), floor=True, overlap=False, note="R5：门口扫帚")
    obj("Bathroom", "GQ_Bathroom_Bucket_Brush", "水桶和刷子", [mat("Metal_Galvanized", "#9aa1a6", metal=0.7, rough=0.4), mat("Plastic_Brush_Red", "#c03a2a")],
        lambda bm: (bm_cyl(bm, 0.15, 0.12, 0.3, loc=(0, 0, 0.15), seg=14, mi=0), bm_cube(bm, (0.2, 0.06, 0.05), loc=(0.25, 0.0, 0.025), mi=1)),
        loc=(-5.2, wy1 - 0.4, 0), floor=True, status="inferred", note="清洁用品为推测")
    # 灯
    for nm, loc, energy in (("GQ_Light_Kitchen_Dining", (-1.9, 0.2, B + 2.4), 140), ("GQ_Light_Kitchen_Counter", (-3.2, -1.7, B + 2.3), 60),
                            ("GQ_Light_Bedroom", (3.0, 0.3, B + 2.35), 110), ("GQ_Light_Bathroom", (-5.75, -0.5, B + 2.1), 55)):
        li = bpy.data.lights.new(nm, "POINT")
        li.energy = energy
        li.color = (1.0, 0.84, 0.64)
        li.shadow_soft_size = 0.3
        lo = bpy.data.objects.new(nm, li)
        (ROOM["Bedroom"] if "Bedroom" in nm else ROOM["Bathroom"] if "Bathroom" in nm else ROOM["Kitchen"]).objects.link(lo)
        lo.parent = root
        lo.location = loc


def build_warehouse():
    """光头强的独立仓库（整栋为推测：动画里没有可用画面；R7 玩家复刻只用来理解“高山墙木板仓库、正中一扇门”的结构）。
    局部坐标：+Y 为正面（大门），根物体旋转后大门朝向木屋（世界 -X）。"""
    WC = COLL["GuangtouQiang_Warehouse"]
    WR = COLL["WH_Roof_Removable"]
    WI = COLL["WH_Interior"]
    P = WAREHOUSE
    W, D, H, rise, Bw = P["W"], P["D"], P["H"], P["rise"], P["floor"]
    wx, wy = HOUSE["x"] + P["lx"], HOUSE["y"] + P["ly"]
    c, s = math.cos(P["rot"]), math.sin(P["rot"])

    def to_world(x, y):
        return (wx + c * x - s * y, wy + s * x + c * y)
    gz = max(ground(*to_world(x, y)) for x in (-W / 2, W / 2) for y in (-D / 2, D / 2 + 1.0))
    root = empty("Warehouse_Root", WC, (wx, wy, gz), (0, 0, P["rot"]), size=1.5,
                 props=dict(cn="光头强的仓库（根，整栋推测）", status="inferred",
                            note="动画中没有仓库的可用画面；R7 玩家复刻只用于理解结构；外观、门窗位置和内部全部是推测"))
    rnd = random.Random(31)

    def legs(bm, w, d, h, t=0.05, mi=0):
        for sx in (-1, 1):
            for sy in (-1, 1):
                bm_cube(bm, (t, t, h), loc=(sx * (w / 2 - t / 2 - 0.02), sy * (d / 2 - t / 2 - 0.02), h / 2), mi=mi)

    def lg(x, y):
        return ground(*to_world(x, y)) - gz
    planks_m = [mat_noise(f"Wood_Warehouse_Weathered_{i}", c1, c2, scale=9, bump=0.2, stretch=(1.0, 1.0, 0.25)) for i, (c1, c2) in enumerate(
        (("#6b5a48", "#7a6854"), ("#5e4e3e", "#6c5a48"), ("#7a6650", "#88735c"), ("#544538", "#625244")))]
    frame_m = mat_noise("Wood_Warehouse_Frame", "#4e3b2c", "#5c4636", scale=8)
    roof_m = [mat_noise(f"Roof_Warehouse_Board_{i}", c1, c2, scale=7, bump=0.2, stretch=(0.3, 1.0, 1.0)) for i, (c1, c2) in enumerate(
        (("#4a6a80", "#567689"), ("#5a6e78", "#667a84"), ("#3f5c70", "#4a687c")))]
    patch_m = [MATS["Roof_Patch_Pale_Blue"], MATS["Roof_Patch_Tan_Wood"], MATS["Roof_Patch_Grey"]]
    moss_m = [MATS["Roof_Moss_Grass"], MATS["Roof_Twig"]]
    stone = MATS["Stone_Base_Grey"]
    core = MATS["Stone_Base_Core"]
    floor_ms = [mat_noise(f"Wood_Warehouse_Floor_{i}", c1, c2, scale=8, stretch=(1.0, 0.25, 1.0)) for i, (c1, c2) in enumerate(
        (("#7a6248", "#866d52"), ("#6c563e", "#7a6248"), ("#86705a", "#937c64")))]
    steel = MATS["Steel_Pot"]
    iron = MATS["Iron_Wok"]
    cut = MATS["Wood_Cut_End"]
    bark = MATS.get("Bark_Log") or mat_noise("Bark_Log", "#5d3f2a", "#7b573c", scale=6)
    glow = MATS["Lantern_Glow"]
    lumber = [mat_noise(f"Wood_Lumber_{i}", c1, c2, scale=8, stretch=(0.2, 1.0, 1.0)) for i, (c1, c2) in enumerate(
        (("#c9a06a", "#d6b07a"), ("#b88c58", "#c69a66"), ("#d8b886", "#e3c696"), ("#a67a4a", "#b48858")))]
    crate_m = mat_noise("Wood_Crate", "#a8824e", "#b8925c", scale=9)

    def wobj(name, cn, mats, build, loc=(0, 0, 0), rot=(0, 0, 0), C=None, floor=False, overlap=True, smooth_shade=False, note=None):
        bm = bmesh.new()
        build(bm)
        ob = new_obj(name, bm, C or WI, mats, smooth_shade=smooth_shade, parent=root, props=dict(cn=cn, status="inferred", note=note))
        ob.location = (loc[0], loc[1], loc[2] + (Bw if C in (None, WI) else 0.0))
        ob.rotation_euler = rot
        ob["position_status"] = "inferred"
        if floor:
            ob["room"] = "Warehouse"
            ob["floor_item"] = True
            ob["floor_z_world"] = gz + Bw
            ob["overlap_check"] = overlap
        return ob

    # 基座：石头墙基 + 内芯
    bm = bmesh.new()
    zb = min(lg(x, y) for x in (-W / 2, W / 2) for y in (-D / 2, D / 2)) - 0.5
    bm_cube(bm, (W + 0.1, D + 0.1, Bw - 0.04 - zb), loc=(0, 0, (Bw - 0.04 + zb) / 2), mi=0)
    for (ax, ay), (bx, by) in zip([(-W / 2, -D / 2), (W / 2, -D / 2), (W / 2, D / 2), (-W / 2, D / 2)],
                                  [(W / 2, -D / 2), (W / 2, D / 2), (-W / 2, D / 2), (-W / 2, -D / 2)]):
        L = math.hypot(bx - ax, by - ay)
        n = int(L / 0.6)
        along_x = abs(bx - ax) > 0.1
        for i in range(n + 1):
            t = i / n
            px, py = ax + (bx - ax) * t, ay + (by - ay) * t
            px += 0.06 * (1 if px > 0 else -1) * (0 if along_x else 1)
            py += 0.06 * (1 if py > 0 else -1) * (1 if along_x else 0)
            z0 = lg(px, py)
            bm_ico(bm, rnd.uniform(0.22, 0.3), loc=(px, py, (z0 + Bw) / 2 - 0.05), scale=(1.2, 0.6, 0.8) if along_x else (0.6, 1.2, 0.8),
                   subdiv=1, rough=0.25, seed=i, mi=1)
    new_obj("Warehouse_Stone_Footing", bm, WC, [core, stone], parent=root, props=dict(cn="仓库石头墙基", status="inferred"))
    # 竖木板墙：前后山墙（前面开大门），两侧各两扇小窗
    door_w, door_h = 2.6, 2.7
    side_holes = [(-2.4, -1.3, 1.35, 2.25), (1.3, 2.4, 1.35, 2.25)]
    top_fn = lambda x: H + rise * (1 - abs(x) / (W / 2))
    for nm, cn, M, L, holes, top in (("Front", "仓库正面山墙（大门）", Matrix.Translation((0, D / 2, Bw)), W, [(-door_w / 2, door_w / 2, 0.0, door_h)], top_fn),
                                     ("Back", "仓库背面山墙", Matrix.Translation((0, -D / 2, Bw)) @ Matrix.Rotation(math.pi, 4, "Z"), W, [(-0.35, 0.35, 3.3, 3.9)], top_fn),
                                     ("East", "仓库东墙（两扇小窗）", Matrix.Translation((W / 2, 0, Bw)) @ Matrix.Rotation(math.pi / 2, 4, "Z"), D, side_holes, None),
                                     ("West", "仓库西墙（两扇小窗）", Matrix.Translation((-W / 2, 0, Bw)) @ Matrix.Rotation(-math.pi / 2, 4, "Z"), D, side_holes, None)):
        bm = bmesh.new()
        vplank_wall(bm, L, H, holes, len(planks_m), rnd, top=top)
        bmesh.ops.transform(bm, matrix=M, verts=bm.verts[:])
        new_obj(f"Warehouse_Wall_{nm}", bm, WC, planks_m, parent=root, props=dict(cn=cn, status="inferred", note="风化的竖木板墙；R7 只用于理解结构"))
    # 木构架：转角柱、中间柱、顶梁、斜撑、门框
    bm = bmesh.new()
    for x in (-W / 2 + 0.1, W / 2 - 0.1):
        for y in (-D / 2 + 0.1, -D / 2 + D / 3, D / 2 - D / 3, D / 2 - 0.1):
            bm_cube(bm, (0.16, 0.16, H), loc=(x, y, Bw + H / 2))
        bm_cube(bm, (0.16, D, 0.16), loc=(x, 0, Bw + H - 0.08))
        for y0 in (-D / 2 + 0.1, D / 2 - D / 3):
            bm_cube(bm, (0.08, 0.1, math.hypot(D / 3 - 0.1, 1.2)), loc=(x, y0 + (D / 3 - 0.1) / 2, Bw + H - 0.7),
                    rot=(math.atan2(D / 3 - 0.1, 1.2), 0, 0))
    for y in (-D / 2 + D / 3, D / 2 - D / 3):
        bm_cube(bm, (W, 0.14, 0.16), loc=(0, y, Bw + H - 0.08))
        bm_cube(bm, (0.12, 0.12, rise - 0.2), loc=(0, y, Bw + H + (rise - 0.2) / 2))
    for x in (-door_w / 2 - 0.08, door_w / 2 + 0.08):
        bm_cube(bm, (0.16, 0.2, door_h + 0.1), loc=(x, D / 2, Bw + (door_h + 0.1) / 2))
    bm_cube(bm, (door_w + 0.32, 0.2, 0.16), loc=(0, D / 2, Bw + door_h + 0.08))
    for (y0, y1) in [(h[0], h[1]) for h in side_holes]:
        for x in (-W / 2, W / 2):
            bm_cube(bm, (0.2, y1 - y0 + 0.12, 0.08), loc=(x, (y0 + y1) / 2, Bw + 1.31))
            bm_cube(bm, (0.2, y1 - y0 + 0.12, 0.08), loc=(x, (y0 + y1) / 2, Bw + 2.29))
            for yy in (y0 - 0.03, y1 + 0.03):
                bm_cube(bm, (0.2, 0.06, 0.98), loc=(x, yy, Bw + 1.8))
    new_obj("Warehouse_Timber_Frame", bm, WC, [frame_m], parent=root, props=dict(cn="仓库木构架（柱、梁、斜撑、门窗框）", status="inferred"))
    # 窗：脏玻璃 + 十字木条；东侧一扇木百叶打开
    bm = bmesh.new()
    for (y0, y1) in [(h[0], h[1]) for h in side_holes]:
        for x in (-W / 2, W / 2):
            yc, ln = (y0 + y1) / 2, y1 - y0
            bm_cube(bm, (0.02, ln, 0.9), loc=(x, yc, Bw + 1.8), mi=0)
            bm_cube(bm, (0.05, ln, 0.04), loc=(x, yc, Bw + 1.8), mi=1)
            bm_cube(bm, (0.05, 0.04, 0.9), loc=(x, yc, Bw + 1.8), mi=1)
    bm_cube(bm, (0.04, 0.55, 0.95), loc=(W / 2 + 0.35, 2.4 + 0.15, Bw + 1.8), rot=(0, 0, 0.9), mi=2)
    new_obj("Warehouse_Windows", bm, WC, [mat("Glass_Dusty", "#9aa59a", rough=0.5, transmission=0.4), frame_m, planks_m[2]], parent=root,
            props=dict(cn="仓库小窗（脏玻璃、木百叶）", status="inferred"))
    # 屋顶（可隐藏）：屋脊沿局部 Y，木板屋顶 + 补丁
    rot90 = Matrix.Rotation(math.pi / 2, 4, "Z")
    x0r, x1r = -D / 2 - 0.5, D / 2 + 0.5
    Sr = roof_surface(x0r, x1r, 0.0, W / 2, 0.55, Bw + H, rise, lift_hi=0.3, lift_lo=0.2)
    bm = bmesh.new()
    roof_boards(bm, Sr, x0r, x1r, rnd, len(roof_m), tiers=3)
    for side in (-1, 1):
        surf_box(bm, lambda u, xx, side=side: Sr(xx, side, u) + Vector((0, 0, 0.15)), 0.0, 0.07, x0r - 0.1, x1r + 0.1, 0.05, nu=1, nv=10, mi=1)
        surf_box(bm, lambda u, xx, side=side: Sr(xx, side, u) - Vector((0, 0, 0.1)), 0.0, 1.0, x0r, x1r, 0.04, nu=16, nv=36, mi=len(roof_m))
    for side, u in ((1, 0.0), (1, 0.5), (-1, 0.5)):
        p = Sr(0.0, side, u)
        bm_cyl(bm, 0.12, 0.12, x1r - x0r, loc=(0, p.y, p.z - 0.15), rot=(0, math.pi / 2, 0), seg=10, mi=len(roof_m) + 1)
    bmesh.ops.transform(bm, matrix=rot90, verts=bm.verts[:])
    new_obj("Warehouse_Roof_Boards", bm, WR, roof_m + [mat_noise("Wood_Warehouse_Ceiling", "#5a4a3c", "#665546", scale=8), frame_m], parent=root,
            props=dict(cn="仓库木板屋顶（可隐藏）", status="inferred", note="按木屋屋顶的做法推测"))
    bm_p, bm_m = bmesh.new(), bmesh.new()
    roof_extras(bm_p, bm_m, Sr, x0r, x1r, rnd, 9, n_moss=16, n_twig=3)
    bmesh.ops.transform(bm_p, matrix=rot90, verts=bm_p.verts[:])
    bmesh.ops.transform(bm_m, matrix=rot90, verts=bm_m.verts[:])
    new_obj("Warehouse_Roof_Patches", bm_p, WR, patch_m, parent=root, props=dict(cn="仓库屋顶补丁", status="inferred"))
    new_obj("Warehouse_Roof_Moss", bm_m, WR, moss_m, parent=root, props=dict(cn="仓库屋顶苔藓和树枝", status="inferred"))
    # 大门：两扇竖木板谷仓门（Z 字斜撑），向外打开
    for side, hx_ in (("North", door_w / 2), ("South", -door_w / 2)):
        bm = bmesh.new()
        sgn = -1 if side == "North" else 1
        lw = door_w / 2 - 0.02
        x = 0.0
        while x < lw - 0.01:
            w = min(0.22, lw - x)
            bm_cube(bm, (w - 0.012, 0.05, door_h - 0.05), loc=(sgn * (x + w / 2), 0, (door_h - 0.05) / 2 + 0.03), mi=rnd.randrange(2))
            x += w
        for z in (0.35, door_h - 0.4):
            bm_cube(bm, (lw, 0.06, 0.14), loc=(sgn * lw / 2, 0.05, z), mi=2)
        ang = math.atan2(door_h - 0.75, lw - 0.1)
        bm_cube(bm, (math.hypot(door_h - 0.75, lw - 0.1), 0.06, 0.12), loc=(sgn * lw / 2, 0.05, door_h / 2), rot=(0, -sgn * ang, 0), mi=2)
        bm_cyl(bm, 0.05, 0.05, 0.02, loc=(sgn * (lw - 0.15), 0.09, 1.2), rot=(math.pi / 2, 0, 0), seg=10, mi=3)
        ob = new_obj(f"Warehouse_Barn_Door_{side}", bm, WC, [planks_m[0], planks_m[2], frame_m, steel], parent=root,
                     props=dict(cn="仓库对开大门（已打开）", status="inferred"))
        ob.location = (hx_, D / 2 + 0.12, Bw)
        ob.rotation_euler = (0, 0, math.radians(-105) if side == "North" else math.radians(105))
    # 门前坡道
    yr0, yr1 = D / 2, D / 2 + 1.3
    zr1 = lg(0, yr1 + 0.2) - 0.05
    bm = bmesh.new()
    for i in range(7):
        xa = -1.25 + i * 0.36
        surf_box(bm, lambda u, v: Vector((v, lerp(yr0, yr1, u), lerp(Bw - 0.05, zr1, u))), 0.0, 1.0, xa, xa + 0.34, 0.05, nu=2, nv=1, mi=rnd.randrange(2))
    for x in (-1.2, 1.2):
        bm_cube(bm, (0.12, yr1 - yr0, 0.2), loc=(x, (yr0 + yr1) / 2, (Bw + zr1) / 2 - 0.12), rot=(-math.atan2(Bw - zr1, yr1 - yr0), 0, 0), mi=2)
    new_obj("Warehouse_Entrance_Ramp", bm, WC, [planks_m[2], planks_m[0], frame_m], parent=root, props=dict(cn="仓库门前木坡道", status="inferred"))
    DOOR_PASSAGES.append(("仓库大门", "Warehouse_Root", (-door_w / 2 + 0.2, door_w / 2 - 0.2, D / 2 - 1.2, D / 2 + 1.0, Bw + 0.05, Bw + 2.4)))

    # ---- 内部（可进入）：地板、木料悬臂架、原木堆、木箱、货架、工作台和工具、钉板、靠墙旧木板、油桶、吊灯
    IX, IY = W / 2 - 0.2, D / 2 - 0.15

    def wplanks(bm):
        x = -IX
        while x < IX - 0.01:
            w = min(rnd.uniform(0.2, 0.28), IX - x)
            bm_cube(bm, (w - 0.01, 2 * IY, 0.05), loc=(x + w / 2, 0, -0.025), mi=rnd.randrange(3))
            x += w
    wobj("Warehouse_Floor_Planks", "仓库旧木地板", floor_ms, wplanks)

    def lumber_rack(bm):
        for y in (-3.4, -1.6, 0.2, 1.6):
            bm_cube(bm, (0.14, 0.14, 2.5), loc=(0.35, y, 1.25), mi=0)
            bm_cube(bm, (0.9, 0.5, 0.08), loc=(0.0, y, 0.04), mi=0)
            for z in (0.45, 1.05, 1.65, 2.25):
                bm_cube(bm, (0.85, 0.08, 0.07), loc=(-0.08, y, z), rot=(0, -0.04, 0), mi=0)
        rr = random.Random(5)
        for z in (0.45, 1.05, 1.65, 2.25):
            n = rr.randint(3, 6)
            for k in range(n):
                th = rr.choice((0.04, 0.05, 0.1, 0.15))
                wdt = rr.choice((0.15, 0.2, 0.25)) if th < 0.1 else th
                L = rr.uniform(3.8, 5.4)
                bm_cube(bm, (wdt, L, th), loc=(-0.4 + k * 0.13 + rr.uniform(-0.02, 0.02), -0.85 + rr.uniform(-0.3, 0.3), z + 0.035 + th / 2 + (k % 2) * 0.0),
                        rot=(0, 0, rr.uniform(-0.01, 0.01)), mi=1 + rr.randrange(4))
    wobj("Warehouse_Lumber_Cantilever_Rack", "木料悬臂架和板材、方木", [frame_m] + lumber, lumber_rack, loc=(IX - 0.5, 0, 0), floor=True,
         note="木料堆放为推测")

    def log_pile(bm, n=4, L=2.6, r=0.2):
        for row in range(n):
            for i in range(n - row):
                x = (i - (n - row - 1) / 2) * r * 2.05
                z = r + row * r * 1.75
                bm_cyl(bm, r, r, L, loc=(0, x, z), rot=(0, math.pi / 2, 0), seg=10, mi=0, caps=False)
                for e in (-1, 1):
                    bm_cyl(bm, r * 0.97, r * 0.97, 0.02, loc=(e * L / 2, x, z), rot=(0, math.pi / 2, 0), seg=10, mi=1)
    wobj("Warehouse_Log_Pile", "原木堆", [bark, cut], lambda bm: log_pile(bm), loc=(0.3, -IY + 0.72, 0), floor=True)

    def crates(bm):
        for (x, y, z, sz) in ((0, 0, 0, 0.6), (0.65, 0.05, 0, 0.6), (0.3, 0.0, 0.6, 0.6), (0.05, 0.65, 0, 0.55)):
            bm_cube(bm, (sz, sz, sz), loc=(x, y, z + sz / 2), rot=(0, 0, rnd.uniform(-0.08, 0.08)), mi=0)
            for zz in (0.12, sz - 0.12):
                bm_cube(bm, (sz + 0.02, sz + 0.02, 0.05), loc=(x, y, z + zz), mi=1)
    wobj("Warehouse_Crate_Stack", "木箱堆", [crate_m, frame_m], crates, loc=(-IX + 0.45, -IY + 0.45, 0), floor=True)

    def shelving(bm):
        rr = random.Random(9)
        for z in (0.05, 0.6, 1.15, 1.7):
            bm_cube(bm, (0.45, 1.6, 0.04), loc=(0, 0, z), mi=0)
        for y in (-0.78, 0.78):
            for x in (-0.2, 0.2):
                bm_cube(bm, (0.05, 0.05, 2.0), loc=(x, y, 1.0), mi=0)
        for z in (0.07, 0.62, 1.17, 1.72):
            y = -0.7
            while y < 0.6:
                k = rr.random()
                if k < 0.4:
                    s = rr.uniform(0.2, 0.32)
                    bm_cube(bm, (0.3, s, s * 0.8), loc=(0, y + s / 2, z + 0.02 + s * 0.4), mi=1)
                    y += s + 0.04
                elif k < 0.7:
                    for j in range(3):
                        bm_cyl(bm, 0.05, 0.05, 0.13, loc=(-0.08 + (j % 2) * 0.12, y + 0.06 + j * 0.06, z + 0.085), seg=10, mi=2)
                    y += 0.25
                else:
                    bm_torus(bm, 0.13, 0.04, loc=(0, y + 0.15, z + 0.06), seg=16, rseg=6, mi=3)
                    y += 0.32
    wobj("Warehouse_Shelving_Boxes_Cans_Rope", "货架（纸箱、罐头、绳子）", [frame_m, mat("Cardboard_Box_Tan", "#b8955e", rough=0.8),
                                                                     mat("Can_Paint_Blue", "#3b6e9e", metal=0.4, rough=0.4), mat("Rope_Hemp", "#b49a68", rough=0.9)],
         shelving, loc=(-IX + 0.25, 1.9, 0), floor=True)

    def workbench(bm):
        bm_cube(bm, (0.8, 2.0, 0.08), loc=(0, 0, 0.88), mi=0)
        legs(bm, 0.8, 2.0, 0.84, 0.09, 1)
        bm_cube(bm, (0.7, 1.9, 0.04), loc=(0, 0, 0.25), mi=0)
        bm_cube(bm, (0.2, 0.18, 0.12), loc=(0.35, -0.75, 0.98), mi=2)
        bm_cube(bm, (0.08, 0.18, 0.12), loc=(0.48, -0.75, 0.98), mi=2)
        bm_cyl(bm, 0.015, 0.015, 0.3, loc=(0.55, -0.75, 0.98), rot=(0, 0, math.pi / 2), seg=6, mi=2)
        for i in range(4):
            bm_cube(bm, (0.5, 0.12, 0.05), loc=(-0.1, 0.4 + i * 0.13, 0.3), mi=3)
    wobj("Warehouse_Workbench_Vise", "工作台和台钳", [mat_noise("Wood_Workbench_Top", "#8a6a48", "#9a7854", scale=8), frame_m, iron, lumber[0]], workbench,
         loc=(-IX + 0.45, -1.3, 0), floor=True)

    def tools(bm):
        # 电锯（橙色机身、银色导板）、锤子、斧头、手锯
        bm_cube(bm, (0.22, 0.38, 0.22), loc=(0.0, 0.0, 0.11), mi=0)
        bm_cube(bm, (0.04, 0.6, 0.1), loc=(0.0, 0.48, 0.1), mi=1)
        bm_torus(bm, 0.09, 0.015, loc=(0, -0.08, 0.27), rot=(0, math.pi / 2, 0), seg=12, rseg=4, mi=2, arc=math.pi)
        bm_cyl(bm, 0.018, 0.018, 0.32, loc=(0.1, 0.9, 0.02), rot=(math.pi / 2, 0, 0.3), seg=6, mi=3)
        bm_cube(bm, (0.12, 0.04, 0.04), loc=(0.15, 1.05, 0.02), rot=(0, 0, 0.3), mi=1)
        bm_cyl(bm, 0.02, 0.022, 0.6, loc=(-0.15, -0.6, 0.02), rot=(math.pi / 2, 0, -0.2), seg=6, mi=3)
        bm_cube(bm, (0.16, 0.03, 0.12), loc=(-0.21, -0.88, 0.02), rot=(math.pi / 2, 0, -0.2), mi=1)
    wobj("Warehouse_Tools_On_Bench", "台面上的电锯、锤子、斧头", [mat("Plastic_Chainsaw_Orange", "#e0761e", rough=0.4), MATS["Steel_Axe_Head"] if "Steel_Axe_Head" in MATS else steel,
                                                       iron, mat_noise("Wood_Axe_Handle", "#9b7347", "#b08455", scale=10)],
         tools, loc=(-IX + 0.5, -1.3, 0.92), note="光头强常用电锯（第一季截图 S1E1-28/66）；放在工作台上为推测")

    def pegboard(bm):
        bm_cube(bm, (0.03, 1.8, 1.0), loc=(0, 0, 0), mi=0)
        for i in range(5):
            bm_cube(bm, (0.04, 0.03, 0.03), loc=(0.03, -0.7 + i * 0.35, 0.3), mi=1)
        bm_cube(bm, (0.01, 0.55, 0.12), loc=(0.05, -0.55, 0.05), rot=(0.1, 0, 0), mi=2)
        bm_cube(bm, (0.03, 0.05, 0.12), loc=(0.05, -0.85, 0.05), mi=3)
        for i, (y, ln) in enumerate(((0.0, 0.35), (0.3, 0.28), (0.6, 0.4))):
            bm_cyl(bm, 0.015, 0.015, ln, loc=(0.05, y, 0.1), seg=6, mi=3)
            bm_cube(bm, (0.04, 0.1, 0.05), loc=(0.05, y, 0.1 + ln / 2), mi=1)
        bm_torus(bm, 0.12, 0.02, loc=(0.06, 0.35, -0.3), rot=(0, math.pi / 2, 0), seg=14, rseg=4, mi=4)
    wobj("Warehouse_Pegboard_Hand_Tools", "墙上钉板和手工具（手锯、锤子、扳手、绳圈）",
         [mat("Pegboard_Brown", "#7a5e40", rough=0.8), iron, steel, MATS["Wood_Axe_Handle"], MATS["Rope_Hemp"]],
         pegboard, loc=(-W / 2 + 0.075, -1.3, 1.65))

    def leaning(bm):
        rr = random.Random(3)
        for i in range(6):
            L = rr.uniform(1.8, 2.5)
            bm_cube(bm, (rr.uniform(0.15, 0.25), 0.035, L), loc=(i * 0.2, 0.0, L / 2 * math.cos(0.2)), rot=(-0.2, 0, rr.uniform(-0.05, 0.05)), mi=rr.randrange(2))
    wobj("Warehouse_Old_Boards_Leaning", "靠墙的旧木板", [planks_m[1], planks_m[3]], leaning, loc=(-2.6, IY - 0.32, 0), floor=True, overlap=False)
    wobj("Warehouse_Oil_Drums", "油桶", [mat("Paint_Drum_Red", "#a8382c", metal=0.4, rough=0.5), mat("Paint_Drum_Blue", "#2f5e8a", metal=0.4, rough=0.5)],
         lambda bm: (bm_cyl(bm, 0.29, 0.29, 0.88, loc=(0, 0, 0.44), seg=16, mi=0), bm_cyl(bm, 0.29, 0.29, 0.88, loc=(0.62, 0.05, 0.44), seg=16, mi=1),
                     bm_torus(bm, 0.295, 0.015, loc=(0, 0, 0.3), seg=16, rseg=4, mi=0), bm_torus(bm, 0.295, 0.015, loc=(0, 0, 0.6), seg=16, rseg=4, mi=0)),
         loc=(IX - 1.2, IY - 0.55, 0), floor=True)
    wobj("Warehouse_Sawhorse_Plank", "锯木架和木板", [frame_m, lumber[2]],
         lambda bm: ([bm_cube(bm, (0.06, 0.06, 0.8), loc=(sx * 0.12, y, 0.38), rot=(0, sx * 0.25, 0), mi=0) for sx in (-1, 1) for y in (-0.5, 0.5)],
                     [bm_cube(bm, (0.1, 0.06, 0.08), loc=(0, y, 0.78), mi=0) for y in (-0.5, 0.5)],
                     bm_cube(bm, (0.25, 1.6, 0.05), loc=(0, 0.1, 0.845), rot=(0, 0, 0.08), mi=1)),
         loc=(0.6, -1.0, 0), floor=True)
    wobj("Warehouse_Hanging_Lamp", "吊灯", [MATS["Lantern_Metal"], glow],
         lambda bm: (bm_cyl(bm, 0.006, 0.006, 1.2, loc=(0, 0, 0.6), seg=4, mi=0), bm_cyl(bm, 0.3, 0.05, 0.16, loc=(0, 0, -0.05), seg=16, mi=0),
                     bm_sphere(bm, (0.07, 0.07, 0.07), loc=(0, 0, -0.12), seg=10, rings=6, mi=1)), loc=(0, 0.0, H - 0.3))
    for nm, loc, e in (("Warehouse_Light_Main", (0, 0, Bw + H - 0.6), 260), ("Warehouse_Light_Fill", (0, -2.5, Bw + 2.4), 120)):
        li = bpy.data.lights.new(nm, "POINT")
        li.energy = e
        li.color = (1.0, 0.86, 0.68)
        li.shadow_soft_size = 0.4
        lo = bpy.data.objects.new(nm, li)
        WI.objects.link(lo)
        lo.parent = root
        lo.location = loc
    return root


def build_yard(root, lg, y_stair):
    """院子（R1：歪斜木栅栏、蓝顶院门、轮胎堆、原木、水缸；U3：门前铁盆、木桶、木墩斧头）。坐标用木屋局部坐标，物体放在世界坐标里贴地。"""
    P = COLL["Props"]
    hx, hy = HOUSE["x"], HOUSE["y"]
    log_bark = MATS.get("Bark_Log") or mat_noise("Bark_Log", "#5d3f2a", "#7b573c", scale=6)
    cut = MATS["Wood_Cut_End"]
    metal = mat("Metal_Galvanized", "#9aa1a6", metal=0.7, rough=0.4)

    def put(name, cn, mats, build, lx, ly, rot=0.0, status="observed", note=None, smooth_shade=False, sink=0.02, world=False):
        x, y = (lx, ly) if world else (hx + lx, hy + ly)
        bm = bmesh.new()
        build(bm)
        ob = new_obj(name, bm, P, mats, smooth_shade=smooth_shade, props=dict(cn=cn, status=status, note=note))
        ob.location = (x, y, ground(x, y) - sink)
        ob.rotation_euler = (0, 0, rot)
        return ob

    put("Prop_Washtub_Galvanized", "铁皮洗衣盆", [metal], lambda bm: bm_cyl(bm, 0.45, 0.38, 0.32, loc=(0, 0, 0.16), seg=20), 2.8, 11.0,
        note="U3：门前铁皮盆；R1：楼梯左侧的盆")
    put("Prop_Bucket_Galvanized", "铁桶", [metal], lambda bm: bm_cyl(bm, 0.18, 0.15, 0.36, loc=(0, 0, 0.18), seg=16), 1.8, 11.3, rot=0.3, note="U3")
    put("Prop_Wooden_Barrel", "木桶", [mat_noise("Wood_Barrel", "#8a5a33", "#a06b3f", scale=10), metal],
        lambda bm: (bm_sphere(bm, (0.34, 0.34, 0.45), loc=(0, 0, 0.45), seg=16, rings=10, deform=lambda co: Vector((co.x, co.y, clamp(co.z, -0.85, 0.85)))),
                    bm_torus(bm, 0.36, 0.02, loc=(0, 0, 0.2), mi=1), bm_torus(bm, 0.36, 0.02, loc=(0, 0, 0.7), mi=1)),
        -5.6, 3.3, smooth_shade=True, note="U3")
    put("Prop_Water_Jar_Clay", "水缸", [mat_noise("Clay_Water_Jar", "#6a5444", "#7a6252", scale=5), mat_water("Water_Jar_Surface", "#4a7a8a", "#2e5866")],
        lambda bm: (bm_sphere(bm, (0.42, 0.42, 0.4), loc=(0, 0, 0.4), seg=18, rings=10, deform=lambda co: Vector((co.x, co.y, min(co.z, 0.85)))),
                    bm_cyl(bm, 0.36, 0.36, 0.01, loc=(0, 0, 0.72), seg=18, mi=1)),
        -6.7, 3.1, smooth_shade=True, note="R1：院子里的水缸")
    put("Prop_Chopping_Block", "劈柴木墩", [log_bark, cut],
        lambda bm: (bm_cyl(bm, 0.36, 0.4, 0.55, loc=(0, 0, 0.275), seg=12, mi=0), bm_cyl(bm, 0.355, 0.355, 0.01, loc=(0, 0, 0.555), seg=12, mi=1)),
        6.4, 7.0, note="U3")
    put("Prop_Axe", "斧头", [mat_noise("Wood_Axe_Handle", "#9b7347", "#b08455", scale=10), mat("Steel_Axe_Head", "#9fa6ab", metal=0.8, rough=0.3)],
        lambda bm: (bm_cyl(bm, 0.025, 0.03, 0.75, loc=(0, 0, 0.9), rot=(0, 0.45, 0), seg=8, mi=0),
                    bm_cube(bm, (0.2, 0.04, 0.12), loc=(-0.12, 0, 0.56), rot=(0, 0.45, 0), mi=1)), 6.4, 7.0, sink=0.0, note="U3：斧头插在木墩上")
    put("Prop_Logs_Front", "院里的原木", [log_bark, cut],
        lambda bm: [bm_cyl(bm, 0.16, 0.16, 1.6, loc=(0, i * 0.34, 0.16), rot=(0, math.pi / 2, 0), seg=10, mi=0) for i in range(3)],
        8.0, 5.8, rot=0.2, note="U3、R1")

    def log_pile(bm, n=5, L=4.0, r=0.3):
        for row in range(n):
            for i in range(n - row):
                x = (i - (n - row - 1) / 2) * r * 2.05
                z = r + row * r * 1.75
                bm_cyl(bm, r, r, L, loc=(x, 0, z), rot=(math.pi / 2, 0, 0), seg=10, mi=0, caps=False)
                bm_cyl(bm, r * 0.97, r * 0.97, 0.02, loc=(x, L / 2, z), rot=(math.pi / 2, 0, 0), seg=10, mi=1)
                bm_cyl(bm, r * 0.97, r * 0.97, 0.02, loc=(x, -L / 2, z), rot=(math.pi / 2, 0, 0), seg=10, mi=1)
    put("Prop_Log_Pile_A", "原木堆", [log_bark, cut], lambda bm: log_pile(bm, 5), LOGYARD[0], LOGYARD[1], rot=0.4, world=True, note="U4：窗外能看到原木堆")
    put("Prop_Log_Pile_B", "原木堆", [log_bark, cut], lambda bm: log_pile(bm, 4, 3.4, 0.26), LOGYARD[0] + 3.0, LOGYARD[1] + 4.0, rot=1.2, world=True, note="U4")
    put("Prop_Log_Pile_Yard", "院子后面的原木堆", [log_bark, cut], lambda bm: log_pile(bm, 3, 3.0, 0.22), -8.0, -3.5, rot=0.05, note="R1：院子里有原木堆")
    rnd = random.Random(17)
    for k in range(8):
        a = rnd.uniform(0, 6.28)
        r = rnd.uniform(2.5, 6.0)
        x, y = LOGYARD[0] + math.cos(a) * r, LOGYARD[1] + math.sin(a) * r
        rr = rnd.uniform(0.3, 0.5)
        put(f"Prop_Stump_{k}", "树桩", [log_bark, cut],
            lambda bm, rr=rr: (bm_cyl(bm, rr, rr * 1.2, 0.5, loc=(0, 0, 0.25), seg=12, mi=0), bm_cyl(bm, rr * 0.98, rr * 0.98, 0.01, loc=(0, 0, 0.505), seg=12, mi=1)),
            x, y, status="inferred", world=True)
    tire = mat("Rubber_Tire", "#232426", rough=0.9)
    put("Prop_Tire_Stack", "轮胎堆", [tire], lambda bm: [bm_torus(bm, 0.36, 0.14, loc=(0, 0, 0.14 + i * 0.27), seg=20, rseg=8) for i in range(4)],
        -3.5, 6.6, smooth_shade=True, note="R1：楼梯右侧的轮胎堆；U4")
    put("Prop_Tires_Lying", "地上的轮胎", [tire], lambda bm: (bm_torus(bm, 0.36, 0.14, loc=(0, 0, 0.14), seg=20, rseg=8),
                                                        bm_torus(bm, 0.36, 0.14, loc=(0.8, 0.3, 0.14), rot=(0.15, 0, 0), seg=20, rseg=8)),
        -4.7, 7.6, smooth_shade=True, note="R1")

    def hose(bm):
        pts = [(math.cos(i * 0.42) * (0.32 + i * 0.002), math.sin(i * 0.42) * (0.32 + i * 0.002), 0.03) for i in range(60)]
        bm_tube(bm, pts, [0.025] * len(pts), seg=6, mi=0)
    put("Prop_Garden_Hose_Green", "绿色水管", [mat("Rubber_Hose_Green", "#2f8a4e", rough=0.5)], hose, -8.2, 0.6, smooth_shade=True, note="U4")
    # 歪斜、高低不一的木板栅栏（R1），正面西段有带蓝色木板小屋顶的院门，东段留出车道
    fence_ms = [mat_noise("Wood_Fence_A", "#9b7650", "#ae8960", scale=8), mat_noise("Wood_Fence_B", "#7e5e3e", "#8e6c4a", scale=8),
                mat_noise("Wood_Fence_C", "#b08a5e", "#c09a6c", scale=8)]
    F = dict(x0=-10.0, x1=15.0, y0=-22.0, y1=12.0)  # 一整圈；屋后一段把仓库围在院里（推测）
    gate = (6.6, 9.0)   # R1、H2：相机对着木屋正面时，带蓝顶的院门在画面左侧（模型里是局部 +X 一侧）
    drive = (11.5, 14.0)
    runs = [((F["x0"], F["y1"]), (gate[0], F["y1"])), ((gate[1], F["y1"]), (drive[0], F["y1"])), ((drive[1], F["y1"]), (F["x1"], F["y1"])),
            ((F["x1"], F["y1"]), (F["x1"], F["y0"])), ((F["x1"], F["y0"]), (F["x0"], F["y0"])), ((F["x0"], F["y0"]), (F["x0"], F["y1"]))]
    for i, ((ax, ay), (bx, by)) in enumerate(runs):
        L = math.hypot(bx - ax, by - ay)
        ang = math.atan2(by - ay, bx - ax)
        bm = bmesh.new()
        n_post = max(1, int(L / 2.2))
        for k in range(n_post + 1):
            t = k / n_post
            lx, ly = ax + (bx - ax) * t, ay + (by - ay) * t
            z = lg(lx, ly)
            bm_cyl(bm, 0.08, 0.09, 1.5, loc=(lx, ly, z + 0.55), rot=(rnd.uniform(-0.06, 0.06), rnd.uniform(-0.06, 0.06), 0), seg=8, mi=1)
        for k in range(n_post):
            for zz in (0.35, 0.85):
                t0, t1 = k / n_post, (k + 1) / n_post
                pa = (ax + (bx - ax) * t0, ay + (by - ay) * t0)
                pb = (ax + (bx - ax) * t1, ay + (by - ay) * t1)
                za, zb_ = lg(*pa) + zz + rnd.uniform(-0.06, 0.06), lg(*pb) + zz + rnd.uniform(-0.06, 0.06)
                bm_tube(bm, [(pa[0], pa[1], za), ((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2, (za + zb_) / 2 - 0.05), (pb[0], pb[1], zb_)], [0.04] * 3, seg=6, mi=1)
        t = 0.0
        while t < L - 0.1:
            w = rnd.uniform(0.12, 0.2)
            t += w / 2
            lx, ly = ax + math.cos(ang) * t, ay + math.sin(ang) * t
            if rnd.random() > 0.12:
                h = rnd.uniform(0.85, 1.35)
                z = lg(lx, ly)
                bm_cube(bm, (w, 0.035, h), loc=(lx - math.sin(ang) * 0.06, ly + math.cos(ang) * 0.06, z + h / 2 - 0.1),
                        rot=(rnd.uniform(-0.05, 0.05), rnd.uniform(-0.15, 0.15), ang + rnd.uniform(-0.04, 0.04)),
                        mi=rnd.randrange(3))
            t += w / 2 + rnd.uniform(0.02, 0.12)
        ob = new_obj(f"Prop_Fence_Crooked_{i}", bm, P, fence_ms, props=dict(cn="歪斜木板栅栏", status="observed",
                                                                           note="R1：高低不一、歪斜的木板栅栏；完整走向只看到正面，其余为推测"))
        ob.location = (hx, hy, root.location.z)
    # 院门：两根柱子 + 蓝色木板小屋顶（R1 左侧）
    gz0 = lg(sum(gate) / 2, F["y1"])
    bm = bmesh.new()
    for x in gate:
        bm_cyl(bm, 0.12, 0.13, 2.7, loc=(x, F["y1"], gz0 + 1.25), seg=10)
    bm_cube(bm, (gate[1] - gate[0] + 0.6, 0.16, 0.16), loc=(sum(gate) / 2, F["y1"], gz0 + 2.55))
    ob = new_obj("Prop_Yard_Gate_Posts", bm, P, [fence_ms[1]], props=dict(cn="院门门柱和横梁", status="observed", note="R1"))
    ob.location = (hx, hy, root.location.z)
    Sg = roof_surface(gate[0] - 0.5, gate[1] + 0.5, F["y1"], 0.6, 0.15, gz0 + 2.6, 0.55, lift_hi=0.18, lift_lo=0.18)
    bm = bmesh.new()
    roof_boards(bm, Sg, gate[0] - 0.5, gate[1] + 0.5, rnd, 2, tiers=1, thick=0.04, wmin=0.25, wmax=0.35)
    ob = new_obj("Prop_Yard_Gate_Roof_Blue", bm, P, [MATS["Roof_Board_BlueGrey_1"], MATS["Roof_Board_BlueGrey_3"]],
                 props=dict(cn="院门上的蓝色木板小屋顶", status="observed", note="R1"))
    ob.location = (hx, hy, root.location.z)


def mat_brick(name, c1, c2, mortar, scale=3.0, rough=0.85):
    """砖墙（烟囱、炕身）：在竖直面上用 (x+y, z) 作为砖纹坐标。"""
    if name in MATS:
        return MATS[name]
    m = _new_mat(name)
    nodes, links = _nodes(m)
    b = nodes.get("Principled BSDF")
    tc = nodes.new("ShaderNodeTexCoord")
    sep = nodes.new("ShaderNodeSeparateXYZ")
    add = nodes.new("ShaderNodeMath")
    cmb = nodes.new("ShaderNodeCombineXYZ")
    links.new(tc.outputs["Object"], sep.inputs[0])
    links.new(sep.outputs["X"], add.inputs[0])
    links.new(sep.outputs["Y"], add.inputs[1])
    links.new(add.outputs[0], cmb.inputs["X"])
    links.new(sep.outputs["Z"], cmb.inputs["Y"])
    br = nodes.new("ShaderNodeTexBrick")
    br.inputs["Color1"].default_value = srgb(c1)
    br.inputs["Color2"].default_value = srgb(c2)
    br.inputs["Mortar"].default_value = srgb(mortar)
    br.inputs["Scale"].default_value = scale
    br.inputs["Mortar Size"].default_value = 0.012
    links.new(cmb.outputs["Vector"], br.inputs["Vector"])
    links.new(br.outputs["Color"], b.inputs["Base Color"])
    bp = nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.3
    links.new(br.outputs["Fac"], bp.inputs["Height"])
    links.new(bp.outputs["Normal"], b.inputs["Normal"])
    _set(b, "Roughness", rough)
    m.diffuse_color = srgb(c1)
    MATS[name] = m
    return m


def mat_checker(name, c1, c2, scale=10.0, rough=0.9):
    """格子布（炕上叠着的格子被，R4）。"""
    if name in MATS:
        return MATS[name]
    m = _new_mat(name)
    nodes, links = _nodes(m)
    b = nodes.get("Principled BSDF")
    tc = nodes.new("ShaderNodeTexCoord")
    ck = nodes.new("ShaderNodeTexChecker")
    ck.inputs["Color1"].default_value = srgb(c1)
    ck.inputs["Color2"].default_value = srgb(c2)
    ck.inputs["Scale"].default_value = scale
    links.new(tc.outputs["Object"], ck.inputs["Vector"])
    links.new(ck.outputs["Color"], b.inputs["Base Color"])
    _set(b, "Roughness", rough)
    m.diffuse_color = srgb(c1)
    MATS[name] = m
    return m


# ------------------------------------------------------------------------------------------------
# 熊大熊二的树洞（推测）与蜂巢树


def add_cutters(target, coll_, specs, prefix):
    """用布尔“差集”修改器在 target 上挖洞；切割体保留在场景里（渲染隐藏、线框显示），移动它们就能改洞口。
    specs: [(名字, 半径缩放 (x, y, z), 局部位置, 局部旋转 z)]，位置是 target 的局部坐标。"""
    for k, (nm, sc, loc, rz) in enumerate(specs):
        bm = bmesh.new()
        bm_ico(bm, 1.0, scale=sc, subdiv=3, rough=0.08, seed=k * 2.7)
        cut = new_obj(f"{prefix}_Cutter_{nm}", bm, coll_, [], parent=target, props=dict(cn=f"洞口切割体（{nm}，渲染时隐藏）", status="inferred"))
        cut.location = loc
        cut.rotation_euler = (0, 0, rz)
        cut.hide_render = True
        cut.display_type = "WIRE"
        cut["helper"] = True
        md = target.modifiers.new(f"Cut_{nm}", "BOOLEAN")
        md.operation = "DIFFERENCE"
        md.solver = "EXACT"
        md.use_self = True
        md.object = cut


def stacked_swirl(bm, r, h, loc, mi=0, rings=5):
    """橙色螺旋叠圈物（依据熊洞室内剧照；像第一季片头的叠圈蜂巢，身份待确认）。"""
    x, y, z = loc
    for i in range(rings):
        t = i / rings
        bm_torus(bm, r * (1 - 0.75 * t), r * 0.28 * (1 - 0.5 * t), loc=(x, y, z + h * t), seg=18, rseg=8, mi=mi)
    bm_cyl(bm, r * 0.22, 0.0, h * 0.3, loc=(x, y, z + h * 1.02), seg=10, mi=mi)


def build_bears_home():
    """熊大熊二的树洞：巨大老树的空心树干，能从正面的天然洞口走进去（依据爱奇艺熊洞室内剧照 B1）。
    B1：室内是一条条扭曲的树根状内壁（橙黄到棕色），挂着藤蔓，后壁有一个拱形圆洞能看到外面的森林；
    一块长长的灰色石板床；墙上、地上有橙色螺旋叠圈物；树根上有苔藓和小草。
    外观没有原版画面：玩家复刻 B2 只用来理解“巨树底部开门”的结构。局部 -Y 为正面洞口。"""
    C = COLL["Bears_TreeHome"]
    x, y = BEARHOME["x"], BEARHOME["y"]
    gz = ground(x, y)
    root = empty("Bears_TreeHome_Root", C, (x, y, gz), (0, 0, BEARHOME["rot"]), size=2.0,
                 props=dict(cn="熊大熊二的树洞（根）", status="inferred",
                            note="室内依据 B1；外观、尺寸和在地图上的位置为推测；B2 玩家复刻只用于理解结构"))
    rnd = random.Random(3)
    bark = mat_noise("Bark_Big_Tree", "#5a3c28", "#77543a", scale=3, bump=0.5, stretch=(1.0, 1.0, 0.3))
    inner = mat_noise("Wood_TreeHome_Inner_Flutes", "#c98a3e", "#a8642c", scale=2.2, bump=0.4, stretch=(1.0, 1.0, 0.35))
    moss = mat_noise("Moss_TreeHome", "#5e8f34", "#7aa844", scale=6)
    # ---- 空心树干：外壁（底部外扩、竖向沟槽）+ 内壁（扭曲的树根状肋条，顶部收成穹顶）
    nT = 72
    zo = [-0.6 + i * 0.3 for i in range(23)]           # 外壁 -0.6 … 6.0
    zi = [0.0 + i * 0.25 for i in range(19)]            # 内壁 0 … 4.5，之后接穹顶

    def r_out(a, z):
        return (3.5 + 1.3 * math.exp(-(z + 0.6) / 0.9)) * (1 + 0.06 * math.sin(7 * a + 0.35 * z) + 0.03 * math.sin(13 * a))

    def r_in(a, z):
        rib = 0.22 * max(0.0, math.sin(9 * a + 0.55 * z)) ** 3
        return 2.85 - rib - 0.05 * math.sin(5 * a)
    bm = bmesh.new()
    ring_o = [[bm.verts.new((r_out(2 * math.pi * k / nT, z) * math.cos(2 * math.pi * k / nT), r_out(2 * math.pi * k / nT, z) * math.sin(2 * math.pi * k / nT), z))
               for k in range(nT)] for z in zo]
    dome = [4.5 + 0.2 * i for i in range(1, 8)]
    rows_i = []
    for z in zi + dome:
        s = 1.0 if z <= 4.5 else math.sqrt(max(0.02, 1 - ((z - 4.5) / 1.5) ** 2))
        rows_i.append([bm.verts.new((r_in(2 * math.pi * k / nT, z) * s * math.cos(2 * math.pi * k / nT),
                                     r_in(2 * math.pi * k / nT, z) * s * math.sin(2 * math.pi * k / nT), z)) for k in range(nT)])
    pole = bm.verts.new((0, 0, 6.05))

    def band(r0, r1, flip=False):
        for k in range(nT):
            q = (r0[k], r0[(k + 1) % nT], r1[(k + 1) % nT], r1[k])
            f = bm.faces.new(q[::-1] if flip else q)
    for i in range(len(ring_o) - 1):
        band(ring_o[i], ring_o[i + 1])
    for i in range(len(rows_i) - 1):
        band(rows_i[i], rows_i[i + 1], flip=True)
    for k in range(nT):
        bm.faces.new((rows_i[-1][(k + 1) % nT], rows_i[-1][k], pole))
    bm.faces.new(ring_o[-1])                      # 外壁顶盖（上面接实心的上段树干）
    band(ring_o[0], rows_i[0], flip=True)         # 底部环面
    hollow = new_obj("Bears_TreeHome_Hollow_Trunk", bm, C, [bark], smooth_shade=True, parent=root,
                     props=dict(cn="空心树干（外壁、树根状内壁、穹顶）", status="observed",
                                note="B1：内壁是一条条扭曲的树根状木头；外壁形状为推测"))
    hollow.data.materials.append(inner)
    for p in hollow.data.polygons:  # 内壁用橙黄色木头材质
        c = p.center
        if math.hypot(c.x, c.y) < 3.0 and c.z > -0.05:
            p.material_index = 1
    add_cutters(hollow, C, [("Front_Entrance", (1.2, 2.2, 1.55), (0, -3.3, 1.05), 0.0),
                            ("Back_Round_Opening", (1.35, 1.8, 1.05), (0.3, 3.3, 2.05), 0.15)], "Bears_TreeHome")
    DOOR_PASSAGES.append(("熊洞洞口", "Bears_TreeHome_Root", (-0.7, 0.7, -4.6, -1.6, 0.15, 1.9)))
    # ---- 上段树干、树枝、树冠、外面的大树根
    bm = bmesh.new()
    bm_tube(bm, [(0, 0, 5.6), (0.2, 0.1, 8), (0.1, -0.1, 10.5), (0.3, 0, 12.5)], [3.0, 2.2, 1.7, 1.2], seg=16)
    for k in range(5):
        a = 2 * math.pi * k / 5 + 0.5
        bm_tube(bm, [(0.2, 0, 11.0), (math.cos(a) * 2.8, math.sin(a) * 2.8, 13.2), (math.cos(a) * 5.0, math.sin(a) * 5.0, 14.2)], [0.7, 0.45, 0.18], seg=8)
    for k in range(9):
        a = 2 * math.pi * k / 9 + 0.15
        if abs(math.atan2(math.sin(a + math.pi / 2), math.cos(a + math.pi / 2))) < 0.6:
            continue  # 洞口前不放树根
        bm_tube(bm, [(math.cos(a) * 3.4, math.sin(a) * 3.4, 1.6), (math.cos(a) * 4.6, math.sin(a) * 4.6, 0.4), (math.cos(a) * 6.0, math.sin(a) * 6.0, -0.3)],
                [0.9, 0.6, 0.22], seg=10)
    new_obj("Bears_TreeHome_Upper_Trunk_Roots", bm, C, [bark], smooth_shade=True, parent=root,
            props=dict(cn="上段树干、树枝和外面的粗树根", status="inferred"))
    bm = bmesh.new()
    for k in range(9):
        a = 2 * math.pi * k / 9
        bm_ico(bm, rnd.uniform(3.2, 4.4), loc=(math.cos(a) * 4.3, math.sin(a) * 4.3, 14.8 + rnd.uniform(-0.5, 1.5)), scale=(1, 1, 0.8), subdiv=2, rough=0.2, seed=k)
    bm_ico(bm, 4.8, loc=(0, 0, 16.8), scale=(1, 1, 0.8), subdiv=2, rough=0.2, seed=20)
    new_obj("Bears_TreeHome_Canopy", bm, C, [MATS["Foliage_Broadleaf_Dark"]], smooth_shade=True, parent=root,
            props=dict(cn="树冠", status="inferred"))
    # ---- 室内（B1）
    INT = coll("Bears_TreeHome_Interior", C)

    def obj(name, cn, mats, build, loc=(0, 0, 0), rot=(0, 0, 0), status="observed", note="B1", floor=False, overlap=True, smooth_shade=True):
        bm = bmesh.new()
        build(bm)
        ob = new_obj(name, bm, INT, mats, smooth_shade=smooth_shade, parent=root, props=dict(cn=cn, status=status, note=note))
        ob.location = loc
        ob.rotation_euler = rot
        ob["position_status"] = "inferred"
        if floor:
            ob["room"] = "BearsTreeHome"
            ob["floor_item"] = True
            ob["floor_z_world"] = gz
            ob["overlap_check"] = overlap
        return ob

    def floor_disk(bm):
        bm_cyl(bm, 2.95, 2.95, 0.05, loc=(0, 0, -0.025), seg=48, mi=0)
        for k in range(10):
            a = rnd.uniform(0, 6.283)
            bm_ico(bm, rnd.uniform(0.1, 0.25), loc=(math.cos(a) * rnd.uniform(0.5, 2.4), math.sin(a) * rnd.uniform(0.5, 2.4), 0.0), scale=(1.4, 1.0, 0.35), subdiv=1, mi=1)
    obj("Bears_TreeHome_Floor", "树洞地面（泥土、小石子）", [mat_noise("Soil_TreeHome", "#6a4e34", "#7d5c3e", scale=5), MATS["Pebble_BlueGrey"]],
        floor_disk, status="inferred")

    def ribs(bm):  # 从穹顶顺着内壁扭下来、铺到地上的树根
        for k in range(10):
            a0 = 2 * math.pi * k / 10 + 0.2
            if abs(math.atan2(math.sin(a0 + math.pi / 2), math.cos(a0 + math.pi / 2))) < 0.5:
                continue
            if abs(math.atan2(math.sin(a0 + 0.3 - 1.48), math.cos(a0 + 0.3 - 1.48))) < 0.75:  # B1：后壁圆洞周围不挡
                continue
            pts = []
            for i in range(9):
                t = i / 8
                a = a0 + 0.6 * t
                rr = 2.6 - 0.15 * math.sin(t * 3) if t < 0.8 else 2.6 - (t - 0.8) * 4.0
                pts.append((math.cos(a) * rr, math.sin(a) * rr, 4.6 * (1 - t) + 0.05))
            bm_tube(bm, pts, [0.38 - 0.14 * (i / 8) for i in range(9)], seg=12, mi=0)
    obj("Bears_TreeHome_Inner_Root_Ribs", "内壁上扭曲下垂的树根", [inner], ribs, note="B1：室内一条条扭曲的树根")

    def bed(bm):
        bm_cube(bm, (2.9, 1.15, 0.34), loc=(0, 0, 0.17), mi=0)
        bm_cube(bm, (2.75, 1.0, 0.08), loc=(0.02, 0.02, 0.37), rot=(0, 0.02, 0), mi=0)
    ob = obj("Bears_TreeHome_Stone_Bed", "长条灰色石板床", [mat_noise("Stone_Bed_Grey_Purple", "#8d8a98", "#a4a1ae", scale=3, bump=0.3)], bed,
             loc=(1.0, 1.3, 0), rot=(0, 0, -0.35), floor=True, note="B1：熊大躺在一块长条灰色石板上", smooth_shade=False)
    soft = ob.modifiers.new("Bevel_Soft", "BEVEL")
    soft.width = 0.08
    soft.segments = 2
    obj("Bears_TreeHome_Leaf_Bed_XiongEr", "熊二的树叶铺（推测）", [mat_noise("Leaf_Bed_Green", "#5f8f3a", "#77a64a", scale=8)],
        lambda bm: bm_ico(bm, 1.0, scale=(1.1, 0.75, 0.18), subdiv=2, rough=0.08, seed=4), loc=(-1.7, 0.4, 0.195), floor=True,
        status="inferred", note="B1 只看到一块石板床；熊二睡哪里没有画面")
    orange = mat_noise("Swirl_Orange", "#e07a28", "#f09238", scale=6)
    spots = [(-2.45, 0.6, 1.4, 0.18), (2.3, -1.2, 2.4, 0.2), (1.2, 2.5, 3.2, 0.22), (-1.6, -2.0, 2.0, 0.16), (2.6, 0.9, 0.9, 0.15), (-2.2, 1.6, 3.4, 0.2)]

    def swirls(bm):
        for (sx, sy, sz, rr) in spots:
            stacked_swirl(bm, rr, rr * 1.8, (sx, sy, sz))
        stacked_swirl(bm, 0.24, 0.42, (-0.9, -0.4, 0.0))
        stacked_swirl(bm, 0.2, 0.36, (1.9, -0.1, 0.0))
    obj("Bears_TreeHome_Orange_Swirls", "橙色螺旋叠圈物（墙上和地上；身份待确认：可能是蜂蜜/蜂巢或菌类）", [orange], swirls,
        note="B1：墙上、地上有橙色螺旋叠圈物；具体是什么、位置为推测")
    obj("Bears_TreeHome_Honey_Pot", "蜂蜜罐（推测）", [mat_noise("Clay_Honey_Pot", "#9a6a3a", "#ad7a46", scale=5), mat("Honey_Gold", "#f2a71e", rough=0.2, emit="#f0a020", emit_strength=0.1)],
        lambda bm: (bm_sphere(bm, (0.28, 0.28, 0.3), loc=(0, 0, 0.3), seg=16, rings=10, mi=0), bm_cyl(bm, 0.2, 0.22, 0.05, loc=(0, 0, 0.58), seg=16, mi=1),
                    bm_sphere(bm, (0.06, 0.06, 0.12), loc=(0.18, -0.12, 0.5), seg=8, rings=6, mi=1)), loc=(-1.9, -0.6, 0), floor=True,
        status="inferred", note="熊爱吃蜂蜜；B1 里没有看到蜂蜜罐")

    def vines(bm):
        for k in range(6):
            a = rnd.uniform(0, 6.283)
            r0 = rnd.uniform(0.6, 2.2)
            x0, y0 = math.cos(a) * r0, math.sin(a) * r0
            L = rnd.uniform(1.6, 3.2)
            pts = [(x0 + 0.1 * math.sin(i), y0 + 0.1 * math.cos(i * 1.3), 5.4 - (i / 6) * L) for i in range(7)]
            bm_tube(bm, pts, [0.035] * 7, seg=6, mi=0)
            for j in range(3):
                p = pts[2 + j]
                bm_sphere(bm, (0.09, 0.03, 0.05), loc=(p[0] + 0.06, p[1], p[2]), seg=8, rings=4, mi=1)
    obj("Bears_TreeHome_Hanging_Vines", "垂下来的藤蔓", [mat("Vine_Dark_Green", "#3f6a2a", rough=0.7), mat("Vine_Leaf", "#5a9a3a", rough=0.6)], vines,
        note="B1：上方垂下来的藤蔓；位置为推测")

    def greens(bm):
        for k in range(18):
            a = rnd.uniform(0, 6.283)
            rr = rnd.uniform(1.6, 2.7)
            if abs(math.atan2(math.sin(a + math.pi / 2), math.cos(a + math.pi / 2))) < 0.4:
                continue
            px, py = math.cos(a) * rr, math.sin(a) * rr
            if k % 3 == 0:
                bm_ico(bm, rnd.uniform(0.2, 0.45), loc=(px, py, 0.02), scale=(1.4, 1.0, 0.3), subdiv=1, rough=0.3, mi=0)
            else:
                for g in range(6):
                    aa = g * 1.05
                    bm_cyl(bm, 0.025, 0.0, rnd.uniform(0.25, 0.45), loc=(px + math.cos(aa) * 0.05, py + math.sin(aa) * 0.05, 0.15),
                           rot=(math.cos(aa) * 0.35, math.sin(aa) * 0.35, 0), seg=4, mi=1)
        for k in range(5):  # 小蘑菇（推测）
            a = rnd.uniform(0, 6.283)
            px, py = math.cos(a) * 2.5, math.sin(a) * 2.5
            bm_cyl(bm, 0.03, 0.03, 0.12, loc=(px, py, 0.06), seg=6, mi=2)
            bm_sphere(bm, (0.08, 0.08, 0.04), loc=(px, py, 0.13), seg=10, rings=6, mi=3)
    obj("Bears_TreeHome_Moss_Grass_Mushrooms", "树洞里的苔藓、小草和小蘑菇", [moss, mat("Grass_Cave", "#5aa04a", rough=0.7),
                                                                      mat("Mushroom_Stem", "#e9e0c8"), mat("Mushroom_Cap_Red", "#c8462e")], greens,
        status="observed", note="B1：树根上的苔藓、地上的小草；小蘑菇为推测")
    li = bpy.data.lights.new("Bears_TreeHome_Light", "POINT")
    li.energy = 160
    li.color = (1.0, 0.85, 0.62)
    li.shadow_soft_size = 0.6
    lo = bpy.data.objects.new("Bears_TreeHome_Light", li)
    INT.objects.link(lo)
    lo.parent = root
    lo.location = (0, 0, 3.6)

    # 蜂巢树 + 叠圈蜂巢（第一季片头可见）
    hx, hy = HONEYTREE
    linked(bpy.data.objects["Proto_Broadleaf_1"], "Tree_HoneyTree", COLL["Forest_Trees"], (hx, hy, ground(hx, hy) - 0.15),
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


def build_monkey_cave():
    """吉吉和毛毛的山洞（依据 hdslb 剧照 M1）：长满苔藓的灰绿色大石堆成的山包，正面一个不规则的黑洞口，
    洞口上方石头上刻着图案；洞前是一层层平整的石板平台，平台前有两根雕刻的木图腾柱；周围灌木、蕨类，右侧云杉。
    洞内空间和吉吉的生活区、毛毛的休息区没有原版画面，全部为推测。局部 -Y 为洞口。"""
    C = COLL["MonkeyCave"]
    P = MONKEYCAVE
    gz = ground(P["x"], P["y"])
    root = empty("MonkeyCave_Root", C, (P["x"], P["y"], gz), (0, 0, P["rot"]), size=2.0,
                 props=dict(cn="吉吉和毛毛的山洞（根）", status="observed", note="外观依据 M1；洞内和在地图上的位置为推测"))
    rnd = random.Random(41)
    rock = mat_lake_rock("Rock_Cave_GreyGreen_Moss", "#566557", "#687868", algae="#5f8a3c", speck="#a9b3a4", algae_amt=1.2, speck_amt=0.1)
    rock2 = mat_lake_rock("Rock_Cave_Grey", "#5f665f", "#737b72", algae="#5f8a3c", speck="#a9b3a4", algae_amt=0.6, speck_amt=0.05)
    # 山包主体：一大块粗糙岩体，挖出洞室和洞口通道（布尔修改器）
    bm = bmesh.new()
    ret = bmesh.ops.create_icosphere(bm, subdivisions=4, radius=1.0)
    for v in ret["verts"]:
        k = 1 + 0.18 * noise.noise(v.co * 1.6 + Vector((2.1, 0.3, 1.0))) + 0.06 * noise.noise(v.co * 5)
        v.co = Vector((v.co.x * 6.8 * k, v.co.y * 6.0 * k + 1.6, v.co.z * 7.2 * k + 1.4))  # M1：高高的石山
    body = new_obj("MonkeyCave_Rock_Mound", bm, C, [rock], smooth_shade=True, parent=root,
                   props=dict(cn="山包主体（洞室和洞口用布尔修改器挖出）", status="observed", note="M1：灰绿色、长苔藓的大石山包"))
    add_cutters(body, C, [("Chamber", (3.4, 3.2, 2.5), (0, 1.8, 1.2), 0.0), ("Entrance_Tunnel", (1.25, 3.1, 1.45), (0, -2.9, 1.15), 0.0)], "MonkeyCave")
    DOOR_PASSAGES.append(("猴洞洞口", "MonkeyCave_Root", (-0.6, 0.6, -5.4, -1.0, 0.2, 1.9)))
    # 外面堆着的大圆石（避开洞口），洞口两侧和上方的“门框”石
    bm = bmesh.new()
    for k in range(16):
        a = rnd.uniform(0, 2 * math.pi)
        el = rnd.uniform(0.1, 1.3)
        if abs(math.atan2(math.sin(a + math.pi / 2), math.cos(a + math.pi / 2))) < 0.5 and el < 0.7:
            continue
        rr = rnd.uniform(1.2, 2.2)
        px, py, pz = math.cos(a) * math.cos(el) * 7.0, math.sin(a) * math.cos(el) * 6.3 + 1.6, math.sin(el) * 7.0 + 1.0
        bm_ico(bm, rr, loc=(px, py, pz), scale=(1.25, 1.0, 0.8), subdiv=2, rough=0.35, seed=k * 1.7)
    for (px, py, pz, rr, sc) in ((-1.9, -4.2, 1.2, 1.15, (0.9, 1.0, 1.4)), (1.9, -4.2, 1.1, 1.1, (0.9, 1.0, 1.4)), (0.0, -4.0, 3.4, 1.35, (1.5, 0.9, 0.7))):
        bm_ico(bm, rr, loc=(px, py, pz), scale=sc, subdiv=3, rough=0.2, seed=px + pz)
    new_obj("MonkeyCave_Boulders", bm, C, [rock2], smooth_shade=True, parent=root,
            props=dict(cn="山包外圆石和洞口两侧、上方的大石", status="observed", note="M1；石块数量和位置为推测"))
    # 洞口上方石头上的刻纹（M1 可见，有图案；图案细节看不清，用简单线条代替）
    bm = bmesh.new()
    bm_torus(bm, 0.28, 0.035, loc=(0, -5.22, 3.45), rot=(math.pi / 2, 0, 0), seg=20, rseg=4)
    for (dx, dz, ang) in ((-0.12, 0.05, 0.6), (0.14, 0.02, -0.5), (0.0, -0.15, 0.0)):
        bm_cube(bm, (0.05, 0.03, 0.3), loc=(dx, -5.25, 3.45 + dz), rot=(0, ang, 0))
    new_obj("MonkeyCave_Rock_Carving", bm, C, [mat("Carving_Pale", "#d9dccf", rough=0.8)], parent=root,
            props=dict(cn="洞口上方的石刻图案", status="observed", note="M1：洞口上方石头上刻着浅色图案；图案细节为推测"))
    # 洞前石板平台（M1：一层层平整石板）和台阶
    bm = bmesh.new()
    for (w, d, h, px, py, pz) in ((5.6, 2.6, 0.55, 0.0, -5.7, 0.27), (7.2, 2.2, 0.45, -0.3, -7.8, 0.02), (2.6, 1.8, 0.6, -3.8, -6.0, 0.6),
                                  (2.2, 1.6, 0.55, 3.6, -6.2, 0.55), (3.2, 1.4, 0.35, 1.0, -9.4, -0.1)):
        bm_cube(bm, (w, d, h), loc=(px + rnd.uniform(-0.1, 0.1), py, pz), rot=(rnd.uniform(-0.02, 0.02), rnd.uniform(-0.02, 0.02), rnd.uniform(-0.06, 0.06)))
    pl = new_obj("MonkeyCave_Stone_Platform", bm, C, [rock2], parent=root, props=dict(cn="洞前石板平台", status="observed", note="M1；尺寸为推测"))
    md = pl.modifiers.new("Bevel_Soft", "BEVEL")
    md.width = 0.12
    md.segments = 2
    # 两根雕刻木图腾柱（M1 平台前）
    wood = mat_noise("Wood_Totem", "#7a5a3c", "#8d6a48", scale=8)
    dark = mat("Wood_Totem_Carve", "#3a2a1c", rough=0.8)
    for side, px in (("Left", -2.6), ("Right", 2.4)):
        bm = bmesh.new()
        bm_cube(bm, (0.5, 0.36, 1.5), loc=(0, 0, 0.75), mi=0)
        bm_cube(bm, (0.6, 0.42, 0.12), loc=(0, 0, 1.5), mi=0)
        for ex in (-0.12, 0.12):
            bm_cube(bm, (0.1, 0.05, 0.08), loc=(ex, -0.18, 1.15), mi=1)
        bm_cube(bm, (0.26, 0.05, 0.07), loc=(0, -0.18, 0.85), mi=1)
        bm_cube(bm, (0.08, 0.06, 0.18), loc=(0, -0.2, 1.0), mi=0)
        ob = new_obj(f"MonkeyCave_Totem_{side}", bm, C, [wood, dark], parent=root,
                     props=dict(cn="雕刻木图腾柱", status="observed", note="M1：平台前两根带人脸雕刻的木柱；雕刻细节为推测"))
        ob.location = (px, -8.6, 0.24)
        ob.rotation_euler = (0, 0, rnd.uniform(-0.2, 0.2))
    # 洞口周围的灌木和蕨类
    for k, (px, py) in enumerate(((-4.8, -4.6), (4.6, -4.2), (-5.9, -7.4), (5.7, -8.0), (-7.4, -1.6), (7.2, -1.0))):
        proto = bpy.data.objects[f"Proto_Bush_{k % 3}"] if f"Proto_Bush_{k % 3}" in bpy.data.objects else None
        if proto:
            ob = linked(proto, f"MonkeyCave_Bush_{k}", C, (px, py, 0.1), (0, 0, k), 1.2, props=dict(cn="洞口周围的灌木", status="observed", note="M1"))
            ob.parent = root
    # 洞内（全部推测）。洞内地面抬到洞室范围里最高的地形之上，避免山坡地形从地面冒出来
    INT = coll("MonkeyCave_Interior", C)
    cR = Matrix.Rotation(P["rot"], 3, "Z")
    fz = max(ground(*(Vector((P["x"], P["y"], 0)) + cR @ Vector((dx, 1.8 + dy, 0)))[:2]) - gz
             for dx in (-3.0, -1.5, 0, 1.5, 3.0) for dy in (-2.8, -1.4, 0, 1.4, 2.8)) + 0.03
    fz = max(0.0, fz)

    def obj(name, cn, mats, build, loc, rot=(0, 0, 0), floor=True, note="洞内没有原版画面，摆设为推测"):
        bm = bmesh.new()
        build(bm)
        ob = new_obj(name, bm, INT, mats, smooth_shade=True, parent=root, props=dict(cn=cn, status="inferred", note=note))
        ob.location = (loc[0], loc[1], loc[2] + fz)
        ob.rotation_euler = rot
        ob["position_status"] = "inferred"
        if floor:
            ob["room"] = "MonkeyCave"
            ob["floor_item"] = True
            ob["floor_z_world"] = gz + fz
            ob["overlap_check"] = True
        return ob
    obj("MonkeyCave_Floor", "洞内地面", [mat_noise("Soil_Cave", "#6d6252", "#7d7262", scale=5)],
        lambda bm: bm_cyl(bm, 3.3, 3.3, 0.06, loc=(0, 0, -0.03), seg=40), (0, 1.8, 0), floor=False)
    obj("MonkeyCave_JiJi_Stone_Seat", "吉吉的石座和树叶垫（推测）", [rock2, mat_noise("Leaf_Cushion", "#6a9a3a", "#82b04a", scale=8)],
        lambda bm: (bm_ico(bm, 0.6, loc=(0, 0, 0.335), scale=(1.1, 0.9, 0.55), subdiv=2, rough=0.15, mi=0),
                    bm_ico(bm, 0.45, loc=(0, 0, 0.655), scale=(1.1, 0.9, 0.2), subdiv=2, rough=0.2, mi=1)), (-1.2, 3.2, 0))
    obj("MonkeyCave_MaoMao_Straw_Nest", "毛毛的草窝（推测）", [mat_noise("Straw_Nest", "#c9a85a", "#b8964a", scale=14)],
        lambda bm: bm_torus(bm, 0.45, 0.18, loc=(0, 0, 0.12), seg=20, rseg=8, scale=(1.0, 0.8, 0.8)), (1.5, 2.6, 0))
    obj("MonkeyCave_Banana_Leaf_Pile", "香蕉叶和果子（推测）", [mat("Banana_Leaf", "#4f9a3a", rough=0.6), mat("Fruit_Yellow", "#f0c430")],
        lambda bm: ([bm_ico(bm, 0.5, loc=(i * 0.2, 0, 0.05 + i * 0.04), scale=(1.4, 0.5, 0.06), subdiv=1, mi=0) for i in range(3)],
                    [bm_sphere(bm, (0.08, 0.08, 0.18), loc=(0.2 + i * 0.12, 0.1, 0.22), rot=(0, 0.6, 0), seg=10, rings=6, mi=1) for i in range(3)]),
        (0.4, 4.3, 0))
    li = bpy.data.lights.new("MonkeyCave_Light", "POINT")
    li.energy = 120
    li.color = (1.0, 0.86, 0.66)
    lo = bpy.data.objects.new("MonkeyCave_Light", li)
    INT.objects.link(lo)
    lo.parent = root
    lo.location = (0, 2.0, 2.6 + fz)


def build_squirrel_tree():
    """蹦蹦的松鼠窝：一棵大树的树干上、粗树枝和树干相接处开一个小洞（候选洞口 A），里面是小洞室。
    S1：爱奇艺剧照里蹦蹦站在一根粗树枝上，树枝和树干相接处有一个深色竖缝——只能说明那里可能有洞，不能证明洞口位置和大小。
    洞口 A 放在粗树枝根部正上方（局部方位 -0.4 rad），宽 0.2 m、高 0.44 m：比 S1 的缝略宽，是为了让 0.69 m 高的蹦蹦能钻进去（比例测试 ST03）。
    第一季第 1 集（其他版本）截图里蹦蹦的树洞里堆满松果，用作辅助。洞室大小、松果堆、睡窝都是推测。局部 +X 为树枝方向。"""
    C = COLL["SquirrelNest"]
    P = SQUIRRELTREE
    gz = ground(P["x"], P["y"])
    root = empty("SquirrelNest_Tree_Root", C, (P["x"], P["y"], gz), (0, 0, P["rot"]), size=1.5,
                 props=dict(cn="蹦蹦的松鼠窝大树（根）", status="inferred", note="树干和树枝依据 S1；洞口、洞室和在地图上的位置为推测"))
    rnd = random.Random(61)
    bark = mat_noise("Bark_Squirrel_Tree_Cracked", "#8f6c4c", "#b18d66", scale=5, bump=0.6, stretch=(1.0, 1.0, 0.45))
    bm = bmesh.new()
    bm_tube(bm, [(0, 0, -0.4), (0, 0, 2), (0.05, 0, 5), (0.0, 0.05, 8), (0.05, 0, 11)], [1.15, 0.92, 0.85, 0.7, 0.45], seg=20)
    trunk = new_obj("SquirrelNest_Trunk", bm, C, [bark], smooth_shade=True, parent=root,
                    props=dict(cn="大树树干（裂纹树皮）", status="observed", note="S1：浅棕色、龟裂的树皮"))
    add_cutters(trunk, C, [("Nest_Chamber", (0.55, 0.5, 0.6), (0.1, 0, 4.85), 0.0), ("Entrance_A_Slot", (0.2, 0.62, 0.44), (0.6 * math.cos(-0.4), 0.6 * math.sin(-0.4), 4.87), -0.4 - math.pi / 2)],
                "SquirrelNest")
    bm = bmesh.new()
    bm_tube(bm, [(0.6, 0, 4.25), (2.0, 0.05, 4.3), (3.6, 0.1, 4.45), (4.8, 0.2, 4.6)], [0.36, 0.32, 0.26, 0.15], seg=14)
    for k in range(6):
        z = 6.0 + k * 0.9
        a = k * 2.1
        bm_tube(bm, [(math.cos(a) * 0.5, math.sin(a) * 0.5, z), (math.cos(a) * 2.2, math.sin(a) * 2.2, z + 0.5), (math.cos(a) * 3.4, math.sin(a) * 3.4, z + 0.9)],
                [0.2, 0.13, 0.05], seg=8)
    new_obj("SquirrelNest_Branches", bm, C, [bark], smooth_shade=True, parent=root,
            props=dict(cn="粗树枝（蹦蹦站的那根）和上面的树枝", status="observed", note="S1：粗横枝；上方树枝为推测"))
    bm = bmesh.new()
    for k in range(5):
        z = 7.0 + k * 1.4
        bm_cyl(bm, 3.2 - k * 0.5, 0.4, 2.4, loc=(0, 0, z), seg=14)
    new_obj("SquirrelNest_Canopy", bm, C, [MATS.get("Foliage_Spruce") or mat("Foliage_Spruce_Generic", "#2f6b3a", rough=0.8)], smooth_shade=True, parent=root,
            props=dict(cn="树冠（推测：S1 背景是云杉，这棵树是什么树看不清）", status="inferred"))
    INT = coll("SquirrelNest_Interior", C)
    pine = mat_noise("Pinecone_Brown", "#7a4e2a", "#90603a", scale=12)

    def pile(bm):
        for k in range(16):
            a = rnd.uniform(0, 6.283)
            rr = rnd.uniform(0.0, 0.28)
            bm_sphere(bm, (0.06, 0.06, 0.09), loc=(math.cos(a) * rr, math.sin(a) * rr, 0.07 + (0.28 - rr) * 0.4 + rnd.uniform(0, 0.05)),
                      rot=(rnd.uniform(-1, 1), rnd.uniform(-1, 1), 0), seg=8, rings=6)
    ob = new_obj("SquirrelNest_Pinecone_Pile", bpy_bm(pile), INT, [pine], smooth_shade=True, parent=root,
                 props=dict(cn="洞里的松果堆（推测）", status="inferred", note="第一季第 1 集（其他版本）：蹦蹦的树洞里堆满松果；四季篇没有画面"))
    ob.location = (-0.1, 0.12, 4.3)
    ob = new_obj("SquirrelNest_Leaf_Bed", bpy_bm(lambda bm: bm_torus(bm, 0.18, 0.08, loc=(0, 0, 0.05), seg=16, rseg=6)), INT,
                 [mat_noise("Leaf_Bed_Dry", "#b8863a", "#c99a48", scale=10)], smooth_shade=True, parent=root,
                 props=dict(cn="睡窝（推测）", status="inferred", note="没有画面"))
    ob.location = (0.2, -0.22, 4.3)
    li = bpy.data.lights.new("SquirrelNest_Chamber_Light", "POINT")
    li.energy = 1.5
    li.shadow_soft_size = 0.1
    li.color = (1.0, 0.85, 0.6)
    lo = bpy.data.objects.new("SquirrelNest_Chamber_Light", li)
    INT.objects.link(lo)
    lo.parent = root
    lo.location = (0.05, 0.0, 4.9)
    empty("SquirrelNest_Candidate_Entrance_B", C, (-0.8, 0.0, 7.2), size=0.4, parent=root,
          props=dict(cn="候选洞口 B（只是标记，没有挖洞）", status="inferred", note="另一个可能的洞口位置，等截图确认"))
    DOOR_PASSAGES.append(("松鼠窝洞口 A", "SquirrelNest_Tree_Root", (0.52, 0.6, -0.3, -0.18, 4.68, 5.05)))


def bpy_bm(build):
    bm = bmesh.new()
    build(bm)
    return bm


# ------------------------------------------------------------------------------------------------
# 阶段 5：皮卡（第一季截图；四季篇是否同一辆车不确定 → 推测）


def build_pickup():
    """光头强的蓝色皮卡，逐部件按第一季第 1 集截图制作（见 REFERENCE_CATALOG.md 第 1 节）。
    局部坐标：+Y 车头，+X 车身右侧，Z 向上；原点在车底中心的地面上。
    尺寸为估算：车长约 5.3 m，宽 2.0 m（含轮拱），高 2.3 m，轮胎直径 1.05 m，轴距 3.1 m。"""
    V = COLL["Vehicles"]
    x, y, rot = HOUSE["x"] + 22.0, HOUSE["y"] + 13.6, math.radians(-100)  # 院外土路上（R1 院子里看不到皮卡；位置为推测）
    root = empty("Vehicle_Pickup_Root", V, (x, y, ground(x, y)), (0, 0, rot), size=1.5,
                 props=dict(cn="光头强的蓝色皮卡", status="inferred",
                            note="各部件按第一季截图（S1E1-18/25/33/39/47/60 等）制作；四季篇是否同一辆车无法确认"))
    blue = mat_noise("Paint_Pickup_Blue", "#2a58b8", "#3366c4", scale=14, rough=0.35, bump=0.02)
    blue_dark = mat("Paint_Pickup_Blue_Dark", "#21468f", rough=0.45)
    dark = mat("Pickup_Chassis_Dark", "#25282c", rough=0.6)
    chrome = mat("Chrome", "#d5dbe0", metal=0.95, rough=0.15)
    glass = mat("Glass_Car", "#9fc0d4", rough=0.06, transmission=0.7)
    seat = mat_noise("Seat_Orange_Cloth", "#c9662a", "#dc7a35", scale=30, rough=0.85, bump=0.05)
    plate = mat("Plate_Yellow", "#f2c521", rough=0.5)
    plate_ink = mat("Plate_Ink_Black", "#151515", rough=0.5)
    amber = mat("Light_Tail_Amber", "#f0a020", emit="#ff9a10", emit_strength=0.3)
    red = mat("Light_Tail_Red", "#d8261e", emit="#ff2010", emit_strength=0.4)
    white = mat("Light_Reverse_White", "#f4f4f0", rough=0.2)
    head = mat("Light_Head", "#f6f3e4", emit="#fff8e0", emit_strength=0.5)
    tire = MATS.get("Rubber_Tire") or mat("Rubber_Tire", "#232426", rough=0.9)
    rim = mat("Rim_Silver_Steel", "#b9c0c6", metal=0.7, rough=0.3)

    WB, TR, R = 3.1, 0.93, 0.525  # 轴距、轮距半宽、轮胎半径
    SILL, BELT, ROOF = 1.02, 1.6, 2.28  # 车门下沿、车窗下沿、车顶高度
    CAB_F, CAB_B = 0.78, -0.48  # 驾驶室前后（风挡根部 / 驾驶室后墙）
    BED_B = -2.58

    def part(name, cn, mats, build, smooth_shade=False, bevel=0.0, status="observed", note=None, loc=(0, 0, 0), rot=(0, 0, 0)):
        bm = bmesh.new()
        build(bm)
        ob = new_obj(name, bm, V, mats, smooth_shade=smooth_shade, parent=root, props=dict(cn=cn, status=status, note=note))
        ob.location = loc
        ob.rotation_euler = rot
        if bevel:
            md = ob.modifiers.new("Bevel_Rounded", "BEVEL")
            md.width = bevel
            md.segments = 3
            md.limit_method = "ANGLE"
            md.harden_normals = False
        return ob

    def tubes(bm, segs, r, mi=0):
        for a, b in segs:
            bm_tube(bm, [a, b], [r, r], seg=10, mi=mi)

    # 车架、车桥、油箱（抬高底盘下可见）
    part("Vehicle_Pickup_Chassis", "车架和车桥（抬高底盘）", [dark], lambda bm: (
        [bm_cube(bm, (0.14, 5.0, 0.18), loc=(sx * 0.55, -0.1, 0.82)) for sx in (-1, 1)],
        [bm_cube(bm, (1.2, 0.12, 0.14), loc=(0, yy, 0.82)) for yy in (2.0, 0.6, -1.0, -2.3)],
        [bm_cyl(bm, 0.09, 0.09, 2 * TR - 0.3, loc=(0, yy, R), rot=(0, math.pi / 2, 0), seg=10) for yy in (WB / 2, -WB / 2)],
        [bm_cyl(bm, 0.06, 0.06, 0.5, loc=(sx * 0.55, yy, R + 0.2), rot=(0, 0, 0), seg=8) for sx in (-1, 1) for yy in (WB / 2, -WB / 2)],
        bm_cube(bm, (0.6, 0.7, 0.3), loc=(0.55, -0.9, 0.85))), status="inferred", note="车底细节剧照看不清")
    # 车头：引擎盖 + 前翼子板（圆润）
    part("Vehicle_Pickup_Body_Front", "车头（引擎盖、翼子板）", [blue], lambda bm: (
        bm_cube(bm, (1.82, 2.4 - CAB_F + 0.05, 0.58), loc=(0, (CAB_F + 2.4) / 2, SILL + 0.27)),
        bm_cube(bm, (1.7, 0.4, 0.12), loc=(0, 2.25, SILL + 0.6), rot=(0.12, 0, 0))), bevel=0.09, note="S1E1-25：圆润的长车头")
    # 驾驶室下半（车门以外的部分）和车顶、立柱
    part("Vehicle_Pickup_Cab_Body", "驾驶室车身", [blue], lambda bm: (
        bm_cube(bm, (1.82, 0.12, BELT - SILL + 0.05), loc=(0, CAB_F - 0.02, (SILL + BELT) / 2)),
        bm_cube(bm, (1.82, 0.12, BELT - SILL + 0.05), loc=(0, CAB_B + 0.06, (SILL + BELT) / 2)),
        bm_cube(bm, (1.7, CAB_F - CAB_B - 0.35, 0.08), loc=(0, (CAB_F + CAB_B) / 2 - 0.15, ROOF - 0.04)),
        [bm_tube(bm, [(sx * 0.86, CAB_F, BELT), (sx * 0.83, CAB_F - 0.42, ROOF - 0.04)], [0.05, 0.05], seg=8) for sx in (-1, 1)],
        [bm_cube(bm, (0.08, 0.14, ROOF - BELT), loc=(sx * 0.85, CAB_B + 0.08, (BELT + ROOF) / 2)) for sx in (-1, 1)],
        [bm_cube(bm, (0.06, 0.06, ROOF - BELT), loc=(sx * 0.85, CAB_F - 0.75, (BELT + ROOF) / 2)) for sx in (-1, 1)],
        bm_cube(bm, (1.82, 0.06, ROOF - BELT), loc=(0, CAB_B + 0.03, (BELT + ROOF) / 2))), bevel=0.04,
        note="S1E1-41/42：平车顶；S1E1-20：侧窗与三角窗")
    # 车窗玻璃：前风挡、侧窗、三角窗、后窗
    part("Vehicle_Pickup_Glass", "车窗玻璃", [glass], lambda bm: (
        bm_cube(bm, (1.62, 0.02, 0.78), loc=(0, CAB_F - 0.21, (BELT + ROOF) / 2), rot=(-0.5, 0, 0)),
        [bm_cube(bm, (0.02, CAB_F - CAB_B - 0.55, ROOF - BELT - 0.08), loc=(sx * 0.855, (CAB_F + CAB_B) / 2 - 0.12, (BELT + ROOF) / 2 - 0.02)) for sx in (-1, 1)],
        bm_cube(bm, (1.5, 0.02, 0.5), loc=(0, CAB_B, BELT + 0.35))), note="S1E1-20/33")
    # 车门（左右各一，可单独打开）：门板、镀铬把手、下部饰条
    for sx, sn in ((-1, "Left"), (1, "Right")):
        part(f"Vehicle_Pickup_Door_{sn}", "车门（原点在铰链，可绕 Z 轴打开）", [blue, chrome, dark], lambda bm, sx=sx: (
            bm_cube(bm, (0.06, 1.1, BELT - SILL), loc=(0, -0.55, (BELT + SILL) / 2 - SILL), mi=0),
            bm_cube(bm, (0.03, 0.22, 0.05), loc=(sx * 0.04, -0.9, BELT - SILL - 0.12), mi=1),
            bm_cube(bm, (0.02, 1.08, 0.035), loc=(sx * 0.035, -0.55, 0.15), mi=1),
            bm_cube(bm, (0.012, 0.012, BELT - SILL), loc=(sx * 0.035, -1.09, (BELT - SILL) / 2), mi=2)),
            bevel=0.025, note="S1E1-19：镀铬门把手、车门下部横饰条", loc=(sx * 0.92, CAB_F - 0.06, SILL))
    # 车斗：底板、侧板、前板、边沿、绳钩；尾门单独
    def bed(bm):
        L = CAB_B - 0.1 - BED_B
        yc = (CAB_B - 0.1 + BED_B) / 2
        bm_cube(bm, (1.82, L, 0.12), loc=(0, yc, SILL + 0.06), mi=0)
        for sxx in (-1, 1):
            bm_cube(bm, (0.07, L, 0.6), loc=(sxx * 0.875, yc, SILL + 0.36), mi=0)
            bm_cube(bm, (0.14, L, 0.05), loc=(sxx * 0.87, yc, SILL + 0.68), mi=1)
            for k in range(5):
                bm_torus(bm, 0.035, 0.008, loc=(sxx * 0.95, yc - L / 2 + 0.25 + k * (L - 0.5) / 4, SILL + 0.6), rot=(0, math.pi / 2, 0), seg=10, rseg=4, mi=2)
        bm_cube(bm, (1.82, 0.07, 0.6), loc=(0, CAB_B - 0.12, SILL + 0.36), mi=0)
    part("Vehicle_Pickup_Bed", "车斗（带绳钩）", [blue, blue_dark, chrome], bed, bevel=0.03, note="S1E1-49/51：车斗边沿一排绳钩")
    part("Vehicle_Pickup_Tailgate", "尾门（带镀铬把手）", [blue, chrome], lambda bm: (
        bm_cube(bm, (1.72, 0.07, 0.6), loc=(0, 0, 0.3), mi=0),
        bm_cube(bm, (0.32, 0.03, 0.08), loc=(0, -0.05, 0.47), mi=1)), bevel=0.02, note="S1E1-47：尾门中间镀铬把手",
        loc=(0, BED_B + 0.04, SILL + 0.06))
    # 轮拱（外扩）
    def arches(bm):
        for yy in (WB / 2, -WB / 2):
            for sxx in (-1, 1):
                bm_torus(bm, R + 0.1, 0.1, loc=(sxx * 0.93, yy, R + 0.02), rot=(0, math.pi / 2, 0), seg=18, rseg=6, arc=math.pi, mi=0,
                         scale=(1.0, 1.0, 1.4))
    part("Vehicle_Pickup_Fender_Flares", "外扩轮拱", [blue], arches, smooth_shade=True, note="S1E1-27")
    # 车头：镀铬竖条格栅、方形大灯、前保险杠、护杠、前车牌
    def front(bm):
        yf = 2.42
        bm_cube(bm, (1.1, 0.06, 0.44), loc=(0, yf, SILL + 0.3), mi=0)
        for i in range(11):
            bm_cube(bm, (0.035, 0.06, 0.38), loc=(-0.5 + i * 0.1, yf + 0.03, SILL + 0.3), mi=1)
        for sxx in (-1, 1):
            bm_cube(bm, (0.32, 0.06, 0.22), loc=(sxx * 0.74, yf, SILL + 0.33), mi=0)
            bm_cube(bm, (0.27, 0.02, 0.17), loc=(sxx * 0.74, yf + 0.035, SILL + 0.33), mi=2)
        bm_cube(bm, (1.96, 0.22, 0.22), loc=(0, yf + 0.12, SILL - 0.06), mi=3)
        bm_cube(bm, (0.5, 0.02, 0.15), loc=(0, yf + 0.235, SILL - 0.06), mi=4)
    part("Vehicle_Pickup_Front_Grille_Lights_Bumper", "镀铬格栅、方形大灯、前保险杠、黄色前车牌", [chrome, MATS.get("Chrome_Bars") or chrome, head, dark, plate],
         front, bevel=0.015, note="S1E1-18/25")
    part("Vehicle_Pickup_Bull_Bar", "镀铬护杠", [chrome], lambda bm: tubes(bm, [
        ((-0.5, 2.68, SILL - 0.1), (-0.5, 2.68, SILL + 0.55)), ((0.5, 2.68, SILL - 0.1), (0.5, 2.68, SILL + 0.55)),
        ((-0.62, 2.66, SILL + 0.55), (0.62, 2.66, SILL + 0.55)), ((-0.85, 2.62, SILL + 0.2), (0.85, 2.62, SILL + 0.2)),
        ((-0.5, 2.68, SILL - 0.1), (-0.5, 2.5, SILL - 0.1)), ((0.5, 2.68, SILL - 0.1), (0.5, 2.5, SILL - 0.1))], 0.045),
        smooth_shade=True, note="S1E1-25：格栅前竖管 + 横管护杠")
    # 车尾：竖条组合尾灯（上琥珀、红、白、红）、后保险杠、后车牌
    def rear(bm):
        yb = BED_B + 0.0
        for sxx in (-1, 1):
            for k, mi in enumerate((0, 1, 2, 1)):
                bm_cube(bm, (0.1, 0.05, 0.12), loc=(sxx * 0.86, yb - 0.01, SILL + 0.62 - k * 0.13), mi=mi)
        bm_cube(bm, (1.9, 0.2, 0.18), loc=(0, yb - 0.1, SILL - 0.08), mi=3)
        bm_cube(bm, (0.5, 0.02, 0.15), loc=(0, yb - 0.025, SILL + 0.17), mi=4)
    part("Vehicle_Pickup_Rear_Lights_Bumper", "竖条组合尾灯、后保险杠、黄色后车牌", [amber, red, white, dark, plate], rear, bevel=0.01,
         note="S1E1-35/40/47")
    # 车牌文字（S1E1-33/47）：前五个字符读作“Y2 MM”；最后一个字符分辨率太低，K/R 难以区分，按 R（推测）
    fc = bpy.data.curves.new("Vehicle_Pickup_Plate_Text", "FONT")
    fc.body = "Y2 MMR"
    fc.size = 0.085
    fc.align_x = "CENTER"
    fc.align_y = "CENTER"
    fc.extrude = 0.004
    fc.materials.append(plate_ink)
    to = bpy.data.objects.new("Vehicle_Pickup_Plate_Text", fc)
    V.objects.link(to)
    to.parent = root
    to.location = (0, BED_B - 0.04, SILL + 0.17)
    to.rotation_euler = (math.pi / 2, 0, 0)  # 字面朝车尾（-Y），从车后看是正读
    tag(to, cn="后车牌文字 Y2 MMR（最后一个字母不确定）", status="inferred", note="S1E1-33/47：最后一个字符看不清，K 或 R")
    # 侧踏杠、后视镜
    part("Vehicle_Pickup_Side_Steps", "镀铬侧踏杠", [chrome], lambda bm: (
        tubes(bm, [((sxx * 1.0, -0.4, 0.86), (sxx * 1.0, 0.75, 0.86)) for sxx in (-1, 1)], 0.04),
        tubes(bm, [((sxx * 1.0, yy, 0.86), (sxx * 0.75, yy, 0.86)) for sxx in (-1, 1) for yy in (-0.3, 0.65)], 0.025)),
        smooth_shade=True, note="S1E1-39/43")
    part("Vehicle_Pickup_Mirrors", "方形大后视镜（镀铬支架）", [chrome, dark, glass], lambda bm: [
        (bm_tube(bm, [(sxx * 0.9, CAB_F - 0.08, BELT + 0.05), (sxx * 1.08, CAB_F - 0.05, BELT + 0.12)], [0.02, 0.02], seg=6, mi=0),
         bm_cube(bm, (0.05, 0.16, 0.26), loc=(sxx * 1.12, CAB_F - 0.05, BELT + 0.2), mi=1),
         bm_cube(bm, (0.01, 0.13, 0.22), loc=(sxx * 1.12 + sxx * -0.03, CAB_F - 0.05, BELT + 0.2), mi=2)) for sxx in (-1, 1)],
        note="S1E1-20")
    # 车内：橙色座椅（带头枕）、方向盘、仪表台
    part("Vehicle_Pickup_Interior", "车内：橙色座椅、方向盘、仪表台", [seat, dark], lambda bm: (
        bm_cube(bm, (1.55, 0.55, 0.18), loc=(0, CAB_B + 0.45, SILL + 0.38), mi=0),
        bm_cube(bm, (1.55, 0.16, 0.6), loc=(0, CAB_B + 0.18, SILL + 0.72), mi=0),
        [bm_cube(bm, (0.32, 0.12, 0.22), loc=(sxx * 0.4, CAB_B + 0.18, SILL + 1.13), mi=0) for sxx in (-1, 1)],
        bm_cube(bm, (1.6, 0.35, 0.22), loc=(0, CAB_F - 0.12, BELT - 0.05), mi=1),
        bm_torus(bm, 0.18, 0.025, loc=(-0.4, CAB_F - 0.4, BELT + 0.02), rot=(1.1, 0, 0), seg=20, rseg=6, mi=1),
        bm_cyl(bm, 0.03, 0.03, 0.4, loc=(-0.4, CAB_F - 0.25, BELT - 0.05), rot=(1.1, 0, 0), seg=6, mi=1)), bevel=0.03,
        note="S1E1-24：橙色布座椅、黑色方向盘")
    # 四个车轮：花纹越野胎 + 8 孔银色钢圈
    for wi, (sx, sy) in enumerate(((-1, WB / 2), (1, WB / 2), (-1, -WB / 2), (1, -WB / 2))):
        def wheel(bm, sx=sx):
            bm_cyl(bm, R - 0.04, R - 0.04, 0.42, rot=(0, math.pi / 2, 0), seg=28, mi=0)
            bm_torus(bm, R - 0.1, 0.1, rot=(0, math.pi / 2, 0), loc=(0.12, 0, 0), seg=28, rseg=8, mi=0)
            bm_torus(bm, R - 0.1, 0.1, rot=(0, math.pi / 2, 0), loc=(-0.12, 0, 0), seg=28, rseg=8, mi=0)
            for k in range(22):
                a = 2 * math.pi * k / 22
                for side in (-1, 1):
                    off = 0.1 * side + (0.04 if k % 2 else -0.04)
                    bm_cube(bm, (0.15, 0.16, 0.07), loc=(off, math.cos(a) * (R - 0.02), math.sin(a) * (R - 0.02)), rot=(a + math.pi / 2, 0, 0), mi=0)
            bm_cyl(bm, 0.31, 0.31, 0.43, rot=(0, math.pi / 2, 0), seg=24, mi=1)
            bm_cyl(bm, 0.09, 0.07, 0.48, rot=(0, math.pi / 2, 0), seg=12, mi=1)
            for k in range(8):
                a = 2 * math.pi * k / 8
                bm_cyl(bm, 0.035, 0.035, 0.44, loc=(0, math.cos(a) * 0.2, math.sin(a) * 0.2), rot=(0, math.pi / 2, 0), seg=8, mi=2)
        part(f"Vehicle_Pickup_Wheel_{['FL', 'FR', 'RL', 'RR'][wi]}", "越野花纹轮胎 + 8 孔银色钢圈", [tire, rim, dark], wheel,
             smooth_shade=True, note="S1E1-39：大越野胎、8 孔银色钢圈", loc=(sx * TR, sy, R))


# ------------------------------------------------------------------------------------------------
# 阶段 5：角色


def mat_fur_patch(name, fur, patch, kind, oval=(0.0, 0.82, 0.47, 0.5), front_y=-0.12, swirl=False):
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
        # |x| < 0.05 + 0.4 * (z - 0.62)，且 0.62 < z < 1.74（S1E1-10/11/62：白色 V 字从脖子到肚子）
        lim = math_node("ADD", math_node("MULTIPLY", math_node("SUBTRACT", Z, 0.62), 0.4), 0.05)
        v = soft(math_node("SUBTRACT", lim, math_node("ABSOLUTE", X)), 0.012)
        top = soft(math_node("SUBTRACT", 1.74, Z), 0.02)
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
    out = mix.outputs["Result"]
    if swirl:
        # S1E1-13/23/44：熊二身上一圈圈的弧形毛纹
        wv = nodes.new("ShaderNodeTexWave")
        wv.wave_type = "RINGS"
        wv.inputs["Scale"].default_value = 5.0
        wv.inputs["Distortion"].default_value = 1.5
        links.new(tc.outputs["Object"], wv.inputs["Vector"])
        mr = nodes.new("ShaderNodeMapRange")
        mr.inputs["To Min"].default_value = 0.86
        mr.inputs["To Max"].default_value = 1.0
        links.new(wv.outputs["Fac"], mr.inputs["Value"])
        mul = nodes.new("ShaderNodeVectorMath")
        mul.operation = "SCALE"
        links.new(out, mul.inputs[0])
        links.new(mr.outputs["Result"], mul.inputs["Scale"])
        out = mul.outputs["Vector"]
    links.new(out, b.inputs["Base Color"])
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


def bear(name_en, cn, C, pos, rot, fur, fur_dark, bib, belly, muzzle, nose, plump=1.0, eye_patch=None):
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
    body_mat = mat_fur_patch(f"{name_en}_Fur_With_{'Bib' if bib else 'Belly'}", fur, bib or belly, "bib" if bib else "belly", swirl=not bib)
    part_blob(root, C, f"{name_en}_Body", "身体（梨形，胸前毛色分区）", [body_mat], (rx, ry, rz), (0, 0, 1.0), deform=lambda co: Vector((co.x * (1 + 0.16 * -co.z), co.y * (1 + 0.12 * -co.z), co.z)),
              seg=48, rings=32)
    hz = 1.68
    part_blob(root, C, f"{name_en}_Head", "头", [M["Fur"]], (0.4, 0.37, 0.34), (0, -0.06, hz),
              deform=lambda co: Vector((co.x * (1 + 0.06 * co.z), co.y, co.z)))
    part_blob(root, C, f"{name_en}_Muzzle", "口鼻", [M["Muzzle"]], (0.26, 0.2, 0.19), (0, -0.33, hz - 0.08))
    part_blob(root, C, f"{name_en}_Nose", "鼻子", [M["Nose"]], (0.14, 0.1, 0.095), (0, -0.53, hz + 0.0), subsurf=1)
    part_blob(root, C, f"{name_en}_Mouth", "嘴", [M["Mouth"]], (0.12, 0.05, 0.035), (0, -0.5, hz - 0.15), subsurf=1)
    eyes_pair(root, C, name_en, M, 0.13, -0.36, hz + 0.12, 0.065)
    if eye_patch:  # E44、S1E1-13：熊二眼睛周围一圈浅色
        for s, sn in ((-1, "L"), (1, "R")):
            part_blob(root, C, f"{name_en}_EyePatch_{sn}", "眼周浅色毛", [mat(f"{name_en}_EyePatch", eye_patch)],
                      (0.12, 0.04, 0.11), (s * 0.13, -0.345, hz + 0.12), subsurf=1)
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
                                        Pants="#5b3f93", Stripe="#eeeeee", Shoe="#1c1a1a", Belt="#6b2a24", Hat="#8d6648",
                                        HatLight="#a98163", Brow="#3a2618", **EYE))
    for s, sn in ((-1, "L"), (1, "R")):
        part_limb(root, C, f"GuangtouQiang_Leg_{sn}", "裤腿（紫色运动裤）", [M["Pants"]], (s * 0.1, 0, 0.78), (s * 0.11, 0, 0.12), 0.075, 0.062)
        bm = bmesh.new()
        for dy in (-0.016, 0.016):
            bm_cube(bm, (0.012, 0.009, 0.62), loc=(s * 0.172, dy, 0.45), rot=(0, s * -0.02, 0))
        new_obj(f"GuangtouQiang_Pants_Stripe_{sn}", bm, C, [M["Stripe"]], parent=root,
                props=dict(cn="裤子侧边两道白条", note="U4；E44 清楚看到每条裤腿侧边两道白条"))
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
    for nm, loc, R, r, sc in (("Collar", (0, 0, 1.19), 0.135, 0.028, (1.0, 0.8, 1)), ("Hem", (0, 0, 0.82), 0.185, 0.022, (1.0, 0.76, 1))):
        bm = bmesh.new()
        bm_torus(bm, R, r, loc=loc, seg=22, rseg=8, scale=sc)
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
    part_blob(root, C, "LuoBoTou_Head", "宽脸（大片奶白色）",
              [mat_fur_patch("LuoBoTou_Head_Brown_With_Face", "#94653a", "#efdcb4", "oval", oval=(0, 0.5, 0.16, 0.1), front_y=-0.04)],
              (0.17, 0.15, 0.13), (0, -0.02, 0.53), seg=32, rings=22)
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
    part_blob(root, C, "BengBeng_Head", "头（橙色，奶黄脸）",
              [mat_fur_patch("BengBeng_Head_Orange_With_Face", "#c8642c", "#f2d892", "oval", oval=(0, 0.355, 0.085, 0.06), front_y=-0.03)],
              (0.11, 0.1, 0.1), (0, -0.01, 0.38), seg=32, rings=22)
    part_blob(root, C, "BengBeng_Head_Top", "头顶红棕色毛", [M["Top"]], (0.095, 0.085, 0.045), (0, 0.0, 0.445), subsurf=1)
    part_blob(root, C, "BengBeng_Snout", "口鼻", [M["Cream"]], (0.06, 0.05, 0.045), (0, -0.09, 0.35), subsurf=1)
    part_blob(root, C, "BengBeng_Teeth", "大门牙", [M["Teeth"]], (0.025, 0.008, 0.03), (0, -0.13, 0.31), subsurf=0)
    eyes_pair(root, C, "BengBeng", M, 0.045, -0.08, 0.42, 0.035, iris=M["Iris"])
    for s, sn in ((-1, "L"), (1, "R")):
        part_blob(root, C, f"BengBeng_Ear_{sn}", "棕色耳朵", [M["Top"]], (0.025, 0.015, 0.045), (s * 0.07, 0, 0.48), rot=(0, s * 0.35, 0), subsurf=1)
        part_limb(root, C, f"BengBeng_Arm_{sn}", "手臂", [M["Orange"]], (s * 0.08, -0.03, 0.25), (s * 0.11, -0.07, 0.15), 0.02, 0.016)
        part_blob(root, C, f"BengBeng_Foot_{sn}", "脚", [M["Orange"]], (0.03, 0.05, 0.02), (s * 0.05, -0.03, 0.02), subsurf=1)
    # 大尾巴：从身后向上弯起、尾尖向前卷的一整条蓬松尾巴，棕色夹浅色横纹（立绘、S1E1-78–81）
    tail_m = mat_stripes("BengBeng_Tail_Striped", "#6c4630", "#d9bf86", scale=4.0, axis="Z")
    cr = [n for n in tail_m.node_tree.nodes if n.type == "VALTORGB"][0].color_ramp
    cr.interpolation = "EASE"
    cr.elements[0].position = 0.84
    cr.elements[1].position = 0.93
    bm = bmesh.new()
    bm_tube(bm, [(0, 0.07, 0.1), (0, 0.17, 0.14), (0, 0.27, 0.26), (0, 0.3, 0.42), (0, 0.25, 0.55), (0, 0.15, 0.6), (0, 0.09, 0.56)],
            [0.035, 0.07, 0.11, 0.125, 0.115, 0.09, 0.05], seg=14)
    new_obj("BengBeng_Tail", bm, C, [tail_m], smooth_shade=True, subsurf=2, parent=root, props=dict(cn="棕色条纹大尾巴"))
    return root


def build_characters():
    CH = COLL
    m = MEADOW
    bear("XiongDa", "熊大", CH["Characters_XiongDa"], (m[0] - 1.6, m[1] + 2.0), math.radians(10),
         fur="#9b4f2e", fur_dark="#7c3a20", bib="#efdcc2", belly=None, muzzle="#f1e2cf", nose="#d4424a")
    bear("XiongEr", "熊二", CH["Characters_XiongEr"], (m[0] + 1.6, m[1] + 1.6), math.radians(-12),
         fur="#d6a356", fur_dark="#b9853c", bib=None, belly="#ecca8c", muzzle="#f2ddb0", nose="#5e6683", plump=1.15, eye_patch="#f0dfb2")
    guangtouqiang(CH["Characters_GuangtouQiang"], (HOUSE["x"] + 0.6, HOUSE["y"] + 9.2), math.radians(160))
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
    hz = bpy.data.objects["GQ_House_Root"].location.z
    cam("Cam_House_Interior", "木屋室内：客厅/厨房（看冰箱、水槽、圆窗、蓝色橱柜）", (hx + 0.95, hy + 2.45, hz + FOUND + 1.7),
        (hx - 2.6, hy - 2.3, hz + FOUND + 0.9), 14)
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
    build_check_cameras()


def build_check_cameras():
    """正交检查相机：每个人物正/侧/背，皮卡和木屋四视图，室内平面，地图俯视。
    相机的裁剪范围只包住目标物体，所以近处的树不会挡住画面。渲染用 render_checks.py。"""
    CC = coll("Check_Cameras", COLL["Lights_and_Cameras"])

    def ortho(name, cn, target, direction, dist, scale, clip_half, res):
        cd = bpy.data.cameras.new(name)
        cd.type = "ORTHO"
        cd.ortho_scale = scale
        cd.clip_start = max(0.05, dist - clip_half)
        cd.clip_end = dist + clip_half
        co = bpy.data.objects.new(name, cd)
        CC.objects.link(co)
        d = Vector(direction).normalized()
        co.location = Vector(target) + d * dist
        if abs(d.z) > 0.99:
            co.rotation_euler = (0, 0, 0) if d.z > 0 else (math.pi, 0, 0)
        else:
            look_at(co, target)
        co["name_cn"] = cn
        co["check_res"] = res
        return co

    def views(root_name, label, h, width, clip_half, kinds=("Front", "Side", "Back"), res="700x900"):
        r = bpy.data.objects[root_name]
        rz = r.rotation_euler.z
        fwd = Matrix.Rotation(rz, 3, "Z") @ Vector((0, -1, 0))  # 角色正面 = 局部 -Y
        right = Matrix.Rotation(rz, 3, "Z") @ Vector((1, 0, 0))
        tgt = r.location + Vector((0, 0, h / 2))
        dirs = {"Front": fwd, "Side": right, "Back": -fwd, "Left": -right, "Top": Vector((0, 0, 1))}
        names = {"Front": "正面", "Side": "侧面", "Back": "背面", "Left": "另一侧", "Top": "俯视"}
        for k in kinds:
            ortho(f"Check_{label}_{k}", f"{r.get('name_cn', label)} {names[k]}", tgt if k != "Top" else r.location,
                  dirs[k], 30 if k == "Top" else max(8, clip_half + 4), max(h, width) * 1.25, clip_half if k != "Top" else 31, res)
    for root_name, label, h, w, c in (("XiongDa_Root", "XiongDa", 2.05, 1.7, 1.3), ("XiongEr_Root", "XiongEr", 2.05, 1.9, 1.3),
                                       ("GuangtouQiang_Root", "GuangtouQiang", 1.7, 0.9, 0.6), ("TuTu_Root", "TuTu", 0.6, 0.5, 0.33),
                                       ("LuoBoTou_Root", "LuoBoTou", 0.7, 0.5, 0.33), ("BengBeng_Root", "BengBeng", 0.66, 0.6, 0.6)):
        views(root_name, label, h, w, c)
    views("Vehicle_Pickup_Root", "Pickup", 2.4, 5.6, 3.2, kinds=("Front", "Side", "Back", "Top"), res="1000x700")
    views("Crab_Rig", "Crab", 1.7, 3.8, 2.2, kinds=("Front", "Side", "Back", "Top"), res="1000x700")
    for k in ("Front", "Side", "Back", "Top"):
        bpy.data.objects[f"Check_Crab_{k}"]["hide_collections"] = "Lake_Water,Lake_Rocks,Lake_Weeds"
    # 皮卡正面 = 局部 +Y：把 Front/Back 对调
    for a, b in (("Check_Pickup_Front", "Check_Pickup_Back_tmp"), ("Check_Pickup_Back", "Check_Pickup_Front"), ("Check_Pickup_Back_tmp", "Check_Pickup_Back")):
        bpy.data.objects[a].name = b
    for n, cn in (("Check_Pickup_Front", "皮卡 正面"), ("Check_Pickup_Back", "皮卡 车尾"), ("Check_Pickup_Side", "皮卡 侧面"), ("Check_Pickup_Top", "皮卡 俯视")):
        bpy.data.objects[n]["name_cn"] = cn
    views("GQ_House_Root", "House", 8.6, 14.5, 9.0, kinds=("Front", "Side", "Back", "Top"), res="1100x700")
    for a, b in (("Check_House_Front", "Check_House_Back_tmp"), ("Check_House_Back", "Check_House_Front"), ("Check_House_Back_tmp", "Check_House_Back")):
        bpy.data.objects[a].name = b
    bpy.data.objects["Check_House_Back"]["hide_collections"] = "GuangtouQiang_Warehouse"
    for n, cn in (("Check_House_Front", "木屋 正面"), ("Check_House_Back", "木屋 背面"), ("Check_House_Side", "木屋 侧面（东）"), ("Check_House_Top", "木屋 俯视")):
        bpy.data.objects[n]["name_cn"] = cn
    hr = bpy.data.objects["GQ_House_Root"]
    ortho("Check_House_Interior_Plan", "木屋室内平面（隐藏屋顶）", hr.location + Vector((-1.2, 0.4, 1.0)), (0, 0, 1), 12, 13.2, 10.6, "1100x800")
    ortho("Check_Map_Top", "地图俯视", (0, 0, 0), (0, 0, 1), 260, 205, 300, "1400x1050")
    build_acceptance_cameras()


def build_lake_cameras():
    """湖泊初步检查相机（render_acceptance.py 的第 5 个参数传 Lake_Check_Cameras 渲染）：鸟瞰、隐藏水面的湖底俯视、
    沙滩到石崖的剖面（相机裁剪面正好切在剖面上）、隐藏水面的湖底斜视。"""
    LCC = coll("Lake_Check_Cameras", COLL["Lights_and_Cameras"])
    cx, cy, lv = LAKE["x"], LAKE["y"], LAKE["level"]
    hide_wf = "Lake_Water,Forest_Trees,Forest_Plants,Characters"

    def cam(name, cn, loc, tgt, lens=30, hide="", res="1600x1000", ortho=None, clip=0.5, rot=None):
        cd = bpy.data.cameras.new(name)
        cd.lens = lens
        cd.clip_start, cd.clip_end = clip, 2000
        co = bpy.data.objects.new(name, cd)
        LCC.objects.link(co)
        co.location = loc
        if ortho:
            cd.type = "ORTHO"
            cd.ortho_scale = ortho
        if rot is not None:
            co.rotation_euler = rot
        else:
            look_at(co, tgt)
        co["name_cn"] = cn
        co["hide_collections"] = hide
        co["acc_res"] = res
        return co
    cam("Lake_01_Aerial_With_Forest", "湖泊与周围森林鸟瞰", (cx + 30, cy - 42, 46), (cx, cy + 2, 0), lens=30)
    cam("Lake_02_Bottom_Top_NoWater", "隐藏水面后的湖底俯视（正交）", (cx, cy, 60), None, ortho=50, hide=hide_wf, res="1600x1100", rot=(0, 0, 0))
    # 剖面：沿“沙滩—湖心—石崖”方向的竖直面；相机在剖面一侧，clip_start 正好落在剖面上
    ux, uy = math.cos(CLIFF["fall"]) * LAKE["rx"], math.sin(CLIFF["fall"]) * LAKE["ry"]
    L = math.hypot(ux, uy)
    ux, uy = ux / L, uy / L
    nx_, ny_ = uy, -ux  # 剖面法线
    D = 80.0
    co = cam("Lake_03_Section_Beach_Center_Cliff", "湖底剖面：沙滩—湖心—石崖（相机裁剪面切在剖面上）",
             (cx - nx_ * D, cy - ny_ * D, lv - 1.5), (cx, cy, lv - 1.5), ortho=56, hide=hide_wf, res="1600x800", clip=D)
    co["section_axis"] = (ux, uy)
    cam("Lake_04_Bottom_Oblique_NoWater", "隐藏水面后的湖底斜视", (cx + 26, cy - 30, 20), (cx - 2, cy + 1, lv - 4), lens=28, hide=hide_wf)
    R, f, r = lake_rock_frame()
    zf = ground(R.x, R.y)
    up = Vector((0, 0, 1))
    cam("Lake_05_Ref_Still_Match_L1", "按 L1 剧照构图重建的水下镜头（预览）", R - f * 7.0 + up * (zf + 1.3), R + up * (zf + 2.9), lens=22,
        hide="Characters")
    cam("Lake_06_Rock_Group_NoWater", "岩石区全貌（隐藏水体）", R - f * 13 - r * 7 + up * (zf + 7.5), R + f * 2 + up * (zf + 1.5), lens=26, hide=hide_wf)
    cam("Lake_07_Rock_Tower_Closeup", "岩石塔近景（隐藏水体）", R - f * 5.0 + r * 1.8 + up * (zf + 2.2), R + up * (zf + 2.6), lens=30, hide=hide_wf)
    cam("Lake_08_Underwater_Wide", "湖底整体广角（水下）", R - f * 15.0 - r * 2.0 + up * (lv - 3.0), R + f * 2.0 + up * (zf + 1.0), lens=18, hide="Characters")
    cam("Lake_09_Underwater_Look_Up", "水下仰视水面", R - f * 5.5 + r * 3.0 + up * (zf + 1.0), R - f * 2.0 + r * 1.0 + up * (lv + 0.5), lens=16, hide="Characters")
    cam("Lake_10_Waterweed_Closeup", "水草近景（隐藏水体）", R - f * 2.0 - r * 3.2 + up * (zf + 0.9), R - f * 1.0 - r * 7.0 + up * (zf + 0.4), lens=24, hide=hide_wf)
    ex, ey = lake_point(math.radians(-50), 1.12)
    cam("Lake_12_Shore_Front", "湖岸正面：从沙滩入水点看湖面、石崖和瀑布", (ex, ey, ground(ex, ey) + 1.7), (cx - 4, cy + 6, lv + 3.0), lens=24, hide="Characters")
    co = cam("Lake_11_Cutaway_With_Water", "整体剖视：湖面、水下、岸边（相机裁剪面切在剖面上）",
             (cx - nx_ * D, cy - ny_ * D, lv - 1.5), (cx, cy, lv - 1.5), ortho=56, hide="Forest_Trees,Forest_Plants,Characters", res="1600x800", clip=D)


def build_still_match_cameras():
    """剧照对位相机：每台相机按一张原作剧照的构图摆放（位置是从画面判断的近似值），用来把模型和剧照并排比较。
    ref_id 对应 evidence/REFERENCE_INDEX.csv；render_still_match.py 渲染并拼对照图。"""
    SC_ = coll("Still_Match_Cameras", COLL["Lights_and_Cameras"])
    bpy.context.view_layer.update()
    B = FOUND

    def cam(name, ref, cn, root, loc, tgt, lens, extra=""):
        cd = bpy.data.cameras.new(name)
        cd.lens = lens
        cd.clip_start = 0.05
        cd.clip_end = 1500
        co = bpy.data.objects.new(name, cd)
        SC_.objects.link(co)
        M = bpy.data.objects[root].matrix_world
        co.location = M @ Vector(loc)
        look_at(co, M @ Vector(tgt))
        co["ref_id"] = ref
        co["name_cn"] = cn
        co["match_setup"] = extra
        return co
    cam("SM_R1_Yard_Overview", "R1", "院落全景（院门在画面左侧）", "GQ_House_Root", (16.0, 24.0, 6.5), (-2.0, 2.0, 2.5), 26)["clear_near"] = 14.0
    cam("SM_R2_Front_Closeup", "R2", "木屋正面近景", "GQ_House_Root", (3.6, 9.2, B + 0.9), (-0.8, 3.0, B + 1.7), 22)
    cam("SM_A45_Front_Window", "A45", "正面窗（窗扇向外上翻）", "GQ_House_Root", (-2.4, 6.4, B + 1.05), (-2.6, 3.0, B + 1.25), 26, "open_shutters")
    cam("SM_R3_Kitchen", "R3", "厨房：卧室门、冰箱、水槽、圆窗", "GQ_House_Root", (0.25, 0.9, B + 1.25), (0.0, -2.8, B + 1.05), 18)
    cam("SM_R4_Bedroom", "R4", "卧室：窗下土炕、铁炉、绿沙发、电视", "GQ_House_Root", (2.9, -1.95, B + 1.45), (2.9, 2.8, B + 0.85), 15)
    cam("SM_A65_Bedroom_Desk", "A65", "卧室书桌和火枪", "GQ_House_Root", (2.65, 0.95, B + 1.25), (1.45, -0.2, B + 0.95), 24)
    cam("SM_B1_TreeHome_Interior", "B1", "熊洞室内：后壁圆洞、石板床", "Bears_TreeHome_Root", (-0.3, -1.9, 1.05), (0.3, 3.0, 1.5), 18)
    cam("SM_M1_MonkeyCave_Front", "M1", "猴洞洞口和石板平台", "MonkeyCave_Root", (2.6, -16.5, 3.4), (0.0, -4.5, 3.4), 26)
    cam("SM_S1_Squirrel_Branch", "S1", "蹦蹦站的粗树枝和枝干相接处", "SquirrelNest_Tree_Root", (1.9, -3.6, 4.95), (1.3, 0.0, 4.75), 32)


def build_acceptance_cameras():
    """验收相机（render_acceptance.py 渲染）：木屋四面、屋顶近景、室内俯视、三个房间、仓库四面、仓库内部、储物细节、院子全景。
    hide_collections 里的集合在渲染这台相机时隐藏（例如拆掉屋顶看室内）。室外相机的 clip_start 用来切掉挡在前面的树和另一栋建筑。"""
    AC = coll("Acceptance_Cameras", COLL["Lights_and_Cameras"])
    bpy.context.view_layer.update()
    hr = bpy.data.objects["GQ_House_Root"]
    wr = bpy.data.objects["Warehouse_Root"]
    B, Bw = FOUND, WAREHOUSE["floor"]

    def cam(name, cn, root, loc, tgt, lens=40, clip=0.1, hide="", res="1600x1000", ortho=None, clear=False):
        cd = bpy.data.cameras.new(name)
        cd.lens = lens
        cd.clip_start = clip
        cd.clip_end = 1500
        co = bpy.data.objects.new(name, cd)
        AC.objects.link(co)
        M = root.matrix_world
        co.location = M @ Vector(loc)
        if ortho:
            cd.type = "ORTHO"
            cd.ortho_scale = ortho
            cd.clip_start, cd.clip_end = 1.0, 30.0
            co.rotation_euler = (0, 0, root.rotation_euler.z)
        else:
            look_at(co, M @ Vector(tgt))
            co["view_target"] = list(M @ Vector(tgt))
        co["clear_trees"] = clear
        co["name_cn"] = cn
        co["hide_collections"] = hide
        co["acc_res"] = res
        return co
    roof_h, roof_w = "GQ_House_Roof_Removable", "WH_Roof_Removable"
    wh = "GuangtouQiang_Warehouse"
    house = "GuangtouQiang_House_Exterior,GuangtouQiang_House_Interior"
    cam("Acc_01_House_Front", "木屋正面", hr, (-1.0, 19.0, 4.6), (-1.2, 0.0, 3.4), clear=True)
    cam("Acc_02_House_Back", "木屋背面（渲染时隐藏屋后的仓库）", hr, (-1.5, -17.5, 4.6), (-1.2, 0.0, 3.2), hide="GuangtouQiang_Warehouse", clear=True)
    cam("Acc_03_House_East_Side", "木屋局部 +X 侧（地图约定叫“东”，没有原作证据；从院子正对木屋时在画面左侧，卧室一侧）", hr, (18.5, 0.8, 4.6), (0.0, 0.8, 3.2), hide=wh, clear=True)
    cam("Acc_04_House_West_Side", "木屋局部 -X 侧（地图约定叫“西”；从院子正对木屋时在画面右侧，卫生间侧翼）", hr, (-21.0, 0.8, 4.6), (-2.0, 0.8, 3.0), clear=True)
    cam("Acc_05_House_Roof_Closeup", "屋顶近景（烟囱、天线、补丁、上翘屋檐）", hr, (-8.5, 9.0, 10.5), (-1.6, -0.6, 5.2), lens=32, clip=2.0)
    cam("Acc_06_House_Interior_Top", "木屋室内俯视（拆掉屋顶）", hr, (-1.2, 0.4, 13.0), None, hide=roof_h, res="1500x1000", ortho=13.6)
    cam("Acc_07_Kitchen_Dining", "客厅/厨房/餐厅", hr, (0.95, 2.45, B + 1.7), (-2.6, -2.3, B + 0.9), lens=14)
    cam("Acc_08_Bedroom", "卧室", hr, (1.75, -1.6, B + 1.7), (3.6, 1.5, B + 0.8), lens=14)
    cam("Acc_09_Bathroom", "卫生间（从洗手池一角看马桶、木柜、门）", hr, (-6.25, 1.35, B + 1.7), (-5.2, -2.4, B + 0.6), lens=13)
    cam("Acc_09b_Bathroom_Sink", "卫生间（看洗手池、镜子、毛巾）", hr, (-5.0, -2.1, B + 1.7), (-6.6, 1.2, B + 1.0), lens=14)
    cam("Acc_10_Warehouse_Front", "仓库正面（大门朝向木屋；渲染时隐藏木屋）", wr, (0.0, 17.0, 3.6), (0.0, 0.0, 2.6), hide=house, clear=True)
    cam("Acc_11_Warehouse_Back", "仓库背面", wr, (0.0, -17.0, 3.6), (0.0, 0.0, 2.6), clear=True)
    cam("Acc_12_Warehouse_East", "仓库局部 +X 侧", wr, (16.0, 0.0, 3.6), (0.0, 0.0, 2.4), clear=True)
    cam("Acc_13_Warehouse_West", "仓库局部 -X 侧", wr, (-16.0, 0.0, 3.6), (0.0, 0.0, 2.4), clear=True)
    cam("Acc_14_Warehouse_Interior", "仓库内部（从大门往里看）", wr, (0.5, 3.6, Bw + 1.7), (-0.5, -2.5, Bw + 0.9), lens=14)
    cam("Acc_15_Warehouse_Storage_Detail", "仓库储物细节（木料架）", wr, (0.2, 0.6, Bw + 1.6), (2.3, -1.6, Bw + 1.1), lens=20)
    cam("Acc_16_Warehouse_Interior_Top", "仓库室内俯视（拆掉屋顶）", wr, (0.0, 0.0, 12.0), None, hide=roof_w, res="1200x1400", ortho=9.6)
    build_lake_cameras()
    build_still_match_cameras()
    cam("Acc_17_Yard_Overview", "院子全景（木屋、仓库、小路、栅栏、院门）", hr, (18.0, 30.0, 20.0), (1.0, -7.0, 1.0), lens=26, clip=2.0)
    tr, mc, sq = (bpy.data.objects[n] for n in ("Bears_TreeHome_Root", "MonkeyCave_Root", "SquirrelNest_Tree_Root"))
    cam("Acc_18_TreeHome_Exterior", "熊洞外观（大树树干、前洞口、树根）", tr, (5.0, -15.0, 3.2), (0.0, 0.0, 3.4), lens=24, clear=True)
    cam("Acc_19_TreeHome_Interior", "熊洞室内（石板床、树叶铺、后壁圆洞）", tr, (-1.7, -1.5, 1.7), (0.9, 2.1, 1.0), lens=14)
    cam("Acc_20_MonkeyCave_Exterior", "猴洞外观（岩石山、洞口、石板平台、图腾）", mc, (-6.5, -19.0, 5.0), (0.0, -2.5, 3.0), lens=24, clear=True)
    cam("Acc_21_MonkeyCave_Interior", "猴洞内部（从隧道往里看：座位、睡窝）", mc, (0.0, -4.4, 1.6), (0.0, 0.8, 1.0), lens=16)
    cam("Acc_22_SquirrelNest_Tree", "松鼠窝大树（粗树枝和洞口 A）", sq, (6.5, -10.0, 3.6), (0.6, 0.0, 4.8), lens=28, clear=True)
    cam("Acc_23_SquirrelNest_Entrance", "松鼠窝洞口 A 近景（粗树枝根部正上方）", sq, (1.9, -2.6, 5.1), (0.6, -0.2, 4.85), lens=30)


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
    # 室内家具：落地物体的底面要贴地板；同一房间里的落地家具在平面上不能互相穿插；门洞里不能有家具
    bpy.context.view_layer.update()

    def wbox(ob):
        cs = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
        return (min(c.x for c in cs), max(c.x for c in cs), min(c.y for c in cs), max(c.y for c in cs), min(c.z for c in cs), max(c.z for c in cs))
    def lbox(ob):  # 在所属建筑（父物体）的局部坐标里算包围盒：建筑旋转后，世界轴向的包围盒会被放大
        M = (ob.parent.matrix_world.inverted() if ob.parent else Matrix.Identity(4)) @ ob.matrix_world
        cs = [M @ Vector(c) for c in ob.bound_box]
        return (min(c.x for c in cs), max(c.x for c in cs), min(c.y for c in cs), max(c.y for c in cs), min(c.z for c in cs), max(c.z for c in cs))
    items = [o for o in bpy.data.objects if o.get("floor_item")]
    boxes = {o.name: wbox(o) for o in items}
    lboxes = {o.name: lbox(o) for o in items}
    for o in items:
        dz = boxes[o.name][4] - o["floor_z_world"]
        if abs(dz) > 0.03:
            report.append(f"家具没贴地板: {o.name} dz={dz:.3f}")
    for i, a in enumerate(items):
        for b in items[i + 1:]:
            if a["room"] != b["room"] or not (a.get("overlap_check") and b.get("overlap_check")):
                continue
            A, Bx = lboxes[a.name], lboxes[b.name]
            ox = min(A[1], Bx[1]) - max(A[0], Bx[0])
            oy = min(A[3], Bx[3]) - max(A[2], Bx[2])
            if ox > 0.02 and oy > 0.02:
                report.append(f"家具互相穿插: {a.name} / {b.name} ({ox:.2f}×{oy:.2f} m)")
    for nm, root_name, (x0, x1, y0, y1, z0, z1) in DOOR_PASSAGES:
        M = bpy.data.objects[root_name].matrix_world
        cs = [M @ Vector((x, y, z)) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
        P = (min(c.x for c in cs), max(c.x for c in cs), min(c.y for c in cs), max(c.y for c in cs), min(c.z for c in cs), max(c.z for c in cs))
        for o in bpy.data.objects:
            if o.type != "MESH" or not (o.get("floor_item") or "Leaf" in o.name or "Barn_Door" in o.name):
                continue
            A = boxes.get(o.name) or wbox(o)
            if all(min(A[2 * k + 1], P[2 * k + 1]) - max(A[2 * k], P[2 * k]) > 0.0 for k in range(3)):
                report.append(f"门洞被挡住: {nm} ← {o.name}")
    # 缺失贴图（本脚本不用外部贴图，应为 0）
    for im in bpy.data.images:
        if im.source == "FILE" and not os.path.isfile(bpy.path.abspath(im.filepath)):
            report.append(f"缺失贴图: {im.name}")
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
    # Inferred_Models 只是“推测模型”的选择清单：从视图层排除，避免物体经由它被重复显示，
    # 这样在大纲里隐藏某个集合（例如可拆屋顶）时，它的物体会真正隐藏。
    def _layer(lc, name):
        if lc.collection.name == name:
            return lc
        for ch in lc.children:
            r = _layer(ch, name)
            if r:
                return r
    for n in ("Inferred_Models", "Prototypes_Hidden"):
        lc = _layer(bpy.context.view_layer.layer_collection, n)
        if lc:
            lc.exclude = True
    import json
    sc["door_passages_json"] = json.dumps(DOOR_PASSAGES, ensure_ascii=False)  # reopen_check.py 用
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
    step("warehouse", build_warehouse)
    step("bears home", build_bears_home)
    step("monkey cave", build_monkey_cave)
    step("squirrel tree", build_squirrel_tree)
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
