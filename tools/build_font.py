#!/usr/bin/env python3
"""Build Pixelspace TTF/OTF/WOFF2 from the SVG font in sources/Pixelspace.svg.

The SVG font is the canonical source: it stores each glyph as a sequence of
125x125 unit pixel rectangles inside an 875-unit em. This script parses the
`<font-face>` metrics plus every `<glyph>` (and `<missing-glyph>`) path, then
emits binary fonts via fontTools.

Path pixels are encoded as `M X,Y h125 v-125 h-125 Z` — one `M` per pixel,
where `(X, Y)` is the top-left corner in SVG-font (y-up) coordinates. The
baseline sits at y=0; rows 0-4 are above it (cap height 625), rows 5-6
descend below (descent 250).
"""
from __future__ import annotations

import base64
import re
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.ttLib import newTable

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources" / "Pixelspace.svg"
FONT_DIR = ROOT / "fonts"
DOCS_DIR = ROOT / "docs"

FAMILY = "Pixelspace"
STYLE = "Regular"
VERSION = "1.001"
COPYRIGHT = "Copyright 2026 The Pixelspace Project Authors (https://github.com/anistark/pixelspace)"
MANUFACTURER = "Kumar Anirudha"
DESIGNER = "Kumar Anirudha"
DESIGNER_URL = "https://github.com/anistark"
VENDOR_ID = "KANS"
LICENSE_URL = "https://openfontlicense.org"
LICENSE_NAME = (
    "This Font Software is licensed under the SIL Open Font License, "
    "Version 1.1. This license is available with a FAQ at: "
    "https://openfontlicense.org"
)

PIXEL = 125          # one pixel cell, in font units — set from SVG for cross-checks
PIXEL_GAP = 15       # font units of empty space between adjacent on-pixels
PIXEL_RADIUS_PCT = 0.10   # corner radius as fraction of the inner pixel size
PIXEL_RE = re.compile(r"M\s*(-?\d+)\s*,\s*(-?\d+)")

# Derived: inner square drawn at the top-left corner of the 125-unit cell.
# Using inner=124 and offset=0 means the right/bottom sides leave a 1-unit
# gap to the next cell's boundary; adjacent on-pixels end up exactly
# PIXEL_GAP apart in both axes.
_INNER = PIXEL - PIXEL_GAP
_R = max(0, int(round(_INNER * PIXEL_RADIUS_PCT)))


# ---------- SVG parsing ----------

