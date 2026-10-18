"""Final assembly of the documentary: joins each segment's chunks, crossfades the segments, burns in the
graphics (title, part and node cards, quote cards, AI-voice labels, credits), adds the narration as a soft
CC subtitle track (and, with --hardsub, burns it in too), normalises loudness (EBU R128 two-pass, -15
LUFS, -1.5 dBTP) and encodes an H.264/AAC MP4 for Bilibili.
    python doc_assemble.py out.mp4 [--hardsub]"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TL = json.load(open(f'{HERE}/doc_timeline.json'))
CHUNKS = f'{HERE}/chunks'
FONTS = f'{HERE}/fonts'
OUT = next((a for a in sys.argv[1:] if not a.startswith('--')), f'{HERE}/feishui-documentary.mp4')
HARDSUB = '--hardsub' in sys.argv
FPS = TL['fps']


def run(cmd, **kw):
    print('$', ' '.join(cmd[:14]), '...' if len(cmd) > 14 else '', flush=True)
    return subprocess.run(cmd, check=True, **kw)


def frames_of(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-count_packets', '-show_entries', 'stream=nb_read_packets',
                        '-of', 'csv=p=0', path], capture_output=True, text=True, check=True)
    return int(r.stdout.strip())


def join_segments():
    out = []
    for seg in TL['segments']:
        files = sorted(f for f in os.listdir(CHUNKS) if f.startswith(seg['name'] + '_') and f.endswith('.mp4'))
        need = -(-seg['frames'] // 240)
        assert len(files) >= need, f"{seg['name']}: {len(files)}/{need} chunks"
        files = files[:need]
        lst = f"{CHUNKS}/{seg['name']}.txt"
        with open(lst, 'w') as f:
            f.writelines(f"file '{CHUNKS}/{x}'\n" for x in files)
        path = f"{CHUNKS}/seg_{seg['name']}.mp4"
        run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', path])
        have = frames_of(path)
        print(f"  {seg['name']}: {have} frames, timeline wants {seg['frames']}")
        out.append((path, have, seg))
    return out


def loudness():
    r = run(['ffmpeg', '-hide_banner', '-i', f'{HERE}/doc_mix.wav', '-af', 'loudnorm=I=-15:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'],
            capture_output=True, text=True)
    m = json.loads(r.stderr[r.stderr.rindex('{'):r.stderr.rindex('}') + 1])
    return (f"loudnorm=I=-15:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
            f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")


def main():
    segs = join_segments()
    an = loudness()
    xf = TL['xfade']
    chain = []
    for n, (path, have, seg) in enumerate(segs):
        want = seg['frames']
        fix = f'trim=end_frame={want},' if have > want else ''
        pad = f',tpad=stop_mode=clone:stop={want - have}' if have < want else ''
        # a light temporal denoise evens out the film grain of the first chunks (the rest render without it)
        chain.append(f'[{n}:v]{fix}setpts=PTS-STARTPTS,fps={FPS}{pad},hqdn3d=2:1.5:4:3,format=yuv420p[s{n}]')
    last = '[s0]'
    for n, (_, _, seg) in enumerate(segs[1:], 1):
        lab = f'[x{n}]'
        chain.append(f"{last}[s{n}]xfade=transition=fade:duration={xf}:offset={seg['start']:.4f}{lab}")
        last = lab
    subs = f"subtitles={HERE}/doc_graphics.ass:fontsdir={FONTS}"
    if HARDSUB:
        subs += f",subtitles={HERE}/doc_cc.ass:fontsdir={FONTS}"
    chain.append(f'{last}{subs},format=yuv420p[v]')
    na = len(segs)
    chain.append(f'[{na}:a]{an},aresample=48000[a]')
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-stats']
    for path, _, _ in segs:
        cmd += ['-i', path]
    cmd += ['-i', f'{HERE}/doc_mix.wav', '-i', f'{HERE}/narration.srt', '-filter_complex', ';'.join(chain),
            '-map', '[v]', '-map', '[a]', '-map', f'{na + 1}:s',
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '19', '-profile:v', 'high', '-level', '4.1', '-r', str(FPS),
            '-g', str(FPS * 2), '-bf', '3', '-c:a', 'aac', '-b:a', '256k', '-ar', '48000', '-metadata:s:a:0', 'language=chi',
            '-c:s', 'mov_text', '-metadata:s:s:0', 'language=chi', '-metadata:s:s:0', 'title=解说字幕（CC）', '-disposition:s:0', 'default',
            '-movflags', '+faststart', '-metadata', 'title=淝水之战 · 三维沙盘纪录片', '-metadata', 'comment=解说为AI合成语音',
            '-t', f"{TL['duration']:.3f}", OUT]
    run(cmd)
    print('wrote', OUT)


if __name__ == '__main__':
    main()
