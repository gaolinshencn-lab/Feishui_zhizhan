# -*- coding: utf-8 -*-
"""导入用户提供的截图目录：过滤缩略图、按 sha256 和 dhash 去重，复制到仓库外的存储目录并写索引。可重复运行（已收的会跳过）。

python3 ingest_frames.py --dir <截图目录> --series 夏日连连看 --episode 41 --title 生存技能 [--source-note 说明]
python3 ingest_frames.py --stats
"""
import argparse
import collections
import os
import shutil

from PIL import Image

import common as C


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir")
    ap.add_argument("--series", default="待核验")
    ap.add_argument("--episode", default="")
    ap.add_argument("--title", default="")
    ap.add_argument("--source-note", default="")
    ap.add_argument("--stats", action="store_true")
    a = ap.parse_args()
    rows = C.read_index()
    if a.stats or not a.dir:
        print("已收:", len(rows), "（人工看过:", sum(r.get("reviewed") == "yes" for r in rows), "）")
        for k, v in collections.Counter((r["series"], r["episode"]) for r in rows).most_common():
            print(" ", k, v)
        return
    dd = C.Deduper(rows)
    dst = os.path.join(C.STORE, C.series_code(a.series), f"E{a.episode or 'NA'}")
    os.makedirs(dst, exist_ok=True)
    n_img = sum(1 for r in rows if r["source_type"] == "user_screenshot" and r["series"] == a.series and r["episode"] == a.episode)
    new, rej = [], collections.Counter()
    for fn in sorted(os.listdir(a.dir)):
        p = os.path.join(a.dir, fn)
        if not fn.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".bmp")):
            continue
        try:
            im = Image.open(p)
            im.load()
        except Exception:
            rej["打不开"] += 1
            continue
        if min(im.size) < C.MIN_SHORT_SIDE:
            rej["缩略图（短边太小）"] += 1
            continue
        sha, dh = C.sha256(p), C.dhash(im)
        why = dd.check(sha, dh)
        if why:
            rej[why] += 1
            continue
        n_img += 1
        fid = f"{C.series_code(a.series)}-E{a.episode or 'NA'}-IMG{n_img:04d}"
        ext = os.path.splitext(fn)[1].lower()
        shutil.copy2(p, os.path.join(dst, fid + ext))
        dd.add(sha, dh)
        new.append(dict(frame_id=fid, series=a.series, episode=a.episode, episode_title=a.title, timestamp_s="",
                        source_type="user_screenshot", source=fn + (f"（{a.source_note}）" if a.source_note else ""),
                        sha256=sha, dhash=dh, width=im.size[0], height=im.size[1], reviewed="no"))
    C.append_index(new)
    print("新收:", len(new), "拒收:", dict(rej), "索引总数:", len(rows) + len(new))


if __name__ == "__main__":
    main()
