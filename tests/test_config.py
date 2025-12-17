"""Tests for config module"""

import pytest
import json
from pathlib import Path
from steam_pipewire.utils.config import ConfigManager, AppSettings


class TestAppSettings:
    """Test AppSettings dataclass"""

    def test_default_settings(self):
        """Test default settings initialization"""
        settings = AppSettings()
        
        assert settings.restore_default_on_close is True
        assert settings.auto_detect_interval == 3
        assert settings.preferred_sink is None
        assert settings.excluded_games == []
        assert settings.auto_apply_games is True
        assert settings.minimize_to_tray is True
        assert 'apply_routing' in settings.shortcuts

    def test_to_dict(self):
        """Test converting settings to dictionary"""
        settings = AppSettings(
            restore_default_on_close=False,
            auto_detect_interval=5
        )
        
        data = settings.to_dict()
        
        assert isinstance(data, dict)
        assert data['restore_default_on_close'] is False
        assert data['auto_detect_interval'] == 5

    def test_from_dict(self):
        """Test creating settings from dictionary"""
        data = {
            'restore_default_on_close': False,
            'auto_detect_interval': 10,
            'unknown_field': 'should be ignored'
        }
        
        settings = AppSettings.from_dict(data)
        
        assert settings.restore_default_on_close is False
        assert settings.auto_detect_interval == 10
        # Unknown field should be ignored
        assert not hasattr(settings, 'unknown_field')

    def test_custom_shortcuts(self):
        """Test custom keyboard shortcuts"""
        settings = AppSettings(
            shortcuts={
                'apply_routing': 'Alt+A',
                'clear_routes': 'Alt+C'
            }
        )
        
        assert settings.shortcuts['apply_routing'] == 'Alt+A'
        assert settings.shortcuts['clear_routes'] == 'Alt+C'


class TestConfigManager:
    """Test ConfigManager class"""

    def test_init(self, tmp_path, monkeypatch):
        """Test ConfigManager initialization"""
        # Use temporary directory instead of ~/.config
        config_dir = tmp_path / ".config" / "steam-audio-isolator"
        monkeypatch.setattr(Path, 'home', lambda: tmp_path)
        
        manager = ConfigManager()
        
        assert manager.config_dir.exists()
        assert manager.profiles_dir.exists()

    def test_load_settings_default(self, tmp_path, monkeypatch):
        """Test loading default settings when file doesn't exist"""
        monkeypatch.setattr(Path, 'home', lambda: tmp_path)
        
        manager = ConfigManager()
        settings = manager.load_settings()
        
        assert isinstance(settings, dict)
        assert settings['restore_default_on_close'] is True
        assert settings['auto_detect_interval'] == 3

    def test_save_and_load_settings(self, tmp_path, monkeypatch):
        """Test saving and loading settings"""
        monkeypatch.setattr(Path, 'home', lambda: tmp_path)
        
        manager = ConfigManager()
        
        # Save custom settings
        custom_settings = {
            'restore_default_on_close': False,
            'auto_detect_interval': 10,
            'excluded_games': ['steamwebhelper', 'test.exe']
        }
        
        success = manager.save_settings(custom_settings)
        assert success is True
        
        # Load settings back
        loaded = manager.load_settings()
        assert loaded['restore_default_on_close'] is False
        assert loaded['auto_detect_interval'] == 10
        assert 'steamwebhelper' in loaded['excluded_games']

    def test_save_profile(self, tmp_path, monkeypatch, sample_profile):
        """Test saving a routing profile"""
        monkeypatch.setattr(Path, 'home', lambda: tmp_path)
        
        manager = ConfigManager()
        
        success = manager.save_profile("test_profile", sample_profile)
        assert success is True
        
        # Verify file exists
        profile_file = manager.profiles_dir / "test_profile.json"
        assert profile_file.exists()

    def test_load_profile(self, tmp_path, monkeypatch, sample_profile):
        """Test loading a routing profile"""
        monkeypatch.setattr(Path, 'home', lambda: tmp_path)
        
        manager = ConfigManager()
        
        # Save profile first
        manager.save_profile("test_profile", sample_profile)
        
        # Load it back
        loaded = manager.load_profile("test_profile")
        
        assert loaded is not None
        assert loaded['name'] == "Test Profile"
        assert 137 in loaded['enabled_sources']

    def test_load_profile_not_found(self, tmp_path, monkeypatch):
        """Test loading non-existent profile"""
        monkeypatch.setattr(Path, 'home', lambda: tmp_path)
        
        manager = ConfigManager()
        loaded = manager.load_profile("nonexistent")
        
        assert loaded is None

    def test_list_profiles(self, tmp_path, monkeypatch, sample_profile):
        """Test listing available profiles"""
        monkeypatch.setattr(Path, 'home', lambda: tmp_path)
        
        manager = ConfigManager()
        
        # Save multiple profiles
        manager.save_profile("profile1", sample_profile)
        manager.save_profile("profile2", sample_profile)
        
        profiles = manager.list_profiles()
        
        assert len(profiles) >= 2
        assert "profile1" in profiles
        assert "profile2" in profiles

    def test_delete_profile(self, tmp_path, monkeypatch, sample_profile):
        """Test deleting a profile"""
        monkeypatch.setattr(Path, 'home', lambda: tmp_path)
        
        manager = ConfigManager()
        
        # Save and then delete
        manager.save_profile("to_delete", sample_profile)
        assert "to_delete" in manager.list_profiles()
        
        success = manager.delete_profile("to_delete")
        assert success is True
        assert "to_delete" not in manager.list_profiles()

    def test_delete_profile_not_found(self, tmp_path, monkeypatch):
        """Test deleting non-existent profile"""
        monkeypatch.setattr(Path, 'home', lambda: tmp_path)
        
        manager = ConfigManager()
        success = manager.delete_profile("nonexistent")
        
        # Should return True (nothing to delete)
        assert success is True

    def test_settings_validation(self, tmp_path, monkeypatch):
        """Test that invalid settings are handled gracefully"""
        monkeypatch.setattr(Path, 'home', lambda: tmp_path)
        
        manager = ConfigManager()
        
        # Try to save settings with invalid type
        invalid_settings = {
            'restore_default_on_close': "not a boolean",
            'auto_detect_interval': "not an integer"
        }
        
        # Should not crash, but may fail validation
        try:
            manager.save_settings(invalid_settings)
        except (TypeError, ValueError):
            pass  # Expected to fail validation

    def test_profile_with_metadata(self, tmp_path, monkeypatch):
        """Test profile with additional metadata"""
        monkeypatch.setattr(Path, 'home', lambda: tmp_path)
        
        manager = ConfigManager()
        
        profile = {
            'name': 'Gaming Setup',
            'enabled_sources': [137, 200],
            'steam_node_id': 154,
            'created_at': '2024-01-01',
            'description': 'My favorite gaming audio setup',
            'tags': ['gaming', 'discord']
        }
        
        manager.save_profile("gaming", profile)
        loaded = manager.load_profile("gaming")
        
        assert loaded['name'] == 'Gaming Setup'
        assert loaded['description'] == 'My favorite gaming audio setup'
        assert 'gaming' in loaded['tags']
