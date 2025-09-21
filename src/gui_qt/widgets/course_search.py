"""
Course Search Widget for PyQt6 UofT Course Dashboard
Modern course search interface with live filtering and results
"""

import sys
from typing import Optional, List, Dict
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QComboBox,
    QTextEdit, QSplitter, QFrame, QHeaderView, QMessageBox,
    QProgressBar, QGroupBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont


class CourseSearchThread(QThread):
    """Background thread for course searching via Academic Calendar"""
    search_completed = pyqtSignal(list)
    search_error = pyqtSignal(str)

    def __init__(self, database, search_params):
        super().__init__()
        self.database = database
        self.search_params = search_params

    def run(self):
        try:
            # Initialize scraper for web search
            from main import AcademicCalendarScraper
            scraper = AcademicCalendarScraper(debug=False)

            # Search using course code
            course_code = self.search_params.get('course_code', '')
            results = scraper.search_courses(course_code)

            # Close scraper
            scraper.close_driver()

            self.search_completed.emit(results)
        except Exception as e:
            self.search_error.emit(str(e))


class CourseSearchWidget(QWidget):
    """Course search widget for UofT Academic Calendar lookups"""

    course_selected = pyqtSignal(dict)  # Emitted when a course is selected

    def __init__(self, database, parent=None):
        super().__init__(parent)
        self.database = database
        self.search_thread = None
        self.current_results = []

        self.init_ui()
        self.setup_connections()
        self.load_initial_data()

    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Header
        header_label = QLabel("Course Search")
        header_font = QFont()
        header_font.setPointSize(16)
        header_font.setBold(True)
        header_label.setFont(header_font)
        layout.addWidget(header_label)

        # Search section
        search_group = QGroupBox("Search Criteria")
        search_layout = QVBoxLayout(search_group)

        # Course code search - simplified and focused
        search_row = QHBoxLayout()

        search_row.addWidget(QLabel("Course Code:"))
        self.course_code_input = QLineEdit()
        self.course_code_input.setPlaceholderText("Enter course code (e.g. CSC108H1, MAT137Y1)")
        self.course_code_input.setMinimumWidth(300)
        search_row.addWidget(self.course_code_input)

        search_layout.addLayout(search_row)

        # Search buttons
        button_row = QHBoxLayout()

        self.search_button = QPushButton("Search Academic Calendar")
        self.search_button.setStyleSheet("""
            QPushButton {
                background-color: #0066cc;
                color: #ffffff;
                border: 2px solid #0066cc;
                padding: 12px 24px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 180px;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #0052a3;
                border-color: #0052a3;
            }
        """)
        button_row.addWidget(self.search_button)

        self.clear_button = QPushButton("Clear")
        self.clear_button.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #000000;
                border: 2px solid #666666;
                padding: 12px 24px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 100px;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
                border-color: #333333;
            }
        """)
        button_row.addWidget(self.clear_button)

        button_row.addStretch()
        search_layout.addLayout(button_row)

        layout.addWidget(search_group)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Results section
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Results table
        results_frame = QFrame()
        results_layout = QVBoxLayout(results_frame)

        results_label = QLabel("Search Results")
        results_font = QFont()
        results_font.setPointSize(12)
        results_font.setBold(True)
        results_label.setFont(results_font)
        results_layout.addWidget(results_label)

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(3)
        self.results_table.setHorizontalHeaderLabels([
            "Course Code", "Title", "Credits"
        ])

        # Configure table appearance
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)    # Course Code
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Title
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)    # Credits

        self.results_table.setColumnWidth(0, 120)  # Course Code
        self.results_table.setColumnWidth(2, 80)   # Credits

        self.results_table.setAlternatingRowColors(True)
        self.results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.results_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)

        results_layout.addWidget(self.results_table)

        # Results summary
        self.results_summary = QLabel("Enter a course code to search the UofT Academic Calendar")
        results_layout.addWidget(self.results_summary)

        splitter.addWidget(results_frame)

        # Course details panel
        details_frame = QFrame()
        details_layout = QVBoxLayout(details_frame)

        details_label = QLabel("Course Details")
        details_label.setFont(results_font)
        details_layout.addWidget(details_label)

        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMaximumWidth(350)
        details_layout.addWidget(self.details_text)

        # Action buttons
        action_layout = QHBoxLayout()

        self.add_to_transcript_btn = QPushButton("Add to Transcript")
        self.add_to_transcript_btn.setEnabled(False)
        self.add_to_transcript_btn.setStyleSheet("""
            QPushButton {
                background-color: #006600;
                color: #ffffff;
                border: 2px solid #006600;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #004d00;
                border-color: #004d00;
            }
            QPushButton:disabled {
                background-color: #e6e6e6;
                border-color: #cccccc;
                color: #666666;
            }
        """)
        action_layout.addWidget(self.add_to_transcript_btn)

        self.add_to_planning_btn = QPushButton("Add to Planning")
        self.add_to_planning_btn.setEnabled(False)
        self.add_to_planning_btn.setStyleSheet("""
            QPushButton {
                background-color: #0066cc;
                color: #ffffff;
                border: 2px solid #0066cc;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0052a3;
                border-color: #0052a3;
            }
            QPushButton:disabled {
                background-color: #e6e6e6;
                border-color: #cccccc;
                color: #666666;
            }
        """)
        action_layout.addWidget(self.add_to_planning_btn)

        details_layout.addLayout(action_layout)

        splitter.addWidget(details_frame)
        splitter.setSizes([600, 350])

        layout.addWidget(splitter)

    def setup_connections(self):
        """Setup signal connections"""
        self.search_button.clicked.connect(self.perform_search)
        self.clear_button.clicked.connect(self.clear_search)
        self.results_table.itemSelectionChanged.connect(self.on_selection_changed)

        # Enter key triggers search
        self.course_code_input.returnPressed.connect(self.perform_search)

    def load_initial_data(self):
        """Initialize scraper for course lookups"""
        pass  # No initial data needed for direct course lookups

    def perform_search(self):
        """Perform course search via Academic Calendar"""
        if self.search_thread and self.search_thread.isRunning():
            return

        # Get course code
        course_code = self.course_code_input.text().strip().upper()

        # Validate course code format
        if not course_code:
            QMessageBox.warning(self, "Invalid Input", "Please enter a course code.")
            return

        if len(course_code) < 6:
            QMessageBox.warning(self, "Invalid Input", "Please enter a complete course code (e.g. CSC108H1).")
            return

        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.search_button.setEnabled(False)
        self.results_summary.setText("Searching Academic Calendar...")

        # Start search thread
        search_params = {'course_code': course_code}
        self.search_thread = CourseSearchThread(self.database, search_params)
        self.search_thread.search_completed.connect(self.on_search_completed)
        self.search_thread.search_error.connect(self.on_search_error)
        self.search_thread.start()

    def on_search_completed(self, results):
        """Handle search completion"""
        self.progress_bar.setVisible(False)
        self.search_button.setEnabled(True)

        self.current_results = results
        self.populate_results_table(results)

        # Update summary
        self.results_summary.setText(f"Found {len(results)} courses")

    def on_search_error(self, error_msg):
        """Handle search error"""
        self.progress_bar.setVisible(False)
        self.search_button.setEnabled(True)

        QMessageBox.warning(self, "Search Error", f"Search failed: {error_msg}")
        self.results_summary.setText("Search failed")

    def populate_results_table(self, results):
        """Populate the results table with course data"""
        self.results_table.setRowCount(len(results))

        for row, course in enumerate(results):
            # Course Code
            item = QTableWidgetItem(course.get('course_code', ''))
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.results_table.setItem(row, 0, item)

            # Title
            item = QTableWidgetItem(course.get('title', ''))
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.results_table.setItem(row, 1, item)

            # Credits - extract from course code or details
            credits = course.get('credits', '')
            if not credits:
                # Try to determine credits from course code (H=0.5, Y=1.0)
                course_code = course.get('course_code', '')
                if 'H' in course_code:
                    credits = '0.5'
                elif 'Y' in course_code:
                    credits = '1.0'
                else:
                    credits = 'TBD'
            elif isinstance(credits, (int, float)):
                credits = str(credits)

            item = QTableWidgetItem(credits)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.results_table.setItem(row, 2, item)

    def on_selection_changed(self):
        """Handle table selection changes"""
        current_row = self.results_table.currentRow()

        if current_row >= 0 and current_row < len(self.current_results):
            course = self.current_results[current_row]
            self.display_course_details(course)
            self.add_to_transcript_btn.setEnabled(True)
            self.add_to_planning_btn.setEnabled(True)
        else:
            self.details_text.clear()
            self.add_to_transcript_btn.setEnabled(False)
            self.add_to_planning_btn.setEnabled(False)

    def display_course_details(self, course):
        """Display detailed course information"""
        details = []

        # Course header
        course_code = course.get('course_code', 'Unknown')
        title = course.get('title', 'No title available')
        details.append(f"<h3>{course_code}: {title}</h3>")

        # Credits
        credits = course.get('credits', 'Unknown')
        details.append(f"<b>Credits:</b> {credits}")

        # Description
        description = course.get('description', 'No description available')
        details.append(f"<b>Description:</b><br>{description}")

        # Prerequisites
        prereq = course.get('prerequisites', 'None')
        if prereq and prereq != 'None':
            details.append(f"<b>Prerequisites:</b><br>{prereq}")

        # Exclusions
        exclusions = course.get('exclusions', 'None')
        if exclusions and exclusions != 'None':
            details.append(f"<b>Exclusions:</b><br>{exclusions}")

        # Breadth requirements
        breadth = course.get('breadth_requirements', 'None specified')
        details.append(f"<b>Breadth Requirements:</b> {breadth}")

        # Hours
        hours = course.get('hours', '')
        if hours:
            details.append(f"<b>Hours:</b> {hours}")

        self.details_text.setHtml("<br><br>".join(details))

    def clear_search(self):
        """Clear all search inputs and results"""
        self.course_code_input.clear()
        self.results_table.setRowCount(0)
        self.details_text.clear()
        self.current_results = []

        self.results_summary.setText("Enter a course code to search")
        self.add_to_transcript_btn.setEnabled(False)
        self.add_to_planning_btn.setEnabled(False)

    def get_selected_course(self):
        """Get the currently selected course"""
        current_row = self.results_table.currentRow()
        if current_row >= 0 and current_row < len(self.current_results):
            return self.current_results[current_row]
        return None