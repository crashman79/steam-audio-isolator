#!/usr/bin/env python3
"""Configuration management for Steam Audio Isolator"""

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Any, List, Optional


@dataclass
class AppSettings:
    """Application settings with type safety and defaults"""
    restore_default_on_close: bool = True
    auto_detect_interval: int = 3  # seconds
    preferred_sink: Optional[str] = None
    excluded_games: List[str] = field(default_factory=list)
    auto_apply_games: bool = True
    minimize_to_tray: bool = True
    shortcuts: Dict[str, str] = field(default_factory=lambda: {
        'apply_routing': 'Ctrl+Shift+A',
        'clear_routes': 'Ctrl+Shift+C',
        'refresh_sources': 'F5',
        'toggle_window': 'Ctrl+Shift+H'
    })
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AppSettings':
        """Create from dictionary, ignoring unknown keys"""
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered_data)


class ConfigManager:
    """Manage application configuration and profiles"""

    def __init__(self):
        self.config_dir = Path.home() / '.config' / 'steam-audio-isolator'
        self.profiles_dir = self.config_dir / 'profiles'
        self.settings_file = self.config_dir / 'settings.json'
        self._ensure_dirs()
        self._default_settings = AppSettings()

    def _ensure_dirs(self):
        """Ensure configuration directories exist"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.profiles_dir.mkdir(parents=True, exist_ok=True)

    def load_settings(self) -> Dict[str, Any]:
        """Load application settings, with defaults if not set"""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r') as f:
                    settings_data = json.load(f)
                    settings = AppSettings.from_dict(settings_data)
                    return settings.to_dict()
            else:
                return self._default_settings.to_dict()
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            return self._default_settings.to_dict()

    def save_settings(self, settings: Dict[str, Any]) -> bool:
        """Save application settings"""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # Validate settings through dataclass
            settings_obj = AppSettings.from_dict(settings)
            with open(self.settings_file, 'w') as f:
                json.dump(settings_obj.to_dict(), f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            return False

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a single setting value"""
        settings = self.load_settings()
        return settings.get(key, default if default is not None else self._default_settings.get(key))

    def set_setting(self, key: str, value: Any) -> bool:
        """Set a single setting value"""
        settings = self.load_settings()
        settings[key] = value
        return self.save_settings(settings)

    def save_profile(self, filename: str, profile_data: Dict[str, Any]) -> bool:
        """Save a configuration profile"""
        try:
            filepath = self.profiles_dir / filename
            if not filename.endswith('.pwp'):
                filepath = filepath.with_suffix('.pwp')

            with open(filepath, 'w') as f:
                json.dump(profile_data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving profile: {e}")
            raise

    def load_profile(self, filename: str) -> Dict[str, Any]:
        """Load a configuration profile"""
        try:
            filepath = self.profiles_dir / filename
            if not filepath.exists():
                filepath = Path(filename)

            with open(filepath, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading profile: {e}")
            raise

    def list_profiles(self) -> list:
        """List all saved profiles"""
        try:
            profiles = []
            for profile_file in self.profiles_dir.glob('*.pwp'):
                profiles.append(profile_file.stem)
            return profiles
        except Exception as e:
            print(f"Error listing profiles: {e}")
            return []

    def delete_profile(self, filename: str) -> bool:
        """Delete a saved profile"""
        try:
            filepath = self.profiles_dir / filename
            if not filepath.exists():
                filepath = filepath.with_suffix('.pwp')

            if filepath.exists():
                filepath.unlink()
                return True
            return False
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error deleting profile: {e}")
            raise
    
    def get_excluded_games(self) -> list:
        """Get list of excluded game names"""
        return self.get_setting('excluded_games', [])

    def add_excluded_game(self, game_name: str) -> bool:
        """Add a game to the exclusion list"""
        excluded = self.get_excluded_games()
        if game_name not in excluded:
            excluded.append(game_name)
            return self.set_setting('excluded_games', excluded)
        return True

    def remove_excluded_game(self, game_name: str) -> bool:
        """Remove a game from the exclusion list"""
        excluded = self.get_excluded_games()
        if game_name in excluded:
            excluded.remove(game_name)
            return self.set_setting('excluded_games', excluded)
        return True