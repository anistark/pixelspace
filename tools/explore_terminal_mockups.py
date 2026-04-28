#!/usr/bin/env python3
"""Throwaway: render gap-aesthetic mockups for the pixelspace-terminal decision.

Outputs build/mockups/comparison.png — a single composite showing three TUI
scenarios (vim split, btop half-block bars, starship powerline prompt) rendered
twice each, side by side: 'gappy' (current Pixelspace pixel style applied to
box-drawing) vs 'flush' (edge-to-edge pixels). Plus a bonus close-up of a few
plain letters using the existing font, so the gappy column reflects what
pixelspace already looks like today.

This file is throwaway and not wired into the build / justfile.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
TTF = ROOT / "fonts" / "Pixelspace-Regular.ttf"
OUT_DIR = ROOT / "build" / "mockups"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Each Pixelspace pixel renders as CELL image-px.
CELL = 22
INNER = round(CELL * 110 / 125)         # = 19 at CELL=22
RADIUS = max(1, round(INNER * 0.10))    # = 2
INK = (32, 32, 40)
BG = (250, 248, 244)
DIVIDER = (210, 200, 188)
LABEL = (110, 90, 70)
HEADING = (32, 32, 40)

# A small system font for English labels (column headers, captions). Tries a
# few candidates so this works on macOS / Linux / fallback.
def _load_label_font(size):
    for path in (
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


HEADING_FONT = _load_label_font(28)
LABEL_FONT = _load_label_font(16)


# ---------- pixel renderers ----------

def gappy_pixel(d, col, row, origin):
    """Draw one Pixelspace-style rounded-corner pixel (signature look)."""
    cx = origin[0] + col * CELL
    cy = origin[1] + row * CELL
    d.rounded_rectangle(
        [cx, cy, cx + INNER - 1, cy + INNER - 1],
        radius=RADIUS, fill=INK,
    )


def flush_pixel(d, col, row, origin):
    """Draw one flush edge-to-edge pixel (proposed terminal look)."""
    cx = origin[0] + col * CELL
    cy = origin[1] + row * CELL
    d.rectangle([cx, cy, cx + CELL - 1, cy + CELL - 1], fill=INK)


# ---------- 5x7 glyph bitmaps ----------
# Each entry is a list of (col, row) cells that are "on" in a 5-col × 7-row
# grid. Box-drawing chars use the canonical mid-row/mid-col convention.

def _box_corner(cols, rows):
    return [(c, 3) for c in cols] + [(2, r) for r in rows]


GLYPHS = {
    # box-drawing
    "─": [(c, 3) for c in range(5)],
    "│": [(2, r) for r in range(7)],
    "┌": _box_corner(range(2, 5), range(3, 7)),
    "┐": _box_corner(range(0, 3), range(3, 7)),
    "└": _box_corner(range(2, 5), range(0, 4)),
    "┘": _box_corner(range(0, 3), range(0, 4)),
    "├": [(c, 3) for c in range(2, 5)] + [(2, r) for r in range(7)],
    "┤": [(c, 3) for c in range(0, 3)] + [(2, r) for r in range(7)],
    # blocks
    "█": [(c, r) for c in range(5) for r in range(7)],
    "▀": [(c, r) for c in range(5) for r in range(4)],
    "▄": [(c, r) for c in range(5) for r in range(3, 7)],
    "░": [(c, r) for c in range(5) for r in range(7) if (c + r) % 2 == 0],
    # powerline (PUA)
    "▶": [(0, r) for r in range(7)]
         + [(1, r) for r in range(1, 6)]
         + [(2, r) for r in range(2, 5)]
         + [(3, 3)],
    " ": [],
    # a few lowercase letters for inline labels (rough hand-drawn 5x7)
    "a": [(1,2),(2,2),(3,2),(4,3),(1,4),(2,4),(3,4),(4,4),(0,5),(4,5),(1,6),(2,6),(3,6),(4,6)],
    "c": [(1,2),(2,2),(3,2),(0,3),(4,3),(0,4),(0,5),(4,5),(1,6),(2,6),(3,6)],
    "d": [(4,0),(4,1),(1,2),(2,2),(3,2),(4,2),(0,3),(4,3),(0,4),(4,4),(0,5),(4,5),(1,6),(2,6),(3,6),(4,6)],
    "e": [(1,2),(2,2),(3,2),(0,3),(4,3),(0,4),(1,4),(2,4),(3,4),(4,4),(0,5),(1,6),(2,6),(3,6),(4,6)],
    "h": [(0,0),(0,1),(0,2),(1,2),(2,2),(3,2),(0,3),(4,3),(0,4),(4,4),(0,5),(4,5),(0,6),(4,6)],
    "i": [(2,0),(2,2),(2,3),(2,4),(2,5),(2,6)],
    "l": [(2,0),(2,1),(2,2),(2,3),(2,4),(2,5),(2,6)],
    "m": [(0,2),(1,2),(3,2),(0,3),(2,3),(4,3),(0,4),(2,4),(4,4),(0,5),(2,5),(4,5),(0,6),(2,6),(4,6)],
    "n": [(0,2),(1,2),(2,2),(3,2),(0,3),(4,3),(0,4),(4,4),(0,5),(4,5),(0,6),(4,6)],
    "p": [(0,2),(1,2),(2,2),(3,2),(0,3),(4,3),(0,4),(1,4),(2,4),(3,4),(0,5),(0,6)],
    "r": [(0,2),(2,2),(3,2),(4,2),(0,3),(1,3),(0,4),(0,5),(0,6)],
    "s": [(1,2),(2,2),(3,2),(4,2),(0,3),(1,4),(2,4),(3,4),(4,5),(0,6),(1,6),(2,6),(3,6)],
    "t": [(2,0),(2,1),(1,2),(2,2),(3,2),(2,3),(2,4),(2,5),(3,6)],
    "v": [(0,2),(4,2),(0,3),(4,3),(0,4),(4,4),(1,5),(3,5),(2,6)],
    "/": [(4,1),(3,2),(3,3),(2,3),(2,4),(1,4),(1,5),(0,6)],
    "~": [(0,2),(1,2),(4,2),(2,3),(3,3),(0,4),(3,4),(4,4)],
    ">": [(0,2),(1,3),(2,4),(1,5),(0,6)],
    "x": [(0,2),(4,2),(1,3),(3,3),(2,4),(1,5),(3,5),(0,6),(4,6)],
}


# Characters whose pixel style flips between scenarios. Letters & punctuation
# always render gappy (the existing Pixelspace look is preserved). Only
# box-drawing, blocks, and powerline glyphs use the scenario's draw_fn.
STRUCTURAL = set("─│┌┐└┘├┤█▀▄░▶")


def render_text(d, text, char_col, char_row, draw_fn, origin):
    """Render a string of glyphs. Structural chars use draw_fn (the scenario's
    pixel style); content chars (letters, punctuation) always use gappy."""
    for i, ch in enumerate(text):
        cells = GLYPHS.get(ch, [])
        char_origin = (
            origin[0] + (char_col + i) * 6 * CELL,
            origin[1] + char_row * 7 * CELL,
        )
        pen = draw_fn if ch in STRUCTURAL else gappy_pixel
        for c, r in cells:
            pen(d, c, r, char_origin)


# ---------- scenario painters (each receives a draw_fn) ----------

def paint_vim_split(canvas, origin, draw_fn):
    d = ImageDraw.Draw(canvas)
    cols = 12
    # row 0: ┌ ─×(cols-2) ┐
    line = "┌" + "─" * (cols - 2) + "┐"
    render_text(d, line, 0, 0, draw_fn, origin)
    # rows 1: │ src/      │
    render_text(d, "│", 0, 1, draw_fn, origin)
    render_text(d, "src/", 2, 1, draw_fn, origin)
    render_text(d, "│", cols - 1, 1, draw_fn, origin)
    # row 2: ├ ─×(cols-2) ┤
    mid = "├" + "─" * (cols - 2) + "┤"
    render_text(d, mid, 0, 2, draw_fn, origin)
    # row 3: │ test/     │
    render_text(d, "│", 0, 3, draw_fn, origin)
    render_text(d, "test/", 2, 3, draw_fn, origin)
    render_text(d, "│", cols - 1, 3, draw_fn, origin)
    # row 4: └ ─×(cols-2) ┘
    bot = "└" + "─" * (cols - 2) + "┘"
    render_text(d, bot, 0, 4, draw_fn, origin)


def paint_btop_bars(canvas, origin, draw_fn):
    d = ImageDraw.Draw(canvas)
    # 12 columns of bars with varying heights using ▄ █ ▀
    # Each "bar slot" is one char wide, rows 0-4 tall
    heights = [1.0, 2.5, 3.5, 4.0, 3.5, 2.5, 4.5, 5.0, 4.0, 2.5, 3.0, 1.5]
    rows_total = 5
    for col, h in enumerate(heights):
        # h is in units of full rows; render full blocks bottom-up, then a half on top
        full = int(h)
        half = (h - full) >= 0.5
        # bottom-up fill: rows from (rows_total - full) to (rows_total - 1)
        for r in range(rows_total - full, rows_total):
            render_text(d, "█", col, r, draw_fn, origin)
        if half:
            top_row = rows_total - full - 1
            if top_row >= 0:
                render_text(d, "▄", col, top_row, draw_fn, origin)


def paint_powerline(canvas, origin, draw_fn):
    # A simulated starship prompt:  ▶ ~/code  main ▶
    d = ImageDraw.Draw(canvas)
    s = "▶ ~/code main ▶"
    render_text(d, s, 0, 0, draw_fn, origin)


# ---------- composite layout ----------

def make_comparison():
    margin = 40
    col_pad = 60
    row_pad = 50
    # Per-scenario char dimensions (cols × rows). Height in char-rows.
    scenarios = [
        ("vim split / box-drawing", (12, 5), paint_vim_split),
        ("btop bars / half-blocks", (12, 5), paint_btop_bars),
        ("starship prompt / powerline", (15, 1), paint_powerline),
    ]
    # Compute per-column width and total height
    panel_w = max(w for _, (w, _h), _ in scenarios) * 6 * CELL
    total_w = margin * 2 + col_pad + 2 * panel_w + col_pad
    header_h = 90
    panel_heights = [h * 7 * CELL + 30 for _, (_w, h), _ in scenarios]
    total_h = margin + header_h + sum(panel_heights) + row_pad * (len(scenarios) - 1) + margin

    img = Image.new("RGB", (total_w, total_h), BG)
    d = ImageDraw.Draw(img)

    # Title
    d.text((margin, margin), "Pixelspace terminal — gap aesthetic",
           font=HEADING_FONT, fill=HEADING)
    d.text((margin, margin + 40),
           "Compare the same TUI scenarios with two pixel styles for box-drawing / blocks.",
           font=LABEL_FONT, fill=LABEL)

    # Column headers
    col_x = [margin + col_pad, margin + col_pad + panel_w + col_pad]
    header_y = margin + header_h - 30
    d.text((col_x[0], header_y), "GAPPY  (current Pixelspace look)",
           font=LABEL_FONT, fill=LABEL)
    d.text((col_x[1], header_y), "FLUSH  (proposed for terminal)",
           font=LABEL_FONT, fill=LABEL)

    # Vertical divider between columns
    div_x = (col_x[0] + panel_w + col_x[1]) // 2
    d.line([(div_x, margin + header_h), (div_x, total_h - margin)],
           fill=DIVIDER, width=2)

    # Scenarios
    y = margin + header_h
    for (label, (w, h), painter), panel_h in zip(scenarios, panel_heights):
        d.text((margin, y - 4), label, font=LABEL_FONT, fill=LABEL)
        # Left panel: gappy
        painter(img, (col_x[0], y + 22), gappy_pixel)
        # Right panel: flush
        painter(img, (col_x[1], y + 22), flush_pixel)
        y += panel_h + row_pad

    out = OUT_DIR / "comparison.png"
    img.save(out)
    print(f"wrote {out.relative_to(ROOT)}  ({out.stat().st_size // 1024} KB, {img.size[0]}×{img.size[1]})")


# ---------- bonus: existing-font sample for reference ----------

def make_existing_sample():
    """Render a small sample of the actual current Pixelspace font for reference,
    so the user can compare the hand-drawn 'gappy' approximation in comparison.png
    against what the real font produces today."""
    font = ImageFont.truetype(str(TTF), 96)
    rows = [
        "$ ls -la",
        "src/  test/",
        "ABCDEFGHIJ",
        "abcdefghij",
    ]
    img = Image.new("RGB", (1100, 540), BG)
    d = ImageDraw.Draw(img)
    d.text((40, 30), "Reference: real Pixelspace font (no terminal additions yet)",
           font=LABEL_FONT, fill=LABEL)
    for i, r in enumerate(rows):
        d.text((40, 80 + i * 110), r, font=font, fill=INK)
    out = OUT_DIR / "reference_existing.png"
    img.save(out)
    print(f"wrote {out.relative_to(ROOT)}  ({out.stat().st_size // 1024} KB, {img.size[0]}×{img.size[1]})")


if __name__ == "__main__":
    make_comparison()
    make_existing_sample()
