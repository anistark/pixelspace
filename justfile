# Pixelspace — build / serve / validate
#
# Assumes a local `.venv` with `fonttools`, `brotli`, `pillow`, and
# `fontbakery` installed. Run `just setup` once to create it.

venv := ".venv"
py   := venv + "/bin/python"
pip  := venv + "/bin/pip"

# Single source of truth for the version — read from build_font.py.
version := `grep '^VERSION = ' tools/build_font.py | cut -d'"' -f2`

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
    {{py}} -m http.server 8000 --directory docs

# Render a quick preview PNG of the compiled TTF (alphabet + digits).
preview: build
    {{py}} tools/preview.py

# Regenerate article/specimen.png — the hero image used in ARTICLE.en_us.html.
specimen: build
    {{py}} tools/specimen.py

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

# The website's Download button links to this asset on the latest release.
# Normally built & attached by .github/workflows/release-zip.yml on
# release:published — run locally only if you need to attach by hand.
# Build the user-facing release zip (TTF + OTF + license + install).
release-zip: build
    rm -f Pixelspace.zip
    zip -j Pixelspace.zip \
        fonts/Pixelspace-Regular.ttf \
        fonts/Pixelspace-Regular.otf \
        OFL.txt FONTLOG.txt INSTALL.txt README.md
    @echo ""
    @echo "Bundle: Pixelspace.zip — attach to the GitHub release"
    @unzip -l Pixelspace.zip

# The release-zip workflow then auto-attaches Pixelspace.zip — no need
# to run release-zip locally.
# Cut a GitHub release for the current VERSION.
gh-release:
    @gh auth status >/dev/null 2>&1 || { echo "✗ Run 'gh auth login' first"; exit 1; }
    @echo "Releasing v{{version}}..."
    gh release create v{{version}} \
        --title "Pixelspace v{{version}}" \
        --notes "Pixelspace v{{version}}. See [FONTLOG.txt](https://github.com/anistark/pixelspace/blob/main/FONTLOG.txt) for changes. The downloadable .zip will be attached automatically by CI."
    @echo ""
    @echo "Released: https://github.com/anistark/pixelspace/releases/tag/v{{version}}"

# Cuts the GitHub release; the release-zip workflow then builds the
# font on CI and attaches Pixelspace.zip — no local zip step needed.
# Publish a new version (cut the GitHub release; CI handles the zip).
publish: gh-release
    @echo ""
    @echo "Watch the asset attach at:"
    @echo "  https://github.com/anistark/pixelspace/actions/workflows/release-zip.yml"

# Stage a Google Fonts submission directory under build/gf/ofl/pixelspace/.
# Initialises build/gf/ as its own git repo so fontbakery's license check
# does not walk up into this repo and see a duplicate OFL.txt.
gf-bundle: build
    rm -rf build/gf
    mkdir -p build/gf/ofl/pixelspace
    cp fonts/Pixelspace-Regular.ttf build/gf/ofl/pixelspace/
    cp OFL.txt FONTLOG.txt METADATA.pb build/gf/ofl/pixelspace/
    cp -r article build/gf/ofl/pixelspace/
    git -C build/gf init -q
    @echo ""
    @echo "Google Fonts submission staged at build/gf/ofl/pixelspace/"
    @ls -la build/gf/ofl/pixelspace/

# Run fontbakery against the staged GF bundle (the submission shape).
check-gf: gf-bundle
    {{venv}}/bin/fontbakery check-googlefonts \
        build/gf/ofl/pixelspace/Pixelspace-Regular.ttf

# Remove build outputs (fonts, docs font assets, bundles).
clean:
    rm -f fonts/Pixelspace-Regular.ttf fonts/Pixelspace-Regular.otf \
          fonts/Pixelspace-Regular.woff2 fonts/Pixelspace-Regular.png
    rm -f docs/Pixelspace-Regular.ttf docs/Pixelspace-Regular.woff2 \
          docs/pixelspace-font.css
    rm -f pixelspace-dafont.zip Pixelspace.zip
    rm -rf build
