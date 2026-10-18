import os, sys, re, glob, difflib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib, doc_script
importlib.reload(doc_script)
S = os.environ.get('SRC_TEXTS', 'src_texts')  # Wikisource texts, simplified
han = lambda s: re.sub(r'[^一-鿿]', '', s)
texts = {p: open(p, encoding='utf-8').read() for p in glob.glob(f'{S}/*.s.txt')}
H = {p: han(t) for p, t in texts.items()}
def where(src):
    if not src: return list(H)
    if '通鉴' in src:
        m = re.search(r'卷(一〇〇|一〇二|一〇三|一〇四|一〇五|一〇六)', src)
        if m:
            n = {'一〇〇':'100','一〇二':'102','一〇三':'103','一〇四':'104','一〇五':'105','一〇六':'106'}[m.group(1)]
            return [p for p in H if f'卷{n}' in p]
    return list(H)
for i, l in enumerate(doc_script.lines()):
    q = l['quote']
    if not q: continue
    parts = [han(x) for x in re.split(r'……', q) if han(x)]
    res = []
    for part in parts:
        hits = [p for p in where(l['src']) if part in H[p]]
        if not hits:
            hits = [p for p in H if part in H[p]]
            res.append(('OTHER:' + ','.join(h.split('/')[-1] for h in hits)) if hits else 'MISS')
        else:
            res.append('ok:' + ','.join(h.split('/')[-1][:-6] for h in hits))
    flag = all(r.startswith('ok') for r in res)
    print(i, 'OK ' if flag else '!! ', l['src'], '|', q[:40], '|', res)
    if not flag:
        # show best matching window for misses
        for part, r in zip(parts, res):
            if r.startswith('ok'): continue
            best = (0, None, None)
            for p in H:
                h = H[p]
                L = len(part)
                sm = difflib.SequenceMatcher(None, part, '', autojunk=False)
                # seed by longest common substrings of 4 chars
                seeds = set()
                for k in range(0, max(1, L - 4), 2):
                    s4 = part[k:k+4]
                    for m in re.finditer(re.escape(s4), h):
                        seeds.add(max(0, m.start() - k))
                for st in list(seeds)[:200]:
                    w = h[max(0, st - 10): st + L + 10]
                    r2 = difflib.SequenceMatcher(None, part, w, autojunk=False).ratio()
                    if r2 > best[0]: best = (r2, p, w)
            print('     best %.2f %s: %s' % (best[0], best[1], best[2]))
