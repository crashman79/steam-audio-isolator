#!/usr/bin/env python3
"""Main application window for Steam Audio Isolator"""

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QCheckBox, QScrollArea, QGroupBox,
    QFileDialog, QMessageBox, QComboBox, QListWidget, QListWidgetItem,
    QTabWidget, QTextEdit, QSpinBox, QLineEdit, QSystemTrayIcon, QMenu, QAction,
    QGraphicsView, QGraphicsScene, QGraphicsRectItem, QGraphicsLineItem, QGraphicsTextItem,
    QGraphicsPathItem, QGraphicsPixmapItem, QGraphicsEllipseItem, QApplication
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QVariant, QTimer, QPointF, QRectF, QSize, QMimeData
from PyQt5.QtGui import QColor, QFont, QKeySequence, QIcon, QPixmap, QPainter, QPen, QBrush, QPainterPath
from pathlib import Path
import os
from steam_pipewire.pipewire.source_detector import SourceDetector
from steam_pipewire.pipewire.controller import PipeWireController
from steam_pipewire.utils.config import ConfigManager
from steam_pipewire.ui.theme import ThemeManager, Theme


class IconCache:
    """Cache for game and application icons"""
    _instance = None
    _cache = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_icon(self, app_name: str, size: int = 32) -> QPixmap:
        """Get icon for an application, with fallback to default"""
        cache_key = f"{app_name}_{size}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        pixmap = self._try_get_icon(app_name, size)
        self._cache[cache_key] = pixmap
        return pixmap
    
    def _try_get_icon(self, app_name: str, size: int) -> QPixmap:
        """Try multiple sources to get an icon"""
        # First, try Qt icon theme (picks up steam_icon_* and other system icons)
        qt_icon = QIcon.fromTheme(app_name.lower())
        if not qt_icon.isNull():
            pixmap = qt_icon.pixmap(size, size)
            if not pixmap.isNull():
                return pixmap
        
        # Try with "steam_icon_" prefix for Steam games
        # Look for desktop file to get the icon name
        desktop_icon_name = self._get_desktop_icon_name(app_name)
        if desktop_icon_name:
            qt_icon = QIcon.fromTheme(desktop_icon_name)
            if not qt_icon.isNull():
                pixmap = qt_icon.pixmap(size, size)
                if not pixmap.isNull():
                    return pixmap
        
        # For Wine/Proton games without Steam icons, skip system search
        app_lower = app_name.lower()
        if any(wine_indicator in app_lower for wine_indicator in ['.exe', 'wine', 'proton']):
            return self._create_default_icon(app_name, size)
        
        # Try Steam library cache
        steam_icon = self._get_steam_game_icon(app_name, size)
        if not steam_icon.isNull():
            return steam_icon
        
        # Try system icon files directly
        system_icon = self._get_system_icon(app_name, size)
        if not system_icon.isNull():
            return system_icon
        
        # Return default colored pixmap
        return self._create_default_icon(app_name, size)
    
    def _get_desktop_icon_name(self, app_name: str) -> str:
        """Get icon name from .desktop file"""
        desktop_dirs = [
            f'{Path.home()}/.local/share/applications',
            '/usr/share/applications'
        ]
        
        search_term = app_name.lower()
        
        for desktop_dir in desktop_dirs:
            if not Path(desktop_dir).exists():
                continue
            
            for desktop_file in Path(desktop_dir).glob('*.desktop'):
                if search_term in desktop_file.stem.lower():
                    try:
                        with open(desktop_file, 'r') as f:
                            for line in f:
                                if line.startswith('Icon='):
                                    icon_name = line.split('=', 1)[1].strip()
                                    return icon_name
                    except:
                        pass
        
        return ""
    
    def _get_steam_game_icon(self, app_name: str, size: int) -> QPixmap:
        """Try to get icon from Steam library"""
        steam_dir = Path.home() / '.steam' / 'root'
        if not steam_dir.exists():
            steam_dir = Path.home() / '.local' / 'share' / 'Steam'
        
        if not steam_dir.exists():
            return QPixmap()
        
        # Look in userdata for icons
        userdata = steam_dir / 'userdata'
        if userdata.exists():
            for user_dir in userdata.iterdir():
                icons_dir = user_dir / 'config' / 'shortcuts'
                if icons_dir.exists():
                    for icon_file in icons_dir.glob('*'):
                        if app_name.lower() in icon_file.stem.lower():
                            pm = QPixmap(str(icon_file))
                            if not pm.isNull():
                                return pm.scaledToWidth(size, Qt.SmoothTransformation)
        
        return QPixmap()
    
    def _get_system_icon(self, app_name: str, size: int) -> QPixmap:
        """Try to get icon from system icon theme"""
        # Search common icon locations
        icon_paths = [
            '/usr/share/icons/hicolor',
            f'{Path.home()}/.local/share/icons/hicolor',
            '/usr/share/pixmaps'
        ]
        
        # Sanitize app_name for filename search
        search_term = app_name.lower().split()[0]
        
        # Avoid generic icons (wine, proton, etc.) - prefer game-specific
        skip_patterns = ['wine', 'proton', 'steam-launch', 'wineserver']
        
        best_match = None
        for icon_path in icon_paths:
            if not Path(icon_path).exists():
                continue
            
            # First try exact name match
            for icon_file in Path(icon_path).rglob(f'{search_term}.png'):
                # Skip generic icons
                if any(skip in icon_file.name.lower() for skip in skip_patterns):
                    continue
                pm = QPixmap(str(icon_file))
                if not pm.isNull():
                    return pm.scaledToWidth(size, Qt.SmoothTransformation)
            
            # Then try prefix match, but be selective
            for icon_file in Path(icon_path).rglob(f'{search_term}*.png'):
                # Skip generic icons
                if any(skip in icon_file.name.lower() for skip in skip_patterns):
                    continue
                if best_match is None:
                    best_match = icon_file
        
        if best_match:
            pm = QPixmap(str(best_match))
            if not pm.isNull():
                return pm.scaledToWidth(size, Qt.SmoothTransformation)
        
        return QPixmap()
    
    def _get_desktop_icon(self, app_name: str, size: int) -> QPixmap:
        """Try to get icon from .desktop files"""
        desktop_dirs = [
            '/usr/share/applications',
            f'{Path.home()}/.local/share/applications'
        ]
        
        search_term = app_name.lower().split()[0]
        
        for desktop_dir in desktop_dirs:
            if not Path(desktop_dir).exists():
                continue
            
            for desktop_file in Path(desktop_dir).glob('*.desktop'):
                if search_term in desktop_file.stem.lower():
                    try:
                        with open(desktop_file, 'r') as f:
                            content = f.read()
                            # Look for Icon= line
                            for line in content.split('\n'):
                                if line.startswith('Icon='):
                                    icon_name = line.split('=', 1)[1].strip()
                                    pm = QPixmap(icon_name)
                                    if not pm.isNull():
                                        return pm.scaledToWidth(size, Qt.SmoothTransformation)
                    except:
                        pass
        
        return QPixmap()
    
    def _create_default_icon(self, app_name: str, size: int) -> QPixmap:
        """Create a default colored icon with initials"""
        pm = QPixmap(size, size)
        
        # Color based on app name hash
        colors = [
            QColor("#FF6B6B"), QColor("#4ECDC4"), QColor("#45B7D1"),
            QColor("#F7B731"), QColor("#5F27CD"), QColor("#00D2D3")
        ]
        color = colors[hash(app_name) % len(colors)]
        
        pm.fill(color)
        
        # Draw first letter
        painter = QPainter(pm)
        painter.setFont(QFont("Arial", int(size * 0.6), QFont.Bold))
        painter.setPen(QColor("white"))
        painter.drawText(pm.rect(), Qt.AlignCenter, app_name[0].upper())
        painter.end()
        
        return pm


