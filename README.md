# Steam Audio Isolator

<p align="center">
  <img src="steam-audio-isolator-256.png" alt="Steam Audio Isolator" width="128">
</p>

<p align="center">
  <strong>Isolate game audio for clean Steam game recording on Linux</strong>
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#the-problem">The Problem</a> •
  <a href="#installation">Installation</a> •
  <a href="#usage">Usage</a> •
  <a href="#contributing">Contributing</a>
</p>

---

## The Problem

Steam's game recording feature on Linux captures **all system audio** by default:
- ❌ System notifications
- ❌ Browser audio (YouTube, Spotify, etc.)
- ❌ Discord/chat applications
- ❌ Background applications

This results in cluttered recordings with unwanted sounds mixing into your gameplay footage.

## The Solution

Steam Audio Isolator creates **direct audio connections** from your game to Steam's recording input, bypassing the system audio mixer entirely:

```
Without Steam Audio Isolator:
Game → Audio Sink (speakers) → Steam Recording
     ↳ Browser, Discord, notifications also recorded 😞

With Steam Audio Isolator:
Game → Direct Connection → Steam Recording ✓
Other Audio → Audio Sink → Speakers (not recorded) ✓
```

## Overview

Steam's game recording feature on Linux captures all audio sources by default. This tool allows you to:
- Select specific audio sources (game audio)
- Filter out system audio, browser audio, and other non-game sources
- Create PipeWire connections to route only game audio to Steam's recording input
- View and manage active audio routes in real-time

## How It Works

## Features

### Core Functionality
- 🎮 **Automatic Game Detection** - Detects Wine/Proton games automatically
- 🎯 **Smart Categorization** - Groups audio sources by type (Game, Browser, System, Communication)
- 🔗 **Direct Audio Routing** - Creates point-to-point PipeWire connections
- 💾 **Profile Management** - Save and load routing configurations
- 🎵 **Multi-Stream Support** - Handles games with multiple audio streams (main, UI, voice/chat)

### UI & UX
- 🪟 **System Tray Integration** - Minimize to tray with custom cyan icon
- ⌨️ **Keyboard Shortcuts** - Quick access (Ctrl+Shift+A/C, F5, Ctrl+Shift+H)
- 🔄 **Real-Time Updates** - Auto-detect new audio sources
- ℹ️ **Built-in Help** - Comprehensive About tab with usage guide

### Configuration
- ⚙️ **Flexible Settings** - Configure auto-detect interval, tray behavior, routing restoration
- 🎨 **Stream Purpose Hints** - Identifies main audio, UI sounds, and voice chat streams
- 🚀 **Auto-Apply** - Automatically route newly detected games

## Example Configuration (with Duckov Game)

When analyzing a sample game session:
- **Duckov.exe** (Stream/Output/Audio) → Selected for recording
- **System audio sink** → Filtered out (not captured)
- **Browser audio** → Filtered out (if not selected)
- **Steam Recording Node** → Final destination for game audio

The key distinction: instead of routing all audio through the audio sink (speakers), we connect the game's audio output node **directly** to Steam's recording input node.

## Features

- **Real-time Source Detection**: Automatically discovers all PipeWire audio nodes
- **Source Categorization**: Intelligently groups audio sources by type
- **Direct Node Connections**: Creates point-to-point routes for low-latency recording
- **Route Management**: View, create, and remove audio routes
- **System Information**: Debug view showing node IDs and properties

## Requirements

### System Requirements
- **Linux** with PipeWire audio system (not PulseAudio)
- **Python 3.8+**
- **Steam** with game recording enabled
- PipeWire tools: `pw-cli`, `pw-dump` (usually pre-installed)

### Verify PipeWire
```bash
# Check if PipeWire is running
systemctl --user status wireplumber

# Check available tools
which pw-dump pw-cli
```

## Installation

### Option 1: Download Standalone Binary (Recommended)

**No Python installation required!** Just download and run.

