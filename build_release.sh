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

# Create release directory structure
echo "Creating release package..."
mkdir -p dist/release

# Copy files to release directory
echo "Copying files to release directory..."
cp dist/steam-audio-isolator dist/release/
cp steam-audio-isolator-256.png dist/release/
cp steam-audio-isolator.desktop dist/release/

# Create installation script
cat > dist/release/install.sh << 'EOF'
#!/bin/bash
# Installation script for Steam Audio Isolator

set -e

INSTALL_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"

echo "=== Steam Audio Isolator Installer ==="
echo ""

# Create directories
mkdir -p "$INSTALL_DIR"
mkdir -p "$DESKTOP_DIR"
mkdir -p "$ICON_DIR"

# Copy executable
echo "Installing executable to $INSTALL_DIR..."
cp steam-audio-isolator "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/steam-audio-isolator"

# Copy icon
echo "Installing icon..."
cp steam-audio-isolator-256.png "$ICON_DIR/steam-audio-isolator.png"

# Update .desktop file paths
echo "Installing desktop entry..."
sed "s|Exec=.*|Exec=$INSTALL_DIR/steam-audio-isolator|g" steam-audio-isolator.desktop > "$DESKTOP_DIR/steam-audio-isolator.desktop"
chmod +x "$DESKTOP_DIR/steam-audio-isolator.desktop"

# Update desktop database
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database "$DESKTOP_DIR"
fi

echo ""
echo "✅ Installation complete!"
echo ""
echo "You can now:"
echo "  • Find 'Steam Audio Isolator' in your application menu"
echo "  • Run from terminal: steam-audio-isolator"
EOF

# Make install.sh executable
chmod +x dist/release/install.sh

# Create README for release
cat > dist/release/README.txt << 'EOF'
Steam Audio Isolator - Standalone Release

QUICK START
===========

1. Extract this archive
2. Run: ./install.sh
3. Launch from your application menu or run: steam-audio-isolator

MANUAL INSTALLATION
===================

If you prefer not to use the install script:

1. Copy 'steam-audio-isolator' to somewhere in your PATH
   Example: cp steam-audio-isolator ~/.local/bin/

2. Make it executable:
   chmod +x ~/.local/bin/steam-audio-isolator

3. (Optional) Install desktop entry:
   cp steam-audio-isolator.desktop ~/.local/share/applications/
   cp steam-audio-isolator-256.png ~/.local/share/icons/hicolor/256x256/apps/

REQUIREMENTS
============

- Linux with PipeWire (not PulseAudio)
- Steam with game recording enabled
- PipeWire tools (pw-cli, pw-dump) - usually pre-installed

RUNNING
=======

From terminal:
  ./steam-audio-isolator

Or find it in your application menu after installation.

UNINSTALL
=========

rm ~/.local/bin/steam-audio-isolator
rm ~/.local/share/applications/steam-audio-isolator.desktop
rm ~/.local/share/icons/hicolor/256x256/apps/steam-audio-isolator.png
rm -rf ~/.config/steam-audio-isolator/

For more information, visit:
https://github.com/YOUR_USERNAME/steam-audio-isolator
EOF

# Create tarball (preserve file permissions with -p)
RELEASE_NAME="steam-audio-isolator-linux-x86_64"
tar -czpf "dist/${RELEASE_NAME}.tar.gz" -C dist/release .

# Calculate size
SIZE=$(du -h "${RELEASE_NAME}.tar.gz" | cut -f1)

echo ""
echo "=== Build Complete! ==="
echo ""
echo "Release package: dist/${RELEASE_NAME}.tar.gz"
echo "Size: $SIZE"
echo ""
echo "Contents:"
echo "  • steam-audio-isolator (executable)"
echo "  • install.sh (automatic installer)"
echo "  • steam-audio-isolator-256.png (icon)"
echo "  • steam-audio-isolator.desktop (desktop entry)"
echo "  • README.txt (instructions)"
echo ""
echo "Upload this file to GitHub Releases!"
echo ""
