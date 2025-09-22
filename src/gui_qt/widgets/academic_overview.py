"""
Academic Overview Widget for PyQt6 UofT Course Dashboard
Main dashboard with status cards, progress visualization, and quick actions
"""

from typing import Dict, List, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QGroupBox, QProgressBar, QListWidget, QListWidgetItem,
    QPushButton, QFrame, QSplitter, QLineEdit, QTextEdit,
    QFormLayout, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPalette


class StatusCard(QGroupBox):
    """Individual status card widget for key metrics"""

    def __init__(self, title: str, value: str, subtitle: str = "", parent=None):
        super().__init__(title, parent)
        self.setup_ui(value, subtitle)

    def setup_ui(self, value: str, subtitle: str):
        """Setup the status card layout"""
        layout = QVBoxLayout(self)

        # Main value
        value_label = QLabel(value)
        value_font = QFont()
        value_font.setPointSize(24)
        value_font.setBold(True)
        value_label.setFont(value_font)
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(value_label)

        # Subtitle if provided
        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_font = QFont()
            subtitle_font.setPointSize(9)
            subtitle_label.setFont(subtitle_font)
            subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            # Use system colors for subtitle
            palette = subtitle_label.palette()
            palette.setColor(QPalette.ColorRole.WindowText,
                           palette.color(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText))
            subtitle_label.setPalette(palette)
            layout.addWidget(subtitle_label)

        self.setMaximumHeight(120)
        self.setMinimumHeight(100)

    def update_value(self, value: str, subtitle: str = ""):
        """Update the card's displayed values"""
        layout = self.layout()
        # Update value label (first item)
        if layout.itemAt(0):
            layout.itemAt(0).widget().setText(value)
        # Update subtitle if it exists (second item)
        if layout.itemAt(1) and subtitle:
            layout.itemAt(1).widget().setText(subtitle)


class ProgressSection(QGroupBox):
    """Progress visualization section with native progress bars"""

    def __init__(self, parent=None):
        super().__init__("Degree Progress", parent)
        self.setup_ui()

    def setup_ui(self):
        """Setup progress bars and labels"""
        layout = QVBoxLayout(self)

        # Overall progress
        overall_layout = QHBoxLayout()
        overall_label = QLabel("Overall Completion:")
        overall_label.setMinimumWidth(150)
        self.overall_progress = QProgressBar()
        self.overall_progress.setMinimum(0)
        self.overall_progress.setMaximum(200)  # 20.0 credits * 10
        self.overall_progress.setValue(0)
        self.overall_progress.setFormat("%p% (%v/20.0 credits)")
        overall_layout.addWidget(overall_label)
        overall_layout.addWidget(self.overall_progress)
        layout.addLayout(overall_layout)

        # Upper level credits
        upper_layout = QHBoxLayout()
        upper_label = QLabel("Upper Level (200+):")
        upper_label.setMinimumWidth(150)
        self.upper_progress = QProgressBar()
        self.upper_progress.setMinimum(0)
        self.upper_progress.setMaximum(130)  # 13.0 credits * 10
        self.upper_progress.setValue(0)
        self.upper_progress.setFormat("%p% (%v/13.0 credits)")
        upper_layout.addWidget(upper_label)
        upper_layout.addWidget(self.upper_progress)
        layout.addLayout(upper_layout)

        # Advanced credits
        advanced_layout = QHBoxLayout()
        advanced_label = QLabel("Advanced (300+):")
        advanced_label.setMinimumWidth(150)
        self.advanced_progress = QProgressBar()
        self.advanced_progress.setMinimum(0)
        self.advanced_progress.setMaximum(60)  # 6.0 credits * 10
        self.advanced_progress.setValue(0)
        self.advanced_progress.setFormat("%p% (%v/6.0 credits)")
        advanced_layout.addWidget(advanced_label)
        advanced_layout.addWidget(self.advanced_progress)
        layout.addLayout(advanced_layout)

        # Breadth requirements
        breadth_layout = QHBoxLayout()
        breadth_label = QLabel("Breadth Requirements:")
        breadth_label.setMinimumWidth(150)
        self.breadth_progress = QProgressBar()
        self.breadth_progress.setMinimum(0)
        self.breadth_progress.setMaximum(40)  # 4.0 credits * 10
        self.breadth_progress.setValue(0)
        self.breadth_progress.setFormat("%p% (%v/4.0 credits)")
        breadth_layout.addWidget(breadth_label)
        breadth_layout.addWidget(self.breadth_progress)
        layout.addLayout(breadth_layout)

    def update_progress(self, progress_data: Dict):
        """Update progress bars with current data"""
        if 'total_credits' in progress_data:
            self.overall_progress.setValue(int(progress_data['total_credits'] * 10))
        if 'upper_credits' in progress_data:
            self.upper_progress.setValue(int(progress_data['upper_credits'] * 10))
        if 'advanced_credits' in progress_data:
            self.advanced_progress.setValue(int(progress_data['advanced_credits'] * 10))
        if 'breadth_credits' in progress_data:
            self.breadth_progress.setValue(int(progress_data['breadth_credits'] * 10))


