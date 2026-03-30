#!/bin/bash
# Build script for Steam Audio Isolator standalone release

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "=== Steam Audio Isolator Release Builder ==="
echo ""

VENV_PY="${SCRIPT_DIR}/.venv/bin/python"

# Create venv if missing (Arch / PEP 668: never use system pip without a venv)
if [ ! -x "$VENV_PY" ]; then
    echo "Creating virtual environment (.venv)..."
    if command -v python3 >/dev/null 2>&1; then
        python3 -m venv "${SCRIPT_DIR}/.venv"
    else
        python -m venv "${SCRIPT_DIR}/.venv"
    fi
fi

if [ ! -x "$VENV_PY" ]; then
    echo "Error: Could not create or use .venv (missing $VENV_PY)"
    exit 1
fi

# Always use venv interpreter so pip/PyInstaller never hit the system environment
echo "Installing build dependencies into .venv..."
"$VENV_PY" -m pip install --upgrade pip
"$VENV_PY" -m pip install -r "${SCRIPT_DIR}/requirements.txt"
"$VENV_PY" -m pip install --upgrade pyinstaller

# Generate icons if they don't exist
if [ ! -f "steam-audio-isolator-256.png" ]; then
    echo "Generating icons..."
    "$VENV_PY" generate_icon.py
fi

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build/ dist/ steam_pipewire.spec

# Build with PyInstaller
echo ""
echo "Building standalone executable..."
"$VENV_PY" -m PyInstaller --name="steam-audio-isolator" \
    --onefile \
    --windowed \
    --icon=steam-audio-isolator-256.png \
    --add-data="steam-audio-isolator-256.png:." \
    --hidden-import=PyQt5.QtCore \
    --hidden-import=PyQt5.QtGui \
    --hidden-import=PyQt5.QtWidgets \
    --collect-all=PyQt5 \
    --collect-data=certifi \
    --hidden-import=certifi \
    steam_pipewire/main.py

# Create release directory: binary only, no install step
echo "Creating release package..."
mkdir -p dist/release
cp dist/steam-audio-isolator dist/release/
chmod +x dist/release/steam-audio-isolator

# Minimal README: run the binary; app manages config, menu, autostart
cat > dist/release/README.txt << 'EOF'
Steam Audio Isolator - Standalone binary (no installation)

RUN
===

  chmod +x steam-audio-isolator
  ./steam-audio-isolator

On first run the app creates config at ~/.config/steam-audio-isolator/
Use Settings in the app to add to application menu or launch at login.

REQUIREMENTS
============

- Linux with PipeWire (not PulseAudio)
- Steam with game recording enabled
- pw-cli, pw-dump (usually pre-installed)
EOF

# Create tarball (preserve file permissions with -p)
RELEASE_NAME="steam-audio-isolator-linux-x86_64"
tar -czpf "dist/${RELEASE_NAME}.tar.gz" -C dist/release .
SIZE=$(du -h "dist/${RELEASE_NAME}.tar.gz" | cut -f1)

echo ""
echo "Building portable bundle (venv + launcher; recommended when onefile is fragile)..."
PORTABLE_BASE="${SCRIPT_DIR}/dist"
PORTABLE="${PORTABLE_BASE}/steam-audio-isolator-portable"
rm -rf "${PORTABLE}"
mkdir -p "${PORTABLE}"
cp -a "${SCRIPT_DIR}/steam_pipewire" "${PORTABLE}/"
cp "${SCRIPT_DIR}/requirements.txt" "${PORTABLE}/"
if [ -f "${SCRIPT_DIR}/steam-audio-isolator-256.png" ]; then
  cp "${SCRIPT_DIR}/steam-audio-isolator-256.png" "${PORTABLE}/"
fi
cp "${SCRIPT_DIR}/packaging/portable-launcher.sh" "${PORTABLE}/steam-audio-isolator"
chmod +x "${PORTABLE}/steam-audio-isolator"

"${VENV_PY}" -m venv "${PORTABLE}/.venv"
"${PORTABLE}/.venv/bin/pip" install --upgrade pip
"${PORTABLE}/.venv/bin/pip" install --no-cache-dir -r "${PORTABLE}/requirements.txt"

cat > "${PORTABLE}/README.txt" << 'PREADME'
Steam Audio Isolator — portable directory bundle

RUN
===

  cd steam-audio-isolator-portable
  ./steam-audio-isolator

This uses a normal Python venv and PyQt5 wheels (no PyInstaller). It tends to
behave better across Wayland vs X11 and Ubuntu vs Arch than the single-file
binary, at the cost of a larger download.

REFRESH ON A NEW PC / AFTER UPGRADE
===================================

  ./.venv/bin/pip install --no-cache-dir -r requirements.txt

ADVANCED: distro PyQt5 (optional)
=================================

  rm -rf .venv && python3 -m venv --system-site-packages .venv
  ./.venv/bin/pip install --no-cache-dir pydbus darkdetect 'certifi>=2023'

  Install your distro's PyQt5 for Python (e.g. python-pyqt5) so the venv sees it via system-site-packages.

REQUIREMENTS
============

- Linux x86_64 with PipeWire, pw-cli, pw-dump
- Steam with game recording enabled
PREADME

PORTABLE_TAR="steam-audio-isolator-linux-x86_64-portable.tar.gz"
tar -czpf "${PORTABLE_BASE}/${PORTABLE_TAR}" -C "${PORTABLE_BASE}" steam-audio-isolator-portable
PORTABLE_SIZE=$(du -h "${PORTABLE_BASE}/${PORTABLE_TAR}" | cut -f1)

echo ""
echo "=== Build Complete! ==="
echo ""
echo "One-file:  dist/${RELEASE_NAME}.tar.gz (size: $SIZE)"
echo "Portable:  dist/${PORTABLE_TAR} (size: $PORTABLE_SIZE)"
echo ""
echo "One-file: run steam-audio-isolator; smallest download; can be picky on some setups."
echo "Portable: unpack steam-audio-isolator-portable/ and run ./steam-audio-isolator — uses venv PyQt (more flexible)."
echo ""