class SourceDetectorThread(QThread):
    """Worker thread for detecting audio sources"""
    sources_found = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, detector=None):
        super().__init__()
        self.detector = detector or SourceDetector()

    def run(self):
        """Run source detection in background"""
        try:
            sources = self.detector.get_audio_sources()
            self.sources_found.emit(sources)
        except Exception as e:
            self.error_occurred.emit(str(e))


class RouteRefreshThread(QThread):
    """Worker thread for refreshing routes without blocking UI"""
    routes_updated = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
    
    def run(self):
        """Refresh routes in background"""
        try:
            routes = self.controller.get_current_routes()
            self.routes_updated.emit(routes)
        except Exception as e:
            self.error_occurred.emit(str(e))


class SettingsDialog(QWidget):
    """Settings/Preferences dialog"""
    settings_changed = pyqtSignal(dict)
    
    def __init__(self, config: 'ConfigManager', parent=None):
        super().__init__(parent)
        self.config = config
        self.settings = config.load_settings()
        self.init_ui()
    
    def init_ui(self):
        """Initialize settings UI"""
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Theme selection
        theme_group = QGroupBox("Appearance")
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("Theme:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark", "System"])
        current_theme = self.settings.get('theme', 'system')
        theme_index = {"light": 0, "dark": 1, "system": 2}.get(current_theme.lower(), 2)
        self.theme_combo.setCurrentIndex(theme_index)
        self.theme_combo.currentIndexChanged.connect(self._on_settings_changed)
        theme_layout.addWidget(self.theme_combo)
        theme_layout.addStretch()
        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)
        
        # Restore on close
        restore_group = QGroupBox("On Application Close")
        restore_layout = QVBoxLayout()
        self.restore_checkbox = QCheckBox("Restore default sink routing when app closes")
        self.restore_checkbox.setChecked(self.settings.get('restore_default_on_close', True))
        self.restore_checkbox.stateChanged.connect(self._on_settings_changed)
        restore_layout.addWidget(self.restore_checkbox)
        restore_layout.addWidget(QLabel(
            "When enabled, closing the app will disconnect game audio from Steam\n"
            "and reconnect the system audio sink (restoring default behavior)."
        ))
        self.prompt_checkbox = QCheckBox("Show confirmation dialog when closing")
        self.prompt_checkbox.setChecked(self.settings.get('prompt_on_close', True))
        self.prompt_checkbox.stateChanged.connect(self._on_settings_changed)
        restore_layout.addWidget(self.prompt_checkbox)
        restore_layout.addWidget(QLabel(
            "When enabled, a confirmation dialog appears before closing the application."
        ))
        restore_group.setLayout(restore_layout)
        layout.addWidget(restore_group)
        
        # Auto-detect interval
        interval_group = QGroupBox("Source Auto-Detection")
        interval_layout = QVBoxLayout()
        
        # Auto-detect interval spinner
        interval_row = QHBoxLayout()
        interval_row.addWidget(QLabel("Check for new audio sources every:"))
        self.interval_spinbox = QSpinBox()
        self.interval_spinbox.setMinimum(1)
        self.interval_spinbox.setMaximum(30)
        self.interval_spinbox.setValue(self.settings.get('auto_detect_interval', 3))
        self.interval_spinbox.setSuffix(" seconds")
        self.interval_spinbox.valueChanged.connect(self._on_settings_changed)
        interval_row.addWidget(self.interval_spinbox)
        interval_row.addStretch()
        interval_layout.addLayout(interval_row)
        
        # Auto-apply routing checkbox
        self.auto_apply_checkbox = QCheckBox("Automatically apply routing when new games are detected")
        self.auto_apply_checkbox.setChecked(self.settings.get('auto_apply_games', False))
        self.auto_apply_checkbox.stateChanged.connect(self._on_settings_changed)
        interval_layout.addWidget(self.auto_apply_checkbox)
        interval_layout.addWidget(QLabel(
            "When enabled, detected games will be automatically connected to Steam recording.\n"
            "When disabled, you must manually click 'Apply Routing' after games are detected."
        ))
        
        interval_group.setLayout(interval_layout)
        layout.addWidget(interval_group)
        
        # System tray
        tray_group = QGroupBox("System Tray")
        tray_layout = QVBoxLayout()
        self.tray_checkbox = QCheckBox("Minimize to system tray on close")
        self.tray_checkbox.setChecked(self.settings.get('minimize_to_tray', True))
        self.tray_checkbox.stateChanged.connect(self._on_settings_changed)
        tray_layout.addWidget(self.tray_checkbox)
        tray_layout.addWidget(QLabel(
            "When enabled, closing the window will minimize to tray.\n"
            "Use the tray menu to quit completely."
        ))
        tray_group.setLayout(tray_layout)
        layout.addWidget(tray_group)
        
        layout.addStretch()
        
        # Save button
        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self.save_settings)
        layout.addWidget(save_btn)
        
        self.setLayout(layout)
    
    def _on_settings_changed(self):
        """Handle settings changes"""
        # Enable save button or auto-save
        pass
    
    def save_settings(self):
        """Save current settings"""
        theme_map = {0: "light", 1: "dark", 2: "system"}
        
        self.settings['restore_default_on_close'] = self.restore_checkbox.isChecked()
        self.settings['prompt_on_close'] = self.prompt_checkbox.isChecked()
        self.settings['auto_detect_interval'] = self.interval_spinbox.value()
        self.settings['auto_apply_games'] = self.auto_apply_checkbox.isChecked()
        self.settings['minimize_to_tray'] = self.tray_checkbox.isChecked()
        self.settings['theme'] = theme_map.get(self.theme_combo.currentIndex(), 'system')
        
        self.config.save_settings(self.settings)
        self.settings_changed.emit(self.settings)
        
        # Apply theme immediately
        theme_str = self.settings['theme'].upper()
        theme = Theme[theme_str] if theme_str in Theme.__members__ else Theme.SYSTEM
        ThemeManager.apply_theme(QApplication.instance(), theme)
        
        # Show confirmation
        QMessageBox.information(self, "Success", "Settings saved successfully!")
    
    def get_settings(self):
        """Get current settings"""
        return self.settings


