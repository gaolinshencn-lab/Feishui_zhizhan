"""Writes the upload notes (title, description with chapter times, tags, declarations) and the full
narration script with its sources, both as Markdown, from the final timeline."""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
TL = json.load(open(f'{HERE}/doc_timeline.json'))


def mmss(t):
    t = int(round(t))
    return f'{t // 60:02d}:{t % 60:02d}'


def chapters():
    marks = [(0.0, '序章')]
    for p in TL['parts']:
        marks.append((p['start'], f"{p['no']} {p['title']}"))
    for c in TL['nodes_cards']:
        marks.append((c['start'], f"　{c['title']}"))
    marks.append((TL['credits_start'], '片尾'))
    return sorted(marks)


def notes():
    dur = TL['duration']
    out = [
        '# B站投稿信息',
        '',
        '## 标题（任选其一）',
        '',
        '- 【三维沙盘纪录片】淝水之战：八万晋军，如何击溃号称百万的前秦大军？',
        '- 投鞭断流、草木皆兵、风声鹤唳——用三维沙盘复原淝水之战（引经据典·完整版）',
        '',
        '## 简介',
        '',
        f'公元383年，统一北方的前秦天王苻坚号称百万南征，东晋只派出八万人迎战。本片用一座按真实地形复原的三维沙盘，'
        f'从两个王朝的由来讲起，经太极殿廷议、大军南下、寿阳失守、洛涧夜袭、草木皆兵、淝水决战，一直讲到前秦瓦解与南北朝的开端。'
        f'所引原文均据《资治通鉴》《晋书》《水经注》核对。全片约{dur / 60:.0f}分钟。',
        '',
        '解说为AI合成语音（非真人配音，未模仿任何真实人物的声音）；沙盘、音效与配乐《前秦风雨》均为原创。',
        '营址、队形与行军路线多为依据史文与地形的推定。',
        '',
        '## 章节时间（可填入“分段章节”）',
        '',
    ]
    for t, name in chapters():
        out.append(f'- {mmss(t)}　{name.strip()}')
    out += [
        '',
        '## 标签',
        '',
        '淝水之战、历史、纪录片、三维沙盘、东晋、前秦、苻坚、谢安、谢玄、资治通鉴、晋书、军事史、以少胜多、成语故事、五胡十六国',
        '',
        '## 视频文件',
        '',
        '- `feishui-documentary-hevc.mp4`：单个文件，H.265 编码，约 400 MB，可直接上传。',
        '- 原画质版（H.264，1,439,925,482 字节）分成 `feishui-documentary.mp4.001` 到 `.004` 四段，下载到同一文件夹后合并成一个文件：',
        '  - Windows（在该文件夹打开“命令提示符”）：`copy /b feishui-documentary.mp4.001+feishui-documentary.mp4.002+feishui-documentary.mp4.003+feishui-documentary.mp4.004 feishui-documentary.mp4`',
        '  - macOS / Linux（终端）：`cat feishui-documentary.mp4.00? > feishui-documentary.mp4`',
        '  - 也可以用 7-Zip 选中 `.001` 文件，点“文件 → 合并文件”。',
        '- 两个版本内容相同；原画质版码率更高，B站转码后画面更清楚，上传优先用它。',
        '',
        '## 投稿设置建议',
        '',
        '- 分区：知识 → 人文历史（或 社科·法律·心理 / 科学科普 中的历史类）',
        '- 类型：自制',
        '- **创作声明：勾选“作品含AI生成内容”**（解说为AI合成语音）。画面内片头、角落和片尾也已标注“AI合成语音”。',
        '- 字幕：在投稿页的字幕设置里上传 `narration.srt`（语言选中文），观众就能开关CC字幕。B站不读取视频文件里内嵌的字幕轨；内嵌字幕轨供本地播放器（PotPlayer、VLC、IINA 等）使用。',
        '- 封面：`cover-16x9.jpg`（另附 `cover-4x3.jpg` 备用）。',
        '',
        '## 史料',
        '',
        '《资治通鉴》卷一〇〇、一〇三—一〇六（含“臣光曰”）；《晋书》卷九《孝武帝纪》、卷七十九《谢安传》《谢玄传》、'
        '卷八十四《刘牢之传》、卷九十八《王敦传》、卷一一三—一一四《苻坚载记》《王猛载记》；《水经注》卷三十《淮水》、卷三十二《肥水》。',
        '',
    ]
    with open(f'{HERE}/bilibili-upload.md', 'w') as f:
        f.write('\n'.join(out))


def script():
    parts = {p['sec']: p for p in TL['parts']}
    out = ['# 《淝水之战》三维沙盘纪录片 · 解说词', '', '时间为成片中的位置；引文均据维基文库所录《资治通鉴》《晋书》《水经注》核对。', '']
    sec = None
    for l in TL['lines']:
        if l['node'] in parts and l['node'] != sec:
            p = parts[l['node']]
            out += ['', f"## {p['no']}　{p['title']}", '']
        sec = l['node']
        line = f"`{mmss(l['start'])}`　{l['text']}"
        if l['quote']:
            line += f"\n\n> {l['quote']}\n> ——{l['src']}"
        out += [line, '']
    with open(f'{HERE}/narration-script.md', 'w') as f:
        f.write('\n'.join(out))


if __name__ == '__main__':
    notes()
    script()
    print('wrote bilibili-upload.md and narration-script.md')
