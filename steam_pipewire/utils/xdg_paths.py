from __future__ import annotations

import os
from pathlib import Path


def _xdg_home(env_key: str, fallback_suffix: str) -> Path:
    """
    Return an XDG base dir from environment or a sane fallback under $HOME.

    fallback_suffix examples:
      - ".config"
      - ".cache"
      - ".local/share"
    """
    v = (os.environ.get(env_key) or "").strip()
    if v:
        return Path(v).expanduser()
    return Path.home() / fallback_suffix


def xdg_config_home() -> Path:
    return _xdg_home("XDG_CONFIG_HOME", ".config")


def xdg_cache_home() -> Path:
    return _xdg_home("XDG_CACHE_HOME", ".cache")


def xdg_data_home() -> Path:
    return _xdg_home("XDG_DATA_HOME", ".local/share")


def app_config_dir(app_name: str = "steam-audio-isolator") -> Path:
    return xdg_config_home() / app_name


def app_cache_dir(app_name: str = "steam-audio-isolator") -> Path:
    return xdg_cache_home() / app_name


def app_data_dir(app_name: str = "steam-audio-isolator") -> Path:
    return xdg_data_home() / app_name

