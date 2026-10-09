"""
Build static/images/pdf-watermark.png, the tiled /try/ preview watermark.

    .venv/bin/python scripts/make_pdf_watermark.py static/images/pdf-watermark.png 0.24

The second argument is the text opacity. xhtml2pdf only honours transparency
in RGBA PNGs (palette and grey+alpha render black), so the image is RGBA with
one colour everywhere and only alpha varying, which keeps it small. The font
path is macOS; point it at any bold TTF elsewhere.
"""
import sys
from PIL import Image, ImageDraw, ImageFont

W, H = 850, 1100  # 8.5x11in at 100dpi
font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf', 30)
text = 'FREE PREVIEW  ·  INVOICEKITS.COM'
fill = (120, 128, 140, int(255 * float(sys.argv[2])))

big = Image.new('RGBA', (W * 2, H * 2), fill[:3] + (0,))
d = ImageDraw.Draw(big)
tw = d.textlength(text, font=font) + 80
for row, y in enumerate(range(0, H * 2, 127)):
    offset = (row % 2) * tw / 2
    x = -offset
    while x < W * 2:
        d.text((x, y), text, font=font, fill=fill)
        x += tw
big = big.rotate(30, resample=Image.BICUBIC, fillcolor=fill[:3] + (0,))
alpha = big.crop((W // 2, H // 2, W // 2 + W, H // 2 + H)).getchannel('A')
# One colour everywhere, only alpha varies: compresses far smaller.
out = Image.new('RGBA', (W, H), fill[:3] + (0,))
out.putalpha(alpha)
out.save(sys.argv[1], optimize=True)
