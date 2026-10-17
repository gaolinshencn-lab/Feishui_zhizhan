# -*- coding: utf-8 -*-
"""采集脚本共用：索引读写、哈希、去重。"""
import csv
import hashlib
import os

HERE = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(HERE, "frames_index.csv")
SOURCES = os.path.join(HERE, "sources.csv")
STORE = os.path.expanduser(os.environ.get("BOONIE_FRAMES", "~/boonie_frames"))
FIELDS = ["frame_id", "series", "episode", "episode_title", "timestamp_s", "source_type", "source", "sha256", "dhash",
          "width", "height", "scene_tag", "visible_details", "evidence_level", "reviewed", "notes"]
MIN_SHORT_SIDE = 480  # 短边小于这个算缩略图，不收
DHASH_DUP = 6         # 汉明距离 ≤ 6 算近似重复


def read_index():
    if not os.path.exists(INDEX):
        return []
    with open(INDEX, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def append_index(rows):
    new = not os.path.exists(INDEX)
    with open(INDEX, "a", encoding="utf-8-sig" if new else "utf-8", newline="") as f:
        w = csv.DictWriter(f, FIELDS)
        if new:
            w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in FIELDS})


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def dhash(img):
    g = img.convert("L").resize((9, 8))
    px = list(g.getdata())
    bits = 0
    for y in range(8):
        for x in range(8):
            bits = (bits << 1) | (px[y * 9 + x] > px[y * 9 + x + 1])
    return f"{bits:016x}"


def hamming(a, b):
    return bin(int(a, 16) ^ int(b, 16)).count("1")


class Deduper:
    def __init__(self, rows):
        self.sha = {r["sha256"] for r in rows if r.get("sha256")}
        self.dh = [r["dhash"] for r in rows if r.get("dhash")]

    def check(self, sha, dh):
        """返回 None 表示可以收；否则返回拒收原因。"""
        if sha in self.sha:
            return "重复（sha256 相同）"
        for d in self.dh:
            if hamming(d, dh) <= DHASH_DUP:
                return "近似重复（dhash）"
        return None

    def add(self, sha, dh):
        self.sha.add(sha)
        self.dh.append(dh)


def series_code(series):
    table = {"夏日连连看": "XRLLK", "春日对对碰": "CRDDP", "秋日团团转": "QRTTZ", "冬日乐翻天": "DRLFT"}
    return table.get(series, "SER")
