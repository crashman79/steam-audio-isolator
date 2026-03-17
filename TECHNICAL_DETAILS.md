# Technical Details

Deep dive into how Steam Audio Isolator works with PipeWire's audio routing system.

## Understanding the Problem

Steam's game recording feature captures audio from the system's **audio sink** (speakers), which means **everything** playing through your speakers gets recorded:

- Game audio ✓
- Browser audio (YouTube, music) ✗
- System notifications ✗
- Discord/voice chat ✗

This happens because Steam's recording node is typically connected to the same audio sink that handles all playback.

## How Steam Audio Isolator Works

### Node Types in PipeWire

| Type | Example | Role |
|------|---------|------|
| **Audio/Sink** | Hardware speakers | System playback output (all audio) |
| **Stream/Output/Audio** | Game audio, Browser | Application audio source |
| **Stream/Input/Audio** | Steam recording | Application audio capture |

### The Routing Strategy

**Standard Setup (Everything Recorded):**
```
Game (137)      ─┐
Browser (105)   ─┼─→ Audio Sink (66) ─→ Steam Recording (154)
System (67)     ─┘

Result: Game + Browser + System audio all recorded 😞
```

**With Steam Audio Isolator (Game Only):**
```
Game (137) ─────────────────┐
                            ├─→ Steam Recording (154) ✓
Browser (105) ─┐            │
System (67)   ─┼─→ Audio Sink (66) ─→ Speakers ✓
              │
App audio  ───┘

Result: Only game audio recorded, rest plays normally ✓
```

### Application Detection Logic

The app categorizes sources in order of priority:

**1. Communication Apps (checked FIRST)**
- Binary check: discord, slack, zoom, telegram, teams, skype, mumble, teamspeak
- Name check: Similar names
- **Why first?** Electron apps (Discord, Slack) appear as "Chromium" but have different binaries

**2. Browsers**
- Binary: firefox, chrome, chromium, opera, brave, edge, vivaldi, safari, epiphany
- Name: Similar patterns
- **Excludes**: Communication apps already caught in step 1

**3. Games**
- Binary: wine, proton, or contains .exe
- Type: Stream/Output/Audio
- **Includes**: Wine, Proton, native Linux games

**4. System Audio**
- Echo cancellation nodes (echo-cancel-*)
- Dummy drivers
- ALSA, Pulse, JACK nodes
- Internal mixers

**5. Everything Else**
- Categorized as "Application"

### Routing Process

When you click **"Apply Routing"**:

1. **Enumerate all nodes** via `pw-dump`
2. **Identify Steam node** by checking `application.name == "Steam"`
3. **Find selected source nodes** (your game selections)
4. **Disconnect sink→Steam links** (remove default routing)
5. **Create source→Steam links** (direct game audio routes)
6. **Update visualization** in real-time

### Cleanup Process

When you click **"Clear All Routes"**:

1. **Disconnect all source→Steam links**
2. **Optionally reconnect sink→Steam** (if "Restore default on close" is enabled)
3. **Visualization updates** to show no active routes

## Real-World Example

### Before Running the App

```bash
$ pw-dump | jq '.[] | select(.type == "PipeWire:Interface:Link")'
{
  "id": 100,
  "direction": "->",
  "ports": [66, 154]  # Audio Sink → Steam Recording
}
```

This shows the audio sink is connected to Steam recording (the problem).

### After Running the App

```bash
$ pw-dump | jq '.[] | select(.type == "PipeWire:Interface:Link")'
[
  {
    "id": 100,
    "ports": [66, 154]  # REMOVED: Audio Sink → Steam
  },
  {
    "id": 200,
    "ports": [137, 154]  # ADDED: Game → Steam
  }
]
```

Now only the game audio reaches Steam.

## PipeWire Command Reference

```bash
# List all nodes with their IDs and types
pw-dump | jq '.[] | select(.type == "PipeWire:Interface:Node") | {id: .id, name: .info.props."node.name", app: .info.props."application.name"}'

# Find a specific application
pw-dump | jq '.[] | select(.info.props."application.name" == "Steam")'

# List all active audio connections
pw-cli list-objects Link

# Get detailed info about a node
pw-cli info 137

# Create a connection between nodes
pw-cli create-link 137 154

# Destroy a connection
pw-cli destroy 200

# Check for connections to a specific node (Steam)
pw-dump | jq '.[] | select(.type == "PipeWire:Interface:Link") | select(.ports[] | contains(154))'
```

## Stream Purpose Detection

When a game has multiple audio streams, the app attempts to identify:

- **Main audio** - Primary game music/SFX
- **UI sounds** - Menu clicks, notifications
- **Voice chat** - Communication audio

