"""Bilibili covers from a rendered frame: darkened left side, calligraphic title, gold line, small series
line. Text stays inside the central 4:3 area so the cover still reads when Bilibili crops it.
    python doc_cover.py frame.png"""
import os, sys
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
TITLE_FONT = f'{HERE}/fonts/MaShanZheng-Regular.ttf'
SERIF = f'{HERE}/fonts/NotoSerifSC-SemiBold.otf'
SANS = f'{HERE}/fonts/NotoSansCJKsc-Bold.otf'


def cover(frame, out, size):
    w, h = size
    src = Image.open(frame).convert('RGB')
    # fill the target aspect from the frame's centre-right (the battlefield), then darken towards the left
    sw, sh = src.size
    scale = max(w / sw, h / sh)
    src = src.resize((round(sw * scale), round(sh * scale)), Image.LANCZOS)
    x0 = (src.width - w) // 2 + (src.width - w) // 4
    im = src.crop((x0, (src.height - h) // 2, x0 + w, (src.height - h) // 2 + h))
    shade = Image.new('L', size)
    d = ImageDraw.Draw(shade)
    for x in range(w):
        d.line([(x, 0), (x, h)], fill=int(215 * max(0.0, 1 - x / (w * 0.66)) ** 1.25))
    im = Image.composite(Image.new('RGB', size, (12, 10, 8)), im, shade)
    draw = ImageDraw.Draw(im)
    left = int(w * (0.5 - 0.375 * h / w * 4 / 3)) + int(h * 0.06)  # inside the central 4:3 area
    tf = ImageFont.truetype(TITLE_FONT, int(h * 0.24))
    for dx in (6, 3):
        draw.text((left + dx, int(h * 0.17) + dx), '淝水之战', font=tf, fill=(0, 0, 0))
    draw.text((left, int(h * 0.17)), '淝水之战', font=tf, fill=(245, 237, 222))
    sf = ImageFont.truetype(SERIF, int(h * 0.072))
    draw.text((left + 8, int(h * 0.49)), '八万，对阵号称百万', font=sf, fill=(234, 198, 122), stroke_width=3, stroke_fill=(20, 14, 8))
    tf2 = ImageFont.truetype(SANS, int(h * 0.043))
    draw.text((left + 10, int(h * 0.62)), '三维沙盘纪录片 · 引经据典讲透前因后果', font=tf2, fill=(240, 232, 216), stroke_width=2, stroke_fill=(20, 14, 8))
    im.save(out, quality=93)


if __name__ == '__main__':
    frame = sys.argv[1]
    cover(frame, f'{HERE}/cover-16x9.jpg', (1920, 1080))
    cover(frame, f'{HERE}/cover-4x3.jpg', (1440, 1080))
    print('covers written')
