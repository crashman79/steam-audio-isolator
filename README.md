# Steam Audio Isolator

A PyQt5-based GUI application that isolates game audio for clean Steam game recording on Linux.

## Overview

Steam's game recording feature on Linux captures all audio sources by default. This tool allows you to:
- Select specific audio sources (game audio)
- Filter out system audio, browser audio, and other non-game sources
- Create PipeWire connections to route only game audio to Steam's recording input
- View and manage active audio routes in real-time

## How It Works

The application analyzes your PipeWire audio configuration to:

1. **Detect Audio Sources**: Identifies all active audio producers (games, browsers, applications)
2. **Filter Sources**: Automatically categorizes sources as:
   - **Game**: Wine/Proton games, detected by `.exe` binary or wine process name
   - **Browser**: Firefox, Chromium, Chrome, Opera, Brave
   - **Communication**: Discord, Slack, Zoom, Telegram, Teams
   - **System**: ALSA hardware devices and system audio
   - **Application**: Other audio-producing applications

3. **Create Routes**: Connects selected sources directly to Steam's recording input node
4. **Manage Routes**: View active connections and disconnect as needed

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

- Linux with PipeWire audio system
- Python 3.8+
- PyQt5 (>=5.15.0)
- PipeWire tools: `pw-cli`, `pw-dump`
- Steam with game recording enabled

## Installation

```bash
pip install -r requirements.txt
python -m steam_pipewire.main
```

Or install the package:

```bash
pip install -e .
steam-pipewire-helper
```

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

1. **Launch the application**
   ```bash
   python -m steam_pipewire.main
   ```

2. **Audio Routing Tab**:
   - Sources are automatically detected and grouped by type
   - Check sources you want to include in Steam recording
   - Click "Apply Routing" to connect them to Steam

3. **Current Routes Tab**:
   - View all active audio connections to Steam
   - Monitor what's currently being recorded

4. **System Info Tab**:
   - Debug information showing node IDs and properties
   - Useful for troubleshooting PipeWire configuration

## Technical Details

### PipeWire Node Types
- **Stream/Output/Audio**: Audio producers (games, apps)
- **Stream/Input/Audio**: Audio consumers (Steam recording, applications)
- **Audio/Source**: Hardware input devices
- **Audio/Sink**: Hardware output devices (speakers)

### Audio Flow in Steam Recording

**Without Filter** (Current Steam behavior):
```
Game Audio → Audio Sink → Hardware → Steam Recording Input
```
This captures everything connected to the audio sink.

**With Filter** (This app):
```
Game Audio (Node 137) → Direct Link → Steam Recording Input (Node 154)
```
Only selected sources connect directly to Steam, system audio flows normally to speakers.

### Example Node IDs (from Duckov game session)
- Node 66: Audio Sink (speakers)
- Node 137: Duckov.exe (Stream/Output/Audio) - Game audio
- Node 154: Steam (Stream/Input/Audio) - Recording input
- Active links: 137 → 66 (for playback), 66 → 154 (everything to Steam)

## Configuration

Profiles are saved in `~/.config/steam-pipewire-helper/profiles/`

## License

MIT

## Troubleshooting

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