class ActivityTimeline(QGroupBox):
    """Recent activity timeline using QListWidget"""

    def __init__(self, parent=None):
        super().__init__("Recent Activity", parent)
        self.setup_ui()

    def setup_ui(self):
        """Setup activity list"""
        layout = QVBoxLayout(self)

        self.activity_list = QListWidget()
        self.activity_list.setMaximumHeight(150)
        layout.addWidget(self.activity_list)

        # Add some placeholder items
        self.add_activity("Application started", "Welcome to UofT Course Dashboard")
        self.add_activity("Database loaded", "Found existing transcript data")

    def add_activity(self, title: str, description: str):
        """Add an activity item to the timeline"""
        item_text = f"{title}\n{description}"
        item = QListWidgetItem(item_text)
        self.activity_list.insertItem(0, item)  # Add to top

        # Limit to 10 items
        if self.activity_list.count() > 10:
            self.activity_list.takeItem(self.activity_list.count() - 1)


class QuickActions(QGroupBox):
    """Quick action panel with course lookup and common tasks"""

    course_search_requested = pyqtSignal(str)
    course_add_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("Quick Actions", parent)
        self.setup_ui()

    def setup_ui(self):
        """Setup quick action controls"""
        layout = QVBoxLayout(self)

        # Quick course search
        search_layout = QVBoxLayout()
        search_label = QLabel("Quick Course Lookup:")
        search_layout.addWidget(search_label)

        self.course_input = QLineEdit()
        self.course_input.setPlaceholderText("Enter course code (e.g. CSC108H1)")
        self.course_input.setToolTip("Enter a course code to search the Academic Calendar for details")
        search_layout.addWidget(self.course_input)

        search_btn = QPushButton("Search Academic Calendar")
        search_btn.clicked.connect(self.on_search_requested)
        search_layout.addWidget(search_btn)

        layout.addLayout(search_layout)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)

        # Common actions
        actions_layout = QVBoxLayout()

        add_course_btn = QPushButton("Add Course to Transcript")
        add_course_btn.setToolTip("Add a new course to your transcript")
        add_course_btn.clicked.connect(self.course_add_requested.emit)
        actions_layout.addWidget(add_course_btn)

        view_requirements_btn = QPushButton("View Degree Requirements")
        view_requirements_btn.setToolTip("View your degree requirements and progress")
        view_requirements_btn.clicked.connect(self.on_requirements_requested)
        actions_layout.addWidget(view_requirements_btn)

        export_btn = QPushButton("Export Transcript")
        export_btn.setToolTip("Export your transcript to a file")
        export_btn.clicked.connect(self.on_export_requested)
        actions_layout.addWidget(export_btn)

        layout.addLayout(actions_layout)

        # Connect enter key to search
        self.course_input.returnPressed.connect(self.on_search_requested)

    def on_search_requested(self):
        """Handle search request"""
        course_code = self.course_input.text().strip()
        if course_code:
            self.course_search_requested.emit(course_code)
            self.course_input.clear()

    def on_requirements_requested(self):
        """Handle requirements view request"""
        # This will be connected to switch to planning tab
        pass

    def on_export_requested(self):
        """Handle export request"""
        # This will be connected to export functionality
        pass


