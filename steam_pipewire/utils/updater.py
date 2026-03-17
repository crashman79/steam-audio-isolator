#!/usr/bin/env python3
"""Auto-update: check GitHub Releases, download new binary, replace-and-run."""

import re
import urllib.request
import urllib.error
import json
import ssl
from pathlib import Path
from typing import Tuple, Optional

# Configurable constants
GITHUB_RELEASES_API = "https://api.github.com/repos/crashman79/steam-audio-isolator/releases/latest"
UPDATES_CACHE_DIR = Path.home() / ".cache" / "steam-audio-isolator"
UPDATES_NEW_BINARY = UPDATES_CACHE_DIR / "steam-audio-isolator.new"
RELEASE_ASSET_NAME = "steam-audio-isolator"


def _parse_version(tag: str) -> Tuple[int, ...]:
    """Normalize version string to tuple for comparison. tag e.g. 'v0.2.0' or '0.2.0'."""
    s = tag.lstrip("v").strip()
    parts = re.findall(r"\d+", s)
    return tuple(int(p) for p in parts) if parts else (0,)


def is_frozen() -> bool:
    return getattr(__import__("sys"), "frozen", False)


def check_for_updates(current_version: str) -> Tuple[bool, str, Optional[str], Optional[str]]:
    """
    Call GitHub Releases API and compare latest tag with current_version.
    Returns (success, user_message, latest_tag_or_None, download_url_or_None).
    """
    try:
        req = urllib.request.Request(
            GITHUB_RELEASES_API,
            headers={"Accept": "application/vnd.github.v3+json"},
        )
        with urllib.request.urlopen(req, timeout=10, context=ssl.create_default_context()) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.URLError as e:
        return False, f"Update check failed: {e.reason}", None, None
    except Exception as e:
        return False, f"Update check failed: {str(e)}", None, None

    tag = data.get("tag_name") or ""
    assets = data.get("assets") or []
    download_url = None
    for a in assets:
        if a.get("name") == RELEASE_ASSET_NAME:
            download_url = a.get("browser_download_url")
            break

    current_tup = _parse_version(current_version)
    latest_tup = _parse_version(tag)
    if latest_tup > current_tup:
        return True, f"Update available: {tag}", tag, download_url
    if latest_tup <= current_tup:
        return True, "You have the latest version.", tag, None
    return True, "You have the latest version.", tag, None


def download_update(download_url: str) -> Tuple[bool, str]:
    """
    Download the release asset to UPDATES_NEW_BINARY. Run in a background thread.
    Returns (success, message).
    """
    try:
        UPDATES_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(
            download_url,
            headers={"Accept": "application/octet-stream"},
        )
        with urllib.request.urlopen(req, timeout=60, context=ssl.create_default_context()) as resp:
            data = resp.read()
        UPDATES_NEW_BINARY.write_bytes(data)
        UPDATES_NEW_BINARY.chmod(0o755)
        return True, "Update downloaded. Restart to apply."
    except Exception as e:
        return False, str(e)


def has_pending_update() -> bool:
    """True if the .new binary exists and we can restart to apply."""
    return is_frozen() and UPDATES_NEW_BINARY.exists()


def get_current_binary_path() -> Optional[str]:
    """Current executable path when frozen; None when not frozen."""
    if not is_frozen():
        return None
    return __import__("sys").executable


def restart_to_apply() -> bool:
    """
    Run the .new binary with --replace-and-run <current_binary>, then exit.
    Returns True if execv was attempted (caller should exit); False if not possible.
    """
    if not is_frozen():
        return False
    if not UPDATES_NEW_BINARY.exists():
        return False
    current = get_current_binary_path()
    if not current:
        return False
    try:
        os = __import__("os")
        os.execv(
            str(UPDATES_NEW_BINARY),
            [str(UPDATES_NEW_BINARY), "--replace-and-run", current],
        )
    except Exception:
        return False
    return True
