# -*- coding: utf-8 -*-
"""P4 两张地图：
  - Evidence Map（证据关系图）：只画剧照能证明的关系。节点的摆放**不是**地理位置，图上没有距离和方向。
  - Playable Map（可漫游地图）：模型里的实际布局（俯视示意），每个地点、每条路都标明是证据还是推测。

两步（和 lake_layout_diagrams.py 一样）：
  1. blender -b --factory-startup -P map_diagrams.py -- sample <输出目录>   （读取建模脚本里的布局常量，写 map_samples.json）
  2. python3 map_diagrams.py draw <输出目录>                                （用 Pillow 画 EVIDENCE_MAP.png、PLAYABLE_MAP.png）
"""
import json
import math
import os
import sys

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
mode, out = argv[0], os.path.abspath(argv[1])
os.makedirs(out, exist_ok=True)
HERE = os.path.dirname(os.path.abspath(__file__))

# 证据关系：(节点 A, 节点 B, 关系, 参考编号, 等级)。只收剧照里同一画面能看到的关系；文字资料单独标“文字”。
NODES = {
    "house": "光头强木屋",
    "gate": "蓝顶院门",
    "fence": "院子栅栏",
    "deck": "前廊、楼梯",
    "tires": "轮胎堆",
    "warehouse": "仓库",
    "lake": "湖",
    "beach": "沙滩",
    "cliff": "石崖",
    "fall": "瀑布",
    "birch": "湖边黄叶白桦",
    "bearhome": "熊大熊二树洞",
    "bh_forest": "树洞后壁圆洞外的树林",
    "cave": "吉吉毛毛山洞",
    "platform": "石板平台、图腾",
    "squirrel": "蹦蹦的树（粗树枝）",
    "spruce": "云杉林",
}
EVIDENCE = [
    ("house", "gate", "从院子正对木屋时，院门在画面左侧", "R1、H2", "A/B"),
    ("house", "fence", "栅栏在木屋正面前方；H2 能看到绕到屋后", "R1、H2", "A/B"),
    ("house", "deck", "前廊在正面，楼梯在正中", "R1、R2", "A"),
    ("deck", "tires", "轮胎堆在楼梯右侧（画面方位）", "R1", "A"),
    ("lake", "beach", "同一画面：沙滩在湖边", "U1、U2", "A"),
    ("lake", "cliff", "同一画面：石崖在湖的另一岸", "U1、E41-072s", "A"),
    ("cliff", "fall", "瀑布从崖顶落进湖里", "U1", "A"),
    ("lake", "birch", "湖边有黄叶白桦", "U1", "A"),
    ("bearhome", "bh_forest", "后壁圆洞外能看到树林", "B1", "B"),
    ("cave", "platform", "洞口前是石板平台和两根图腾", "M1", "B"),
    ("squirrel", "spruce", "背景是云杉（冬季）", "S1", "B"),
    ("house", "lake", "从木屋窗口能看到瀑布和湖（夏日篇）", "第30集小帧1", "B"),
]
# 边标签的位置（像素），避免互相压住
LABEL_AT = {("house", "gate"): (330, 150), ("house", "deck"): (660, 290), ("deck", "tires"): (840, 178), ("house", "fence"): (330, 420),
            ("lake", "beach"): (1010, 110), ("lake", "cliff"): (1350, 255), ("cliff", "fall"): (1560, 400)}
UNKNOWN = ["warehouse"]  # 没有任何画面
# 用户提供、还没有画面验证的线索；以及只有文字的说法。都画成虚线，不算证据。
USER_CLAIMS = [("warehouse", "lake", "用户提供：仓库位于湖边（待画面验证）")]
TEXT_ONLY = [("cave", "bearhome", "熊大熊二把一个山洞分给吉吉毛毛住（萌娘百科文字，不是画面）"),
             ("warehouse", "house", "网易文章：变形记里仓库建在家门口（其他系列，文字）")]

