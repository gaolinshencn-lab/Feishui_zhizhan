"""Renders the still sections (background, aftermath) as slow pans and push-ins across the 4K stills,
crossfading between shots, into 240-frame chunks like the live footage (chunks/<seg>_NNN.mp4).
    python kenburns.py [bg|end ...]"""
import json, math, os, subprocess, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
TL = json.load(open(f'{HERE}/doc_timeline.json'))
FPS, CH = TL['fps'], 240
STILLS = f'{HERE}/stills'
OUT = f'{HERE}/chunks'
W, H = 1920, 1080
ZOOM = 1.13
os.makedirs(OUT, exist_ok=True)


def ease(u):
    u = min(1.0, max(0.0, u))
    return 0.5 - 0.5 * math.cos(math.pi * u)


class Clip:
    def __init__(self, st, n, phase):
        self.st = st
        self.img = Image.open(f"{STILLS}/{st['shot']}@{phase}.png").convert('RGB')
        self.sw, self.sh = self.img.size
        # alternate the drift direction so consecutive shots do not all slide the same way
        sx = (-1, 1, 1, -1)[n % 4]
        sy = (1, -1, 1, -1)[n % 4]
        self.c0 = (0.5 - 0.018 * sx, 0.5 - 0.012 * sy)
        self.c1 = (0.5 + 0.018 * sx, 0.5 + 0.012 * sy)
        self.z0, self.z1 = (1.0, ZOOM) if st['zoom'] == 'in' else (ZOOM, 1.0)

    def frame(self, t):
        u = ease((t - self.st['start']) / max(1e-6, self.st['end'] - self.st['start']))
        z = self.z0 + (self.z1 - self.z0) * u
        cx = (self.c0[0] + (self.c1[0] - self.c0[0]) * u) * self.sw
        cy = (self.c0[1] + (self.c1[1] - self.c0[1]) * u) * self.sh
        w, h = self.sw / z, self.sh / z
        x0 = min(max(cx - w / 2, 0), self.sw - w)
        y0 = min(max(cy - h / 2, 0), self.sh - h)
        return np.asarray(self.img.resize((W, H), Image.LANCZOS, box=(x0, y0, x0 + w, y0 + h), reducing_gap=2.0), dtype=np.float32)


def render(seg_name):
    seg = next(s for s in TL['segments'] if s['name'] == seg_name)
    phase = 'start' if seg_name == 'bg' else 'end'
    s0, s1 = seg['start'], seg['end']
    sts = [st for st in TL['stills'] if st['end'] > s0 and st['start'] < s1]
    # the first and last shots cover the segment's crossfade margins too
    sts[0] = {**sts[0], 'start': min(sts[0]['start'], s0)}
    sts[-1] = {**sts[-1], 'end': max(sts[-1]['end'], s1)}
    clips = [Clip(st, n, phase) for n, st in enumerate(sts)]
    xf = TL['xfade_still']
    nchunks = -(-seg['frames'] // CH)
    for c in range(nchunks):
        path = f'{OUT}/{seg_name}_{c:03d}.mp4'
        if os.path.exists(path):
            continue
        tmp = f'{OUT}/.{seg_name}_{c:03d}.mp4'
        ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                               '-c:v', 'libx264', '-preset', 'medium', '-crf', '15', '-pix_fmt', 'yuv420p', tmp], stdin=subprocess.PIPE)
        for f in range(c * CH, min(seg['frames'], (c + 1) * CH)):
            t = (seg['frame0'] + f) / FPS
            act = [k for k in clips if k.st['start'] <= t < k.st['end']] or [min(clips, key=lambda k: abs(k.st['start'] - t))]
            if len(act) == 1:
                img = act[0].frame(t)
            else:
                a, b = act[0], act[-1]
                w = ease((t - b.st['start']) / xf)
                img = a.frame(t) * (1 - w) + b.frame(t) * w
            ff.stdin.write(np.clip(img + 0.5, 0, 255).astype(np.uint8).tobytes())
        ff.stdin.close()
        if ff.wait() != 0:
            raise SystemExit(f'ffmpeg failed on {path}')
        os.replace(tmp, path)
        print(path, flush=True)


if __name__ == '__main__':
    for name in sys.argv[1:] or ['bg', 'end']:
        render(name)