def _strip_ns(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_svg_font(path: Path) -> dict:
    """Return {metrics, missing_glyph, glyphs: [{unicode, adv, pixels}...]}."""
    tree = ET.parse(path)
    root = tree.getroot()

    font_el = None
    for el in root.iter():
        if _strip_ns(el.tag) == "font":
            font_el = el
            break
    if font_el is None:
        raise SystemExit(f"No <font> element in {path}")

    face_el = None
    missing_el = None
    glyph_els: list[ET.Element] = []
    for el in font_el:
        tag = _strip_ns(el.tag)
        if tag == "font-face":
            face_el = el
        elif tag == "missing-glyph":
            missing_el = el
        elif tag == "glyph":
            glyph_els.append(el)

    if face_el is None:
        raise SystemExit("No <font-face> in SVG font")

    def f(name: str, default: float | None = None) -> float:
        v = face_el.get(name)
        if v is None:
            if default is None:
                raise SystemExit(f"<font-face> missing {name}")
            return default
        return float(v)

    metrics = dict(
        upem=int(f("units-per-em")),
        ascent=int(f("ascent")),
        descent=int(f("descent")),          # negative in SVG convention
        cap_height=int(f("cap-height")),
        x_height=int(f("x-height")),
        underline_position=int(f("underline-position", -PIXEL * 3 // 2)),
        underline_thickness=int(f("underline-thickness", PIXEL)),
        default_adv=int(float(font_el.get("horiz-adv-x", 750))),
        panose=face_el.get("panose-1", "2 0 5 9 0 0 0 0 0 0"),
    )

    missing = None
    if missing_el is not None:
        missing = dict(
            adv=int(float(missing_el.get("horiz-adv-x", metrics["default_adv"]))),
            pixels=[(int(x), int(y)) for x, y in PIXEL_RE.findall(missing_el.get("d", ""))],
        )

    glyphs = []
    for g in glyph_els:
        uni_attr = g.get("unicode")
        if uni_attr is None or len(uni_attr) != 1:
            # We only ship single-codepoint glyphs; skip anything exotic.
            continue
        glyphs.append(dict(
            char=uni_attr,
            name=g.get("glyph-name") or f"uni{ord(uni_attr):04X}",
            adv=int(float(g.get("horiz-adv-x", metrics["default_adv"]))),
            pixels=[(int(x), int(y)) for x, y in PIXEL_RE.findall(g.get("d", ""))],
        ))

    return dict(metrics=metrics, missing=missing, glyphs=glyphs)


# ---------- Glyph drawing ----------
#
# Each on-pixel in the SVG has its TOP-LEFT corner at (x, y) in y-up font
# coordinates. We draw an INNER rounded square of side _INNER (= PIXEL -
# PIXEL_GAP) anchored at (x, y), so adjacent on-pixels leave exactly
# PIXEL_GAP units of background between them and each rect has rounded
# corners of radius _R. TrueType outer contours wind CLOCKWISE in y-up;
# CFF winds COUNTER-CLOCKWISE.

def draw_pixel_tt(pen, x: int, y: int) -> None:
    w, r = _INNER, _R
    if r <= 0:
        pen.moveTo((x, y))
        pen.lineTo((x + w, y))
        pen.lineTo((x + w, y - w))
        pen.lineTo((x, y - w))
        pen.closePath()
        return
    pen.moveTo((x + r, y))
    pen.lineTo((x + w - r, y))
    pen.qCurveTo((x + w, y), (x + w, y - r))          # top-right
    pen.lineTo((x + w, y - w + r))
    pen.qCurveTo((x + w, y - w), (x + w - r, y - w))  # bottom-right
    pen.lineTo((x + r, y - w))
    pen.qCurveTo((x, y - w), (x, y - w + r))          # bottom-left
    pen.lineTo((x, y - r))
    pen.qCurveTo((x, y), (x + r, y))                  # top-left
    pen.closePath()


def draw_pixel_cff(pen, x: int, y: int) -> None:
    w, r = _INNER, _R
    if r <= 0:
        pen.moveTo((x, y))
        pen.lineTo((x, y - w))
        pen.lineTo((x + w, y - w))
        pen.lineTo((x + w, y))
        pen.closePath()
        return
    pen.moveTo((x + r, y))
    pen.qCurveTo((x, y), (x, y - r))                  # top-left
    pen.lineTo((x, y - w + r))
    pen.qCurveTo((x, y - w), (x + r, y - w))          # bottom-left
    pen.lineTo((x + w - r, y - w))
    pen.qCurveTo((x + w, y - w), (x + w, y - w + r))  # bottom-right
    pen.lineTo((x + w, y - r))
    pen.qCurveTo((x + w, y), (x + w - r, y))          # top-right
    pen.closePath()


def draw_glyph_tt(pixels: list[tuple[int, int]]):
    pen = TTGlyphPen(None)
    for x, y in pixels:
        draw_pixel_tt(pen, x, y)
    return pen.glyph()


def draw_glyph_cff(pixels: list[tuple[int, int]], adv: int):
    pen = T2CharStringPen(adv, None)
    for x, y in pixels:
        draw_pixel_cff(pen, x, y)
    return pen.getCharString()


# ---------- Glyph names ----------
#
# fontTools accepts any unique non-empty identifiers, but shipping conventional
# Adobe-style post-table names keeps downstream tools (and Font Bakery) happy.

_ADOBE_NAMES = {
    " ": "space", "!": "exclam", '"': "quotedbl", "#": "numbersign",
    "$": "dollar", "%": "percent", "&": "ampersand", "'": "quotesingle",
    "(": "parenleft", ")": "parenright", "*": "asterisk", "+": "plus",
    ",": "comma", "-": "hyphen", ".": "period", "/": "slash",
    "0": "zero", "1": "one", "2": "two", "3": "three", "4": "four",
    "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "nine",
    ":": "colon", ";": "semicolon", "<": "less", "=": "equal",
    ">": "greater", "?": "question", "@": "at",
    "[": "bracketleft", "\\": "backslash", "]": "bracketright",
    "^": "asciicircum", "_": "underscore", "`": "grave",
    "{": "braceleft", "|": "bar", "}": "braceright", "~": "asciitilde",
}


def glyph_name_for(char: str) -> str:
    if char in _ADOBE_NAMES:
        return _ADOBE_NAMES[char]
    if char.isalpha() and char.isascii():
        return char
    return f"uni{ord(char):04X}"


# ---------- Build ----------

def build(data: dict) -> None:
    FONT_DIR.mkdir(parents=True, exist_ok=True)

    metrics = data["metrics"]
    upem = metrics["upem"]
    ink_ascent = metrics["ascent"]        # 625: top of caps
    ink_descent = metrics["descent"]      # -250: bottom of descenders
    cap_height = metrics["cap_height"]
    x_height = metrics["x_height"]
    underline_pos = metrics["underline_position"]
    underline_thk = metrics["underline_thickness"]
    default_adv = metrics["default_adv"]
    # Google Fonts requires lineGap = 0 AND ascender + |descender| + lineGap
    # to sit between 120% and 150% of UPM. The design's ink extent is only
    # 100% (625 + 250 = 875 = UPM), so we pad the ascender with 375 units of
    # blank space above the caps — equivalent to our old `line_gap = 375`,
    # just relocated from hhea.lineGap into hhea.ascender so GF is happy.
    # Total: 1000 + 250 + 0 = 1250 = 143% of UPM. cap_height/x_height stay
    # at their ink values so clients that honour them still see the design.
    ascent = 1000
    descent = -250
    line_gap = 0
    panose_values = [int(v) for v in metrics["panose"].split()]
    panose_values = (panose_values + [0] * 10)[:10]

    # Ordered glyph list: .notdef first, then space, then the rest by codepoint.
    glyph_recs = sorted(data["glyphs"], key=lambda g: ord(g["char"]))
    space = next((g for g in glyph_recs if g["char"] == " "), None)
    if space is not None:
        glyph_recs.remove(space)
        glyph_recs.insert(0, space)

    for g in glyph_recs:
        g["gname"] = glyph_name_for(g["char"])

    glyph_order = [".notdef"] + [g["gname"] for g in glyph_recs]
    # Dedupe defensively.
    seen: set[str] = set()
    glyph_order = [n for n in glyph_order if not (n in seen or seen.add(n))]

    cmap = {ord(g["char"]): g["gname"] for g in glyph_recs}
    # NBSP (U+00A0) aliases to the same glyph as U+0020 — required by Google
    # Fonts and expected by most layout engines.
    if 0x20 in cmap:
        cmap.setdefault(0x00A0, cmap[0x20])
    hmtx = {g["gname"]: (g["adv"], 0) for g in glyph_recs}

    missing = data["missing"]
    missing_pixels = missing["pixels"] if missing else []
    missing_adv = missing["adv"] if missing else default_adv
    hmtx[".notdef"] = (missing_adv, 0)

    # ---- TrueType (.ttf) ----
    fb_tt = FontBuilder(upem, isTTF=True)
    fb_tt.setupGlyphOrder(glyph_order)
    fb_tt.setupCharacterMap(cmap)

    tt_glyphs = {".notdef": draw_glyph_tt(missing_pixels)}
    for g in glyph_recs:
        tt_glyphs[g["gname"]] = draw_glyph_tt(g["pixels"])
    fb_tt.setupGlyf(tt_glyphs)

    fb_tt.setupHorizontalMetrics(hmtx)
    fb_tt.setupHorizontalHeader(ascent=ascent, descent=descent, lineGap=line_gap)

    # fsSelection: REGULAR (bit 6) + USE_TYPO_METRICS (bit 7). A zero
    # fsSelection causes some browsers to silently reject the font's
    # glyphs and fall back to the next family; bit 7 asks clients to
    # honour sTypo* metrics over the Win ascent/descent pair, which is
    # what Google Fonts requires for consistent line heights.
    FS_REGULAR = 1 << 6
    FS_USE_TYPO_METRICS = 1 << 7
    fs_selection = FS_REGULAR | FS_USE_TYPO_METRICS
    os2_panose = dict(
        bFamilyType=panose_values[0], bSerifStyle=panose_values[1],
        bWeight=panose_values[2], bProportion=panose_values[3],
        bContrast=panose_values[4], bStrokeVariation=panose_values[5],
        bArmStyle=panose_values[6], bLetterForm=panose_values[7],
        bMidline=panose_values[8], bXHeight=panose_values[9],
    )

    fb_tt.setupOS2(
        sTypoAscender=ascent,
        sTypoDescender=descent,
        sTypoLineGap=line_gap,
        usWinAscent=ascent,
        usWinDescent=-descent,          # usWinDescent is unsigned / positive
        sxHeight=x_height,
        sCapHeight=cap_height,
        achVendID=VENDOR_ID,
        fsType=0,
        fsSelection=fs_selection,
        version=4,
        ulCodePageRange1=1,     # bit 0 = Latin 1 (CP 1252)
        usWeightClass=400,
        usWidthClass=5,
        panose=os2_panose,
    )
    fb_tt.setupNameTable(dict(
        copyright=COPYRIGHT,
        familyName=FAMILY,
        styleName=STYLE,
        uniqueFontIdentifier=f"{VERSION};{VENDOR_ID};{FAMILY}-{STYLE}",
        fullName=f"{FAMILY} {STYLE}",
        psName=f"{FAMILY}-{STYLE}",
        version=f"Version {VERSION}",
        manufacturer=MANUFACTURER,
        designer=DESIGNER,
        designerURL=DESIGNER_URL,
        vendorURL="https://github.com/anistark/pixelspace",
        licenseDescription=LICENSE_NAME,
        licenseInfoURL=LICENSE_URL,
    ))
    fb_tt.setupPost(
        isFixedPitch=1,
        underlinePosition=underline_pos,
        underlineThickness=underline_thk,
    )

    # gasp: non-hinted, grid-fit + symmetric smoothing at all sizes. Google
    # Fonts requires TTFs to ship a gasp table even when unhinted.
    gasp = newTable("gasp")
    gasp.version = 1
    gasp.gaspRange = {0xFFFF: 0x000F}
    fb_tt.font["gasp"] = gasp

    # prep: smart-dropout control program. Canonical unhinted-TTF incantation
    # (PUSHW 511, SCANCTRL, PUSHB 4, SCANTYPE) — Google Fonts flags missing
    # prep bytecode as FAIL even on unhinted fonts.
    from fontTools.ttLib.tables.ttProgram import Program
    prep = newTable("prep")
    prep_prog = Program()
    prep_prog.fromBytecode(b"\xb8\x01\xff\x85\xb0\x04\x8d")
    prep.program = prep_prog
    fb_tt.font["prep"] = prep

    # meta: declare supported + designed scripts. Suppresses a Font Bakery
    # warning and helps downstream tooling.
    meta = newTable("meta")
    meta.data = {"dlng": "Latn", "slng": "Latn"}
    fb_tt.font["meta"] = meta

    ttf_path = FONT_DIR / f"{FAMILY}-{STYLE}.ttf"
    fb_tt.font.save(ttf_path)
    print(f"wrote {ttf_path} ({ttf_path.stat().st_size} bytes)")

    woff2_path: Path | None = None
    try:
        fb_tt.font.flavor = "woff2"
        woff2_path = FONT_DIR / f"{FAMILY}-{STYLE}.woff2"
        fb_tt.font.save(woff2_path)
        fb_tt.font.flavor = None
        print(f"wrote {woff2_path} ({woff2_path.stat().st_size} bytes)")
    except ImportError:
        print("skipped woff2 (install `brotli` to enable)")

    if DOCS_DIR.is_dir():
        for p in (ttf_path, woff2_path):
            if p is not None:
                dst = DOCS_DIR / p.name
                shutil.copy2(p, dst)
                print(f"staged {dst}")

        if woff2_path is not None:
            b64 = base64.b64encode(woff2_path.read_bytes()).decode("ascii")
            css = (
                "/* Auto-generated by tools/build_font.py - do not edit. */\n"
                "@font-face {\n"
                f'  font-family: "{FAMILY}";\n'
                f'  src: url(data:font/woff2;base64,{b64}) format("woff2");\n'
                "  font-weight: 400;\n"
                "  font-style: normal;\n"
                "  font-display: swap;\n"
                "}\n"
            )
            css_path = DOCS_DIR / "pixelspace-font.css"
            css_path.write_text(css, encoding="utf-8")
            print(f"staged {css_path} ({css_path.stat().st_size} bytes)")

    # ---- CFF / OTF (.otf) ----
    fb_otf = FontBuilder(upem, isTTF=False)
    fb_otf.setupGlyphOrder(glyph_order)
    fb_otf.setupCharacterMap(cmap)

    cff_charstrings = {".notdef": draw_glyph_cff(missing_pixels, missing_adv)}
    for g in glyph_recs:
        cff_charstrings[g["gname"]] = draw_glyph_cff(g["pixels"], g["adv"])
    fb_otf.setupCFF(
        psName=f"{FAMILY}-{STYLE}",
        fontInfo=dict(
            FullName=f"{FAMILY} {STYLE}",
            FamilyName=FAMILY,
            Weight=STYLE,
            version=VERSION,
            Notice=COPYRIGHT,
        ),
        privateDict={},
        charStringsDict=cff_charstrings,
    )
    fb_otf.setupHorizontalMetrics(hmtx)
    fb_otf.setupHorizontalHeader(ascent=ascent, descent=descent, lineGap=line_gap)
    fb_otf.setupOS2(
        sTypoAscender=ascent,
        sTypoDescender=descent,
        sTypoLineGap=line_gap,
        usWinAscent=ascent,
        usWinDescent=-descent,
        sxHeight=x_height,
        sCapHeight=cap_height,
        achVendID=VENDOR_ID,
        fsType=0,
        fsSelection=fs_selection,
        version=4,
        ulCodePageRange1=1,     # bit 0 = Latin 1 (CP 1252)
        usWeightClass=400,
        usWidthClass=5,
        panose=os2_panose,
    )
    fb_otf.setupNameTable(dict(
        copyright=COPYRIGHT,
        familyName=FAMILY,
        styleName=STYLE,
        uniqueFontIdentifier=f"{VERSION};{VENDOR_ID};{FAMILY}-{STYLE}",
        fullName=f"{FAMILY} {STYLE}",
        psName=f"{FAMILY}-{STYLE}",
        version=f"Version {VERSION}",
        manufacturer=MANUFACTURER,
        designer=DESIGNER,
        designerURL=DESIGNER_URL,
        vendorURL="https://github.com/anistark/pixelspace",
        licenseDescription=LICENSE_NAME,
        licenseInfoURL=LICENSE_URL,
    ))
    fb_otf.setupPost(
        isFixedPitch=1,
        underlinePosition=underline_pos,
        underlineThickness=underline_thk,
    )

    otf_meta = newTable("meta")
    otf_meta.data = {"dlng": "Latn", "slng": "Latn"}
    fb_otf.font["meta"] = otf_meta

    otf_path = FONT_DIR / f"{FAMILY}-{STYLE}.otf"
    fb_otf.font.save(otf_path)
    print(f"wrote {otf_path} ({otf_path.stat().st_size} bytes)")


if __name__ == "__main__":
    data = parse_svg_font(SRC)
    m = data["metrics"]
    print(
        f"parsed {len(data['glyphs'])} glyphs from {SRC.name} "
        f"(upem={m['upem']}, ascent={m['ascent']}, descent={m['descent']}, "
        f"cap={m['cap_height']}, x={m['x_height']})"
    )
    build(data)
