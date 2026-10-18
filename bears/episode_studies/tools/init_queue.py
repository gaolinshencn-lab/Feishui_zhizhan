# -*- coding: utf-8 -*-
"""生成或补齐 EPISODE_QUEUE.csv（四季篇 4 部 × 52 集）。已有的行保持不变，只补缺的行。
集名只填核实过的（KNOWN），其余写“待核实”，不要猜。"""
import csv
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE = os.path.join(HERE, "EPISODE_QUEUE.csv")
SEASONS = [("S1", "CRDDP", "春日对对碰"), ("S2", "XRLLK", "夏日连连看"), ("S3", "QRTTZ", "秋日团团转"), ("S4", "DRLFT", "冬日乐翻天")]
KNOWN = {  # (季, 集): (集名, 依据)
    ("S1", 1): ("赏花大会", "YouTube 熊出没官方频道标题；央视网、百度百科分集"),
    ("S1", 4): ("注意！禽流感", "萌娘百科人物条目（文字）"),
    ("S1", 33): ("同桌的你", "萌娘百科人物条目（文字）"),
    ("S2", 30): ("湖底历险记", "用户提供"),
    ("S2", 41): ("生存技能", "用户提供"),
}
FIELDS = ["season", "code", "series", "episode", "title", "title_source", "status", "frames_reviewed", "video_sources", "notes"]


def main():
    rows = {}
    if os.path.exists(QUEUE):
        with open(QUEUE, encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                rows[(r["season"], int(r["episode"]))] = r
    for s, code, name in SEASONS:
        for e in range(1, 53):
            if (s, e) in rows:
                continue
            t, src = KNOWN.get((s, e), ("待核实", ""))
            rows[(s, e)] = dict(season=s, code=code, series=name, episode=e, title=t, title_source=src, status="NOT_STARTED", frames_reviewed=0)
    with open(QUEUE, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, FIELDS)
        w.writeheader()
        for k in sorted(rows, key=lambda k: (k[0], k[1])):
            w.writerow({x: rows[k].get(x, "") for x in FIELDS})
    print("队列行数:", len(rows))


if __name__ == "__main__":
    main()
