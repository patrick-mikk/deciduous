"""
Settings Dialog for PyQt6 UofT Course Dashboard
Comprehensive application preferences and configuration
"""

from typing import Dict, Any
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QGroupBox, QLabel, QLineEdit, QPushButton, QCheckBox,
    QComboBox, QSpinBox, QSlider, QTextEdit, QFormLayout,
    QFileDialog, QMessageBox, QDialogButtonBox, QFrame,
    QColorDialog, QFontDialog, QProgressBar, QListWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QSettings
from PyQt6.QtGui import QFont, QColor, QPalette
import json
from pathlib import Path

class GeneralSettingsTab(QWidget):
    """General application settings"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Startup behavior
        startup_group = QGroupBox("Startup Behavior")
        startup_layout = QFormLayout(startup_group)

        self.auto_refresh_check = QCheckBox("Auto-refresh data on startup")
        self.auto_refresh_check.setToolTip("Automatically refresh course data when the application starts")
        startup_layout.addRow("Data Loading:", self.auto_refresh_check)

        self.remember_window_check = QCheckBox("Remember window size and position")
        self.remember_window_check.setToolTip("Save and restore window dimensions between sessions")
        startup_layout.addRow("Window State:", self.remember_window_check)

        self.startup_tab_combo = QComboBox()
        self.startup_tab_combo.addItems([
            "Academic Overview", "Course Management", "Degree Planning", "Analytics & Reports"
        ])
        self.startup_tab_combo.setToolTip("Which tab to show when the application starts")
        startup_layout.addRow("Default Tab:", self.startup_tab_combo)

        layout.addWidget(startup_group)

        # Auto-save settings
        autosave_group = QGroupBox("Auto-Save Settings")
        autosave_layout = QFormLayout(autosave_group)

        self.autosave_enabled_check = QCheckBox("Enable auto-save")
        self.autosave_enabled_check.setToolTip("Automatically save changes without user intervention")
        autosave_layout.addRow("Auto-Save:", self.autosave_enabled_check)

        self.autosave_interval_spin = QSpinBox()
        self.autosave_interval_spin.setRange(1, 60)
        self.autosave_interval_spin.setValue(5)
        self.autosave_interval_spin.setSuffix(" minutes")
        self.autosave_interval_spin.setToolTip("How often to automatically save changes")
        autosave_layout.addRow("Save Interval:", self.autosave_interval_spin)

        layout.addWidget(autosave_group)

        # Confirmation dialogs
        confirm_group = QGroupBox("Confirmation Dialogs")
        confirm_layout = QFormLayout(confirm_group)

        self.confirm_delete_check = QCheckBox("Confirm before deleting courses")
        self.confirm_delete_check.setChecked(True)
        confirm_layout.addRow("Delete Confirmation:", self.confirm_delete_check)

        self.confirm_bulk_check = QCheckBox("Confirm bulk operations")
        self.confirm_bulk_check.setChecked(True)
        confirm_layout.addRow("Bulk Operations:", self.confirm_bulk_check)

        layout.addWidget(confirm_group)

        layout.addStretch()

class DisplaySettingsTab(QWidget):
    """Display and appearance settings"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Theme settings
        theme_group = QGroupBox("Theme and Appearance")
        theme_layout = QFormLayout(theme_group)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["System Default", "Light", "Dark", "High Contrast"])
        self.theme_combo.setToolTip("Choose the application color theme")
        theme_layout.addRow("Theme:", self.theme_combo)

        self.font_button = QPushButton("Choose Font...")
        self.font_button.setToolTip("Select the application font family and size")
        self.font_button.clicked.connect(self.choose_font)
        theme_layout.addRow("Application Font:", self.font_button)

        self.accent_color_button = QPushButton("Accent Color...")
        self.accent_color_button.setToolTip("Choose the accent color for buttons and highlights")
        self.accent_color_button.clicked.connect(self.choose_accent_color)
        theme_layout.addRow("Accent Color:", self.accent_color_button)

        layout.addWidget(theme_group)

        # Table settings
        table_group = QGroupBox("Table Display")
        table_layout = QFormLayout(table_group)

        self.alternating_rows_check = QCheckBox("Alternating row colors")
        self.alternating_rows_check.setChecked(True)
        table_layout.addRow("Row Colors:", self.alternating_rows_check)

        self.show_grid_check = QCheckBox("Show grid lines")
        self.show_grid_check.setChecked(False)
        table_layout.addRow("Grid Lines:", self.show_grid_check)

        self.row_height_spin = QSpinBox()
        self.row_height_spin.setRange(20, 50)
        self.row_height_spin.setValue(25)
        self.row_height_spin.setSuffix(" px")
        table_layout.addRow("Row Height:", self.row_height_spin)

        layout.addWidget(table_group)

        # Chart settings
        chart_group = QGroupBox("Charts and Graphs")
        chart_layout = QFormLayout(chart_group)

        self.animated_charts_check = QCheckBox("Animated chart transitions")
        self.animated_charts_check.setChecked(True)
        chart_layout.addRow("Animations:", self.animated_charts_check)

        self.chart_style_combo = QComboBox()
        self.chart_style_combo.addItems(["Modern", "Classic", "Minimal"])
        chart_layout.addRow("Chart Style:", self.chart_style_combo)

        layout.addWidget(chart_group)

        layout.addStretch()

    def choose_font(self):
        """Open font selection dialog"""
        font, ok = QFontDialog.getFont()
        if ok:
            self.current_font = font
            self.font_button.setText(f"{font.family()} {font.pointSize()}pt")

    def choose_accent_color(self):
        """Open color selection dialog"""
        color = QColorDialog.getColor()
        if color.isValid():
            self.current_accent_color = color
            self.accent_color_button.setStyleSheet(f"background-color: {color.name()}")

