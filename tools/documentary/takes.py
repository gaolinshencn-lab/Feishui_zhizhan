# Synthesises alternative takes of given lines (no ASR in this process, to stay within memory):
#   python takes.py 15 16 32 [takes=3]   ->  voice_doc/.take_<i>_<k>.wav
import sys, os, json
TTS_HOME = os.environ.get('TTS_HOME', '/root/tts')
sys.path.insert(0, TTS_HOME + '/cv2-studio'); sys.path.insert(0, TTS_HOME + '/cv2-studio/third_party/Matcha-TTS'); sys.path.insert(0, TTS_HOME)
VIDEO = os.environ.get('DOC_DIR', os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, VIDEO)
import torch, torchaudio
torch.set_num_threads(4)
from doc_script import lines
from cosyvoice.cli.cosyvoice import CosyVoice2
from cosyvoice.utils.file_utils import load_wav
from cosyvoice.utils.common import set_all_random_seed
import fastpatch
args = [int(a) for a in sys.argv[1:] if '=' not in a]
opts = dict(a.split('=', 1) for a in sys.argv[1:] if '=' in a)
L = list(lines())
cv = CosyVoice2(TTS_HOME + '/models/CosyVoice2-0.5B', load_jit=False, load_trt=False, fp16=False)
fastpatch.apply(cv, flow_bf16=True)
prompt = load_wav(TTS_HOME + '/out/prompt_male.wav', 16000)
for i in args:
    for k in range(int(opts.get('takes', 3))):
        seed = 5000 + 977 * k + i
        set_all_random_seed(seed)
        audio = torch.cat([j['tts_speech'] for j in cv.inference_instruct2(L[i]['say'], '用沉稳浑厚、从容舒缓的纪录片解说语气讲述。', prompt, stream=False, speed=0.95)], dim=1)
        torchaudio.save(f'{VIDEO}/voice_doc/.take_{i}_{k}.wav', audio, cv.sample_rate)
        print(json.dumps({'i': i, 'k': k, 'seed': seed, 'dur': round(audio.shape[1] / cv.sample_rate, 2)}), flush=True)
print('done', flush=True)
