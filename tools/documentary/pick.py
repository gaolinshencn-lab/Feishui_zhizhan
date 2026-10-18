# Scores the current file and the alternative takes of each line by ASR (pinyin with tones, best of two
# recognisers) and keeps the best:   python pick.py 15 16 32
import sys, os, json, re, glob
VIDEO = os.environ.get('DOC_DIR', os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, VIDEO)
import soundfile as sf
from doc_script import lines
from pypinyin import lazy_pinyin, Style
from tn.chinese.normalizer import Normalizer
from funasr import AutoModel
tn = Normalizer()
asr = AutoModel(model='iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch', disable_update=True, log_level='ERROR')
asr2 = AutoModel(model='iic/SenseVoiceSmall', disable_update=True, log_level='ERROR')
py = lambda s: lazy_pinyin(re.sub(r'[^一-鿿]', '', s), style=Style.TONE3, neutral_tone_with_five=True)
def dist(a, b):
    d = list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        prev, d[0] = d[0], i
        for j in range(1, len(b) + 1):
            cur = min(d[j] + 1, d[j - 1] + 1, prev + (a[i - 1] != b[j - 1]))
            prev, d[j] = d[j], cur
    return d[len(b)]
def score(path, say):
    ref = py(tn.normalize(say))
    h1 = asr.generate(input=path, batch_size_s=300)[0]['text'].replace(' ', '')
    h2 = re.sub(r'<\|[^|]*\|>', '', asr2.generate(input=path, language='zh', use_itn=False)[0]['text']).replace(' ', '')
    return min(dist(ref, py(h1)) / len(ref), dist(ref, py(h2)) / len(ref))
L = list(lines())
idx_path = f'{VIDEO}/voice_doc/index.json'
index = json.load(open(idx_path))
for i in map(int, sys.argv[1:]):
    l = L[i]
    cur = f"{VIDEO}/voice_doc/{l['vid']}.wav"
    cands = [(score(cur, l['say']), cur)] + [(score(p, l['say']), p) for p in sorted(glob.glob(f'{VIDEO}/voice_doc/.take_{i}_*.wav'))]
    best = min(cands)
    print(json.dumps({'i': i, 'scores': [(round(s, 3), os.path.basename(p)) for s, p in cands], 'kept': os.path.basename(best[1])}), flush=True)
    if best[1] != cur:
        os.replace(best[1], cur)
        info = sf.info(cur)
        index[l['vid']]['dur'] = round(info.frames / info.samplerate, 2)
        index[l['vid']]['seed'] = 'take'
        json.dump(index, open(idx_path, 'w'), ensure_ascii=False, indent=0)
    for _, p in cands:
        if p != cur and os.path.exists(p):
            os.remove(p)
print('done', flush=True)
