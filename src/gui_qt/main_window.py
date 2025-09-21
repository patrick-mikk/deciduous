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


class MainWindow(QMainWindow):
    """Modern main application window for UofT Course Dashboard"""

    def __init__(self):
        super().__init__()

        # Initialize core components (from existing tkinter version)
        self.database = None
        self.scraper = None
        self.requirements_calculator = None

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

            # Initialize scraper if available (defer to avoid blocking)
            self.scraper = None
            print("Web scraper initialization deferred for better startup performance")

            self.status_message("Database initialized successfully")

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
        """Create main application tabs"""
        # Tab 1: Course Search (implemented in Phase 2B)
        try:
            from gui_qt.widgets.course_search import CourseSearchWidget
            self.search_tab = CourseSearchWidget(self.database)
            self.tab_widget.addTab(self.search_tab, "Course Search")
        except ImportError as e:
            search_tab = QWidget()
            search_layout = QVBoxLayout(search_tab)
            search_layout.addWidget(QLabel(f"Course Search Tab\n\nError loading widget: {e}"))
            self.tab_widget.addTab(search_tab, "Course Search")

        # Tab 2: Transcript (implemented in Phase 2B)
        try:
            from gui_qt.widgets.transcript_table import TranscriptTableWidget
            self.transcript_tab = TranscriptTableWidget(self.database)
            self.transcript_tab.courses_modified.connect(self.refresh_all_data)
            self.tab_widget.addTab(self.transcript_tab, "Transcript")
        except ImportError as e:
            transcript_tab = QWidget()
            transcript_layout = QVBoxLayout(transcript_tab)
            transcript_layout.addWidget(QLabel(f"Transcript Tab\n\nError loading widget: {e}"))
            self.tab_widget.addTab(transcript_tab, "Transcript")

        # Tab 3: Planning (placeholder)
        planning_tab = QWidget()
        planning_layout = QVBoxLayout(planning_tab)
        planning_layout.addWidget(QLabel("Course Planning Tab\n\nPyQt6 implementation coming in Phase 2C..."))
        self.tab_widget.addTab(planning_tab, "Planning")

        # Tab 4: Requirements (placeholder)
        requirements_tab = QWidget()
        requirements_layout = QVBoxLayout(requirements_tab)
        requirements_layout.addWidget(QLabel("Requirements Tab\n\nPyQt6 implementation coming in Phase 2C..."))
        self.tab_widget.addTab(requirements_tab, "Requirements")

        # Tab 5: GPA Dashboard (placeholder)
        gpa_tab = QWidget()
        gpa_layout = QVBoxLayout(gpa_tab)
        gpa_layout.addWidget(QLabel("GPA Dashboard Tab\n\nPyQt6 implementation coming in Phase 2C..."))
        self.tab_widget.addTab(gpa_tab, "GPA Dashboard")

        # Tab 6: Analytics (placeholder)
        analytics_tab = QWidget()
        analytics_layout = QVBoxLayout(analytics_tab)
        analytics_layout.addWidget(QLabel("Analytics Tab\n\nPyQt6 implementation coming in Phase 2C..."))
        self.tab_widget.addTab(analytics_tab, "Analytics")

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

        settings_action = QAction('&Settings...', self)
        settings_action.triggered.connect(self.show_settings)
        tools_menu.addAction(settings_action)

        # Help menu
        help_menu = menubar.addMenu('&Help')

        about_action = QAction('&About...', self)
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
        """Apply modern styling to the application"""
        try:
            # Load stylesheet from file
            style_path = Path(__file__).parent / "resources" / "styles.qss"
            if style_path.exists():
                with open(style_path, 'r', encoding='utf-8') as f:
                    stylesheet = f.read()
                self.setStyleSheet(stylesheet)
                print("High-contrast light theme loaded successfully")
            else:
                print(f"Stylesheet not found at {style_path}, using fallback")
                self.apply_fallback_styling()
        except Exception as e:
            print(f"Error loading stylesheet: {e}, using fallback")
            self.apply_fallback_styling()

    def apply_fallback_styling(self):
        """Apply fallback styling if main stylesheet fails to load"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #ffffff;
                color: #000000;
                font-family: "Segoe UI", Arial, sans-serif;
                font-size: 9pt;
            }
            QTabWidget::pane {
                border: 2px solid #cccccc;
                background-color: #ffffff;
            }
            QTabBar::tab {
                background-color: #f5f5f5;
                border: 1px solid #cccccc;
                padding: 12px 24px;
                margin-right: 2px;
                color: #000000;
            }
            QTabBar::tab:selected {
                background-color: #ffffff;
                font-weight: bold;
                color: #000000;
            }
            QPushButton {
                background-color: #0066cc;
                color: #ffffff;
                border: 2px solid #0066cc;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QLabel {
                color: #000000;
                background-color: transparent;
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
            # TODO: Update all tabs when implemented
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
        self.status_message("Settings dialog coming in Phase 2C...")

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
        self.status_message("Degree Explorer functionality coming in Phase 2C...")
        # Switch to requirements tab for now
        self.tab_widget.setCurrentIndex(3)  # Requirements tab

    def closeEvent(self, event):
        """Handle application close event"""
        try:
            if self.scraper:
                self.scraper.close_driver()
        except:
            pass
        event.accept()


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