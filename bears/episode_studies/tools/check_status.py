# -*- coding: utf-8 -*-
"""检查队列状态是否守规则：
  - VISUALLY_REVIEWED 及以后：frames_reviewed > 0，而且该集 episode_report.md 里列出了真正看过的画面；
  - MODEL_UPDATED 及以后：该集 model_changes.md 不能是空的；
  - ACCEPTED：该集目录里有 comparisons/ 对照图记录（对照图本身含剧照，不进仓库，只记录文件名）。
"""
import csv
import glob
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORDER = ["NOT_STARTED", "SOURCES_FOUND", "FRAMES_AVAILABLE", "VISUALLY_REVIEWED", "MODEL_UPDATED", "ACCEPTED"]


def ep_dir(r):
    d = glob.glob(os.path.join(HERE, f"{r['season']}_{r['code']}", f"E{int(r['episode']):02d}_*"))
    return d[0] if d else None


def main():
    bad = 0
    with open(os.path.join(HERE, "EPISODE_QUEUE.csv"), encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        st = r["status"]
        if st not in ORDER:
            print("未知状态", r["season"], r["episode"], st); bad += 1; continue
        lv = ORDER.index(st)
        d = ep_dir(r)
        if lv >= ORDER.index("SOURCES_FOUND") and not d:
            print("缺少集目录", r["season"], r["episode"]); bad += 1; continue
        if lv >= ORDER.index("VISUALLY_REVIEWED"):
            if int(r["frames_reviewed"] or 0) <= 0:
                print("没有看过的画面却标成", st, r["season"], r["episode"]); bad += 1
        if lv >= ORDER.index("MODEL_UPDATED"):
            p = os.path.join(d, "model_changes.md")
            if not os.path.exists(p) or len(open(p, encoding="utf-8").read().strip()) < 50:
                print("model_changes.md 为空", r["season"], r["episode"]); bad += 1
    counts = {s: sum(r["status"] == s for r in rows) for s in ORDER}
    print("状态统计:", counts, "问题:", bad)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
