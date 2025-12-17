#!/usr/bin/env python3
"""
PIPEWIRE CONFIGURATION ANALYSIS - Duckov Game Example

This document explains the PipeWire audio configuration discovered when
running the Duckov game with Steam recording enabled.

=== KEY NODES IDENTIFIED ===

1. Node 66: Audio Sink (alsa_output.pci-0000_0e_00.4.analog-stereo)
   - Type: Audio/Sink
   - Description: Starship/Matisse HD Audio Controller Analog Stereo
   - Role: Hardware playback device (speakers)

2. Node 137: Duckov.exe (Game Audio Output)
   - Type: Stream/Output/Audio
   - Application: Duckov.exe (Wine game)
   - Role: Game audio source
   - Binary: wine64-preloader

3. Node 154: Steam (Recording Input)
   - Type: Stream/Input/Audio
   - Application: Steam
   - Role: Game recording capture node
   - Note: This is what Steam's record button uses

=== CURRENT AUDIO ROUTING (OBSERVED) ===

Current Flow:
  Duckov (137) --link-118--> Audio Sink (66) --link-139--> Steam (154)
  Duckov (137) --link-121--> Audio Sink (66)

This means:
- Duckov outputs audio to the system audio sink (speakers)
- The audio sink is connected to Steam's recording input
- Therefore Steam captures ALL audio routed through that sink

=== PROBLEM WITH CURRENT SETUP ===

When any application outputs audio to Node 66 (speakers), Steam will record it:
- System notification sounds → Steam captures them
- Browser audio → Steam captures them (if playing through same sink)
- Any application audio → Steam captures it

This is why Steam records "all audio" currently.

=== SOLUTION: DIRECT NODE ROUTING ===

Instead of routing through the audio sink, we create direct connections:

Desired Flow:
  Duckov (137) --new-link--> Steam (154)  [DIRECT]
  [Other audio] --> Audio Sink (66) --> [Speakers only]

Implementation:
  pw-cli connect 137 154

This:
1. Creates a direct link from game output to Steam input
2. Bypasses the audio sink entirely for Steam recording
3. Allows other audio to play normally on speakers
4. Lets Steam only record the selected game audio

=== SOURCE DETECTION LOGIC ===

The application uses these heuristics to identify game audio:

1. Check application.process.binary:
   - Contains 'wine', 'proton' → GAME
   - Contains 'game', '.exe' → GAME

2. Check application.name:
   - Contains 'firefox', 'chrome', 'chromium' → BROWSER
   - Contains 'discord', 'slack', 'zoom' → COMMUNICATION
   - Contains 'wine', 'proton' → GAME

3. Check node.name:
   - Contains 'alsa', 'pulse', 'jack' → SYSTEM
   - Otherwise → APPLICATION

4. Media class filtering:
   - Only accept: Stream/Output/Audio, Audio/Source
   - Reject: Stream/Input/Audio, Midi/Bridge, etc.

5. Skip internal nodes:
   - echo-cancel-* → skip (system processing)
   - dummy-driver → skip (fallback driver)
   - freewheel-driver → skip (test driver)

=== CONFIGURATION FILES ===

Profiles saved in: ~/.config/steam-pipewire-helper/profiles/

Example profile (profile_name.pwp):
{
  "sources": ["Duckov.exe"],
  "steam_device": 154
}

=== MANAGING ROUTES ===

List current routes to Steam:
  pw-dump Link | jq '.[] | select(.info.input_node_id == 154)'

Create route:
  pw-cli connect <source_node_id> <steam_node_id>

Remove route:
  pw-cli destroy <link_id>

=== SYSTEM INFORMATION ===

Commands used in the application:

1. Get all nodes:
   pw-dump | jq '.[] | select(.type == "PipeWire:Interface:Node")'

2. Get node details:
   pw-cli info <node_id>

3. List links:
   pw-cli list-objects Link

4. Find Steam node:
   pw-dump | jq '.[] | select(.info.props."application.name" == "Steam")'

=== TESTING THE SOLUTION ===

To test game audio filtering:

1. Launch app and select only Duckov.exe
2. Click "Apply Routing"
3. Play game audio → Steam records it
4. Open browser and play audio → Game NOT recorded
5. Play system notification → Game NOT recorded

Verify with:
  pw-cli list-objects Link | grep "137\|154"

This shows the connections between Duckov (137) and Steam (154).

=== NOTES FOR DEVELOPERS ===

- Node IDs change on every reboot/audio restart
- Application names vary (wine-preloader, game.exe, etc.)
- Some games use ALSA directly instead of PulseAudio
- Proton games may show as game.so or custom binary names
- Always verify steam_node_id is set before creating routes
- PipeWire may auto-connect nodes, requiring cleanup first
