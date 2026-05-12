# Steam Audio Isolator
**Isolate game audio for clean Steam Game Recording on Linux**

---

## Problem Statement
Steam Game Recording on Linux captures all system audio by default—everything playing through your speakers gets recorded:

*   System notifications
*   Browser audio (YouTube, Spotify, etc.)
*   Discord/chat applications
*   Background applications

This results in cluttered recordings with unwanted sounds mixing into your gameplay footage.

## Solution
Steam Audio Isolator creates direct audio connections from your game to Steam Game Recording's input, completely bypassing the system audio mixer:

```bash
❌ WITHOUT Steam Audio Isolator:
   Game → Audio Sink (speakers) → Steam Game Recording
       ↳ Browser, Discord, notifications also recorded

✅ WITH Steam Audio Isolator:
   Game → Direct Connection → Steam Game Recording
   Other Audio → Speakers (not recorded)
```

## Features

### Core Functionality
*   **Automatic Game Detection**: Detects Wine/Proton and native Linux games.
*   **Intelligent Categorization**: Automatically classifies audio sources:
    *   Games: Wine, Proton, native executables
    *   Browsers: Firefox, Chrome, Chromium, Brave, Vivaldi, Edge, Safari
    *   Communication: Discord, Slack, Zoom, Telegram, Teams, Skype
    *   System: ALSA, PulseAudio, notification daemons
    *   Applications: Everything else
*   **Direct Audio Routing**: Creates point-to-point PipeWire connections, bypassing the audio sink.
*   **Multi-Stream Support**: Handles games with multiple audio streams (main, UI, voice).
*   **Profile Management**: Save and load routing configurations for quick switching.

### User Interface
*   **Current Routes table**: Active PipeWire links to Steam recording (auto-refreshed on the same interval as source detection).
*   **System Tray Integration**: Minimize to tray with a custom icon.
*   **Real-Time Updates**: Auto-detects new audio sources every 3 seconds.
*   **Tabbed Interface**:
    *   Audio Routing (source selection)
    *   Current Routes (active links table)
    *   System Info (node IDs and properties)
    *   Settings (behavior configuration)
    *   Profiles (save/load configurations)
    *   About (help and information)

### Configuration & Settings
*   **Flexible Settings**:
    *   Auto-detect interval (how often to check for new audio sources)
    *   Restore default on close (reconnect audio sink when quitting)
    *   Minimize to tray vs. close behavior
    *   Add to application menu and Start when I log in (app manages desktop and autostart entries itself)
*   **Stream Purpose Detection**: Identifies main audio vs. UI sounds vs. voice chat.
*   **Auto-Apply Routing**: Automatically routes newly detected games.

## Screenshots

<p align="center">
    <img src="screenshots/steam-audio-isolator%20main%20tab.png" alt="Steam Audio Isolator Main Tab" width="800">
    <br><em>Main tab showing the current routing UI after the recent layout revisions</em>
</p>

<p align="center">
    <img src="screenshots/steam-audio-isolator%20settings%20tab.png" alt="Steam Audio Isolator Settings Tab" width="800">
    <br><em>Settings tab showing the updated configuration layout</em>
</p>

<details>
<summary>Click to see routing comparison in qpwgraph</summary>

<p align="center">
    <img src="screenshots/before%20routing.png" alt="Before Routing" width="800">
    <br><em>qpwgraph before routing - all audio flows through the default sink (speakers), including game audio, browser, and system sounds</em>
</p>

<p align="center">
    <img src="screenshots/after%20routing.png" alt="After Routing" width="800">
    <br><em>qpwgraph after routing - game audio has direct connections to Steam Game Recording input, bypassing the sink. Browser and system audio remain on speakers (not recorded)</em>
</p>
</details>

## Installation

