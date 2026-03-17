#!/usr/bin/env python3
"""Main entry point for Steam Audio Isolator application"""

import sys
import logging
import os
import fcntl
from pathlib import Path
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QTimer
from steam_pipewire.ui.main_window import MainWindow
from steam_pipewire.utils.config import ConfigManager


# Set up logging
log_file = Path.home() / ".cache" / "steam-audio-isolator.log"
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


def get_autostart_exec_path() -> str:
    """Return the command used to start this app (for autostart desktop file)."""
    if getattr(sys, 'frozen', False):
        return sys.executable
    return f"{sys.executable} -m steam_pipewire.main"


def acquire_lock():
    """Acquire an exclusive lock to ensure only one instance runs.
    
    Returns the lock file object if successful, None if another instance is running.
    """
    lock_dir = Path.home() / ".cache"
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
    # Try to acquire exclusive lock
    lock_file = acquire_lock()
    if lock_file is None:
        app = QApplication(sys.argv)
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
    app.setApplicationName("Steam Audio Isolator")
    app.setDesktopFileName("steam-audio-isolator.desktop")
    exec_path = get_autostart_exec_path()
    window = MainWindow(exec_path=exec_path)
    config = ConfigManager()
    start_minimized = config.get_setting('start_minimized_to_tray')
    if start_minimized and window.tray_icon is not None and window.tray_icon.isVisible():
        # Keep window hidden; only tray icon visible
        pass
    else:
        window.show()
    QTimer.singleShot(300, window.maybe_prompt_install_once)
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
