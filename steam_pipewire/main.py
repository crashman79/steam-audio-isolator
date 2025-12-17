#!/usr/bin/env python3
"""Main entry point for Steam Audio Isolator application"""

import sys
import logging
from pathlib import Path
from PyQt5.QtWidgets import QApplication
from steam_pipewire.ui.main_window import MainWindow


# Set up logging
log_file = Path.home() / ".cache" / "steam-audio-isolator.log"
log_file.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)
logger.info("="*60)
logger.info("Steam Audio Isolator starting up")
logger.info("="*60)


def main():
    """Launch the application"""
    app = QApplication(sys.argv)
    app.setApplicationName("Steam Audio Isolator")
    app.setDesktopFileName("steam-audio-isolator.desktop")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
