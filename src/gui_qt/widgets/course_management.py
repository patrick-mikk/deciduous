"""
Course Management Widget for PyQt6 UofT Course Dashboard
Unified course search, transcript management, and course details in three-panel layout
"""

from typing import List, Dict, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QTextEdit,
    QSplitter, QGroupBox, QHeaderView, QAbstractItemView,
    QComboBox, QFormLayout, QFrame, QProgressBar, QMessageBox,
    QCheckBox, QMenu
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QAction


class CourseSearchThread(QThread):
    """Background thread for Academic Calendar course searching"""
    search_completed = pyqtSignal(list)
    search_error = pyqtSignal(str)

    def __init__(self, course_code: str):
        super().__init__()
        self.course_code = course_code

    def run(self):
        try:
            from main import AcademicCalendarScraper
            scraper = AcademicCalendarScraper(debug=False)
            results = scraper.search_courses(self.course_code)
            scraper.close_driver()
            self.search_completed.emit(results)
        except Exception as e:
            self.search_error.emit(str(e))


class SearchPanel(QGroupBox):
    """Left panel for course search functionality"""

    search_requested = pyqtSignal(str)
    course_selected = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__("Academic Calendar Search", parent)
        self.search_thread = None
        self.search_results = []
        self.setup_ui()
        self.setup_connections()

    def setup_ui(self):
        """Setup search interface"""
        layout = QVBoxLayout(self)

        # Search input
        search_layout = QFormLayout()
        self.course_input = QLineEdit()
        self.course_input.setPlaceholderText("Enter course code (e.g. CSC108H1)")
        search_layout.addRow("Course Code:", self.course_input)

        self.search_btn = QPushButton("Search Calendar")
        self.search_btn.setDefault(True)
        search_layout.addRow(self.search_btn)

        layout.addLayout(search_layout)

        # Progress indicator
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Results table
        results_label = QLabel("Search Results:")
        layout.addWidget(results_label)

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(3)
        self.results_table.setHorizontalHeaderLabels(["Course Code", "Title", "Credits"])

        # Configure table
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)

        self.results_table.setColumnWidth(0, 100)
        self.results_table.setColumnWidth(2, 60)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        layout.addWidget(self.results_table)

        # Status label
        self.status_label = QLabel("Enter a course code to search")
        layout.addWidget(self.status_label)

    def setup_connections(self):
        """Setup signal connections"""
        self.search_btn.clicked.connect(self.perform_search)
        self.course_input.returnPressed.connect(self.perform_search)
        self.results_table.itemSelectionChanged.connect(self.on_selection_changed)

    def perform_search(self):
        """Perform course search"""
        if self.search_thread and self.search_thread.isRunning():
            return

        course_code = self.course_input.text().strip().upper()
        if not course_code:
            QMessageBox.warning(self, "Invalid Input", "Please enter a course code.")
            return

        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.search_btn.setEnabled(False)
        self.status_label.setText("Searching Academic Calendar...")

        # Start search
        self.search_thread = CourseSearchThread(course_code)
        self.search_thread.search_completed.connect(self.on_search_completed)
        self.search_thread.search_error.connect(self.on_search_error)
        self.search_thread.start()

    def on_search_completed(self, results):
        """Handle successful search"""
        self.progress_bar.setVisible(False)
        self.search_btn.setEnabled(True)
        self.search_results = results

        self.populate_results(results)
        self.status_label.setText(f"Found {len(results)} course(s)")

    def on_search_error(self, error_msg):
        """Handle search error"""
        self.progress_bar.setVisible(False)
        self.search_btn.setEnabled(True)
        QMessageBox.warning(self, "Search Error", f"Search failed: {error_msg}")
        self.status_label.setText("Search failed")

    def populate_results(self, results):
        """Populate results table"""
        self.results_table.setRowCount(len(results))

        for row, course in enumerate(results):
            # Course code
            code_item = QTableWidgetItem(course.get('course_code', ''))
            code_item.setFlags(code_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.results_table.setItem(row, 0, code_item)

            # Title
            title_item = QTableWidgetItem(course.get('title', ''))
            title_item.setFlags(title_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.results_table.setItem(row, 1, title_item)

            # Credits (infer from course code if needed)
            credits = course.get('credits', '')
            if not credits:
                course_code = course.get('course_code', '')
                if 'H' in course_code:
                    credits = '0.5'
                elif 'Y' in course_code:
                    credits = '1.0'
                else:
                    credits = 'TBD'

            credits_item = QTableWidgetItem(str(credits))
            credits_item.setFlags(credits_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.results_table.setItem(row, 2, credits_item)

    def on_selection_changed(self):
        """Handle table selection changes"""
        current_row = self.results_table.currentRow()
        if 0 <= current_row < len(self.search_results):
            course = self.search_results[current_row]
            self.course_selected.emit(course)


class TranscriptPanel(QGroupBox):
    """Bottom panel for transcript management"""

    course_details_requested = pyqtSignal(dict)

    def __init__(self, database, parent=None):
        super().__init__("Transcript Management", parent)
        self.database = database
        self.transcript_data = []
        self.filtered_data = []
        self.setup_ui()
        self.setup_connections()
        self.load_transcript_data()

    def setup_ui(self):
        """Setup transcript interface"""
        layout = QVBoxLayout(self)

        # Filters
        filter_layout = QHBoxLayout()

        # Course code filter
        filter_layout.addWidget(QLabel("Filter:"))
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Course code...")
        filter_layout.addWidget(self.filter_input)

        # Session filter
        self.session_filter = QComboBox()
        self.session_filter.addItems(["All Sessions", "Fall", "Winter", "Summer"])
        filter_layout.addWidget(self.session_filter)

        # Grade filter
        self.grade_filter = QComboBox()
        self.grade_filter.addItem("All Grades")
        filter_layout.addWidget(self.grade_filter)

        # Clear button
        clear_btn = QPushButton("Clear Filters")
        clear_btn.clicked.connect(self.clear_filters)
        filter_layout.addWidget(clear_btn)

        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # Action buttons
        action_layout = QHBoxLayout()
        add_btn = QPushButton("Add Course")
        edit_btn = QPushButton("Edit Selected")
        delete_btn = QPushButton("Delete Selected")

        action_layout.addWidget(add_btn)
        action_layout.addWidget(edit_btn)
        action_layout.addWidget(delete_btn)
        action_layout.addStretch()

        layout.addLayout(action_layout)

        # Transcript table
        self.transcript_table = QTableWidget()
        self.transcript_table.setColumnCount(8)
        self.transcript_table.setHorizontalHeaderLabels([
            "Course Code", "Title", "Credits", "Grade", "Mark", "Session", "Year", "Status"
        ])

        # Configure table
        header = self.transcript_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)    # Course Code
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Title
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)    # Credits
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)    # Grade
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)    # Mark
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)    # Session
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)    # Year
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)    # Status

        self.transcript_table.setColumnWidth(0, 100)  # Course Code
        self.transcript_table.setColumnWidth(2, 60)   # Credits
        self.transcript_table.setColumnWidth(3, 50)   # Grade
        self.transcript_table.setColumnWidth(4, 50)   # Mark
        self.transcript_table.setColumnWidth(5, 70)   # Session
        self.transcript_table.setColumnWidth(6, 50)   # Year
        self.transcript_table.setColumnWidth(7, 80)   # Status

        self.transcript_table.setAlternatingRowColors(True)
        self.transcript_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.transcript_table.setSortingEnabled(True)

        layout.addWidget(self.transcript_table)

        # Summary
        self.summary_label = QLabel("No courses loaded")
        layout.addWidget(self.summary_label)

    def setup_connections(self):
        """Setup signal connections"""
        self.filter_input.textChanged.connect(self.apply_filters)
        self.session_filter.currentTextChanged.connect(self.apply_filters)
        self.grade_filter.currentTextChanged.connect(self.apply_filters)
        self.transcript_table.itemDoubleClicked.connect(self.on_course_double_clicked)

    def load_transcript_data(self):
        """Load transcript data from database"""
        try:
            self.transcript_data = self.database.get_transcript_courses()
            self.populate_grade_filter()
            self.apply_filters()
        except Exception as e:
            QMessageBox.warning(self, "Data Error", f"Failed to load transcript: {e}")

    def populate_grade_filter(self):
        """Populate grade filter with available grades"""
        grades = set()
        for course in self.transcript_data:
            if len(course) > 4 and course[4]:
                grades.add(course[4])

        self.grade_filter.clear()
        self.grade_filter.addItem("All Grades")
        for grade in sorted(grades):
            self.grade_filter.addItem(grade)

    def apply_filters(self):
        """Apply current filters to transcript data"""
        self.filtered_data = self.transcript_data.copy()

        # Course code filter
        code_filter = self.filter_input.text().strip().upper()
        if code_filter:
            self.filtered_data = [
                course for course in self.filtered_data
                if code_filter in course[1].upper()  # Course code is at index 1
            ]

        # Session filter
        session_filter = self.session_filter.currentText()
        if session_filter != "All Sessions":
            self.filtered_data = [
                course for course in self.filtered_data
                if len(course) > 5 and course[5] == session_filter
            ]

        # Grade filter
        grade_filter = self.grade_filter.currentText()
        if grade_filter != "All Grades":
            self.filtered_data = [
                course for course in self.filtered_data
                if len(course) > 4 and course[4] == grade_filter
            ]

        self.populate_transcript_table()
        self.update_summary()

    def populate_transcript_table(self):
        """Populate transcript table with filtered data"""
        self.transcript_table.setRowCount(len(self.filtered_data))

        for row, course in enumerate(self.filtered_data):
            # Extract course data safely
            course_code = course[1] if len(course) > 1 else ""
            title = course[2] if len(course) > 2 else ""
            credits = str(course[3]) if len(course) > 3 else ""
            grade = course[4] if len(course) > 4 else ""
            mark = str(course[5]) if len(course) > 5 and course[5] is not None else ""
            session = course[6] if len(course) > 6 else ""
            year = str(course[7]) if len(course) > 7 else ""
            status = course[8] if len(course) > 8 else ""

            # Populate cells
            items = [course_code, title, credits, grade, mark, session, year, status]
            for col, value in enumerate(items):
                item = QTableWidgetItem(str(value))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.transcript_table.setItem(row, col, item)

    def update_summary(self):
        """Update summary information"""
        total_courses = len(self.filtered_data)
        total_credits = 0
        gpa_points = 0
        gpa_credits = 0

        grade_points = {
            'A+': 4.0, 'A': 4.0, 'A-': 3.7,
            'B+': 3.3, 'B': 3.0, 'B-': 2.7,
            'C+': 2.3, 'C': 2.0, 'C-': 1.7,
            'D+': 1.3, 'D': 1.0, 'D-': 0.7,
            'F': 0.0, 'FZ': 0.0
        }

        for course in self.filtered_data:
            if len(course) > 3 and course[3]:
                try:
                    credits = float(course[3])
                    total_credits += credits

                    if len(course) > 4 and course[4] in grade_points:
                        gpa_points += grade_points[course[4]] * credits
                        gpa_credits += credits
                except (ValueError, TypeError):
                    pass

        gpa = gpa_points / gpa_credits if gpa_credits > 0 else 0

        summary_text = (
            f"Showing {total_courses} courses | "
            f"Total Credits: {total_credits:.1f} | "
            f"GPA: {gpa:.2f}"
        )
        self.summary_label.setText(summary_text)

    def clear_filters(self):
        """Clear all filters"""
        self.filter_input.clear()
        self.session_filter.setCurrentText("All Sessions")
        self.grade_filter.setCurrentText("All Grades")

    def on_course_double_clicked(self, item):
        """Handle double-click on course"""
        row = item.row()
        if 0 <= row < len(self.filtered_data):
            course_data = self.filtered_data[row]
            course_dict = {
                'id': course_data[0] if len(course_data) > 0 else None,
                'course_code': course_data[1] if len(course_data) > 1 else "",
                'title': course_data[2] if len(course_data) > 2 else "",
                'credits': course_data[3] if len(course_data) > 3 else 0,
                'grade': course_data[4] if len(course_data) > 4 else "",
                'mark': course_data[5] if len(course_data) > 5 else None,
                'session': course_data[6] if len(course_data) > 6 else "",
                'year': course_data[7] if len(course_data) > 7 else 0,
                'status': course_data[8] if len(course_data) > 8 else ""
            }
            self.course_details_requested.emit(course_dict)

    def refresh_data(self):
        """Refresh transcript data"""
        self.load_transcript_data()