if mode == "sample":
    import importlib.util
    spec = importlib.util.spec_from_file_location("bbm", os.path.join(HERE, "build_boonie_bears_map.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    H, W = m.HOUSE, m.WAREHOUSE
    c, s_ = math.cos(H["rot"]), math.sin(H["rot"])

    def hw(lx, ly):
        return (H["x"] + c * lx - s_ * ly, H["y"] + s_ * lx + c * ly)
    places = {
        "house": (H["x"], H["y"]), "gate": hw(6.6, 9.0), "warehouse": m.warehouse_site()[:2], "warehouse_alt": hw(2.0, -15.0),
        "pickup": (H["x"] + 22.0, H["y"] + 13.6), "meadow": m.MEADOW[:2],
        "bearhome": (m.BEARHOME["x"], m.BEARHOME["y"]), "honeytree": m.HONEYTREE,
        "cave": (m.MONKEYCAVE["x"], m.MONKEYCAVE["y"]), "squirrel": (m.SQUIRRELTREE["x"], m.SQUIRRELTREE["y"]),
        "fall": m.lake_point(m.CLIFF["fall"], 1.1), "beach": m.lake_point(math.radians(-62), 1.25),
        "logyard": m.LOGYARD[:2],
    }
    lake = [m.lake_point(2 * math.pi * k / 180, 1.0) for k in range(180)]
    cliff = [m.lake_point(m.CLIFF["a0"] + (m.CLIFF["a1"] - m.CLIFF["a0"]) * k / 30, 1.12) for k in range(31)]
    data = dict(places=places, lake=lake, cliff=cliff, creek=m.creek_pts(), paths=[dict(name=p["name"], w=p["w"], pts=p["pts"]) for p in m.PATHS],
                core=m.CORE)
    with open(os.path.join(out, "map_samples.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    print("SAMPLED")
    sys.exit(0)

from PIL import Image, ImageDraw, ImageFont  # noqa: E402


def font(size):
    for f in ("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
              "C:/Windows/Fonts/msyh.ttc", "/System/Library/Fonts/PingFang.ttc"):
        if os.path.exists(f):
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


F, FS, FB = font(22), font(17), font(32)
COL = {"user": (150, 60, 170), "A": (30, 120, 50), "A/B": (40, 110, 140), "B": (40, 90, 190), "text": (150, 150, 150), "inferred": (215, 110, 20)}


def evidence_map():
    """节点按主题分成几簇（簇之间的相对位置没有意义），边上写关系和参考编号。"""
    Wd, Hd = 1800, 1250
    im = Image.new("RGB", (Wd, Hd), "white")
    dr = ImageDraw.Draw(im)
    pos = {
        "house": (330, 330), "gate": (110, 200), "fence": (110, 470), "deck": (560, 220), "tires": (720, 120), "warehouse": (560, 520),
        "lake": (1240, 330), "beach": (1040, 170), "cliff": (1460, 180), "fall": (1660, 330), "birch": (1240, 560),
        "bearhome": (330, 860), "bh_forest": (330, 1080),
        "cave": (860, 900), "platform": (860, 1100),
        "squirrel": (1400, 900), "spruce": (1400, 1100),
    }
    dr.text((30, 20), "Evidence Map：只画剧照能证明的关系", fill=(0, 0, 0), font=FB)
    dr.text((30, 62), "节点位置不是地理位置；图上没有距离、没有东南西北。同一画面里的前景/背景不等于地图距离。", fill=(90, 90, 90), font=FS)
    for a, b, rel, ref, lv in EVIDENCE:
        (x1, y1), (x2, y2) = pos[a], pos[b]
        dr.line((x1, y1, x2, y2), fill=COL[lv], width=4)
        mx, my = LABEL_AT.get((a, b), ((x1 + x2) / 2, (y1 + y2) / 2))
        t = f"{ref}（{lv}）：{rel}"
        w = dr.textlength(t, font=FS)
        mx = min(max(mx, w / 2 + 10), Wd - w / 2 - 10)
        dr.rectangle((mx - w / 2 - 4, my - 12, mx + w / 2 + 4, my + 12), fill=(255, 255, 255))
        dr.text((mx - w / 2, my - 10), t, fill=COL[lv], font=FS)
    for a, b, rel in TEXT_ONLY:
        (x1, y1), (x2, y2) = pos[a], pos[b]
        n = 24
        for k in range(0, n, 2):
            dr.line((x1 + (x2 - x1) * k / n, y1 + (y2 - y1) * k / n, x1 + (x2 - x1) * (k + 1) / n, y1 + (y2 - y1) * (k + 1) / n), fill=COL["text"], width=3)
        dr.text({("cave", "bearhome"): (420, 790), ("warehouse", "house"): (180, 580)}[(a, b)], "文字：" + rel, fill=COL["text"], font=FS)
    for a, b, rel in USER_CLAIMS:
        (x1, y1), (x2, y2) = pos[a], pos[b]
        n = 30
        for k in range(0, n, 2):
            dr.line((x1 + (x2 - x1) * k / n, y1 + (y2 - y1) * k / n, x1 + (x2 - x1) * (k + 1) / n, y1 + (y2 - y1) * (k + 1) / n), fill=COL["user"], width=4)
        dr.text((760, 470), rel, fill=COL["user"], font=FS)
    for k, (x, y) in pos.items():
        t = NODES[k]
        w = dr.textlength(t, font=F)
        unk = k in UNKNOWN
        dr.rounded_rectangle((x - w / 2 - 12, y - 20, x + w / 2 + 12, y + 20), 10, fill=(255, 245, 230) if unk else (240, 246, 240),
                             outline=COL["inferred"] if unk else (60, 60, 60), width=3)
        dr.text((x - w / 2, y - 13), t, fill=(0, 0, 0), font=F)
    dr.text((pos["warehouse"][0] - 130, pos["warehouse"][1] + 26), "没有任何原作画面", fill=COL["inferred"], font=FS)
    y = Hd - 60
    for lv, t in (("A", "A：四季篇画面（R1–R4 季别待核验）"), ("A/B", "A/B：A 和其他版本都有"), ("B", "B：其他系列或季别未核验"),
                  ("text", "灰虚线：只有文字"), ("user", "紫虚线：用户提供，待画面验证")):
        x = 30 + ("A", "A/B", "B", "text", "user").index(lv) * 355
        dr.line((x, y + 10, x + 40, y + 10), fill=COL[lv], width=4)
        dr.text((x + 50, y), t, fill=COL[lv], font=FS)
    im.save(os.path.join(out, "EVIDENCE_MAP.png"))


def playable_map(d):
    Wd, Hd = 1800, 1400
    cx0, cy0, sc = 0.0, 4.0, 9.0  # 世界坐标 → 像素
    im = Image.new("RGB", (Wd, Hd), (236, 242, 228))
    dr = ImageDraw.Draw(im)

    def P(x, y):
        return (Wd / 2 + (x - cx0) * sc, Hd / 2 - (y - cy0) * sc)
    dr.polygon([P(*p) for p in d["lake"]], fill=(150, 205, 210), outline=(60, 120, 140))
    dr.line([P(*p) for p in d["cliff"]], fill=(70, 70, 75), width=10)
    dr.line([P(*p) for p in d["creek"]], fill=(70, 150, 190), width=4)
    for p in d["paths"]:
        dr.line([P(*q) for q in p["pts"]], fill=(170, 135, 90), width=max(3, int(p["w"] * sc * 0.6)))
    pl = d["places"]
    # (键, 标签, 地点本身的等级, 在地图上的位置是否有证据)
    items = [
        ("house", "光头强木屋", "A", "推测"), ("gate", "院门（画面左侧：R1）", "A", "相对木屋：R1；世界方位：约定"),
        ("warehouse", "仓库（湖边候选）", "D", "用户提供“在湖边”，待画面验证；离湖多远是推测"),
        ("warehouse_alt", "旧候选：屋后（已撤销）", "D", "R1 推断不成立，只作对照"), ("pickup", "皮卡", "B", "推测"), ("meadow", "空地", "D", "推测"),
        ("bearhome", "熊洞", "B", "推测"), ("honeytree", "蜂蜜树", "B", "推测"), ("cave", "猴洞", "B", "推测"),
        ("squirrel", "松鼠窝", "B", "推测"), ("fall", "瀑布", "A", "相对湖：U1"), ("beach", "沙滩", "A", "相对湖：U1"), ("logyard", "原木堆场", "D", "推测"),
    ]
    for k, label, lv, where in items:
        x, y = P(*pl[k])
        col = COL["inferred"] if lv == "D" else (COL["A"] if lv == "A" else COL["B"])
        dr.ellipse((x - 9, y - 9, x + 9, y + 9), fill=col, outline=(0, 0, 0))
        dr.text((x + 13, y - 22), label, fill=(0, 0, 0), font=F)
        dr.text((x + 13, y + 2), "位置：" + where, fill=COL["inferred"] if "推测" in where else (60, 60, 60), font=FS)
    # 比例尺和方位约定
    x, y = 60, Hd - 70
    dr.line((x, y, x + 20 * sc, y), fill=(0, 0, 0), width=4)
    dr.text((x, y + 8), "20 m（模型尺寸）", fill=(0, 0, 0), font=FS)
    dr.text((30, 20), "Playable Map：模型里的实际布局（可漫游）", fill=(0, 0, 0), font=FB)
    dr.text((30, 62), "地点之间的距离、方向、道路走向全是推测（橙色）。“上 = 北”只是模型约定，不是原作证据。", fill=COL["inferred"], font=FS)
    dr.text((30, 88), "点的颜色 = 地点本身的依据：绿 A、蓝 B、橙 推测。说明见 evidence/MAPS.md。", fill=(60, 60, 60), font=FS)
    ax, ay = Wd - 80, 140
    dr.line((ax, ay + 50, ax, ay), fill=(0, 0, 0), width=3)
    dr.polygon([(ax - 8, ay + 8), (ax + 8, ay + 8), (ax, ay - 8)], fill=(0, 0, 0))
    dr.text((ax - 40, ay + 56), "+Y（约定“北”）", fill=(0, 0, 0), font=FS)
    im.save(os.path.join(out, "PLAYABLE_MAP.png"))


with open(os.path.join(out, "map_samples.json"), encoding="utf-8") as f:
    data = json.load(f)
evidence_map()
playable_map(data)
print("DRAWN")
