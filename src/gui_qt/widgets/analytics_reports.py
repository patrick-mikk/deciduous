"""
Analytics & Reports Widget for PyQt6 UofT Course Dashboard
Data visualization, trends analysis, and export functionality
"""

from typing import Dict, List, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QTableWidget, QTableWidgetItem, QPushButton, QComboBox,
    QTextEdit, QSplitter, QFormLayout, QSpinBox, QCheckBox,
    QFileDialog, QMessageBox, QTabWidget, QScrollArea,
    QGridLayout, QProgressBar, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QFont, QPalette
import json
import csv
from datetime import datetime


class KPICard(QGroupBox):
    """Key Performance Indicator card widget"""

    def __init__(self, title: str, value: str, change: str = "", parent=None):
        super().__init__(title, parent)
        self.setup_ui(value, change)

    def setup_ui(self, value: str, change: str):
        """Setup KPI card layout"""
        layout = QVBoxLayout(self)

        # Main value
        value_label = QLabel(value)
        value_font = QFont()
        value_font.setPointSize(20)
        value_font.setBold(True)
        value_label.setFont(value_font)
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(value_label)

        # Change indicator
        if change:
            change_label = QLabel(change)
            change_font = QFont()
            change_font.setPointSize(9)
            change_label.setFont(change_font)
            change_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

            # Color code the change
            if change.startswith('+'):
                change_label.setStyleSheet("color: green;")
            elif change.startswith('-'):
                change_label.setStyleSheet("color: red;")

            layout.addWidget(change_label)

        self.setMaximumHeight(100)
        self.setMinimumHeight(80)

    def update_value(self, value: str, change: str = ""):
        """Update the KPI values"""
        layout = self.layout()
        if layout.itemAt(0):
            layout.itemAt(0).widget().setText(value)
        if layout.itemAt(1) and change:
            layout.itemAt(1).widget().setText(change)


class GradeTrendChart(QGroupBox):
    """Simulated chart widget for grade trends"""

    def __init__(self, parent=None):
        super().__init__("Grade Trends", parent)
        self.setup_ui()

    def setup_ui(self):
        """Setup chart placeholder"""
        layout = QVBoxLayout(self)

        # Chart placeholder (would use Qt Charts or matplotlib in real implementation)
        chart_placeholder = QLabel("Grade Trend Chart\n(Chart visualization would appear here)")
        chart_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        chart_placeholder.setMinimumHeight(200)
        chart_placeholder.setStyleSheet("""
            QLabel {
                border: 2px dashed #cccccc;
                border-radius: 4px;
                background-color: #f9f9f9;
            }
        """)
        layout.addWidget(chart_placeholder)

        # Chart controls
        controls_layout = QHBoxLayout()
        controls_layout.addWidget(QLabel("Time Period:"))

        period_combo = QComboBox()
        period_combo.addItems(["Last Year", "Last 2 Years", "All Time"])
        controls_layout.addWidget(period_combo)

        controls_layout.addStretch()
        layout.addLayout(controls_layout)


class CreditDistributionChart(QGroupBox):
    """Credit distribution visualization"""

    def __init__(self, parent=None):
        super().__init__("Credit Distribution", parent)
        self.setup_ui()

    def setup_ui(self):
        """Setup distribution chart"""
        layout = QVBoxLayout(self)

        # Progress bars for different categories
        categories = [
            ("100-level courses", 0),
            ("200-level courses", 0),
            ("300-level courses", 0),
            ("400-level courses", 0),
            ("Breadth requirements", 0)
        ]

        self.progress_bars = {}
        for category, value in categories:
            cat_layout = QHBoxLayout()

            label = QLabel(category)
            label.setMinimumWidth(150)
            cat_layout.addWidget(label)

            progress = QProgressBar()
            progress.setMinimum(0)
            progress.setMaximum(100)
            progress.setValue(value)
            progress.setFormat("%v credits")
            cat_layout.addWidget(progress)

            layout.addLayout(cat_layout)
            self.progress_bars[category] = progress

    def update_distribution(self, data: Dict[str, float]):
        """Update the credit distribution"""
        for category, credits in data.items():
            if category in self.progress_bars:
                self.progress_bars[category].setValue(int(credits * 10))


