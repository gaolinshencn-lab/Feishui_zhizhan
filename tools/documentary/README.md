# 《淝水之战》三维沙盘纪录片 · 制作流程

用本仓库的三维沙盘（`docs/index.html`）逐帧渲染画面，配上 AI 合成的纪录片解说、沙盘自带的战场音效和原创配乐《前秦风雨》，生成约 35 分钟的科普纪录片。这里是生成这部片子的全部脚本；成片、配音和中间素材体积太大，不放进仓库。

解说词与引文见 [`docs/documentary-script.md`](../../docs/documentary-script.md)。每一条引文都对照维基文库所录《资治通鉴》《晋书》《水经注》原文核对过（`check_quotes.py`）。

## 结构

| 文件 | 作用 |
| --- | --- |
| `doc_script.py` | 解说词：分段、镜头、沙盘进度提示、原文引文与出处；`SAY` 表把生僻字、多音字换成同音字，只影响朗读 |
| `synth_doc.py` · `fastpatch.py` | CosyVoice 2（指令模式，"沉稳浑厚、从容舒缓的纪录片解说语气"）逐句合成，可断点续跑；`fastpatch` 跳过 Qwen2 用不到的整词表输出层、流匹配解码用 bf16，CPU 上快约 25% |
| `qa_doc.py` · `fix_lines.py` · `takes.py` · `pick.py` | 两个语音识别模型（Paraformer、SenseVoice）听写比对带声调拼音；问题句换随机种子重录，择优保留（`takes.py` 只合成、`pick.py` 只打分，分两个进程跑可省内存） |
| `doc_tighten.py` | 适度压缩句内过长停顿 |
| `doc_timeline.py` | 时间轴：每句起点、沙盘时间 T 与镜头、章节卡、引文卡、静帧段；各渲染段使用各自的时间基准 |
| `capture_doc.mjs` | 逐帧驱动沙盘（`app.captureFrame`）截图编码；按镜头运动量自适应抽帧（静止时最多隔 3 帧，运动时逐帧），其余帧以 `framerate` 滤镜混合补齐；可多进程分片、断点续跑 |
| `stills_doc.mjs` · `kenburns.py` | 背景与尾声部分：4K 静帧上的缓推缓移 |
| `doc-sound.mjs` · `www/doc-sound.js` | 用沙盘自己的声音引擎离线渲染每个实时段的战场音效 |
| `doc_music.py` · `doc_mix.py` | 配乐（低音铺底 + 《前秦风雨》）与混音：音效、音乐在解说下自动避让 |
| `doc_subs.py` | 片名、章节卡、节点卡、引文卡、AI 合成语音标识、片尾（ASS，烧录）；解说字幕（SRT，作 CC 软字幕） |
| `doc_assemble.py` | 拼接、交叉淡化、烧录图文、响度归一（-15 LUFS），输出 H.264/AAC MP4，内嵌 CC 字幕轨 |
| `doc_notes.py` | B 站投稿信息（标题、简介、分段章节、标签、AI 声明） |
| `cover_still.mjs` · `doc_cover.py` | 封面：以 4K 渲染决战时刻（镜头偏离脚本位置，把左上角留给标题），再排上片名 |

## 运行顺序

```bash
python doc_script.py                       # 统计字数、检查分段
python synth_doc.py && python qa_doc.py    # 配音与质检（CosyVoice 2 环境，TTS_HOME 指向模型目录）
python fix_lines.py 84 85                  # 重录有问题的句子
python doc_tighten.py && python doc_timeline.py
node stills_doc.mjs doc_timeline.json stills && python kenburns.py
PIXEL_RATIO=0.8 node capture_doc.mjs doc_timeline.json chunks A,geo,B,C 0 2   # 两个进程各渲染一半
PIXEL_RATIO=0.8 node capture_doc.mjs doc_timeline.json chunks A,geo,B,C 1 2
# 以 www/ 为根在 127.0.0.1:8765 起静态服务（www/src → 仓库 src，www/video → 本目录），然后每个实时段：
node doc-sound.mjs B fx_B.wav
python doc_music.py && python doc_mix.py && python doc_subs.py
python doc_assemble.py feishui-documentary.mp4            # 加 --hardsub 则同时烧录解说字幕
python doc_notes.py
node cover_still.mjs 9.27 2 '[{"name":"cover4k","fx":0.13,"fy":0.11,"dist":0.95,"pitch":-8}]' covers
python doc_cover.py covers/cover4k.png
```

渲染在无 GPU 的机器上用 SwiftShader 完成：1080p 每张约 1.2 秒，自适应抽帧后整片约 4–5 小时（4 核）。
