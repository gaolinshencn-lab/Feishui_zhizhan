"""The documentary's on-screen text as two ASS files and an SRT:
  doc_graphics.ass  title, part titles, node cards, quote cards, AI-voice labels, credits (burned in)
  doc_cc.ass        the narration as subtitles (burned in for the hard-subtitled version)
  narration.srt     the narration for Bilibili's CC track / the MP4's soft subtitle track
Subtitle chunks split at punctuation; their boundaries snap to pauses in the synthesised voice."""
import json, os, re, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
TL = json.load(open(f'{HERE}/doc_timeline.json'))
VOICE = os.environ.get('VOICE_DIR', f'{HERE}/voice_doc_t')
MAXLEN = 20
PUNCT = '，。；：、！？'
STRONG = '。；！？'
BREAK_COST = {'。': 0.0, '！': 0.0, '？': 0.0, '；': 0.1, '：': 0.35, '，': 0.45, '、': 1.2}
OPENERS = '曾在于从向把被将对与和及并而却也都又才就便由以为'
NUMERALS = '0123456789一二三四五六七八九十百千万两几'
MEASURES = '位个名人里年月日天次户艘匹骑员'
OPEN_MARKS = '“‘《「『（'
CLOSE_MARKS = '，。；：、！？”’》」』）⋯'
GOLD = '&H0078C4E8'
PAPER = '&H00E6EEF4'


def ts(t):
    t = max(0.0, t)
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f'{int(h)}:{int(m):02d}:{s:05.2f}'


