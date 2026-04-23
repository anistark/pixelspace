#!/usr/bin/env python3
"""Render a Pixelspace preview PNG with uppercase, lowercase, digits + punct."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
TTF = ROOT / "fonts" / "Pixelspace-Regular.ttf"
OUT = ROOT / "fonts" / "Pixelspace-Regular.png"

rows = [
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    "abcdefghijklmnopqrstuvwxyz",
    "0123456789 .,:;!?\"'&()[]{}<>/\\|~`",
]

font = ImageFont.truetype(str(TTF), 64)
img = Image.new("RGB", (1800, 380), "white")
draw = ImageDraw.Draw(img)
for i, row in enumerate(rows):
    draw.text((16, 16 + i * 100), row, font=font, fill="black")
img.save(OUT)
print(f"wrote {OUT.relative_to(ROOT)}")