class CoursePerformanceTable(QGroupBox):
    """Table showing course performance metrics"""

    def __init__(self, parent=None):
        super().__init__("Course Performance Analysis", parent)
        self.setup_ui()

    def setup_ui(self):
        """Setup performance table"""
        layout = QVBoxLayout(self)

        # Filters
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Department:"))

        self.dept_filter = QComboBox()
        self.dept_filter.addItems(["All Departments", "CSC", "MAT", "STA", "PHY"])
        filter_layout.addWidget(self.dept_filter)

        filter_layout.addWidget(QLabel("Level:"))

        self.level_filter = QComboBox()
        self.level_filter.addItems(["All Levels", "100", "200", "300", "400"])
        filter_layout.addWidget(self.level_filter)

        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # Performance table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Course", "Grade", "Credits", "GPA Points", "Difficulty", "Satisfaction"
        ])

        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

    def update_performance_data(self, courses: List[tuple]):
        """Update the performance table with course data"""
        self.table.setRowCount(len(courses))

        grade_points = {
            'A+': 4.0, 'A': 4.0, 'A-': 3.7,
            'B+': 3.3, 'B': 3.0, 'B-': 2.7,
            'C+': 2.3, 'C': 2.0, 'C-': 1.7,
            'D+': 1.3, 'D': 1.0, 'D-': 0.7,
            'F': 0.0, 'FZ': 0.0
        }

        for row, course in enumerate(courses):
            if len(course) < 5:
                continue

            course_code = course[1] if len(course) > 1 else ""
            grade = course[4] if len(course) > 4 else ""
            credits = str(course[3]) if len(course) > 3 else ""

            gpa_points = grade_points.get(grade, 0.0)

            # Simulate difficulty and satisfaction (would come from real data)
            difficulty = "Medium"
            satisfaction = "Good"

            items = [course_code, grade, credits, f"{gpa_points:.1f}", difficulty, satisfaction]
            for col, item_text in enumerate(items):
                item = QTableWidgetItem(str(item_text))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, col, item)


class ExportPanel(QGroupBox):
    """Export functionality panel"""

    export_requested = pyqtSignal(str, dict)  # format, options

    def __init__(self, parent=None):
        super().__init__("Export & Reports", parent)
        self.setup_ui()

    def setup_ui(self):
        """Setup export controls"""
        layout = QVBoxLayout(self)

        # Export format selection
        format_layout = QFormLayout()

        self.format_combo = QComboBox()
        self.format_combo.addItems(["PDF Report", "Excel Spreadsheet", "CSV Data", "JSON Data"])
        format_layout.addRow("Export Format:", self.format_combo)

        layout.addLayout(format_layout)

        # Export options
        options_group = QGroupBox("Export Options")
        options_layout = QVBoxLayout(options_group)

        self.include_transcript = QCheckBox("Include Transcript Data")
        self.include_transcript.setChecked(True)
        options_layout.addWidget(self.include_transcript)

        self.include_analytics = QCheckBox("Include Analytics")
        self.include_analytics.setChecked(True)
        options_layout.addWidget(self.include_analytics)

        self.include_requirements = QCheckBox("Include Requirements Progress")
        self.include_requirements.setChecked(True)
        options_layout.addWidget(self.include_requirements)

        layout.addWidget(options_group)

        # Export buttons
        button_layout = QVBoxLayout()

        export_btn = QPushButton("Export Data")
        export_btn.clicked.connect(self.on_export_clicked)
        button_layout.addWidget(export_btn)

        preview_btn = QPushButton("Preview Report")
        preview_btn.clicked.connect(self.on_preview_clicked)
        button_layout.addWidget(preview_btn)

        layout.addLayout(button_layout)

        # Export status
        self.status_label = QLabel("Ready to export")
        layout.addWidget(self.status_label)

    def on_export_clicked(self):
        """Handle export button click"""
        export_format = self.format_combo.currentText()
        options = {
            'include_transcript': self.include_transcript.isChecked(),
            'include_analytics': self.include_analytics.isChecked(),
            'include_requirements': self.include_requirements.isChecked()
        }

        self.export_requested.emit(export_format, options)

    def on_preview_clicked(self):
        """Handle preview button click"""
        self.status_label.setText("Preview functionality coming soon...")


