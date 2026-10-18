"""Builds the documentary's timeline from the script and the synthesised voice: when each line is spoken,
the part, node and quote cards, the still shots with their pans, and the rendered live segments (with
the sand table's timeline T and, where the camera is keyed, its pose for every frame). Writes
doc_timeline.json.

Live segments are rendered on their own time base (frame 0 = the segment's first frame) so each can be
rendered as soon as its lines are synthesised."""
import json, os, sys, wave
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from doc_script import lines, SECTIONS, PARTS, SHOTS

HERE = os.path.dirname(os.path.abspath(__file__))
VOICE = os.environ.get('VOICE_DIR', f'{HERE}/voice_doc_t')
FPS = 24
GAP, LONG = 0.5, 1.15            # pause after a line, after a '|' line
GAP_I, LONG_I = 0.55, 1.3        # the intro is paced more slowly
LEAD = 1.2                       # node card to the first line
PART_HOLD = 5.0                  # full-screen part title before the part's narration
TITLE_HOLD = 5.5                 # the film's title after "这条河，叫淝水。"
TAIL = {'raid': 2.0, 'battle': 3.0, 'rout': 1.5, 'epilogue': 1.0}  # let a node's sounds play out
VMAX = 3.0                       # never run the sand table faster than 3x its own pace
XF = 1.0                         # crossfade between segments
XF_STILL = 0.9                   # crossfade between two still shots
INTRO_T, GEO_T, END_T = 8.15, 3.0, 13 - 1e-4
CREDITS = 9.0
EPS = json.load(open(f'{HERE}/episodes.json'))
NODES = [e['id'] for e in EPS]

PART_SUB = {
    'background': '公元四世纪 · 北方与江南',
    'prologue': '太元七年冬 — 八年九月 · 公元382 — 383年',
    'geo': '寿阳 · 淝水 · 八公山 · 硖石 · 洛涧',
    'advance': '太元八年十一月 · 公元383年12月',
    'news': '公元383 — 385年',
    'aftermath2': '',
}

# The intro's keyed camera (tactical table, down onto the Fei), relative to the line "这条河，叫淝水。".
INTRO_KEYS = lambda river, end: [
    (0.0, ([116.81, 32.625], 72, -12, 60)),
    (river - 6, ([116.792, 32.602], 30, 6, 46)),
    (river + 0.5, ([116.785, 32.594], 15.5, 20, 36)),
    (end, ([116.781, 32.592], 12.5, 32, 31)),
]


def drift(pose):
    """A slow push-in and turn while a shot is held."""
    target, dist, yaw, pitch = pose
    return (target, dist * 0.94, yaw + 5, pitch - 1.5)


def voice_duration(vid, text):
    path = f'{VOICE}/{vid}.wav'
    if os.path.exists(path):
        with wave.open(path) as w:
            return w.getnframes() / w.getframerate()
    return len(text) / 4.0  # estimate until the line is synthesised