### Flatpak (recommended)
Stable Freedesktop **24.08** runtime; `pw-cli` / `pw-dump` are bundled in the app. **Install from [GitHub Releases](https://github.com/crashman79/steam-audio-isolator/releases):** download **`steam-audio-isolator-x86_64.flatpak`**, then:

```bash
flatpak install --user ./steam-audio-isolator-x86_64.flatpak
flatpak run io.github.crashman79.steam-audio-isolator
```
For a newer version, install the new `.flatpak` from the latest release (or uninstall the old ref first if the installer prompts).

**Build and install locally from this repo** (installs Freedesktop 24.08 runtime/SDK from Flathub if needed):

```bash
chmod +x build.sh
./build.sh
flatpak run io.github.crashman79.steam-audio-isolator
```

See [`flatpak/README.md`](flatpak/README.md) for CI, permissions, and `./build.sh --bundle`.

On first run the app uses XDG config/cache/data (under `~/.var/app/...` when installed as Flatpak). **GitHub Releases** ship **`steam-audio-isolator-x86_64.flatpak`** only ([`.github/workflows/build-release.yml`](.github/workflows/build-release.yml)).

### Building releases (developers)
*   **Flatpak**: `./build.sh` (user install) or `./build.sh --bundle` (`.flatpak` file). Manifest: `flatpak/io.github.crashman79.steam-audio-isolator.yml`.

### Requirements
*   **Linux** with PipeWire audio system (not PulseAudio)
*   **Steam** with game recording enabled
*   PipeWire tools: `pw-cli`, `pw-dump` (usually pre-installed)

**Verify PipeWire is running:**
```bash
systemctl --user status wireplumber
which pw-dump pw-cli
```

---

## Quick Start

### Step 1: Start the Application
*   Run the Flatpak (`flatpak run io.github.crashman79.steam-audio-isolator`) or open **Steam Audio Isolator** from your application menu after installing the `.flatpak` or building locally with `./build.sh`. The app automatically detects all PipeWire audio sources.

### Step 2: Select Audio Sources
1.  Go to **Audio Routing** tab.
2.  Game sources are auto-detected and auto-selected.
3.  Uncheck system, browser, and other non-game sources.
4.  Your selection will be highlighted in the list.

### Step 3: Apply Routing
1.  Click **Apply Routing**.
2.  Watch the **Current Routes** tab update in real-time.
3.  The routes visualization diagram should show your connections.

### Step 4: Start Recording in Steam
1.  Press Steam's recording hotkey (default: **Ctrl+F11**).
2.  Only your selected game audio is captured!
3.  Verify in the **Current Routes** tab that connections are active.

### Step 5: When Done
*   Click **Clear All Routes** to disconnect. The app restores default routing (if "Restore default on close" is enabled).

---

## Application Tabs

### Audio Routing Tab
*   **Source List**: Displays all detected audio sources grouped by type (Game, Browser, System, Communication, Application).
*   **Checkboxes**: Select which sources to route to Steam.
*   **Buttons**: **Apply Routing** (create selected routes), **Clear All Routes** (disconnect all).
*   **Auto-select**: Games are automatically selected when detected.
*   **Status**: Shows total sources found and current selection.

### Current Routes Tab
*   **Table**: Source name, node ID, channel, and link ID for each active route to Steam recording.
*   **Auto-refresh**: Same interval as **Source Auto-Detection** in Settings (plus **Refresh now** if you want an immediate update).

### System Info Tab
*   **Node IDs and Details**: Shows node IDs, names, and properties for debugging purposes.
*   **Technical**: Shows application names, binaries, media classes.

### Settings Tab
*   **Restore default on close**: When enabled, disconnects game routes and reconnects audio sink on exit.
*   **Show confirmation when closing**: Prompts before quitting.
*   **Auto-detect interval**: How often (in seconds) to check for new audio sources.
*   **Automatically apply routing when new games are detected**: Optional auto-apply feature.
*   **Minimize to tray**: Close button hides to tray instead of quitting.
*   **Start minimized to tray**: App starts with only the tray icon visible.
*   **Flatpak:** "Start when I log in" uses **xdg-desktop-portal** (`RequestBackground`) so KDE, GNOME, and other portal-enabled desktops show a system permission dialog instead of a sandbox-only autostart file. “Add to menu” / “copy to ~/.local/bin” are not offered; use `flatpak update` for updates.
*   **Theme**: Light, dark, or system.

### Profiles Tab
*   **Save Profile**: Create a named profile with your current routing selection.
*   **Load Profile**: Quickly restore a saved configuration.
*   **Delete Profile**: Remove a profile you no longer need.
*   **Storage**: Profiles are stored under the app config dir (Flatpak: `~/.var/app/io.github.crashman79.steam-audio-isolator/config/steam-audio-isolator/profiles/`).

### About Tab
*   **Version Info**: Current application version.
*   **Usage Guide**: Quick reference for common tasks.
*   **Repository Link**: Link to GitHub project.

---

## How It Works
### Detection & Categorization
The app analyzes each PipeWire node's properties to categorize sources:
1.  Check process binary (wine, proton, firefox, etc.).
2.  Check application name (Discord, Slack, Zoom, etc.).
3.  Check media class (Stream/Output/Audio = audio producer).
4.  Exclude system nodes (dummy drivers, echo cancellation, ALSA, Pulse).

### Routing
When you click "Apply Routing":
1. Finds the Steam recording node (auto-discovered).
2. Removes any existing audio sink → Steam connections (to prevent double-recording).
3. Creates direct **game audio → Steam** connections using `pw-cli create-link`.
4. System audio continues to speakers normally.
5. The Current Routes table updates on the next poll (or use **Refresh now**).

### Cleanup
When you click "Clear All Routes":
1. Disconnects all game audio from Steam.
2. Optionally reconnects the audio sink (for default behavior).
3. All audio returns to speakers.

## Technical Details

### Source Detection
*   **Games**: Detects Wine, Proton executables and native Linux games.
*   **Browsers**: Firefox, Chrome, Chromium, Opera, Brave, Edge, Vivaldi, Safari.
*   **Communication**: Discord, Slack, Zoom, Telegram, Teams, Skype, Mumble, TeamSpeak.
*   **System**: System daemons, notification systems.
*   **Filtering**: Automatically excludes echo-cancel nodes, dummy drivers, internal systems.

### Node Structure
*   **Audio Sink**: Your speaker/headphone hardware.
*   **Game Node**: Audio output from your game.
*   **Steam Node**: Steam's recording input.

### Why Direct Routing Works
*   Selective: Only chosen sources connect to Steam.
*   Dual playback: Game audio goes to speakers AND Steam simultaneously.
*   Clean: No system audio in your recording.
*   Reversible: Easy to restore default routing anytime.
*   Real-time: Changes take effect instantly.

### PipeWire Commands Used
```bash
pw-dump                              # Query all nodes and connections
pw-cli create-link                   # Create audio routing connection
pw-cli destroy <link_id>             # Remove routing connection
pw-cli list-objects Link             # View active connections
```

### Configuration Storage
```
~/.var/app/io.github.crashman79.steam-audio-isolator/config/steam-audio-isolator/
├── settings.json                    # Application settings (theme, tray, autostart, etc.)
└── profiles/
    ├── game-only.pwp               # Saved routing profiles
    └── ...

~/.var/app/io.github.crashman79.steam-audio-isolator/cache/
└── steam-audio-isolator.log
```

---

## Troubleshooting

### "Steam node not found"
**Cause**: Steam's recording input isn't detected.
**Solutions**:
*   Ensure Steam is running.
*   Enable **Game Recording** in Steam settings for your game.
*   Verify PipeWire is running: `systemctl --user status wireplumber`.
*   Check Steam node exists: `pw-dump | grep -i steam`.
*   Click **Refresh Sources** in the app.

### "No audio sources detected"
**Cause**: Game not started or PipeWire issue.
**Solutions**:
*   Start your game *before* launching the app.
*   Check PipeWire is running: `systemctl --user status wireplumber`.
*   Verify tools are installed: `which pw-dump pw-cli`.
*   Click **Refresh Sources** (F5) button.
*   Check logs: `~/.cache/steam-audio-isolator.log`.

### Routes not appearing in "Current Routes"
**Solutions**:
*   Click **Refresh Routes** button in Current Routes tab.
*   Check **System Info** tab for node IDs.
*   Verify with: `pw-cli list-objects Link`.

### Audio still being captured (unwanted sources)
**Problem**: System sounds or browser audio in recording.
**Solution**:
1.  Go to **Audio Routing** tab.
2.  Uncheck any system, browser, or non-game sources.
3.  Keep only game sources checked.
4.  Click **Apply Routing** again.

### Game audio plays but doesn't record in Steam
**Solutions**:
*   Press Steam's recording hotkey (default: **Ctrl+F11**).
*   Verify Steam Game Recording is enabled per-game in Steam settings.
*   Check audio is working in speakers first.

---

## Project Structure
```
steam_pipewire/
├── main.py                 # Application entry point
├── ui/
│   ├── __init__.py
│   └── main_window.py      # PyQt5 GUI with 6 tabs + routes diagram
├── pipewire/
│   ├── __init__.py
│   ├── source_detector.py  # PipeWire node detection & categorization
│   └── controller.py       # PipeWire routing control (pw-cli interface)
└── utils/
    ├── __init__.py
    └── config.py           # Settings & profile management
```

---

## Version History

**v0.2.0 (2025-03-17)** — Standalone binary, app-managed config/menu/autostart, Copy to ~/.local/bin, first-run install prompt. See [CHANGELOG.md](CHANGELOG.md).

**v0.1.3 (2025-12-18)**
*   Added routes visualization diagram in Current Routes tab.
*   Fixed unnecessary scrollbar in routes display.
*   Improved Steam recording target label.

**v0.1.1 (2025-12-17)**
*   Fixed Discord detection for Electron apps.
*   Fixed Vivaldi browser detection.
*   Improved communication app detection priority.

**v0.1.0 (2025-12-16)**
*   Initial public release.
*   Core audio routing functionality.
*   GUI with settings and profiles.
*   Real-time source detection.

See [CHANGELOG.md](CHANGELOG.md) for detailed changes.

---

## Contributing
Contributions welcome! This project benefits from:
*   Bug reports and feature requests
*   Documentation improvements
*   UI/UX enhancements
*   Code optimization
*   Testing on different Linux distributions

### Development
Clone the repo, run `./build.sh` then `flatpak run io.github.crashman79.steam-audio-isolator`.

---

## Notes
This tool is for **Linux only** with **PipeWire**. It will not work with PulseAudio or on Windows/macOS.