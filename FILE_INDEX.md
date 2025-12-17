# Steam PipeWire Helper - File Index & Navigation

## 📋 Quick Navigation

### 🚀 Getting Started
1. **[QUICK_START.md](QUICK_START.md)** ← **START HERE**
   - Installation steps
   - Basic usage guide
   - Troubleshooting section
   - Common workflows

2. **[README.md](README.md)**
   - Project overview
   - Features and benefits
   - Requirements and installation
   - Complete usage documentation

### 📚 Technical Documentation

3. **[PIPEWIRE_ANALYSIS.md](PIPEWIRE_ANALYSIS.md)**
   - Deep dive into Duckov game configuration
   - Node structure and routing analysis
   - Source detection logic explanation
   - Testing commands reference

4. **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)**
   - Architecture overview
   - Component breakdown
   - Technical achievements
   - Performance characteristics

5. **[PROJECT_DELIVERY_SUMMARY.md](PROJECT_DELIVERY_SUMMARY.md)**
   - Complete delivery report
   - What was built and why
   - Verification results
   - Success metrics

### 👨‍💻 Developer Resources

6. **[.github/copilot-instructions.md](.github/copilot-instructions.md)**
   - Development guidelines
   - Project structure explanation
   - Testing commands
   - Future enhancements roadmap

7. **[.vscode/tasks.json](.vscode/tasks.json)**
   - VS Code task configuration
   - Build and run commands
   - Task automation

---

## 📦 Application Structure

```
steam_pipewire/
├── main.py                         Entry point (13 lines)
├── __init__.py                     Package init
│
├── ui/
│   ├── __init__.py
│   └── main_window.py             GUI implementation (465 lines)
│                                   ├─ SourceDetectorThread: Background detection
│                                   ├─ MainWindow: Tabbed interface
│                                   │  ├─ Audio Routing Tab
│                                   │  ├─ Current Routes Tab
│                                   │  └─ System Info Tab
│                                   └─ Event handlers and UI logic
│
├── pipewire/
│   ├── __init__.py
│   ├── source_detector.py         Audio source detection (170 lines)
│   │                               ├─ get_audio_sources(): Main detection
│   │                               ├─ get_steam_recording_node(): Find Steam
│   │                               ├─ _parse_nodes(): Node analysis
│   │                               └─ _determine_source_type(): Classification
│   │
│   └── controller.py              Routing control (180 lines)
│                                   ├─ _update_steam_node(): Auto-discover
│                                   ├─ get_recording_devices(): List targets
│                                   ├─ get_current_routes(): Show active
│                                   ├─ create_audio_routing(): Apply routing
│                                   ├─ remove_routing(): Disconnect
│                                   └─ disconnect_all_from_steam(): Bulk remove
│
└── utils/
    ├── __init__.py
    └── config.py                  Profile management (80 lines)
                                    ├─ save_profile(): Save JSON config
                                    ├─ load_profile(): Load JSON config
                                    ├─ list_profiles(): List saved profiles
                                    └─ delete_profile(): Remove profile
```

---

## 🔧 Configuration Files

### `setup.py`
- Package metadata and dependencies
- Entry point configuration
- Installation script

### `requirements.txt`
- PyQt5==5.15.9
- pydbus==0.6.0

### `.vscode/tasks.json`
- "Run Steam PipeWire Helper" task
- "Install Dependencies" task
- Task automation for VS Code

### `.github/copilot-instructions.md`
- AI assistant guidelines
- Development best practices
- Testing and documentation standards

---

## 📖 Documentation File Breakdown

### QUICK_START.md (5.3 KB)
**For**: Users ready to use the application
- Installation procedures
- Step-by-step usage guide
- Troubleshooting common issues
- Advanced workflows
- Configuration examples

### README.md (5.1 KB)
**For**: Understanding the project scope
- Problem statement (Steam records all audio)
- Solution explanation (direct node routing)
- Feature list
- Installation and usage
- Technical architecture diagram
- Configuration management
- Troubleshooting guide

### PIPEWIRE_ANALYSIS.md (4.3 KB)
**For**: Technical deep-dive on audio configuration
- Duckov game node analysis
- Current vs desired audio routing
- Node identification and purposes
- Source detection algorithms
- PipeWire commands reference
- Testing procedures

### IMPLEMENTATION_SUMMARY.md (8.6 KB)
**For**: Understanding how the solution works
- Problem and solution diagrams
- Component descriptions
- User workflow explanation
- Technical architecture
- Discovery findings
- Advantages comparison table
- Performance metrics

### PROJECT_DELIVERY_SUMMARY.md (12 KB)
**For**: Executive overview and verification
- Complete feature list
- Technical achievements
- File structure with line counts
- Verified functionality
- Testing commands
- Success metrics

### .github/copilot-instructions.md (4.5 KB)
**For**: Developers and AI assistants
- Project guidelines
- Development practices
- Testing procedures
- Future enhancements
- Best practices

---

## 🎯 Feature Map

| Feature | File | Method | Status |
|---------|------|--------|--------|
| Audio Detection | source_detector.py | get_audio_sources() | ✅ |
| Source Categorization | source_detector.py | _determine_source_type() | ✅ |
| Steam Node Discovery | controller.py | _update_steam_node() | ✅ |
| Create Routes | controller.py | create_audio_routing() | ✅ |
| Remove Routes | controller.py | remove_routing() | ✅ |
| List Routes | controller.py | get_current_routes() | ✅ |
| GUI Window | main_window.py | MainWindow | ✅ |
| Routing Tab | main_window.py | create_routing_tab() | ✅ |
| Routes Tab | main_window.py | create_routes_tab() | ✅ |
| Info Tab | main_window.py | create_info_tab() | ✅ |
| Profile Save | config.py | save_profile() | ✅ |
| Profile Load | config.py | load_profile() | ✅ |

