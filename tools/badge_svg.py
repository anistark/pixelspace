#!/usr/bin/env python3
"""Generate docs/badge.svg — a "font: Pixelspace" badge rendered in the font.

Both segments — the "font" label and the "Pixelspace" wordmark — are drawn
from the canonical bitmaps in sources/glyphs.txt using the same pixel
primitive as the font: each "on" pixel is an inset rounded square (110 units
in a 125-unit cell, 10% corner radius), leaving the signature 15-unit gap on
the right and bottom. Both share one row grid, so they sit at the same pixel
size on a common baseline. Because every pixel is a plain <rect>, the badge
renders identically everywhere — including GitHub's image proxy — with no
font to load.

Run after editing glyphs.txt (or the constants below) to refresh the badge:

    just badge        # or: uv run tools/badge_svg.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from parse_bitmap import COLS, PIXEL, parse_bitmap  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources" / "glyphs.txt"
DST = ROOT / "docs" / "badge.svg"

# ---- Badge content & style -------------------------------------------------
LABEL = "font"               # left segment
WORDMARK = "Pixelspace"      # right segment

CELL = 5                     # screen px per design pixel
INNER_PCT = (PIXEL - 15) / PIXEL   # 110/125 — inner square as fraction of cell
RADIUS_PCT = 0.10 * INNER_PCT      # corner radius as fraction of cell

PAD_X = 14                   # px padding inside each segment, left/right
PAD_Y = 9                    # px padding above/below the tallest ink
CORNER = 4                   # outer rounded-corner radius

LABEL_BG = "#6e4a32"         # brand brown
WORD_BG = "#000000"
FG = "#f4ecd8"               # warm cream from the site palette


def char_grid(data: dict):
    """char -> list of (col, row) on-cells (row 0 = top), and char -> advance in cells."""
    cells: dict[str, list[tuple[int, int]]] = {}
    adv_cells: dict[str, int] = {}
    for g in data["glyphs"]:
        cells[g["char"]] = [(x // PIXEL, 5 - (y // PIXEL)) for x, y in g["pixels"]]
        adv_cells[g["char"]] = g["adv"] // PIXEL
    return cells, adv_cells


def layout(text: str, cells, adv_cells):
    """Return (rects, width_cells, min_row, max_row) for `text`, in cell units."""
    rects: list[tuple[int, int]] = []
    pen = 0
    min_row, max_row = 99, -1
    for ch in text:
        if ch not in cells:
            raise SystemExit(f"badge: no glyph for {ch!r} in the font")
        for col, row in cells[ch]:
            rects.append((pen + col, row))
            min_row, max_row = min(min_row, row), max(max_row, row)
        pen += adv_cells[ch]
    # trim the trailing right-side bearing of the last glyph from the width
    width_cells = pen - (adv_cells[text[-1]] - COLS) if text else 0
    return rects, width_cells, min_row, max_row


def main() -> None:
    data = parse_bitmap(SRC)
    cells, adv_cells = char_grid(data)

    lbl, lbl_w, lbl_lo, lbl_hi = layout(LABEL, cells, adv_cells)
    wrd, wrd_w, wrd_lo, wrd_hi = layout(WORDMARK, cells, adv_cells)

    inner = CELL * INNER_PCT
    radius = CELL * RADIUS_PCT
    min_row, max_row = min(lbl_lo, wrd_lo), max(lbl_hi, wrd_hi)

    height = (max_row - min_row + 1) * CELL + 2 * PAD_Y
    oy = PAD_Y - min_row * CELL                       # shared row->y, common baseline
    label_seg = lbl_w * CELL + 2 * PAD_X
    word_seg = wrd_w * CELL + 2 * PAD_X
    total_w = label_seg + word_seg

    px = lambda v: f"{v:.2f}".rstrip("0").rstrip(".")

    def emit(rects, ox):
        for col, row in rects:
            yield (f'      <rect x="{px(ox + col * CELL)}" y="{px(oy + row * CELL)}" '
                   f'width="{px(inner)}" height="{px(inner)}" rx="{px(radius)}"/>')

    out: list[str] = []
    out.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total_w}" '
        f'height="{height}" viewBox="0 0 {total_w} {height}" '
        f'role="img" aria-label="{LABEL} {WORDMARK}">'
    )
    out.append(f"  <title>{LABEL}: {WORDMARK}</title>")
    out.append(f'  <clipPath id="r"><rect width="{total_w}" height="{height}" '
               f'rx="{CORNER}"/></clipPath>')
    out.append('  <g clip-path="url(#r)">')
    out.append(f'    <rect width="{label_seg}" height="{height}" fill="{LABEL_BG}"/>')
    out.append(f'    <rect x="{label_seg}" width="{word_seg}" height="{height}" '
               f'fill="{WORD_BG}"/>')
    out.append(f'    <g fill="{FG}">')
    out.extend(emit(lbl, PAD_X))
    out.extend(emit(wrd, label_seg + PAD_X))
    out.append("    </g>")
    out.append("  </g>")
    out.append("</svg>")

    svg = "\n".join(out) + "\n"
    DST.write_text(svg, encoding="utf-8")
    print(f"wrote {DST.relative_to(ROOT)} ({total_w}x{height}, "
          f"{len(lbl) + len(wrd)} pixels)")


if __name__ == "__main__":
    main()
