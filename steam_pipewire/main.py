#!/usr/bin/env python3
"""Main entry point for Steam Audio Isolator application"""

import sys
import os
from pathlib import Path

from steam_pipewire.utils.xdg_paths import app_cache_dir

# --- Stale update cleanup: when running as built binary (and not from .new), remove leftover .new file ---
if getattr(sys, "frozen", False):
    new_path = app_cache_dir("steam-audio-isolator") / "steam-audio-isolator.new"
    if new_path.exists() and Path(sys.executable).resolve() != new_path.resolve():
        try:
            new_path.unlink()
        except Exception:
            pass

from steam_pipewire.qt_env import apply_qt_platform_environment

apply_qt_platform_environment()

# --- Normal imports and startup ---
import logging
import traceback
import fcntl
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QTimer
from steam_pipewire.ui.main_window import MainWindow
from steam_pipewire.ui.theme import ThemeManager, Theme
from steam_pipewire.utils.config import ConfigManager, flatpak_app_id


# Set up logging
log_file = app_cache_dir("steam-audio-isolator") / "steam-audio-isolator.log"
log_file.parent.mkdir(parents=True, exist_ok=True)

# File handler with DEBUG, console with INFO only
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[file_handler, console_handler]
)
logger = logging.getLogger(__name__)
logger.debug(
    "QT_QPA_PLATFORM=%s",
    os.environ.get("QT_QPA_PLATFORM", "(unset, Qt default)"),
)


def _install_excepthook():
    """Log uncaught exceptions and show a dialog when a QApplication exists (desktop launches hide stderr)."""

    def _hook(exc_type, exc_value, exc_tb):
        logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_tb))
        try:
            app = QApplication.instance()
            if app is not None:
                QMessageBox.critical(
                    None,
                    "Steam Audio Isolator",
                    f"Unexpected error:\n\n{exc_value}\n\n"
                    f"Details were written to:\n{log_file}",
                )
        except Exception:
            pass
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = _hook


def get_autostart_exec_path() -> str:
    """Return the command used to start this app (for autostart desktop file)."""
    if getattr(sys, 'frozen', False):
        return sys.executable
    aid = flatpak_app_id()
    if aid:
        return f"flatpak run {aid}"
    launcher = os.environ.get("STEAM_AUDIO_ISOLATOR_LAUNCHER", "").strip()
    if launcher and os.path.isfile(launcher) and os.access(launcher, os.X_OK):
        return launcher
    return f"{sys.executable} -m steam_pipewire.main"


def acquire_lock():
    """Acquire an exclusive lock to ensure only one instance runs.
    
    Returns the lock file object if successful, None if another instance is running.
    """
    lock_dir = app_cache_dir("steam-audio-isolator")
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_file_path = lock_dir / "steam-audio-isolator.lock"
    
    try:
        lock_file = open(lock_file_path, 'w')
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_file.write(str(os.getpid()))
        lock_file.flush()
        logger.info(f"Lock acquired successfully (PID: {os.getpid()})")
        return lock_file
    except IOError:
        logger.warning("Another instance of Steam Audio Isolator is already running")
        return None


def main():
    """Launch the application"""
    try:
        # Flatpak portal autostart may pass this (see portal_background.RequestBackground).
        minimized_from_cli = "--minimized" in sys.argv
        if minimized_from_cli:
            sys.argv = [a for a in sys.argv if a != "--minimized"]

        # SinkSwitch: prefer native Wayland when available (Flatpak included); avoids XWayland quirks.
        if sys.platform.startswith("linux") and os.environ.get("WAYLAND_DISPLAY"):
            os.environ.setdefault("QT_QPA_PLATFORM", "wayland;xcb")

        # Try to acquire exclusive lock
        lock_file = acquire_lock()
        if lock_file is None:
            app = QApplication(sys.argv)
            _install_excepthook()
            _cfg0 = ConfigManager()
            _s0 = _cfg0.load_settings()
            _t0 = _s0.get("theme", "system").upper()
            _th0 = Theme[_t0] if _t0 in Theme.__members__ else Theme.SYSTEM
            ThemeManager.apply_theme(app, _th0)
            QMessageBox.warning(
                None,
                "Steam Audio Isolator",
                "Another instance of Steam Audio Isolator is already running."
            )
            sys.exit(1)

        logger.info("="*60)
        logger.info("Steam Audio Isolator starting up")
        logger.info("="*60)

        app = QApplication(sys.argv)
        _install_excepthook()
        app.setApplicationName("Steam Audio Isolator")
        _dfn = flatpak_app_id() or "steam-audio-isolator"
        app.setDesktopFileName(_dfn)
        config = ConfigManager()
        settings = config.load_settings()
        theme_str = settings.get("theme", "system").upper()
        theme = Theme[theme_str] if theme_str in Theme.__members__ else Theme.SYSTEM
        ThemeManager.apply_theme(app, theme)
        exec_path = get_autostart_exec_path()
        window = MainWindow(exec_path=exec_path)
        start_minimized = minimized_from_cli or settings.get("start_minimized_to_tray")
        if start_minimized and window.tray_icon is not None and window.tray_icon.isVisible():
            # Keep window hidden; only tray icon visible — show popup so user notices
            QTimer.singleShot(800, window.show_tray_launch_notification)
        else:
            window.show()
        QTimer.singleShot(300, window.maybe_prompt_install_once)
        sys.exit(app.exec_())
    except Exception as e:
        logger.critical(f"Startup failed: {e}", exc_info=True)
        try:
            app = QApplication.instance()
            if app is None:
                app = QApplication(sys.argv)
            QMessageBox.critical(
                None,
                "Steam Audio Isolator",
                f"Could not start:\n\n{e}\n\nSee log:\n{log_file}",
            )
        except Exception:
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
