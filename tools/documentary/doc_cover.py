"""Bilibili covers from a rendered frame (best a 3840x2160 still with the action in the lower right, see
cover_still.mjs): the upper left is darkened, with the calligraphic title, a gold line and a small series
line on a soft dark halo. Text stays inside the central 4:3 area so the cover still reads when Bilibili
crops it.
    python doc_cover.py frame.png"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
TITLE_FONT = f'{HERE}/fonts/MaShanZheng-Regular.ttf'
SERIF = f'{HERE}/fonts/NotoSerifSC-SemiBold.otf'
SANS = f'{HERE}/fonts/NotoSansCJKsc-Bold.otf'
LINES = [  # text, font, size and top as fractions of the height, colour
    ('淝水之战', TITLE_FONT, 0.215, 0.06, (246, 238, 222)),
    ('八万，对阵号称百万', SERIF, 0.068, 0.335, (236, 200, 124)),
    ('三维沙盘纪录片 · 引经据典讲透前因后果', SANS, 0.04, 0.445, (238, 230, 214)),
]


def cover(frame, out, size):
    w, h = size
    src = Image.open(frame).convert('RGB')
    # fill the target aspect, keeping the right-hand side of the frame (where the action is)
    sw, sh = src.size
    scale = max(w / sw, h / sh)
    src = src.resize((round(sw * scale), round(sh * scale)), Image.LANCZOS, reducing_gap=2.0)
    x0 = (src.width - w) * 3 // 4
    im = src.crop((x0, (src.height - h) // 2, x0 + w, (src.height - h) // 2 + h))

    left = max(0, (w - h * 4 // 3) // 2) + int(h * 0.075)
    fonts = [ImageFont.truetype(f, int(h * s)) for _, f, s, _, _ in LINES]
    # darken the upper left, falling off diagonally towards the battle, plus a soft halo behind the text
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    grad = np.clip(1 - (0.62 * xx / w + 0.85 * yy / h) / 0.95, 0, None) ** 1.15 * (200 / 255)
    halo = Image.new('L', size)
    hd = ImageDraw.Draw(halo)
    for (text, _, s, top, _), font in zip(LINES, fonts):
        hd.text((left, int(h * top)), text, font=font, fill=255, stroke_width=int(h * s * 0.12))
    halo = np.asarray(halo.filter(ImageFilter.GaussianBlur(h * 0.03)), np.float32) / 255 * 0.62
    dark = 1 - (1 - grad) * (1 - halo)
    im = Image.composite(Image.new('RGB', size, (10, 8, 6)), im, Image.fromarray((dark * 255).astype(np.uint8), 'L'))

    draw = ImageDraw.Draw(im)
    for (text, path, s, top, colour), font in zip(LINES, fonts):
        y = int(h * top)
        if path == TITLE_FONT:
            for d in (int(h * 0.006), int(h * 0.003)):
                draw.text((left + d, y + d), text, font=font, fill=(0, 0, 0))
            draw.text((left, y), text, font=font, fill=colour)
        else:
            draw.text((left + int(h * 0.005), y), text, font=font, fill=colour,
                      stroke_width=max(2, int(h * 0.0025)), stroke_fill=(16, 12, 8))
    im.save(out, quality=93)


if __name__ == '__main__':
    frame = sys.argv[1]
    cover(frame, f'{HERE}/cover-16x9.jpg', (1920, 1080))
    cover(frame, f'{HERE}/cover-4x3.jpg', (1440, 1080))
    print('covers written')