class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Steam Audio Isolator v{__import__('steam_pipewire').__version__}")
        self.setGeometry(100, 100, 900, 750)

        self.pipewire = PipeWireController()
        self.config = ConfigManager()
        self.sources = []
        self.selected_sources = set()
        self.detector_thread = None  # Track detector thread to prevent concurrent runs
        self.source_detection_timeout = None  # Watchdog timer for detection
        self.last_sources_hash = None  # Track source changes for auto-detect
        self.auto_detect_timer = None  # Timer for auto-detect polling
        self.previously_detected_games = set()  # Track game sources for auto-apply
        
        # Load settings
        self.settings = self.config.load_settings()
        
        # Apply theme
        theme_str = self.settings.get('theme', 'system').upper()
        theme = Theme[theme_str] if theme_str in Theme.__members__ else Theme.SYSTEM
        ThemeManager.apply_theme(QApplication.instance(), theme)
        
        # System tray
        self.tray_icon = None
        self.is_closing = False
        
        # Set custom colored icon for window
        self.setWindowIcon(self.create_app_icon())

        self.init_ui()
        self.setup_system_tray()
        self.detect_sources()
        self.start_auto_detect()

    def init_ui(self):
        """Initialize the user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()

        # Header with title and info
        header_layout = QHBoxLayout()
        
        # Title on the left
        title = QLabel("Steam Audio Isolator")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        header_layout.addWidget(title)
        
        # Info note on the right - changes based on restore_default_on_close setting
        restore_on_close = self.settings.get('restore_default_on_close', True)
        minimize_to_tray = self.settings.get('minimize_to_tray', True)
        
        if minimize_to_tray:
            info_text = "ℹ Minimize to tray enabled. " + ("Quitting will restore default routing" if restore_on_close else "Quitting will keep current routing")
        else:
            info_text = "ℹ Closing will restore default routing" if restore_on_close else "ℹ Closing will keep current routing"
        
        self.info_note = QLabel(info_text)
        self.info_note.setStyleSheet("color: #1976d2; font-size: 10px; padding: 5px;")
        self.info_note.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        header_layout.addWidget(self.info_note)
        
        main_layout.addLayout(header_layout)
        
        # Status label
        self.status_label = QLabel("Detecting audio sources...")
        self.status_label.setStyleSheet("color: #666; font-size: 11px;")
        main_layout.addWidget(self.status_label)

        # Create tabs for different views
        tabs = QTabWidget()
        
        # Routing tab
        routing_tab = self.create_routing_tab()
        tabs.addTab(routing_tab, "Audio Routing")
        
        # Current routes tab
        routes_tab = self.create_routes_tab()
        tabs.addTab(routes_tab, "Current Routes")
        
        # Info tab
        info_tab = self.create_info_tab()
        tabs.addTab(info_tab, "System Info")
        
        # Settings tab
        settings_tab = SettingsDialog(self.config)
        settings_tab.settings_changed.connect(self.on_settings_changed)
        tabs.addTab(settings_tab, "⚙ Settings")
        
        # Profiles tab
        profiles_tab = self.create_profiles_tab()
        tabs.addTab(profiles_tab, "💾 Profiles")
        
        # About tab
        about_tab = self.create_about_tab()
        tabs.addTab(about_tab, "ℹ About")
        
        main_layout.addWidget(tabs)
        central_widget.setLayout(main_layout)

    def setup_system_tray(self):
        """Setup system tray icon and menu"""
        import logging
        logger = logging.getLogger(__name__)
        
        # Check if system tray is available
        if not QSystemTrayIcon.isSystemTrayAvailable():
            logger.warning("System tray not available on this system")
            return
        
        # Create custom colored icon
        icon = self.create_app_icon()
        
        # Create tray icon
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(icon)
        self.tray_icon.setToolTip("Steam Audio Isolator")
        
        # Create tray menu
        tray_menu = QMenu()
        
        show_action = QAction("Show Window", self)
        show_action.triggered.connect(self.show_from_tray)
        tray_menu.addAction(show_action)
        
        tray_menu.addSeparator()
        
        apply_action = QAction("Apply Routing", self)
        apply_action.triggered.connect(self.apply_routing)
        tray_menu.addAction(apply_action)
        
        clear_action = QAction("Clear Routes", self)
        clear_action.triggered.connect(self.clear_all_routes)
        tray_menu.addAction(clear_action)
        
        refresh_action = QAction("Refresh Sources", self)
        refresh_action.triggered.connect(self.detect_sources)
        tray_menu.addAction(refresh_action)
        
        tray_menu.addSeparator()
        
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_application)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)
        self.tray_icon.show()
        
        logger.debug("System tray icon initialized")
    
    def create_app_icon(self):
        """Create a custom colored icon to distinguish from system audio"""
        # Create a 64x64 pixmap
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw a distinctive colored speaker icon
        # Use green/blue gradient to stand out from gray audio icons
        from PyQt5.QtGui import QLinearGradient, QPen, QBrush
        
        # Create gradient (teal/cyan color scheme)
        gradient = QLinearGradient(0, 0, 64, 64)
        gradient.setColorAt(0, QColor(0, 180, 180))  # Cyan
        gradient.setColorAt(1, QColor(0, 120, 160))  # Teal
        
        # Draw speaker base (trapezoid)
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(QColor(0, 100, 120), 2))
        from PyQt5.QtCore import QPoint
        speaker_points = [
            QPoint(12, 20),
            QPoint(28, 16),
            QPoint(28, 48),
            QPoint(12, 44)
        ]
        from PyQt5.QtGui import QPolygon
        painter.drawPolygon(QPolygon(speaker_points))
        
        # Draw speaker cone (small rectangle on left)
        painter.drawRect(8, 26, 6, 12)
        
        # Draw sound waves (arcs)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor(0, 200, 200), 3))
        painter.drawArc(32, 24, 8, 16, 90 * 16, 180 * 16)
        painter.drawArc(38, 20, 14, 24, 90 * 16, 180 * 16)
        painter.drawArc(44, 16, 18, 32, 90 * 16, 180 * 16)
        
        painter.end()
        
        return QIcon(pixmap)
    
    def _update_graphics_view_theme(self):
        """Update graphics view background color based on current theme"""
        theme_str = self.settings.get('theme', 'system').upper()
        theme = Theme[theme_str] if theme_str in Theme.__members__ else Theme.SYSTEM
        colors = ThemeManager.get_colors(theme)
        graphics_bg = colors.get('graphics_bg', '#2b2b2b')
        self.routes_graphics_view.setStyleSheet(f"QGraphicsView {{ background-color: {graphics_bg}; }}")

    def tray_icon_activated(self, reason):
        """Handle tray icon activation"""
        if reason == QSystemTrayIcon.Trigger:
            self.toggle_visibility()
    
    def show_from_tray(self):
        """Show window from system tray"""
        self.show()
        self.activateWindow()
        self.raise_()
    
    def toggle_visibility(self):
        """Toggle window visibility"""
        if self.isVisible():
            self.hide()
        else:
            self.show_from_tray()
    
    def quit_application(self):
        """Quit the application completely"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info("Quitting application via tray menu")
        
        # Set flag to indicate we want to actually quit (not minimize)
        self.is_closing = True
        
        # closeEvent will handle the confirmation and cleanup
        self.close()

    def create_routing_tab(self) -> QWidget:
        """Create the audio routing configuration tab"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Instructions (dynamic based on auto-apply setting)
        self.routing_instructions = QLabel()
        self.routing_instructions.setTextFormat(Qt.RichText)
        self.routing_instructions.setWordWrap(True)
        self.routing_instructions.setStyleSheet("color: #333; padding: 8px; background-color: #fff9e6; border-left: 4px solid #ffc107; border-radius: 3px;")
        self._update_routing_instructions()
        layout.addWidget(self.routing_instructions)

        # Source list area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.sources_group = QGroupBox("Available Audio Sources")
        self.sources_layout = QVBoxLayout(self.sources_group)
        scroll.setWidget(self.sources_group)
        layout.addWidget(scroll)

        # Control buttons
        button_layout = QHBoxLayout()

        refresh_btn = QPushButton("🔄 Refresh Sources")
        refresh_btn.clicked.connect(self.detect_sources)
        button_layout.addWidget(refresh_btn)

        button_layout.addStretch()

        apply_btn = QPushButton("✓ Apply Routing")
        apply_btn.clicked.connect(self.apply_routing)
        apply_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 5px; font-weight: bold;")
        apply_btn.setToolTip("Click to create audio connections for checked sources.\nThis is a manual action - routing is NOT automatic.")
        button_layout.addWidget(apply_btn)

        clear_btn = QPushButton("✕ Clear All Routes")
        clear_btn.clicked.connect(self.clear_all_routes)
        button_layout.addWidget(clear_btn)

        layout.addLayout(button_layout)

        widget.setLayout(layout)
        return widget

    def create_routes_tab(self) -> QWidget:
        """Create the current routes display tab"""
        widget = QWidget()
        layout = QVBoxLayout()

        layout.addWidget(QLabel("Currently connected audio routes to Steam:"))

        # Visual graph view with dark background
        self.routes_graphics_view = QGraphicsView()
        self.routes_scene = QGraphicsScene()
        self.routes_graphics_view.setScene(self.routes_scene)
        # Set background color based on theme
        self._update_graphics_view_theme()
        self.routes_graphics_view.setMinimumHeight(300)
        self.routes_graphics_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.routes_graphics_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        layout.addWidget(self.routes_graphics_view)

        # List view below
        self.routes_list = QListWidget()
        self.routes_list.setMaximumHeight(150)
        layout.addWidget(self.routes_list)

        refresh_routes_btn = QPushButton("Refresh Routes")
        refresh_routes_btn.clicked.connect(self.update_current_routes)
        layout.addWidget(refresh_routes_btn)

        widget.setLayout(layout)
        return widget

    def create_info_tab(self) -> QWidget:
        """Create the system information tab"""
        widget = QWidget()
        layout = QVBoxLayout()

        layout.addWidget(QLabel("PipeWire System Information:"))

        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setFont(QFont("Monospace"))
        layout.addWidget(self.info_text)

        update_info_btn = QPushButton("Update Info")
        update_info_btn.clicked.connect(self.update_system_info)
        layout.addWidget(update_info_btn)

        widget.setLayout(layout)
        return widget

    def create_profiles_tab(self) -> QWidget:
        """Create the profile management tab"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Save current selection as profile
        save_group = QGroupBox("Save Current Selection as Profile")
        save_layout = QHBoxLayout()
        save_layout.addWidget(QLabel("Profile name:"))
        self.profile_name_input = QLineEdit()
        self.profile_name_input.setPlaceholderText("e.g., Game Only, Game + Discord")
        save_layout.addWidget(self.profile_name_input)
        save_btn = QPushButton("💾 Save Profile")
        save_btn.clicked.connect(self.save_profile)
        save_layout.addWidget(save_btn)
        save_group.setLayout(save_layout)
        layout.addWidget(save_group)

        # Load/Delete profiles
        list_group = QGroupBox("Saved Profiles")
        list_layout = QVBoxLayout()
        
        list_layout.addWidget(QLabel("Click to load a profile:"))
        
        self.profiles_list = QListWidget()
        self.profiles_list.itemClicked.connect(self.on_profile_selected)
        list_layout.addWidget(self.profiles_list)
        
        button_layout = QHBoxLayout()
        load_btn = QPushButton("✓ Load Selected")
        load_btn.clicked.connect(self.load_selected_profile)
        button_layout.addWidget(load_btn)
        
        delete_btn = QPushButton("✕ Delete Selected")
        delete_btn.setStyleSheet("background-color: #f44336; color: white;")
        delete_btn.clicked.connect(self.delete_selected_profile)
        button_layout.addWidget(delete_btn)
        
        refresh_btn = QPushButton("🔄 Refresh List")
        refresh_btn.clicked.connect(self.refresh_profiles_list)
        button_layout.addWidget(refresh_btn)
        
        list_layout.addLayout(button_layout)
        list_group.setLayout(list_layout)
        layout.addWidget(list_group)
        
        widget.setLayout(layout)
        
        # Load initial profile list
        self.refresh_profiles_list()
        
        return widget

    def create_about_tab(self) -> QWidget:
        """Create the About/Help tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(20)
        
        # Title
        title = QLabel("Steam Audio Isolator")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Subtitle
        subtitle = QLabel("Isolate game audio for clean Steam game recording")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #666; font-size: 12px; margin-bottom: 10px;")
        layout.addWidget(subtitle)
        
        # Main description
        description = QLabel(
            "<h3>What This App Does</h3>"
            "<p>Steam's game recording feature on Linux captures <b>all audio</b> by default - "
            "including system notifications, browser audio, and background applications. "
            "This makes your recordings cluttered with unwanted sounds.</p>"
            
            "<p><b>Steam Audio Isolator</b> solves this problem by creating direct audio connections "
            "from your game to Steam's recording input, bypassing the system audio mixer entirely.</p>"
            
            "<h3>How It Works</h3>"
            "<p><b>Without this app:</b><br>"
            "Game → Audio Sink (speakers) → Steam Recording<br>"
            "<i>Steam records everything going to your speakers</i></p>"
            
            "<p><b>With this app:</b><br>"
            "Game → Direct Connection → Steam Recording<br>"
            "Other Audio → Audio Sink → Speakers (not recorded)<br>"
            "<i>Steam only records what you select</i></p>"
            
            "<h3>Quick Start</h3>"
            "<ol>"
            "<li><b>Audio Routing Tab:</b> Check the games you want to record</li>"
            "<li>Click <b>Apply Routing</b> to create direct connections</li>"
            "<li><b>Current Routes Tab:</b> View active audio routes</li>"
            "<li><b>Profiles Tab:</b> Save/load routing configurations</li>"
            "<li><b>Settings Tab:</b> Configure behavior and preferences</li>"
            "</ol>"
            
            "<h3>Technology</h3>"
            "<p>Uses <b>PipeWire</b> audio system to route audio streams directly between "
            "applications without going through the system mixer. This provides clean, "
            "isolated game audio for your Steam recordings.</p>"
            
            f"<p style='margin-top: 20px; color: #666; font-size: 10px;'>"
            f"Version {__import__('steam_pipewire').__version__} | "
            f"Config: ~/.config/steam-audio-isolator/ | "
            f"Logs: ~/.cache/steam-audio-isolator.log"
            "</p>"
        )
        description.setWordWrap(True)
        description.setTextFormat(Qt.RichText)
        description.setOpenExternalLinks(True)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(description)
        layout.addWidget(scroll)
        
        widget.setLayout(layout)
        return widget

    def on_profile_selected(self, item):
        """Handle profile selection in list"""
        # This just marks the item as selected for load/delete operations
        pass

    def save_profile(self):
        """Save current source selection as a profile"""
        import logging
        logger = logging.getLogger(__name__)
        
        profile_name = self.profile_name_input.text().strip()
        if not profile_name:
            QMessageBox.warning(self, "Error", "Please enter a profile name")
            return
        
        # Create profile data
        profile_data = {
            "name": profile_name,
            "sources": list(self.selected_sources),
            "timestamp": __import__('time').strftime("%Y-%m-%d %H:%M:%S")
        }
        
        try:
            self.config.save_profile(profile_name, profile_data)
            logger.info(f"Profile saved: {profile_name}")
            QMessageBox.information(self, "Success", f"Profile '{profile_name}' saved!")
            self.profile_name_input.clear()
            self.refresh_profiles_list()
        except Exception as e:
            logger.error(f"Error saving profile: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save profile: {e}")

    def load_selected_profile(self):
        """Load the selected profile"""
        import logging
        logger = logging.getLogger(__name__)
        
        current_item = self.profiles_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Error", "Please select a profile to load")
            return
        
        profile_name = current_item.text()
        
        try:
            profile_data = self.config.load_profile(profile_name)
            sources_to_select = profile_data.get("sources", [])
            
            # Update selected sources
            self.selected_sources = set(sources_to_select)
            logger.info(f"Profile loaded: {profile_name}")
            logger.debug(f"Selected sources: {self.selected_sources}")
            
            # Update UI
            self.update_sources_list()
            
            # Automatically apply routing
            self.apply_routing()
            
            QMessageBox.information(self, "Success", f"Profile '{profile_name}' loaded and routing applied!\n\nSelected sources:\n" + "\n".join(sources_to_select))
        except Exception as e:
            logger.error(f"Error loading profile: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load profile: {e}")

    def delete_selected_profile(self):
        """Delete the selected profile"""
        import logging
        logger = logging.getLogger(__name__)
        
        current_item = self.profiles_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Error", "Please select a profile to delete")
            return
        
        profile_name = current_item.text()
        
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete profile '{profile_name}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                self.config.delete_profile(profile_name)
                logger.info(f"Profile deleted: {profile_name}")
                QMessageBox.information(self, "Success", f"Profile '{profile_name}' deleted!")
                self.refresh_profiles_list()
            except Exception as e:
                logger.error(f"Error deleting profile: {e}")
                QMessageBox.critical(self, "Error", f"Failed to delete profile: {e}")

    def refresh_profiles_list(self):
        """Refresh the list of saved profiles"""
        self.profiles_list.clear()
        profiles = self.config.list_profiles()
        
        if profiles:
            for profile_name in sorted(profiles):
                item = QListWidgetItem(profile_name)
                self.profiles_list.addItem(item)
        else:
            item = QListWidgetItem("No profiles saved yet")
            item.setForeground(QColor("gray"))
            self.profiles_list.addItem(item)

    def detect_sources(self):
        """Detect audio sources in background"""
        import logging
        logger = logging.getLogger(__name__)
        
        # Prevent concurrent detection runs
        if self.detector_thread and self.detector_thread.isRunning():
            logger.debug("Source detection already in progress, skipping...")
            return
        
        logger.debug("Starting source detection thread...")
        
        # Each thread gets its own detector instance to avoid concurrency issues
        self.detector_thread = SourceDetectorThread(SourceDetector())
        self.detector_thread.sources_found.connect(self.on_sources_detected)
        self.detector_thread.error_occurred.connect(self.on_detection_error)
        self.detector_thread.start()
        
        # Set a watchdog timer - if detection takes > 5 seconds, force timeout
        self.source_detection_timeout = QTimer()
        self.source_detection_timeout.setSingleShot(True)
        self.source_detection_timeout.timeout.connect(self._on_detection_timeout)
        self.source_detection_timeout.start(5000)  # 5 second timeout
    
    def _on_detection_timeout(self):
        """Handle source detection timeout"""
        import logging
        logger = logging.getLogger(__name__)
        
        if self.detector_thread and self.detector_thread.isRunning():
            logger.error("Source detection timeout! Force killing thread.")
            self.detector_thread.terminate()
            self.detector_thread.wait(1000)  # Wait up to 1 second for graceful shutdown
            self.status_label.setText("✗ Source detection timed out (PipeWire issue)")
            self.status_label.setStyleSheet("color: #f44336; font-size: 11px;")
    
    def start_auto_detect(self):
        """Start automatic source detection polling with configurable interval"""
        import logging
        logger = logging.getLogger(__name__)
        
        interval_ms = self.settings.get('auto_detect_interval', 3) * 1000
        
        self.auto_detect_timer = QTimer()
        self.auto_detect_timer.timeout.connect(self._check_for_source_changes)
        self.auto_detect_timer.start(int(interval_ms))
        logger.debug(f"Auto-detect polling started ({interval_ms/1000}s interval)")
    
    def _check_for_source_changes(self):
        """Periodically check if sources have changed"""
        import logging
        import hashlib
        logger = logging.getLogger(__name__)
        
        # Skip if detection already running
        if self.detector_thread and self.detector_thread.isRunning():
            return
        
        # Get current sources (use cached detector)
        detector = SourceDetector()
        current_sources = detector.get_audio_sources()
        
        # Create hash of source list to detect changes
        sources_str = str(sorted([(s['id'], s['name']) for s in current_sources]))
        current_hash = hashlib.md5(sources_str.encode()).hexdigest()
        
        # If sources changed, trigger full update
        if current_hash != self.last_sources_hash:
            logger.debug(f"Source change detected! Old: {self.last_sources_hash}, New: {current_hash}")
            self.last_sources_hash = current_hash
            self.sources = current_sources
            
            # Check for new game sources
            excluded_games = self.config.get_excluded_games()
            auto_apply_enabled = self.settings.get('auto_apply_games', False)  # Default to False - require user action
            
            current_games = {s['name'] for s in current_sources if s['type'] == 'Game'}
            new_games = current_games - self.previously_detected_games - set(excluded_games)
            
            if new_games and auto_apply_enabled:
                logger.info(f"New game(s) detected: {new_games}")
                # Update source list first
                self.update_sources_list()
                # Then auto-apply routing
                self._auto_apply_new_games()
            else:
                # Just update the source list
                self.update_sources_list()
            
            # Update tracked games
            self.previously_detected_games = current_games
            
            # Update status
            if current_sources:
                self.status_label.setText(f"✓ Found {len(current_sources)} audio source(s)")
                self.status_label.setStyleSheet("color: #4CAF50; font-size: 11px;")

    def _auto_apply_new_games(self):
        """Automatically apply routing when new games are detected"""
        import logging
        logger = logging.getLogger(__name__)
        
        if not self.selected_sources:
            logger.debug("No game sources selected, skipping auto-apply")
            return
        
        try:
            steam_node_id = self.pipewire.steam_node_id
            if not steam_node_id:
                logger.warning("Steam node not found, cannot auto-apply routing")
                return
            
            selected_source_ids = [s['id'] for s in self.sources if s['name'] in self.selected_sources]
            
            if selected_source_ids:
                logger.info(f"Auto-applying routing for: {self.selected_sources}")
                success, message = self.pipewire.create_audio_routing(selected_source_ids, steam_node_id)
                
                if success:
                    logger.info(f"Auto-apply successful: {message}")
                    self.status_label.setText(f"✓ Auto-applied routing to new games")
                    self.status_label.setStyleSheet("color: #4CAF50; font-size: 11px;")
                    
                    # Update routes display
                    self.route_check_timer = QTimer()
                    self.route_check_timer.setSingleShot(True)
                    self.route_check_timer.timeout.connect(self.update_current_routes)
                    self.route_check_timer.start(500)
                else:
                    logger.warning(f"Auto-apply failed: {message}")
        except Exception as e:
            logger.error(f"Error in auto-apply: {e}")

    
    def closeEvent(self, event):
        """Handle window close - optionally minimize to tray or quit"""
        import logging
        import time
        logger = logging.getLogger(__name__)
        
        # Check if we should minimize to tray instead of closing
        minimize_to_tray = self.settings.get('minimize_to_tray', True)
        restore_on_close = self.settings.get('restore_default_on_close', True)
        prompt_on_close = self.settings.get('prompt_on_close', True)
        
        # If trying to close via window X button and tray is enabled, minimize instead
        if not self.is_closing and minimize_to_tray and self.tray_icon and self.tray_icon.isVisible():
            # Minimizing to tray - show what will happen on actual quit
            logger.debug("Minimizing to system tray")
            self.hide()
            event.ignore()
            
            # Show notification explaining the behavior
            if not hasattr(self, '_tray_notified'):
                restore_msg = "Routes will be restored to default when you quit." if restore_on_close else "Current routes will be kept when you quit."
                self.tray_icon.showMessage(
                    "Steam Audio Isolator",
                    f"Application minimized to system tray.\n{restore_msg}\nRight-click tray icon to quit.",
                    QSystemTrayIcon.Information,
                    3000
                )
                self._tray_notified = True
            return
        
        # Actually closing the application - show confirmation if enabled
        if prompt_on_close and (not hasattr(self, '_quit_confirmed') or not self._quit_confirmed):
            # Build confirmation message based on settings
            if restore_on_close:
                message = (
                    "Closing will restore default audio sink routing.\n"
                    "All game audio will disconnect from Steam and reconnect to speakers.\n\n"
                    "Do you want to close the application?"
                )
            else:
                message = (
                    "Current audio routing will remain active after closing.\n"
                    "Game audio will stay connected to Steam recording.\n\n"
                    "Do you want to close the application?"
                )
            
            reply = QMessageBox.question(
                self, "Confirm Close",
                message,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                self.is_closing = False  # Reset flag
                event.ignore()
                return
            
            self._quit_confirmed = True
        
        # Actually closing the application
        logger.debug("Application closing")
        
        # Hide tray icon
        if self.tray_icon:
            self.tray_icon.hide()
        
        # Stop auto-detect timer
        if self.auto_detect_timer:
            self.auto_detect_timer.stop()
        
        # Check if restore on close is enabled
        if restore_on_close:
            logger.debug("App closing - restoring default sink routing...")
            
            # First, disconnect all direct game audio routes
            logger.debug("Disconnecting game audio routes...")
            success, message = self.pipewire.disconnect_all_from_steam()
            logger.debug(f"Disconnect result: {message}")
            
            # Small delay for PipeWire to process disconnections
            time.sleep(0.3)
            
            # Then reconnect the sink to restore default behavior
            logger.debug("Reconnecting audio sink...")
            success, message = self.pipewire.reconnect_sink_to_steam()
            if success:
                logger.info(f"Sink reconnected on close: {message}")
            else:
                logger.warning(f"Failed to reconnect sink on close: {message}")
            
            # Small delay to ensure PipeWire processes the connection
            time.sleep(0.5)
        else:
            logger.debug("App closing (restore on close disabled)")
        
        event.accept()

    def on_sources_detected(self, sources):
        """Handle detected sources"""
        # Cancel the watchdog timeout since detection completed
        if self.source_detection_timeout:
            self.source_detection_timeout.stop()
        
        self.sources = sources
        self.update_sources_list()
        
        # Update status
        if sources:
            self.status_label.setText(f"✓ Found {len(sources)} audio source(s)")
            self.status_label.setStyleSheet("color: #4CAF50; font-size: 11px;")
        else:
            self.status_label.setText("⚠ No audio sources detected (is PipeWire running?)")
            self.status_label.setStyleSheet("color: #ff9800; font-size: 11px;")

    def on_detection_error(self, error):
        """Handle detection error"""
        self.status_label.setText(f"✗ Error detecting sources: {error}")
        self.status_label.setStyleSheet("color: #f44336; font-size: 11px;")

    def update_sources_list(self):
        """Update the UI with detected sources - optimized for speed"""
        import logging
        logger = logging.getLogger(__name__)
        
        # Block signals temporarily to avoid signal spam during update
        self.sources_group.blockSignals(True)
        
        # Clear existing widgets more efficiently
        while self.sources_layout.count():
            item = self.sources_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.sources:
            no_sources_label = QLabel("No audio sources detected")
            no_sources_label.setStyleSheet("color: gray;")
            self.sources_layout.addWidget(no_sources_label)
            self.sources_group.blockSignals(False)
            return

        # Get excluded games from config
        excluded_games = self.config.get_excluded_games()
        
        # Add checkboxes for each source, grouped by type
        type_groups = {}
        for source in self.sources:
            source_type = source['type']
            if source_type not in type_groups:
                type_groups[source_type] = []
            type_groups[source_type].append(source)

        # Display sources grouped by type
        for source_type in sorted(type_groups.keys()):
            group_box = QGroupBox(f"{source_type} Sources")
            group_layout = QVBoxLayout()
            
            for source in type_groups[source_type]:
                # Create horizontal layout for checkbox + best estimate label
                row_layout = QHBoxLayout()
                
                checkbox = QCheckBox(f"{source['name']}")
                app_name = source.get('app_name', 'Unknown')
                
                # Auto-check games (except excluded ones)
                if source_type == 'Game' and source['name'] not in excluded_games:
                    checkbox.setChecked(True)
                    self.selected_sources.add(source['name'])
                    logger.debug(f"Auto-selected game: {source['name']}")
                else:
                    checkbox.setChecked(source['name'] in self.selected_sources)
                
                # Set tooltip with app name and exclusion hint
                tooltip = f"App: {app_name}\nRight-click to exclude"
                checkbox.setToolTip(tooltip)
                
                # Connect state change handler
                checkbox.stateChanged.connect(
                    lambda state, s=source: self.on_source_toggled(s, state)
                )
                
                # Add context menu for exclusion
                checkbox.setContextMenuPolicy(Qt.CustomContextMenu)
                checkbox.customContextMenuRequested.connect(
                    lambda pos, s=source, cb=checkbox: self.show_source_context_menu(s, cb, pos)
                )
                
                row_layout.addWidget(checkbox)
                
                # Add best estimate label if available (only for games)
                stream_purpose = source.get('stream_purpose', '')
                if stream_purpose and source_type == 'Game':
                    estimate_label = QLabel(f"(guess: {stream_purpose})")
                    estimate_label.setStyleSheet("color: #555; font-size: 10px; margin-left: 15px;")
                    estimate_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    estimate_label.setToolTip("Estimated based on audio buffer size - may be incorrect")
                    row_layout.addWidget(estimate_label)
                
                group_layout.addLayout(row_layout)
            
            group_layout.addStretch()
            group_box.setLayout(group_layout)
            self.sources_layout.addWidget(group_box)

        self.sources_layout.addStretch()
        self.sources_group.blockSignals(False)

    def show_source_context_menu(self, source, checkbox, pos):
        """Show context menu for source exclusion"""
        import logging
        logger = logging.getLogger(__name__)
        
        from PyQt5.QtWidgets import QMenu
        
        excluded_games = self.config.get_excluded_games()
        is_excluded = source['name'] in excluded_games
        
        menu = QMenu()
        
        if source['type'] == 'Game':
            if is_excluded:
                action = menu.addAction(f"✓ Include {source['name']} in auto-select")
                action.triggered.connect(
                    lambda: self.toggle_game_exclusion(source['name'], exclude=False)
                )
            else:
                action = menu.addAction(f"✗ Exclude {source['name']} from auto-select")
                action.triggered.connect(
                    lambda: self.toggle_game_exclusion(source['name'], exclude=True)
                )
            
            menu.popup(checkbox.mapToGlobal(pos))

    def toggle_game_exclusion(self, game_name: str, exclude: bool):
        """Toggle game exclusion and update UI"""
        import logging
        logger = logging.getLogger(__name__)
        
        if exclude:
            self.config.add_excluded_game(game_name)
            self.selected_sources.discard(game_name)
            logger.info(f"Excluded game from auto-select: {game_name}")
        else:
            self.config.remove_excluded_game(game_name)
            self.selected_sources.add(game_name)
            logger.info(f"Included game in auto-select: {game_name}")
        
        # Refresh UI to reflect changes
        self.update_sources_list()

    def on_source_toggled(self, source, state):
        """Handle source selection change"""
        if state == Qt.CheckState.Checked:
            self.selected_sources.add(source['name'])
        else:
            self.selected_sources.discard(source['name'])

    def apply_routing(self):
        """Apply the selected audio routing"""
        import logging
        logger = logging.getLogger(__name__)
        
        if not self.selected_sources:
            QMessageBox.warning(self, "Warning", "Please select at least one audio source")
            return

        try:
            steam_node_id = self.pipewire.steam_node_id
            if not steam_node_id:
                QMessageBox.critical(
                    self, "Steam Not Found", 
                    "Steam recording node not detected.\n\n"
                    "Make sure:\n"
                    "• Steam is running\n"
                    "• Steam Game Recording is enabled for your game\n"
                    "  (Steam → Settings → Game Recording)\n"
                    "• Steam is configured to use PipeWire (not PulseAudio)\n\n"
                    "Check: systemctl --user status wireplumber"
                )
                return

            selected_source_ids = [s['id'] for s in self.sources if s['name'] in self.selected_sources]
            
            logger.debug(f"apply_routing: selected_sources={self.selected_sources}")
            logger.debug(f"apply_routing: all sources={[(s['id'], s['name']) for s in self.sources]}")
            logger.debug(f"apply_routing: selected_source_ids={selected_source_ids}")
            logger.debug(f"apply_routing: steam_node_id={steam_node_id}")

            success, message = self.pipewire.create_audio_routing(selected_source_ids, steam_node_id)
            
            if success:
                QMessageBox.information(self, "Success", f"Audio routing applied!\n{message}\n\nSwitch to 'Current Routes' tab and click Refresh to verify.")
            else:
                QMessageBox.warning(self, "Partial Success", f"Some routes may have failed.\n{message}")
            
            # Small delay then update routes display
            self.route_check_timer = QTimer()
            self.route_check_timer.setSingleShot(True)
            self.route_check_timer.timeout.connect(self.update_current_routes)
            self.route_check_timer.start(500)  # 500ms delay
        except Exception as e:
            QMessageBox.critical(
                self, "Routing Failed", 
                f"Failed to create audio routes.\n\n"
                f"Error: {e}\n\n"
                f"Troubleshooting:\n"
                f"• Verify PipeWire is running: systemctl --user status wireplumber\n"
                f"• Check logs: ~/.cache/steam-pipewire-helper.log\n"
                f"• Try running: pw-cli list-objects Node"
            )

    def clear_all_routes(self):
        """Clear all audio routes to Steam and restore sink routing"""
        import logging
        logger = logging.getLogger(__name__)
        
        reply = QMessageBox.question(
            self, "Confirm",
            "Disconnect all audio sources from Steam recording?\nThis will restore default sink-based routing.",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                success, message = self.pipewire.disconnect_all_from_steam()
                
                # Reconnect sink to restore default behavior
                sink_success, sink_message = self.pipewire.reconnect_sink_to_steam()
                logger.info(f"Sink reconnected after clear: {sink_message}")
                
                combined_msg = f"Routes cleared.\n{message}\n\nSink routing restored: {sink_message}"
                QMessageBox.information(self, "Success", combined_msg)
                self.update_current_routes()
            except Exception as e:
                QMessageBox.critical(
                    self, "Error", 
                    f"Failed to clear routes.\n\n"
                    f"Error: {e}\n\n"
                    f"Troubleshooting:\n"
                    f"• Check PipeWire status: systemctl --user status wireplumber\n"
                    f"• List active routes: pw-cli list-objects Link\n"
                    f"• Ensure Steam is running"
                )

    def update_current_routes(self):
        """Update the list of current routes (background thread)"""
        self.routes_list.clear()
        self.routes_list.addItem("Loading routes...")
        
        self.route_update_thread = RouteRefreshThread(self.pipewire)
        self.route_update_thread.routes_updated.connect(self.on_routes_updated)
        self.route_update_thread.error_occurred.connect(self.on_route_error)
        self.route_update_thread.start()

    def on_routes_updated(self, routes):
        """Handle updated routes"""
        self.routes_list.clear()
        
        if not routes:
            item = QListWidgetItem("No active routes")
            item.setForeground(QColor("gray"))
            self.routes_list.addItem(item)
            # Clear the visual graph
            self.routes_scene.clear()
        else:
            for route in routes:
                channel = route.get('channel', 'Unknown')
                item_text = f"[Node {route['source_node_id']}] {route['source_name']} → Steam ({channel})"
                item = QListWidgetItem(item_text)
                item.setData(Qt.ItemDataRole.UserRole, QVariant(route['link_id']))
                self.routes_list.addItem(item)
            
            # Draw the visual graph
            self.draw_routes_graph(routes)

    def on_route_error(self, error):
        """Handle route update error"""
        self.routes_list.clear()
        item = QListWidgetItem(f"Error loading routes: {error}")
        item.setForeground(QColor("red"))
        self.routes_list.addItem(item)
        self.routes_scene.clear()

    def draw_routes_graph(self, routes):
        """Draw audio routes with individual source curves to Steam"""
        self.routes_scene.clear()
        
        # Dimensions - reduced by 20% for more compact display
        margin = 20
        icon_size = 28  # was 36
        cols = 2  # 2 sources per row for compact layout
        col_spacing = 104  # was 130
        row_spacing = 80  # was 100
        steam_x = 248  # was 310
        steam_icon_size = 28  # was 36
        
        icon_cache = IconCache()
        
        # Group routes by source
        sources = {}
        for route in routes:
            source_id = route['source_node_id']
            if source_id not in sources:
                sources[source_id] = {
                    'name': route['source_name'],
                    'routes': []
                }
            sources[source_id]['routes'].append(route)
        
        source_list = list(sources.items())
        source_positions = {}
        
        # Arrange sources in a grid (2 columns)
        num_sources = len(source_list)
        num_rows = (num_sources + cols - 1) // cols
        
        # Calculate total height - use fixed start position to prevent drift
        grid_height = (num_rows - 1) * row_spacing + icon_size
        start_y = margin  # Fixed starting position instead of calculating from scene height
        
        for idx, (source_id, source_info) in enumerate(source_list):
            source_name = source_info['name']
            
            # Calculate position in 2-column grid
            row = idx // cols
            col = idx % cols
            icon_x = margin + col * col_spacing
            icon_y = start_y + row * row_spacing
            
            # Get icon
            icon_pixmap = icon_cache.get_icon(source_name, icon_size)
            
            # Draw icon
            if not icon_pixmap.isNull():
                icon_item = QGraphicsPixmapItem(icon_pixmap)
                icon_item.setPos(icon_x, icon_y)
                self.routes_scene.addItem(icon_item)
            else:
                # Placeholder rectangle if icon fails
                placeholder = QGraphicsRectItem(icon_x, icon_y, icon_size, icon_size)
                placeholder.setBrush(QBrush(QColor("#555555")))
                placeholder.setPen(QPen(QColor("#888888"), 1))
                self.routes_scene.addItem(placeholder)
            
            # Add badge with source number if multiple sources
            if len(source_list) > 1:
                badge_text = str(idx + 1)
                badge = QGraphicsTextItem(badge_text)
                badge.setDefaultTextColor(QColor("#ffffff"))
                badge_font = QFont("Arial", 8)
                badge_font.setWeight(QFont.Bold)
                badge_font.setStyleStrategy(QFont.PreferAntialias)
                badge.setFont(badge_font)
                
                # Badge circle parameters
                badge_radius = 9
                badge_center_x = icon_x + icon_size - badge_radius + 2
                badge_center_y = icon_y - badge_radius + 2
                
                # Background circle
                badge_bg = QGraphicsEllipseItem(badge_center_x - badge_radius, 
                                               badge_center_y - badge_radius, 
                                               badge_radius * 2, badge_radius * 2)
                badge_bg.setBrush(QBrush(QColor("#1976D2")))
                badge_bg.setPen(QPen(QColor("#0D47A1"), 1.5))
                self.routes_scene.addItem(badge_bg)
                
                # Get text bounds to center it properly
                text_rect = badge.boundingRect()
                text_width = text_rect.width()
                text_height = text_rect.height()
                
                # Center text in the circle
                badge.setPos(badge_center_x - text_width / 2, badge_center_y - text_height / 2 - 2)
                self.routes_scene.addItem(badge)
            
            # Connection point at right edge of icon
            connection_x = icon_x + icon_size
            connection_y = icon_y + icon_size / 2
            source_positions[idx] = {
                'x': connection_x,
                'y': connection_y,
                'idx': idx
            }
            
            # Draw source name below icon
            text_item = QGraphicsTextItem(source_name)
            text_item.setDefaultTextColor(QColor("#e0e0e0"))
            font = QFont("Arial", 6)
            font.setStyleStrategy(QFont.PreferAntialias)
            text_item.setFont(font)
            text_item.setPos(icon_x, icon_y + icon_size + 2)
            self.routes_scene.addItem(text_item)
        
        # Calculate Steam position - centered vertically on grid
        bus_top = start_y
        bus_bottom = start_y + (num_rows - 1) * row_spacing
        steam_y = (bus_top + bus_bottom) / 2 - steam_icon_size / 2
        
        steam_icon_pixmap = icon_cache.get_icon("Steam", steam_icon_size)
        steam_icon_x = steam_x
        steam_icon_y = steam_y
        
        if not steam_icon_pixmap.isNull():
            steam_icon_item = QGraphicsPixmapItem(steam_icon_pixmap)
            steam_icon_item.setPos(steam_icon_x, steam_icon_y)
            self.routes_scene.addItem(steam_icon_item)
        else:
            placeholder = QGraphicsRectItem(steam_icon_x, steam_icon_y, steam_icon_size, steam_icon_size)
            placeholder.setBrush(QBrush(QColor("#555555")))
            placeholder.setPen(QPen(QColor("#888888"), 1))
            self.routes_scene.addItem(placeholder)
        
        steam_connection_x = steam_icon_x
        steam_connection_y = steam_icon_y + steam_icon_size / 2
        
        # Steam label
        steam_text = QGraphicsTextItem("Steam Game Recording")
        steam_text.setDefaultTextColor(QColor("#e0e0e0"))
        font = QFont("Arial", 6)
        font.setStyleStrategy(QFont.PreferAntialias)
        font.setWeight(QFont.Bold)
        steam_text.setFont(font)
        steam_text.setPos(steam_icon_x - 10, steam_icon_y + steam_icon_size + 2)
        self.routes_scene.addItem(steam_text)
        
        # Draw individual curves from each source to Steam
        pen = QPen(QColor("#42A5F5"), 2.5)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        
        # Offset to avoid overlapping icons
        curve_offset_x = 20
        
        steam_connection_x = steam_icon_x
        steam_connection_y = steam_icon_y + steam_icon_size / 2
        
        for src in source_positions.values():
            # Start curve from a point offset to the right to avoid icons
            start_x = src['x'] + curve_offset_x
            start_y = src['y']
            
            # Draw line from icon to curve start
            pre_line = QGraphicsLineItem(src['x'], src['y'], start_x, start_y)
            pre_line.setPen(pen)
            self.routes_scene.addItem(pre_line)
            
            # Individual curve from offset point to Steam
            path = QPainterPath(QPointF(start_x, start_y))
            
            # Control points for smooth curve
            ctrl1_x = start_x + (steam_connection_x - start_x) * 0.35
            ctrl2_x = start_x + (steam_connection_x - start_x) * 0.65
            
            path.cubicTo(ctrl1_x, start_y, ctrl2_x, steam_connection_y, 
                        steam_connection_x, steam_connection_y)
            
            path_item = QGraphicsPathItem(path)
            path_item.setPen(pen)
            self.routes_scene.addItem(path_item)
            
            # Dot at source connection
            src_dot = QGraphicsEllipseItem(src['x'] - 4, src['y'] - 4, 8, 8)
            src_dot.setBrush(QBrush(QColor("#42A5F5")))
            src_dot.setPen(QPen(QColor("#1976D2"), 1))
            self.routes_scene.addItem(src_dot)
        
        # Dot at steam connection
        steam_dot = QGraphicsEllipseItem(steam_connection_x - 4, steam_connection_y - 4, 8, 8)
        steam_dot.setBrush(QBrush(QColor("#42A5F5")))
        steam_dot.setPen(QPen(QColor("#1976D2"), 1))
        self.routes_scene.addItem(steam_dot)
        
        # Set fixed scene rect for consistent layout
        total_height = start_y + grid_height + margin + 50
        scene_width = steam_x + steam_icon_size + margin
        
        self.routes_scene.setSceneRect(0, 0, scene_width, total_height)
        
        # Reset view to show entire scene at consistent scale
        # Use resetTransform to avoid accumulation of transforms
        self.routes_graphics_view.resetTransform()
        self.routes_graphics_view.fitInView(self.routes_scene.sceneRect(), Qt.KeepAspectRatio)

    def update_system_info(self):
        """Update system information display"""
        info_lines = []
        
        try:
            info_lines.append("=== Steam Recording Node ===")
            steam_node = self.pipewire.get_recording_devices()
            if steam_node:
                for device in steam_node:
                    info_lines.append(f"ID: {device['id']}")
                    info_lines.append(f"Name: {device['name']}")
            else:
                info_lines.append("Steam node not found (is Steam running?)")
            
            info_lines.append("\n=== Detected Audio Sources ===")
            for source in self.sources:
                info_lines.append(f"ID: {source['id']}")
                info_lines.append(f"Name: {source['name']}")
                info_lines.append(f"Type: {source['type']}")
                info_lines.append(f"App: {source.get('app_name', 'Unknown')}")
                info_lines.append(f"Class: {source.get('media_class', 'Unknown')}")
                info_lines.append("")
        except Exception as e:
            info_lines.append(f"Error: {e}")
        
        self.info_text.setText("\n".join(info_lines))
    def on_settings_changed(self, new_settings):
        """Handle settings changes"""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.debug(f"Settings updated: {new_settings}")
        
        # Update internal settings
        self.settings = new_settings
        
        # Update routing instructions based on auto_apply setting
        self._update_routing_instructions()
        
        # Update info note based on both restore_default_on_close and minimize_to_tray settings
        restore_on_close = new_settings.get('restore_default_on_close', True)
        minimize_to_tray = new_settings.get('minimize_to_tray', True)
        
        if minimize_to_tray:
            info_text = "ℹ Minimize to tray enabled. " + ("Quitting will restore default routing" if restore_on_close else "Quitting will keep current routing")
        else:
            info_text = "ℹ Closing will restore default routing" if restore_on_close else "ℹ Closing will keep current routing"
        
        self.info_note.setText(info_text)
        
        # Update graphics view theme if theme setting changed
        self._update_graphics_view_theme()
    
    def _update_routing_instructions(self):
        """Update routing instructions text based on auto-apply setting"""
        auto_apply = self.settings.get('auto_apply_games', False)
        
        if auto_apply:
            text = (
                "Select audio sources you want to include in Steam recording.\n"
                "Only selected sources will be captured by Steam's game recording feature.\n\n"
                "🔄 <b>Auto-apply is ENABLED</b> - New games will be automatically routed to Steam.\n"
                "You can manually click '<b>Apply Routing</b>' to update connections at any time."
            )
        else:
            text = (
                "Select audio sources you want to include in Steam recording.\n"
                "Only selected sources will be captured by Steam's game recording feature.\n\n"
                "💡 <b>Auto-apply is DISABLED</b> - New games are detected and selected, but NOT connected.\n"
                "You must click '<b>Apply Routing</b>' button below to activate the connections."
            )
        
        self.routing_instructions.setText(text)
        
        # Restart auto-detect with new interval if it changed
        if self.auto_detect_timer:
            self.auto_detect_timer.stop()
            self.start_auto_detect()