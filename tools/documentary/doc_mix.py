"""Mixes the documentary's soundtrack a minute at a time (memory-mapped stems): the narration placed on
the timeline, the battlefield sound of each live segment (rendered by the app's own engine, crossfaded at
the segment joins) and the music stem, both ducked under the voice with look-ahead; fades and a soft peak
limit. Writes doc_mix.wav (float32, 48 kHz stereo)."""
import json, os
import numpy as np
from scipy.signal import resample_poly
import wavmm

HERE = os.path.dirname(os.path.abspath(__file__))
TL = json.load(open(f'{HERE}/doc_timeline.json'))
VOICE = os.environ.get('VOICE_DIR', f'{HERE}/voice_doc_t')
SR = 48000
N = int(TL['duration'] * SR)
CR = 100            # control rate (Hz) of the ducking envelope
BLOCK = 60 * SR


def voice_track():
    """The narration as a memory-mapped mono track, levelled to about -18.5 dBFS speech RMS."""
    v = wavmm.create(f'{HERE}/.voice_track.wav', N, 1, SR)
    for l in TL['lines']:
        sr, x, k = wavmm.read(f"{VOICE}/{l['vid']}.wav")
        x = np.asarray(x, dtype=np.float32) * k
        if x.ndim > 1:
            x = x.mean(axis=1)
        x = resample_poly(x, SR, sr).astype(np.float32)
        a = int(l['start'] * SR)
        n = min(len(x), N - a)
        v[a:a + n, 0] += x[:n]
    ss = cnt = 0.0
    for a in range(0, N, BLOCK):
        b = v[a:a + BLOCK, 0]
        m = np.abs(b) > 1e-3
        ss += float(np.sum(b[m].astype(np.float64) ** 2))
        cnt += int(m.sum())
    g = 10 ** (-18.5 / 20) / (np.sqrt(ss / max(1, cnt)) + 1e-9)
    for a in range(0, N, BLOCK):
        v[a:a + BLOCK] *= g
    return v


def duck_envelope(v):
    """0 where the voice is silent, 1 where it speaks (CR Hz), with attack/release and look-ahead."""
    hop = SR // CR
    n = N // hop
    e = np.zeros(n)
    for k0 in range(0, n, BLOCK // hop):
        k1 = min(n, k0 + BLOCK // hop)
        blk = np.asarray(v[k0 * hop:k1 * hop, 0], dtype=np.float64).reshape(-1, hop)
        e[k0:k1] = np.sqrt((blk ** 2).mean(axis=1))
    e = np.sqrt(np.convolve(e ** 2, np.ones(8) / 8, mode='same'))
    act = (e > 10 ** (-42 / 20)).astype(np.float64)
    shift = int(0.2 * CR)
    act = np.maximum(act, np.concatenate([act[shift:], np.zeros(shift)]))
    up, down = 1 - np.exp(-1 / (0.12 * CR)), 1 - np.exp(-1 / (0.6 * CR))
    g = np.zeros(n)
    x = 0.0
    for i, a in enumerate(act):
        x += (a - x) * (up if a > x else down)
        g[i] = x
    return g, act.mean()


def build():
    v = voice_track()
    duck, active = duck_envelope(v)
    mu_sr, mu, mu_k = wavmm.read(f'{HERE}/music.wav')
    fx = []
    for seg in TL['segments']:
        path = f"{HERE}/fx_{seg['name']}.wav"
        if seg['camera'] != 'still' and os.path.exists(path):
            sr, x, k = wavmm.read(path)
            assert sr == SR, path
            fx.append((seg, x, k))
    out = wavmm.create(f'{HERE}/doc_mix.wav', N, 2, SR)
    xf = TL['xfade']
    peak_db = -99.0
    for a in range(0, N, BLOCK):
        b = min(N, a + BLOCK)
        t = np.arange(a, b) / SR
        d = np.interp(t * CR, np.arange(len(duck)), duck)
        f = np.zeros((b - a, 2), np.float32)
        for seg, x, k in fx:
            s0 = int(seg['start'] * SR)
            lo, hi = max(a, s0), min(b, s0 + len(x), int(seg['end'] * SR))
            if lo >= hi:
                continue
            chunk = np.asarray(x[lo - s0:hi - s0], dtype=np.float32) * k
            tt = np.arange(lo, hi) / SR
            ramp = np.clip((tt - seg['start']) / xf, 0, 1) if seg['start'] > 0 else np.ones(len(tt))
            ramp = np.minimum(ramp, np.clip((seg['end'] - tt) / xf, 0, 1))
            f[lo - a:hi - a] += chunk * ramp[:, None].astype(np.float32)
        m = np.asarray(mu[a:b], dtype=np.float32) * mu_k
        if len(m) < b - a:
            m = np.pad(m, ((0, b - a - len(m)), (0, 0)))
        fade = np.clip(t / 2.0, 0, 1) * np.clip((TL['duration'] - t) / 4.0, 0, 1)
        credits = np.clip((t - TL['credits_start']) / 1.5, 0, 1)
        fx_gain = 10 ** ((-1.0 - 7.5 * d) / 20) * fade * (1 - 0.8 * credits)
        mu_gain = 10 ** ((-1.0 - 8.0 * d) / 20) * fade
        mix = f * fx_gain[:, None].astype(np.float32) + m * mu_gain[:, None].astype(np.float32) + np.asarray(v[a:b], dtype=np.float32)
        pk = 10 ** (-2 / 20)
        aa = np.abs(mix)
        over = aa > pk
        mix[over] = np.sign(mix[over]) * (pk + (1 - pk) * np.tanh((aa[over] - pk) / (1 - pk)))
        out[a:b] = mix
        peak_db = max(peak_db, 20 * np.log10(float(np.abs(mix).max()) + 1e-9))
    out.flush()
    os.remove(f'{HERE}/.voice_track.wav')
    print(f'mix {N / SR:.1f}s; voice active {active * 100:.0f}% of the time; peak {peak_db:.1f} dBFS')


if __name__ == '__main__':
    build()
