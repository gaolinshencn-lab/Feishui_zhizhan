#!/usr/bin/env python3
"""
Subset the calligraphic display face (Ma Shan Zheng 马善政楷书, SIL OFL 1.1) to the glyphs the
model actually shows, and write it as WOFF2 for inlining into the single-file build.

  node tools/display-glyphs.mjs > /tmp/glyphs.txt   (done automatically below)
  python3 tools/subset_fonts.py
"""
import subprocess
import sys
import urllib.request
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "tools" / ".cache" / "fonts"
OUT = ROOT / "src" / "assets" / "fonts"
SRC_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/mashanzheng/MaShanZheng-Regular.ttf"


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    ttf = CACHE / "MaShanZheng-Regular.ttf"
    if not ttf.exists():
        with urllib.request.urlopen(SRC_URL, timeout=120) as r:
            ttf.write_bytes(r.read())
    glyphs = subprocess.run(["node", str(ROOT / "tools" / "display-glyphs.mjs")], capture_output=True, text=True, check=True).stdout
    font = TTFont(str(ttf))
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = ["*"]
    opts.name_IDs = ["*"]
    opts.notdef_outline = True
    sub = subset.Subsetter(options=opts)
    sub.populate(text=glyphs)
    sub.subset(font)
    out = OUT / "MaShanZheng-subset.woff2"
    font.flavor = "woff2"
    font.save(str(out))
    missing = [c for c in glyphs if ord(c) not in TTFont(str(ttf)).getBestCmap()]
    print(f"{len(glyphs)} glyphs -> {out.relative_to(ROOT)} ({out.stat().st_size // 1024} KB)")
    if missing:
        print("not in font (fallback face will be used):", "".join(missing), file=sys.stderr)


if __name__ == "__main__":
    main()