class DataSettingsTab(QWidget):
    """Data management and backup settings"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Database settings
        database_group = QGroupBox("Database Configuration")
        database_layout = QFormLayout(database_group)

        self.db_path_edit = QLineEdit()
        self.db_path_edit.setReadOnly(True)
        self.db_path_edit.setToolTip("Location of the application database file")

        db_path_layout = QHBoxLayout()
        db_path_layout.addWidget(self.db_path_edit)

        browse_db_btn = QPushButton("Browse...")
        browse_db_btn.clicked.connect(self.browse_database_path)
        db_path_layout.addWidget(browse_db_btn)

        database_layout.addRow("Database Location:", db_path_layout)

        layout.addWidget(database_group)

        # Backup settings
        backup_group = QGroupBox("Backup and Export")
        backup_layout = QFormLayout(backup_group)

        self.auto_backup_check = QCheckBox("Enable automatic backups")
        self.auto_backup_check.setToolTip("Automatically create database backups")
        backup_layout.addRow("Auto Backup:", self.auto_backup_check)

        self.backup_frequency_combo = QComboBox()
        self.backup_frequency_combo.addItems(["Daily", "Weekly", "Monthly"])
        backup_layout.addRow("Backup Frequency:", self.backup_frequency_combo)

        self.backup_path_edit = QLineEdit()
        self.backup_path_edit.setReadOnly(True)

        backup_path_layout = QHBoxLayout()
        backup_path_layout.addWidget(self.backup_path_edit)

        browse_backup_btn = QPushButton("Browse...")
        browse_backup_btn.clicked.connect(self.browse_backup_path)
        backup_path_layout.addWidget(browse_backup_btn)

        backup_layout.addRow("Backup Location:", backup_path_layout)

        layout.addWidget(backup_group)

        # Import/Export formats
        format_group = QGroupBox("Import/Export Formats")
        format_layout = QFormLayout(format_group)

        self.export_format_combo = QComboBox()
        self.export_format_combo.addItems(["CSV", "Excel", "JSON", "PDF"])
        format_layout.addRow("Default Export Format:", self.export_format_combo)

        self.include_grades_check = QCheckBox("Include grades in exports")
        self.include_grades_check.setChecked(True)
        format_layout.addRow("Export Options:", self.include_grades_check)

        layout.addWidget(format_group)

        layout.addStretch()

    def browse_database_path(self):
        """Browse for database file location"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Choose Database Location",
            self.db_path_edit.text(),
            "Database Files (*.db);;All Files (*)"
        )
        if file_path:
            self.db_path_edit.setText(file_path)

    def browse_backup_path(self):
        """Browse for backup directory"""
        dir_path = QFileDialog.getExistingDirectory(
            self, "Choose Backup Directory",
            self.backup_path_edit.text()
        )
        if dir_path:
            self.backup_path_edit.setText(dir_path)

