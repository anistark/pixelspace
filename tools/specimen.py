#!/usr/bin/env python3
"""Render article/specimen.png — the hero image used in ARTICLE.en_us.html.

Pixelspace renders pixel-perfect at em sizes that are multiples of 7
(one design pixel = 125/875 = 1/7 of em), so all sizes here are 7×n.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
TTF = ROOT / "fonts" / "Pixelspace-Regular.ttf"
OUT = ROOT / "article" / "specimen.png"

W, H = 1600, 960
MARGIN = 40

img = Image.new("RGB", (W, H), "white")
draw = ImageDraw.Draw(img)

title = ImageFont.truetype(str(TTF), 140)   # 20 px / pixel
sub = ImageFont.truetype(str(TTF), 49)      # 7 px / pixel
body = ImageFont.truetype(str(TTF), 56)     # 8 px / pixel

draw.text((MARGIN, 0), "Pixelspace", font=title, fill="black")
draw.text((MARGIN, 210), "A 5x7 pixel display typeface", font=sub, fill="#444")
draw.text((MARGIN, 290), "Single weight . 474 glyphs", font=sub, fill="#444")

rows = [
    "ABCDEFGHIJKLMN",
    "OPQRSTUVWXYZ",
    "abcdefghijklmn",
    "opqrstuvwxyz",
    "0123456789 .,:;!?",
    "┌─┬─┐ ━ ═ ░▒▓█ ▖▗▘▝",
]
y = 390
for row in rows:
    draw.text((MARGIN, y), row, font=body, fill="black")
    y += 80

img.save(OUT)
print(f"wrote {OUT.relative_to(ROOT)}")
