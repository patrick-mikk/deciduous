"""
Course Dialog for PyQt6 UofT Course Dashboard
Add/Edit course dialog with comprehensive data entry
"""

from typing import Dict, Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QLineEdit, QPushButton, QComboBox, QSpinBox, QDoubleSpinBox,
    QTextEdit, QDialogButtonBox, QGroupBox, QMessageBox,
    QCheckBox, QDateEdit, QTabWidget, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QDate
from PyQt6.QtGui import QFont

class CourseDialog(QDialog):
    """Dialog for adding/editing course information"""

    course_saved = pyqtSignal(dict)

    def __init__(self, parent=None, course_data=None, data_manager=None):
        super().__init__(parent)
        self.course_data = course_data or {}
        self.data_manager = data_manager
        self.is_edit_mode = bool(course_data)

        self.setup_ui()
        self.populate_data()

        # Connect to data manager validation errors if available
        if self.data_manager:
            self.data_manager.validation_error.connect(self.show_validation_error)

    def setup_ui(self):
        """Setup the dialog layout"""
        title = "Edit Course" if self.is_edit_mode else "Add New Course"
        self.setWindowTitle(title)
        self.setFixedSize(500, 600)

        layout = QVBoxLayout(self)

        # Create tab widget for organized data entry
        self.tab_widget = QTabWidget()

        # Basic Information Tab
        self.basic_tab = self.create_basic_tab()
        self.tab_widget.addTab(self.basic_tab, "Basic Info")

        # Academic Details Tab
        self.academic_tab = self.create_academic_tab()
        self.tab_widget.addTab(self.academic_tab, "Academic")

        # Additional Info Tab
        self.additional_tab = self.create_additional_tab()
        self.tab_widget.addTab(self.additional_tab, "Additional")

        layout.addWidget(self.tab_widget)

        # Button box
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept_course)
        button_box.rejected.connect(self.reject)

        layout.addWidget(button_box)

    def create_basic_tab(self):
        """Create basic information tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Course identification
        id_group = QGroupBox("Course Identification")
        id_form = QFormLayout(id_group)

        self.course_code_edit = QLineEdit()
        self.course_code_edit.setPlaceholderText("e.g., CSC108H1")
        self.course_code_edit.setToolTip("Enter the full course code including section")
        id_form.addRow("Course Code*:", self.course_code_edit)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("e.g., Introduction to Computer Programming")
        self.title_edit.setToolTip("Enter the official course title")
        id_form.addRow("Course Title*:", self.title_edit)

        self.department_combo = QComboBox()
        self.department_combo.setEditable(True)
        departments = [
            "Computer Science", "Mathematics", "Statistics", "Physics",
            "Chemistry", "Biology", "Economics", "Psychology", "Philosophy",
            "History", "English", "Political Science", "Anthropology", "Sociology"
        ]
        self.department_combo.addItems(departments)
        id_form.addRow("Department:", self.department_combo)

        layout.addWidget(id_group)

        # Credits and level
        credit_group = QGroupBox("Academic Classification")
        credit_form = QFormLayout(credit_group)

        self.credits_spin = QDoubleSpinBox()
        self.credits_spin.setRange(0.0, 6.0)
        self.credits_spin.setSingleStep(0.5)
        self.credits_spin.setValue(0.5)
        self.credits_spin.setToolTip("Credit weight (typically 0.5 for half-courses, 1.0 for full courses)")
        credit_form.addRow("Credits*:", self.credits_spin)

        self.level_combo = QComboBox()
        self.level_combo.addItems(["100-level", "200-level", "300-level", "400-level", "Graduate"])
        credit_form.addRow("Course Level:", self.level_combo)

        self.breadth_combo = QComboBox()
        breadth_categories = [
            "None", "Breadth Requirement 1", "Breadth Requirement 2",
            "Breadth Requirement 3", "Breadth Requirement 4", "Breadth Requirement 5"
        ]
        self.breadth_combo.addItems(breadth_categories)
        credit_form.addRow("Breadth Category:", self.breadth_combo)

        layout.addWidget(credit_group)
        layout.addStretch()

        return tab

    def create_academic_tab(self):
        """Create academic performance tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Performance data
        performance_group = QGroupBox("Academic Performance")
        performance_form = QFormLayout(performance_group)

        self.grade_combo = QComboBox()
        grades = ["", "A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "D-", "F", "FZ", "P", "CR", "NCR"]
        self.grade_combo.addItems(grades)
        self.grade_combo.setToolTip("Select the final letter grade received")
        performance_form.addRow("Grade:", self.grade_combo)

        self.mark_spin = QSpinBox()
        self.mark_spin.setRange(0, 100)
        self.mark_spin.setValue(0)
        self.mark_spin.setSpecialValueText("Not Set")
        self.mark_spin.setToolTip("Numerical grade percentage (optional)")
        performance_form.addRow("Mark (%):", self.mark_spin)

        self.gpa_points_spin = QDoubleSpinBox()
        self.gpa_points_spin.setRange(0.0, 4.0)
        self.gpa_points_spin.setSingleStep(0.1)
        self.gpa_points_spin.setReadOnly(True)
        self.gpa_points_spin.setToolTip("GPA points calculated from grade (read-only)")
        performance_form.addRow("GPA Points:", self.gpa_points_spin)

        # Connect grade change to auto-calculate GPA points
        self.grade_combo.currentTextChanged.connect(self.update_gpa_points)

        layout.addWidget(performance_group)

        # Session information
        session_group = QGroupBox("Session Information")
        session_form = QFormLayout(session_group)

        self.session_combo = QComboBox()
        self.session_combo.addItems(["Fall", "Winter", "Summer"])
        session_form.addRow("Session*:", self.session_combo)

        self.year_spin = QSpinBox()
        self.year_spin.setRange(2000, 2030)
        self.year_spin.setValue(2024)
        session_form.addRow("Year*:", self.year_spin)

        self.status_combo = QComboBox()
        statuses = ["Completed", "In Progress", "Planned", "Dropped", "Withdrawn"]
        self.status_combo.addItems(statuses)
        session_form.addRow("Status:", self.status_combo)

        layout.addWidget(session_group)
        layout.addStretch()

        return tab

    def create_additional_tab(self):
        """Create additional information tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Prerequisites and notes
        prereq_group = QGroupBox("Course Details")
        prereq_layout = QVBoxLayout(prereq_group)

        prereq_layout.addWidget(QLabel("Prerequisites:"))
        self.prerequisites_edit = QTextEdit()
        self.prerequisites_edit.setMaximumHeight(80)
        self.prerequisites_edit.setPlaceholderText("Enter prerequisite courses or requirements...")
        prereq_layout.addWidget(self.prerequisites_edit)

        prereq_layout.addWidget(QLabel("Course Description:"))
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(100)
        self.description_edit.setPlaceholderText("Enter course description...")
        prereq_layout.addWidget(self.description_edit)

        prereq_layout.addWidget(QLabel("Personal Notes:"))
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(80)
        self.notes_edit.setPlaceholderText("Add personal notes about this course...")
        prereq_layout.addWidget(self.notes_edit)

        layout.addWidget(prereq_group)

        # Flags and options
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout(options_group)

        self.exclude_gpa_check = QCheckBox("Exclude from GPA calculation")
        self.exclude_gpa_check.setToolTip("Check if this course should not count toward GPA")
        options_layout.addWidget(self.exclude_gpa_check)

        self.repeat_check = QCheckBox("Course repeat")
        self.repeat_check.setToolTip("Check if this is a repeated course")
        options_layout.addWidget(self.repeat_check)

        layout.addWidget(options_group)
        layout.addStretch()

        return tab

    def update_gpa_points(self, grade):
        """Update GPA points based on selected grade"""
        grade_points = {
            'A+': 4.0, 'A': 4.0, 'A-': 3.7,
            'B+': 3.3, 'B': 3.0, 'B-': 2.7,
            'C+': 2.3, 'C': 2.0, 'C-': 1.7,
            'D+': 1.3, 'D': 1.0, 'D-': 0.7,
            'F': 0.0, 'FZ': 0.0
        }
        points = grade_points.get(grade, 0.0)
        self.gpa_points_spin.setValue(points)

    def populate_data(self):
        """Populate form with existing course data if editing"""
        if not self.course_data:
            return

        # Basic information
        course_code = self.course_data.get('course_code', '')
        self.course_code_edit.setText(course_code)

        # If course code came from academic calendar search, make it read-only to prevent accidental changes
        if course_code and not self.is_edit_mode:
            self.course_code_edit.setReadOnly(True)
            self.course_code_edit.setStyleSheet("background-color: #f0f0f0;")

        self.title_edit.setText(self.course_data.get('title', ''))

        if 'credits' in self.course_data:
            self.credits_spin.setValue(float(self.course_data['credits']))

        # Academic performance
        if 'grade' in self.course_data:
            grade = self.course_data['grade']
            index = self.grade_combo.findText(grade)
            if index >= 0:
                self.grade_combo.setCurrentIndex(index)

        if 'mark' in self.course_data and self.course_data['mark'] is not None:
            self.mark_spin.setValue(int(self.course_data['mark']))

        # Session information
        if 'session' in self.course_data:
            session = self.course_data['session']
            index = self.session_combo.findText(session)
            if index >= 0:
                self.session_combo.setCurrentIndex(index)

        if 'year' in self.course_data:
            self.year_spin.setValue(int(self.course_data['year']))

        if 'status' in self.course_data:
            status = self.course_data['status']
            index = self.status_combo.findText(status)
            if index >= 0:
                self.status_combo.setCurrentIndex(index)

        # Academic details - populate from scraped data
        if 'prerequisites' in self.course_data:
            self.prerequisites_edit.setPlainText(str(self.course_data['prerequisites']))

        if 'description' in self.course_data:
            self.description_edit.setPlainText(str(self.course_data['description']))

        if 'breadth_requirements' in self.course_data and self.course_data['breadth_requirements']:
            # Try to match breadth requirement text
            breadth_text = str(self.course_data['breadth_requirements'])
            for i in range(self.breadth_combo.count()):
                if breadth_text.lower() in self.breadth_combo.itemText(i).lower():
                    self.breadth_combo.setCurrentIndex(i)
                    break

        # Additional fields if available
        if 'exclusions' in self.course_data:
            # Store exclusions in notes for now (we can add an exclusions field later)
            existing_notes = getattr(self, 'notes_edit', None)
            if existing_notes and self.course_data['exclusions']:
                current_text = existing_notes.toPlainText()
                exclusions_text = f"Exclusions: {self.course_data['exclusions']}"
                if current_text:
                    existing_notes.setPlainText(f"{current_text}\n\n{exclusions_text}")
                else:
                    existing_notes.setPlainText(exclusions_text)

    def validate_data(self):
        """Validate form data before saving"""
        errors = []

        # Required fields
        if not self.course_code_edit.text().strip():
            errors.append("Course code is required")

        if not self.title_edit.text().strip():
            errors.append("Course title is required")

        if self.credits_spin.value() <= 0:
            errors.append("Credits must be greater than 0")

        # Course code format validation
        course_code = self.course_code_edit.text().strip().upper()
        if course_code and len(course_code) < 6:
            errors.append("Course code appears to be too short")

        return errors

    def show_validation_error(self, field, error):
        """Show validation error from data manager"""
        QMessageBox.warning(self, "Validation Error", f"Error in {field}: {error}")

    def get_course_data(self):
        """Get course data from form"""
        mark_value = self.mark_spin.value() if self.mark_spin.value() > 0 else None

        # Ensure course code is not empty
        course_code = self.course_code_edit.text().strip().upper()
        if not course_code:
            # Try to restore from original course data if available
            course_code = self.course_data.get('course_code', '').strip().upper()

        return {
            'course_code': course_code,
            'title': self.title_edit.text().strip(),
            'credits': self.credits_spin.value(),
            'grade': self.grade_combo.currentText() if self.grade_combo.currentText() else None,
            'mark': mark_value,
            'session': self.session_combo.currentText(),
            'year': self.year_spin.value(),
            'status': self.status_combo.currentText(),
            'department': self.department_combo.currentText(),
            'level': self.level_combo.currentText(),
            'breadth': self.breadth_combo.currentText(),
            'prerequisites': self.prerequisites_edit.toPlainText().strip(),
            'description': self.description_edit.toPlainText().strip(),
            'notes': self.notes_edit.toPlainText().strip(),
            'exclude_gpa': self.exclude_gpa_check.isChecked(),
            'is_repeat': self.repeat_check.isChecked()
        }

    def accept_course(self):
        """Validate and accept course data"""
        errors = self.validate_data()

        if errors:
            QMessageBox.warning(
                self, "Validation Error",
                "Please fix the following errors:\n\n" + "\n".join(f"• {error}" for error in errors)
            )
            return

        course_data = self.get_course_data()

        # Use data manager if available
        if self.data_manager:
            try:
                if self.is_edit_mode:
                    course_id = self.course_data.get('id')
                    success = self.data_manager.modify_course(course_id, course_data)
                else:
                    success = self.data_manager.add_course(course_data)

                if success:
                    self.course_saved.emit(course_data)
                    self.accept()
                else:
                    # Show more detailed error message
                    error_msg = "Failed to save course. Please check:\n"
                    error_msg += f"• Course code: '{course_data.get('course_code', '')}'\n"
                    error_msg += f"• Course title: '{course_data.get('title', '')}'\n"
                    error_msg += f"• Credits: {course_data.get('credits', 'N/A')}\n"
                    error_msg += f"• Year: {course_data.get('year', 'N/A')}"
                    QMessageBox.warning(self, "Save Error", error_msg)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"An error occurred while saving: {str(e)}")
        else:
            # Fallback: emit signal for manual handling
            self.course_saved.emit(course_data)
            self.accept()

class QuickAddCourseDialog(QDialog):
    """Simplified dialog for quick course addition"""

    course_saved = pyqtSignal(dict)

    def __init__(self, parent=None, course_data=None):
        super().__init__(parent)
        self.course_data = course_data or {}
        self.setup_ui()
        self.populate_data()

    def setup_ui(self):
        """Setup simplified layout"""
        self.setWindowTitle("Quick Add Course")
        self.setFixedSize(400, 300)

        layout = QVBoxLayout(self)

        # Essential fields only
        form_layout = QFormLayout()

        self.course_code_edit = QLineEdit()
        self.course_code_edit.setPlaceholderText("e.g., CSC108H1")
        form_layout.addRow("Course Code*:", self.course_code_edit)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Course title")
        form_layout.addRow("Title*:", self.title_edit)

        self.credits_spin = QDoubleSpinBox()
        self.credits_spin.setRange(0.0, 6.0)
        self.credits_spin.setSingleStep(0.5)
        self.credits_spin.setValue(0.5)
        form_layout.addRow("Credits*:", self.credits_spin)

        self.session_combo = QComboBox()
        self.session_combo.addItems(["Fall", "Winter", "Summer"])
        form_layout.addRow("Session*:", self.session_combo)

        self.year_spin = QSpinBox()
        self.year_spin.setRange(2000, 2030)
        self.year_spin.setValue(2024)
        form_layout.addRow("Year*:", self.year_spin)

        layout.addLayout(form_layout)

        # Buttons
        button_layout = QHBoxLayout()

        add_btn = QPushButton("Add Course")
        add_btn.clicked.connect(self.accept_course)
        button_layout.addWidget(add_btn)

        detailed_btn = QPushButton("Detailed Entry...")
        detailed_btn.clicked.connect(self.open_detailed_dialog)
        button_layout.addWidget(detailed_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

    def populate_data(self):
        """Populate with provided course data"""
        if 'course_code' in self.course_data:
            self.course_code_edit.setText(self.course_data['course_code'])
        if 'title' in self.course_data:
            self.title_edit.setText(self.course_data['title'])
        if 'credits' in self.course_data:
            self.credits_spin.setValue(float(self.course_data['credits']))

    def accept_course(self):
        """Quick validation and accept"""
        course_code = self.course_code_edit.text().strip()
        title = self.title_edit.text().strip()

        if not course_code or not title:
            QMessageBox.warning(self, "Required Fields", "Course code and title are required.")
            return

        course_data = {
            'course_code': course_code.upper(),
            'title': title,
            'credits': self.credits_spin.value(),
            'session': self.session_combo.currentText(),
            'year': self.year_spin.value(),
            'status': 'Planned'
        }

        self.course_saved.emit(course_data)
        self.accept()

    def open_detailed_dialog(self):
        """Open detailed course dialog"""
        course_data = {
            'course_code': self.course_code_edit.text().strip(),
            'title': self.title_edit.text().strip(),
            'credits': self.credits_spin.value(),
            'session': self.session_combo.currentText(),
            'year': self.year_spin.value()
        }

        detailed_dialog = CourseDialog(self.parent(), course_data)
        detailed_dialog.course_saved.connect(self.course_saved.emit)
        self.close()
        detailed_dialog.exec()