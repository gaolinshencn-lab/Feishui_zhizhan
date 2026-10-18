# Listens to every synthesised line through ASR and compares pronunciations (pinyin with tones).
import os, sys, json, re, wave
sys.path.insert(0, os.environ.get('DOC_DIR', os.path.dirname(os.path.abspath(__file__))))
from doc_script import lines
from pypinyin import lazy_pinyin, Style
from tn.chinese.normalizer import Normalizer
from funasr import AutoModel
V = os.environ.get('DOC_DIR', os.path.dirname(os.path.abspath(__file__))) + '/' + (sys.argv.pop(1) if len(sys.argv) > 1 and sys.argv[1].startswith('voice') else 'voice_doc')
tn = Normalizer()
asr = AutoModel(model='iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch', disable_update=True, log_level='ERROR')
asr2 = AutoModel(model='iic/SenseVoiceSmall', disable_update=True, log_level='ERROR')
def py(s):
    s = re.sub(r'[^一-鿿]', '', s)
    return lazy_pinyin(s, style=Style.TONE3, neutral_tone_with_five=True)
def dist(a, b):
    d = list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        prev, d[0] = d[0], i
        for j in range(1, len(b) + 1):
            cur = min(d[j] + 1, d[j - 1] + 1, prev + (a[i - 1] != b[j - 1]))
            prev, d[j] = d[j], cur
    return d[len(b)]
only = set(int(x) for x in sys.argv[1:]) or None
for i, l in enumerate(lines()):
    if only and i not in only:
        continue
    path = f"{V}/{l['vid']}.wav"
    try:
        with wave.open(path) as w:
            dur = w.getnframes() / w.getframerate()
    except FileNotFoundError:
        continue
    ref = tn.normalize(l['say'])
    hyp = asr.generate(input=path, batch_size_s=300)[0]['text'].replace(' ', '')
    hyp2 = re.sub(r'<\|[^|]*\|>', '', asr2.generate(input=path, language='zh', use_itn=False)[0]['text']).replace(' ', '')
    pr = py(ref)
    per1, per2 = dist(pr, py(hyp)) / max(1, len(pr)), dist(pr, py(hyp2)) / max(1, len(pr))
    per = min(per1, per2)
    if per2 < per1:
        hyp = hyp2
    rate = len(re.sub(r'[^一-鿿]', '', ref)) / dur
    flag = 'BAD' if per > 0.06 else 'ok'
    print(json.dumps({'i': i, 'per': round(per, 3), 'rate': round(rate, 2), 'flag': flag, 'hyp': hyp, 'ref': re.sub(r'[^一-鿿]', '', ref)}, ensure_ascii=False), flush=True)
