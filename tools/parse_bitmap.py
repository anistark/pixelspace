#!/usr/bin/env python3
"""Parse sources/glyphs.txt — Pixelspace's canonical bitmap source format.

Produces the same dict shape as tools/build_font.parse_svg_font(), so
build_font.build() can consume either source identically.

Format
------
- Lines starting with `;` are comments (run to EOL). Blank lines separate
  sections. The `#` character is reserved for bitmap pixels.
- `@meta` section: key: value lines for font-face metrics.
- `@glyph <name>` section: optional `unicode: U+XXXX` line, optional
  `adv: N` line (defaults to default-adv from @meta), then exactly 7 lines
  of bitmap (5 cols wide). `.` = off pixel, `#` = on pixel.
- The glyph named `.notdef` becomes the missing-glyph fallback. All other
  glyphs require a `unicode:` field.

Coordinates
-----------
Bitmap row 0 is the top row (cap-top, y=625). Row 4 is the bottom of the
cap area (y=125). Row 5 starts the descender (y=0). Row 6 is the bottom
descender row (y=-125). Column 0 is at x=0; column 4 at x=500.

Each on-pixel emits (x, y) = (col * 125, (5 - row) * 125), matching what
parse_svg_font() returns from M-command coordinates in the SVG-font path.
"""
from __future__ import annotations

import re
from pathlib import Path

PIXEL = 125
ROWS_TOTAL = 7
ROWS_ABOVE_BASELINE = 5
COLS = 5

_HEADING = re.compile(r"^@(meta|glyph)(?:\s+(\S+))?\s*$")
_KV = re.compile(r"^([\w-]+)\s*:\s*(.+?)\s*$")
_UNICODE = re.compile(r"^[Uu]\+?([0-9A-Fa-f]+)$")


def _strip_comment(line: str) -> str:
    semi = line.find(";")
    if semi >= 0:
        line = line[:semi]
    return line.rstrip()


def _row_to_y(r: int) -> int:
    return (ROWS_ABOVE_BASELINE - r) * PIXEL


def _bitmap_to_pixels(rows: list[str], gname: str) -> list[tuple[int, int]]:
    if len(rows) != ROWS_TOTAL:
        raise SystemExit(
            f"glyph {gname!r}: expected {ROWS_TOTAL} bitmap rows, got {len(rows)}"
        )
    pixels: list[tuple[int, int]] = []
    for r, row in enumerate(rows):
        if len(row) != COLS or any(c not in ".#" for c in row):
            raise SystemExit(
                f"glyph {gname!r}: bad bitmap row {r} {row!r} "
                f"(need exactly {COLS} chars of '.' or '#')"
            )
        y = _row_to_y(r)
        for c, ch in enumerate(row):
            if ch == "#":
                pixels.append((c * PIXEL, y))
    return pixels


def parse_bitmap(path: Path | str) -> dict:
    text = Path(path).read_text(encoding="utf-8")

    metrics_raw: dict[str, str] = {}
    missing: dict | None = None
    glyphs: list[dict] = []

    section: str | None = None
    cur_name: str | None = None
    cur_kv: dict[str, str] = {}
    cur_rows: list[str] = []

    def flush() -> None:
        nonlocal section, cur_name, missing
        if section == "meta":
            metrics_raw.update(cur_kv)
        elif section == "glyph":
            assert cur_name is not None
            pixels = _bitmap_to_pixels(cur_rows, cur_name)
            default_adv = int(metrics_raw.get("default-adv", "750"))
            adv = int(cur_kv.get("adv", default_adv))
            uni = cur_kv.get("unicode")

            if cur_name == ".notdef":
                missing = dict(adv=adv, pixels=pixels)
            else:
                if uni is None:
                    raise SystemExit(f"glyph {cur_name!r}: missing 'unicode:' field")
                m = _UNICODE.match(uni)
                if not m:
                    raise SystemExit(f"glyph {cur_name!r}: bad unicode {uni!r}")
                cp = int(m.group(1), 16)
                glyphs.append(dict(
                    char=chr(cp),
                    name=cur_name,
                    adv=adv,
                    pixels=pixels,
                ))
        cur_kv.clear()
        cur_rows.clear()
        section = None
        cur_name = None

    for raw in text.splitlines():
        line = _strip_comment(raw)
        if not line:
            continue

        m = _HEADING.match(line)
        if m:
            flush()
            section = m.group(1)
            cur_name = m.group(2)
            if section == "glyph" and not cur_name:
                raise SystemExit(f"@glyph heading missing name: {raw!r}")
            continue

        if section is None:
            raise SystemExit(f"content before any @section: {raw!r}")

        # A bitmap row is exactly COLS chars of '.' or '#'.
        if len(line) == COLS and all(c in ".#" for c in line):
            if section != "glyph":
                raise SystemExit(f"bitmap row outside @glyph: {raw!r}")
            cur_rows.append(line)
            continue

        kv = _KV.match(line)
        if kv:
            cur_kv[kv.group(1)] = kv.group(2)
            continue

        raise SystemExit(f"unparseable line: {raw!r}")

    flush()

    metrics = dict(
        upem=int(metrics_raw["upem"]),
        ascent=int(metrics_raw["ascent"]),
        descent=int(metrics_raw["descent"]),
        cap_height=int(metrics_raw["cap-height"]),
        x_height=int(metrics_raw["x-height"]),
        underline_position=int(metrics_raw["underline-position"]),
        underline_thickness=int(metrics_raw["underline-thickness"]),
        default_adv=int(metrics_raw["default-adv"]),
        panose=metrics_raw.get("panose", "2 0 5 9 0 0 0 0 0 0"),
    )

    return dict(metrics=metrics, missing=missing, glyphs=glyphs)


if __name__ == "__main__":
    import sys
    src = Path(sys.argv[1] if len(sys.argv) > 1 else "sources/glyphs.txt")
    data = parse_bitmap(src)
    m = data["metrics"]
    print(
        f"parsed {len(data['glyphs'])} glyphs from {src} "
        f"(upem={m['upem']}, ascent={m['ascent']}, descent={m['descent']})"
    )
    if data["missing"]:
        print(f"missing-glyph: {len(data['missing']['pixels'])} pixels")
