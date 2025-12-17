# Steam Audio Isolator - Copilot Instructions

## Project Overview
This is a PyQt5-based GUI application that isolates game audio for clean Steam game recording on Linux. The app allows users to select which audio sources (game audio) should be routed directly to Steam's recording input, filtering out system audio, browser audio, and other non-game sources.

## Current Implementation Status
- ✅ Complete PyQt5 GUI with tabbed interface
- ✅ Real-time PipeWire node detection and analysis
- ✅ Intelligent source categorization (Game, Browser, System, Communication, Application)
- ✅ Direct node-to-node audio routing via pw-cli
- ✅ Route management (view current routes, apply new routes, disconnect)
- ✅ System information and debugging view
- ✅ Error handling and user feedback

## How to Run
1. From terminal in the project directory:
   ```bash
   "/home/crashman79/development/steam pipewire helper/.venv/bin/python" -m steam_pipewire.main
   ```

2. Or use VS Code task: Press Ctrl+Shift+B and select "Run Steam PipeWire Helper"

## PipeWire Configuration Analysis (Duckov Example)

### Problem Identified
Steam's default game recording captures **ALL audio** routed to the audio sink (speakers), including:
- System notifications
- Browser audio
- Any application audio playing simultaneously

### Solution Implemented
Instead of routing through the audio sink, the app creates **direct connections** between game audio nodes and Steam's recording input:

**Current (Default) Flow:**
```
Game (137) → Audio Sink (66) → Steam Recording (154)
[All audio through sink → Steam records everything]
```

**Fixed Flow (With App):**
```
Game (137) → Direct Link → Steam Recording (154)
[System audio plays through speakers, Steam only records game]
```

### Key Node IDs (from Duckov Analysis)
- Node 66: Audio Sink (speakers)
- Node 137: Duckov.exe (Stream/Output/Audio)
- Node 154: Steam (Stream/Input/Audio)
- Active Links: 118, 121 (game to sink), 139 (sink to Steam)

### Application Detection Logic
Sources are categorized by checking:
1. `application.process.binary` - wine, proton, .exe → Game
2. `application.name` - firefox, chrome → Browser; discord, slack → Communication
3. `node.name` - alsa, pulse → System
4. Skip internal nodes: echo-cancel-*, dummy-driver, freewheel-driver

## Project Structure
```
steam_pipewire/
├── main.py                           # Application entry point
├── ui/
│   ├── __init__.py
│   └── main_window.py               # Tabbed GUI window
├── pipewire/
│   ├── __init__.py
│   ├── source_detector.py           # PipeWire node analysis
│   └── controller.py                # pw-cli interface
└── utils/
    ├── __init__.py
    └── config.py                    # Profile management
```

## Key Features Implemented
1. **Audio Source Detection**: Queries pw-dump for all PipeWire nodes
2. **Intelligent Filtering**: Excludes system nodes, only shows audio producers
3. **Source Categorization**: Automatically classifies sources by application type
4. **Direct Routing**: Creates direct node connections via pw-cli
5. **Route Management**: View active connections and toggle routes on/off
6. **System Info Tab**: Shows node IDs and properties for debugging
7. **Error Handling**: Graceful failures with user feedback

## Development Notes
- Requires PipeWire (not PulseAudio): `systemctl --user status wireplumber`
- Uses `pw-dump` for node enumeration and `pw-cli` for routing
- Steam node ID is automatically discovered and cached
- Routes are created with: `pw-cli connect <source_id> <steam_id>`
- Routes are removed with: `pw-cli destroy <link_id>`
- Profiles stored in: `~/.config/steam-pipewire-helper/profiles/`

## UI Components
1. **Audio Routing Tab**: Select sources and apply routing
2. **Current Routes Tab**: View active connections to Steam
3. **System Info Tab**: Debug information and node details

## Dependencies
- PyQt5 (>=5.15.0) - GUI framework
- pydbus (>=0.6.0) - D-Bus support (optional, for future features)
- PipeWire tools (pw-dump, pw-cli) - Audio system utilities
- System: PipeWire daemon and WirePlumber

## Testing Commands
```bash
# Check PipeWire status
systemctl --user status wireplumber

# List all audio nodes
pw-dump | jq '.[] | select(.type == "PipeWire:Interface:Node")'

# Find Steam node
pw-dump | jq '.[] | select(.info.props."application.name" == "Steam")'

# List active routes
pw-cli list-objects Link

# Get node details
pw-cli info 154

# Create test route
pw-cli connect 137 154

# Remove route
pw-cli destroy <link_id>
```

## Future Enhancements
- Real-time audio level monitoring with visual indicators
- Audio waveform visualization
- Automatic game detection using Steam API
- Profile templates for popular games
- System tray integration
- Hotkey support for quick routing changes
- Advanced PipeWire config export/import
- Audio format and sample rate management
