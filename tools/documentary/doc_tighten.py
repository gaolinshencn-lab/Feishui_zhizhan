"""Tightens the documentary narration gently: trims leading/trailing silence and compresses only the
longest pauses inside a line (cut in the middle of the silence, with short crossfades). voice_doc/ ->
voice_doc_t/, only for lines whose source changed."""
import os, sys, glob
import numpy as np
from scipy.io import wavfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC, DST = f'{HERE}/voice_doc', f'{HERE}/voice_doc_t'
KNEE, RATIO, EDGE, XF = 0.5, 0.55, 0.06, 0.012


def tighten(x, sr):
    hop = sr // 100
    n = len(x) // hop
    e = np.sqrt(np.convolve((x[: n * hop].reshape(n, hop) ** 2).mean(1), np.ones(3) / 3, 'same'))
    v = e > max(0.008, np.percentile(e, 95) * 0.05)
    idx = np.nonzero(v)[0]
    if len(idx) == 0:
        return x
    a, b = max(0, idx[0] * hop - int(EDGE * sr)), min(len(x), (idx[-1] + 1) * hop + int(EDGE * 1.5 * sr))
    x = x[a:b]
    v = v[idx[0]: idx[-1] + 1]
    # silent runs inside
    runs, start = [], None
    for i, s in enumerate(v):
        if not s and start is None:
            start = i
        elif s and start is not None:
            runs.append((start, i))
            start = None
    off = idx[0] * hop - a
    out, pos = [], 0
    xf = int(XF * sr)
    for s, e_ in runs:
        length = (e_ - s) / 100
        if length <= KNEE:
            continue
        keep = KNEE + RATIO * (length - KNEE)
        cut = int((length - keep) * sr)
        mid = off + int((s + e_) / 2 * hop)
        c0, c1 = mid - cut // 2, mid - cut // 2 + cut
        if c0 - xf <= pos:
            continue
        seg = x[pos:c0].copy()
        nxt = x[c1:c1 + xf]
        ramp = np.linspace(0, 1, len(nxt))
        seg[-len(nxt):] = seg[-len(nxt):] * (1 - ramp) + nxt * ramp
        out.append(seg)
        pos = c1 + xf
    out.append(x[pos:])
    y = np.concatenate(out)
    f = int(0.005 * sr)
    y[:f] *= np.linspace(0, 1, f)
    y[-f:] *= np.linspace(1, 0, f)
    return y


if __name__ == '__main__':
    os.makedirs(DST, exist_ok=True)
    before = after = 0
    for p in sorted(glob.glob(f'{SRC}/*.wav')):
        dst = f'{DST}/{os.path.basename(p)}'
        if os.path.exists(dst) and os.path.getmtime(dst) > os.path.getmtime(p):
            continue
        sr, x = wavfile.read(p)
        x = x.astype(np.float32) / 32768
        y = tighten(x, sr)
        before += len(x) / sr
        after += len(y) / sr
        wavfile.write(dst, sr, (np.clip(y, -1, 1) * 32767).astype(np.int16))
    if before:
        print(f'narration {before:.1f}s -> {after:.1f}s ({100 * (1 - after / before):.0f}% shorter)')
