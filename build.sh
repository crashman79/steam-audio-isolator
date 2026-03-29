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
echo "=== Build Complete! ==="
echo ""
echo "Release: dist/${RELEASE_NAME}.tar.gz (size: $SIZE)"
echo "Contents: steam-audio-isolator, README.txt"
echo ""
echo "No install step. User runs the binary; app manages config, menu, and autostart via Settings."
echo ""
