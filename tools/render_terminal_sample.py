#!/usr/bin/env python3
"""Render Pixelspace at realistic terminal sizes to validate the gappy
aesthetic for box-drawing / blocks against the actual font (not hand-drawn
mockups).

Outputs build/mockups/terminal_sample.png — a single composite showing the
same vim-split-style scene rendered at three font sizes:
  - 14px (cramped terminal default — pixel cell ≈ 2 image-px)
  - 21px (3× natural — clean integer-pixel rendering)
  - 42px (6× natural — design-detail visible)

This is throwaway — it isn't wired into the build / justfile.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
TTF = ROOT / "fonts" / "Pixelspace-Regular.ttf"
OUT = ROOT / "build" / "mockups" / "terminal_sample.png"
OUT.parent.mkdir(parents=True, exist_ok=True)

INK = (32, 32, 40)
DIM = (130, 130, 140)
BG = (250, 248, 244)
LABEL = (110, 90, 70)


def _label_font(size):
    for path in (
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


HEAD_FONT = _label_font(28)
LABEL_FONT = _label_font(15)

# A multi-line scene exercising the full v1.100 terminal-coverage glyphs:
# light/heavy/double box-drawing, half-blocks, eighths-blocks, shade blocks,
# and quadrants. Each section is labelled so the user can spot the variants.
SCENE = [
    "┌─ light box ───────────┐",
    "│ src/                  │",
    "│ ├─ build_font.py      │",
    "│ └─ glyphs.txt         │",
    "├───────────────────────┤",
    "┏━ heavy box ━━━━━━━━━━━┓",
    "┃ ▏▎▍▌▋▊▉█ left eighths ┃",
    "┃ ▁▂▃▄▅▆▇█ low  eighths ┃",
    "┣━━━━━━━━━━━━━━━━━━━━━━━┫",
    "╔═ double box ══════════╗",
    "║ ░░▒▒▓▓██ shades       ║",
    "║ ▖▗▘▝▙▚▛▜▞▟ quadrants  ║",
    "╚═══════════════════════╝",
    "├ ╭ rounded ╮ ─ /─\\─/ ─┤",
    "│ cpu ▄▆█▆█▂▂▄▄ 47%     │",
    "│ mem ▆▆▆▆▆▆▂▆▆ 68%     │",
    "│ net ▄▄▄█▄▄▄▄▄ 12 MB/s │",
    "└───────────────────────┘",
]

SIZES = [
    (14, "14px — typical small terminal (each pixel ≈ 2 image-px)"),
    (21, "21px — 3× clean rendering"),
    (42, "42px — 6× design-detail visible"),
]


def render():
    pad = 30
    label_h = 50
    section_gap = 40

    # Pre-measure each section so we can size the canvas correctly.
    sections = []
    for px, caption in SIZES:
        font = ImageFont.truetype(str(TTF), px)
        # Measure the widest line and total height. Pixelspace is monospace so
        # one measurement suffices; just pad a bit.
        bbox = font.getbbox(SCENE[0])
        line_w = bbox[2] - bbox[0]
        line_h = int(px * 1.43)   # font has 1250/875 line height (143%)
        block_h = line_h * len(SCENE)
        sections.append((px, caption, font, line_w, line_h, block_h))

    img_w = pad * 2 + max(s[3] for s in sections)
    img_h = (
        pad
        + 60   # title
        + sum(label_h + s[5] + section_gap for s in sections)
        + pad
    )
    img = Image.new("RGB", (img_w, img_h), BG)
    d = ImageDraw.Draw(img)

    d.text((pad, pad), "Pixelspace terminal — real-font sample",
           font=HEAD_FONT, fill=INK)
    d.text((pad, pad + 36), "Box-drawing & blocks rendered by the actual TTF "
           "(not hand-drawn mockups). 14 new glyphs added to glyphs.txt.",
           font=LABEL_FONT, fill=LABEL)

    y = pad + 80
    for px, caption, font, line_w, line_h, block_h in sections:
        d.text((pad, y), caption, font=LABEL_FONT, fill=LABEL)
        y += label_h - 20
        for line in SCENE:
            d.text((pad, y), line, font=font, fill=INK)
            y += line_h
        y += section_gap

    img.save(OUT)
    print(f"wrote {OUT.relative_to(ROOT)} ({img.size[0]}×{img.size[1]})")


if __name__ == "__main__":
    render()
