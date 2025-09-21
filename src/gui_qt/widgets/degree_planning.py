"""
Degree Planning Widget for PyQt6 UofT Course Dashboard
Requirements tracking, course planning workspace, and program management
"""

from typing import Dict, List, Optional, Set
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTreeWidget,
    QTreeWidgetItem, QSplitter, QGroupBox, QListWidget, QListWidgetItem,
    QProgressBar, QFrame, QPushButton, QComboBox, QTextEdit,
    QFormLayout, QSpinBox, QCheckBox, QTabWidget, QScrollArea,
    QGridLayout, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData
from PyQt6.QtGui import QFont, QDragEnterEvent, QDropEvent, QPalette


class RequirementsTreeWidget(QTreeWidget):
    """Tree widget for displaying degree requirements with progress"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """Setup the requirements tree"""
        self.setHeaderLabels(["Requirement", "Progress", "Status"])
        self.setColumnWidth(0, 200)
        self.setColumnWidth(1, 100)
        self.setColumnWidth(2, 80)

        # Enable alternating row colors
        self.setAlternatingRowColors(True)
        self.setRootIsDecorated(True)


class RequirementsPanel(QGroupBox):
    """Left panel showing degree requirements and progress"""

    requirement_selected = pyqtSignal(dict)

    def __init__(self, database, parent=None):
        super().__init__("Degree Requirements", parent)
        self.database = database
        self.requirements_data = {}
        self.setup_ui()
        self.load_requirements()

    def setup_ui(self):
        """Setup requirements interface"""
        layout = QVBoxLayout(self)

        # Program selection
        program_layout = QFormLayout()
        self.program_combo = QComboBox()
        self.program_combo.addItem("Select a program...")
        program_layout.addRow("Program:", self.program_combo)
        layout.addLayout(program_layout)

        # Requirements tree
        self.requirements_tree = RequirementsTreeWidget()
        layout.addWidget(self.requirements_tree)

        # Overall progress
        progress_group = QGroupBox("Overall Progress")
        progress_layout = QVBoxLayout(progress_group)

        # Total credits progress
        self.overall_progress = QProgressBar()
        self.overall_progress.setMinimum(0)
        self.overall_progress.setMaximum(200)  # 20.0 credits
        self.overall_progress.setFormat("Credits: %v/20.0 (%p%)")
        progress_layout.addWidget(QLabel("Total Credits:"))
        progress_layout.addWidget(self.overall_progress)

        # GPA requirement
        self.gpa_progress = QProgressBar()
        self.gpa_progress.setMinimum(0)
        self.gpa_progress.setMaximum(400)  # 4.0 GPA * 100
        self.gpa_progress.setFormat("GPA: %v/1.85 minimum")
        progress_layout.addWidget(QLabel("Academic Standing:"))
        progress_layout.addWidget(self.gpa_progress)

        layout.addWidget(progress_group)

        # Connect signals
        self.program_combo.currentTextChanged.connect(self.on_program_changed)
        self.requirements_tree.itemClicked.connect(self.on_requirement_clicked)

    def load_requirements(self):
        """Load requirements data from database"""
        try:
            # Load programs
            programs = self.database.get_programs()
            self.program_combo.clear()
            self.program_combo.addItem("Select a program...")
            for program in programs:
                program_name = program[1] if len(program) > 1 else "Unknown Program"
                self.program_combo.addItem(program_name)

            # Load current progress
            self.update_progress()

        except Exception as e:
            print(f"Error loading requirements: {e}")

    def on_program_changed(self, program_name):
        """Handle program selection change"""
        if program_name == "Select a program...":
            self.clear_requirements_tree()
            return

        self.load_program_requirements(program_name)

    def load_program_requirements(self, program_name):
        """Load requirements for specific program"""
        self.requirements_tree.clear()

        # Create main requirement categories
        self.create_core_requirements()
        self.create_breadth_requirements()
        self.create_level_requirements()
        self.create_program_requirements(program_name)

    def create_core_requirements(self):
        """Create core degree requirements section"""
        core_item = QTreeWidgetItem(self.requirements_tree, ["Core Requirements", "", ""])
        core_item.setExpanded(True)

        # Total credits
        credits_item = QTreeWidgetItem(core_item, ["Total Credits", "0.0/20.0", "In Progress"])

        # Academic standing
        gpa_item = QTreeWidgetItem(core_item, ["Minimum GPA", "0.00/1.85", "In Progress"])

        # Arts & Science credits
        artsci_item = QTreeWidgetItem(core_item, ["A&S Credits", "0.0/10.0", "In Progress"])

    def create_breadth_requirements(self):
        """Create breadth requirements section"""
        breadth_item = QTreeWidgetItem(self.requirements_tree, ["Breadth Requirements", "0.0/4.0", "In Progress"])
        breadth_item.setExpanded(True)

        # Five breadth categories
        categories = [
            "Creative and Cultural Representations",
            "Thought, Belief and Behaviour",
            "Society and its Institutions",
            "Living Things and their Environment",
            "The Physical and Mathematical Universes"
        ]

        for category in categories:
            cat_item = QTreeWidgetItem(breadth_item, [category, "0.0/1.0", "Not Started"])

    def create_level_requirements(self):
        """Create course level requirements section"""
        level_item = QTreeWidgetItem(self.requirements_tree, ["Course Level Requirements", "", ""])
        level_item.setExpanded(True)

        # Upper level (200+)
        upper_item = QTreeWidgetItem(level_item, ["200+ Level Courses", "0.0/13.0", "In Progress"])

        # Advanced (300+)
        advanced_item = QTreeWidgetItem(level_item, ["300+ Level Courses", "0.0/6.0", "In Progress"])

    def create_program_requirements(self, program_name):
        """Create program-specific requirements"""
        program_item = QTreeWidgetItem(self.requirements_tree, [f"{program_name} Requirements", "", ""])
        program_item.setExpanded(True)

        # This would be populated based on specific program requirements
        placeholder_item = QTreeWidgetItem(program_item, ["Program Courses", "TBD", "Not Started"])

    def update_progress(self):
        """Update progress bars and tree items"""
        try:
            # Get transcript data
            courses = self.database.get_transcript_courses()

            total_credits = 0
            total_points = 0
            grade_credits = 0

            grade_points = {
                'A+': 4.0, 'A': 4.0, 'A-': 3.7,
                'B+': 3.3, 'B': 3.0, 'B-': 2.7,
                'C+': 2.3, 'C': 2.0, 'C-': 1.7,
                'D+': 1.3, 'D': 1.0, 'D-': 0.7,
                'F': 0.0, 'FZ': 0.0
            }

            for course in courses:
                if len(course) > 3 and course[3]:
                    credits = float(course[3])
                    total_credits += credits

                    if len(course) > 4 and course[4] in grade_points:
                        total_points += grade_points[course[4]] * credits
                        grade_credits += credits

            # Update progress bars
            self.overall_progress.setValue(int(total_credits * 10))

            gpa = total_points / grade_credits if grade_credits > 0 else 0.0
            self.gpa_progress.setValue(int(gpa * 100))
            self.gpa_progress.setFormat(f"GPA: {gpa:.2f}/1.85 minimum")

        except Exception as e:
            print(f"Error updating progress: {e}")

    def clear_requirements_tree(self):
        """Clear the requirements tree"""
        self.requirements_tree.clear()

    def on_requirement_clicked(self, item, column):
        """Handle requirement item click"""
        req_data = {
            'name': item.text(0),
            'progress': item.text(1),
            'status': item.text(2)
        }
        self.requirement_selected.emit(req_data)


class PlanningWorkspace(QGroupBox):
    """Center panel for course planning workspace"""

    course_planned = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__("Course Planning Workspace", parent)
        self.planned_courses = {}  # semester -> list of courses
        self.setup_ui()

    def setup_ui(self):
        """Setup planning workspace"""
        layout = QVBoxLayout(self)

        # Year/semester selection
        control_layout = QHBoxLayout()
        control_layout.addWidget(QLabel("Planning Year:"))

        self.year_combo = QComboBox()
        current_year = 2025
        for year in range(current_year, current_year + 4):
            self.year_combo.addItem(str(year))
        control_layout.addWidget(self.year_combo)

        control_layout.addStretch()
        layout.addLayout(control_layout)

        # Create semester planning area
        self.create_semester_layout(layout)

        # Planning summary
        self.create_summary_section(layout)

    def create_semester_layout(self, layout):
        """Create semester planning grid"""
        semester_widget = QWidget()
        semester_layout = QGridLayout(semester_widget)

        # Create semester boxes
        self.semester_widgets = {}
        semesters = ["Fall", "Winter", "Summer"]

        for i, semester in enumerate(semesters):
            semester_group = QGroupBox(f"{semester} Semester")
            semester_group_layout = QVBoxLayout(semester_group)

            # Planned courses list
            semester_list = QListWidget()
            semester_list.setMaximumHeight(200)
            semester_list.setAcceptDrops(True)
            semester_list.setDragDropMode(QListWidget.DragDropMode.DropOnly)
            semester_group_layout.addWidget(semester_list)

            # Add course button
            add_btn = QPushButton(f"Add Course to {semester}")
            add_btn.clicked.connect(lambda checked, s=semester: self.add_course_to_semester(s))
            semester_group_layout.addWidget(add_btn)

            # Credits summary
            credits_label = QLabel("Credits: 0.0")
            semester_group_layout.addWidget(credits_label)

            semester_layout.addWidget(semester_group, 0, i)

            self.semester_widgets[semester] = {
                'group': semester_group,
                'list': semester_list,
                'credits_label': credits_label
            }

        layout.addWidget(semester_widget)

    def create_summary_section(self, layout):
        """Create planning summary section"""
        summary_group = QGroupBox("Planning Summary")
        summary_layout = QVBoxLayout(summary_group)

        self.summary_text = QTextEdit()
        self.summary_text.setMaximumHeight(100)
        self.summary_text.setReadOnly(True)
        self.summary_text.setPlainText("No courses planned yet")
        summary_layout.addWidget(self.summary_text)

        layout.addWidget(summary_group)

    def add_course_to_semester(self, semester):
        """Add a course to specific semester"""
        # This would open a course selection dialog
        from PyQt6.QtWidgets import QInputDialog

        course_code, ok = QInputDialog.getText(
            self, f"Add Course to {semester}",
            "Enter course code:"
        )

        if ok and course_code:
            self.add_planned_course(semester, {
                'course_code': course_code.strip().upper(),
                'title': 'Planned Course',
                'credits': '0.5'  # Default
            })

    def add_planned_course(self, semester, course_data):
        """Add a course to the planning workspace"""
        semester_list = self.semester_widgets[semester]['list']

        # Create list item
        course_text = f"{course_data['course_code']} ({course_data.get('credits', '0.5')} credits)"
        item = QListWidgetItem(course_text)
        semester_list.addItem(item)

        # Update credits
        self.update_semester_credits(semester)
        self.update_summary()

        # Emit signal
        self.course_planned.emit(course_data)

    def update_semester_credits(self, semester):
        """Update credits display for semester"""
        semester_list = self.semester_widgets[semester]['list']
        credits_label = self.semester_widgets[semester]['credits_label']

        total_credits = 0
        for i in range(semester_list.count()):
            item = semester_list.item(i)
            # Extract credits from item text (rough parsing)
            if '(' in item.text() and 'credits)' in item.text():
                try:
                    credits_str = item.text().split('(')[1].split(' credits)')[0]
                    total_credits += float(credits_str)
                except:
                    total_credits += 0.5  # Default

        credits_label.setText(f"Credits: {total_credits:.1f}")

    def update_summary(self):
        """Update planning summary"""
        total_courses = 0
        total_credits = 0

        for semester in self.semester_widgets:
            semester_list = self.semester_widgets[semester]['list']
            course_count = semester_list.count()
            total_courses += course_count

            # Calculate credits for this semester
            for i in range(course_count):
                try:
                    item = semester_list.item(i)
                    if '(' in item.text() and 'credits)' in item.text():
                        credits_str = item.text().split('(')[1].split(' credits)')[0]
                        total_credits += float(credits_str)
                    else:
                        total_credits += 0.5
                except:
                    total_credits += 0.5

        summary = f"Total Planned: {total_courses} courses, {total_credits:.1f} credits"
        self.summary_text.setPlainText(summary)


class CourseCatalog(QGroupBox):
    """Right panel for browsing available courses"""

    course_selected = pyqtSignal(dict)

    def __init__(self, database, parent=None):
        super().__init__("Course Catalog", parent)
        self.database = database
        self.setup_ui()
        self.load_catalog()

    def setup_ui(self):
        """Setup catalog interface"""
        layout = QVBoxLayout(self)

        # Search/filter controls
        search_layout = QFormLayout()

        self.department_filter = QComboBox()
        self.department_filter.addItem("All Departments")
        search_layout.addRow("Department:", self.department_filter)

        self.level_filter = QComboBox()
        self.level_filter.addItems(["All Levels", "100-level", "200-level", "300-level", "400-level"])
        search_layout.addRow("Level:", self.level_filter)

        layout.addLayout(search_layout)

        # Course list
        self.course_list = QListWidget()
        self.course_list.setDragEnabled(True)
        self.course_list.setDefaultDropAction(Qt.DropAction.CopyAction)
        layout.addWidget(self.course_list)

        # Course details
        self.details_text = QTextEdit()
        self.details_text.setMaximumHeight(150)
        self.details_text.setReadOnly(True)
        layout.addWidget(self.details_text)

        # Connect signals
        self.department_filter.currentTextChanged.connect(self.apply_filters)
        self.level_filter.currentTextChanged.connect(self.apply_filters)
        self.course_list.itemClicked.connect(self.on_course_selected)

    def load_catalog(self):
        """Load available courses"""
        try:
            # This would load from a comprehensive course database
            # For now, add some sample courses
            sample_courses = [
                {"course_code": "CSC108H1", "title": "Introduction to Computer Programming", "credits": "0.5", "level": "100"},
                {"course_code": "CSC148H1", "title": "Introduction to Computer Science", "credits": "0.5", "level": "100"},
                {"course_code": "CSC207H1", "title": "Software Design", "credits": "0.5", "level": "200"},
                {"course_code": "MAT137Y1", "title": "Calculus", "credits": "1.0", "level": "100"},
                {"course_code": "MAT223H1", "title": "Linear Algebra", "credits": "0.5", "level": "200"},
            ]

            self.all_courses = sample_courses
            self.apply_filters()

        except Exception as e:
            print(f"Error loading catalog: {e}")

    def apply_filters(self):
        """Apply current filters to course list"""
        if not hasattr(self, 'all_courses'):
            return

        filtered_courses = self.all_courses.copy()

        # Department filter
        dept_filter = self.department_filter.currentText()
        if dept_filter != "All Departments":
            dept_code = dept_filter.split(' - ')[0] if ' - ' in dept_filter else dept_filter
            filtered_courses = [c for c in filtered_courses
                              if c['course_code'].startswith(dept_code)]

        # Level filter
        level_filter = self.level_filter.currentText()
        if level_filter != "All Levels":
            level = level_filter.split('-')[0]  # Extract number
            filtered_courses = [c for c in filtered_courses
                              if c.get('level', '').startswith(level)]

        # Populate list
        self.course_list.clear()
        for course in filtered_courses:
            item_text = f"{course['course_code']} - {course['title']} ({course['credits']} credits)"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, course)
            self.course_list.addItem(item)

    def on_course_selected(self, item):
        """Handle course selection"""
        course_data = item.data(Qt.ItemDataRole.UserRole)
        if course_data:
            # Display course details
            details = f"<b>{course_data['course_code']}: {course_data['title']}</b><br>"
            details += f"Credits: {course_data['credits']}<br>"
            details += f"Level: {course_data.get('level', 'Unknown')}-level course"

            self.details_text.setHtml(details)
            self.course_selected.emit(course_data)


class DegreePlanningWidget(QWidget):
    """Main degree planning widget with three-panel layout"""

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

        # Left panel - Requirements
        self.requirements_panel = RequirementsPanel(self.database)
        self.requirements_panel.setMinimumWidth(300)
        self.requirements_panel.setMaximumWidth(400)
        main_splitter.addWidget(self.requirements_panel)

        # Center panel - Planning workspace
        self.planning_workspace = PlanningWorkspace()
        main_splitter.addWidget(self.planning_workspace)

        # Right panel - Course catalog
        self.course_catalog = CourseCatalog(self.database)
        self.course_catalog.setMinimumWidth(250)
        self.course_catalog.setMaximumWidth(350)
        main_splitter.addWidget(self.course_catalog)

        # Set proportions
        main_splitter.setSizes([350, 500, 300])

        layout.addWidget(main_splitter)

    def setup_connections(self):
        """Setup signal connections between panels"""
        # Requirements panel signals
        self.requirements_panel.requirement_selected.connect(self.on_requirement_selected)

        # Planning workspace signals
        self.planning_workspace.course_planned.connect(self.on_course_planned)

        # Course catalog signals
        self.course_catalog.course_selected.connect(self.on_catalog_course_selected)

    def on_requirement_selected(self, requirement_data):
        """Handle requirement selection"""
        # Could highlight related courses in catalog
        print(f"Requirement selected: {requirement_data['name']}")

    def on_course_planned(self, course_data):
        """Handle course being added to plan"""
        # Update requirements progress if applicable
        self.requirements_panel.update_progress()

    def on_catalog_course_selected(self, course_data):
        """Handle course selection from catalog"""
        # Course details are already shown in catalog panel
        pass

    def refresh_data(self):
        """Refresh all panel data"""
        self.requirements_panel.load_requirements()
        self.course_catalog.load_catalog()