class DetailsPanel(QGroupBox):
    """Right panel for course details and actions"""

    add_to_transcript_requested = pyqtSignal(dict)
    add_to_planning_requested = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__("Course Details", parent)
        self.current_course = None
        self.setup_ui()

    def setup_ui(self):
        """Setup details interface"""
        layout = QVBoxLayout(self)

        # Course details display
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMaximumHeight(400)
        layout.addWidget(self.details_text)

        # Action buttons
        action_layout = QVBoxLayout()

        self.add_transcript_btn = QPushButton("Add to Transcript")
        self.add_transcript_btn.setEnabled(False)
        self.add_transcript_btn.clicked.connect(self.on_add_to_transcript)
        action_layout.addWidget(self.add_transcript_btn)

        self.add_planning_btn = QPushButton("Add to Planning")
        self.add_planning_btn.setEnabled(False)
        self.add_planning_btn.clicked.connect(self.on_add_to_planning)
        action_layout.addWidget(self.add_planning_btn)

        layout.addLayout(action_layout)

        # Clear display
        self.clear_details()

    def display_course(self, course_data: Dict):
        """Display course information"""
        self.current_course = course_data

        details = []

        # Course header
        course_code = course_data.get('course_code', 'Unknown')
        title = course_data.get('title', 'No title available')
        details.append(f"<h3>{course_code}: {title}</h3>")

        # Credits
        credits = course_data.get('credits', 'Unknown')
        details.append(f"<b>Credits:</b> {credits}")

        # Description
        description = course_data.get('description', 'No description available')
        details.append(f"<b>Description:</b><br>{description}")

        # Prerequisites
        prereq = course_data.get('prerequisites', '')
        if prereq and prereq != 'None':
            details.append(f"<b>Prerequisites:</b><br>{prereq}")

        # Exclusions
        exclusions = course_data.get('exclusions', '')
        if exclusions and exclusions != 'None':
            details.append(f"<b>Exclusions:</b><br>{exclusions}")

        # Breadth requirements
        breadth = course_data.get('breadth_requirements', '')
        if breadth:
            details.append(f"<b>Breadth Requirements:</b> {breadth}")

        self.details_text.setHtml("<br><br>".join(details))

        # Enable action buttons
        self.add_transcript_btn.setEnabled(True)
        self.add_planning_btn.setEnabled(True)

    def clear_details(self):
        """Clear the details display"""
        self.details_text.setPlainText("Select a course to view details")
        self.current_course = None
        self.add_transcript_btn.setEnabled(False)
        self.add_planning_btn.setEnabled(False)

    def on_add_to_transcript(self):
        """Handle add to transcript request"""
        if self.current_course:
            self.add_to_transcript_requested.emit(self.current_course)

    def on_add_to_planning(self):
        """Handle add to planning request"""
        if self.current_course:
            self.add_to_planning_requested.emit(self.current_course)