class AcademicOverviewWidget(QWidget):
    """Main academic overview dashboard widget"""

    course_search_requested = pyqtSignal(str)
    tab_switch_requested = pyqtSignal(int)  # Request to switch to specific tab

    def __init__(self, database, data_manager=None, parent=None):
        super().__init__(parent)
        self.database = database
        self.data_manager = data_manager
        self.setup_ui()
        self.setup_connections()
        self.load_data()

    def setup_ui(self):
        """Setup the main dashboard layout"""
        layout = QVBoxLayout(self)

        # Create main horizontal splitter
        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel - Status and progress
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # Status cards section
        self.create_status_cards(left_layout)

        # Progress section
        self.progress_section = ProgressSection()
        left_layout.addWidget(self.progress_section)

        # Activity timeline
        self.activity_timeline = ActivityTimeline()
        left_layout.addWidget(self.activity_timeline)

        main_splitter.addWidget(left_panel)

        # Right panel - Quick actions
        self.quick_actions = QuickActions()
        self.quick_actions.setMaximumWidth(300)
        self.quick_actions.setMinimumWidth(250)
        main_splitter.addWidget(self.quick_actions)

        # Set splitter proportions
        main_splitter.setSizes([600, 300])

        layout.addWidget(main_splitter)

    def create_status_cards(self, layout):
        """Create the status cards section"""
        cards_group = QGroupBox("Academic Status")
        cards_layout = QGridLayout(cards_group)

        # Create status cards with tooltips
        self.gpa_card = StatusCard("Current GPA", "0.00", "Cumulative")
        self.gpa_card.setToolTip("Your current Grade Point Average based on completed courses with grades")

        self.credits_card = StatusCard("Credits Earned", "0.0", "of 20.0 required")
        self.credits_card.setToolTip("Total credits completed toward your degree (20.0 credits required)")

        self.standing_card = StatusCard("Academic Standing", "Good", "Satisfactory Progress")
        self.standing_card.setToolTip("Your current academic standing based on GPA and progress")

        self.completion_card = StatusCard("Degree Progress", "0%", "Estimated completion")
        self.completion_card.setToolTip("Percentage of degree requirements completed")

        # Arrange in 2x2 grid
        cards_layout.addWidget(self.gpa_card, 0, 0)
        cards_layout.addWidget(self.credits_card, 0, 1)
        cards_layout.addWidget(self.standing_card, 1, 0)
        cards_layout.addWidget(self.completion_card, 1, 1)

        layout.addWidget(cards_group)

    def setup_connections(self):
        """Setup signal connections"""
        self.quick_actions.course_search_requested.connect(self.course_search_requested.emit)
        self.quick_actions.course_add_requested.connect(self.on_add_course_requested)

    def load_data(self):
        """Load and display academic data"""
        try:
            # Get transcript data
            courses = self.database.get_transcript_courses()

            # Calculate metrics
            total_credits = 0
            total_points = 0
            grade_credits = 0
            upper_credits = 0
            advanced_credits = 0

            grade_points = {
                'A+': 4.0, 'A': 4.0, 'A-': 3.7,
                'B+': 3.3, 'B': 3.0, 'B-': 2.7,
                'C+': 2.3, 'C': 2.0, 'C-': 1.7,
                'D+': 1.3, 'D': 1.0, 'D-': 0.7,
                'F': 0.0, 'FZ': 0.0
            }

            for course in courses:
                if len(course) > 2 and course[2]:  # Has credits (index 2)
                    credits = float(course[2])
                    total_credits += credits

                    # GPA calculation (grade is at index 3)
                    if len(course) > 3 and course[3] and course[3] in grade_points:
                        total_points += grade_points[course[3]] * credits
                        grade_credits += credits

                    # Level analysis
                    if len(course) > 0:  # Has course code
                        course_code = course[0]
                        # Extract course level (e.g., CSC108 -> 1, CSC200 -> 2)
                        level_match = None
                        for char in course_code:
                            if char.isdigit():
                                level_match = int(char)
                                break

                        if level_match and level_match >= 2:
                            upper_credits += credits
                        if level_match and level_match >= 3:
                            advanced_credits += credits

            # Calculate GPA
            gpa = total_points / grade_credits if grade_credits > 0 else 0.0

            # Determine academic standing
            standing = "Good Standing"
            if gpa < 1.85:
                standing = "At Risk"
            elif gpa >= 3.5:
                standing = "Dean's List"

            # Calculate completion percentage
            completion = min(100, (total_credits / 20.0) * 100)

            # Update status cards
            self.gpa_card.update_value(f"{gpa:.2f}", "Cumulative GPA")
            self.credits_card.update_value(f"{total_credits:.1f}", f"of 20.0 required")
            self.standing_card.update_value(standing, "Academic Status")
            self.completion_card.update_value(f"{completion:.0f}%", "Degree Complete")

            # Update progress bars
            progress_data = {
                'total_credits': total_credits,
                'upper_credits': upper_credits,
                'advanced_credits': advanced_credits,
                'breadth_credits': min(4.0, total_credits * 0.2)  # Estimate
            }
            self.progress_section.update_progress(progress_data)

            # Add activity
            self.activity_timeline.add_activity(
                "Data updated",
                f"Loaded {len(courses)} courses, {total_credits:.1f} credits"
            )

        except Exception as e:
            print(f"Error loading academic data: {e}")
            # Set default values
            self.gpa_card.update_value("N/A", "No data available")
            self.credits_card.update_value("0.0", "of 20.0 required")
            self.standing_card.update_value("Unknown", "Check transcript")
            self.completion_card.update_value("0%", "No progress")

    def on_add_course_requested(self):
        """Handle add course request"""
        # Switch to course management tab
        self.tab_switch_requested.emit(1)  # Course Management is tab 1

    def refresh_data(self):
        """Refresh all dashboard data"""
        self.load_data()
        self.activity_timeline.add_activity("Dashboard refreshed", "Data updated successfully")

    def focus_search(self):
        """Focus the search input for keyboard shortcut"""
        self.course_input.setFocus()
        self.course_input.selectAll()