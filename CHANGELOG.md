# Changelog

All notable changes to Steam Audio Isolator will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- **Critical fix**: Bluetooth devices no longer detected as audio sources and routed to Steam
  - Added filtering for Bluetooth nodes during source detection (bluez, bluetooth, bt_, hci)
  - Added validation in routing logic to reject Bluetooth devices, audio sinks, and output devices
  - Prevents Bluetooth earbuds/headphones from being incorrectly routed to Steam recording
- **Critical fix**: Game audio now properly continues to play through speakers when routing is applied
  - Removed incorrect logic that was disconnecting game→sink (speakers) connections
  - Game audio now has TWO simultaneous connections: game→speakers (for playback) AND game→Steam (for recording)
  - Only sink→Steam connection is removed to prevent ALL system audio from being recorded
- Added comprehensive Bluetooth device filtering in multiple detection points

### Changed
- Routing logic now preserves game→sink connections to maintain audio playback
- Improved logging for filtered Bluetooth and invalid audio nodes

## [0.1.7] - 2025-12-20

### Fixed
- **Critical fix**: Audio sink (speakers) now properly disconnected from Steam during routing
  - Previously hardcoded audio sink node ID (66), now dynamically detected
  - Fixes issue where system audio leaked into Steam recordings
  - Properly removes all three interfering routes: game→sink, sink→Steam, game→Steam
- Route diagram no longer drifts or changes size when refreshing
- Steam game icons now display correctly (uses Qt icon theme to find steam_icon_* files)
- Wine/Proton games without Steam icons now show colored fallback instead of generic Wine icon
- Internal/monitoring streams (e.g. Bluetooth monitoring) now filtered out and won't be auto-selected

### Changed
- **Auto-apply routing disabled by default** - users must now manually click "Apply Routing"
  - Games are still auto-detected and pre-selected in the list
  - This prevents unwanted automatic routing changes
  - Added checkbox in Settings to enable auto-apply if desired
- Diagram reduced by 20% for more compact display
- Routing instructions now update dynamically based on auto-apply setting

### Added
- Auto-apply routing setting in preferences (Settings tab)
- Dynamic instruction text on routing tab that reflects current auto-apply state

## [0.1.5] - 2025-12-18

### Added
- **Release automation**: New `release.sh` script for automated version bumping across all files
  - Automatically updates version in `setup.py`, `steam_pipewire/__init__.py`, and CHANGELOG.md
  - Creates git commit and annotated tag with proper formatting
  - Validates version format (X.Y.Z) before proceeding
- **Changelog in releases**: Build process now includes version-specific CHANGELOG.md in release tarball
- **Enhanced GitHub Actions**: Workflow automatically extracts changelog section for GitHub release notes

### Changed
- `build_release.sh` now extracts and includes the appropriate changelog version in the release
- GitHub Actions workflow improved to parse and display changelog in release notes

## [0.1.4] - 2025-12-18

### Fixed
- Fixed release installer script not being executable when extracted from tarball
- Fixed stray chmod command appearing in generated install.sh during build

## [0.1.3] - 2025-12-18

### Added
- **Routes visualization diagram**: Visual representation of audio routing to Steam with icons, numbered badges for multiple sources, and curved connection lines
- Diagram displays in "Current Routes" tab showing how audio sources connect to Steam Game Recording

### Fixed
- Removed accidental text paste on line 94 in main_window.py
- Fixed routes diagram visualization scrollbar appearing unnecessarily

### Fixed
- **Discord detection**: Discord now correctly categorized as "Communication" instead of "Browser"
  - Discord appears as "Chromium" in app name but binary is "Discord"
  - WEBRTC VoiceEngine streams now also detected as Discord
- **Vivaldi detection**: Vivaldi browser now properly detected
  - Binary is "vivaldi-bin" which is now in detection list
- **Detection priority**: Communication apps (Discord, Slack) checked before browsers to prevent Electron app misidentification

### Added
- Expanded browser detection: vivaldi, safari, epiphany, falkon, midori, qutebrowser
- Expanded communication apps: element, signal, whatsapp, skype, mumble, teamspeak
- Binary name checking for more reliable app categorization

## [0.1.0] - 2024-12-16

### Added
- Initial public release
- Real-time PipeWire audio source detection
- Intelligent source categorization (Game, Browser, System, Communication, Application)
- Direct node-to-node audio routing via pw-cli
- Route management (view, apply, disconnect)
- System information and debugging view
- Standalone binary with desktop integration
- Automated GitHub Actions build and release
- Issue templates for bug reports, feature requests, and help

### Game Detection Features
- Wine/Proton game detection (.exe, wine64-preloader)
- Steam runtime container detection (pressure-vessel, steam-runtime, reaper)
- Native Linux game detection (.x86_64, .x86, .bin, .sh with Steam path checking)
- Media role hints (media.role=game or production)
- Smart filtering of Steam's own processes (steamwebhelper, gameoverlayui)

### Browser Detection
- Firefox, Chromium, Chrome, Opera, Brave, Edge support

### Communication Apps
- Discord, Slack, Zoom, Telegram, Teams detection

[Unreleased]: https://github.com/crashman79/steam-audio-isolator/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/crashman79/steam-audio-isolator/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/crashman79/steam-audio-isolator/releases/tag/v0.1.0