class AnalyticsReportsWidget(QWidget):
    """Main analytics and reports widget"""

    def __init__(self, database, parent=None):
        super().__init__(parent)
        self.database = database
        self.setup_ui()
        self.setup_connections()
        self.load_analytics_data()

    def setup_ui(self):
        """Setup the analytics interface"""
        layout = QVBoxLayout(self)

        # Create tabbed interface for different analytics views
        self.tab_widget = QTabWidget()

        # Overview tab
        self.create_overview_tab()

        # Performance tab
        self.create_performance_tab()

        # Export tab
        self.create_export_tab()

        layout.addWidget(self.tab_widget)

    def create_overview_tab(self):
        """Create the overview analytics tab"""
        overview_widget = QWidget()
        layout = QVBoxLayout(overview_widget)

        # KPI Cards section
        kpi_layout = QGridLayout()

        self.gpa_kpi = KPICard("Current GPA", "0.00", "")
        self.credits_kpi = KPICard("Credits Earned", "0.0", "")
        self.completion_kpi = KPICard("Degree Progress", "0%", "")
        self.standing_kpi = KPICard("Academic Standing", "Good", "")

        kpi_layout.addWidget(self.gpa_kpi, 0, 0)
        kpi_layout.addWidget(self.credits_kpi, 0, 1)
        kpi_layout.addWidget(self.completion_kpi, 0, 2)
        kpi_layout.addWidget(self.standing_kpi, 0, 3)

        layout.addLayout(kpi_layout)

        # Charts section
        charts_layout = QHBoxLayout()

        self.grade_trend_chart = GradeTrendChart()
        charts_layout.addWidget(self.grade_trend_chart)

        self.credit_distribution = CreditDistributionChart()
        charts_layout.addWidget(self.credit_distribution)

        layout.addLayout(charts_layout)

        self.tab_widget.addTab(overview_widget, "Overview")

    def create_performance_tab(self):
        """Create the performance analysis tab"""
        performance_widget = QWidget()
        layout = QVBoxLayout(performance_widget)

        # Performance metrics
        metrics_group = QGroupBox("Performance Metrics")
        metrics_layout = QFormLayout(metrics_group)

        self.avg_grade_label = QLabel("B+")
        metrics_layout.addRow("Average Grade:", self.avg_grade_label)

        self.best_subject_label = QLabel("Computer Science")
        metrics_layout.addRow("Best Subject:", self.best_subject_label)

        self.hardest_course_label = QLabel("MAT137Y1")
        metrics_layout.addRow("Most Challenging:", self.hardest_course_label)

        layout.addWidget(metrics_group)

        # Course performance table
        self.performance_table = CoursePerformanceTable()
        layout.addWidget(self.performance_table)

        self.tab_widget.addTab(performance_widget, "Performance")

    def create_export_tab(self):
        """Create the export functionality tab"""
        export_widget = QWidget()
        layout = QHBoxLayout(export_widget)

        # Export panel
        self.export_panel = ExportPanel()
        layout.addWidget(self.export_panel)

        # Export preview area
        preview_group = QGroupBox("Export Preview")
        preview_layout = QVBoxLayout(preview_group)

        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setPlainText("Export preview will appear here...")
        preview_layout.addWidget(self.preview_text)

        layout.addWidget(preview_group)

        self.tab_widget.addTab(export_widget, "Export")

    def setup_connections(self):
        """Setup signal connections"""
        self.export_panel.export_requested.connect(self.handle_export_request)

    def load_analytics_data(self):
        """Load and calculate analytics data"""
        try:
            # Get transcript data
            courses = self.database.get_transcript_courses()

            if not courses:
                return

            # Calculate metrics
            total_credits = 0
            total_points = 0
            grade_credits = 0
            level_distribution = {'100': 0, '200': 0, '300': 0, '400': 0, 'other': 0}

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

                    # GPA calculation
                    if len(course) > 4 and course[4] in grade_points:
                        total_points += grade_points[course[4]] * credits
                        grade_credits += credits

                    # Level distribution
                    if len(course) > 1:
                        course_code = course[1]
                        for char in course_code:
                            if char.isdigit():
                                level = char + '00'
                                if level in level_distribution:
                                    level_distribution[level] += credits
                                else:
                                    level_distribution['other'] += credits
                                break

            # Update KPIs
            gpa = total_points / grade_credits if grade_credits > 0 else 0.0
            completion = min(100, (total_credits / 20.0) * 100)

            standing = "Good Standing"
            if gpa < 1.85:
                standing = "At Risk"
            elif gpa >= 3.5:
                standing = "Dean's List"

            self.gpa_kpi.update_value(f"{gpa:.2f}")
            self.credits_kpi.update_value(f"{total_credits:.1f}")
            self.completion_kpi.update_value(f"{completion:.0f}%")
            self.standing_kpi.update_value(standing)

            # Update credit distribution
            distribution_data = {
                "100-level courses": level_distribution['100'],
                "200-level courses": level_distribution['200'],
                "300-level courses": level_distribution['300'],
                "400-level courses": level_distribution['400']
            }
            self.credit_distribution.update_distribution(distribution_data)

            # Update performance table
            self.performance_table.update_performance_data(courses)

            # Update performance metrics
            if courses:
                grades = [course[4] for course in courses if len(course) > 4 and course[4]]
                if grades:
                    # Calculate average grade (simplified)
                    grade_values = [grade_points.get(g, 0) for g in grades if g in grade_points]
                    if grade_values:
                        avg_grade_value = sum(grade_values) / len(grade_values)
                        avg_grade = self.value_to_grade(avg_grade_value)
                        self.avg_grade_label.setText(avg_grade)

        except Exception as e:
            print(f"Error loading analytics data: {e}")

    def value_to_grade(self, value: float) -> str:
        """Convert GPA value back to letter grade"""
        if value >= 3.85: return "A"
        elif value >= 3.7: return "A-"
        elif value >= 3.3: return "B+"
        elif value >= 3.0: return "B"
        elif value >= 2.7: return "B-"
        elif value >= 2.3: return "C+"
        elif value >= 2.0: return "C"
        elif value >= 1.7: return "C-"
        elif value >= 1.3: return "D+"
        elif value >= 1.0: return "D"
        else: return "F"

    def handle_export_request(self, export_format: str, options: Dict):
        """Handle export data request"""
        try:
            # Get file path
            format_extensions = {
                "PDF Report": "pdf",
                "Excel Spreadsheet": "xlsx",
                "CSV Data": "csv",
                "JSON Data": "json"
            }

            extension = format_extensions.get(export_format, "txt")
            file_path, _ = QFileDialog.getSaveFileName(
                self, f"Export {export_format}",
                f"uoft_dashboard_export.{extension}",
                f"{export_format} (*.{extension})"
            )

            if not file_path:
                return

            # Export based on format
            if export_format == "CSV Data":
                self.export_csv(file_path, options)
            elif export_format == "JSON Data":
                self.export_json(file_path, options)
            else:
                # For PDF and Excel, show placeholder message
                QMessageBox.information(
                    self, "Export",
                    f"{export_format} export functionality will be implemented in a future update.\n"
                    f"For now, use CSV or JSON export options."
                )
                return

            QMessageBox.information(self, "Export Complete", f"Data exported to:\n{file_path}")
            self.export_panel.status_label.setText("Export completed successfully")

        except Exception as e:
            QMessageBox.warning(self, "Export Error", f"Export failed: {str(e)}")
            self.export_panel.status_label.setText("Export failed")

    def export_csv(self, file_path: str, options: Dict):
        """Export data to CSV format"""
        if options.get('include_transcript', False):
            courses = self.database.get_transcript_courses()

            with open(file_path, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)

                # Write header
                writer.writerow(['Course Code', 'Title', 'Credits', 'Grade', 'Mark', 'Session', 'Year', 'Status'])

                # Write course data
                for course in courses:
                    row = []
                    for i in range(8):  # 8 columns
                        if i < len(course):
                            row.append(course[i] if i > 0 else str(course[i]))  # Skip ID for first column
                        else:
                            row.append('')
                    if len(row) > 1:  # Skip the ID column
                        writer.writerow(row[1:])

    def export_json(self, file_path: str, options: Dict):
        """Export data to JSON format"""
        export_data = {
            'export_date': datetime.now().isoformat(),
            'export_options': options
        }

        if options.get('include_transcript', False):
            courses = self.database.get_transcript_courses()
            transcript_data = []

            for course in courses:
                if len(course) >= 8:
                    course_dict = {
                        'course_code': course[1],
                        'title': course[2],
                        'credits': course[3],
                        'grade': course[4],
                        'mark': course[5],
                        'session': course[6],
                        'year': course[7],
                        'status': course[8] if len(course) > 8 else ''
                    }
                    transcript_data.append(course_dict)

            export_data['transcript'] = transcript_data

        # Add analytics data if requested
        if options.get('include_analytics', False):
            # Add basic analytics (could be expanded)
            export_data['analytics'] = {
                'total_courses': len(courses) if 'courses' in locals() else 0,
                'export_note': 'Full analytics export coming in future update'
            }

        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(export_data, file, indent=2, ensure_ascii=False)

    def refresh_data(self):
        """Refresh all analytics data"""
        self.load_analytics_data()