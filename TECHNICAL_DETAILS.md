# PipeWire Technical Details

This document provides technical insight into how Steam Audio Isolator works with PipeWire's audio routing system.

## Understanding the Problem

Steam's game recording feature on Linux captures audio from the system's audio sink (speakers), which means **everything** playing through your speakers gets recorded:

- Game audio ✓
- Browser audio (YouTube, music) ✗
- System notifications ✗
- Discord/voice chat ✗

## Example: PipeWire Node Analysis

Here's a real example from running a game with Steam recording:

### Key Nodes Identified

**1. Node 66: Audio Sink (Hardware)**
- Type: `Audio/Sink`
- Description: System audio output (speakers)
- Role: Hardware playback device

**2. Node 137: Game Audio Output**
- Type: `Stream/Output/Audio`
- Application: Game running under Wine/Proton
- Binary: `wine64-preloader`
- Role: Game audio source

**3. Node 154: Steam Recording Input**
- Type: `Stream/Input/Audio`
- Application: Steam
- Role: Steam's game recording capture node

## Audio Routing Comparison

**Without Steam Audio Isolator:**

```
Game (137) → Audio Sink (66) → Steam Recording (154)
                ↑
        Browser, Discord, System Audio
        (ALL recorded together!)
```

**With Steam Audio Isolator:**

```
Game (137) → Direct Link → Steam Recording (154)
                            (Only game audio)

Browser/System → Audio Sink (66) → Speakers
                                    (Not recorded)
```

## How the Application Works

### 1. Node Discovery

The app uses `pw-dump` to query all PipeWire nodes:

```bash
pw-dump | jq '.[] | select(.type == "PipeWire:Interface:Node")'
```

### 2. Game Detection

Identifies game audio by checking node properties:

- `application.process.binary` contains: `wine`, `proton`, `.exe`
- `media.class` = `Stream/Output/Audio` (audio producer)
- Excludes system nodes: `echo-cancel-*`, `dummy-driver`, `alsa`, `pulse`

### 3. Steam Node Discovery

Locates Steam's recording input:

```bash
pw-dump | jq '.[] | select(.info.props."application.name" == "Steam")'
```

### 4. Direct Routing

Creates point-to-point connection using `pw-cli`:

```bash
pw-cli connect <game_node_id> <steam_node_id>
```

This bypasses the audio sink entirely, so only game audio reaches Steam.

### 5. Route Management

- Lists active links: `pw-cli list-objects Link`
- Removes routes: `pw-cli destroy <link_id>`
- Monitors for new nodes in real-time

## PipeWire Commands Reference

### View all audio nodes
```bash
pw-dump | jq '.[] | select(.type == "PipeWire:Interface:Node")'
```

### Find specific node by name
```bash
pw-dump | jq '.[] | select(.info.props."node.name" | contains("game"))'
```

### List active connections
```bash
pw-cli list-objects Link
```

### Get detailed node info
```bash
pw-cli info <node_id>
```

### Create audio route
```bash
pw-cli connect <source_id> <destination_id>
```

### Remove route
```bash
pw-cli destroy <link_id>
```

## Node Types

- **Audio/Sink**: Hardware output device (speakers, headphones)
- **Audio/Source**: Hardware input device (microphone)
- **Stream/Output/Audio**: Application audio output (games, music players)
- **Stream/Input/Audio**: Application audio input (recording, VOIP)

## Why This Approach Works

1. **Selective Routing**: Only chosen sources connect to Steam
2. **Dual Playback**: Game audio can simultaneously go to speakers AND Steam
3. **No System Impact**: Browser, notifications, etc. still play normally
4. **Real-time**: Changes take effect immediately without restart
5. **Reversible**: Easy to restore default routing

## Debugging Tips

### Check PipeWire is running
```bash
systemctl --user status wireplumber
```

### View graph in real-time
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

## Further Reading

- [PipeWire Documentation](https://docs.pipewire.org/)
- [PipeWire Wiki](https://gitlab.freedesktop.org/pipewire/pipewire/-/wikis/home)
- [pw-cli Manual](https://docs.pipewire.org/page_man_pw-cli_1.html)