This is based on stream names and ports, allowing selective routing if desired.

## Configuration Files

### Settings Storage
```
~/.config/steam-audio-isolator/settings.json
{
  "restore_default_on_close": true,
  "prompt_on_close": true,
  "auto_detect_interval": 3,
  "auto_apply_games": true,
  "minimize_to_tray": true,
  "theme": "system",
  "start_minimized_to_tray": false,
  "start_at_login": false,
  "add_to_app_menu": false,
  "install_prompt_shown": false
}
```
When "Add to application menu" or "Start when I log in" is enabled, the app copies the running binary to `~/.local/bin/steam-audio-isolator` (when running as a PyInstaller binary) and writes the desktop or autostart file with that path, so launchers work regardless of where the binary was originally run from.

### Profile Storage
```
~/.config/steam-audio-isolator/profiles/game-only.pwp
{
  "name": "Game Only",
  "sources": [137, 138, 152]          # Node IDs to route
}
```

### Log Files
```
~/.cache/steam-audio-isolator.log     # Debug logs with timestamps
```

## Visualization Diagram

The **Current Routes** tab displays a diagram showing:

- **2-column grid** of your audio sources with icons
- **Numbered badges** (#1, #2, etc.) for multiple sources from same app
- **Curved connection lines** from each source to Steam Game Recording
- **Real-time updates** as routes change

The diagram makes it visually clear which sources are connected to Steam.

## Key Design Decisions

### Why Direct Routing?
- ✓ **Clean audio**: No unwanted sources mixed in
- ✓ **Low latency**: Direct connections, no intermediate processing
- ✓ **Reversible**: Easy to restore default behavior
- ✓ **Dual output**: Game audio can go to both speakers AND Steam

### Why Auto-Detection?
- ✓ **User convenience**: Don't ask which is game audio
- ✓ **Reliable**: Process binaries are consistent
- ✓ **Fast**: Detection happens in < 100ms

### Why PipeWire?
- Modern Linux audio system with fine-grained control
- Graph-based routing (not stream-based like Pulse)
- Supports exactly what we need: node enumeration + link creation
- Replaces PulseAudio on newer distributions

## Debugging Tips

### Enable verbose logging
```bash
# Check logs in real-time
tail -f ~/.cache/steam-audio-isolator.log

# Or set log level (if implemented)
export STEAM_AUDIO_DEBUG=1
steam-audio-isolator
```

### Verify PipeWire state
```bash
# Check if wireplumber is running
systemctl --user status wireplumber

# Monitor PipeWire changes in real-time
pw-mon

# Check PipeWire version
pw-dump | head -5
```

### Manually check Steam node
```bash
# Find Steam in the output
pw-dump | jq '.[] | select(.info.props."application.name" | contains("Steam"))'

# Check if it has audio connections
pw-cli list-objects Link | grep -A2 -B2 "node_id.*154"
```

### Troubleshoot a route
```bash
# Verify a route was created
pw-cli list-objects Link | grep "137"  # Check if node 137 connected

# Get details on the link
pw-cli info 200  # Use link ID from above

# Remove problematic link
pw-cli destroy 200

# Recreate it manually
pw-cli create-link 137 154
```

### View graph in real time
```bash
pw-top
```

### Monitor events
```bash
pw-dump --monitor
```

### Check Steam node exists
```bash
pw-dump | grep -i steam
```

## Future Improvements

- Per-stream routing (select which game streams go to Steam)
- Audio level monitoring with visual indicators
- Automatic route creation based on Steam's current game
- Advanced PipeWire configuration export/import
- User-customizable app detection patterns

## Multi-Stream Games

Some games produce multiple audio streams:

- **Main Audio**: Game sound effects, music
- **UI Audio**: Menu sounds, notifications  
- **Voice Chat**: In-game voice communication

The app detects these using `media.role` hints:
- `Movie` / `Game` → Main audio (auto-selected)
- `Communication` → Voice chat (user choice)
- `Notification` / `event` → UI sounds (user choice)

This allows fine-grained control over what gets recorded.

## References

- [PipeWire Documentation](https://pipewire.org/)
- [pw-dump Reference](https://manpages.debian.org/bookworm/pipewire/pw-dump.1.en.html)
- [pw-cli Reference](https://manpages.debian.org/bookworm/pipewire/pw-cli.1.en.html)
- [Steam Game Recording on Linux](https://support.steampowered.com/kb_article.php?ref=8789-YDXV-8589)
- [PipeWire Wiki](https://gitlab.freedesktop.org/pipewire/pipewire/-/wikis/home)
