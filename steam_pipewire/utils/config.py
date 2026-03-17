#!/usr/bin/env python3
"""Configuration management for Steam Audio Isolator"""

import json
import os
import shutil
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Any, List, Optional


@dataclass
class AppSettings:
    """Application settings with type safety and defaults"""
    restore_default_on_close: bool = True
    prompt_on_close: bool = True
    auto_detect_interval: int = 3  # seconds
    preferred_sink: Optional[str] = None
    excluded_games: List[str] = field(default_factory=list)
    auto_apply_games: bool = True
    minimize_to_tray: bool = True
    theme: str = "system"  # light, dark, or system
    start_minimized_to_tray: bool = False
    start_at_login: bool = False
    add_to_app_menu: bool = False
    install_prompt_shown: bool = False

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
        self.autostart_dir = Path.home() / '.config' / 'autostart'
        self.autostart_desktop_path = self.autostart_dir / 'steam-audio-isolator.desktop'
        self.applications_dir = Path.home() / '.local' / 'share' / 'applications'
        self.desktop_entry_path = self.applications_dir / 'steam-audio-isolator.desktop'
        self.install_bin_dir = Path.home() / '.local' / 'bin'
        self.install_bin_path = self.install_bin_dir / 'steam-audio-isolator'
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
        if default is not None:
            return settings.get(key, default)
        defaults = self._default_settings.to_dict()
        return settings.get(key, defaults.get(key))

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
            if not filename.endswith('.pwp'):
                filepath = filepath.with_suffix('.pwp')
            
            if not filepath.exists():
                raise FileNotFoundError(f"Profile not found: {filepath}")

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

    def is_frozen(self) -> bool:
        """Return True when running as PyInstaller binary."""
        return getattr(sys, 'frozen', False)

    def is_running_from_local_bin(self) -> bool:
        """Return True when the running binary is already in ~/.local/bin."""
        if not self.is_frozen():
            return False
        try:
            return Path(sys.executable).resolve() == self.install_bin_path.resolve()
        except Exception:
            return False

    def ensure_installed_to_local_bin(self, exec_path: str) -> str:
        """When running as frozen binary, copy self to ~/.local/bin and return that path.
        Desktop/autostart then use a path without spaces. When not frozen, return exec_path unchanged.
        """
        if not exec_path or not self.is_frozen():
            return exec_path
        try:
            self.install_bin_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(sys.executable, self.install_bin_path)
            self.install_bin_path.chmod(0o755)
            return str(self.install_bin_path)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Could not install to ~/.local/bin: {e}, using current path")
            return exec_path

    def install_to_local_bin(self) -> tuple[bool, str]:
        """Copy the running binary to ~/.local/bin/steam-audio-isolator. Returns (success, message)."""
        if not self.is_frozen():
            return False, "Only available when running the standalone binary."
        try:
            self.install_bin_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(sys.executable, self.install_bin_path)
            self.install_bin_path.chmod(0o755)
            return True, f"Installed to {self.install_bin_path}"
        except Exception as e:
            return False, str(e)

    def _quote_exec(self, exec_path: str) -> str:
        """Quote Exec value if it contains spaces (desktop entry spec)."""
        if " " in exec_path.strip():
            return f'"{exec_path}"'
        return exec_path

    def get_autostart_desktop_content(self, exec_path: str, icon_path: Optional[str] = None) -> str:
        """Return desktop file content for XDG autostart."""
        exec_val = self._quote_exec(exec_path)
        icon_line = f"Icon={icon_path}\n" if icon_path else "Icon=steam-audio-isolator\n"
        return (
            "[Desktop Entry]\n"
            "Type=Application\n"
            "Name=Steam Audio Isolator\n"
            "Comment=Isolate game audio for clean Steam game recording\n"
            f"Exec={exec_val}\n"
            f"{icon_line}"
            "Terminal=false\n"
            "X-GNOME-Autostart-enabled=true\n"
        )

    def enable_autostart(self, exec_path: str, icon_path: Optional[str] = None) -> tuple[bool, str]:
        """Create autostart desktop file so app starts at login. Returns (success, message)."""
        if not exec_path or not exec_path.strip():
            return False, "No executable path available (run from installed binary or use Copy to ~/.local/bin first)."
        try:
            exec_path = self.ensure_installed_to_local_bin(exec_path)
            self.autostart_dir.mkdir(parents=True, exist_ok=True)
            self.autostart_desktop_path.write_text(
                self.get_autostart_desktop_content(exec_path, icon_path),
                encoding='utf-8'
            )
            return True, str(self.autostart_desktop_path)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error enabling autostart: {e}")
            return False, str(e)

    def disable_autostart(self) -> bool:
        """Remove autostart desktop file."""
        try:
            if self.autostart_desktop_path.exists():
                self.autostart_desktop_path.unlink()
                return True
            return True
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error disabling autostart: {e}")
            return False

    def is_autostart_enabled(self) -> bool:
        """Return whether autostart desktop file exists."""
        return self.autostart_desktop_path.exists()

    def get_desktop_entry_content(self, exec_path: str, icon_path: Optional[str] = None) -> str:
        """Return desktop file content for application menu."""
        exec_val = self._quote_exec(exec_path)
        icon_line = f"Icon={icon_path}\n" if icon_path else "Icon=steam-audio-isolator\n"
        return (
            "[Desktop Entry]\n"
            "Version=1.0\n"
            "Type=Application\n"
            "Name=Steam Audio Isolator\n"
            "Comment=Isolate game audio for clean Steam game recording\n"
            f"Exec={exec_val}\n"
            f"{icon_line}"
            "Terminal=false\n"
            "Categories=Audio;Utility;\n"
            "StartupNotify=true\n"
        )

    def enable_desktop_entry(self, exec_path: str, icon_path: Optional[str] = None) -> tuple[bool, str]:
        """Create desktop entry so app appears in application menu. Returns (success, message)."""
        if not exec_path or not exec_path.strip():
            return False, "No executable path available (run from installed binary or use Copy to ~/.local/bin first)."
        try:
            exec_path = self.ensure_installed_to_local_bin(exec_path)
            self.applications_dir.mkdir(parents=True, exist_ok=True)
            self.desktop_entry_path.write_text(
                self.get_desktop_entry_content(exec_path, icon_path),
                encoding='utf-8'
            )
            return True, str(self.desktop_entry_path)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error enabling desktop entry: {e}")
            return False, str(e)

    def disable_desktop_entry(self) -> bool:
        """Remove desktop entry from application menu."""
        try:
            if self.desktop_entry_path.exists():
                self.desktop_entry_path.unlink()
                return True
            return True
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error disabling desktop entry: {e}")
            return False

    def is_desktop_entry_enabled(self) -> bool:
        """Return whether application menu desktop file exists."""
        return self.desktop_entry_path.exists()