# Re-synthesises flagged narration lines with other seeds, scores every take by ASR (pinyin with tones,
# best of two recognisers) and keeps the best one.   python fix_lines.py 40 52 ...  [takes=3]
import sys, os, json, re, time
TTS_HOME = os.environ.get('TTS_HOME', '/root/tts')  # CosyVoice code, models and the narrator's reference clip
sys.path.insert(0, TTS_HOME + '/cv2-studio'); sys.path.insert(0, TTS_HOME + '/cv2-studio/third_party/Matcha-TTS'); sys.path.insert(0, TTS_HOME)
VIDEO = os.environ.get('DOC_DIR', os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, VIDEO)
import torch, torchaudio
torch.set_num_threads(4)
from doc_script import lines
from cosyvoice.cli.cosyvoice import CosyVoice2
from cosyvoice.utils.file_utils import load_wav
from cosyvoice.utils.common import set_all_random_seed
from pypinyin import lazy_pinyin, Style
from tn.chinese.normalizer import Normalizer
from funasr import AutoModel
import fastpatch

STYLE = '用沉稳浑厚、从容舒缓的纪录片解说语气讲述。'
SPEED = 0.95
OUT = f'{VIDEO}/voice_doc'
args = [a for a in sys.argv[1:] if '=' not in a]
opts = dict(a.split('=', 1) for a in sys.argv[1:] if '=' in a)
TAKES = int(opts.get('takes', 3))
idx_path = f'{OUT}/index.json'
index = json.load(open(idx_path))
L = list(lines())

tn = Normalizer()
asr = AutoModel(model='iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch', disable_update=True, log_level='ERROR')
asr2 = AutoModel(model='iic/SenseVoiceSmall', disable_update=True, log_level='ERROR')
cv = CosyVoice2(TTS_HOME + '/models/CosyVoice2-0.5B', load_jit=False, load_trt=False, fp16=False)
fastpatch.apply(cv, flow_bf16=True)
prompt = load_wav(TTS_HOME + '/out/prompt_male.wav', 16000)


def py(s):
    return lazy_pinyin(re.sub(r'[^一-鿿]', '', s), style=Style.TONE3, neutral_tone_with_five=True)


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
    p1, p2 = dist(ref, py(h1)) / max(1, len(ref)), dist(ref, py(h2)) / max(1, len(ref))
    return (p1, h1) if p1 <= p2 else (p2, h2)


for i in map(int, args):
    l = L[i]
    path = f"{OUT}/{l['vid']}.wav"
    takes = []
    if os.path.exists(path):
        takes.append((score(path, l['say'])[0], path, index.get(l['vid'], {}).get('seed')))
    for k in range(TAKES):
        seed = 5000 + 977 * k + i
        set_all_random_seed(seed)
        audio = torch.cat([j['tts_speech'] for j in cv.inference_instruct2(l['say'], STYLE, prompt, stream=False, speed=SPEED)], dim=1)
        tmp = f'{OUT}/.take_{i}_{k}.wav'
        torchaudio.save(tmp, audio, cv.sample_rate)
        per, hyp = score(tmp, l['say'])
        takes.append((per, tmp, seed))
        print(json.dumps({'i': i, 'seed': seed, 'per': round(per, 3), 'hyp': hyp}, ensure_ascii=False), flush=True)
        if per == 0:
            break
    best = min(takes, key=lambda x: x[0])
    if best[1] != path:
        os.replace(best[1], path)
        w = torchaudio.info(path)
        index[l['vid']] = {'say': l['say'], 'seed': best[2], 'speed': SPEED, 'dur': round(w.num_frames / w.sample_rate, 2)}
        json.dump(index, open(idx_path, 'w'), ensure_ascii=False, indent=0)
    for _, p, _ in takes:
        if p != path and os.path.exists(p):
            os.remove(p)
    print(json.dumps({'i': i, 'kept_per': round(best[0], 3), 'seed': best[2]}), flush=True)
print('done', flush=True)
