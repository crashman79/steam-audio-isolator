"""Qt platform environment — must run before any PyQt5 import."""

from __future__ import annotations

import os


def apply_qt_platform_environment() -> None:
    """Tune Qt platform selection to avoid XCB + libxkbcommon SEGVs.

    On Wayland desktops Qt often defaults to the xcb plugin (XWayland). That
    path loads Qt5XcbQpa and libxkbcommon; with the PyInstaller-bundled stack
    this has been observed to segfault during keyboard / keymap setup. Prefer
    the native Wayland platform first; ``wayland;xcb`` falls back if the
    Wayland plugin cannot load.

    Honors ``QT_QPA_PLATFORM`` if already set. Set ``STEAM_AUDIO_FORCE_QT_XCB=1``
    to keep the default and skip Wayland preference (for debugging).

    Under Flatpak we do not override the platform plugin: the runtime and session
    (X11, Wayland, or XWayland) should choose without forcing ``wayland`` or ``xcb``.
    """
    try:
        from steam_pipewire.utils.config import is_flatpak_runtime

        if is_flatpak_runtime():
            return
    except Exception:
        if os.environ.get("FLATPAK_ID"):
            return
    if os.environ.get("QT_QPA_PLATFORM"):
        return
    force_xcb = os.environ.get("STEAM_AUDIO_FORCE_QT_XCB", "").strip().lower()
    if force_xcb in ("1", "true", "yes", "on"):
        return
    if not os.environ.get("WAYLAND_DISPLAY"):
        return
    os.environ["QT_QPA_PLATFORM"] = "wayland;xcb"
