# -*- coding: utf-8 -*-
"""从用户提供的本地视频抽帧（不下载任何东西）：固定间隔 + 场景切换，去重后写进存储目录和索引。
中断后重跑会从 sources.csv 里记录的最后时间码继续。

python3 extract_frames.py --video <本地视频> --series 夏日连连看 --episode 30 --title 湖底历险记 [--every 2.0] [--scene 0.3]
"""
import argparse
import csv
import json
import os
import subprocess
import tempfile

from PIL import Image

import common as C


def probe_duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", path], capture_output=True, text=True, check=True)
    return float(json.loads(r.stdout)["format"]["duration"])


def load_sources():
    if not os.path.exists(C.SOURCES):
        return []
    with open(C.SOURCES, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def save_sources(rows):
    keys = ["source_id", "source_type", "location", "series", "episode", "episode_title", "status", "frames_done", "last_timestamp_s", "notes"]
    with open(C.SOURCES, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in keys})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--series", default="待核验")
    ap.add_argument("--episode", default="")
    ap.add_argument("--title", default="")
    ap.add_argument("--every", type=float, default=2.0, help="固定间隔（秒）")
    ap.add_argument("--scene", type=float, default=0.3, help="场景切换阈值（ffmpeg select scene）")
    ap.add_argument("--chunk", type=float, default=120.0, help="每次处理多少秒（便于中断续跑）")
    a = ap.parse_args()
    if not os.path.isfile(a.video):
        raise SystemExit("只处理本地视频文件；不下载网络视频")
    srcs = load_sources()
    loc = os.path.abspath(a.video)
    src = next((s for s in srcs if s["location"] == loc), None)
    if src is None:
        src = dict(source_id=f"SRC-{len(srcs) + 1:03d}", source_type="user_video", location=loc, series=a.series, episode=a.episode,
                   episode_title=a.title, status="in_progress", frames_done="0", last_timestamp_s="0")
        srcs.append(src)
    dur = probe_duration(a.video)
    t0 = float(src.get("last_timestamp_s") or 0)
    rows = C.read_index()
    dd = C.Deduper(rows)
    dst = os.path.join(C.STORE, C.series_code(a.series), f"E{a.episode or 'NA'}")
    os.makedirs(dst, exist_ok=True)
    while t0 < dur:
        t1 = min(dur, t0 + a.chunk)
        with tempfile.TemporaryDirectory() as tmp:
            vf = f"select='isnan(prev_selected_t)+gte(t-prev_selected_t\\,{a.every})+gt(scene\\,{a.scene})',showinfo"
            cmd = ["ffmpeg", "-v", "info", "-ss", str(t0), "-to", str(t1), "-i", a.video, "-vf", vf, "-vsync", "vfr", os.path.join(tmp, "f_%05d.png")]
            r = subprocess.run(cmd, capture_output=True, text=True)
            pts = [float(l.split("pts_time:")[1].split()[0]) for l in r.stderr.splitlines() if "pts_time:" in l]
            new = []
            for k, fn in enumerate(sorted(os.listdir(tmp))):
                p = os.path.join(tmp, fn)
                ts = round(t0 + (pts[k] if k < len(pts) else 0.0), 2)
                im = Image.open(p)
                if min(im.size) < C.MIN_SHORT_SIDE:
                    continue
                sha, dh = C.sha256(p), C.dhash(im)
                if dd.check(sha, dh):
                    continue
                fid = f"{C.series_code(a.series)}-E{a.episode or 'NA'}-{ts:08.2f}"
                im.convert("RGB").save(os.path.join(dst, fid + ".jpg"), quality=92)
                dd.add(sha, dh)
                new.append(dict(frame_id=fid, series=a.series, episode=a.episode, episode_title=a.title, timestamp_s=ts,
                                source_type="user_video", source=os.path.basename(a.video), sha256=sha, dhash=dh,
                                width=im.size[0], height=im.size[1], reviewed="no"))
            C.append_index(new)
        src["frames_done"] = str(int(src.get("frames_done") or 0) + len(new))
        src["last_timestamp_s"] = f"{t1:.2f}"
        src["status"] = "done" if t1 >= dur else "in_progress"
        save_sources(srcs)
        print(f"{t0:.0f}–{t1:.0f} s：新收 {len(new)} 张，本视频累计 {src['frames_done']}", flush=True)
        t0 = t1


if __name__ == "__main__":
    main()
