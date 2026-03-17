#!/bin/bash
# Build script for Steam Audio Isolator standalone release

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "=== Steam Audio Isolator Release Builder ==="
echo ""

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Error: Virtual environment not found. Run: python -m venv .venv"
    exit 1
fi

# Activate virtual environment
source .venv/bin/activate

# Install/upgrade PyInstaller
echo "Installing PyInstaller..."
pip install --upgrade pyinstaller

# Generate icons if they don't exist
if [ ! -f "steam-audio-isolator-256.png" ]; then
    echo "Generating icons..."
    python generate_icon.py
fi

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build/ dist/ steam_pipewire.spec

# Build with PyInstaller
echo ""
echo "Building standalone executable..."
pyinstaller --name="steam-audio-isolator" \
    --onefile \
    --windowed \
    --icon=steam-audio-isolator-256.png \
    --add-data="steam-audio-isolator-256.png:." \
    --hidden-import=PyQt5.QtCore \
    --hidden-import=PyQt5.QtGui \
    --hidden-import=PyQt5.QtWidgets \
    --collect-all=PyQt5 \
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