1. Go to [Releases](https://github.com/crashman79/steam-audio-isolator/releases)
2. Download `steam-audio-isolator-linux-x86_64.tar.gz`
3. Extract and install:
   ```bash
   tar -xzf steam-audio-isolator-linux-x86_64.tar.gz
   cd steam-audio-isolator-linux-x86_64
   ./install.sh
   ```
4. Launch from application menu or run: `steam-audio-isolator`

### Option 2: Run from Source

```bash
# Clone the repository
git clone https://github.com/crashman79/steam-audio-isolator.git
cd steam-audio-isolator

# Install dependencies
pip install -r requirements.txt

# Run the application
python -m steam_pipewire.main
```

### Option 3: Build Standalone Binary (For Developers)

```bash
# Clone and build
git clone https://github.com/crashman79/steam-audio-isolator.git
cd steam-audio-isolator

# Install build dependencies
pip install -r requirements.txt pyinstaller

# Build release package
chmod +x build_release.sh
./build_release.sh

# Release tarball will be in dist/
```

**Note**: Desktop integration (application menu, icon, .desktop file) is automatically handled by `install.sh` in the binary release.

## Project Structure

```
steam_pipewire/
├── main.py                 # Application entry point
├── ui/
│   ├── __init__.py
│   └── main_window.py      # Main application window with tabs
├── pipewire/
│   ├── __init__.py
│   ├── source_detector.py  # PipeWire audio source detection
│   └── controller.py       # PipeWire routing control interface
└── utils/
    ├── __init__.py
    └── config.py           # Profile and configuration management
```

## Usage

### Basic Workflow

1. **Start the application** (from terminal or desktop menu)
2. **Audio Routing Tab**: Select games you want to record
   - Game sources are auto-detected and auto-selected
   - Uncheck browser/system audio to exclude them
3. **Click "Apply Routing"** to create direct connections
4. **Start recording in Steam** - Only selected audio is captured!

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Shift+A` | Apply routing |
| `Ctrl+Shift+C` | Clear all routes |
| `F5` | Refresh audio sources |
| `Ctrl+Shift+H` | Hide/Show window |

### Profiles

Save your routing configurations for quick switching:

1. Select desired audio sources
2. Go to **Profiles** tab
3. Enter a name (e.g., "Game Only", "Game + Discord")
4. Click **Save Profile**

### Settings

- **Restore default on close**: Reconnect system audio when quitting
- **Auto-detect interval**: How often to check for new audio sources
- **Minimize to tray**: Hide to system tray instead of closing

### Tips

- **Multiple streams from one game?** The app can identify main audio, UI sounds, and voice chat
- **Don't want a game auto-selected?** Right-click the checkbox to exclude it
- **System tray**: Left-click to show/hide, right-click for menu

## Technical Details

### How It Works

The application uses PipeWire's graph API to:

1. **Enumerate nodes** with `pw-dump` (JSON query)
2. **Identify game audio** by checking process binaries (wine, proton, .exe)
3. **Find Steam's recording node** (auto-discovered each session)
4. **Create direct links** using `pw-cli connect <source> <steam>`
5. **Bypass the audio sink** so system audio isn't captured

### PipeWire Commands

The app uses these commands internally:

```bash
# List all nodes
pw-dump | jq '.[] | select(.type == "PipeWire:Interface:Node")'

# Find Steam node
pw-dump | jq '.[] | select(.info.props."application.name" == "Steam")'

# Create route
pw-cli connect <source_node_id> <steam_node_id>

# List active routes
pw-cli list-objects Link

# Remove route
pw-cli destroy <link_id>
```

### Configuration Files

```
~/.config/steam-audio-isolator/
├── settings.json           # Application settings
└── profiles/
    ├── game-only.pwp      # Saved routing profiles
    ├── game-discord.pwp
    └── ...

~/.cache/steam-audio-isolator.log  # Application logs
```

## Troubleshooting

### "Steam node not found"

**Cause**: Steam's recording input isn't detected

**Solutions**:
- Ensure Steam is running
- Enable **Game Recording** for your game in Steam settings
- Verify PipeWire is running: `systemctl --user status wireplumber`
- Check Steam node exists: `pw-dump | grep -i steam`

### "No audio sources detected"

**Cause**: PipeWire query issues

**Solutions**:
- Start your game **before** launching the app
- Click **Refresh Sources** (F5)
- Verify PipeWire tools: `which pw-dump pw-cli`
- Check logs: `~/.cache/steam-audio-isolator.log`

### Routes not working

**Cause**: Connection issues

**Solutions**:
- Check **Current Routes** tab - are routes listed?
- Verify with: `pw-cli list-objects Link | grep Steam`
- Try **Clear All Routes** then reapply
- Check **System Info** tab for node IDs

### Game audio plays but doesn't record

**Cause**: Steam recording not active

**Solutions**:
- Press Steam's recording hotkey (default: Ctrl+F11)
- Check Steam recording is enabled in settings
- Ensure Steam Game Recording is enabled **per-game**

## Contributing

Contributions are welcome! This project benefits from:

- 🐛 Bug reports and feature requests (open an issue)
- 📝 Documentation improvements
- 🎨 UI/UX enhancements
- 🔧 Code optimization and refactoring
- 🌍 Testing on different Linux distributions

### Development Setup

```bash
git clone https://github.com/crashman79/steam-audio-isolator.git
cd steam-audio-isolator
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m steam_pipewire.main
```

### Building Releases

To build a standalone release package:

```bash
./build_release.sh
```

This creates `dist/steam-audio-isolator-linux-x86_64.tar.gz` ready for GitHub Releases.

**Automated Builds**: The project uses GitHub Actions to automatically build releases when you push a version tag:

```bash
git tag v1.0.0
git push origin v1.0.0
```

## Credits

Developed with AI pair programming assistance (Claude/Copilot), combining human expertise in Linux audio systems and AI-assisted rapid prototyping.

### Technologies

- **PyQt5** - GUI framework
- **PipeWire** - Modern Linux audio system
- **Python 3.8+** - Application runtime

## License

MIT License - see LICENSE file for details

## Support

If you find this tool useful, consider:
- ⭐ Starring the repository
- 🐛 Reporting bugs
- 💡 Suggesting features
- 📢 Sharing with other Linux gamers

---

**Note**: This tool is specifically for Linux systems using PipeWire. It will not work with PulseAudio.

### "Steam node not found"
- Ensure Steam is running
- Make sure PipeWire is your primary audio server
- Check with `pw-dump | grep Steam`

### No audio sources detected
- Verify PipeWire is running: `systemctl --user status wireplumber`
- Check available nodes: `pw-dump Node | jq '.[] | select(.type == "PipeWire:Interface:Node")'`

### Routes not applying
- Verify node IDs are correct in System Info tab
- Check PipeWire logs: `journalctl --user -u wireplumber -f`
- Ensure you have permission to create links: `pw-cli list-objects Link`
