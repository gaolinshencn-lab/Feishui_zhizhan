# -*- coding: utf-8 -*-
"""从模板建一集的目录：python3 tools/new_episode.py S1 2 [集名]"""
import csv
import os
import shutil
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODES = {"S1": ("CRDDP", "春日对对碰"), "S2": ("XRLLK", "夏日连连看"), "S3": ("QRTTZ", "秋日团团转"), "S4": ("DRLFT", "冬日乐翻天")}


def main():
    season, ep = sys.argv[1], int(sys.argv[2])
    title = sys.argv[3] if len(sys.argv) > 3 else "待核实"
    code, series = CODES[season]
    d = os.path.join(HERE, f"{season}_{code}", f"E{ep:02d}_{title}")
    if os.path.exists(d):
        raise SystemExit(f"已存在：{d}")
    os.makedirs(d)
    for fn in os.listdir(os.path.join(HERE, "templates")):
        src = os.path.join(HERE, "templates", fn)
        dst = os.path.join(d, fn)
        if fn.endswith(".md"):
            with open(src, encoding="utf-8") as f:
                txt = f.read().format(series=series, ep=ep, title=title)
            with open(dst, "w", encoding="utf-8") as f:
                f.write(txt)
        else:
            shutil.copy(src, dst)
    print("已建：", d)


if __name__ == "__main__":
    main()
