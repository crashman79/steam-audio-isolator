"""Tests for source_detector module"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from steam_pipewire.pipewire.source_detector import SourceDetector


class TestSourceDetector:
    """Test SourceDetector class"""

    def test_init(self):
        """Test SourceDetector initialization"""
        detector = SourceDetector()
        assert detector.sources == []
        assert detector.node_map == {}
        assert detector._cache is None

    @patch('subprocess.run')
    def test_get_audio_sources_success(self, mock_run, mock_pw_dump_data):
        """Test successful audio source detection"""
        # Mock subprocess to return our test data
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps(mock_pw_dump_data)
        )

        detector = SourceDetector()
        sources = detector.get_audio_sources()

        # Should have found game, Discord, Vivaldi, and Steam runtime game (excluding steamwebhelper)
        assert len(sources) >= 4
        
        # Check that sources have required fields
        for source in sources:
            assert 'id' in source
            assert 'name' in source
            assert 'type' in source
            assert source['type'] in ['Game', 'Browser', 'Communication', 'System', 'Application']

    @patch('subprocess.run')
    def test_get_audio_sources_caching(self, mock_run, mock_pw_dump_data):
        """Test that sources are cached properly"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps(mock_pw_dump_data)
        )

        detector = SourceDetector()
        
        # First call should hit subprocess
        sources1 = detector.get_audio_sources()
        assert mock_run.call_count == 1
        
        # Second call within cache duration should use cache
        sources2 = detector.get_audio_sources()
        assert mock_run.call_count == 1  # Should not call again
        assert sources1 == sources2

    @patch('subprocess.run')
    def test_get_audio_sources_timeout(self, mock_run):
        """Test handling of pw-dump timeout"""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired('pw-dump', 2)

        detector = SourceDetector()
        sources = detector.get_audio_sources()
        
        assert sources == []

    @patch('subprocess.run')
    def test_get_audio_sources_invalid_json(self, mock_run):
        """Test handling of invalid JSON from pw-dump"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="invalid json {{"
        )

        detector = SourceDetector()
        sources = detector.get_audio_sources()
        
        assert sources == []

    def test_determine_source_type_game_wine(self):
        """Test game detection for Wine/Proton games"""
        detector = SourceDetector()
        
        # Wine game
        props = {
            "application.name": "game.exe",
            "application.process.binary": "wine64-preloader",
            "node.name": "game.exe"
        }
        assert detector._determine_source_type(props) == "Game"
        
        # Proton game
        props = {
            "application.name": "Steam Game",
            "application.process.binary": "proton",
            "node.name": "game"
        }
        assert detector._determine_source_type(props) == "Game"

    def test_determine_source_type_game_steam_runtime(self):
        """Test game detection for Steam runtime containers"""
        detector = SourceDetector()
        
        props = {
            "application.name": "pressure-vessel-wrap",
            "application.process.binary": "game.x86_64",
            "node.name": "SteamGame"
        }
        assert detector._determine_source_type(props) == "Game"

    def test_determine_source_type_game_native(self):
        """Test game detection for native Linux games"""
        detector = SourceDetector()
        
        # Native game with .x86_64 extension
        props = {
            "application.name": "NativeGame",
            "application.process.binary": "game.x86_64",
            "node.name": "game",
            "application.process.id": "12345",
            "pipewire.access.portal.app_id": "/steamapps/common/game"
        }
        assert detector._determine_source_type(props) == "Game"

    def test_determine_source_type_discord(self):
        """Test Discord detection (Electron app with Discord binary)"""
        detector = SourceDetector()
        
        # Discord appears as Chromium but binary is Discord
        props = {
            "application.name": "Chromium",
            "application.process.binary": "Discord",
            "node.name": "Chromium"
        }
        assert detector._determine_source_type(props) == "Communication"
        
        # WEBRTC VoiceEngine with Discord binary
        props = {
            "application.name": "WEBRTC VoiceEngine",
            "application.process.binary": "Discord",
            "node.name": "WEBRTC VoiceEngine"
        }
        assert detector._determine_source_type(props) == "Communication"

    def test_determine_source_type_vivaldi(self):
        """Test Vivaldi browser detection"""
        detector = SourceDetector()
        
        props = {
            "application.name": "Vivaldi",
            "application.process.binary": "vivaldi-bin",
            "node.name": "Vivaldi"
        }
        assert detector._determine_source_type(props) == "Browser"

    def test_determine_source_type_firefox(self):
        """Test Firefox browser detection"""
        detector = SourceDetector()
        
        props = {
            "application.name": "Firefox",
            "application.process.binary": "firefox",
            "node.name": "AudioStream"
        }
        assert detector._determine_source_type(props) == "Browser"

    def test_determine_source_type_system(self):
        """Test system audio detection"""
        detector = SourceDetector()
        
        props = {
            "node.name": "alsa_output.pci-0000_00_1f.3.analog-stereo",
            "media.class": "Audio/Sink"
        }
        assert detector._determine_source_type(props) == "System"

    def test_is_internal_node_steamwebhelper(self):
        """Test that steamwebhelper is filtered out"""
        detector = SourceDetector()
        
        props = {
            "application.name": "steamwebhelper",
            "application.process.binary": "steamwebhelper",
            "node.name": "steamwebhelper"
        }
        assert detector._is_internal_node(props) is True

    def test_is_internal_node_gameoverlayui(self):
        """Test that gameoverlayui is filtered out"""
        detector = SourceDetector()
        
        props = {
            "application.name": "gameoverlayui",
            "application.process.binary": "gameoverlayui",
            "node.name": "gameoverlayui"
        }
        assert detector._is_internal_node(props) is True

    def test_is_internal_node_echo_cancel(self):
        """Test that echo-cancel nodes are filtered out"""
        detector = SourceDetector()
        
        props = {
            "node.name": "echo-cancel-source",
            "application.name": "PipeWire"
        }
        assert detector._is_internal_node(props) is True

    def test_is_internal_node_regular_app(self):
        """Test that regular apps are not filtered"""
        detector = SourceDetector()
        
        props = {
            "application.name": "Spotify",
            "application.process.binary": "spotify",
            "node.name": "Spotify"
        }
        assert detector._is_internal_node(props) is False

    @patch('subprocess.run')
    def test_find_steam_node(self, mock_run, mock_pw_dump_data):
        """Test finding Steam recording node"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps(mock_pw_dump_data)
        )

        detector = SourceDetector()
        steam_id = detector.find_steam_node()
        
        assert steam_id == 154

    @patch('subprocess.run')
    def test_find_steam_node_not_found(self, mock_run):
        """Test when Steam node is not found"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps([])
        )

        detector = SourceDetector()
        steam_id = detector.find_steam_node()
        
        assert steam_id is None

    def test_get_node_info(self):
        """Test getting cached node info"""
        detector = SourceDetector()
        detector.node_map = {
            137: {
                "id": 137,
                "info": {
                    "props": {
                        "application.name": "TestApp",
                        "node.name": "test"
                    }
                }
            }
        }
        
        info = detector.get_node_info(137)
        assert info is not None
        assert info["id"] == 137
        
        # Non-existent node
        info = detector.get_node_info(999)
        assert info is None
