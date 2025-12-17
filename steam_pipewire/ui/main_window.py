#!/usr/bin/env python3
"""Main application window for Steam Audio Isolator"""

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QCheckBox, QScrollArea, QGroupBox,
    QFileDialog, QMessageBox, QComboBox, QListWidget, QListWidgetItem,
    QTabWidget, QTextEdit, QSpinBox, QLineEdit, QSystemTrayIcon, QMenu, QAction
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QVariant, QTimer
from PyQt5.QtGui import QColor, QFont, QKeySequence, QIcon, QPixmap, QPainter
from steam_pipewire.pipewire.source_detector import SourceDetector
from steam_pipewire.pipewire.controller import PipeWireController
from steam_pipewire.utils.config import ConfigManager


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
        restore_group.setLayout(restore_layout)
        layout.addWidget(restore_group)
        
        # Auto-detect interval
        interval_group = QGroupBox("Source Auto-Detection")
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("Check for new audio sources every:"))
        self.interval_spinbox = QSpinBox()
        self.interval_spinbox.setMinimum(1)
        self.interval_spinbox.setMaximum(30)
        self.interval_spinbox.setValue(self.settings.get('auto_detect_interval', 3))
        self.interval_spinbox.setSuffix(" seconds")
        self.interval_spinbox.valueChanged.connect(self._on_settings_changed)
        interval_layout.addWidget(self.interval_spinbox)
        interval_layout.addStretch()
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
        
        # Keyboard shortcuts info
        shortcuts_group = QGroupBox("Keyboard Shortcuts")
        shortcuts_layout = QVBoxLayout()
        shortcuts_info = QLabel(
            "<b>Default Shortcuts:</b><br>"
            "• <b>Ctrl+Shift+A</b>: Apply routing<br>"
            "• <b>Ctrl+Shift+C</b>: Clear all routes<br>"
            "• <b>F5</b>: Refresh sources<br>"
            "• <b>Ctrl+Shift+H</b>: Hide/Show window"
        )
        shortcuts_info.setTextFormat(Qt.RichText)
        shortcuts_layout.addWidget(shortcuts_info)
        shortcuts_group.setLayout(shortcuts_layout)
        layout.addWidget(shortcuts_group)
        
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
        self.settings['restore_default_on_close'] = self.restore_checkbox.isChecked()
        self.settings['auto_detect_interval'] = self.interval_spinbox.value()
        self.settings['minimize_to_tray'] = self.tray_checkbox.isChecked()
        
        self.config.save_settings(self.settings)
        self.settings_changed.emit(self.settings)
        
        # Show confirmation
        QMessageBox.information(self, "Success", "Settings saved successfully!")


class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Steam Audio Isolator")
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
        
        # System tray
        self.tray_icon = None
        self.is_closing = False
        
        # Set custom colored icon for window
        self.setWindowIcon(self.create_app_icon())

        self.init_ui()
        self.setup_system_tray()
        self.setup_keyboard_shortcuts()
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
    
    def setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts"""
        import logging
        from PyQt5.QtWidgets import QShortcut
        logger = logging.getLogger(__name__)
        
        shortcuts = self.settings.get('shortcuts', {
            'apply_routing': 'Ctrl+Shift+A',
            'clear_routes': 'Ctrl+Shift+C',
            'refresh_sources': 'F5',
            'toggle_window': 'Ctrl+Shift+H'
        })
        
        # Apply routing shortcut
        apply_shortcut = QShortcut(QKeySequence(shortcuts.get('apply_routing', 'Ctrl+Shift+A')), self)
        apply_shortcut.activated.connect(self.apply_routing)
        
        # Clear routes shortcut
        clear_shortcut = QShortcut(QKeySequence(shortcuts.get('clear_routes', 'Ctrl+Shift+C')), self)
        clear_shortcut.activated.connect(self.clear_all_routes)
        
        # Refresh sources shortcut
        refresh_shortcut = QShortcut(QKeySequence(shortcuts.get('refresh_sources', 'F5')), self)
        refresh_shortcut.activated.connect(self.detect_sources)
        
        # Toggle window visibility shortcut
        toggle_shortcut = QShortcut(QKeySequence(shortcuts.get('toggle_window', 'Ctrl+Shift+H')), self)
        toggle_shortcut.activated.connect(self.toggle_visibility)
        
        logger.debug(f"Keyboard shortcuts initialized: {shortcuts}")
    
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

        # Instructions
        instructions = QLabel(
            "Select audio sources you want to include in Steam recording.\n"
            "Only selected sources will be captured by Steam's game recording feature."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

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
        apply_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 5px;")
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

        self.routes_list = QListWidget()
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
            "<li><b>Settings Tab:</b> Configure behavior and shortcuts</li>"
            "</ol>"
            
            "<h3>Keyboard Shortcuts</h3>"
            "<p>"
            "<b>Ctrl+Shift+A</b> - Apply routing<br>"
            "<b>Ctrl+Shift+C</b> - Clear all routes<br>"
            "<b>F5</b> - Refresh sources<br>"
            "<b>Ctrl+Shift+H</b> - Hide/Show window"
            "</p>"
            
            "<h3>Technology</h3>"
            "<p>Uses <b>PipeWire</b> audio system to route audio streams directly between "
            "applications without going through the system mixer. This provides clean, "
            "isolated game audio for your Steam recordings.</p>"
            
            "<p style='margin-top: 20px; color: #666; font-size: 10px;'>"
            "Version 0.1.0 | "
            "Config: ~/.config/steam-audio-isolator/ | "
            "Logs: ~/.cache/steam-audio-isolator.log"
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
            QMessageBox.information(self, "Success", f"Profile '{profile_name}' loaded!\n\nSelected sources:\n" + "\n".join(sources_to_select))
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
            auto_apply_enabled = self.settings.get('auto_apply_games', True)
            
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
        
        # Actually closing the application - show confirmation
        if not hasattr(self, '_quit_confirmed') or not self._quit_confirmed:
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
        else:
            for route in routes:
                item_text = f"[Node {route['source_node_id']}] {route['source_name']} → Steam"
                item = QListWidgetItem(item_text)
                item.setData(Qt.ItemDataRole.UserRole, QVariant(route['link_id']))
                self.routes_list.addItem(item)

    def on_route_error(self, error):
        """Handle route update error"""
        self.routes_list.clear()
        item = QListWidgetItem(f"Error loading routes: {error}")
        item.setForeground(QColor("red"))
        self.routes_list.addItem(item)

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
        
        # Update info note based on both restore_default_on_close and minimize_to_tray settings
        restore_on_close = new_settings.get('restore_default_on_close', True)
        minimize_to_tray = new_settings.get('minimize_to_tray', True)
        
        if minimize_to_tray:
            info_text = "ℹ Minimize to tray enabled. " + ("Quitting will restore default routing" if restore_on_close else "Quitting will keep current routing")
        else:
            info_text = "ℹ Closing will restore default routing" if restore_on_close else "ℹ Closing will keep current routing"
        
        self.info_note.setText(info_text)
        
        # Restart auto-detect with new interval if it changed
        if self.auto_detect_timer:
            self.auto_detect_timer.stop()
            self.start_auto_detect()