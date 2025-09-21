"""
Main Window for PyQt6 UofT Course Dashboard
Modern interface with enhanced user experience
"""

import sys
import os
from pathlib import Path
from typing import Optional

try:
    from PyQt6.QtWidgets import (
        QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
        QMenuBar, QStatusBar, QLabel, QApplication, QMessageBox,
        QPushButton, QFrame, QSplitter
    )
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal
    from PyQt6.QtGui import QIcon, QFont, QAction, QPixmap
except ImportError:
    print("PyQt6 not available. Please install: pip install PyQt6>=6.4.0")
    sys.exit(1)

# Import existing core modules
sys.path.append(str(Path(__file__).parent.parent))
from main import UnifiedCourseDatabase, RequirementsCalculator, AcademicCalendarScraper
from gui_qt.utils.data_manager import UnifiedDataManager


class MainWindow(QMainWindow):
    """Modern main application window for UofT Course Dashboard"""

    def __init__(self):
        super().__init__()

        # Initialize core components (from existing tkinter version)
        self.database = None
        self.scraper = None
        self.requirements_calculator = None
        self.data_manager = None

        # Initialize UI
        self.init_database()
        self.init_ui()
        self.setup_menu_bar()
        self.setup_status_bar()
        self.apply_modern_styling()

        # Load initial data
        self.load_initial_data()

    def init_database(self):
        """Initialize database and core components"""
        try:
            self.database = UnifiedCourseDatabase()
            self.requirements_calculator = RequirementsCalculator(self.database)

            # Initialize unified data manager
            self.data_manager = UnifiedDataManager(self.database)
            self.setup_data_manager_connections()

            # Initialize scraper if available (defer to avoid blocking)
            self.scraper = None
            print("Web scraper initialization deferred for better startup performance")

            self.status_message("Database and data manager initialized successfully")

        except Exception as e:
            QMessageBox.critical(self, "Database Error",
                               f"Failed to initialize database: {e}")
            sys.exit(1)

    def init_scraper_if_needed(self):
        """Initialize scraper on-demand when needed"""
        if self.scraper is None:
            try:
                from main import AcademicCalendarScraper
                self.scraper = AcademicCalendarScraper()
                self.status_message("Web scraper initialized successfully")
                return True
            except Exception as e:
                self.status_message(f"Web scraper not available: {e}")
                return False
        return True

    def init_ui(self):
        """Initialize the main user interface"""
        self.setWindowTitle("University of Toronto Course Dashboard - Faculty of Arts & Science")
        self.setGeometry(100, 100, 1600, 1000)
        self.setMinimumSize(1200, 800)

        # Central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(5)

        # Create header section
        self.create_header_section(main_layout)

        # Create main tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.TabPosition.North)
        self.tab_widget.setMovable(True)
        self.tab_widget.setTabsClosable(False)

        main_layout.addWidget(self.tab_widget)

        # Create tabs (placeholders for now)
        self.create_tabs()

    def create_header_section(self, layout):
        """Create header section with title and quick actions"""
        header_frame = QFrame()
        header_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        header_frame.setMaximumHeight(80)

        header_layout = QHBoxLayout(header_frame)

        # Title section
        title_label = QLabel("University of Toronto Course Dashboard")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #000000; background-color: transparent;")

        subtitle_label = QLabel("Faculty of Arts & Science Academic Management System")
        subtitle_font = QFont()
        subtitle_font.setPointSize(11)
        subtitle_label.setFont(subtitle_font)
        subtitle_label.setStyleSheet("color: #333333; background-color: transparent; font-style: italic;")

        title_layout = QVBoxLayout()
        title_layout.addWidget(title_label)
        title_layout.addWidget(subtitle_label)
        title_layout.setSpacing(2)

        header_layout.addLayout(title_layout)
        header_layout.addStretch()

        # Quick action buttons
        self.create_quick_actions(header_layout)

        layout.addWidget(header_frame)

    def create_quick_actions(self, layout):
        """Create quick action buttons in header"""
        academic_calendar_btn = QPushButton("Academic Calendar")
        degree_explorer_btn = QPushButton("Degree Explorer")
        refresh_btn = QPushButton("Refresh Data")

        # Style buttons with high contrast
        button_style = """
            QPushButton {
                background-color: #0066cc;
                color: #ffffff;
                border: 2px solid #0066cc;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 9pt;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #0052a3;
                border-color: #0052a3;
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: #004085;
                border-color: #004085;
                color: #ffffff;
            }
        """

        for btn in [academic_calendar_btn, degree_explorer_btn, refresh_btn]:
            btn.setStyleSheet(button_style)
            layout.addWidget(btn)

        # Connect buttons
        academic_calendar_btn.clicked.connect(self.open_academic_calendar)
        degree_explorer_btn.clicked.connect(self.open_degree_explorer)
        refresh_btn.clicked.connect(self.refresh_all_data)

    def create_tabs(self):
        """Create main application tabs with Phase 2C enhanced layout"""
        # Tab 1: Academic Overview - Dashboard with status cards and progress
        try:
            from gui_qt.widgets.academic_overview import AcademicOverviewWidget
            self.overview_tab = AcademicOverviewWidget(self.database, self.data_manager)
            self.overview_tab.course_search_requested.connect(self.on_course_search_requested)
            self.overview_tab.tab_switch_requested.connect(self.tab_widget.setCurrentIndex)
            self.tab_widget.addTab(self.overview_tab, "Academic Overview")
        except ImportError as e:
            overview_tab = QWidget()
            overview_layout = QVBoxLayout(overview_tab)
            overview_layout.addWidget(QLabel(f"Academic Overview Tab\n\nError loading widget: {e}"))
            self.tab_widget.addTab(overview_tab, "Academic Overview")

        # Tab 2: Course Management - Search, transcript, and course details
        try:
            from gui_qt.widgets.course_management import CourseManagementWidget
            self.course_tab = CourseManagementWidget(self.database, self.data_manager)
            self.course_tab.courses_modified.connect(self.refresh_all_data)
            self.tab_widget.addTab(self.course_tab, "Course Management")
        except ImportError as e:
            course_tab = QWidget()
            course_layout = QVBoxLayout(course_tab)
            course_layout.addWidget(QLabel(f"Course Management Tab\n\nError loading widget: {e}"))
            self.tab_widget.addTab(course_tab, "Course Management")

        # Tab 3: Degree Planning - Requirements tree and planning workspace
        try:
            from gui_qt.widgets.degree_planning import DegreePlanningWidget
            self.planning_tab = DegreePlanningWidget(self.database, self.data_manager)
            self.planning_tab.courses_modified.connect(self.refresh_all_data)
            self.tab_widget.addTab(self.planning_tab, "Degree Planning")
        except ImportError as e:
            planning_tab = QWidget()
            planning_layout = QVBoxLayout(planning_tab)
            planning_layout.addWidget(QLabel(f"Degree Planning Tab\n\nError loading widget: {e}"))
            self.tab_widget.addTab(planning_tab, "Degree Planning")

        # Tab 4: Analytics & Reports - Performance analytics and export
        try:
            from gui_qt.widgets.analytics_reports import AnalyticsReportsWidget
            self.analytics_tab = AnalyticsReportsWidget(self.database, self.data_manager)
            self.tab_widget.addTab(self.analytics_tab, "Analytics & Reports")
        except ImportError as e:
            analytics_tab = QWidget()
            analytics_layout = QVBoxLayout(analytics_tab)
            analytics_layout.addWidget(QLabel(f"Analytics & Reports Tab\n\nError loading widget: {e}"))
            self.tab_widget.addTab(analytics_tab, "Analytics & Reports")

    def setup_menu_bar(self):
        """Setup application menu bar"""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu('&File')

        import_action = QAction('&Import Transcript...', self)
        import_action.setShortcut('Ctrl+I')
        import_action.triggered.connect(self.import_transcript)
        file_menu.addAction(import_action)

        export_action = QAction('&Export Transcript...', self)
        export_action.setShortcut('Ctrl+E')
        export_action.triggered.connect(self.export_transcript)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        new_course_action = QAction('&Add New Course...', self)
        new_course_action.setShortcut('Ctrl+N')
        new_course_action.triggered.connect(self.add_new_course)
        file_menu.addAction(new_course_action)

        file_menu.addSeparator()

        exit_action = QAction('E&xit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Tools menu
        tools_menu = menubar.addMenu('&Tools')

        refresh_action = QAction('&Refresh All Data', self)
        refresh_action.setShortcut('F5')
        refresh_action.triggered.connect(self.refresh_all_data)
        tools_menu.addAction(refresh_action)

        tools_menu.addSeparator()

        search_action = QAction('&Search Courses...', self)
        search_action.setShortcut('Ctrl+F')
        search_action.triggered.connect(self.focus_search)
        tools_menu.addAction(search_action)

        global_search_action = QAction('&Global Search...', self)
        global_search_action.setShortcut('Ctrl+Shift+F')
        global_search_action.triggered.connect(self.show_global_search)
        tools_menu.addAction(global_search_action)

        tools_menu.addSeparator()

        settings_action = QAction('&Settings...', self)
        settings_action.setShortcut('Ctrl+,')
        settings_action.triggered.connect(self.show_settings)
        tools_menu.addAction(settings_action)

        # View menu
        view_menu = menubar.addMenu('&View')

        # Tab navigation shortcuts
        overview_action = QAction('&Academic Overview', self)
        overview_action.setShortcut('Ctrl+1')
        overview_action.triggered.connect(lambda: self.tab_widget.setCurrentIndex(0))
        view_menu.addAction(overview_action)

        course_action = QAction('&Course Management', self)
        course_action.setShortcut('Ctrl+2')
        course_action.triggered.connect(lambda: self.tab_widget.setCurrentIndex(1))
        view_menu.addAction(course_action)

        planning_action = QAction('&Degree Planning', self)
        planning_action.setShortcut('Ctrl+3')
        planning_action.triggered.connect(lambda: self.tab_widget.setCurrentIndex(2))
        view_menu.addAction(planning_action)

        analytics_action = QAction('&Analytics & Reports', self)
        analytics_action.setShortcut('Ctrl+4')
        analytics_action.triggered.connect(lambda: self.tab_widget.setCurrentIndex(3))
        view_menu.addAction(analytics_action)

        # Help menu
        help_menu = menubar.addMenu('&Help')

        about_action = QAction('&About...', self)
        about_action.setShortcut('F1')
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def setup_status_bar(self):
        """Setup application status bar"""
        self.status_bar = self.statusBar()

        # Left side status
        self.status_label = QLabel("Ready")
        self.status_bar.addWidget(self.status_label)

        # Right side info
        self.status_bar.addPermanentWidget(QLabel("Faculty of Arts & Science"))

    def apply_modern_styling(self):
        """Apply native PyQt6 styling with system integration"""
        try:
            # Use native PyQt6 styling instead of custom CSS
            self.apply_native_styling()
            print("Native PyQt6 styling applied successfully")
        except Exception as e:
            print(f"Error applying native styling: {e}, using fallback")
            self.apply_fallback_styling()

    def apply_native_styling(self):
        """Apply native PyQt6 styling using QPalette and built-in properties"""
        from PyQt6.QtGui import QPalette, QColor
        from PyQt6.QtWidgets import QApplication

        # Get application instance
        app = QApplication.instance()

        # Create and configure palette for consistent theming
        palette = QPalette()

        # Set base colors for light theme
        palette.setColor(QPalette.ColorRole.Window, QColor(255, 255, 255))          # Background
        palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))            # Text
        palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))            # Input backgrounds
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(248, 248, 248))   # Alternate rows
        palette.setColor(QPalette.ColorRole.Text, QColor(0, 0, 0))                  # Input text
        palette.setColor(QPalette.ColorRole.Button, QColor(240, 240, 240))          # Button background
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(0, 0, 0))            # Button text
        palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 102, 204))         # Selection background
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255)) # Selection text

        # Apply palette to application
        app.setPalette(palette)

        # Configure fonts
        font = app.font()
        font.setFamily("Segoe UI")
        font.setPointSize(9)
        app.setFont(font)

        # Apply minimal styling for professional appearance
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 4px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QTabWidget::pane {
                border: 1px solid #cccccc;
                background-color: white;
            }
            QTabBar::tab {
                padding: 8px 16px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                font-weight: bold;
            }
            QProgressBar {
                border: 1px solid #cccccc;
                border-radius: 3px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #0066cc;
                border-radius: 2px;
            }
        """)

    def apply_fallback_styling(self):
        """Apply minimal fallback styling if native styling fails"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: white;
                color: black;
            }
        """)

    def load_initial_data(self):
        """Load initial data and update displays"""
        try:
            # Test database connection
            courses = self.database.get_transcript_courses()
            course_count = len(courses)

            programs = self.database.get_programs()
            program_count = len(programs)

            self.status_message(f"Loaded {course_count} courses, {program_count} programs")

        except Exception as e:
            self.status_message(f"Error loading data: {e}")

    def status_message(self, message: str, timeout: int = 5000):
        """Show message in status bar"""
        # Check if status bar is initialized
        if hasattr(self, 'status_label') and self.status_label:
            self.status_label.setText(message)
            if timeout > 0:
                QTimer.singleShot(timeout, lambda: self.status_label.setText("Ready"))
        else:
            # Fallback to console if UI not ready
            print(f"Status: {message}")

    def refresh_all_data(self):
        """Refresh all application data"""
        self.status_message("Refreshing data...")
        try:
            self.load_initial_data()

            # Refresh all tabs that support it
            if hasattr(self, 'overview_tab') and hasattr(self.overview_tab, 'refresh_data'):
                self.overview_tab.refresh_data()
            if hasattr(self, 'course_tab') and hasattr(self.course_tab, 'refresh_data'):
                self.course_tab.refresh_data()
            if hasattr(self, 'planning_tab') and hasattr(self.planning_tab, 'refresh_data'):
                self.planning_tab.refresh_data()
            if hasattr(self, 'analytics_tab') and hasattr(self.analytics_tab, 'refresh_data'):
                self.analytics_tab.refresh_data()

            self.status_message("Data refreshed successfully")
        except Exception as e:
            self.status_message(f"Refresh failed: {e}")

    def import_transcript(self):
        """Import transcript data"""
        self.status_message("Import transcript functionality coming soon...")

    def export_transcript(self):
        """Export transcript data"""
        self.status_message("Export transcript functionality coming soon...")

    def show_settings(self):
        """Show application settings"""
        try:
            from gui_qt.dialogs.settings_dialog import SettingsDialog
            dialog = SettingsDialog(self)
            dialog.settings_changed.connect(self.apply_settings)
            dialog.exec()
        except ImportError as e:
            self.status_message(f"Settings dialog not available: {e}")
            QMessageBox.information(self, "Settings", "Settings dialog coming soon...")

    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(self, "About University of Toronto Course Dashboard",
                         "University of Toronto Course Dashboard\n"
                         "Faculty of Arts & Science Academic Management System\n\n"
                         "Features:\n"
                         "• 20.0 Credit System Tracking\n"
                         "• Breadth Requirements Management\n"
                         "• Program Progress Monitoring\n"
                         "• Academic Calendar Integration\n\n"
                         "Built with PyQt6 for professional academic planning")

    def open_academic_calendar(self):
        """Open UofT Academic Calendar in browser"""
        import webbrowser
        webbrowser.open("https://artsci.calendar.utoronto.ca/")
        self.status_message("Opened UofT Academic Calendar in browser")

    def open_degree_explorer(self):
        """Launch degree exploration functionality"""
        self.status_message("Opening Degree Planning workspace...")
        # Switch to degree planning tab
        self.tab_widget.setCurrentIndex(2)  # Degree Planning tab

    def closeEvent(self, event):
        """Handle application close event"""
        try:
            if self.scraper:
                self.scraper.close_driver()
        except:
            pass
        event.accept()

    def on_course_search_requested(self, course_code: str):
        """Handle course search requests from other tabs"""
        # Switch to course management tab and perform search
        self.tab_widget.setCurrentIndex(1)  # Course Management tab
        if hasattr(self, 'course_tab') and hasattr(self.course_tab, 'search_course'):
            self.course_tab.search_course(course_code)
        self.status_message(f"Searching for course: {course_code}")

    def add_new_course(self):
        """Handle add new course request"""
        # Switch to course management tab and trigger add course
        self.tab_widget.setCurrentIndex(1)  # Course Management tab
        if hasattr(self, 'course_tab') and hasattr(self.course_tab, 'add_new_course'):
            self.course_tab.add_new_course()
        self.status_message("Add new course dialog")

    def focus_search(self):
        """Focus the search input in current tab or course management"""
        current_index = self.tab_widget.currentIndex()

        if current_index == 0:  # Academic Overview
            if hasattr(self, 'overview_tab') and hasattr(self.overview_tab, 'focus_search'):
                self.overview_tab.focus_search()
        elif current_index == 1:  # Course Management
            if hasattr(self, 'course_tab') and hasattr(self.course_tab, 'focus_search'):
                self.course_tab.focus_search()
        else:
            # Default to course management tab
            self.tab_widget.setCurrentIndex(1)
            if hasattr(self, 'course_tab') and hasattr(self.course_tab, 'focus_search'):
                self.course_tab.focus_search()

        self.status_message("Search focused")

    def show_global_search(self):
        """Show global search dialog"""
        self.status_message("Global search dialog coming soon...")

    def keyPressEvent(self, event):
        """Handle application-wide keyboard shortcuts"""
        # Quick tab switching with Ctrl+1-4
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_1:
                self.tab_widget.setCurrentIndex(0)
                return
            elif event.key() == Qt.Key.Key_2:
                self.tab_widget.setCurrentIndex(1)
                return
            elif event.key() == Qt.Key.Key_3:
                self.tab_widget.setCurrentIndex(2)
                return
            elif event.key() == Qt.Key.Key_4:
                self.tab_widget.setCurrentIndex(3)
                return

        # Call parent implementation for other keys
        super().keyPressEvent(event)

    def setup_data_manager_connections(self):
        """Setup connections for unified data manager signals"""
        if not self.data_manager:
            return

        # Connect data manager signals to status updates
        self.data_manager.operation_completed.connect(self.status_message)
        self.data_manager.validation_error.connect(self.handle_validation_error)

        # Connect data change signals to refresh tabs
        self.data_manager.course_added.connect(self.on_data_changed)
        self.data_manager.course_modified.connect(lambda course_id, data: self.on_data_changed())
        self.data_manager.course_deleted.connect(lambda course_id: self.on_data_changed())
        self.data_manager.data_refreshed.connect(self.refresh_all_data)

    def handle_validation_error(self, field: str, error: str):
        """Handle validation errors from data manager"""
        self.status_message(f"Validation Error - {field}: {error}", 10000)
        if field == 'general':
            QMessageBox.warning(self, "Data Error", error)

    def on_data_changed(self):
        """Handle data changes by refreshing relevant tabs"""
        try:
            # Refresh all tabs that support it
            if hasattr(self, 'overview_tab') and hasattr(self.overview_tab, 'refresh_data'):
                self.overview_tab.refresh_data()
            if hasattr(self, 'course_tab') and hasattr(self.course_tab, 'refresh_data'):
                self.course_tab.refresh_data()
            if hasattr(self, 'planning_tab') and hasattr(self.planning_tab, 'refresh_data'):
                self.planning_tab.refresh_data()
            if hasattr(self, 'analytics_tab') and hasattr(self.analytics_tab, 'refresh_data'):
                self.analytics_tab.refresh_data()
        except Exception as e:
            print(f"Error refreshing tabs after data change: {e}")

    def get_data_manager(self):
        """Get the unified data manager instance"""
        return self.data_manager

    def apply_settings(self, settings_dict):
        """Apply settings changes from settings dialog"""
        try:
            # Apply general settings
            general = settings_dict.get('general', {})
            if general.get('startup_tab') is not None:
                # Store for next startup
                pass

            # Apply display settings
            display = settings_dict.get('display', {})
            if display.get('theme') is not None:
                self.apply_theme_change(display['theme'])

            # Apply data settings
            data = settings_dict.get('data', {})
            # Handle database path changes, etc.

            # Apply advanced settings
            advanced = settings_dict.get('advanced', {})
            if advanced.get('debug_mode'):
                print("Debug mode enabled")

            self.status_message("Settings applied successfully")

        except Exception as e:
            self.status_message(f"Error applying settings: {e}")
            QMessageBox.warning(self, "Settings Error", f"Failed to apply some settings: {e}")

    def apply_theme_change(self, theme_index):
        """Apply theme change"""
        if theme_index == 0:  # System Default
            self.apply_native_styling()
        elif theme_index == 1:  # Light
            self.apply_native_styling()
        elif theme_index == 2:  # Dark
            self.apply_dark_theme()
        elif theme_index == 3:  # High Contrast
            self.apply_high_contrast_theme()

    def apply_dark_theme(self):
        """Apply dark theme styling"""
        from PyQt6.QtGui import QPalette, QColor
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance()
        palette = QPalette()

        # Dark theme colors
        palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(0, 0, 0))

        app.setPalette(palette)
        self.status_message("Dark theme applied")

    def apply_high_contrast_theme(self):
        """Apply high contrast theme styling"""
        from PyQt6.QtGui import QPalette, QColor
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance()
        palette = QPalette()

        # High contrast colors
        palette.setColor(QPalette.ColorRole.Window, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Base, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(64, 64, 64))
        palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Button, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(255, 255, 0))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(0, 0, 0))

        app.setPalette(palette)
        self.status_message("High contrast theme applied")


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)

    # Set application properties
    app.setApplicationName("UofT Course Dashboard")
    app.setApplicationVersion("2.0.0")
    app.setOrganizationName("UofT Course Dashboard Team")

    # Create and show main window
    window = MainWindow()
    window.show()

    # Start event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()