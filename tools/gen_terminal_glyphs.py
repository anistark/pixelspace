#!/usr/bin/env python3
"""Scaffold: generate U+2500-257F (Box Drawing) and U+2580-259F
(Block Elements) glyph entries and append them to sources/glyphs.txt.

This is a one-shot tool. Once the output is in glyphs.txt, that file is the
source of truth — hand-edit individual glyphs there, don't rerun this
script (or only rerun if you also delete the existing entries first).

Design rules (5×7 grid, gappy-pixel aesthetic):

  Orthogonal box-drawing: each glyph has weights for the 4 cardinal
    directions (up/down/left/right), each in {NONE, LIGHT, HEAVY, DOUBLE}.
      LIGHT vert  → col 2          LIGHT horiz → row 3
      HEAVY vert  → cols 1, 2      HEAVY horiz → rows 2, 3
      DOUBLE vert → cols 1, 3      DOUBLE horiz → rows 2, 4

    Each arm extends from the boundary to the centre (col 2, row 3) so
    arms meet naturally. Mixed weights overlap as a union — the result is
    pragmatic on a 5×7 grid; some double-line corners look approximate
    rather than truly parallel.

  Dashed: U+2504/2505 (triple horiz) → cols 0, 2, 4 ; U+2506/2507 (triple
    vert) → rows 0, 3, 6. U+2508-250B (quadruple) → close to triple on a
    5-col grid; quadruple vertical uses rows 0, 2, 4, 6.

  Arcs (U+256D-2570): rendered identical to the corresponding light
    corner. The pixel-corner radius already implies softness.

  Half-segments (U+2574-257F): left/up/right/down half of the centre line,
    in light or heavy. Mixed-weight halves (U+257C-257F) draw two halves
    of different weights meeting at the centre.

  Diagonals (U+2571-2573): hand-coded near-diagonal stair-steps.

  Block elements (U+2580-259F): straight algorithmic fill regions. Half-
    blocks split the cell at row 3.5 (4 rows top half / 4 rows bottom
    half — slight overlap at row 3, invisible at the gappy aesthetic).
    Eighths-blocks scale 1/8…7/8 to the nearest of 1, 2, 3, 4, 5, 6, 7
    rows or columns. Shade blocks (░ ▒ ▓) use scattered-pixel patterns
    at increasing density.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GLYPHS_TXT = ROOT / "sources" / "glyphs.txt"

ROWS = 7
COLS = 5
NONE, LIGHT, HEAVY, DOUBLE = 0, 1, 2, 3


# ---------- bitmap helpers ----------

def empty_grid():
    return [["."] * COLS for _ in range(ROWS)]


def grid_to_lines(grid):
    return ["".join(row) for row in grid]


def fill(grid, rows, cols):
    for r in rows:
        for c in cols:
            if 0 <= r < ROWS and 0 <= c < COLS:
                grid[r][c] = "#"


def vert_cols(weight):
    if weight == LIGHT:
        return [2]
    if weight == HEAVY:
        return [1, 2]
    if weight == DOUBLE:
        return [1, 3]
    return []


def horiz_rows(weight):
    if weight == LIGHT:
        return [3]
    if weight == HEAVY:
        return [2, 3]
    if weight == DOUBLE:
        return [2, 4]
    return []


# ---------- orthogonal box-drawing ----------

def render_orthogonal(u, d, l, r):
    """Render an orthogonal box-drawing glyph with arm weights (u, d, l, r)."""
    grid = empty_grid()
    if u:
        fill(grid, range(0, 4), vert_cols(u))     # up arm rows 0..3
    if d:
        fill(grid, range(3, 7), vert_cols(d))     # down arm rows 3..6
    if l:
        fill(grid, horiz_rows(l), range(0, 3))    # left arm cols 0..2
    if r:
        fill(grid, horiz_rows(r), range(2, 5))    # right arm cols 2..4
    return grid_to_lines(grid)


# Weights for every "orthogonal" box-drawing codepoint in U+2500-256C, by
# (up, down, left, right). Compiled from the official Unicode names in the
# U+2500 block.

ORTHOGONAL_SPECS = {
    0x2500: (0, 0, LIGHT, LIGHT),
    0x2501: (0, 0, HEAVY, HEAVY),
    0x2502: (LIGHT, LIGHT, 0, 0),
    0x2503: (HEAVY, HEAVY, 0, 0),

    # Down + Right corners
    0x250C: (0, LIGHT, 0, LIGHT),
    0x250D: (0, LIGHT, 0, HEAVY),
    0x250E: (0, HEAVY, 0, LIGHT),
    0x250F: (0, HEAVY, 0, HEAVY),

    # Down + Left corners
    0x2510: (0, LIGHT, LIGHT, 0),
    0x2511: (0, LIGHT, HEAVY, 0),
    0x2512: (0, HEAVY, LIGHT, 0),
    0x2513: (0, HEAVY, HEAVY, 0),

    # Up + Right corners
    0x2514: (LIGHT, 0, 0, LIGHT),
    0x2515: (LIGHT, 0, 0, HEAVY),
    0x2516: (HEAVY, 0, 0, LIGHT),
    0x2517: (HEAVY, 0, 0, HEAVY),

    # Up + Left corners
    0x2518: (LIGHT, 0, LIGHT, 0),
    0x2519: (LIGHT, 0, HEAVY, 0),
    0x251A: (HEAVY, 0, LIGHT, 0),
    0x251B: (HEAVY, 0, HEAVY, 0),

    # Vertical + Right (├ family)
    0x251C: (LIGHT, LIGHT, 0, LIGHT),
    0x251D: (LIGHT, LIGHT, 0, HEAVY),
    0x251E: (HEAVY, LIGHT, 0, LIGHT),
    0x251F: (LIGHT, HEAVY, 0, LIGHT),
    0x2520: (HEAVY, HEAVY, 0, LIGHT),
    0x2521: (HEAVY, LIGHT, 0, HEAVY),
    0x2522: (LIGHT, HEAVY, 0, HEAVY),
    0x2523: (HEAVY, HEAVY, 0, HEAVY),

    # Vertical + Left (┤ family)
    0x2524: (LIGHT, LIGHT, LIGHT, 0),
    0x2525: (LIGHT, LIGHT, HEAVY, 0),
    0x2526: (HEAVY, LIGHT, LIGHT, 0),
    0x2527: (LIGHT, HEAVY, LIGHT, 0),
    0x2528: (HEAVY, HEAVY, LIGHT, 0),
    0x2529: (HEAVY, LIGHT, HEAVY, 0),
    0x252A: (LIGHT, HEAVY, HEAVY, 0),
    0x252B: (HEAVY, HEAVY, HEAVY, 0),

    # Down + Horizontal (┬ family)
    0x252C: (0, LIGHT, LIGHT, LIGHT),
    0x252D: (0, LIGHT, HEAVY, LIGHT),
    0x252E: (0, LIGHT, LIGHT, HEAVY),
    0x252F: (0, LIGHT, HEAVY, HEAVY),
    0x2530: (0, HEAVY, LIGHT, LIGHT),
    0x2531: (0, HEAVY, HEAVY, LIGHT),
    0x2532: (0, HEAVY, LIGHT, HEAVY),
    0x2533: (0, HEAVY, HEAVY, HEAVY),

    # Up + Horizontal (┴ family)
    0x2534: (LIGHT, 0, LIGHT, LIGHT),
    0x2535: (LIGHT, 0, HEAVY, LIGHT),
    0x2536: (LIGHT, 0, LIGHT, HEAVY),
    0x2537: (LIGHT, 0, HEAVY, HEAVY),
    0x2538: (HEAVY, 0, LIGHT, LIGHT),
    0x2539: (HEAVY, 0, HEAVY, LIGHT),
    0x253A: (HEAVY, 0, LIGHT, HEAVY),
    0x253B: (HEAVY, 0, HEAVY, HEAVY),

    # Cross (┼ family)
    0x253C: (LIGHT, LIGHT, LIGHT, LIGHT),
    0x253D: (LIGHT, LIGHT, HEAVY, LIGHT),
    0x253E: (LIGHT, LIGHT, LIGHT, HEAVY),
    0x253F: (LIGHT, LIGHT, HEAVY, HEAVY),
    0x2540: (HEAVY, LIGHT, LIGHT, LIGHT),
    0x2541: (LIGHT, HEAVY, LIGHT, LIGHT),
    0x2542: (HEAVY, HEAVY, LIGHT, LIGHT),
    0x2543: (HEAVY, LIGHT, HEAVY, LIGHT),
    0x2544: (HEAVY, LIGHT, LIGHT, HEAVY),
    0x2545: (LIGHT, HEAVY, HEAVY, LIGHT),
    0x2546: (LIGHT, HEAVY, LIGHT, HEAVY),
    0x2547: (HEAVY, LIGHT, HEAVY, HEAVY),
    0x2548: (LIGHT, HEAVY, HEAVY, HEAVY),
    0x2549: (HEAVY, HEAVY, HEAVY, LIGHT),
    0x254A: (HEAVY, HEAVY, LIGHT, HEAVY),
    0x254B: (HEAVY, HEAVY, HEAVY, HEAVY),

    # Double-line horizontals/verticals
    0x2550: (0, 0, DOUBLE, DOUBLE),
    0x2551: (DOUBLE, DOUBLE, 0, 0),

    # Down + Right (mixed light/double)
    0x2552: (0, LIGHT, 0, DOUBLE),
    0x2553: (0, DOUBLE, 0, LIGHT),
    0x2554: (0, DOUBLE, 0, DOUBLE),

    # Down + Left
    0x2555: (0, LIGHT, DOUBLE, 0),
    0x2556: (0, DOUBLE, LIGHT, 0),
    0x2557: (0, DOUBLE, DOUBLE, 0),

    # Up + Right
    0x2558: (LIGHT, 0, 0, DOUBLE),
    0x2559: (DOUBLE, 0, 0, LIGHT),
    0x255A: (DOUBLE, 0, 0, DOUBLE),

    # Up + Left
    0x255B: (LIGHT, 0, DOUBLE, 0),
    0x255C: (DOUBLE, 0, LIGHT, 0),
    0x255D: (DOUBLE, 0, DOUBLE, 0),

    # Vertical + Right
    0x255E: (LIGHT, LIGHT, 0, DOUBLE),
    0x255F: (DOUBLE, DOUBLE, 0, LIGHT),
    0x2560: (DOUBLE, DOUBLE, 0, DOUBLE),

    # Vertical + Left
    0x2561: (LIGHT, LIGHT, DOUBLE, 0),
    0x2562: (DOUBLE, DOUBLE, LIGHT, 0),
    0x2563: (DOUBLE, DOUBLE, DOUBLE, 0),

    # Down + Horizontal
    0x2564: (0, LIGHT, DOUBLE, DOUBLE),
    0x2565: (0, DOUBLE, LIGHT, LIGHT),
    0x2566: (0, DOUBLE, DOUBLE, DOUBLE),

    # Up + Horizontal
    0x2567: (LIGHT, 0, DOUBLE, DOUBLE),
    0x2568: (DOUBLE, 0, LIGHT, LIGHT),
    0x2569: (DOUBLE, 0, DOUBLE, DOUBLE),

    # Cross (double variants)
    0x256A: (LIGHT, LIGHT, DOUBLE, DOUBLE),
    0x256B: (DOUBLE, DOUBLE, LIGHT, LIGHT),
    0x256C: (DOUBLE, DOUBLE, DOUBLE, DOUBLE),
}


# Arc corners — same bitmap as light right-angle corners. The rounded-pixel
# style implies softness without needing a different shape.
ARCS = {
    0x256D: 0x250C,   # ╭ → ┌
    0x256E: 0x2510,   # ╮ → ┐
    0x256F: 0x2518,   # ╯ → ┘
    0x2570: 0x2514,   # ╰ → └
}


# ---------- diagonals ----------

def render_diag_forward():
    """╱ — diagonal from lower-left to upper-right (looks like /)."""
    grid = empty_grid()
    fill(grid, [6], [0])
    fill(grid, [5], [0])
    fill(grid, [4], [1])
    fill(grid, [3], [2])
    fill(grid, [2], [3])
    fill(grid, [1], [4])
    fill(grid, [0], [4])
    return grid_to_lines(grid)


def render_diag_back():
    """╲ — diagonal from upper-left to lower-right (looks like \\)."""
    grid = empty_grid()
    fill(grid, [0], [0])
    fill(grid, [1], [0])
    fill(grid, [2], [1])
    fill(grid, [3], [2])
    fill(grid, [4], [3])
    fill(grid, [5], [4])
    fill(grid, [6], [4])
    return grid_to_lines(grid)


def render_diag_cross():
    """╳ — both diagonals."""
    grid = empty_grid()
    for r, c in zip(range(0, 7), [0, 0, 1, 2, 3, 4, 4]):
        grid[r][c] = "#"
    for r, c in zip(range(0, 7), [4, 4, 3, 2, 1, 0, 0]):
        grid[r][c] = "#"
    return grid_to_lines(grid)


DIAGONALS = {
    0x2571: render_diag_forward,
    0x2572: render_diag_back,
    0x2573: render_diag_cross,
}


# ---------- dashed ----------

def render_dash_h(n_dashes, weight):
    """Horizontal dashed line. n_dashes is the design intent (3 or 4); on a
    5-column grid 4-dash is approximated as 3-dash with one wider segment."""
    grid = empty_grid()
    rows = horiz_rows(weight)
    if n_dashes == 3:
        cols = [0, 2, 4]
    else:                       # quadruple — best approximation on 5 cols
        cols = [0, 1, 3, 4]
    for r in rows:
        for c in cols:
            grid[r][c] = "#"
    return grid_to_lines(grid)


def render_dash_v(n_dashes, weight):
    grid = empty_grid()
    cols = vert_cols(weight)
    if n_dashes == 3:
        rows = [0, 3, 6]
    else:
        rows = [0, 2, 4, 6]
    for c in cols:
        for r in rows:
            grid[r][c] = "#"
    return grid_to_lines(grid)


DASHED = {
    0x2504: lambda: render_dash_h(3, LIGHT),
    0x2505: lambda: render_dash_h(3, HEAVY),
    0x2506: lambda: render_dash_v(3, LIGHT),
    0x2507: lambda: render_dash_v(3, HEAVY),
    0x2508: lambda: render_dash_h(4, LIGHT),
    0x2509: lambda: render_dash_h(4, HEAVY),
    0x250A: lambda: render_dash_v(4, LIGHT),
    0x250B: lambda: render_dash_v(4, HEAVY),
}


# ---------- half-segments ----------
# U+2574 ╴ light left, U+2575 ╵ light up, U+2576 ╶ light right, U+2577 ╷ light down
# U+2578 ╸ heavy left, ...
# U+257C ╼ light left + heavy right (mixed)
# U+257D ╽ light up + heavy down
# U+257E ╾ heavy left + light right
# U+257F ╿ heavy up + light down

HALF_SEGMENTS = {
    0x2574: (0, 0, LIGHT, 0),
    0x2575: (LIGHT, 0, 0, 0),
    0x2576: (0, 0, 0, LIGHT),
    0x2577: (0, LIGHT, 0, 0),
    0x2578: (0, 0, HEAVY, 0),
    0x2579: (HEAVY, 0, 0, 0),
    0x257A: (0, 0, 0, HEAVY),
    0x257B: (0, HEAVY, 0, 0),
    0x257C: (0, 0, LIGHT, HEAVY),
    0x257D: (LIGHT, HEAVY, 0, 0),
    0x257E: (0, 0, HEAVY, LIGHT),
    0x257F: (HEAVY, LIGHT, 0, 0),
}


# ---------- block elements (U+2580-259F) ----------

def render_block(rows_on, cols_on):
    """Block with the given rows/columns turned on. Either or both can be
    full ranges — the on-set is the cartesian product."""
    grid = empty_grid()
    for r in rows_on:
        for c in cols_on:
            grid[r][c] = "#"
    return grid_to_lines(grid)


def render_quadrants(*on):
    """Render block from a set of named quadrants in {ul, ur, ll, lr}.
    Quadrant boundary: row 3 (top half rows 0-3, bottom half rows 4-6),
    col 2 (left half cols 0-1, right half cols 2-4)."""
    # Slight asymmetry on a 5×7 grid — accept it.
    quads = {
        "ul": (range(0, 4), range(0, 2)),
        "ur": (range(0, 4), range(2, 5)),
        "ll": (range(4, 7), range(0, 2)),
        "lr": (range(4, 7), range(2, 5)),
    }
    grid = empty_grid()
    for q in on:
        rows, cols = quads[q]
        for r in rows:
            for c in cols:
                grid[r][c] = "#"
    return grid_to_lines(grid)


def render_shade(density):
    """Density in {1, 2, 3} for ░ ▒ ▓ — scattered-pixel patterns."""
    grid = empty_grid()
    if density == 1:        # ░ ~25%
        ons = {(r, c) for r in range(ROWS) for c in range(COLS)
               if (r + 2 * c) % 4 == 0}
    elif density == 2:      # ▒ ~50% checkerboard
        ons = {(r, c) for r in range(ROWS) for c in range(COLS)
               if (r + c) % 2 == 0}
    else:                    # ▓ ~75% inverse of ░
        all_cells = {(r, c) for r in range(ROWS) for c in range(COLS)}
        light = {(r, c) for r in range(ROWS) for c in range(COLS)
                 if (r + 2 * c) % 4 == 0}
        ons = all_cells - light
    for r, c in ons:
        grid[r][c] = "#"
    return grid_to_lines(grid)


BLOCKS = {
    # Lower-N-eighths bars (▁ … █) and upper half (▀)
    0x2580: lambda: render_block(range(0, 4), range(COLS)),     # ▀ upper half
    0x2581: lambda: render_block([6], range(COLS)),              # ▁ lower 1/8
    0x2582: lambda: render_block(range(5, 7), range(COLS)),      # ▂ lower 2/8
    0x2583: lambda: render_block(range(4, 7), range(COLS)),      # ▃ lower 3/8
    0x2584: lambda: render_block(range(3, 7), range(COLS)),      # ▄ lower half
    0x2585: lambda: render_block(range(3, 7), range(COLS)),      # ▅ ≈ ▄ on 7-row grid
    0x2586: lambda: render_block(range(2, 7), range(COLS)),      # ▆ lower 6/8
    0x2587: lambda: render_block(range(1, 7), range(COLS)),      # ▇ lower 7/8
    0x2588: lambda: render_block(range(ROWS), range(COLS)),      # █ full block

    # Left-N-eighths bars (▏ … ▉) and right half (▐)
    0x2589: lambda: render_block(range(ROWS), range(0, 4)),      # ▉ left 7/8
    0x258A: lambda: render_block(range(ROWS), range(0, 4)),      # ▊ ≈ ▉ on 5-col
    0x258B: lambda: render_block(range(ROWS), range(0, 3)),      # ▋ left 5/8
    0x258C: lambda: render_block(range(ROWS), range(0, 3)),      # ▌ left half (0..2)
    0x258D: lambda: render_block(range(ROWS), range(0, 2)),      # ▍ left 3/8
    0x258E: lambda: render_block(range(ROWS), range(0, 2)),      # ▎ left 2/8
    0x258F: lambda: render_block(range(ROWS), [0]),               # ▏ left 1/8
    0x2590: lambda: render_block(range(ROWS), range(2, 5)),      # ▐ right half

    # Shades
    0x2591: lambda: render_shade(1),                               # ░
    0x2592: lambda: render_shade(2),                               # ▒
    0x2593: lambda: render_shade(3),                               # ▓

    # Top/right 1/8
    0x2594: lambda: render_block([0], range(COLS)),                # ▔ upper 1/8
    0x2595: lambda: render_block(range(ROWS), [4]),                 # ▕ right 1/8

    # Single quadrants
    0x2596: lambda: render_quadrants("ll"),                          # ▖ lower-left
    0x2597: lambda: render_quadrants("lr"),                          # ▗ lower-right
    0x2598: lambda: render_quadrants("ul"),                          # ▘ upper-left
    0x259D: lambda: render_quadrants("ur"),                          # ▝ upper-right

    # Three / two-quadrant combinations
    0x2599: lambda: render_quadrants("ul", "ll", "lr"),              # ▙
    0x259A: lambda: render_quadrants("ul", "lr"),                    # ▚
    0x259B: lambda: render_quadrants("ul", "ur", "ll"),              # ▛
    0x259C: lambda: render_quadrants("ul", "ur", "lr"),              # ▜
    0x259E: lambda: render_quadrants("ur", "ll"),                    # ▞
    0x259F: lambda: render_quadrants("ur", "ll", "lr"),              # ▟
}


# ---------- emit ----------

def render(cp: int) -> list[str] | None:
    if cp in ORTHOGONAL_SPECS:
        return render_orthogonal(*ORTHOGONAL_SPECS[cp])
    if cp in ARCS:
        return render_orthogonal(*ORTHOGONAL_SPECS[ARCS[cp]])
    if cp in DASHED:
        return DASHED[cp]()
    if cp in HALF_SEGMENTS:
        return render_orthogonal(*HALF_SEGMENTS[cp])
    if cp in DIAGONALS:
        return DIAGONALS[cp]()
    if cp in BLOCKS:
        return BLOCKS[cp]()
    return None


def emit_glyph(cp: int, lines: list[str]) -> str:
    out = []
    out.append(f"@glyph uni{cp:04X}")
    out.append(f"unicode: U+{cp:04X}")
    out.extend(lines)
    return "\n".join(out)


def existing_codepoints() -> set[int]:
    text = GLYPHS_TXT.read_text(encoding="utf-8")
    cps: set[int] = set()
    for m in re.finditer(r"^unicode:\s*U\+([0-9A-Fa-f]+)", text, re.MULTILINE):
        cps.add(int(m.group(1), 16))
    return cps


def main() -> int:
    have = existing_codepoints()
    sections: list[tuple[str, range, str]] = [
        ("U+2500-2503: light & heavy lines", range(0x2500, 0x2504),
         "Light & heavy horizontal/vertical."),
        ("U+2504-250B: dashed lines", range(0x2504, 0x250C),
         "Triple/quadruple dashed (collapsed on 5-col grid)."),
        ("U+250C-251B: corners", range(0x250C, 0x251C),
         "All four corners with light/heavy/mixed weights."),
        ("U+251C-252B: T-junctions left/right", range(0x251C, 0x252C),
         "Vertical lines with horizontal arm — light/heavy/mixed."),
        ("U+252C-253B: T-junctions up/down", range(0x252C, 0x253C),
         "Horizontal lines with vertical arm — light/heavy/mixed."),
        ("U+253C-254B: crosses", range(0x253C, 0x254C),
         "Cross junctions with light/heavy/mixed arms."),
        ("U+254C-254F: dashed double-line (skipped — out of scope for v1.100)",
         range(0x254C, 0x2550), ""),
        ("U+2550-256C: double-line forms", range(0x2550, 0x256D),
         "Double-line straights, corners, T-junctions, crosses."),
        ("U+256D-2570: arc corners", range(0x256D, 0x2571),
         "Rounded corners — pixel rounding already implies softness."),
        ("U+2571-2573: diagonals", range(0x2571, 0x2574),
         "Forward / back / cross diagonals — stair-step approximations."),
        ("U+2574-257B: half-segments", range(0x2574, 0x257C),
         "Single-direction half-lines, light & heavy."),
        ("U+257C-257F: mixed-weight half-segments", range(0x257C, 0x2580),
         "Light-meets-heavy half-segments at the centre."),
        ("U+2580-259F: block elements", range(0x2580, 0x25A0),
         "Half-blocks, eighths-blocks, quadrants, shades."),
    ]

    chunks: list[str] = []
    chunks.append("")
    chunks.append("; ===========================================================")
    chunks.append("; Box-drawing (U+2500-257F) and Block Elements (U+2580-259F)")
    chunks.append("; Generated by tools/gen_terminal_glyphs.py — see header for")
    chunks.append("; design rules. Hand-edits welcome going forward.")
    chunks.append("; ===========================================================")
    chunks.append("")

    written = 0
    skipped: list[int] = []
    for label, cps, blurb in sections:
        chunks.append(f"; {label}")
        if blurb:
            chunks.append(f"; {blurb}")
        chunks.append("")
        for cp in cps:
            if cp in have:
                skipped.append(cp)
                continue
            bitmap = render(cp)
            if bitmap is None:
                continue
            chunks.append(emit_glyph(cp, bitmap))
            chunks.append("")
            written += 1

    out = GLYPHS_TXT.read_text(encoding="utf-8").rstrip() + "\n"
    out += "\n".join(chunks).rstrip() + "\n"
    GLYPHS_TXT.write_text(out, encoding="utf-8")
    print(f"appended {written} glyphs to {GLYPHS_TXT.relative_to(ROOT)}")
    if skipped:
        print(f"skipped {len(skipped)} already-present codepoints: "
              f"{', '.join(f'U+{cp:04X}' for cp in skipped)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
