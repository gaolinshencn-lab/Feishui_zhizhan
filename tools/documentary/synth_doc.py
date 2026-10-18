# Synthesises the documentary narration with CosyVoice2 (instruct mode: documentary style, preset
# narrator's reference clip). Resumable: a line is redone only if its file is missing or its text changed.
# Lines whose length is far from the expected speaking time are retried with other seeds.
#   python synth_doc.py [order=live|all] [only=1,2,3] [seed=N]
import sys, os, json, re, time
TTS_HOME = os.environ.get('TTS_HOME', '/root/tts')  # CosyVoice code, models and the narrator's reference clip
sys.path.insert(0, TTS_HOME)
sys.path.insert(0, TTS_HOME + '/cv2-studio'); sys.path.insert(0, TTS_HOME + '/cv2-studio/third_party/Matcha-TTS')
VIDEO = os.environ.get('DOC_DIR', os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, VIDEO)
import torch, torchaudio
torch.set_num_threads(int(os.environ.get('TTS_THREADS', '4')))
from doc_script import lines, SECTIONS
from cosyvoice.cli.cosyvoice import CosyVoice2
from cosyvoice.utils.file_utils import load_wav
from cosyvoice.utils.common import set_all_random_seed

STYLE = '用沉稳浑厚、从容舒缓的纪录片解说语气讲述。'
OUT = f'{VIDEO}/voice_doc'
os.makedirs(OUT, exist_ok=True)
INDEX = f'{OUT}/index.json'
args = dict(a.split('=', 1) for a in sys.argv[1:] if '=' in a)
only = set(int(x) for x in args['only'].split(',')) if 'only' in args else None
seed_base = int(args.get('seed', 2000))
SPEED = float(args.get('speed', 0.95))
index = json.load(open(INDEX)) if os.path.exists(INDEX) else {}

L = list(lines())
order = list(range(len(L)))
if args.get('order', 'live') == 'live':
    # live-rendered sections first, so their footage can start while the stills' lines are synthesised
    order.sort(key=lambda i: (SECTIONS[L[i]['node']][1] == 'still', i))

cv = CosyVoice2(TTS_HOME + '/models/CosyVoice2-0.5B', load_jit=False, load_trt=False, fp16=False)
import fastpatch
fastpatch.apply(cv, flow_bf16=True)  # same tokens; ~25% faster
prompt = load_wav(TTS_HOME + '/out/prompt_male.wav', 16000)


def expected(say):
    return len(re.sub(r'[^一-鿿]', '', say)) / (3.9 * SPEED) + 0.2 * len(re.findall(r'[，。；：、！？]', say))


for i in order:
    l = L[i]
    path = f"{OUT}/{l['vid']}.wav"
    fresh = os.path.exists(path) and index.get(l['vid'], {}).get('speed') == SPEED
    if only is None and fresh:
        continue
    if only is not None and i not in only:
        continue
    t = time.time()
    exp = expected(l['say'])
    best = None
    for k in range(3):
        seed = seed_base + i + 1000 * k
        set_all_random_seed(seed)
        audio = torch.cat([j['tts_speech'] for j in cv.inference_instruct2(l['say'], STYLE, prompt, stream=False, speed=SPEED)], dim=1)
        dur = audio.shape[1] / cv.sample_rate
        ratio = dur / exp
        if best is None or abs(ratio - 1) < abs(best[2] - 1):
            best = (audio, seed, ratio)
        if 0.7 < ratio < 1.45:
            break
    audio, seed, ratio = best
    torchaudio.save(path, audio, cv.sample_rate)
    index[l['vid']] = {'say': l['say'], 'seed': seed, 'speed': SPEED, 'dur': round(audio.shape[1] / cv.sample_rate, 2)}
    json.dump(index, open(INDEX, 'w'), ensure_ascii=False, indent=0)
    print(json.dumps({'i': i, 'vid': l['vid'], 'node': l['node'], 'dur': index[l['vid']]['dur'], 'ratio': round(ratio, 2), 'seed': seed,
                      'secs': round(time.time() - t, 1), 'text': l['text'][:30]}, ensure_ascii=False), flush=True)
print('done', flush=True)
