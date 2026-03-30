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
LOCK_FILE_PATH = UPDATES_CACHE_DIR.parent / "steam-audio-isolator.lock"
RELEASE_ASSET_NAME = "steam-audio-isolator"
# GitHub Releases bundle (matches build-release.yml)
RELEASE_FLATPAK_ASSET = "steam-audio-isolator-x86_64.flatpak"


def _ssl_context():
    """SSL context using certifi's CA bundle when available (required for frozen/PyInstaller)."""
    _cafile = None
    try:
        import certifi
        _cafile = certifi.where()
    except Exception:
        pass
    if not _cafile or not os.path.isfile(_cafile):
        _mei = getattr(__import__("sys"), "_MEIPASS", None)
        if _mei:
            for _p in (os.path.join(_mei, "certifi", "cacert.pem"), os.path.join(_mei, "cacert.pem")):
                if os.path.isfile(_p):
                    _cafile = _p
                    break
    if _cafile and os.path.isfile(_cafile):
        return ssl.create_default_context(cafile=_cafile)
    return ssl.create_default_context()


def _parse_version(tag: str) -> Tuple[int, ...]:
    """Normalize version string to tuple for comparison. tag e.g. 'v0.2.0' or '0.2.0'."""
    s = tag.lstrip("v").strip()
    parts = re.findall(r"\d+", s)
    return tuple(int(p) for p in parts) if parts else (0,)


def is_frozen() -> bool:
    return getattr(__import__("sys"), "frozen", False)


def is_flatpak() -> bool:
    return bool(os.environ.get("FLATPAK_ID", "").strip())


def _fetch_url(url: str, timeout: int = 10, context: Optional[ssl.SSLContext] = None):
    """GET url with optional SSL context. On SSLError, returns (None, error_msg)."""
    ctx = context or _ssl_context()
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github.v3+json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return resp.read(), None
    except ssl.SSLError as e:
        return None, str(e)
    except urllib.error.URLError as e:
        return None, e.reason or str(e)
    except Exception as e:
        return None, str(e)


def check_for_updates(current_version: str) -> Tuple[bool, str, Optional[str], Optional[str], Optional[str]]:
    """
    Call GitHub Releases API and compare latest tag with current_version.

    Returns:
        (success, user_message, latest_tag_or_None, download_url_or_None, release_page_url_or_None).

    * **Frozen (one-file):** ``download_url`` is the ``steam-audio-isolator`` release asset when present.
    * **Flatpak:** compares the same GitHub tag to this build. Flathub does not expose a simple
      in-app API; after publishing there, users normally run ``flatpak update``. ``download_url``
      may point at ``steam-audio-isolator-x86_64.flatpak`` on the release for side-loading.
      ``release_page_url`` is the GitHub release HTML page (open in browser).
    """
    data_bytes, err = _fetch_url(GITHUB_RELEASES_API, timeout=10)
    if err and "certificate" in err.lower():
        # Fallback: retry without verification so user can still get updates
        try:
            unver = ssl._create_unverified_context()
            data_bytes, _ = _fetch_url(GITHUB_RELEASES_API, timeout=10, context=unver)
            if data_bytes:
                err = None
        except Exception:
            pass
    if err or not data_bytes:
        return False, f"Update check failed: {err or 'Unknown error'}", None, None, None
    try:
        data = json.loads(data_bytes.decode())
    except Exception as e:
        return False, f"Update check failed: {str(e)}", None, None, None

    tag = data.get("tag_name") or ""
    release_page = (data.get("html_url") or "").strip() or None
    assets = data.get("assets") or []
    download_url = None
    if is_flatpak():
        for a in assets:
            if a.get("name") == RELEASE_FLATPAK_ASSET:
                download_url = a.get("browser_download_url")
                break
    if download_url is None and not is_flatpak():
        for a in assets:
            if a.get("name") == RELEASE_ASSET_NAME:
                download_url = a.get("browser_download_url")
                break

    current_tup = _parse_version(current_version)
    latest_tup = _parse_version(tag)
    if latest_tup > current_tup:
        msg = f"Update available: {tag}"
        if is_flatpak():
            msg += (
                "\n\n• Installed from Flathub: run: flatpak update\n"
                "• GitHub bundle: use “Open release page” or install the .flatpak from that release."
            )
        return True, msg, tag, download_url, release_page
    if latest_tup <= current_tup:
        msg = "You have the latest version according to GitHub Releases."
        if is_flatpak():
            msg += "\n\nIf you use Flathub, you can still run: flatpak update"
        return True, msg, tag, None, release_page
    return True, "You have the latest version.", tag, None, release_page


def download_update(download_url: str) -> Tuple[bool, str]:
    """
    Download the release asset to UPDATES_NEW_BINARY. Run in a background thread.
    Returns (success, message).
    """
    try:
        UPDATES_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(download_url, headers={"Accept": "application/octet-stream"})
        data = None
        try:
            with urllib.request.urlopen(req, timeout=60, context=_ssl_context()) as resp:
                data = resp.read()
        except ssl.SSLError:
            with urllib.request.urlopen(req, timeout=60, context=ssl._create_unverified_context()) as resp:
                data = resp.read()
        if not data:
            return False, "Download failed (no data)."
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
    lock_arg = str(LOCK_FILE_PATH.resolve())
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", prefix="steam-audio-isolator-update-", suffix=".sh", delete=False
        ) as script:
            # Wait until the old process releases single-instance flock (closeEvent can take seconds).
            # Without this, the new binary often starts while the old PID still holds the lock and exits immediately.
            script.write(
                "#!/bin/sh\n"
                "set -e\n"
                "NEW=\"$1\"\n"
                "CUR=\"$2\"\n"
                "LOCK=\"$3\"\n"
                "mkdir -p \"$(dirname \"$LOCK\")\"\n"
                "exec 9>>\"$LOCK\"\n"
                "flock -w 120 9\n"
                "flock -u 9\n"
                "exec 9<&-\n"
                'cp "$NEW" "$CUR" && chmod 755 "$CUR"\n'
                "sync\n"
                'rm -f "$0"\n'
                'exec "$CUR"\n'
            )
        os.chmod(script.name, 0o755)
        # Spawn helper with a whitelisted env so exec'd binary gets a clean env and does fresh onefile extract.
        # Passing through PyInstaller/LD_* vars causes "Failed to load Python shared library" from wrong _MEI path.
        _safe = (
            "HOME", "USER", "LOGNAME", "PATH", "SHELL", "LANG", "LC_ALL", "LC_CTYPE",
            "DISPLAY", "WAYLAND_DISPLAY", "XDG_RUNTIME_DIR", "XDG_SESSION_TYPE",
            "DBUS_SESSION_BUS_ADDRESS", "XDG_CURRENT_DESKTOP", "XDG_SESSION_DESKTOP",
        )
        env = {k: os.environ[k] for k in _safe if k in os.environ}
        subprocess.Popen(
            ["/bin/sh", script.name, new_path, current_path, lock_arg],
            start_new_session=True,
            close_fds=True,
            env=env,
        )
        sys.exit(0)
    except Exception as e:
        return False, str(e)
    return True, ""
