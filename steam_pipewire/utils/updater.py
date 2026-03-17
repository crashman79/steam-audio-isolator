#!/usr/bin/env python3
"""Auto-update: check GitHub Releases, download new binary, updater-helper restart."""

import os
import re
import subprocess
import sys
import tempfile
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


def get_current_binary_path() -> Optional[Path]:
    """Current executable path when frozen; None when not frozen."""
    if not is_frozen():
        return None
    p = Path(__import__("sys").executable).resolve()
    return p if p.is_file() and os.access(p, os.X_OK) else None


def restart_to_apply() -> Tuple[bool, str]:
    """
    Spawn updater-helper script in a detached child process, then exit. The helper
    waits for this process to exit, copies .new over current binary, then exec's it.
    Returns (False, error_msg) on failure; on success we exit and never return.
    """
    if not is_frozen():
        return False, "Restart is only available when running the built binary."
    if not UPDATES_NEW_BINARY.exists():
        return False, "No downloaded update found."
    current = get_current_binary_path()
    if not current:
        return False, "Could not determine binary path."
    new_path = str(UPDATES_NEW_BINARY.resolve())
    current_path = str(current.resolve())
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", prefix="steam-audio-isolator-update-", suffix=".sh", delete=False
        ) as script:
            script.write(
                "#!/bin/sh\n"
                "sleep 1\n"
                'cp "$1" "$2" && chmod 755 "$2"\n'
                'rm -f "$0"\n'
                'exec "$2"\n'
            )
        os.chmod(script.name, 0o755)
        subprocess.Popen(
            ["/bin/sh", script.name, new_path, current_path],
            start_new_session=True,
            close_fds=True,
        )
        sys.exit(0)
    except Exception as e:
        return False, str(e)
    return True, ""
