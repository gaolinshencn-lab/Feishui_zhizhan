"""The documentary's music stem (music.wav): a low drone bed (the same voicing as the sand table's own
drone, a seamless 50-second loop) under the whole film, and 《前秦风雨》 at the structural points: the
opening (its drums landing on the title), each part title, and the credits (ending with the film).
Built a minute at a time into a memory-mapped float WAV."""
import json, os, subprocess
import numpy as np
import wavmm

HERE = os.path.dirname(os.path.abspath(__file__))
TL = json.load(open(f'{HERE}/doc_timeline.json'))
SR = 48000
N = int((TL['duration'] + 1.0) * SR)
THEME = os.environ.get('THEME', f'{HERE}/qianqin-fengyu-theme.mp3')  # the app's theme, exported
DRUMS_IN = 24.5            # where the theme's drums enter (s)
CR = 100                   # control rate of the level envelope (Hz)
BLOCK = 60 * SR


def drone(period=50.0):
    """Detuned low sawtooth chord through a slowly breathing low-pass, as one seamless loop."""
    n = int(period * SR)
    t = np.arange(n) / SR
    fc = 340 * 2 ** (0.5 * np.sin(2 * np.pi * (3 / period) * t))
    out = np.zeros(n)
    for f0, amp in ((55.0, 1.0), (55.12, 0.8), (82.42, 0.55), (110.1, 0.35)):
        k = 1
        while k * f0 < 1600:
            f = k * f0
            out += amp / k / np.sqrt(1 + (f / fc) ** 4) * np.sin(2 * np.pi * f * t + 0.7 * k)
            k += 1
    out /= np.abs(out).max()
    d = int(0.011 * SR)  # a little width: the right channel a few ms behind
    return np.stack([out, np.roll(out, d)], axis=1).astype(np.float32)


def theme():
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', THEME, '-ac', '2', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).reshape(-1, 2)


def level_envelope():
    """Bed level at CR Hz: a touch louder where stills are shown (no battle sound there), faded at the ends."""
    n = int(N / SR * CR) + 2
    lv = np.full(n, 0.10)
    for seg in TL['segments']:
        if seg['camera'] == 'still':
            lv[int(seg['start'] * CR):int(seg['end'] * CR)] = 0.16
    k = 2 * CR
    c = np.concatenate([[0.0], np.cumsum(lv)])
    i = np.arange(n)
    lo, hi = np.clip(i - k // 2, 0, n), np.clip(i + k // 2, 0, n)
    lv = (c[hi] - c[lo]) / np.maximum(1, hi - lo)
    t = i / CR
    return lv * np.clip(t / 4.0, 0, 1) * np.clip((TL['duration'] - t) / 6.0, 0, 1)


def place(dst, src, at, src_from=0.0, src_to=None, fade_in=1.0, fade_out=3.0, gain=1.0):
    """Mix src[src_from:src_to] into dst starting at time `at`, with fades."""
    a = int(src_from * SR)
    b = len(src) if src_to is None else min(len(src), int(src_to * SR))
    seg = src[a:b].copy()
    if at < 0:
        seg = seg[int(-at * SR):]
        at = 0
    n = len(seg)
    env = np.ones(n, np.float32)
    fi, fo = min(int(fade_in * SR), n), min(int(fade_out * SR), n)
    if fi:
        env[:fi] = np.linspace(0, 1, fi)
    if fo:
        env[-fo:] = np.minimum(env[-fo:], np.linspace(1, 0, fo))
    s = int(at * SR)
    e = min(len(dst), s + n)
    dst[s:e] += seg[: e - s] * (env[: e - s, None] * gain)


def build():
    out = wavmm.create(f'{HERE}/music.wav', N, 2, SR)
    d = drone()
    lv = level_envelope()
    for a in range(0, N, BLOCK):
        b = min(N, a + BLOCK)
        idx = np.arange(a, b)
        bed = d[idx % len(d)]
        g = np.interp(idx / SR * CR, np.arange(len(lv)), lv).astype(np.float32)
        out[a:b] = bed * g[:, None]
    th = theme()
    title = TL['title']['start']
    start = title - DRUMS_IN
    place(out, th, start, 0.0, TL['intro_end'] - start + 2.0, fade_in=3.0, fade_out=6.0, gain=0.9)
    for p in TL['parts']:
        place(out, th, p['start'] - 2.0, DRUMS_IN - 2.0, DRUMS_IN + 14.0, fade_in=1.5, fade_out=8.0, gain=0.8)
    end = TL['duration']
    tail = len(th) / SR
    place(out, th, end - 40.0, tail - 40.0, None, fade_in=4.0, fade_out=2.0, gain=0.95)
    out.flush()
    peak = max(float(np.abs(out[a:a + BLOCK]).max()) for a in range(0, N, BLOCK))
    print(f'music {N / SR:.1f}s, peak {20 * np.log10(peak + 1e-9):.1f} dBFS')


if __name__ == '__main__':
    build()
