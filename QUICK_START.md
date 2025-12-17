# Quick Start Guide

## Installation

1. **Prerequisites**
   ```bash
   # Ensure PipeWire is running
   systemctl --user status wireplumber
   
   # Install Python dependencies
   cd "/home/crashman79/development/steam pipewire helper"
   pip install -r requirements.txt
   ```

2. **Launch the Application**
   ```bash
   # Method 1: Direct Python
   python -m steam_pipewire.main
   
   # Method 2: Virtual environment (recommended)
   /path/to/.venv/bin/python -m steam_pipewire.main
   
   # Method 3: VS Code (Ctrl+Shift+B)
   ```

## Basic Usage

### Step 1: Detect Audio Sources
- Application starts and automatically detects all PipeWire audio sources
- Sources are grouped by type: Game, Browser, System, Communication, Application

### Step 2: Select Sources
1. Check the box next to the game you're playing (e.g., "Duckov.exe")
2. **Important**: Uncheck system, browser, and other non-game sources
3. Current selection shows immediately

### Step 3: Apply Routing
1. Click "✓ Apply Routing"
2. Success message confirms routes were created
3. Steam will now record ONLY the selected game audio

### Step 4: Verify Routes
1. Switch to "Current Routes" tab
2. You should see connections like: `[Node 137] Duckov.exe → Steam`
3. These routes stay active until you click "✕ Clear All Routes"

## Troubleshooting

### "Steam node not found"
**Problem**: Steam recording input not detected
**Solution**: 
1. Make sure Steam is running
2. Enable game recording in Steam settings
3. Click "Refresh Sources" button

### No audio sources detected
**Problem**: Application doesn't find any game audio
**Solution**:
1. Start your game BEFORE launching this app
2. Check PipeWire is running: `systemctl --user status wireplumber`
3. Verify with: `pw-dump | grep "application.name"`

### Routes not appearing in "Current Routes"
**Problem**: Applied routes aren't showing
**Solution**:
1. Switch to "Current Routes" tab
2. Click "Refresh Routes"
3. Check "System Info" tab for node IDs
4. Verify manually: `pw-cli list-objects Link`

### Audio still being captured (unwanted sources)
**Problem**: System sounds still in recording
**Solution**:
1. Return to "Audio Routing" tab
2. Uncheck any uncategorized or system sources
3. Keep only the game source checked
4. Reapply routing

## Advanced Usage

### Save a Profile
1. Select your preferred sources
2. Look for profile save in menu (feature under development)
3. Profiles stored in: `~/.config/steam-pipewire-helper/profiles/`

### Manual PipeWire Commands
```bash
# List all audio nodes
pw-dump | jq '.[] | select(.type == "PipeWire:Interface:Node") | {id, name: .info.props."node.name"}'

# Find Steam
pw-dump | jq '.[] | select(.info.props."application.name" == "Steam")'

# Create route manually
pw-cli connect <source_node_id> <steam_node_id>

# Remove route
pw-cli destroy <link_id>

# View current routes
pw-cli list-objects Link
```

### Configuration Files
```
~/.config/steam-pipewire-helper/
├── profiles/
│   ├── profile1.pwp      # JSON format
│   ├── profile2.pwp
│   └── ...
```

## Common Workflows

### Workflow 1: Multiple Games
```
Game 1 (Proton) → Selected
Game 2 (Wine)   → Not selected
Browser         → Not selected
↓
Apply Routing
↓
Steam records only Game 1
```

### Workflow 2: Game + Voicechat
```
Game Audio      → Selected
Discord         → Selected (if wanted in recording)
Browser         → Not selected
System Sounds   → Not selected
↓
Apply Routing
↓
Steam records game + discord (if selected)
```

### Workflow 3: Multiple Audio Interfaces
```
HDMI Audio      → Not selected
USB Headset     → Selected
Microphone      → Not selected
↓
Apply Routing
↓
Game audio from USB device recorded
```

## System Info Tab

View detailed PipeWire information:
- Steam Recording Node ID
- Detected audio sources with:
  - Node IDs (for manual commands)
  - Application names
  - Media class
  - Source type classification

Use this for:
- Debugging source detection
- Manual PipeWire commands
- Recording node IDs for reference

## Performance Notes

- **Detection**: First run takes ~500ms to query PipeWire
- **Apply Routing**: < 1 second per source
- **UI Response**: Background thread prevents freezing
- **Memory**: ~50MB typical for the application
- **CPU**: Minimal when idle, brief spike during detection

## Getting Help

### Debug Mode
1. Open "System Info" tab
2. Note all node IDs shown
3. Run manual commands: `pw-cli info <node_id>`
4. Compare with expected values

### Manual Testing
```bash
# Test source detection
pw-dump | jq '.[] | select(.info.props."media.class" == "Stream/Output/Audio")'

# Test Steam node
pw-cli info 154  # Usually Steam, but ID varies

# Test routing
pw-cli connect 137 154
pw-cli list-objects Link
pw-cli destroy <link_id>
```

## Next Steps

1. **Customize**: Edit source detection logic in `source_detector.py`
2. **Extend**: Add audio visualization in new tab
3. **Integrate**: Connect with Steam API for auto-detection
4. **Enhance**: Add system tray icon and hotkeys

## Documentation

For more details, see:
- `README.md` - Full project overview
- `PIPEWIRE_ANALYSIS.md` - Technical PipeWire details
- `IMPLEMENTATION_SUMMARY.md` - Architecture and design
- `.github/copilot-instructions.md` - Developer notes
