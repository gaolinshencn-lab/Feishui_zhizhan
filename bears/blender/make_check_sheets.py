# -*- coding: utf-8 -*-
"""把 render_checks.py 渲染的检查视图拼成几张检查图（需要 Pillow）。
用法：python3 make_check_sheets.py <检查视图目录> [输出目录]"""
import json
import os
import sys
from PIL import Image, ImageDraw, ImageFont

src = sys.argv[1]
dst = sys.argv[2] if len(sys.argv) > 2 else src
NAMES = {"Front": "正面", "Side": "侧面", "Back": "背面", "Top": "俯视"}


def sheet(out, rows, cell_w):
    ims = [[(Image.open(os.path.join(src, f + ".png")).convert("RGB"), lab) for f, lab in row] for row in rows]
    cells = []
    for row in ims:
        r = []
        for im, lab in row:
            im = im.copy()
            im.thumbnail((cell_w, cell_w * 2))
            r.append((im, lab))
        cells.append(r)
    W = max(sum(im.width for im, _ in r) for r in cells)
    H = sum(max(im.height for im, _ in r) + 26 for r in cells)
    c = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(c)
    y = 0
    for r in cells:
        x = 0
        for im, lab in r:
            c.paste(im, (x, y + 26))
            d.text((x + 6, y + 6), lab, fill=(30, 30, 30))
            x += im.width
        y += max(im.height for im, _ in r) + 26
    c.save(os.path.join(dst, out), quality=88)
    print("wrote", out)


chars = ["XiongDa", "XiongEr", "GuangtouQiang", "TuTu", "LuoBoTou", "BengBeng"]
sheet("check_characters.jpg", [[(f"Check_{c}_{k}", f"{c} {k}") for k in ("Front", "Side", "Back")] for c in chars], 300)
sheet("check_pickup_4views.jpg", [[("Check_Pickup_Front", "Pickup Front"), ("Check_Pickup_Side", "Pickup Side")],
                                  [("Check_Pickup_Back", "Pickup Back"), ("Check_Pickup_Top", "Pickup Top")]], 640)
sheet("check_house_exterior.jpg", [[("Check_House_Front", "House Front"), ("Check_House_Side", "House Side (east)")],
                                   [("Check_House_Back", "House Back"), ("Check_House_Top", "House Top")]], 640)
sheet("check_house_interior_plan.jpg", [[("Check_House_Interior_Plan", "Interior plan (roof hidden)")]], 1100)


def font(size):
    for f in ("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", "/usr/share/fonts/wqy-zenhei/wqy-zenhei.ttc",
              "C:/Windows/Fonts/msyh.ttc", "/System/Library/Fonts/PingFang.ttc", "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"):
        if os.path.exists(f):
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


# 带标注的室内平面图：observed（剧照可见）用绿色，inferred（推测位置）用橙色
lj = os.path.join(src, "Check_House_Interior_Plan.labels.json")
if os.path.exists(lj):
    im = Image.open(os.path.join(src, "Check_House_Interior_Plan.png")).convert("RGB")
    d = ImageDraw.Draw(im)
    f = font(18)
    seen = set()
    for lab in json.load(open(lj, encoding="utf-8")):
        if lab["cn"] in seen:
            continue
        seen.add(lab["cn"])
        x, y = lab["x"] * im.width, (1 - lab["y"]) * im.height
        col = (20, 120, 40) if lab["status"] == "observed" else (200, 110, 0)
        d.ellipse((x - 5, y - 5, x + 5, y + 5), fill=col)
        t = lab["cn"].split("（")[0]
        d.rectangle(d.textbbox((x + 8, y - 10), t, font=f), fill=(255, 255, 255))
        d.text((x + 8, y - 10), t, fill=col, font=f)
    d.text((10, im.height - 30), "绿色：剧照可见   橙色：位置为推测   上方为门（北）", fill=(0, 0, 0), font=f)
    im.save(os.path.join(dst, "check_house_interior_plan_labeled.jpg"), quality=90)
    print("wrote check_house_interior_plan_labeled.jpg")
sheet("check_map_top.jpg", [[("Check_Map_Top", "Map top view (orthographic)")]], 1400)
