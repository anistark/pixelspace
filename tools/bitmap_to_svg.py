#!/usr/bin/env python3
"""Regenerate sources/Pixelspace.svg from sources/glyphs.txt.

The SVG is kept around as a versioned artifact for SVG-font-aware tooling
(some external converters and previewers expect SVG-font input). It is no
longer the canonical source — glyphs.txt is. Run this after editing
glyphs.txt to keep the SVG in sync, or wire it into a build recipe.

The regenerated SVG is not aimed at byte-identity with the original
hand-written file (formatting differs, the metadata text is regenerated),
but it parses back through build_font.parse_svg_font() to the same data,
so the produced TTF is identical.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from parse_bitmap import PIXEL, parse_bitmap  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources" / "glyphs.txt"
DST = ROOT / "sources" / "Pixelspace.svg"

# XML special chars that must be entity-encoded inside an attribute value.
_XML_ESCAPE = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&#34;",
    "'": "&#39;",
}


def _esc_unicode_attr(ch: str) -> str:
    return _XML_ESCAPE.get(ch, ch)


def pixels_to_path(pixels: list[tuple[int, int]]) -> str:
    return "".join(f"M{x},{y}h{PIXEL}v-{PIXEL}h-{PIXEL}Z" for x, y in pixels)


def emit_svg(data: dict) -> str:
    m = data["metrics"]
    glyphs = sorted(data["glyphs"], key=lambda g: ord(g["char"]))
    bbox = f"0 {m['descent']} {m['cap_height']} {m['cap_height']}"

    lines: list[str] = []
    lines.append('<?xml version="1.0" standalone="no"?>')
    lines.append("")
    lines.append('<svg xmlns="http://www.w3.org/2000/svg">')
    lines.append("  <metadata>")
    lines.append(f"    Pixelspace — a 5x7 pixel font with {len(glyphs)} glyphs.")
    lines.append("    Generated from sources/glyphs.txt by tools/bitmap_to_svg.py.")
    lines.append("    Grid: 5 columns x 7 rows. 1 pixel = 125 font units. units-per-em = 875.")
    lines.append("  </metadata>")
    lines.append("  <defs>")
    lines.append(f'    <font id="Pixelspace" horiz-adv-x="{m["default_adv"]}">')
    lines.append(
        '      <font-face font-family="Pixelspace" font-weight="400" '
        'font-stretch="normal" '
        f'units-per-em="{m["upem"]}" '
        f'ascent="{m["ascent"]}" descent="{m["descent"]}" '
        f'cap-height="{m["cap_height"]}" x-height="{m["x_height"]}" '
        f'bbox="{bbox}" panose-1="{m["panose"]}" '
        f'underline-position="{m["underline_position"]}" '
        f'underline-thickness="{m["underline_thickness"]}"></font-face>'
    )

    if data.get("missing"):
        path = pixels_to_path(data["missing"]["pixels"])
        adv = data["missing"]["adv"]
        lines.append(
            f'      <missing-glyph horiz-adv-x="{adv}" d="{path}"></missing-glyph>'
        )

    for g in glyphs:
        uni_attr = _esc_unicode_attr(g["char"])
        path = pixels_to_path(g["pixels"])
        lines.append(
            f'    <glyph glyph-name="{g["name"]}" unicode="{uni_attr}" '
            f'horiz-adv-x="{g["adv"]}" d="{path}"></glyph>'
        )

    lines.append("    </font>")
    lines.append("  </defs>")
    lines.append("</svg>")

    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    data = parse_bitmap(SRC)
    text = emit_svg(data)
    DST.write_text(text, encoding="utf-8")
    print(
        f"wrote {DST.relative_to(ROOT)} "
        f"({len(text)} bytes, {len(data['glyphs'])} glyphs)"
    )