---

## 🧪 Testing Reference

### Manual PipeWire Commands
```bash
# List all nodes
pw-dump | jq '.[] | select(.type == "PipeWire:Interface:Node")'

# Find specific application
pw-dump | jq '.[] | select(.info.props."application.name" == "Steam")'

# View detailed node info
pw-cli info 137  # Example: Duckov.exe

# Create direct route
pw-cli connect 137 154

# Remove route
pw-cli destroy <link_id>

# List all links
pw-cli list-objects Link
```

---

## 📊 Project Statistics

| Metric | Value |
|--------|-------|
| **Python Code Lines** | 913 |
| **Main Application** | main_window.py (465 lines) |
| **PipeWire Detection** | source_detector.py (170 lines) |
| **Routing Control** | controller.py (180 lines) |
| **Configuration** | config.py (80 lines) |
| **Documentation** | ~40 KB across 5 guides |
| **Components** | 4 modules + utilities |
| **GUI Tabs** | 3 (Routing, Routes, System Info) |
| **Error Checks** | Comprehensive try/except blocks |
| **Type Hints** | Full coverage |

---

## 🔄 Data Flow

### Source Detection Flow
```
User clicks "Refresh" or app starts
    ↓
SourceDetectorThread.run()
    ↓
SourceDetector.get_audio_sources()
    ↓
pw-dump (JSON query)
    ↓
Parse nodes and filter audio sources
    ↓
Categorize by type (Game, Browser, System, etc.)
    ↓
MainWindow.on_sources_detected(sources)
    ↓
Update UI with checkboxes grouped by type
```

### Routing Application Flow
```
User selects sources and clicks "Apply Routing"
    ↓
MainWindow.apply_routing()
    ↓
Get selected source IDs from list
    ↓
Get Steam node ID from PipeWireController
    ↓
PipeWireController.create_audio_routing()
    ↓
For each source: pw-cli connect <source> <steam>
    ↓
Success message or error dialog
    ↓
MainWindow.update_current_routes()
    ↓
Display active routes to user
```

---

## 🚀 Getting Help

### For Installation Issues
→ See [QUICK_START.md](QUICK_START.md) - Troubleshooting section

### For Technical Understanding
→ See [PIPEWIRE_ANALYSIS.md](PIPEWIRE_ANALYSIS.md)

### For Architecture Questions
→ See [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)

### For Using the Application
→ See [README.md](README.md) or [QUICK_START.md](QUICK_START.md)

### For Development
→ See [.github/copilot-instructions.md](.github/copilot-instructions.md)

---

## 📝 Development Workflow

1. **Start**: Read [QUICK_START.md](QUICK_START.md) to understand the application
2. **Explore**: Review [README.md](README.md) for full features
3. **Technical**: Deep dive into [PIPEWIRE_ANALYSIS.md](PIPEWIRE_ANALYSIS.md)
4. **Implement**: Use [.github/copilot-instructions.md](.github/copilot-instructions.md) for coding
5. **Verify**: Follow testing procedures in [PIPEWIRE_ANALYSIS.md](PIPEWIRE_ANALYSIS.md)
6. **Report**: Reference [PROJECT_DELIVERY_SUMMARY.md](PROJECT_DELIVERY_SUMMARY.md)

---

## 🎓 Learning Path

### Beginner (Using the App)
1. QUICK_START.md - Steps 1-2
2. Launch application
3. Follow on-screen instructions

### Intermediate (Understanding)
1. README.md - Full overview
2. QUICK_START.md - Complete guide
3. IMPLEMENTATION_SUMMARY.md - Architecture section

### Advanced (Development)
1. PIPEWIRE_ANALYSIS.md - Technical details
2. Source code review (.py files)
3. .github/copilot-instructions.md - Development guidelines

### Expert (Enhancement)
1. All documentation
2. Complete source code review
3. Add features from enhancement list

---

## 📞 Support Resources

| Need | Resource |
|------|----------|
| How to use | [QUICK_START.md](QUICK_START.md) |
| How it works | [PIPEWIRE_ANALYSIS.md](PIPEWIRE_ANALYSIS.md) |
| Installation | [README.md](README.md) |
| Architecture | [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) |
| What was done | [PROJECT_DELIVERY_SUMMARY.md](PROJECT_DELIVERY_SUMMARY.md) |
| Development | [.github/copilot-instructions.md](.github/copilot-instructions.md) |
| VS Code setup | [.vscode/tasks.json](.vscode/tasks.json) |

---

## ✅ Quality Checklist

- ✅ All Python files compile without errors
- ✅ Comprehensive documentation provided
- ✅ Type hints throughout codebase
- ✅ Error handling implemented
- ✅ GUI is responsive (background threading)
- ✅ Installation tested
- ✅ PipeWire integration verified with real game
- ✅ Configuration management functional
- ✅ VS Code integration configured
- ✅ Future enhancement roadmap included

---

**Last Updated**: December 17, 2025  
**Status**: ✅ Complete and Ready for Use