def srt_ts(t):
    ms = int(round(max(0.0, t) * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'


def spoken_len(text):
    """Syllables the voice actually says (numbers read out)."""
    n = 0
    for tok in re.findall(r'\d+|.', text):
        if tok.isdigit():
            n += len(tok) if len(tok) >= 3 else (1 if len(tok) == 1 else 3)
        elif tok not in PUNCT + '“”「」《》·— ':
            n += 1
    return n


def split_clause(s):
    """Cuts a clause too long for one subtitle near its middle, before a word that usually opens a phrase,
    never between a numeral and its measure word or inside a 《book title》 or a quotation."""
    if len(s) <= MAXLEN:
        return [s]
    best, cut = None, None
    for j in range(max(2, int(len(s) * 0.3)), min(len(s) - 1, int(len(s) * 0.7) + 1)):
        score = abs(j - len(s) / 2)
        if s[j] in OPENERS:
            score -= 3
        if s[j - 1] == '的':
            score -= 1.5
        if s[j - 1] in NUMERALS or s[j] in NUMERALS + MEASURES:
            score += 10
        if s.count('《', 0, j) > s.count('》', 0, j) or s.count('“', 0, j) > s.count('”', 0, j):
            score += 100
        if best is None or score < best:
            best, cut = score, j
    return split_clause(s[:cut]) + split_clause(s[cut:])


def chunks(text):
    """Groups the clauses of a line into subtitles of at most MAXLEN shown characters: as few as possible,
    broken at the strongest punctuation available, sentences kept apart unless that leaves a fragment."""
    parts = re.findall(r'[^，。；：、！？]+[，。；：、！？]?', text)
    n = len(parts)
    best = [0.0] + [float('inf')] * n
    back = [0] * (n + 1)
    for i in range(1, n + 1):
        for j in range(i - 1, -1, -1):
            L = len(''.join(parts[j:i]).rstrip(PUNCT))
            if L > MAXLEN and i - j > 1:
                break
            cost = 1.0 + (0.6 if L <= 3 else 0.25 if L <= 6 else 0.0) + 0.001 * L * L  # the last term evens out lengths
            cost += 1.3 * sum(1 for p in parts[j:i - 1] if p[-1] in STRONG)
            if i < n:
                cost += BREAK_COST.get(parts[i - 1][-1], 0.6)
            if best[j] + cost < best[i]:
                best[i], back[i] = best[j] + cost, j
    out, i = [], n
    while i > 0:
        out.append(''.join(parts[back[i]:i]))
        i = back[i]
    final = []
    for c in reversed(out):
        s = c.rstrip(PUNCT)
        final += split_clause(s) if len(s) > MAXLEN else [c]
    return final


def pauses(path):
    """Voiced span and the silent gaps inside a line's audio."""
    with wave.open(path) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16 if w.getsampwidth() == 2 else np.int32).astype(np.float32)
    x /= np.abs(x).max() + 1e-9
    hop = int(sr * 0.01)
    e = np.array([np.sqrt(np.mean(x[i:i + hop] ** 2)) for i in range(0, len(x) - hop, hop)])
    thr = max(0.02, np.percentile(e, 90) * 0.08)
    voiced = e > thr
    idx = np.nonzero(voiced)[0]
    if len(idx) == 0:
        return 0, len(x) / sr, []
    first, last = idx[0] * 0.01, (idx[-1] + 1) * 0.01
    gaps, run = [], None
    for i in range(idx[0], idx[-1]):
        if not voiced[i] and run is None:
            run = i
        elif voiced[i] and run is not None:
            if (i - run) * 0.01 >= 0.12:
                gaps.append(((run + i) / 2) * 0.01)
            run = None
    return first, last, gaps


def subtitle_events():
    events = []
    for l in TL['lines']:
        parts = chunks(l['text'])
        path = f"{VOICE}/{l['vid']}.wav"
        first, last, gaps = pauses(path) if os.path.exists(path) else (0.0, l['dur'], [])
        total = sum(spoken_len(p) for p in parts) or 1
        bounds, acc = [first], 0
        for p in parts[:-1]:
            acc += spoken_len(p)
            guess = first + (last - first) * acc / total
            near = [g for g in gaps if abs(g - guess) < 0.7 and g > bounds[-1] + 0.3]
            bounds.append(min(near, key=lambda g: abs(g - guess)) if near else guess)
        bounds.append(last)
        for p, a, b in zip(parts, bounds, bounds[1:]):
            events.append((l['start'] + a - 0.05, l['start'] + b + 0.15, p.rstrip('，。；：、')))
    events.sort()
    # hold each subtitle a little into the pause after it (to the next one when the gap is short),
    # and on screen for at least 1.2 s
    for i in range(len(events)):
        a, b, t = events[i]
        nxt = events[i + 1][0] if i + 1 < len(events) else b + 2.0
        b = nxt if nxt - b < 0.6 else max(b + 0.3, a + 1.2)
        events[i] = (a, min(b, nxt - 0.04), t)
    return events


STYLES = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,Noto Sans CJK SC,52,&H00F4F4F4,&H00F4F4F4,&H00141210,&H96000000,0,0,0,0,100,100,2,0,1,3.2,1.2,2,120,120,56,1
Style: NodeNo,Noto Serif SC SemiBold,32,{gold},{gold},&H00141210,&H80000000,0,0,0,0,100,100,6,0,1,2.2,1,7,100,96,78,1
Style: Node,Ma Shan Zheng,84,{paper},{paper},&H00141210,&H80000000,0,0,0,0,100,100,8,0,1,3,1.5,7,96,96,116,1
Style: NodeDate,Noto Sans CJK SC,29,&H00C8D6E2,&H00C8D6E2,&H00141210,&H80000000,0,0,0,0,100,100,2,0,1,2,1,7,102,96,214,1
Style: PartNo,Noto Serif SC SemiBold,46,{gold},{gold},&H00101010,&H80000000,0,0,0,0,100,100,16,0,1,0,0,5,0,0,0,1
Style: Part,Ma Shan Zheng,168,{paper},{paper},&H00101010,&H80000000,0,0,0,0,100,100,20,0,1,0,2,5,0,0,0,1
Style: PartSub,Noto Sans CJK SC,34,&H00C8D8E6,&H00C8D8E6,&H00101010,&H80000000,0,0,0,0,100,100,6,0,1,0,0,5,0,0,0,1
Style: Title,Ma Shan Zheng,200,&H00E8F0F6,&H00E8F0F6,&H00101010,&H80000000,0,0,0,0,100,100,26,0,1,4,2,5,0,0,0,1
Style: TitleSub,Noto Sans CJK SC,42,&H00C8D8E6,&H00C8D8E6,&H00101010,&H80000000,0,0,0,0,100,100,10,0,1,2.4,1,5,0,0,0,1
Style: Quote,Noto Serif SC SemiBold,39,&H00EDF3F7,&H00EDF3F7,&H00101010,&H80000000,0,0,0,0,100,100,3,0,1,0,0,7,0,0,0,1
Style: QuoteSrc,Noto Sans CJK SC,26,{gold},{gold},&H00101010,&H80000000,0,0,0,0,100,100,2,0,1,0,0,9,0,0,0,1
Style: Box,Noto Sans CJK SC,20,&H00000000,&H00000000,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1
Style: Note,Noto Sans CJK SC,28,&H22F0F0F0,&H22F0F0F0,&H55101010,&H80000000,0,0,0,0,100,100,1,0,1,1.6,0,9,60,60,44,1
Style: Mark,Noto Sans CJK SC,21,&H88F0F0F0,&H88F0F0F0,&H99101010,&H80000000,0,0,0,0,100,100,1,0,1,1.2,0,3,40,36,22,1
Style: Credit,Noto Sans CJK SC,31,&H00E8E8E8,&H00E8E8E8,&H00101010,&H80000000,0,0,0,0,100,100,1,0,1,1.6,0,5,0,0,0,1
Style: CreditHead,Ma Shan Zheng,70,&H00E8F0F6,&H00E8F0F6,&H00101010,&H80000000,0,0,0,0,100,100,10,0,1,2.4,1,5,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""".replace('{gold}', GOLD).replace('{paper}', PAPER)

CREDITS = [
    '史料　《资治通鉴》卷一〇〇—一〇六　《晋书》帝纪、载记、谢安传、谢玄传、刘牢之传　《水经注》',
    '原文据维基文库所录文本核对；今人校勘意见参见中华书局点校本《晋书》校勘记',
    '地形　AWS Terrain Tiles（Mapzen）　水系　© OpenStreetMap contributors　Natural Earth',
    '三维沙盘、战场音效与配乐《前秦风雨》　均为本片原创，在浏览器中实时生成',
    '解说　AI 合成语音（CosyVoice 2），非真人配音，亦未模仿任何真实人物的声音',
    '字体　思源宋体 / 思源黑体（Noto CJK）　马善政楷书　均依 SIL OFL 授权使用',
    '营址、队形与行军路线多为依据史文与地形的推定，兵力数字以史书所载为准',
]


def wrap_quote(q, soft=10, hard=17):
    """Breaks a quote into lines of at most `hard` characters (a closing mark may hang one over), evenly and
    preferably after a full stop, then after a comma. No line starts with a closing mark or ends with an
    opening one, and the ellipsis stays whole."""
    units = []
    for ch in q.replace('……', '⋯'):
        if units and (ch in CLOSE_MARKS or units[-1][-1] in OPEN_MARKS):
            units[-1] += ch
        else:
            units.append(ch)
    n = len(units)
    best = [0.0] + [float('inf')] * n
    back = [0] * (n + 1)
    for i in range(1, n + 1):
        for j in range(i - 1, -1, -1):
            line = ''.join(units[j:i])
            L = len(line) + line.count('⋯')
            if L > hard + 1 and i - j > 1:
                break
            cost = 1.0 + 0.004 * L * L
            if i < n:
                end = line.rstrip('”’》」』）') or line
                cost += 0.0 if end[-1] in '。！？；⋯' else 0.35 if end[-1] in '，：' else 1.8 if end[-1] == '、' else 2.4
                cost += 0.6 if L < soft else 0.0
            elif L <= 3 and j > 0:
                cost += 1.0
            if best[j] + cost < best[i]:
                best[i], back[i] = best[j] + cost, j
    lines, i = [], n
    while i > 0:
        lines.append(''.join(units[back[i]:i]).replace('⋯', '……'))
        i = back[i]
    return lines[::-1]


def box(x0, y0, x1, y1, alpha='70', r=14):
    """A filled rounded rectangle (ASS drawing), dark and translucent."""
    d = (f'm {x0 + r} {y0} l {x1 - r} {y0} b {x1} {y0} {x1} {y0} {x1} {y0 + r} l {x1} {y1 - r} b {x1} {y1} {x1} {y1} {x1 - r} {y1} '
         f'l {x0 + r} {y1} b {x0} {y1} {x0} {y1} {x0} {y1 - r} l {x0} {y0 + r} b {x0} {y0} {x0} {y0} {x0 + r} {y0}')
    return r'{\an7\pos(0,0)\1c&H0B0D10&\1a&H' + alpha + r'&\bord0\shad0\p1}' + d + r'{\p0}'


def graphics():
    ev = []
    add = lambda layer, a, b, style, text: ev.append(f'Dialogue: {layer},{ts(a)},{ts(b)},{style},,0,0,0,,{text}')
    # the film's title
    t0, t1 = TL['title']['start'], TL['title']['end']
    add(4, t0, t1, 'Title', r'{\fad(900,900)\pos(960,500)}淝水之战')
    add(4, t0 + 0.5, t1, 'TitleSub', r'{\fad(900,900)\pos(960,668)}三维沙盘纪录片　·　公元383年')
    # AI-voice labels: at the start, small in the corner throughout, and in the credits
    add(5, 0.6, 11.0, 'Note', r'{\fad(600,800)}本片解说为AI合成语音')
    add(1, 11.0, TL['credits_start'], 'Mark', 'AI合成语音解说')
    # part titles: full screen
    for p in TL['parts']:
        a, b = p['start'], p['end']
        add(6, a, b + 0.2, 'Box', r'{\fad(600,700)}' + box(0, 0, 1920, 1080, alpha='48', r=0))
        add(7, a + 0.15, b, 'PartNo', r'{\fad(600,700)\pos(960,388)}' + p['no'])
        add(7, a + 0.3, b, 'Part', r'{\fad(700,700)\pos(960,540)}' + p['title'])
        if p['sub']:
            add(7, a + 0.6, b, 'PartSub', r'{\fad(700,700)\pos(960,706)}' + p['sub'])
        add(7, a + 0.15, b, 'Box', r'{\fad(600,700)}{\an7\pos(0,0)\1c' + GOLD + r'&\1a&H40&\bord0\shad0\p1}m 760 432 l 1160 432 1160 434 760 434{\p0}')
    # node cards: top left
    nums = '一二三四五六七八九十'
    for c in TL['nodes_cards']:
        a, b = c['start'], c['start'] + 6.0
        k = c['k'] + 1
        no = nums[k - 1] if k <= 10 else '十' + nums[k - 11]
        fade = r'{\fad(500,800)}'
        add(3, a, b, 'NodeNo', fade + f'第{no}节')
        add(3, a + 0.15, b, 'Node', fade + c['title'])
        add(3, a + 0.3, b, 'NodeDate', fade + f"{c['date']}　·　{c['western']}")
    # quote cards: top right, while the line is read
    for l in TL['lines']:
        if not l['quote']:
            continue
        rows = wrap_quote(l['quote'])
        lh, pad = 47, 32
        x1 = 1866
        w = max(len(r) for r in rows) * 40 + 2 * pad
        x0 = x1 - max(w, 420)
        y0 = 72
        y_src = y0 + pad + lh * len(rows) + 14
        y1 = y_src + 34 + 22
        a, b = l['start'] + 0.15, l['start'] + l['dur'] + 0.7
        fade = r'{\fad(450,500)}'
        add(2, a, b, 'Box', fade + box(x0, y0, x1, y1))
        add(2, a, b, 'Box', fade + r'{\an7\pos(0,0)\1c' + GOLD + r'&\1a&H30&\bord0\shad0\p1}' + f'm {x0} {y0 + 16} l {x0 + 5} {y0 + 16} {x0 + 5} {y1 - 16} {x0} {y1 - 16}' + r'{\p0}')
        add(3, a, b, 'Quote', fade + rf'{{\pos({x0 + pad},{y0 + pad - 4})}}' + r'\N'.join(rows))
        add(3, a, b, 'QuoteSrc', fade + rf'{{\pos({x1 - pad},{y_src})}}' + '——' + l['src'])
    # credits
    c0, end = TL['credits_start'], TL['duration']
    add(6, c0, end, 'Box', r'{\fad(900,0)}' + box(0, 0, 1920, 1080, alpha='1C', r=0))  # the table's labels stay out of the way
    add(7, c0 + 0.4, end, 'CreditHead', r'{\fad(800,0)\pos(960,250)}淝水之战　·　三维沙盘纪录片')
    for i, line in enumerate(CREDITS):
        add(7, c0 + 0.8 + 0.2 * i, end, 'Credit', rf'{{\fad(700,0)\pos(960,{392 + 70 * i})}}' + line)
    return ev


def build():
    g = graphics()
    with open(f'{HERE}/doc_graphics.ass', 'w') as f:
        f.write(STYLES + '\n'.join(g) + '\n')
    subs = subtitle_events()
    with open(f'{HERE}/doc_cc.ass', 'w') as f:
        f.write(STYLES + '\n'.join(f'Dialogue: 2,{ts(a)},{ts(b)},Sub,,0,0,0,,{t}' for a, b, t in subs) + '\n')
    with open(f'{HERE}/narration.srt', 'w') as f:
        for n, (a, b, t) in enumerate(subs, 1):
            f.write(f'{n}\n{srt_ts(a)} --> {srt_ts(b)}\n{t}\n\n')
    return g, subs


if __name__ == '__main__':
    g, subs = build()
    print(len(g), 'graphic events;', len(subs), 'subtitles,', max(len(t) for _, _, t in subs), 'chars max')