class AdvancedSettingsTab(QWidget):
    """Advanced settings and experimental features"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Performance settings
        performance_group = QGroupBox("Performance Tuning")
        performance_layout = QFormLayout(performance_group)

        self.cache_size_spin = QSpinBox()
        self.cache_size_spin.setRange(10, 1000)
        self.cache_size_spin.setValue(100)
        self.cache_size_spin.setSuffix(" MB")
        self.cache_size_spin.setToolTip("Maximum memory to use for caching")
        performance_layout.addRow("Cache Size:", self.cache_size_spin)

        self.lazy_loading_check = QCheckBox("Enable lazy loading")
        self.lazy_loading_check.setChecked(True)
        self.lazy_loading_check.setToolTip("Load tab content only when needed")
        performance_layout.addRow("Lazy Loading:", self.lazy_loading_check)

        self.background_refresh_check = QCheckBox("Background data refresh")
        self.background_refresh_check.setToolTip("Refresh data in background without blocking UI")
        performance_layout.addRow("Background Refresh:", self.background_refresh_check)

        layout.addWidget(performance_group)

        # Debug settings
        debug_group = QGroupBox("Debug and Logging")
        debug_layout = QFormLayout(debug_group)

        self.debug_mode_check = QCheckBox("Enable debug mode")
        self.debug_mode_check.setToolTip("Show additional debug information")
        debug_layout.addRow("Debug Mode:", self.debug_mode_check)

        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["ERROR", "WARNING", "INFO", "DEBUG"])
        self.log_level_combo.setCurrentText("INFO")
        debug_layout.addRow("Log Level:", self.log_level_combo)

        self.verbose_errors_check = QCheckBox("Verbose error messages")
        self.verbose_errors_check.setToolTip("Show detailed error information")
        debug_layout.addRow("Error Detail:", self.verbose_errors_check)

        layout.addWidget(debug_group)

        # Experimental features
        experimental_group = QGroupBox("Experimental Features")
        experimental_layout = QFormLayout(experimental_group)

        self.ai_suggestions_check = QCheckBox("AI course suggestions")
        self.ai_suggestions_check.setToolTip("Enable experimental AI-powered course recommendations")
        experimental_layout.addRow("AI Features:", self.ai_suggestions_check)

        self.beta_features_check = QCheckBox("Beta features")
        self.beta_features_check.setToolTip("Enable access to experimental features")
        experimental_layout.addRow("Beta Access:", self.beta_features_check)

        layout.addWidget(experimental_group)

        layout.addStretch()

class SettingsDialog(QDialog):
    """Main settings dialog with tabbed interface"""

    settings_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings()
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        """Setup the dialog layout"""
        self.setWindowTitle("Course Dashboard Settings")
        self.setFixedSize(600, 500)

        layout = QVBoxLayout(self)

        # Create tab widget
        self.tab_widget = QTabWidget()

        # Create tabs
        self.general_tab = GeneralSettingsTab()
        self.display_tab = DisplaySettingsTab()
        self.data_tab = DataSettingsTab()
        self.advanced_tab = AdvancedSettingsTab()

        # Add tabs
        self.tab_widget.addTab(self.general_tab, "General")
        self.tab_widget.addTab(self.display_tab, "Display")
        self.tab_widget.addTab(self.data_tab, "Data")
        self.tab_widget.addTab(self.advanced_tab, "Advanced")

        layout.addWidget(self.tab_widget)

        # Button box
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel |
            QDialogButtonBox.StandardButton.Apply |
            QDialogButtonBox.StandardButton.RestoreDefaults
        )

        button_box.accepted.connect(self.accept_settings)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self.apply_settings)
        button_box.button(QDialogButtonBox.StandardButton.RestoreDefaults).clicked.connect(self.restore_defaults)

        layout.addWidget(button_box)

    def load_settings(self):
        """Load settings from QSettings"""
        # General settings
        self.general_tab.auto_refresh_check.setChecked(
            self.settings.value("general/auto_refresh", True, bool)
        )
        self.general_tab.remember_window_check.setChecked(
            self.settings.value("general/remember_window", True, bool)
        )
        startup_tab = self.settings.value("general/startup_tab", 0, int)
        self.general_tab.startup_tab_combo.setCurrentIndex(startup_tab)

        self.general_tab.autosave_enabled_check.setChecked(
            self.settings.value("general/autosave_enabled", True, bool)
        )
        self.general_tab.autosave_interval_spin.setValue(
            self.settings.value("general/autosave_interval", 5, int)
        )

        # Display settings
        theme_index = self.settings.value("display/theme", 0, int)
        self.display_tab.theme_combo.setCurrentIndex(theme_index)

        self.display_tab.alternating_rows_check.setChecked(
            self.settings.value("display/alternating_rows", True, bool)
        )
        self.display_tab.show_grid_check.setChecked(
            self.settings.value("display/show_grid", False, bool)
        )

        # Data settings
        db_path = self.settings.value("data/database_path", "", str)
        self.data_tab.db_path_edit.setText(db_path)

        self.data_tab.auto_backup_check.setChecked(
            self.settings.value("data/auto_backup", False, bool)
        )

        # Advanced settings
        self.advanced_tab.debug_mode_check.setChecked(
            self.settings.value("advanced/debug_mode", False, bool)
        )
        self.advanced_tab.lazy_loading_check.setChecked(
            self.settings.value("advanced/lazy_loading", True, bool)
        )

    def save_settings(self):
        """Save settings to QSettings"""
        # General settings
        self.settings.setValue("general/auto_refresh",
                             self.general_tab.auto_refresh_check.isChecked())
        self.settings.setValue("general/remember_window",
                             self.general_tab.remember_window_check.isChecked())
        self.settings.setValue("general/startup_tab",
                             self.general_tab.startup_tab_combo.currentIndex())
        self.settings.setValue("general/autosave_enabled",
                             self.general_tab.autosave_enabled_check.isChecked())
        self.settings.setValue("general/autosave_interval",
                             self.general_tab.autosave_interval_spin.value())

        # Display settings
        self.settings.setValue("display/theme",
                             self.display_tab.theme_combo.currentIndex())
        self.settings.setValue("display/alternating_rows",
                             self.display_tab.alternating_rows_check.isChecked())
        self.settings.setValue("display/show_grid",
                             self.display_tab.show_grid_check.isChecked())

        # Data settings
        self.settings.setValue("data/database_path",
                             self.data_tab.db_path_edit.text())
        self.settings.setValue("data/auto_backup",
                             self.data_tab.auto_backup_check.isChecked())

        # Advanced settings
        self.settings.setValue("advanced/debug_mode",
                             self.advanced_tab.debug_mode_check.isChecked())
        self.settings.setValue("advanced/lazy_loading",
                             self.advanced_tab.lazy_loading_check.isChecked())

    def get_settings_dict(self) -> Dict[str, Any]:
        """Get all settings as a dictionary"""
        return {
            "general": {
                "auto_refresh": self.general_tab.auto_refresh_check.isChecked(),
                "remember_window": self.general_tab.remember_window_check.isChecked(),
                "startup_tab": self.general_tab.startup_tab_combo.currentIndex(),
                "autosave_enabled": self.general_tab.autosave_enabled_check.isChecked(),
                "autosave_interval": self.general_tab.autosave_interval_spin.value(),
            },
            "display": {
                "theme": self.display_tab.theme_combo.currentIndex(),
                "alternating_rows": self.display_tab.alternating_rows_check.isChecked(),
                "show_grid": self.display_tab.show_grid_check.isChecked(),
                "row_height": self.display_tab.row_height_spin.value(),
            },
            "data": {
                "database_path": self.data_tab.db_path_edit.text(),
                "auto_backup": self.data_tab.auto_backup_check.isChecked(),
                "backup_frequency": self.data_tab.backup_frequency_combo.currentText(),
                "export_format": self.data_tab.export_format_combo.currentText(),
            },
            "advanced": {
                "debug_mode": self.advanced_tab.debug_mode_check.isChecked(),
                "lazy_loading": self.advanced_tab.lazy_loading_check.isChecked(),
                "cache_size": self.advanced_tab.cache_size_spin.value(),
                "log_level": self.advanced_tab.log_level_combo.currentText(),
            }
        }

    def apply_settings(self):
        """Apply settings without closing dialog"""
        self.save_settings()
        settings_dict = self.get_settings_dict()
        self.settings_changed.emit(settings_dict)

    def accept_settings(self):
        """Accept and apply settings"""
        self.apply_settings()
        self.accept()

    def restore_defaults(self):
        """Restore default settings"""
        reply = QMessageBox.question(
            self, "Restore Defaults",
            "This will reset all settings to their default values. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.settings.clear()
            self.load_settings()