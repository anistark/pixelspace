# Pixelspace — build / serve / validate
#
# Assumes a local `.venv` with `fonttools`, `brotli`, `pillow`, and
# `fontbakery` installed. Run `just setup` once to create it.

venv := ".venv"
py   := venv + "/bin/python"
pip  := venv + "/bin/pip"

# Show available recipes.
default:
    @just --list

# Create the virtualenv and install everything the other recipes need.
setup:
    python3 -m venv {{venv}}
    {{pip}} install --upgrade pip
    {{pip}} install fonttools brotli pillow fontbakery

# Compile sources/Pixelspace.svg into fonts/ and stage into docs/.
build:
    {{py}} tools/build_font.py

# Serve the docs specimen at http://localhost:8000 (Ctrl+C to stop).
serve:
    cd docs && {{py}} -m http.server 8000

# Render a quick preview PNG of the compiled TTF (alphabet + digits).
preview: build
    {{py}} tools/preview.py

# Verify fonts/ and docs/ binaries are byte-identical + CSS is staged.
# Pure compare — does NOT rebuild, so it reflects the on-disk state.
# Catches hand-edits or missed copies after a partial build.
sync-check:
    @cmp -s fonts/Pixelspace-Regular.ttf docs/Pixelspace-Regular.ttf \
        || { echo "✗ fonts/ and docs/ TTF differ — run 'just build'"; exit 1; }
    @cmp -s fonts/Pixelspace-Regular.woff2 docs/Pixelspace-Regular.woff2 \
        || { echo "✗ fonts/ and docs/ WOFF2 differ — run 'just build'"; exit 1; }
    @test -f docs/pixelspace-font.css \
        || { echo "✗ docs/pixelspace-font.css missing — run 'just build'"; exit 1; }
    @echo "✓ fonts/ ↔ docs/ in sync"

# Validate the compiled TTF against the Google Fonts profile.
check: build sync-check
    {{venv}}/bin/fontbakery check-googlefonts fonts/Pixelspace-Regular.ttf

# Lighter Font Bakery profile — opentype basics only.
check-opentype: build
    {{venv}}/bin/fontbakery check-opentype fonts/Pixelspace-Regular.ttf

# Build a dafont-ready zip bundle.
dafont-zip: build
    rm -f pixelspace-dafont.zip
    zip -j pixelspace-dafont.zip \
        fonts/Pixelspace-Regular.ttf \
        OFL.txt FONTLOG.txt README.md
    @echo ""
    @echo "Bundle: pixelspace-dafont.zip"
    @unzip -l pixelspace-dafont.zip

# Stage a Google Fonts submission directory under build/gf/ofl/pixelspace/.
gf-bundle: build
    rm -rf build/gf
    mkdir -p build/gf/ofl/pixelspace
    cp fonts/Pixelspace-Regular.ttf build/gf/ofl/pixelspace/
    cp OFL.txt FONTLOG.txt METADATA.pb DESCRIPTION.en_us.html \
       build/gf/ofl/pixelspace/
    @echo ""
    @echo "Google Fonts submission staged at build/gf/ofl/pixelspace/"
    @ls -la build/gf/ofl/pixelspace/

# Remove build outputs (fonts, docs font assets, bundles).
clean:
    rm -f fonts/Pixelspace-Regular.ttf fonts/Pixelspace-Regular.otf \
          fonts/Pixelspace-Regular.woff2 fonts/Pixelspace-Regular.png
    rm -f docs/Pixelspace-Regular.ttf docs/Pixelspace-Regular.woff2 \
          docs/pixelspace-font.css
    rm -f pixelspace-dafont.zip
    rm -rf build
