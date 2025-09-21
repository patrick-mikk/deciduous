"""
Transcript Table Widget for PyQt6 UofT Course Dashboard
Advanced table management with sorting, filtering, and bulk operations
"""

from typing import List, Dict, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QComboBox,
    QHeaderView, QMessageBox, QGroupBox, QCheckBox, QMenu,
    QAbstractItemView, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QSortFilterProxyModel
from PyQt6.QtGui import QFont, QAction


class TranscriptTableWidget(QWidget):
    """Advanced transcript table with filtering, sorting, and bulk operations"""

    course_selected = pyqtSignal(dict)
    courses_modified = pyqtSignal()  # Emitted when transcript data changes

    def __init__(self, database, parent=None):
        super().__init__(parent)
        self.database = database
        self.transcript_data = []
        self.filtered_data = []

        # Grade mappings
        self.GRADE_POINTS = {
            'A+': 4.0, 'A': 4.0, 'A-': 3.7,
            'B+': 3.3, 'B': 3.0, 'B-': 2.7,
            'C+': 2.3, 'C': 2.0, 'C-': 1.7,
            'D+': 1.3, 'D': 1.0, 'D-': 0.7,
            'F': 0.0, 'FZ': 0.0
        }

        self.init_ui()
        self.setup_connections()
        self.load_transcript_data()

    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Header
        header_label = QLabel("Transcript Management")
        header_font = QFont()
        header_font.setPointSize(16)
        header_font.setBold(True)
        header_label.setFont(header_font)
        layout.addWidget(header_label)

        # Filters section
        filter_group = QGroupBox("Filters & Actions")
        filter_layout = QVBoxLayout(filter_group)

        # Filter row 1
        filter_row1 = QHBoxLayout()

        filter_row1.addWidget(QLabel("Course Code:"))
        self.filter_course_code = QLineEdit()
        self.filter_course_code.setPlaceholderText("Filter by course code...")
        filter_row1.addWidget(self.filter_course_code)

        filter_row1.addWidget(QLabel("Session:"))
        self.filter_session = QComboBox()
        self.filter_session.addItems(["All", "Fall", "Winter", "Summer"])
        filter_row1.addWidget(self.filter_session)

        filter_row1.addWidget(QLabel("Year:"))
        self.filter_year = QComboBox()
        self.filter_year.addItem("All")
        filter_row1.addWidget(self.filter_year)

        filter_row1.addWidget(QLabel("Grade:"))
        self.filter_grade = QComboBox()
        self.filter_grade.addItem("All")
        filter_row1.addWidget(self.filter_grade)

        filter_layout.addLayout(filter_row1)

        # Action buttons row
        action_row = QHBoxLayout()

        self.add_course_btn = QPushButton("Add Course")
        self.add_course_btn.setStyleSheet("""
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
        """)
        action_row.addWidget(self.add_course_btn)

        self.edit_course_btn = QPushButton("Edit Selected")
        self.edit_course_btn.setEnabled(False)
        self.edit_course_btn.setStyleSheet("""
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
        action_row.addWidget(self.edit_course_btn)

        self.delete_course_btn = QPushButton("Delete Selected")
        self.delete_course_btn.setEnabled(False)
        self.delete_course_btn.setStyleSheet("""
            QPushButton {
                background-color: #cc0000;
                color: #ffffff;
                border: 2px solid #cc0000;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #990000;
                border-color: #990000;
            }
            QPushButton:disabled {
                background-color: #e6e6e6;
                border-color: #cccccc;
                color: #666666;
            }
        """)
        action_row.addWidget(self.delete_course_btn)

        # Bulk operations
        action_row.addWidget(QFrame())  # Separator

        self.bulk_edit_btn = QPushButton("Bulk Edit")
        self.bulk_edit_btn.setEnabled(False)
        action_row.addWidget(self.bulk_edit_btn)

        self.bulk_delete_btn = QPushButton("Bulk Delete")
        self.bulk_delete_btn.setEnabled(False)
        action_row.addWidget(self.bulk_delete_btn)

        action_row.addStretch()

        self.clear_filters_btn = QPushButton("Clear Filters")
        action_row.addWidget(self.clear_filters_btn)

        filter_layout.addLayout(action_row)
        layout.addWidget(filter_group)

        # Summary section
        self.summary_label = QLabel("No courses loaded")
        self.summary_label.setStyleSheet("color: #333333; font-weight: bold; padding: 8px;")
        layout.addWidget(self.summary_label)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "Select", "Course Code", "Title", "Credits", "Grade", "Mark", "Session", "Year", "Status"
        ])

        # Configure table
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)    # Select
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)    # Course Code
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # Title
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)    # Credits
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)    # Grade
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)    # Mark
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)    # Session
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)    # Year
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)    # Status

        self.table.setColumnWidth(0, 50)   # Select
        self.table.setColumnWidth(1, 100)  # Course Code
        self.table.setColumnWidth(3, 70)   # Credits
        self.table.setColumnWidth(4, 60)   # Grade
        self.table.setColumnWidth(5, 60)   # Mark
        self.table.setColumnWidth(6, 80)   # Session
        self.table.setColumnWidth(7, 60)   # Year
        self.table.setColumnWidth(8, 100)  # Status

        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSortingEnabled(True)

        # Context menu
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        layout.addWidget(self.table)

    def setup_connections(self):
        """Setup signal connections"""
        self.filter_course_code.textChanged.connect(self.apply_filters)
        self.filter_session.currentTextChanged.connect(self.apply_filters)
        self.filter_year.currentTextChanged.connect(self.apply_filters)
        self.filter_grade.currentTextChanged.connect(self.apply_filters)
        self.clear_filters_btn.clicked.connect(self.clear_filters)

        self.add_course_btn.clicked.connect(self.add_course)
        self.edit_course_btn.clicked.connect(self.edit_selected_course)
        self.delete_course_btn.clicked.connect(self.delete_selected_course)
        self.bulk_edit_btn.clicked.connect(self.bulk_edit_courses)
        self.bulk_delete_btn.clicked.connect(self.bulk_delete_courses)

        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.table.cellDoubleClicked.connect(self.on_cell_double_clicked)

    def load_transcript_data(self):
        """Load transcript data from database"""
        try:
            self.transcript_data = self.database.get_transcript_courses()
            self.populate_filter_options()
            self.apply_filters()
            self.update_summary()
        except Exception as e:
            QMessageBox.warning(self, "Data Error", f"Failed to load transcript data: {e}")

    def populate_filter_options(self):
        """Populate filter combo boxes with available options"""
        # Years
        years = set()
        grades = set()

        for course in self.transcript_data:
            if len(course) > 6:  # Check if we have year data
                years.add(str(course[6]))  # Year is at index 6
            if len(course) > 4:  # Check if we have grade data
                grades.add(course[4])     # Grade is at index 4

        # Update year filter
        self.filter_year.clear()
        self.filter_year.addItem("All")
        for year in sorted(years, reverse=True):
            self.filter_year.addItem(year)

        # Update grade filter
        self.filter_grade.clear()
        self.filter_grade.addItem("All")
        for grade in sorted(grades):
            if grade:  # Skip empty grades
                self.filter_grade.addItem(grade)

    def apply_filters(self):
        """Apply current filters to the data"""
        self.filtered_data = self.transcript_data.copy()

        # Course code filter
        course_code_filter = self.filter_course_code.text().strip().upper()
        if course_code_filter:
            self.filtered_data = [
                course for course in self.filtered_data
                if course_code_filter in course[1].upper()  # Course code is at index 1
            ]

        # Session filter
        session_filter = self.filter_session.currentText()
        if session_filter != "All":
            self.filtered_data = [
                course for course in self.filtered_data
                if len(course) > 5 and course[5] == session_filter  # Session is at index 5
            ]

        # Year filter
        year_filter = self.filter_year.currentText()
        if year_filter != "All":
            self.filtered_data = [
                course for course in self.filtered_data
                if len(course) > 6 and str(course[6]) == year_filter  # Year is at index 6
            ]

        # Grade filter
        grade_filter = self.filter_grade.currentText()
        if grade_filter != "All":
            self.filtered_data = [
                course for course in self.filtered_data
                if len(course) > 4 and course[4] == grade_filter  # Grade is at index 4
            ]

        self.populate_table()
        self.update_summary()

    def populate_table(self):
        """Populate the table with filtered data"""
        self.table.setRowCount(len(self.filtered_data))

        for row, course in enumerate(self.filtered_data):
            # Select checkbox
            checkbox = QCheckBox()
            self.table.setCellWidget(row, 0, checkbox)
            checkbox.stateChanged.connect(self.on_checkbox_changed)

            # Course data (handling different tuple lengths gracefully)
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
            for col, value in enumerate(items, 1):  # Start from column 1 (skip checkbox)
                item = QTableWidgetItem(str(value))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, col, item)

    def update_summary(self):
        """Update the summary label"""
        total_courses = len(self.filtered_data)
        total_credits = 0
        completed_courses = 0
        gpa_points = 0
        gpa_credits = 0

        for course in self.filtered_data:
            # Credits
            if len(course) > 3 and course[3]:
                try:
                    credits = float(course[3])
                    total_credits += credits

                    # GPA calculation
                    if len(course) > 4 and course[4] in self.GRADE_POINTS:
                        gpa_points += self.GRADE_POINTS[course[4]] * credits
                        gpa_credits += credits

                    # Count completed courses
                    if len(course) > 8 and course[8] == "completed":
                        completed_courses += 1
                except (ValueError, TypeError):
                    pass

        # Calculate GPA
        gpa = gpa_points / gpa_credits if gpa_credits > 0 else 0

        summary_text = (
            f"Showing {total_courses} courses | "
            f"Total Credits: {total_credits:.1f} | "
            f"Completed: {completed_courses} | "
            f"GPA: {gpa:.2f}"
        )
        self.summary_label.setText(summary_text)

    def clear_filters(self):
        """Clear all filters"""
        self.filter_course_code.clear()
        self.filter_session.setCurrentText("All")
        self.filter_year.setCurrentText("All")
        self.filter_grade.setCurrentText("All")

    def on_selection_changed(self):
        """Handle table selection changes"""
        selected_rows = self.table.selectionModel().selectedRows()
        has_selection = len(selected_rows) > 0

        self.edit_course_btn.setEnabled(has_selection)
        self.delete_course_btn.setEnabled(has_selection)

        if has_selection:
            row = selected_rows[0].row()
            if row < len(self.filtered_data):
                course_data = self.filtered_data[row]
                self.course_selected.emit(self.format_course_dict(course_data))

    def on_checkbox_changed(self):
        """Handle checkbox state changes"""
        selected_count = self.get_selected_count()
        self.bulk_edit_btn.setEnabled(selected_count > 0)
        self.bulk_delete_btn.setEnabled(selected_count > 0)

    def get_selected_count(self):
        """Get count of selected checkboxes"""
        count = 0
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                count += 1
        return count

    def get_selected_courses(self):
        """Get list of selected course data"""
        selected = []
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                if row < len(self.filtered_data):
                    selected.append(self.filtered_data[row])
        return selected

    def format_course_dict(self, course_tuple):
        """Convert course tuple to dictionary format"""
        return {
            'id': course_tuple[0] if len(course_tuple) > 0 else None,
            'course_code': course_tuple[1] if len(course_tuple) > 1 else "",
            'title': course_tuple[2] if len(course_tuple) > 2 else "",
            'credits': course_tuple[3] if len(course_tuple) > 3 else 0,
            'grade': course_tuple[4] if len(course_tuple) > 4 else "",
            'mark': course_tuple[5] if len(course_tuple) > 5 else None,
            'session': course_tuple[6] if len(course_tuple) > 6 else "",
            'year': course_tuple[7] if len(course_tuple) > 7 else 0,
            'status': course_tuple[8] if len(course_tuple) > 8 else ""
        }

    def show_context_menu(self, position):
        """Show context menu for table"""
        if self.table.itemAt(position) is None:
            return

        menu = QMenu(self)

        edit_action = QAction("Edit Course", self)
        edit_action.triggered.connect(self.edit_selected_course)
        menu.addAction(edit_action)

        delete_action = QAction("Delete Course", self)
        delete_action.triggered.connect(self.delete_selected_course)
        menu.addAction(delete_action)

        menu.addSeparator()

        view_details_action = QAction("View Details", self)
        view_details_action.triggered.connect(self.view_course_details)
        menu.addAction(view_details_action)

        menu.exec(self.table.mapToGlobal(position))

    def on_cell_double_clicked(self, row, column):
        """Handle double-click on table cell"""
        self.edit_selected_course()

    # Placeholder methods for course operations
    def add_course(self):
        """Add a new course to transcript"""
        QMessageBox.information(self, "Add Course", "Add course dialog will be implemented in Phase 2C")

    def edit_selected_course(self):
        """Edit the selected course"""
        QMessageBox.information(self, "Edit Course", "Edit course dialog will be implemented in Phase 2C")

    def delete_selected_course(self):
        """Delete the selected course"""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return

        reply = QMessageBox.question(
            self, "Delete Course",
            "Are you sure you want to delete the selected course?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Implementation will be added in Phase 2C
            QMessageBox.information(self, "Delete Course", "Delete functionality will be implemented in Phase 2C")

    def bulk_edit_courses(self):
        """Bulk edit selected courses"""
        selected = self.get_selected_courses()
        if not selected:
            return

        QMessageBox.information(
            self, "Bulk Edit",
            f"Bulk edit dialog for {len(selected)} courses will be implemented in Phase 2C"
        )

    def bulk_delete_courses(self):
        """Bulk delete selected courses"""
        selected = self.get_selected_courses()
        if not selected:
            return

        reply = QMessageBox.question(
            self, "Bulk Delete",
            f"Are you sure you want to delete {len(selected)} selected courses?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            QMessageBox.information(
                self, "Bulk Delete",
                "Bulk delete functionality will be implemented in Phase 2C"
            )

    def view_course_details(self):
        """View detailed course information"""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return

        QMessageBox.information(self, "Course Details", "Course details dialog will be implemented in Phase 2C")

    def refresh_data(self):
        """Refresh transcript data from database"""
        self.load_transcript_data()