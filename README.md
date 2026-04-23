# Pixelspace

An original 5×7 pixel display typeface by [Kumar Anirudha](https://github.com/anistark).
Single weight (Regular), 93 glyphs covering A–Z, a–z, 0–9, and the common
ASCII punctuation you need to set real text. Licensed under the SIL Open
Font License 1.1 — free to use in personal and commercial work, free to
modify, free to redistribute.

## Install

Grab a release and double-click the font file:

- macOS / Linux: `fonts/Pixelspace-Regular.ttf` → Font Book / your font manager
- Windows: right-click the `.ttf` → Install

In CSS:

```css
@font-face {
  font-family: "Pixelspace";
  src: url("fonts/Pixelspace-Regular.woff2") format("woff2"),
       url("fonts/Pixelspace-Regular.ttf")   format("truetype");
  font-weight: 400;
  font-style: normal;
  font-display: swap;
}

.pixel { font-family: "Pixelspace", monospace; }
```

Pixelspace is monospace — every glyph advances the same 6 pixels — so
disable ligatures and kerning for the crispest look.

## Design

- **Grid:** 5 columns × 7 rows per glyph, plus one built-in column of
  right-side bearing.
- **Metrics:** UPEM 875, pixel = 125 units, advance = 750, ascent = 625,
  descent = 250. Baseline sits between row 4 and row 5; rows 5–6 form
  the descender zone for `g j p q y` (and the like).
- **Shape primitive:** every "on" pixel renders as a 110×110-unit rounded
  square (≈10% corner radius) inset at the top-left of its 125-unit cell,
  so adjacent pixels leave a 15-unit gap on every side — the airy look
  of the design tool, baked straight into the outlines.
- **Pixel integrity:** no anti-aliasing, no hinting tricks. Set the font
  at multiples of 7 CSS pixels (14px, 21px, 28px, …, 105px, 175px) and
  every glyph-pixel lands on a whole device pixel.


## Building from source

Requires Python 3.12+.

```sh
python3 -m venv .venv
.venv/bin/pip install fonttools
.venv/bin/python tools/build_font.py
```

The script parses `sources/Pixelspace.svg`, converts each `<glyph>`'s
pixel rectangles into TrueType outlines, and writes `.ttf`, `.otf`, and
`.woff2` to `fonts/`. It also stages the `.ttf` and `.woff2` into `docs/`
so the GitHub Pages site is self-contained.

## Preview site

[`docs/index.html`](docs/index.html) is a GitHub Pages-ready specimen
that uses `@font-face` to load the compiled font. Enable Pages with
"Deploy from a branch" → `main` → `/docs` to get a live demo URL.

### Tweaking a glyph

Open `sources/Pixelspace.svg` and edit the `<glyph>` element for any
character. Each pixel is a path segment of the form
`M x,y h125 v-125 h-125 Z`, where `(x, y)` is the top-left corner in
y-up font units (baseline at `y=0`, top of cell at `y=625`, bottom at
`y=-250`). Re-run the build script — that's it.

```xml
<glyph glyph-name="uni0041" unicode="A" horiz-adv-x="750"
       d="M125,625h125v-125h-125Z M250,625h125v-125h-125Z …"/>
```

## License

Pixelspace is licensed under the **SIL Open Font License, Version 1.1**.
See [OFL.txt](OFL.txt). "Pixelspace" is a Reserved Font Name — if you fork
and modify the fonts, please pick a different primary family name.

Copyright © 2026 Kumar Anirudha · <https://github.com/anistark/pixelspace>