def build():
    L = list(lines())
    for i, l in enumerate(L):
        l['i'] = i
        l['dur'] = voice_duration(l['vid'], l['text'])
    by = {}
    for l in L:
        by.setdefault(l['node'], []).append(l)
    parts, node_cards, stills, segments = [], [], [], []
    title = {}

    def part_card(sec, at):
        no, name = PARTS[sec]
        parts.append({'sec': sec, 'no': no, 'title': name, 'sub': PART_SUB.get(sec, ''), 'start': round(at, 3), 'end': round(at + PART_HOLD, 3)})

    # ── intro: lines one after another, the title after the river line
    t = 2.5
    for l in by['intro']:
        l['start'] = t
        t += l['dur'] + (LONG_I if l['long_pause'] else GAP_I)
        if l['text'].startswith('这条河'):
            river = l['start']
            title = {'start': round(l['start'] + l['dur'] + 0.4, 3)}
            t = title['start'] + TITLE_HOLD
            title['end'] = round(t - 0.3, 3)
    intro_end = t + 0.2
    seg_bounds = [('intro', 0.0)]

    # ── still sections: one shot per run of consecutive lines with the same shot
    def still_section(secs, t, part_first=True):
        runs = []
        for sec in secs:
            for k, l in enumerate(by[sec]):
                if sec in PARTS and k == 0:
                    part_card(sec, t)
                    t += PART_HOLD
                    runs.append({'shot': l['shot'], 'start': t - PART_HOLD, 'lines': []})
                elif not runs or runs[-1]['shot'] != l['shot']:
                    runs.append({'shot': l['shot'], 'start': t - 0.35, 'lines': []})
                l['start'] = t
                runs[-1]['lines'].append(l['i'])
                t += l['dur'] + (LONG if l['long_pause'] else GAP)
        for a, b in zip(runs, runs[1:]):
            a['end'] = b['start'] + XF_STILL
        runs[-1]['end'] = t + 0.3
        for n, r in enumerate(runs):
            r['zoom'] = 'in' if n % 2 == 0 else 'out'
            stills.append({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()})
        return t

    seg_bounds.append(('bg', intro_end))
    t = still_section(['background'], intro_end) + 0.6

    # ── node sections (live, the app's own camera), with part titles where a part begins
    points = []      # (time, T) for the whole film where the sand table runs

    def node_section(ks, t):
        for k in ks:
            nid = NODES[k]
            start = t
            vmax = VMAX / EPS[k]['duration']
            points.append((start, float(k)))
            if nid in PARTS:
                part_card(nid, start)
                t = start + PART_HOLD
                points.append((t, float(k)))
            if not (nid in PARTS and PARTS[nid][1] == EPS[k]['title']):
                node_cards.append({'k': k, 'start': round(t + 0.2, 3), **{x: EPS[k][x] for x in ('no', 'title', 'subtitle', 'date', 'western')}})
            prev_t, prev_p = t, 0.0
            t = t + LEAD
            for l in by[nid]:
                ts = max(t, prev_t + (l['p'] - prev_p) / vmax)
                l['start'] = ts
                points.append((ts, k + l['p']))
                t = ts + l['dur'] + (LONG if l['long_pause'] else GAP)
                prev_t, prev_p = ts, l['p']
            end = max(t - GAP + 0.6 + TAIL.get(nid, 0.0), prev_t + (1 - prev_p) / vmax)
            points.append((end, k + 1.0 - 1e-4))
            t = end
        return t

    seg_bounds.append(('A', t))
    t = node_section([0, 1, 2], t)

    # ── geography tour (live, keyed camera on the tactical table)
    seg_bounds.append(('geo', t))
    geo_start = t
    part_card('geo', t)
    t += PART_HOLD
    pose = SHOTS['t_overview'][1:]
    geo_keys = [(geo_start, pose)]
    for l in by['geo']:
        l['start'] = t
        if l['shot'] != 't_overview':
            # hold (drifting slightly) until just before the line, then move to its shot
            geo_keys.append((t - 0.6, drift(pose)))
            pose = SHOTS[l['shot']][1:]
            geo_keys.append((t + 2.6, pose))
        t += l['dur'] + (LONG if l['long_pause'] else GAP)
    geo_keys.append((t + 1.5, drift(pose)))
    t += 0.6
    geo_end = t

    seg_bounds.append(('B', t))
    t = node_section(list(range(3, 11)), t)
    seg_bounds.append(('C', t))
    t = node_section([11, 12], t)

    # ── aftermath, the closing part and the outro (stills), then the credits
    seg_bounds.append(('end', t))
    t = still_section(['aftermath', 'aftermath2', 'outro'], t + 0.2)
    credits_start = t + 0.6
    duration = credits_start + CREDITS
    stills[-1]['end'] = round(duration + 0.1, 3)

    def T_at(time):
        if time <= points[0][0]:
            return points[0][1]
        for (a, ta), (b, tb) in zip(points, points[1:]):
            if a <= time <= b:
                return ta if b == a else ta + (tb - ta) * (time - a) / (b - a)
        return points[-1][1]

    # ── segments: [start, end) with half a crossfade either side
    bounds = [b for _, b in seg_bounds] + [duration]
    specs = {'intro': ('tactical', 'keyed'), 'bg': ('strategic', 'still'), 'A': ('strategic', 'auto'), 'geo': ('tactical', 'keyed'),
             'B': ('tactical', 'auto'), 'C': ('strategic', 'auto'), 'end': ('strategic', 'still')}
    ranges = {'A': (0, 3), 'B': (3, 11), 'C': (11, 13)}
    for n, (name, _) in enumerate(seg_bounds):
        mp, cam = specs[name]
        s = max(0.0, bounds[n] - (XF / 2 if n > 0 else 0))
        e = min(duration, bounds[n + 1] + (XF / 2 if n < len(seg_bounds) - 1 else 0))
        f0, f1 = round(s * FPS), round(e * FPS)
        seg = {'name': name, 'map': mp, 'camera': cam, 'frame0': f0, 'frames': f1 - f0, 'start': round(f0 / FPS, 3), 'end': round(f1 / FPS, 3)}
        if cam != 'still':
            if name in ranges:
                lo, hi = ranges[name]
                seg['T'] = [round(min(max(T_at(f / FPS), lo), hi - 1e-4), 5) for f in range(f0, f1)]
            else:
                seg['T'] = [INTRO_T if name == 'intro' else GEO_T] * (f1 - f0)
            keys = INTRO_KEYS(river, intro_end + XF) if name == 'intro' else geo_keys if name == 'geo' else None
            if keys:
                seg['keys'] = [[round(a - f0 / FPS, 3), list(p[0]), p[1], p[2], p[3]] for a, p in keys]  # relative to the segment
        segments.append(seg)

    # sound: the sand table's T where it runs, None where stills are shown (30 Hz)
    live = [(s['start'], s['end']) for s in segments if s['camera'] in ('auto',)]
    sound = []
    for x in range(int(duration * 30) + 1):
        tt = x / 30
        if intro_end > tt:
            sound.append([round(tt, 4), INTRO_T])
        elif any(a <= tt < b for a, b in live):
            sound.append([round(tt, 4), round(T_at(tt), 5)])
        elif geo_start <= tt < geo_end:
            sound.append([round(tt, 4), GEO_T])
        else:
            sound.append([round(tt, 4), None])

    out = {
        'fps': FPS, 'duration': round(duration, 3), 'node_durations': [e['duration'] for e in EPS], 'xfade': XF, 'xfade_still': XF_STILL, 'intro_end': round(intro_end, 3),
        'title': title, 'credits_start': round(credits_start, 3), 'parts': parts, 'nodes_cards': node_cards, 'stills': stills,
        'lines': [{k: l[k] for k in ('i', 'vid', 'node', 'start', 'dur', 'text', 'say', 'long_pause', 'quote', 'src', 'shot')} for l in L],
        'segments': segments, 'sound': sound,
    }
    json.dump(out, open(f'{HERE}/doc_timeline.json', 'w'), ensure_ascii=False)
    return out


if __name__ == '__main__':
    o = build()
    print(f"duration {o['duration']:.1f}s ({o['duration'] / 60:.1f} min), intro {o['intro_end']:.1f}s, credits at {o['credits_start']:.1f}s")
    for s in o['segments']:
        print(f"  {s['name']:5s} {s['camera']:6s} {s['start']:7.1f} → {s['end']:7.1f}  ({(s['end'] - s['start']) / 60:4.1f} min, {s['frames']} frames)")
    live = sum(s['frames'] for s in o['segments'] if s['camera'] != 'still')
    print('live frames', live, f'≈ {live * 1.05 / 3600:.1f} h at 1.05 s/frame;', 'stills', len(o['stills']), 'parts', len(o['parts']), 'node cards', len(o['nodes_cards']))
