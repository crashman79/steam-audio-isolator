#!/usr/bin/env python3
"""Theme management for Steam Audio Isolator"""

from enum import Enum
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QColor, QFont, QPalette
import darkdetect


class Theme(Enum):
    """Available themes"""
    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


class ThemeManager:
    """Manage application themes"""
    
    # Light theme palette
    LIGHT_PALETTE = {
        'bg_color': '#FFFFFF',
        'text_color': '#000000',
        'alt_bg_color': '#F5F5F5',
        'selection_color': '#0078D4',
        'border_color': '#D0D0D0',
        'graphics_bg': '#F0F0F0',
    }
    
    # Dark theme palette
    DARK_PALETTE = {
        'bg_color': '#2D2D30',
        'text_color': '#FFFFFF',
        'alt_bg_color': '#3E3E42',
        'selection_color': '#0E639C',
        'border_color': '#555555',
        'graphics_bg': '#2b2b2b',
    }
    
    @staticmethod
    def get_system_theme() -> Theme:
        """Detect system theme preference"""
        try:
            is_dark = darkdetect.isDark()
            return Theme.DARK if is_dark else Theme.LIGHT
        except Exception:
            # Fallback to light if detection fails
            return Theme.LIGHT
    
    @staticmethod
    def get_colors(theme: Theme) -> dict:
        """Get color palette for a theme"""
        if theme == Theme.SYSTEM:
            theme = ThemeManager.get_system_theme()
        return ThemeManager.DARK_PALETTE if theme == Theme.DARK else ThemeManager.LIGHT_PALETTE
    
    @staticmethod
    def apply_theme(app: QApplication, theme: Theme):
        """Apply theme to the application"""
        if theme == Theme.SYSTEM:
            theme = ThemeManager.get_system_theme()
        
        palette = ThemeManager._create_palette(theme)
        stylesheet = ThemeManager._create_stylesheet(theme)
        
        app.setPalette(palette)
        app.setStyle('Fusion')
        app.setStyleSheet(stylesheet)
    
    @staticmethod
    def _create_palette(theme: Theme) -> QPalette:
        """Create QPalette for the theme"""
        palette = QPalette()
        colors = ThemeManager.DARK_PALETTE if theme == Theme.DARK else ThemeManager.LIGHT_PALETTE
        
        palette.setColor(QPalette.Window, QColor(colors['bg_color']))
        palette.setColor(QPalette.WindowText, QColor(colors['text_color']))
        palette.setColor(QPalette.Base, QColor(colors['bg_color']))
        palette.setColor(QPalette.AlternateBase, QColor(colors['alt_bg_color']))
        palette.setColor(QPalette.ToolTipBase, QColor(colors['alt_bg_color']))
        palette.setColor(QPalette.ToolTipText, QColor(colors['text_color']))
        palette.setColor(QPalette.Text, QColor(colors['text_color']))
        palette.setColor(QPalette.Button, QColor(colors['alt_bg_color']))
        palette.setColor(QPalette.ButtonText, QColor(colors['text_color']))
        palette.setColor(QPalette.BrightText, QColor(colors['text_color']))
        palette.setColor(QPalette.Highlight, QColor(colors['selection_color']))
        palette.setColor(QPalette.HighlightedText, QColor(colors['bg_color']))
        palette.setColor(QPalette.Link, QColor(colors['selection_color']))
        
        return palette
    
    @staticmethod
    def _create_stylesheet(theme: Theme) -> str:
        """Create stylesheet for the theme"""
        colors = ThemeManager.DARK_PALETTE if theme == Theme.DARK else ThemeManager.LIGHT_PALETTE
        
        return f"""
            QMainWindow {{
                background-color: {colors['bg_color']};
                color: {colors['text_color']};
            }}
            QWidget {{
                background-color: {colors['bg_color']};
                color: {colors['text_color']};
            }}
            QGroupBox {{
                border: 1px solid {colors['border_color']};
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
            }}
            QPushButton {{
                background-color: {colors['alt_bg_color']};
                color: {colors['text_color']};
                border: 1px solid {colors['border_color']};
                padding: 5px;
                border-radius: 3px;
            }}
            QPushButton:hover {{
                background-color: {colors['selection_color']};
                color: {colors['bg_color']};
            }}
            QPushButton:pressed {{
                background-color: {ThemeManager._darken_color(colors['selection_color'], 20)};
            }}
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
                background-color: {colors['bg_color']};
                color: {colors['text_color']};
                border: 1px solid {colors['border_color']};
                padding: 3px;
                border-radius: 3px;
            }}
            QListWidget, QTextEdit {{
                background-color: {colors['bg_color']};
                color: {colors['text_color']};
                border: 1px solid {colors['border_color']};
                border-radius: 3px;
            }}
            QListWidget::item:selected {{
                background-color: {colors['selection_color']};
            }}
            QCheckBox {{
                color: {colors['text_color']};
            }}
            QLabel {{
                color: {colors['text_color']};
            }}
            QTabBar::tab {{
                background-color: {colors['alt_bg_color']};
                color: {colors['text_color']};
                padding: 5px;
                border: 1px solid {colors['border_color']};
            }}
            QTabBar::tab:selected {{
                background-color: {colors['selection_color']};
                color: {colors['bg_color']};
            }}
            QMenuBar {{
                background-color: {colors['alt_bg_color']};
                color: {colors['text_color']};
            }}
            QMenu {{
                background-color: {colors['alt_bg_color']};
                color: {colors['text_color']};
                border: 1px solid {colors['border_color']};
            }}
            QMenu::item:selected {{
                background-color: {colors['selection_color']};
                color: {colors['bg_color']};
            }}
            QScrollBar:vertical {{
                background-color: {colors['bg_color']};
                width: 12px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {colors['alt_bg_color']};
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {colors['selection_color']};
            }}
        """
    
    @staticmethod
    def _darken_color(color: str, percent: int) -> str:
        """Darken a hex color by a percentage"""
        # Remove '#' if present
        color = color.lstrip('#')
        # Convert hex to RGB
        r, g, b = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
        # Darken
        r = max(0, int(r * (100 - percent) / 100))
        g = max(0, int(g * (100 - percent) / 100))
        b = max(0, int(b * (100 - percent) / 100))
        # Convert back to hex
        return f'#{r:02x}{g:02x}{b:02x}'
