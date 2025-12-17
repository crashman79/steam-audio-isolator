# Steam Audio Isolator - Copilot Instructions

## Project Overview
This is a PyQt5-based GUI application that isolates game audio for clean Steam game recording on Linux. The app allows users to select which audio sources (game audio) should be routed directly to Steam's recording input, filtering out system audio, browser audio, and other non-game sources.

**Current Version:** v0.1.1  
**Repository:** https://github.com/crashman79/steam-audio-isolator  
**Status:** Active development, public releases available

## Current Implementation Status
- ✅ Complete PyQt5 GUI with tabbed interface
- ✅ Real-time PipeWire node detection and analysis with caching
- ✅ Intelligent source categorization (Game, Browser, System, Communication, Application)
- ✅ Direct node-to-node audio routing via pw-cli
- ✅ Route management (view current routes, apply new routes, disconnect)
- ✅ System information and debugging view
- ✅ Error handling and user feedback
- ✅ Standalone binary builds via PyInstaller
- ✅ Automated GitHub Actions CI/CD
- ✅ Desktop integration (.desktop file, system tray)

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

### Application Detection Logic (v0.1.1+)
Sources are categorized by checking in order:

**Priority 1: Communication Apps (checked BEFORE browsers)**
- Binary check: discord, slack, zoom, telegram, teams, skype, mumble, teamspeak, element, signal, whatsapp
- Name check: discord, slack, zoom, telegram, teams, skype, mumble, teamspeak, webrtc, element, signal
- **Why first?** Prevents Electron apps (Discord, Slack) from being misidentified as browsers

**Priority 2: Browsers**
- Binary check: firefox, chrome, chromium, opera, brave, edge, vivaldi, safari, epiphany, falkon, midori, qutebrowser
- Name check: firefox, chrome, chromium, opera, brave, edge, vivaldi, safari, epiphany

**Priority 3: Games**
- Wine/Proton: wine, proton, .exe in binary (1289 lines)
├── pipewire/
│   ├── __init__.py
│   ├── source_detector.py           # PipeWire node analysis & categorization
│   └── controller.py                # pw-cli interface (615 lines)
└── utils/
    ├── __init__.py
    └── config.py                    # Profile management (169 lines)

Root files:
├── CHANGELOG.md                      # Version history (Keep a Changelog format)
├── README.md                         # User documentation
├── TECHNICAL_DETAILS.md              # PipeWire routing details
├── build_release.sh                  # PyInstaller build script
├── requirements.txt                  # Python dependencies
├── setup.py                          # Package configuration
├── .github/
│   ├── workflows/build-release.yml  # Automated builds on tag push
│   └── ISSUE_TEMPLATE/              # Bug report, feature request, help templateslayui
- Exclude internal nodes: echo-cancel-*, dummy-driver, freewheel-driver

**Key Detection Fixes (v0.1.1):**
- Discord: Appears as "Chromium" or "WEBRTC VoiceEngine" but binary is "Discord"
- Vivaldi: Binary is "vivaldi-bin", now correctly detected as browser

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
4.Config stored in: `~/.config/steam-audio-isolator/`
- Profiles: `~/.config/steam-audio-isolator/profiles/*.pwp`
- Logs: `~/.cache/steam-audio-isolator.log`

## Release Process
1. Update CHANGELOG.md: Move [Unreleased] changes to new version section with date
2. Commit changelog: `git commit -m "Release vX.Y.Z"`
3. Create annotated tag: `git tag -a vX.Y.Z -m "Release vX.Y.Z - summary"`
4. Push tag: `git push origin vX.Y.Z`
5. GitHub Actions automatically builds binary and creates release
6. Copy changelog section to GitHub release notes

**Version Numbering:**
- v0.x.x: Pre-1.0 releases (current)
- Patch (0.1.X): Bug fixes, detection improvements
- Minor (0.X.0): New features
- Major (X.0.0): Breaking changes or stable release

## Changelog Maintenance
Always update CHANGELOG.md under `[Unreleased]` section:
- `### Added` - New features
- `### Changed` - Changes to existing functionality
- `### Fixed` - Bug fixes
- `### Removed` - Removed features

Example:
```markdown
## [Unreleased]

### Fixed
- Discord detection now works correctly with Electron apps
``i
5. **Route Management**: View active connections and toggle routes on/off
6. **System Info Tab**: Shows node IDs and properties for debugging
7. **Error Handling**: Graceful failures with user feedback

## Development Notes
- Requires PipeWire (n (Consider for v0.2.0+)
- Real-time audio level monitoring with visual indicators
- Audio waveform visualization
- Automatic game detection using Steam API
- Profile templates for popular games
- Hotkey support for quick routing changes (shortcuts exist but not global)
- Advanced PipeWire config export/import
- Audio format and sample rate management
- User-configurable detection patterns for apps
- Flatpak packaging
- AUR package for Arch Linux

## Known Limitations
- Requires PipeWire (cannot work with PulseAudio)
- Steam must be running for recording node detection
- Some Flatpak apps may not be detected correctly
- No audio preview/monitoring (planned for v0.2.0)

## Testing Notes
- **No unit tests** - This is a desktop GUI app with tight PipeWire integration
- Manual testing required with actual games and Steam
- Test with: Wine games, Proton games, native Linux games, browsers, Discord
- Verify detection accuracy: Check "System Info" tab for node properties

## Important: When Making Changes
1. **Always update CHANGELOG.md** under [Unreleased]
2. Test with actual PipeWire system (no mocking possible)
3. Check both detection and routing functionality
4. Verify Steam node discovery works
5. Test with games in different categories (Wine, Proton, native)
6. Consider backward compatibility for config filesand apply routing
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