class CourseManagementWidget(QWidget):
    """Main course management widget with three-panel layout"""

    tab_switch_requested = pyqtSignal(int)
    courses_modified = pyqtSignal()

    def __init__(self, database, data_manager=None, parent=None):
        super().__init__(parent)
        self.database = database
        self.data_manager = data_manager
        self.setup_ui()
        self.setup_connections()

    def setup_ui(self):
        """Setup the three-panel layout"""
        layout = QVBoxLayout(self)

        # Create main splitter
        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel - Search
        self.search_panel = SearchPanel()
        self.search_panel.setMinimumWidth(300)
        main_splitter.addWidget(self.search_panel)

        # Create vertical splitter for center and bottom
        right_splitter = QSplitter(Qt.Orientation.Vertical)

        # Top right - Course details
        self.details_panel = DetailsPanel()
        self.details_panel.setMaximumHeight(500)
        right_splitter.addWidget(self.details_panel)

        # Bottom right - Transcript
        self.transcript_panel = TranscriptPanel(self.database)
        right_splitter.addWidget(self.transcript_panel)

        # Set proportions for vertical splitter
        right_splitter.setSizes([200, 400])

        main_splitter.addWidget(right_splitter)

        # Set proportions for main splitter
        main_splitter.setSizes([300, 700])

        layout.addWidget(main_splitter)

    def setup_connections(self):
        """Setup signal connections between panels"""
        # Search panel signals
        self.search_panel.course_selected.connect(self.details_panel.display_course)

        # Transcript panel signals
        self.transcript_panel.course_details_requested.connect(self.details_panel.display_course)

        # Details panel signals
        self.details_panel.add_to_transcript_requested.connect(self.on_add_to_transcript)
        self.details_panel.add_to_planning_requested.connect(self.on_add_to_planning)

    def on_add_to_transcript(self, course_data):
        """Handle adding course to transcript"""
        # This would open a dialog to add the course
        QMessageBox.information(self, "Add to Transcript",
                              f"Add course {course_data.get('course_code', 'Unknown')} to transcript?\n"
                              "This functionality will be implemented in Phase 2D.")

    def on_add_to_planning(self, course_data):
        """Handle adding course to planning"""
        # Switch to planning tab
        self.tab_switch_requested.emit(2)  # Planning tab
        QMessageBox.information(self, "Add to Planning",
                              f"Switching to Planning tab to add {course_data.get('course_code', 'Unknown')}")

    def refresh_data(self):
        """Refresh all panel data"""
        self.transcript_panel.refresh_data()