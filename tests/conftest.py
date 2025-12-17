"""Pytest configuration and fixtures"""

import pytest
import json
from pathlib import Path
from typing import Dict, List


@pytest.fixture
def mock_pw_dump_data():
    """Sample pw-dump data for testing"""
    return [
        {
            "id": 137,
            "type": "PipeWire:Interface:Node",
            "info": {
                "props": {
                    "application.name": "Duckov.exe",
                    "application.process.binary": "wine64-preloader",
                    "node.name": "Duckov.exe",
                    "media.class": "Stream/Output/Audio",
                    "node.description": "Duckov Game Audio"
                }
            }
        },
        {
            "id": 154,
            "type": "PipeWire:Interface:Node",
            "info": {
                "props": {
                    "application.name": "Steam",
                    "application.process.binary": "steam",
                    "node.name": "Steam",
                    "media.class": "Stream/Input/Audio",
                    "node.description": "Steam Game Recording"
                }
            }
        },
        {
            "id": 200,
            "type": "PipeWire:Interface:Node",
            "info": {
                "props": {
                    "application.name": "Chromium",
                    "application.process.binary": "Discord",
                    "node.name": "Chromium",
                    "media.class": "Stream/Output/Audio",
                    "node.description": "Discord Audio"
                }
            }
        },
        {
            "id": 201,
            "type": "PipeWire:Interface:Node",
            "info": {
                "props": {
                    "application.name": "WEBRTC VoiceEngine",
                    "application.process.binary": "Discord",
                    "node.name": "WEBRTC VoiceEngine",
                    "media.class": "Stream/Output/Audio",
                    "node.description": "Discord Voice"
                }
            }
        },
        {
            "id": 210,
            "type": "PipeWire:Interface:Node",
            "info": {
                "props": {
                    "application.name": "Vivaldi",
                    "application.process.binary": "vivaldi-bin",
                    "node.name": "Vivaldi",
                    "media.class": "Stream/Output/Audio",
                    "node.description": "Vivaldi Browser"
                }
            }
        },
        {
            "id": 220,
            "type": "PipeWire:Interface:Node",
            "info": {
                "props": {
                    "application.name": "pressure-vessel-wrap",
                    "application.process.binary": "game-binary.x86_64",
                    "node.name": "SteamGame",
                    "media.class": "Stream/Output/Audio",
                    "application.process.id": "12345",
                    "pipewire.access.portal.app_id": "com.valvesoftware.Steam.app123456"
                }
            }
        },
        {
            "id": 66,
            "type": "PipeWire:Interface:Node",
            "info": {
                "props": {
                    "node.name": "alsa_output.pci-0000_00_1f.3.analog-stereo",
                    "media.class": "Audio/Sink",
                    "node.description": "Built-in Audio"
                }
            }
        },
        {
            "id": 300,
            "type": "PipeWire:Interface:Node",
            "info": {
                "props": {
                    "application.name": "steamwebhelper",
                    "application.process.binary": "steamwebhelper",
                    "node.name": "steamwebhelper",
                    "media.class": "Stream/Output/Audio"
                }
            }
        }
    ]


@pytest.fixture
def mock_config_dir(tmp_path):
    """Temporary config directory for testing"""
    config_dir = tmp_path / ".config" / "steam-audio-isolator"
    config_dir.mkdir(parents=True)
    profiles_dir = config_dir / "profiles"
    profiles_dir.mkdir()
    return config_dir


@pytest.fixture
def sample_profile():
    """Sample profile data"""
    return {
        "name": "Test Profile",
        "enabled_sources": [137, 200],
        "steam_node_id": 154,
        "created_at": "2024-01-01T00:00:00"
    }


@pytest.fixture
def sample_settings():
    """Sample application settings"""
    return {
        "restore_default_on_close": True,
        "auto_detect_interval": 3,
        "preferred_sink": None,
        "excluded_games": ["steamwebhelper"],
        "auto_apply_games": True,
        "minimize_to_tray": True,
        "shortcuts": {
            "apply_routing": "Ctrl+Shift+A",
            "clear_routes": "Ctrl+Shift+C",
            "refresh_sources": "F5",
            "toggle_window": "Ctrl+Shift+H"
        }
    }
