import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import csv
import json
from datetime import datetime, timedelta
from collections import defaultdict
import os
import sys
import threading
import webbrowser
import sqlite3
import re
from pathlib import Path
import shutil
from typing import Dict, List, Optional, Tuple
try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("Matplotlib not available - charts will be disabled")

try:
    import openpyxl
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

class UofTTranscriptAnalyzer:
    def __init__(self, root):
        self.root = root
        self.root.title("UofT Academic Transcript Analyzer v3.0 - Enhanced Edition")
        self.root.geometry("1400x900")
        self.root.configure(bg='#f0f0f0')

        # Enhanced configuration
        self.app_data_dir = Path.home() / "UofT_Transcript_Analyzer"
        self.app_data_dir.mkdir(exist_ok=True)
        self.settings_file = self.app_data_dir / "settings.json"
        self.auto_save_file = self.app_data_dir / "auto_save.json"
        self.backup_dir = self.app_data_dir / "backups"
        self.backup_dir.mkdir(exist_ok=True)

        # Load settings
        self.settings = self.load_settings()

        # Auto-save timer
        self.auto_save_timer = None
        self.data_changed = False

        # Search/filter state
        self.current_filter = {}

        # Theme settings
        self.current_theme = self.settings.get('theme', 'light')

        # Course database for prerequisites
        self.course_db_file = self.app_data_dir / "course_data.db"
        self.init_course_database()
        
        # UofT Grade Scale
        self.GRADE_POINTS = {
            'A+': 4.0, 'A': 4.0, 'A-': 3.7,
            'B+': 3.3, 'B': 3.0, 'B-': 2.7,
            'C+': 2.3, 'C': 2.0, 'C-': 1.7,
            'D+': 1.3, 'D': 1.0, 'D-': 0.7,
            'F': 0.0, 'FZ': 0.0
        }
        
        # Special Notations (excluded from GPA calculation)
        self.SPECIAL_NOTATIONS = {
            'CR': 'Credit/No Credit - Pass',
            'NCR': 'Credit/No Credit - Fail', 
            'NC%': 'No Credit (counted as 0.0 in GPA)',
            'IPR': 'In Progress',
            'LWD': 'Late Withdrawal',
            'WDR': 'Withdrawn',
            'AEG': 'Aegrotat Standing',
            'SDF': 'Standing Deferred',
            'DNW': 'Did Not Write',
            'EXT': 'Extra Course',
            'ADD': 'Additional Course',
            'GWR': 'Grade Withheld',
            'INC': 'Incomplete',
            'NGA': 'No Grade Available',
            'XMP': 'Exemption Granted'
        }
        
        # All valid grade/notation options
        self.ALL_GRADES = list(self.GRADE_POINTS.keys()) + list(self.SPECIAL_NOTATIONS.keys())
        
        # Data storage
        self.transcript_data = []
        self.simulation_courses = []
        self.degree_requirements = {}
        self.course_prerequisites = {}
        self.bookmarked_courses = set()

        # Enhanced UofT data
        self.uoft_faculties = {
            'ARTSC': 'Faculty of Arts & Science',
            'ENGR': 'Faculty of Applied Science & Engineering',
            'MUSIC': 'Faculty of Music',
            'KINE': 'Faculty of Kinesiology & Physical Education',
            'UTM': 'University of Toronto Mississauga',
            'UTSC': 'University of Toronto Scarborough'
        }

        self.common_majors = {
            'Computer Science', 'Economics', 'Mathematics', 'Physics',
            'Chemistry', 'Biology', 'Psychology', 'Political Science',
            'History', 'Philosophy', 'English', 'Engineering',
            'Business', 'International Relations', 'Statistics'
        }
        
        self.setup_gui()
        self.load_sample_data()

        # Set up auto-save
        self.schedule_auto_save()

        # Set window close protocol
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def setup_gui(self):
        # Create main notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create tabs
        self.setup_overview_tab()
        self.setup_transcript_tab()
        self.setup_simulation_tab()
        self.setup_analytics_tab()
        self.setup_prerequisites_tab()
        self.setup_degree_progress_tab()
        self.setup_reports_tab()
        self.setup_data_tab()
        self.setup_settings_tab()
        
    def setup_overview_tab(self):
        self.overview_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.overview_frame, text='Overview')
        
        # Stats Frame
        stats_frame = ttk.LabelFrame(self.overview_frame, text="Academic Statistics", padding=15)
        stats_frame.pack(fill='x', padx=10, pady=10)
        
        # Create stats grid
        stats_grid = ttk.Frame(stats_frame)
        stats_grid.pack(fill='x')
        
        # GPA Display
        ttk.Label(stats_grid, text="Cumulative GPA:", font=('Arial', 12, 'bold')).grid(row=0, column=0, sticky='w', padx=5)
        self.gpa_label = ttk.Label(stats_grid, text="0.00", font=('Arial', 14, 'bold'), foreground='blue')
        self.gpa_label.grid(row=0, column=1, sticky='w', padx=5)
        
        # Credits Display
        ttk.Label(stats_grid, text="Total Credits:", font=('Arial', 12, 'bold')).grid(row=0, column=2, sticky='w', padx=20)
        self.credits_label = ttk.Label(stats_grid, text="0.0", font=('Arial', 14, 'bold'), foreground='green')
        self.credits_label.grid(row=0, column=3, sticky='w', padx=5)
        
        # Academic Standing
        ttk.Label(stats_grid, text="Academic Standing:", font=('Arial', 12, 'bold')).grid(row=1, column=0, sticky='w', padx=5, pady=5)
        self.standing_label = ttk.Label(stats_grid, text="Good Standing", font=('Arial', 12, 'bold'), foreground='orange')
        self.standing_label.grid(row=1, column=1, columnspan=2, sticky='w', padx=5, pady=5)
        
        # Courses Completed
        ttk.Label(stats_grid, text="Courses Completed:", font=('Arial', 12, 'bold')).grid(row=1, column=2, sticky='w', padx=20, pady=5)
        self.courses_label = ttk.Label(stats_grid, text="0", font=('Arial', 14, 'bold'), foreground='purple')
        self.courses_label.grid(row=1, column=3, sticky='w', padx=5, pady=5)
        
        # Sessional GPAs Frame
        sessional_frame = ttk.LabelFrame(self.overview_frame, text="Sessional GPAs", padding=15)
        sessional_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Sessional GPA Tree
        columns = ('Term', 'GPA', 'Credits', 'Courses', 'Standing')
        self.sessional_tree = ttk.Treeview(sessional_frame, columns=columns, show='headings', height=10)
        
        for col in columns:
            self.sessional_tree.heading(col, text=col)
            self.sessional_tree.column(col, width=120, anchor='center')
        
        scrollbar_sessional = ttk.Scrollbar(sessional_frame, orient='vertical', command=self.sessional_tree.yview)
        self.sessional_tree.configure(yscrollcommand=scrollbar_sessional.set)
        
        self.sessional_tree.pack(side='left', fill='both', expand=True)
        scrollbar_sessional.pack(side='right', fill='y')
        
    def setup_transcript_tab(self):
        self.transcript_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.transcript_frame, text='Transcript')
        
        # Controls Frame
        controls_frame = ttk.Frame(self.transcript_frame)
        controls_frame.pack(fill='x', padx=10, pady=5)

        # Button row 1
        button_row1 = ttk.Frame(controls_frame)
        button_row1.pack(fill='x', pady=2)

        ttk.Button(button_row1, text="Add Course", command=self.add_course_dialog).pack(side='left', padx=5)
        ttk.Button(button_row1, text="Edit Course", command=self.edit_course).pack(side='left', padx=5)
        ttk.Button(button_row1, text="Delete Course", command=self.delete_course).pack(side='left', padx=5)
        ttk.Button(button_row1, text="Duplicate Course", command=self.duplicate_course).pack(side='left', padx=5)

        # Button row 2
        button_row2 = ttk.Frame(controls_frame)
        button_row2.pack(fill='x', pady=2)

        ttk.Button(button_row2, text="Import CSV", command=self.import_csv).pack(side='left', padx=5)
        ttk.Button(button_row2, text="Export CSV", command=self.export_csv).pack(side='left', padx=5)
        ttk.Button(button_row2, text="Export Excel", command=self.export_excel).pack(side='left', padx=5)
        ttk.Button(button_row2, text="Export PDF", command=self.export_pdf).pack(side='left', padx=5)

        # Search and Filter Frame
        search_frame = ttk.LabelFrame(self.transcript_frame, text="Search & Filter", padding=5)
        search_frame.pack(fill='x', padx=10, pady=5)

        # Search row
        search_row = ttk.Frame(search_frame)
        search_row.pack(fill='x', pady=2)

        ttk.Label(search_row, text="Search:").pack(side='left', padx=5)
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.on_search_change)
        search_entry = ttk.Entry(search_row, textvariable=self.search_var, width=30)
        search_entry.pack(side='left', padx=5)

        ttk.Button(search_row, text="Clear", command=self.clear_search).pack(side='left', padx=5)

        # Filter row
        filter_row = ttk.Frame(search_frame)
        filter_row.pack(fill='x', pady=2)

        ttk.Label(filter_row, text="Term:").pack(side='left', padx=5)
        self.filter_term_var = tk.StringVar(value="All")
        term_filter = ttk.Combobox(filter_row, textvariable=self.filter_term_var,
                                  values=["All", "Fall", "Winter", "Summer"], width=10, state='readonly')
        term_filter.pack(side='left', padx=5)
        term_filter.bind('<<ComboboxSelected>>', self.on_filter_change)

        ttk.Label(filter_row, text="Year:").pack(side='left', padx=5)
        self.filter_year_var = tk.StringVar(value="All")
        self.year_filter = ttk.Combobox(filter_row, textvariable=self.filter_year_var,
                                       width=10, state='readonly')
        self.year_filter.pack(side='left', padx=5)
        self.year_filter.bind('<<ComboboxSelected>>', self.on_filter_change)

        ttk.Label(filter_row, text="Department:").pack(side='left', padx=5)
        self.filter_dept_var = tk.StringVar(value="All")
        self.dept_filter = ttk.Combobox(filter_row, textvariable=self.filter_dept_var,
                                       width=10, state='readonly')
        self.dept_filter.pack(side='left', padx=5)
        self.dept_filter.bind('<<ComboboxSelected>>', self.on_filter_change)

        ttk.Label(filter_row, text="Grade:").pack(side='left', padx=5)
        self.filter_grade_var = tk.StringVar(value="All")
        grade_filter = ttk.Combobox(filter_row, textvariable=self.filter_grade_var,
                                   values=["All", "A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "D-", "F"],
                                   width=8, state='readonly')
        grade_filter.pack(side='left', padx=5)
        grade_filter.bind('<<ComboboxSelected>>', self.on_filter_change)
        
        # Transcript Tree
        columns = ('Term', 'Year', 'Course', 'Title', 'Weight', 'Mark', 'Grade', 'GPA', 'Status')
        self.transcript_tree = ttk.Treeview(self.transcript_frame, columns=columns, show='headings')
        
        for col in columns:
            self.transcript_tree.heading(col, text=col)
            if col == 'Title':
                self.transcript_tree.column(col, width=200)
            elif col in ['Term', 'Year', 'Weight', 'Mark', 'Grade', 'GPA']:
                self.transcript_tree.column(col, width=80, anchor='center')
            else:
                self.transcript_tree.column(col, width=100, anchor='center')
        
        # Scrollbars
        scrollbar_y = ttk.Scrollbar(self.transcript_frame, orient='vertical', command=self.transcript_tree.yview)
        scrollbar_x = ttk.Scrollbar(self.transcript_frame, orient='horizontal', command=self.transcript_tree.xview)
        self.transcript_tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        self.transcript_tree.pack(side='left', fill='both', expand=True, padx=(10, 0), pady=10)
        scrollbar_y.pack(side='right', fill='y', pady=10)
        scrollbar_x.pack(side='bottom', fill='x', padx=10)
        
    def setup_simulation_tab(self):
        self.simulation_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.simulation_frame, text='GPA Simulator')
        
        # Split into two sections
        left_frame = ttk.LabelFrame(self.simulation_frame, text="Future Courses", padding=15)
        left_frame.pack(side='left', fill='both', expand=True, padx=(10, 5), pady=10)
        
        right_frame = ttk.LabelFrame(self.simulation_frame, text="Projection Results", padding=15)
        right_frame.pack(side='right', fill='y', padx=(5, 10), pady=10)
        
        # Future courses controls
        controls_sim = ttk.Frame(left_frame)
        controls_sim.pack(fill='x', pady=(0, 10))
        
        ttk.Button(controls_sim, text="Add Course", command=self.add_simulation_course).pack(side='left', padx=5)
        ttk.Button(controls_sim, text="Remove Selected", command=self.remove_simulation_course).pack(side='left', padx=5)
        ttk.Button(controls_sim, text="Clear All", command=self.clear_simulation).pack(side='left', padx=5)
        
        # Simulation tree
        sim_columns = ('Course', 'Title', 'Weight', 'Expected Grade', 'Notation', 'GPA Impact')
        self.simulation_tree = ttk.Treeview(left_frame, columns=sim_columns, show='headings', height=15)
        
        for col in sim_columns:
            self.simulation_tree.heading(col, text=col)
            if col == 'Title':
                self.simulation_tree.column(col, width=150)
            else:
                self.simulation_tree.column(col, width=100, anchor='center')
        
        sim_scrollbar = ttk.Scrollbar(left_frame, orient='vertical', command=self.simulation_tree.yview)
        self.simulation_tree.configure(yscrollcommand=sim_scrollbar.set)
        
        self.simulation_tree.pack(side='left', fill='both', expand=True)
        sim_scrollbar.pack(side='right', fill='y')
        
        # Results display
        results_grid = ttk.Frame(right_frame)
        results_grid.pack(fill='both', expand=True)
        
        # Current stats
        ttk.Label(results_grid, text="Current GPA:", font=('Arial', 12, 'bold')).grid(row=0, column=0, sticky='w', pady=5)
        self.current_gpa_sim = ttk.Label(results_grid, text="0.00", font=('Arial', 12), foreground='blue')
        self.current_gpa_sim.grid(row=0, column=1, sticky='w', padx=10, pady=5)
        
        ttk.Label(results_grid, text="Current Credits:", font=('Arial', 12, 'bold')).grid(row=1, column=0, sticky='w', pady=5)
        self.current_credits_sim = ttk.Label(results_grid, text="0.0", font=('Arial', 12), foreground='blue')
        self.current_credits_sim.grid(row=1, column=1, sticky='w', padx=10, pady=5)
        
        # Separator
        ttk.Separator(results_grid, orient='horizontal').grid(row=2, column=0, columnspan=2, sticky='ew', pady=10)
        
        # Projected stats
        ttk.Label(results_grid, text="Projected GPA:", font=('Arial', 12, 'bold')).grid(row=3, column=0, sticky='w', pady=5)
        self.projected_gpa = ttk.Label(results_grid, text="0.00", font=('Arial', 14, 'bold'), foreground='red')
        self.projected_gpa.grid(row=3, column=1, sticky='w', padx=10, pady=5)
        
        ttk.Label(results_grid, text="Total Credits:", font=('Arial', 12, 'bold')).grid(row=4, column=0, sticky='w', pady=5)
        self.projected_credits = ttk.Label(results_grid, text="0.0", font=('Arial', 12), foreground='green')
        self.projected_credits.grid(row=4, column=1, sticky='w', padx=10, pady=5)
        
        ttk.Label(results_grid, text="GPA Change:", font=('Arial', 12, 'bold')).grid(row=5, column=0, sticky='w', pady=5)
        self.gpa_change = ttk.Label(results_grid, text="+0.00", font=('Arial', 12, 'bold'))
        self.gpa_change.grid(row=5, column=1, sticky='w', padx=10, pady=5)
        
        ttk.Label(results_grid, text="Added Credits:", font=('Arial', 12, 'bold')).grid(row=6, column=0, sticky='w', pady=5)
        self.added_credits = ttk.Label(results_grid, text="0.0", font=('Arial', 12))
        self.added_credits.grid(row=6, column=1, sticky='w', padx=10, pady=5)
        
        # Goal calculator
        ttk.Separator(results_grid, orient='horizontal').grid(row=7, column=0, columnspan=2, sticky='ew', pady=10)
        
        ttk.Label(results_grid, text="Goal Calculator:", font=('Arial', 12, 'bold')).grid(row=8, column=0, columnspan=2, sticky='w', pady=5)
        
        goal_frame = ttk.Frame(results_grid)
        goal_frame.grid(row=9, column=0, columnspan=2, sticky='ew', pady=5)
        
        ttk.Label(goal_frame, text="Target GPA:").pack(side='left')
        self.target_gpa_var = tk.StringVar(value="3.5")
        target_entry = ttk.Entry(goal_frame, textvariable=self.target_gpa_var, width=6)
        target_entry.pack(side='left', padx=5)
        ttk.Button(goal_frame, text="Calculate", command=self.calculate_goal).pack(side='left', padx=5)
        
        self.goal_result = ttk.Label(results_grid, text="", font=('Arial', 10), wraplength=200)
        self.goal_result.grid(row=10, column=0, columnspan=2, sticky='w', pady=5)
        
    def setup_analytics_tab(self):
        self.analytics_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.analytics_frame, text='Analytics')
        
        # Grade distribution frame
        grade_frame = ttk.LabelFrame(self.analytics_frame, text="Grade Distribution", padding=15)
        grade_frame.pack(fill='x', padx=10, pady=10)
        
        self.grade_dist_text = tk.Text(grade_frame, height=8, width=80)
        self.grade_dist_text.pack(fill='x')
        
        # Subject analysis frame
        subject_frame = ttk.LabelFrame(self.analytics_frame, text="Subject Performance", padding=15)
        subject_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.subject_text = tk.Text(subject_frame, height=15, width=80)
        scrollbar_subject = ttk.Scrollbar(subject_frame, orient='vertical', command=self.subject_text.yview)
        self.subject_text.configure(yscrollcommand=scrollbar_subject.set)
        
        self.subject_text.pack(side='left', fill='both', expand=True)
        scrollbar_subject.pack(side='right', fill='y')
        
    def setup_data_tab(self):
        self.data_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.data_frame, text='Data Management')
        
        # File operations
        file_frame = ttk.LabelFrame(self.data_frame, text="File Operations", padding=15)
        file_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Button(file_frame, text="Import CSV Transcript", command=self.import_csv).pack(side='left', padx=5)
        ttk.Button(file_frame, text="Export Current Data", command=self.export_csv).pack(side='left', padx=5)
        ttk.Button(file_frame, text="Save Session", command=self.save_session).pack(side='left', padx=5)
        ttk.Button(file_frame, text="Load Session", command=self.load_session).pack(side='left', padx=5)
        ttk.Button(file_frame, text="Clear All Data", command=self.clear_all_data).pack(side='left', padx=5)
        
        # Data info
        info_frame = ttk.LabelFrame(self.data_frame, text="Data Information", padding=15)
        info_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.data_info_text = tk.Text(info_frame, height=20, width=80)
        info_scrollbar = ttk.Scrollbar(info_frame, orient='vertical', command=self.data_info_text.yview)
        self.data_info_text.configure(yscrollcommand=info_scrollbar.set)
        
        self.data_info_text.pack(side='left', fill='both', expand=True)
        info_scrollbar.pack(side='right', fill='y')
        
        self.update_data_info()

    def setup_prerequisites_tab(self):
        \"\"\"Setup prerequisites and course planning tab\"\"\"
        self.prereqs_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.prereqs_frame, text='Prerequisites')

        # Course search and info frame
        search_info_frame = ttk.LabelFrame(self.prereqs_frame, text=\"Course Information Lookup\", padding=15)
        search_info_frame.pack(fill='x', padx=10, pady=10)

        search_row = ttk.Frame(search_info_frame)
        search_row.pack(fill='x')

        ttk.Label(search_row, text=\"Course Code:\").pack(side='left', padx=5)
        self.prereq_search_var = tk.StringVar()
        prereq_search = ttk.Entry(search_row, textvariable=self.prereq_search_var, width=15)
        prereq_search.pack(side='left', padx=5)
        ttk.Button(search_row, text=\"Look Up\", command=self.lookup_course_info).pack(side='left', padx=5)
        ttk.Button(search_row, text=\"Add to Database\", command=self.add_course_to_db).pack(side='left', padx=5)

        # Course info display
        self.course_info_text = tk.Text(search_info_frame, height=12, width=80)
        info_scrollbar = ttk.Scrollbar(search_info_frame, orient='vertical', command=self.course_info_text.yview)
        self.course_info_text.configure(yscrollcommand=info_scrollbar.set)

        self.course_info_text.pack(side='left', fill='both', expand=True, pady=10)
        info_scrollbar.pack(side='right', fill='y', pady=10)

        # Prerequisites validation frame
        validation_frame = ttk.LabelFrame(self.prereqs_frame, text=\"Prerequisites Validation\", padding=15)
        validation_frame.pack(fill='both', expand=True, padx=10, pady=10)

        ttk.Button(validation_frame, text=\"Check All Prerequisites\", command=self.validate_all_prerequisites).pack(pady=5)

        self.prereq_validation_text = tk.Text(validation_frame, height=15, width=80)
        validation_scrollbar = ttk.Scrollbar(validation_frame, orient='vertical', command=self.prereq_validation_text.yview)
        self.prereq_validation_text.configure(yscrollcommand=validation_scrollbar.set)

        self.prereq_validation_text.pack(side='left', fill='both', expand=True)
        validation_scrollbar.pack(side='right', fill='y')

    def setup_degree_progress_tab(self):
        \"\"\"Setup degree progress tracking tab\"\"\"
        self.degree_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.degree_frame, text='Degree Progress')

        # Program selection frame
        program_frame = ttk.LabelFrame(self.degree_frame, text=\"Program Selection\", padding=15)
        program_frame.pack(fill='x', padx=10, pady=10)

        program_row = ttk.Frame(program_frame)
        program_row.pack(fill='x')

        ttk.Label(program_row, text=\"Program:\").pack(side='left', padx=5)
        self.program_var = tk.StringVar(value=\"Computer Science Specialist\")
        program_combo = ttk.Combobox(program_row, textvariable=self.program_var,
                                    values=[\"Computer Science Specialist\", \"Economics Major\", \"Mathematics Specialist\",
                                           \"Physics Specialist\", \"Chemistry Specialist\", \"Custom Program\"],
                                    width=25)
        program_combo.pack(side='left', padx=5)

        ttk.Button(program_row, text=\"Load Requirements\", command=self.load_degree_requirements).pack(side='left', padx=5)
        ttk.Button(program_row, text=\"Edit Requirements\", command=self.edit_degree_requirements).pack(side='left', padx=5)

        # Progress overview frame
        progress_frame = ttk.LabelFrame(self.degree_frame, text=\"Progress Overview\", padding=15)
        progress_frame.pack(fill='both', expand=True, padx=10, pady=10)

        # Progress display
        self.progress_text = tk.Text(progress_frame, height=20, width=80)
        progress_scrollbar = ttk.Scrollbar(progress_frame, orient='vertical', command=self.progress_text.yview)
        self.progress_text.configure(yscrollcommand=progress_scrollbar.set)

        self.progress_text.pack(side='left', fill='both', expand=True)
        progress_scrollbar.pack(side='right', fill='y')

    def setup_reports_tab(self):
        \"\"\"Setup enhanced reports and visualizations tab\"\"\"
        self.reports_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.reports_frame, text='Reports & Charts')

        # Report controls
        controls_frame = ttk.LabelFrame(self.reports_frame, text=\"Report Options\", padding=15)
        controls_frame.pack(fill='x', padx=10, pady=10)

        controls_row = ttk.Frame(controls_frame)
        controls_row.pack(fill='x')

        ttk.Button(controls_row, text=\"Generate Transcript Report\", command=self.generate_transcript_report).pack(side='left', padx=5)
        ttk.Button(controls_row, text=\"GPA Trend Analysis\", command=self.generate_gpa_trend).pack(side='left', padx=5)
        ttk.Button(controls_row, text=\"Course Distribution\", command=self.generate_course_distribution).pack(side='left', padx=5)
        ttk.Button(controls_row, text=\"Export All Charts\", command=self.export_all_charts).pack(side='left', padx=5)

        # Chart display area
        if MATPLOTLIB_AVAILABLE:
            self.chart_frame = ttk.Frame(self.reports_frame)
            self.chart_frame.pack(fill='both', expand=True, padx=10, pady=10)
        else:
            # Fallback text display
            no_charts_frame = ttk.LabelFrame(self.reports_frame, text=\"Charts Unavailable\", padding=15)
            no_charts_frame.pack(fill='both', expand=True, padx=10, pady=10)

            info_label = ttk.Label(no_charts_frame,
                                 text=\"Install matplotlib for chart functionality:\\npip install matplotlib\",
                                 font=('Arial', 11))
            info_label.pack(pady=20)

            self.reports_text = tk.Text(no_charts_frame, height=15, width=80)
            reports_scrollbar = ttk.Scrollbar(no_charts_frame, orient='vertical', command=self.reports_text.yview)
            self.reports_text.configure(yscrollcommand=reports_scrollbar.set)

            self.reports_text.pack(side='left', fill='both', expand=True)
            reports_scrollbar.pack(side='right', fill='y')

    def setup_settings_tab(self):
        \"\"\"Setup application settings tab\"\"\"
        self.settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_frame, text='Settings')

        # Appearance settings
        appearance_frame = ttk.LabelFrame(self.settings_frame, text=\"Appearance\", padding=15)
        appearance_frame.pack(fill='x', padx=10, pady=10)

        # Theme selection
        theme_row = ttk.Frame(appearance_frame)
        theme_row.pack(fill='x', pady=5)

        ttk.Label(theme_row, text=\"Theme:\").pack(side='left', padx=5)
        self.theme_var = tk.StringVar(value=self.settings.get('theme', 'light'))
        theme_combo = ttk.Combobox(theme_row, textvariable=self.theme_var,
                                  values=[\"light\", \"dark\"], width=15, state='readonly')
        theme_combo.pack(side='left', padx=5)
        theme_combo.bind('<<ComboboxSelected>>', self.change_theme)

        # Font size
        font_row = ttk.Frame(appearance_frame)
        font_row.pack(fill='x', pady=5)

        ttk.Label(font_row, text=\"Font Size:\").pack(side='left', padx=5)
        self.font_size_var = tk.IntVar(value=self.settings.get('font_size', 10))
        font_spin = ttk.Spinbox(font_row, from_=8, to=16, textvariable=self.font_size_var, width=5)
        font_spin.pack(side='left', padx=5)
        ttk.Button(font_row, text=\"Apply\", command=self.apply_font_size).pack(side='left', padx=5)

        # Data settings
        data_frame = ttk.LabelFrame(self.settings_frame, text=\"Data Management\", padding=15)
        data_frame.pack(fill='x', padx=10, pady=10)

        # Auto-save interval
        autosave_row = ttk.Frame(data_frame)
        autosave_row.pack(fill='x', pady=5)

        ttk.Label(autosave_row, text=\"Auto-save interval (minutes):\").pack(side='left', padx=5)
        self.autosave_var = tk.IntVar(value=self.settings.get('auto_save_interval', 300) // 60)
        autosave_spin = ttk.Spinbox(autosave_row, from_=1, to=60, textvariable=self.autosave_var, width=5)
        autosave_spin.pack(side='left', padx=5)

        # Backup retention
        backup_row = ttk.Frame(data_frame)
        backup_row.pack(fill='x', pady=5)

        ttk.Label(backup_row, text=\"Backup retention (days):\").pack(side='left', padx=5)
        self.backup_retention_var = tk.IntVar(value=self.settings.get('backup_retention_days', 30))
        backup_spin = ttk.Spinbox(backup_row, from_=1, to=365, textvariable=self.backup_retention_var, width=5)
        backup_spin.pack(side='left', padx=5)

        # Buttons
        buttons_row = ttk.Frame(data_frame)
        buttons_row.pack(fill='x', pady=10)

        ttk.Button(buttons_row, text=\"Create Backup Now\", command=self.create_backup).pack(side='left', padx=5)
        ttk.Button(buttons_row, text=\"Open Data Folder\", command=self.open_data_folder).pack(side='left', padx=5)
        ttk.Button(buttons_row, text=\"Export Settings\", command=self.export_settings).pack(side='left', padx=5)
        ttk.Button(buttons_row, text=\"Import Settings\", command=self.import_settings).pack(side='left', padx=5)

        # Save settings button
        save_frame = ttk.Frame(self.settings_frame)
        save_frame.pack(fill='x', padx=10, pady=20)

        ttk.Button(save_frame, text=\"Save All Settings\", command=self.save_all_settings).pack(pady=10)

        # Help and about
        help_frame = ttk.LabelFrame(self.settings_frame, text=\"Help & About\", padding=15)
        help_frame.pack(fill='x', padx=10, pady=10)

        help_row = ttk.Frame(help_frame)
        help_row.pack(fill='x')

        ttk.Button(help_row, text=\"User Guide\", command=self.show_user_guide).pack(side='left', padx=5)
        ttk.Button(help_row, text=\"Keyboard Shortcuts\", command=self.show_shortcuts).pack(side='left', padx=5)
        ttk.Button(help_row, text=\"About\", command=self.show_about).pack(side='left', padx=5)
        ttk.Button(help_row, text=\"Check for Updates\", command=self.check_updates).pack(side='left', padx=5)

    def calculate_gpa(self, courses):
        """Calculate GPA for given courses, handling special notations"""
        valid_courses = []
        
        for course in courses:
            grade = course.get('grade', '')
            notation = course.get('notation', '')
            
            # Skip courses with special notations that don't count toward GPA
            if notation in ['CR', 'NCR', 'IPR', 'LWD', 'WDR', 'AEG', 'SDF', 'DNW', 'EXT', 'ADD', 'GWR', 'INC', 'NGA', 'XMP']:
                continue
                
            # Handle NC% which counts as 0.0 in GPA
            if notation == 'NC%':
                valid_courses.append({
                    'weight': course.get('weight', 0.5),
                    'grade_points': 0.0
                })
                continue
            
            # Regular grades
            if grade in self.GRADE_POINTS:
                valid_courses.append({
                    'weight': course.get('weight', 0.5),
                    'grade_points': self.GRADE_POINTS[grade]
                })
        
        if not valid_courses:
            return 0.0
        
        total_grade_points = sum(course['grade_points'] * course['weight'] for course in valid_courses)
        total_credits = sum(course['weight'] for course in valid_courses)
        
        return total_grade_points / total_credits if total_credits > 0 else 0.0
        
    def get_academic_standing(self, gpa):
        """Determine academic standing based on GPA"""
        if gpa >= 3.5:
            return "Dean's List"
        elif gpa >= 3.0:
            return "Good Standing"
        elif gpa >= 2.0:
            return "Good Standing"
        elif gpa >= 1.0:
            return "Academic Probation"
        else:
            return "Academic Suspension"
    
    def update_displays(self):
        """Update all display elements with current data"""
        # Calculate current statistics
        current_gpa = self.calculate_gpa(self.transcript_data)
        total_credits = sum(course.get('weight', 0.5) for course in self.transcript_data 
                          if course.get('notation', '') not in ['IPR', 'LWD', 'WDR'])
        total_courses = len(self.transcript_data)
        standing = self.get_academic_standing(current_gpa)
        
        # Update overview displays
        self.gpa_label.config(text=f"{current_gpa:.2f}")
        self.credits_label.config(text=f"{total_credits:.1f}")
        self.courses_label.config(text=str(total_courses))
        self.standing_label.config(text=standing)
        
        # Update sessional GPAs
        self.update_sessional_display()
        
        # Update transcript tree
        self.update_transcript_tree()
        
        # Update simulation displays
        self.update_simulation_display()
        
        # Update analytics
        self.update_analytics()
        
    def update_sessional_display(self):
        """Update the sessional GPA display"""
        # Clear existing items
        for item in self.sessional_tree.get_children():
            self.sessional_tree.delete(item)
        
        # Group courses by term and year
        sessions = defaultdict(list)
        for course in self.transcript_data:
            term = course.get('term', '')
            year = course.get('year', '')
            if term and year:
                sessions[f"{term} {year}"].append(course)
        
        # Sort sessions chronologically
        session_order = {'Fall': 1, 'Winter': 2, 'Summer': 3}
        sorted_sessions = sorted(sessions.items(), 
                               key=lambda x: (int(x[0].split()[1]), session_order.get(x[0].split()[0], 0)))
        
        for session_name, courses in sorted_sessions:
            gpa = self.calculate_gpa(courses)
            credits = sum(course.get('weight', 0.5) for course in courses 
                         if course.get('notation', '') not in ['IPR', 'LWD', 'WDR'])
            num_courses = len(courses)
            standing = self.get_academic_standing(gpa)
            
            self.sessional_tree.insert('', 'end', values=(
                session_name, f"{gpa:.2f}", f"{credits:.1f}", 
                str(num_courses), standing
            ))
    
    def update_transcript_tree(self):
        """Update the transcript tree display"""
        # Clear existing items
        for item in self.transcript_tree.get_children():
            self.transcript_tree.delete(item)
        
        # Sort courses by year and term
        session_order = {'Fall': 1, 'Winter': 2, 'Summer': 3}
        sorted_courses = sorted(self.transcript_data, 
                              key=lambda x: (x.get('year', 0), session_order.get(x.get('term', ''), 0)))
        
        for course in sorted_courses:
            grade = course.get('grade', '')
            notation = course.get('notation', '')
            
            # Determine GPA contribution
            if notation in self.SPECIAL_NOTATIONS:
                if notation == 'NC%':
                    gpa_contrib = "0.00"
                else:
                    gpa_contrib = "N/A"
                display_grade = notation
            else:
                gpa_contrib = f"{self.GRADE_POINTS.get(grade, 0.0):.2f}"
                display_grade = grade
            
            # Status
            status = "Complete"
            if notation in ['IPR', 'INC', 'GWR']:
                status = "In Progress"
            elif notation in ['LWD', 'WDR']:
                status = "Withdrawn"
            elif notation in ['CR', 'NCR']:
                status = "CR/NCR"
            
            self.transcript_tree.insert('', 'end', values=(
                course.get('term', ''),
                course.get('year', ''),
                course.get('course_code', ''),
                course.get('title', ''),
                course.get('weight', 0.5),
                course.get('mark', ''),
                display_grade,
                gpa_contrib,
                status
            ))
    
    def update_simulation_display(self):
        """Update simulation results"""
        # Clear simulation tree
        for item in self.simulation_tree.get_children():
            self.simulation_tree.delete(item)
        
        # Add simulation courses to tree
        for course in self.simulation_courses:
            grade = course.get('grade', 'B')
            notation = course.get('notation', '')
            
            if notation and notation != '':
                gpa_impact = "N/A" if notation != 'NC%' else "0.00"
                display_grade = notation
            else:
                gpa_impact = f"{self.GRADE_POINTS.get(grade, 0.0):.2f}"
                display_grade = grade
            
            self.simulation_tree.insert('', 'end', values=(
                course.get('course_code', ''),
                course.get('title', ''),
                course.get('weight', 0.5),
                display_grade,
                notation if notation else 'None',
                gpa_impact
            ))
        
        # Calculate projections
        current_gpa = self.calculate_gpa(self.transcript_data)
        current_credits = sum(course.get('weight', 0.5) for course in self.transcript_data 
                            if course.get('notation', '') not in ['IPR', 'LWD', 'WDR'])
        
        all_courses = self.transcript_data + self.simulation_courses
        projected_gpa = self.calculate_gpa(all_courses)
        projected_credits = sum(course.get('weight', 0.5) for course in all_courses 
                              if course.get('notation', '') not in ['IPR', 'LWD', 'WDR'])
        
        added_credits = sum(course.get('weight', 0.5) for course in self.simulation_courses 
                          if course.get('notation', '') not in ['IPR', 'LWD', 'WDR'])
        
        gpa_change_val = projected_gpa - current_gpa
        
        # Update labels
        self.current_gpa_sim.config(text=f"{current_gpa:.2f}")
        self.current_credits_sim.config(text=f"{current_credits:.1f}")
        self.projected_gpa.config(text=f"{projected_gpa:.2f}")
        self.projected_credits.config(text=f"{projected_credits:.1f}")
        self.added_credits.config(text=f"{added_credits:.1f}")
        
        # Color code GPA change
        change_text = f"{gpa_change_val:+.2f}"
        change_color = "green" if gpa_change_val > 0 else "red" if gpa_change_val < 0 else "black"
        self.gpa_change.config(text=change_text, foreground=change_color)
    
    def update_analytics(self):
        """Update analytics displays"""
        # Grade distribution
        grade_dist = defaultdict(int)
        notation_dist = defaultdict(int)
        
        for course in self.transcript_data:
            notation = course.get('notation', '')
            if notation:
                notation_dist[notation] += 1
            else:
                grade = course.get('grade', '')
                if grade:
                    grade_dist[grade] += 1
        
        # Clear and update grade distribution text
        self.grade_dist_text.delete(1.0, tk.END)
        self.grade_dist_text.insert(tk.END, "GRADE DISTRIBUTION\n" + "="*50 + "\n\n")
        
        if grade_dist:
            self.grade_dist_text.insert(tk.END, "Letter Grades:\n")
            for grade in sorted(grade_dist.keys(), key=lambda x: self.GRADE_POINTS.get(x, 0), reverse=True):
                count = grade_dist[grade]
                percentage = (count / len(self.transcript_data)) * 100
                self.grade_dist_text.insert(tk.END, f"  {grade}: {count} courses ({percentage:.1f}%)\n")
        
        if notation_dist:
            self.grade_dist_text.insert(tk.END, "\nSpecial Notations:\n")
            for notation in sorted(notation_dist.keys()):
                count = notation_dist[notation]
                desc = self.SPECIAL_NOTATIONS.get(notation, 'Unknown')
                self.grade_dist_text.insert(tk.END, f"  {notation}: {count} courses - {desc}\n")
        
        # Subject analysis
        subjects = defaultdict(list)
        for course in self.transcript_data:
            course_code = course.get('course_code', '')
            if course_code and len(course_code) >= 3:
                subject = course_code[:3]  # First 3 letters
                subjects[subject].append(course)
        
        self.subject_text.delete(1.0, tk.END)
        self.subject_text.insert(tk.END, "SUBJECT PERFORMANCE ANALYSIS\n" + "="*50 + "\n\n")
        
        subject_gpas = []
        for subject, courses in subjects.items():
            gpa = self.calculate_gpa(courses)
            credits = sum(course.get('weight', 0.5) for course in courses)
            subject_gpas.append((subject, gpa, len(courses), credits))
        
        # Sort by GPA descending
        subject_gpas.sort(key=lambda x: x[1], reverse=True)
        
        for subject, gpa, count, credits in subject_gpas:
            standing = "Excellent" if gpa >= 3.5 else "Good" if gpa >= 3.0 else "Satisfactory" if gpa >= 2.0 else "Needs Improvement"
            self.subject_text.insert(tk.END, f"{subject}: {gpa:.2f} GPA ({count} courses, {credits:.1f} credits) - {standing}\n")
        
        # Add recommendations
        self.subject_text.insert(tk.END, "\n" + "="*50 + "\nRECOMMENDATIONS\n" + "="*50 + "\n\n")
        
        if subject_gpas:
            worst_subjects = [s for s in subject_gpas if s[1] < 2.0]
            best_subjects = [s for s in subject_gpas if s[1] >= 3.5]
            
            if worst_subjects:
                self.subject_text.insert(tk.END, "Areas Needing Improvement:\n")
                for subject, gpa, count, credits in worst_subjects[:3]:
                    self.subject_text.insert(tk.END, f"  • {subject}: Consider retaking courses or seeking additional support\n")
            
            if best_subjects:
                self.subject_text.insert(tk.END, "\nStrong Areas:\n")
                for subject, gpa, count, credits in best_subjects[:3]:
                    self.subject_text.insert(tk.END, f"  • {subject}: Excellent performance, consider advanced courses\n")
    
    def add_course_dialog(self):
        """Open dialog to add a new course"""
        dialog = CourseDialog(self.root, "Add Course", self.ALL_GRADES)
        if dialog.result:
            self.transcript_data.append(dialog.result)
            self.mark_data_changed()
            self.update_displays()
    
    def edit_course(self):
        """Edit selected course"""
        selection = self.transcript_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a course to edit.")
            return
        
        item = selection[0]
        values = self.transcript_tree.item(item)['values']
        
        # Find the course in data
        course_index = None
        for i, course in enumerate(self.transcript_data):
            if (course.get('term') == values[0] and 
                course.get('year') == int(values[1]) and 
                course.get('course_code') == values[2]):
                course_index = i
                break
        
        if course_index is not None:
            dialog = CourseDialog(self.root, "Edit Course", self.ALL_GRADES, self.transcript_data[course_index])
            if dialog.result:
                self.transcript_data[course_index] = dialog.result
                self.mark_data_changed()
                self.update_displays()
    
    def delete_course(self):
        """Delete selected course"""
        selection = self.transcript_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a course to delete.")
            return
        
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this course?"):
            item = selection[0]
            values = self.transcript_tree.item(item)['values']
            
            # Find and remove the course
            for i, course in enumerate(self.transcript_data):
                if (course.get('term') == values[0] and 
                    course.get('year') == int(values[1]) and 
                    course.get('course_code') == values[2]):
                    del self.transcript_data[i]
                    self.mark_data_changed()
                    break

            self.update_displays()
    
    def add_simulation_course(self):
        """Add a course to simulation"""
        dialog = CourseDialog(self.root, "Add Simulation Course", self.ALL_GRADES, simulation_mode=True)
        if dialog.result:
            self.simulation_courses.append(dialog.result)
            self.mark_data_changed()
            self.update_simulation_display()
    
    def remove_simulation_course(self):
        """Remove selected simulation course"""
        selection = self.simulation_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a course to remove.")
            return
        
        item = selection[0]
        values = self.simulation_tree.item(item)['values']
        course_code = values[0]
        
        # Find and remove the course
        for i, course in enumerate(self.simulation_courses):
            if course.get('course_code') == course_code:
                del self.simulation_courses[i]
                self.mark_data_changed()
                break

        self.update_simulation_display()
    
    def clear_simulation(self):
        """Clear all simulation courses"""
        if messagebox.askyesno("Confirm Clear", "Clear all simulation courses?"):
            self.simulation_courses = []
            self.mark_data_changed()
            self.update_simulation_display()
    
    def calculate_goal(self):
        """Calculate what's needed to reach target GPA"""
        try:
            target_gpa = float(self.target_gpa_var.get())
            if target_gpa < 0 or target_gpa > 4.0:
                raise ValueError("GPA must be between 0.0 and 4.0")
        except ValueError as e:
            messagebox.showerror("Invalid Input", str(e))
            return
        
        current_gpa = self.calculate_gpa(self.transcript_data)
        current_credits = sum(course.get('weight', 0.5) for course in self.transcript_data 
                            if course.get('notation', '') not in ['IPR', 'LWD', 'WDR'])
        
        # Calculate what average grade is needed in next N courses
        for num_courses in [1, 2, 3, 4, 5, 10]:
            credits_per_course = 0.5  # Assume 0.5 FCE courses
            additional_credits = num_courses * credits_per_course
            total_credits = current_credits + additional_credits
            
            required_total_points = target_gpa * total_credits
            current_points = current_gpa * current_credits
            required_additional_points = required_total_points - current_points
            
            if additional_credits > 0:
                required_avg = required_additional_points / additional_credits
                
                if 0 <= required_avg <= 4.0:
                    # Find closest grade
                    closest_grade = min(self.GRADE_POINTS.items(), 
                                      key=lambda x: abs(x[1] - required_avg))[0]
                    
                    result_text = f"To reach {target_gpa:.1f} GPA:\n"
                    result_text += f"Need {required_avg:.2f} average in next {num_courses} courses\n"
                    result_text += f"Approximately {closest_grade} average required"
                    
                    self.goal_result.config(text=result_text)
                    return
        
        self.goal_result.config(text=f"Target GPA {target_gpa:.1f} not achievable with reasonable course load")
    
    def import_csv(self):
        """Import transcript data from CSV"""
        filename = filedialog.askopenfilename(
            title="Import Transcript CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'r', newline='', encoding='utf-8') as file:
                    reader = csv.DictReader(file)
                    imported_data = []
                    
                    for row in reader:
                        # Convert CSV row to course format
                        course = {
                            'term': row.get('Term', ''),
                            'year': int(row.get('Year', 0)) if row.get('Year', '').isdigit() else 0,
                            'course_code': row.get('Course_Code', ''),
                            'title': row.get('Course_Title', ''),
                            'weight': float(row.get('Weight', 0.5)) if row.get('Weight', '') else 0.5,
                            'mark': row.get('Mark', ''),
                            'grade': row.get('Grade', ''),
                            'notation': ''
                        }
                        
                        # Check if grade is actually a special notation
                        if course['grade'] in self.SPECIAL_NOTATIONS:
                            course['notation'] = course['grade']
                            course['grade'] = ''
                        
                        imported_data.append(course)
                    
                    if messagebox.askyesno("Confirm Import",
                                         f"Import {len(imported_data)} courses? This will replace current data."):
                        self.transcript_data = imported_data
                        self.mark_data_changed()
                        self.update_displays()
                        messagebox.showinfo("Success", f"Imported {len(imported_data)} courses successfully.")
                        
            except Exception as e:
                messagebox.showerror("Import Error", f"Error importing CSV: {str(e)}")
    
    def export_csv(self):
        """Export transcript data to CSV"""
        if not self.transcript_data:
            messagebox.showwarning("No Data", "No transcript data to export.")
            return
        
        filename = filedialog.asksaveasfilename(
            title="Export Transcript CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'w', newline='', encoding='utf-8') as file:
                    fieldnames = ['Term', 'Year', 'Course_Code', 'Course_Title', 'Weight', 'Mark', 'Grade', 'Notation']
                    writer = csv.DictWriter(file, fieldnames=fieldnames)
                    writer.writeheader()
                    
                    for course in self.transcript_data:
                        # Export grade or notation
                        display_grade = course.get('notation', '') or course.get('grade', '')
                        
                        writer.writerow({
                            'Term': course.get('term', ''),
                            'Year': course.get('year', ''),
                            'Course_Code': course.get('course_code', ''),
                            'Course_Title': course.get('title', ''),
                            'Weight': course.get('weight', 0.5),
                            'Mark': course.get('mark', ''),
                            'Grade': display_grade,
                            'Notation': course.get('notation', '')
                        })
                
                messagebox.showinfo("Success", f"Exported {len(self.transcript_data)} courses to {filename}")
                
            except Exception as e:
                messagebox.showerror("Export Error", f"Error exporting CSV: {str(e)}")
    
    def save_session(self):
        """Save current session to JSON file"""
        filename = filedialog.asksaveasfilename(
            title="Save Session",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                session_data = {
                    'transcript_data': self.transcript_data,
                    'simulation_courses': self.simulation_courses,
                    'saved_at': datetime.now().isoformat()
                }
                
                with open(filename, 'w', encoding='utf-8') as file:
                    json.dump(session_data, file, indent=2)
                
                messagebox.showinfo("Success", "Session saved successfully.")
                
            except Exception as e:
                messagebox.showerror("Save Error", f"Error saving session: {str(e)}")
    
    def load_session(self):
        """Load session from JSON file"""
        filename = filedialog.askopenfilename(
            title="Load Session",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as file:
                    session_data = json.load(file)
                
                if messagebox.askyesno("Confirm Load", "Loading will replace current data. Continue?"):
                    self.transcript_data = session_data.get('transcript_data', [])
                    self.simulation_courses = session_data.get('simulation_courses', [])
                    self.mark_data_changed()
                    self.update_displays()
                    messagebox.showinfo("Success", "Session loaded successfully.")
                    
            except Exception as e:
                messagebox.showerror("Load Error", f"Error loading session: {str(e)}")
    
    def clear_all_data(self):
        """Clear all data"""
        if messagebox.askyesno("Confirm Clear", "This will delete all transcript and simulation data. Continue?"):
            self.transcript_data = []
            self.simulation_courses = []
            self.mark_data_changed()
            self.update_displays()
    
    def update_data_info(self):
        """Update data information display"""
        info_text = "UofT TRANSCRIPT ANALYZER - DATA REFERENCE\n"
        info_text += "="*60 + "\n\n"
        
        info_text += "GRADE SCALE:\n"
        info_text += "-" * 20 + "\n"
        for grade, points in sorted(self.GRADE_POINTS.items(), key=lambda x: x[1], reverse=True):
            info_text += f"{grade:>3}: {points:.1f} grade points\n"
        
        info_text += "\nSPECIAL NOTATIONS:\n"
        info_text += "-" * 20 + "\n"
        for notation, description in self.SPECIAL_NOTATIONS.items():
            info_text += f"{notation:>4}: {description}\n"
        
        info_text += "\nGPA CALCULATION NOTES:\n"
        info_text += "-" * 25 + "\n"
        info_text += "• Only courses with letter grades (A+ to F) count toward GPA\n"
        info_text += "• CR/NCR courses are excluded from GPA calculation\n"
        info_text += "• NC% notation counts as 0.0 grade points\n"
        info_text += "• IPR, LWD, WDR courses are excluded from credit totals\n"
        info_text += "• Course weights are in Full Course Equivalents (FCE)\n"
        
        info_text += "\nACADEMIC STANDING:\n"
        info_text += "-" * 20 + "\n"
        info_text += "3.5+ GPA: Dean's List\n"
        info_text += "2.0+ GPA: Good Standing\n"
        info_text += "1.0+ GPA: Academic Probation\n"
        info_text += "Below 1.0: Academic Suspension\n"
        
        self.data_info_text.delete(1.0, tk.END)
        self.data_info_text.insert(1.0, info_text)

    # ========== NEW ENHANCED METHODS ==========

    def load_settings(self) -> dict:
        \"\"\"Load application settings from JSON file\"\"\"
        default_settings = {
            'theme': 'light',
            'auto_save_interval': 300,  # 5 minutes
            'backup_retention_days': 30,
            'window_size': '1400x900',
            'font_size': 10,
            'show_tips': True,
            'default_weight': 0.5,
            'preferred_export_format': 'csv'
        }

        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    default_settings.update(loaded_settings)
        except Exception as e:
            print(f\"Error loading settings: {e}\")

        return default_settings

    def save_settings(self):
        \"\"\"Save current settings to JSON file\"\"\"
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f\"Error saving settings: {e}\")

    def init_course_database(self):
        \"\"\"Initialize SQLite database for course prerequisites\"\"\"
        try:
            conn = sqlite3.connect(self.course_db_file)
            cursor = conn.cursor()

            # Create prerequisites table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS prerequisites (
                    course_code TEXT PRIMARY KEY,
                    prerequisites TEXT,
                    corequisites TEXT,
                    exclusions TEXT,
                    description TEXT,
                    faculty TEXT,
                    department TEXT
                )
            ''')

            # Create degree requirements table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS degree_requirements (
                    program_name TEXT,
                    requirement_type TEXT,
                    course_codes TEXT,
                    credit_requirements REAL,
                    description TEXT
                )
            ''')

            conn.commit()
            conn.close()

            # Load sample prerequisite data
            self.load_sample_prerequisites()

        except Exception as e:
            print(f\"Error initializing course database: {e}\")

    def load_sample_prerequisites(self):
        \"\"\"Load sample prerequisite data into database\"\"\"
        sample_prereqs = {
            'CSC148H1': {
                'prerequisites': 'CSC108H1',
                'description': 'Abstract data types and data structures',
                'faculty': 'ARTSC',
                'department': 'Computer Science'
            },
            'CSC236H1': {
                'prerequisites': 'CSC148H1',
                'description': 'Introduction to the theory of computation',
                'faculty': 'ARTSC',
                'department': 'Computer Science'
            },
            'ECO102H1': {
                'prerequisites': 'ECO101H1',
                'description': 'Principles of Macroeconomics',
                'faculty': 'ARTSC',
                'department': 'Economics'
            },
            'ECO200Y1': {
                'prerequisites': 'ECO101H1, ECO102H1',
                'description': 'Microeconomic Theory',
                'faculty': 'ARTSC',
                'department': 'Economics'
            },
            'MAT137Y1': {
                'prerequisites': 'Grade 12 Advanced Functions',
                'description': 'Calculus with Proofs',
                'faculty': 'ARTSC',
                'department': 'Mathematics'
            }
        }

        try:
            conn = sqlite3.connect(self.course_db_file)
            cursor = conn.cursor()

            for course_code, data in sample_prereqs.items():
                cursor.execute('''
                    INSERT OR REPLACE INTO prerequisites
                    (course_code, prerequisites, description, faculty, department)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    course_code,
                    data['prerequisites'],
                    data['description'],
                    data['faculty'],
                    data['department']
                ))

            conn.commit()
            conn.close()
        except Exception as e:
            print(f\"Error loading sample prerequisites: {e}\")

    def schedule_auto_save(self):
        \"\"\"Schedule automatic saving of data\"\"\"
        if self.auto_save_timer:
            self.root.after_cancel(self.auto_save_timer)

        interval = self.settings.get('auto_save_interval', 300) * 1000  # Convert to milliseconds
        self.auto_save_timer = self.root.after(interval, self.auto_save_data)

    def auto_save_data(self):
        \"\"\"Automatically save data if changes detected\"\"\"
        if self.data_changed:
            try:
                auto_save_data = {
                    'transcript_data': self.transcript_data,
                    'simulation_courses': self.simulation_courses,
                    'auto_saved_at': datetime.now().isoformat(),
                    'version': '3.0'
                }

                with open(self.auto_save_file, 'w', encoding='utf-8') as f:
                    json.dump(auto_save_data, f, indent=2)

                self.data_changed = False
                print(\"Auto-save completed successfully\")

            except Exception as e:
                print(f\"Auto-save failed: {e}\")

        # Schedule next auto-save
        self.schedule_auto_save()

    def mark_data_changed(self):
        \"\"\"Mark that data has been modified\"\"\"
        self.data_changed = True

    def create_backup(self):
        \"\"\"Create a timestamped backup of current data\"\"\"
        try:
            timestamp = datetime.now().strftime(\"%Y%m%d_%H%M%S\")
            backup_file = self.backup_dir / f\"backup_{timestamp}.json\"

            backup_data = {
                'transcript_data': self.transcript_data,
                'simulation_courses': self.simulation_courses,
                'settings': self.settings,
                'backup_created': datetime.now().isoformat(),
                'version': '3.0'
            }

            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2)

            # Clean old backups
            self.clean_old_backups()

            return backup_file

        except Exception as e:
            messagebox.showerror(\"Backup Error\", f\"Failed to create backup: {e}\")
            return None

    def clean_old_backups(self):
        \"\"\"Remove old backup files\"\"\"
        try:
            retention_days = self.settings.get('backup_retention_days', 30)
            cutoff_date = datetime.now() - timedelta(days=retention_days)

            for backup_file in self.backup_dir.glob(\"backup_*.json\"):
                try:
                    file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                    if file_time < cutoff_date:
                        backup_file.unlink()
                except Exception:
                    continue

        except Exception as e:
            print(f\"Error cleaning old backups: {e}\")

    def on_closing(self):
        \"\"\"Handle application closing\"\"\"
        if self.data_changed:
            if messagebox.askyesno(\"Unsaved Changes\",
                                 \"You have unsaved changes. Save before closing?\"):
                self.save_session_quick()

        # Cancel auto-save timer
        if self.auto_save_timer:
            self.root.after_cancel(self.auto_save_timer)

        # Save settings
        self.save_settings()

        self.root.destroy()

    def save_session_quick(self):
        \"\"\"Quick save without file dialog\"\"\"
        try:
            session_data = {
                'transcript_data': self.transcript_data,
                'simulation_courses': self.simulation_courses,
                'saved_at': datetime.now().isoformat(),
                'version': '3.0'
            }

            quick_save_file = self.app_data_dir / \"last_session.json\"
            with open(quick_save_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2)

            self.data_changed = False

        except Exception as e:
            messagebox.showerror(\"Save Error\", f\"Failed to save session: {e}\")

    # ========== NEW FEATURE METHODS ==========

    def on_search_change(self, *args):
        \"\"\"Handle search text changes\"\"\"
        self.update_filter_displays()

    def on_filter_change(self, event=None):
        \"\"\"Handle filter changes\"\"\"
        self.update_filter_combo_values()
        self.update_filter_displays()

    def clear_search(self):
        \"\"\"Clear search and filters\"\"\"
        self.search_var.set(\"\")
        self.filter_term_var.set(\"All\")
        self.filter_year_var.set(\"All\")
        self.filter_dept_var.set(\"All\")
        self.filter_grade_var.set(\"All\")
        self.update_filter_displays()

    def update_filter_combo_values(self):
        \"\"\"Update filter combo box values based on current data\"\"\"
        # Update year filter values
        years = sorted(set(str(course.get('year', '')) for course in self.transcript_data if course.get('year')))
        self.year_filter['values'] = [\"All\"] + years

        # Update department filter values
        departments = sorted(set(course.get('course_code', '')[:3] for course in self.transcript_data
                               if course.get('course_code') and len(course.get('course_code', '')) >= 3))
        self.dept_filter['values'] = [\"All\"] + departments

    def update_filter_displays(self):
        \"\"\"Update displays based on current filters\"\"\"
        filtered_data = self.apply_filters(self.transcript_data)
        self.update_transcript_tree_filtered(filtered_data)

    def apply_filters(self, data):
        \"\"\"Apply current filters to data\"\"\"
        search_text = self.search_var.get().lower()
        term_filter = self.filter_term_var.get()
        year_filter = self.filter_year_var.get()
        dept_filter = self.filter_dept_var.get()
        grade_filter = self.filter_grade_var.get()

        filtered_data = []
        for course in data:
            # Apply search filter
            if search_text:
                searchable_text = f\"{course.get('course_code', '')} {course.get('title', '')}\".lower()
                if search_text not in searchable_text:
                    continue

            # Apply term filter
            if term_filter != \"All\" and course.get('term', '') != term_filter:
                continue

            # Apply year filter
            if year_filter != \"All\" and str(course.get('year', '')) != year_filter:
                continue

            # Apply department filter
            if dept_filter != \"All\":
                course_dept = course.get('course_code', '')[:3] if course.get('course_code') else ''
                if course_dept != dept_filter:
                    continue

            # Apply grade filter
            if grade_filter != \"All\":
                course_grade = course.get('grade', '') or course.get('notation', '')
                if course_grade != grade_filter:
                    continue

            filtered_data.append(course)

        return filtered_data

    def update_transcript_tree_filtered(self, courses):
        \"\"\"Update transcript tree with filtered courses\"\"\"
        # Clear existing items
        for item in self.transcript_tree.get_children():
            self.transcript_tree.delete(item)

        # Sort courses by year and term
        session_order = {'Fall': 1, 'Winter': 2, 'Summer': 3}
        sorted_courses = sorted(courses,
                              key=lambda x: (x.get('year', 0), session_order.get(x.get('term', ''), 0)))

        for course in sorted_courses:
            grade = course.get('grade', '')
            notation = course.get('notation', '')

            # Determine GPA contribution
            if notation in self.SPECIAL_NOTATIONS:
                if notation == 'NC%':
                    gpa_contrib = \"0.00\"
                else:
                    gpa_contrib = \"N/A\"
                display_grade = notation
            else:
                gpa_contrib = f\"{self.GRADE_POINTS.get(grade, 0.0):.2f}\"
                display_grade = grade

            # Status
            status = \"Complete\"
            if notation in ['IPR', 'INC', 'GWR']:
                status = \"In Progress\"
            elif notation in ['LWD', 'WDR']:
                status = \"Withdrawn\"
            elif notation in ['CR', 'NCR']:
                status = \"CR/NCR\"

            self.transcript_tree.insert('', 'end', values=(
                course.get('term', ''),
                course.get('year', ''),
                course.get('course_code', ''),
                course.get('title', ''),
                course.get('weight', 0.5),
                course.get('mark', ''),
                display_grade,
                gpa_contrib,
                status
            ))

    def duplicate_course(self):
        \"\"\"Duplicate selected course\"\"\"
        selection = self.transcript_tree.selection()
        if not selection:
            messagebox.showwarning(\"No Selection\", \"Please select a course to duplicate.\")
            return

        item = selection[0]
        values = self.transcript_tree.item(item)['values']

        # Find the course in data
        for course in self.transcript_data:
            if (course.get('term') == values[0] and
                course.get('year') == int(values[1]) and
                course.get('course_code') == values[2]):

                # Create duplicate with dialog
                dialog = CourseDialog(self.root, \"Duplicate Course\", self.ALL_GRADES, course.copy())
                if dialog.result:
                    self.transcript_data.append(dialog.result)
                    self.mark_data_changed()
                    self.update_displays()
                break

    def export_excel(self):
        \"\"\"Export transcript data to Excel\"\"\"
        if not EXCEL_AVAILABLE:
            messagebox.showerror(\"Excel Export Unavailable\",
                               \"Please install openpyxl for Excel export functionality:\\npip install openpyxl\")
            return

        if not self.transcript_data:
            messagebox.showwarning(\"No Data\", \"No transcript data to export.\")
            return

        filename = filedialog.asksaveasfilename(
            title=\"Export to Excel\",
            defaultextension=\".xlsx\",
            filetypes=[(\"Excel files\", \"*.xlsx\"), (\"All files\", \"*.*\")]
        )

        if filename:
            try:
                import openpyxl
                from openpyxl.styles import Font, PatternFill, Alignment

                wb = openpyxl.Workbook()

                # Transcript sheet
                ws1 = wb.active
                ws1.title = \"Transcript\"

                # Headers
                headers = ['Term', 'Year', 'Course Code', 'Course Title', 'Weight', 'Mark', 'Grade', 'GPA Points', 'Status']
                for col, header in enumerate(headers, 1):
                    cell = ws1.cell(row=1, column=col, value=header)
                    cell.font = Font(bold=True)
                    cell.fill = PatternFill(start_color=\"366092\", end_color=\"366092\", fill_type=\"solid\")

                # Data
                for row, course in enumerate(self.transcript_data, 2):
                    grade = course.get('grade', '')
                    notation = course.get('notation', '')
                    display_grade = notation if notation else grade
                    gpa_points = self.GRADE_POINTS.get(grade, 0.0) if grade and not notation else 0.0

                    ws1.cell(row=row, column=1, value=course.get('term', ''))
                    ws1.cell(row=row, column=2, value=course.get('year', ''))
                    ws1.cell(row=row, column=3, value=course.get('course_code', ''))
                    ws1.cell(row=row, column=4, value=course.get('title', ''))
                    ws1.cell(row=row, column=5, value=course.get('weight', 0.5))
                    ws1.cell(row=row, column=6, value=course.get('mark', ''))
                    ws1.cell(row=row, column=7, value=display_grade)
                    ws1.cell(row=row, column=8, value=gpa_points)

                # Summary sheet
                ws2 = wb.create_sheet(\"Summary\")
                current_gpa = self.calculate_gpa(self.transcript_data)
                total_credits = sum(course.get('weight', 0.5) for course in self.transcript_data)

                summary_data = [
                    ['Metric', 'Value'],
                    ['Cumulative GPA', f\"{current_gpa:.2f}\"],
                    ['Total Credits', f\"{total_credits:.1f}\"],
                    ['Courses Completed', str(len(self.transcript_data))],
                    ['Academic Standing', self.get_academic_standing(current_gpa)]
                ]

                for row, row_data in enumerate(summary_data, 1):
                    for col, value in enumerate(row_data, 1):
                        cell = ws2.cell(row=row, column=col, value=value)
                        if row == 1:
                            cell.font = Font(bold=True)

                wb.save(filename)
                messagebox.showinfo(\"Success\", f\"Excel file exported successfully to {filename}\")

            except Exception as e:
                messagebox.showerror(\"Export Error\", f\"Error exporting to Excel: {str(e)}\")

    def export_pdf(self):
        \"\"\"Export transcript data to PDF\"\"\"
        if not PDF_AVAILABLE:
            messagebox.showerror(\"PDF Export Unavailable\",
                               \"Please install reportlab for PDF export functionality:\\npip install reportlab\")
            return

        if not self.transcript_data:
            messagebox.showwarning(\"No Data\", \"No transcript data to export.\")
            return

        filename = filedialog.asksaveasfilename(
            title=\"Export to PDF\",
            defaultextension=\".pdf\",
            filetypes=[(\"PDF files\", \"*.pdf\"), (\"All files\", \"*.*\")]
        )

        if filename:
            try:
                from reportlab.lib.pagesizes import letter
                from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
                from reportlab.lib.styles import getSampleStyleSheet
                from reportlab.lib import colors

                doc = SimpleDocTemplate(filename, pagesize=letter)
                styles = getSampleStyleSheet()
                story = []

                # Title
                title = Paragraph(\"UofT Academic Transcript\", styles['Title'])
                story.append(title)
                story.append(Spacer(1, 12))

                # Summary
                current_gpa = self.calculate_gpa(self.transcript_data)
                total_credits = sum(course.get('weight', 0.5) for course in self.transcript_data)

                summary_text = f\"\"\"
                <b>Cumulative GPA:</b> {current_gpa:.2f}<br/>
                <b>Total Credits:</b> {total_credits:.1f}<br/>
                <b>Courses Completed:</b> {len(self.transcript_data)}<br/>
                <b>Academic Standing:</b> {self.get_academic_standing(current_gpa)}
                \"\"\"

                summary_para = Paragraph(summary_text, styles['Normal'])
                story.append(summary_para)
                story.append(Spacer(1, 12))

                # Course data
                data = [['Term', 'Year', 'Course', 'Title', 'Weight', 'Grade', 'GPA']]

                for course in self.transcript_data:
                    grade = course.get('grade', '')
                    notation = course.get('notation', '')
                    display_grade = notation if notation else grade
                    gpa_points = self.GRADE_POINTS.get(grade, 0.0) if grade and not notation else 0.0

                    data.append([
                        course.get('term', ''),
                        str(course.get('year', '')),
                        course.get('course_code', ''),
                        course.get('title', '')[:30] + '...' if len(course.get('title', '')) > 30 else course.get('title', ''),
                        str(course.get('weight', 0.5)),
                        display_grade,
                        f\"{gpa_points:.2f}\"
                    ])

                table = Table(data)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('FONTSIZE', (0, 1), (-1, -1), 7),
                ]))

                story.append(table)
                doc.build(story)

                messagebox.showinfo(\"Success\", f\"PDF exported successfully to {filename}\")

            except Exception as e:
                messagebox.showerror(\"Export Error\", f\"Error exporting to PDF: {str(e)}\")

    def lookup_course_info(self):
        \"\"\"Look up course information from database\"\"\"
        course_code = self.prereq_search_var.get().strip().upper()
        if not course_code:
            messagebox.showwarning(\"Input Required\", \"Please enter a course code.\")
            return

        try:
            conn = sqlite3.connect(self.course_db_file)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT prerequisites, corequisites, exclusions, description, faculty, department
                FROM prerequisites WHERE course_code = ?
            ''', (course_code,))

            result = cursor.fetchone()
            conn.close()

            self.course_info_text.delete(1.0, tk.END)

            if result:
                prereqs, coreqs, exclusions, description, faculty, department = result

                info_text = f\"COURSE INFORMATION: {course_code}\\n\"
                info_text += \"=\"*50 + \"\\n\\n\"
                info_text += f\"Faculty: {faculty or 'N/A'}\\n\"
                info_text += f\"Department: {department or 'N/A'}\\n\"
                info_text += f\"Description: {description or 'N/A'}\\n\\n\"
                info_text += f\"Prerequisites: {prereqs or 'None'}\\n\"
                info_text += f\"Corequisites: {coreqs or 'None'}\\n\"
                info_text += f\"Exclusions: {exclusions or 'None'}\\n\\n\"

                # Check if student has taken prerequisites
                taken_courses = [course.get('course_code', '') for course in self.transcript_data]
                if prereqs:
                    info_text += \"PREREQUISITE STATUS:\\n\"
                    prereq_list = [p.strip() for p in prereqs.split(',')]
                    for prereq in prereq_list:
                        if prereq in taken_courses:
                            info_text += f\"✓ {prereq} - COMPLETED\\n\"
                        else:
                            info_text += f\"✗ {prereq} - NOT TAKEN\\n\"

                self.course_info_text.insert(1.0, info_text)
            else:
                info_text = f\"Course {course_code} not found in database.\\n\\n\"
                info_text += \"You can add this course to the database using the 'Add to Database' button.\"
                self.course_info_text.insert(1.0, info_text)

        except Exception as e:
            messagebox.showerror(\"Database Error\", f\"Error looking up course: {e}\")

    def add_course_to_db(self):
        \"\"\"Add course to prerequisites database\"\"\"
        course_code = self.prereq_search_var.get().strip().upper()
        if not course_code:
            messagebox.showwarning(\"Input Required\", \"Please enter a course code.\")
            return

        dialog = CourseInfoDialog(self.root, course_code)
        if dialog.result:
            try:
                conn = sqlite3.connect(self.course_db_file)
                cursor = conn.cursor()

                cursor.execute('''
                    INSERT OR REPLACE INTO prerequisites
                    (course_code, prerequisites, corequisites, exclusions, description, faculty, department)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    course_code,
                    dialog.result['prerequisites'],
                    dialog.result['corequisites'],
                    dialog.result['exclusions'],
                    dialog.result['description'],
                    dialog.result['faculty'],
                    dialog.result['department']
                ))

                conn.commit()
                conn.close()

                messagebox.showinfo(\"Success\", f\"Course {course_code} added to database.\")
                self.lookup_course_info()  # Refresh display

            except Exception as e:
                messagebox.showerror(\"Database Error\", f\"Error adding course to database: {e}\")

    def validate_all_prerequisites(self):
        \"\"\"Validate prerequisites for all courses\"\"\"
        self.prereq_validation_text.delete(1.0, tk.END)
        validation_text = \"PREREQUISITES VALIDATION REPORT\\n\"
        validation_text += \"=\"*50 + \"\\n\\n\"

        taken_courses = set(course.get('course_code', '') for course in self.transcript_data)
        issues_found = False

        try:
            conn = sqlite3.connect(self.course_db_file)
            cursor = conn.cursor()

            for course in self.transcript_data:
                course_code = course.get('course_code', '')
                if not course_code:
                    continue

                cursor.execute('''
                    SELECT prerequisites FROM prerequisites WHERE course_code = ?
                ''', (course_code,))

                result = cursor.fetchone()
                if result and result[0]:
                    prereqs = [p.strip() for p in result[0].split(',')]
                    missing_prereqs = [p for p in prereqs if p not in taken_courses]

                    if missing_prereqs:
                        issues_found = True
                        validation_text += f\"⚠️  {course_code}:\\n\"
                        validation_text += f\"   Missing prerequisites: {', '.join(missing_prereqs)}\\n\"
                        validation_text += f\"   Taken in: {course.get('term', '')} {course.get('year', '')}\\n\\n\"

            conn.close()

            if not issues_found:
                validation_text += \"✅ No prerequisite violations found!\\n\"
                validation_text += \"All courses appear to have their prerequisites satisfied.\"

            self.prereq_validation_text.insert(1.0, validation_text)

        except Exception as e:
            error_text = f\"Error validating prerequisites: {e}\"
            self.prereq_validation_text.insert(1.0, error_text)

    def load_degree_requirements(self):
        \"\"\"Load degree requirements for selected program\"\"\"
        program = self.program_var.get()

        # Sample degree requirements
        sample_requirements = {
            \"Computer Science Specialist\": {
                \"core_courses\": [\"CSC108H1\", \"CSC148H1\", \"CSC165H1\", \"CSC207H1\", \"CSC236H1\", \"CSC258H1\", \"CSC263H1\", \"CSC373H1\"],
                \"math_requirements\": [\"MAT137Y1\", \"MAT223H1\", \"STA247H1\"],
                \"breadth_requirements\": {\"humanities\": 1.0, \"social_science\": 1.0, \"science\": 1.0},
                \"total_credits\": 20.0,
                \"minimum_gpa\": 2.0
            },
            \"Economics Major\": {
                \"core_courses\": [\"ECO101H1\", \"ECO102H1\", \"ECO200Y1\", \"ECO202Y1\", \"ECO227Y1\"],
                \"math_requirements\": [\"MAT133Y1\", \"STA220H1\"],
                \"breadth_requirements\": {\"humanities\": 1.0, \"social_science\": 0.5, \"science\": 1.0},
                \"total_credits\": 14.0,
                \"minimum_gpa\": 2.0
            }
        }

        requirements = sample_requirements.get(program, {})
        self.degree_requirements = requirements

        self.update_degree_progress()

    def update_degree_progress(self):
        \"\"\"Update degree progress display\"\"\"
        if not self.degree_requirements:
            self.progress_text.delete(1.0, tk.END)
            self.progress_text.insert(1.0, \"No degree requirements loaded. Please select a program and load requirements.\")
            return

        progress_text = f\"DEGREE PROGRESS: {self.program_var.get()}\\n\"
        progress_text += \"=\"*60 + \"\\n\\n\"

        taken_courses = set(course.get('course_code', '') for course in self.transcript_data)
        total_credits = sum(course.get('weight', 0.5) for course in self.transcript_data)

        # Core courses progress
        if 'core_courses' in self.degree_requirements:
            core_courses = self.degree_requirements['core_courses']
            completed_core = [c for c in core_courses if c in taken_courses]

            progress_text += f\"CORE COURSES ({len(completed_core)}/{len(core_courses)} completed):\\n\"
            for course in core_courses:
                status = \"✓\" if course in taken_courses else \"○\"
                progress_text += f\"  {status} {course}\\n\"
            progress_text += \"\\n\"

        # Math requirements
        if 'math_requirements' in self.degree_requirements:
            math_courses = self.degree_requirements['math_requirements']
            completed_math = [c for c in math_courses if c in taken_courses]

            progress_text += f\"MATH REQUIREMENTS ({len(completed_math)}/{len(math_courses)} completed):\\n\"
            for course in math_courses:
                status = \"✓\" if course in taken_courses else \"○\"
                progress_text += f\"  {status} {course}\\n\"
            progress_text += \"\\n\"

        # Credit progress
        required_credits = self.degree_requirements.get('total_credits', 20.0)
        progress_text += f\"CREDIT PROGRESS:\\n\"
        progress_text += f\"  Completed: {total_credits:.1f} FCE\\n\"
        progress_text += f\"  Required: {required_credits:.1f} FCE\\n\"
        progress_text += f\"  Remaining: {max(0, required_credits - total_credits):.1f} FCE\\n\\n\"

        # GPA requirement
        current_gpa = self.calculate_gpa(self.transcript_data)
        min_gpa = self.degree_requirements.get('minimum_gpa', 2.0)
        gpa_status = \"✓\" if current_gpa >= min_gpa else \"✗\"
        progress_text += f\"GPA REQUIREMENT:\\n\"
        progress_text += f\"  {gpa_status} Current: {current_gpa:.2f} (Required: {min_gpa:.2f})\\n\\n\"

        # Overall progress
        core_progress = len(completed_core) / len(core_courses) if 'core_courses' in self.degree_requirements else 1.0
        credit_progress = min(1.0, total_credits / required_credits)
        gpa_progress = 1.0 if current_gpa >= min_gpa else 0.0

        overall_progress = (core_progress + credit_progress + gpa_progress) / 3 * 100
        progress_text += f\"OVERALL PROGRESS: {overall_progress:.1f}%\\n\"

        self.progress_text.delete(1.0, tk.END)
        self.progress_text.insert(1.0, progress_text)

    def edit_degree_requirements(self):
        \"\"\"Edit degree requirements\"\"\"
        messagebox.showinfo(\"Feature Coming Soon\", \"Degree requirements editing will be available in a future update.\")

    def generate_transcript_report(self):
        \"\"\"Generate comprehensive transcript report\"\"\"
        if not MATPLOTLIB_AVAILABLE:
            # Text-based report
            if hasattr(self, 'reports_text'):
                self.reports_text.delete(1.0, tk.END)
                report_text = self.create_text_report()
                self.reports_text.insert(1.0, report_text)
        else:
            # Generate charts
            self.create_transcript_charts()

    def create_text_report(self):
        \"\"\"Create text-based transcript report\"\"\"
        report = \"COMPREHENSIVE TRANSCRIPT REPORT\\n\"
        report += \"=\"*50 + \"\\n\\n\"

        # Basic statistics
        current_gpa = self.calculate_gpa(self.transcript_data)
        total_credits = sum(course.get('weight', 0.5) for course in self.transcript_data)

        report += f\"Overall Statistics:\\n\"
        report += f\"  Cumulative GPA: {current_gpa:.2f}\\n\"
        report += f\"  Total Credits: {total_credits:.1f} FCE\\n\"
        report += f\"  Courses Taken: {len(self.transcript_data)}\\n\\n\"

        # Grade distribution
        grade_counts = defaultdict(int)
        for course in self.transcript_data:
            grade = course.get('grade', '') or course.get('notation', '')
            if grade:
                grade_counts[grade] += 1

        report += \"Grade Distribution:\\n\"
        for grade in sorted(grade_counts.keys()):
            count = grade_counts[grade]
            percentage = (count / len(self.transcript_data)) * 100
            report += f\"  {grade}: {count} courses ({percentage:.1f}%)\\n\"

        return report

    def create_transcript_charts(self):
        \"\"\"Create matplotlib charts for transcript data\"\"\"
        # Clear existing charts
        for widget in self.chart_frame.winfo_children():
            widget.destroy()

        # Create figure with subplots
        fig = Figure(figsize=(12, 8), dpi=100)

        # GPA by semester chart
        ax1 = fig.add_subplot(2, 2, 1)
        self.plot_gpa_by_semester(ax1)

        # Grade distribution chart
        ax2 = fig.add_subplot(2, 2, 2)
        self.plot_grade_distribution(ax2)

        # Credits by year chart
        ax3 = fig.add_subplot(2, 2, 3)
        self.plot_credits_by_year(ax3)

        # Subject performance chart
        ax4 = fig.add_subplot(2, 2, 4)
        self.plot_subject_performance(ax4)

        fig.tight_layout()

        # Embed in tkinter
        canvas = FigureCanvasTkAgg(fig, self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)

    def plot_gpa_by_semester(self, ax):
        \"\"\"Plot GPA by semester\"\"\"
        sessions = defaultdict(list)
        for course in self.transcript_data:
            term = course.get('term', '')
            year = course.get('year', '')
            if term and year:
                sessions[f\"{term} {year}\"].append(course)

        session_order = {'Fall': 1, 'Winter': 2, 'Summer': 3}
        sorted_sessions = sorted(sessions.items(),
                               key=lambda x: (int(x[0].split()[1]), session_order.get(x[0].split()[0], 0)))

        session_names = []
        gpas = []

        for session_name, courses in sorted_sessions:
            gpa = self.calculate_gpa(courses)
            session_names.append(session_name)
            gpas.append(gpa)

        ax.plot(range(len(session_names)), gpas, marker='o')
        ax.set_title('GPA by Semester')
        ax.set_ylabel('GPA')
        ax.set_xticks(range(len(session_names)))
        ax.set_xticklabels(session_names, rotation=45, ha='right')
        ax.grid(True, alpha=0.3)

    def plot_grade_distribution(self, ax):
        \"\"\"Plot grade distribution\"\"\"
        grade_counts = defaultdict(int)
        for course in self.transcript_data:
            grade = course.get('grade', '')
            if grade and grade in self.GRADE_POINTS:
                grade_counts[grade] += 1

        grades = list(grade_counts.keys())
        counts = list(grade_counts.values())

        ax.bar(grades, counts)
        ax.set_title('Grade Distribution')
        ax.set_ylabel('Number of Courses')
        ax.set_xlabel('Grade')

    def plot_credits_by_year(self, ax):
        \"\"\"Plot credits by year\"\"\"
        year_credits = defaultdict(float)
        for course in self.transcript_data:
            year = course.get('year', '')
            if year:
                year_credits[year] += course.get('weight', 0.5)

        years = sorted(year_credits.keys())
        credits = [year_credits[year] for year in years]

        ax.bar([str(year) for year in years], credits)
        ax.set_title('Credits by Year')
        ax.set_ylabel('Credits (FCE)')
        ax.set_xlabel('Year')

    def plot_subject_performance(self, ax):
        \"\"\"Plot subject performance\"\"\"
        subjects = defaultdict(list)
        for course in self.transcript_data:
            course_code = course.get('course_code', '')
            if course_code and len(course_code) >= 3:
                subject = course_code[:3]
                subjects[subject].append(course)

        subject_gpas = []
        subject_names = []

        for subject, courses in subjects.items():
            gpa = self.calculate_gpa(courses)
            subject_gpas.append(gpa)
            subject_names.append(subject)

        # Sort by GPA
        sorted_data = sorted(zip(subject_names, subject_gpas), key=lambda x: x[1], reverse=True)
        subject_names, subject_gpas = zip(*sorted_data) if sorted_data else ([], [])

        ax.barh(subject_names, subject_gpas)
        ax.set_title('GPA by Subject')
        ax.set_xlabel('GPA')

    def generate_gpa_trend(self):
        \"\"\"Generate GPA trend analysis\"\"\"
        if MATPLOTLIB_AVAILABLE:
            self.create_gpa_trend_chart()
        else:
            messagebox.showinfo(\"Charts Unavailable\", \"Install matplotlib for chart functionality.\")

    def create_gpa_trend_chart(self):
        \"\"\"Create detailed GPA trend chart\"\"\"
        # Clear existing charts
        for widget in self.chart_frame.winfo_children():
            widget.destroy()

        fig = Figure(figsize=(12, 6), dpi=100)
        ax = fig.add_subplot(1, 1, 1)

        # Calculate cumulative GPA over time
        sessions = defaultdict(list)
        for course in self.transcript_data:
            term = course.get('term', '')
            year = course.get('year', '')
            if term and year:
                sessions[f\"{term} {year}\"].append(course)

        session_order = {'Fall': 1, 'Winter': 2, 'Summer': 3}
        sorted_sessions = sorted(sessions.items(),
                               key=lambda x: (int(x[0].split()[1]), session_order.get(x[0].split()[0], 0)))

        cumulative_courses = []
        cumulative_gpas = []
        session_gpas = []
        session_names = []

        for session_name, courses in sorted_sessions:
            cumulative_courses.extend(courses)
            cumulative_gpa = self.calculate_gpa(cumulative_courses)
            session_gpa = self.calculate_gpa(courses)

            cumulative_gpas.append(cumulative_gpa)
            session_gpas.append(session_gpa)
            session_names.append(session_name)

        x_pos = range(len(session_names))

        ax.plot(x_pos, cumulative_gpas, marker='o', label='Cumulative GPA', linewidth=2)
        ax.plot(x_pos, session_gpas, marker='s', label='Session GPA', alpha=0.7)

        ax.set_title('GPA Trend Analysis')
        ax.set_ylabel('GPA')
        ax.set_xlabel('Session')
        ax.set_xticks(x_pos)
        ax.set_xticklabels(session_names, rotation=45, ha='right')
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0, 4)

        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)

    def generate_course_distribution(self):
        \"\"\"Generate course distribution charts\"\"\"
        if MATPLOTLIB_AVAILABLE:
            self.create_course_distribution_charts()
        else:
            messagebox.showinfo(\"Charts Unavailable\", \"Install matplotlib for chart functionality.\")

    def create_course_distribution_charts(self):
        \"\"\"Create course distribution charts\"\"\"
        # Clear existing charts
        for widget in self.chart_frame.winfo_children():
            widget.destroy()

        fig = Figure(figsize=(12, 8), dpi=100)

        # Courses by department
        ax1 = fig.add_subplot(2, 2, 1)
        dept_counts = defaultdict(int)
        for course in self.transcript_data:
            course_code = course.get('course_code', '')
            if course_code and len(course_code) >= 3:
                dept = course_code[:3]
                dept_counts[dept] += 1

        if dept_counts:
            depts, counts = zip(*sorted(dept_counts.items(), key=lambda x: x[1], reverse=True)[:10])
            ax1.bar(depts, counts)
            ax1.set_title('Courses by Department (Top 10)')
            ax1.set_ylabel('Number of Courses')
            ax1.tick_params(axis='x', rotation=45)

        # Courses by level
        ax2 = fig.add_subplot(2, 2, 2)
        level_counts = defaultdict(int)
        for course in self.transcript_data:
            course_code = course.get('course_code', '')
            if course_code and len(course_code) >= 4:
                level = course_code[3]
                level_counts[f\"{level}00-level\"] += 1

        if level_counts:
            levels, counts = zip(*sorted(level_counts.items()))
            ax2.pie(counts, labels=levels, autopct='%1.1f%%')
            ax2.set_title('Courses by Level')

        # Credits by term
        ax3 = fig.add_subplot(2, 2, 3)
        term_credits = defaultdict(float)
        for course in self.transcript_data:
            term = course.get('term', '')
            if term:
                term_credits[term] += course.get('weight', 0.5)

        if term_credits:
            terms, credits = zip(*term_credits.items())
            ax3.bar(terms, credits)
            ax3.set_title('Credits by Term Type')
            ax3.set_ylabel('Credits (FCE)')

        # Performance by course level
        ax4 = fig.add_subplot(2, 2, 4)
        level_gpas = defaultdict(list)
        for course in self.transcript_data:
            course_code = course.get('course_code', '')
            grade = course.get('grade', '')
            if course_code and len(course_code) >= 4 and grade in self.GRADE_POINTS:
                level = course_code[3]
                level_gpas[f\"{level}00\"].append(self.GRADE_POINTS[grade])

        if level_gpas:
            levels = sorted(level_gpas.keys())
            avg_gpas = [sum(level_gpas[level]) / len(level_gpas[level]) for level in levels]
            ax4.bar(levels, avg_gpas)
            ax4.set_title('Average GPA by Course Level')
            ax4.set_ylabel('Average GPA')

        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)

    def export_all_charts(self):
        \"\"\"Export all charts to files\"\"\"
        if not MATPLOTLIB_AVAILABLE:
            messagebox.showerror(\"Charts Unavailable\", \"Install matplotlib for chart functionality.\")
            return

        export_dir = filedialog.askdirectory(title=\"Select Export Directory\")
        if not export_dir:
            return

        try:
            # Generate and save each chart type
            chart_types = [
                ('transcript_overview', self.create_transcript_charts),
                ('gpa_trend', self.create_gpa_trend_chart),
                ('course_distribution', self.create_course_distribution_charts)
            ]

            for chart_name, chart_func in chart_types:
                chart_func()

                # Save current chart
                for widget in self.chart_frame.winfo_children():
                    if isinstance(widget, FigureCanvasTkAgg):
                        widget.figure.savefig(
                            os.path.join(export_dir, f\"{chart_name}.png\"),
                            dpi=300, bbox_inches='tight'
                        )
                        break

            messagebox.showinfo(\"Success\", f\"Charts exported to {export_dir}\")

        except Exception as e:
            messagebox.showerror(\"Export Error\", f\"Error exporting charts: {e}\")

    def change_theme(self, event=None):
        \"\"\"Change application theme\"\"\"
        # This is a placeholder for theme changing functionality
        # Full theme implementation would require more extensive changes
        theme = self.theme_var.get()
        self.settings['theme'] = theme
        messagebox.showinfo(\"Theme Changed\", f\"Theme changed to {theme}. Restart required for full effect.\")

    def apply_font_size(self):
        \"\"\"Apply font size changes\"\"\"
        font_size = self.font_size_var.get()
        self.settings['font_size'] = font_size
        messagebox.showinfo(\"Font Size Changed\", \"Font size updated. Some changes may require restart.\")

    def save_all_settings(self):
        \"\"\"Save all current settings\"\"\"
        self.settings['auto_save_interval'] = self.autosave_var.get() * 60
        self.settings['backup_retention_days'] = self.backup_retention_var.get()
        self.settings['theme'] = self.theme_var.get()
        self.settings['font_size'] = self.font_size_var.get()

        self.save_settings()
        messagebox.showinfo(\"Settings Saved\", \"All settings have been saved successfully.\")

    def open_data_folder(self):
        \"\"\"Open application data folder\"\"\"
        try:
            if sys.platform == \"win32\":
                os.startfile(self.app_data_dir)
            elif sys.platform == \"darwin\":
                os.system(f\"open '{self.app_data_dir}'\"")
            else:
                os.system(f\"xdg-open '{self.app_data_dir}'\"")
        except Exception as e:
            messagebox.showerror(\"Error\", f\"Could not open data folder: {e}\")

    def export_settings(self):
        \"\"\"Export settings to file\"\"\"
        filename = filedialog.asksaveasfilename(
            title=\"Export Settings\",
            defaultextension=\".json\",
            filetypes=[(\"JSON files\", \"*.json\")]
        )

        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(self.settings, f, indent=2)
                messagebox.showinfo(\"Success\", \"Settings exported successfully.\")
            except Exception as e:
                messagebox.showerror(\"Export Error\", f\"Error exporting settings: {e}\")

    def import_settings(self):
        \"\"\"Import settings from file\"\"\"
        filename = filedialog.askopenfilename(
            title=\"Import Settings\",
            filetypes=[(\"JSON files\", \"*.json\")]
        )

        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    imported_settings = json.load(f)

                self.settings.update(imported_settings)
                self.save_settings()
                messagebox.showinfo(\"Success\", \"Settings imported successfully. Restart recommended.\")
            except Exception as e:
                messagebox.showerror(\"Import Error\", f\"Error importing settings: {e}\")

    def show_user_guide(self):
        \"\"\"Show user guide\"\"\"
        guide_window = tk.Toplevel(self.root)
        guide_window.title(\"User Guide\")
        guide_window.geometry(\"800x600\")

        guide_text = tk.Text(guide_window, wrap=tk.WORD, padx=10, pady=10)
        scrollbar = ttk.Scrollbar(guide_window, orient='vertical', command=guide_text.yview)
        guide_text.configure(yscrollcommand=scrollbar.set)

        guide_content = \"\"\"
UofT TRANSCRIPT ANALYZER v3.0 - USER GUIDE

OVERVIEW
========
This application helps University of Toronto students track their academic progress,
calculate GPAs, and plan future courses with comprehensive support for UofT's
grading system and special notations.

MAIN FEATURES
=============

1. OVERVIEW TAB
   - View cumulative GPA and total credits
   - See academic standing
   - Browse sessional GPAs

2. TRANSCRIPT TAB
   - Add, edit, and delete courses
   - Search and filter courses
   - Import/export data in multiple formats
   - Duplicate courses for easy data entry

3. GPA SIMULATOR
   - Plan future courses
   - Simulate different grade scenarios
   - Calculate what grades you need for target GPA

4. ANALYTICS
   - Grade distribution analysis
   - Subject performance breakdown
   - Personalized recommendations

5. PREREQUISITES
   - Look up course prerequisites
   - Validate prerequisite completion
   - Add course information to database

6. DEGREE PROGRESS
   - Track progress toward degree requirements
   - See completed and remaining courses
   - Monitor credit requirements

7. REPORTS & CHARTS
   - Generate visual reports and charts
   - GPA trend analysis
   - Course distribution analytics
   - Export charts and reports

8. DATA MANAGEMENT
   - Import from CSV
   - Export to CSV, Excel, or PDF
   - Save and load sessions
   - Automatic backups

9. SETTINGS
   - Customize appearance and behavior
   - Configure auto-save and backups
   - Import/export settings

GETTING STARTED
===============

1. Add your courses using the Transcript tab
2. Use the search and filter features to find specific courses
3. Check your GPA and academic standing in the Overview tab
4. Plan future courses using the GPA Simulator
5. Analyze your performance in the Analytics tab

KEYBOARD SHORTCUTS
==================
Ctrl+S: Quick save
Ctrl+O: Open/load session
Ctrl+E: Export data
Ctrl+F: Focus search box
F1: Show this guide

TIPS
====
- Use the duplicate feature for similar courses
- Set up auto-save to prevent data loss
- Create regular backups of your data
- Use the prerequisites tab to plan course sequences
- Check the degree progress tab to track graduation requirements

For more help, visit the application's GitHub repository or contact support.
        \"\"\"

        guide_text.insert(1.0, guide_content)
        guide_text.configure(state='disabled')

        guide_text.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

    def show_shortcuts(self):
        \"\"\"Show keyboard shortcuts\"\"\"
        shortcuts_window = tk.Toplevel(self.root)
        shortcuts_window.title(\"Keyboard Shortcuts\")
        shortcuts_window.geometry(\"400x300\")

        shortcuts_text = \"\"\"
KEYBOARD SHORTCUTS

General:
Ctrl+S        Quick save
Ctrl+O        Load session
Ctrl+E        Export data
Ctrl+N        Add new course
Ctrl+D        Duplicate course
Ctrl+Delete   Delete course
F1            Show user guide
F5            Refresh displays

Navigation:
Ctrl+1        Overview tab
Ctrl+2        Transcript tab
Ctrl+3        Simulator tab
Ctrl+4        Analytics tab
Ctrl+5        Prerequisites tab
Ctrl+6        Degree Progress tab
Ctrl+7        Reports tab
Ctrl+8        Data Management tab
Ctrl+9        Settings tab

Search & Filter:
Ctrl+F        Focus search box
Ctrl+Shift+F  Clear filters
Escape        Clear search

Data Entry:
Tab           Next field
Shift+Tab     Previous field
Enter         Save/OK
Escape        Cancel
        \"\"\"

        label = ttk.Label(shortcuts_window, text=shortcuts_text, font=('Courier', 10), justify='left')
        label.pack(padx=20, pady=20)

    def show_about(self):
        \"\"\"Show about dialog\"\"\"
        about_text = \"\"\"
UofT Academic Transcript Analyzer v3.0
Enhanced Edition

A comprehensive desktop application for University of Toronto
students to analyze academic transcripts, calculate GPAs,
and plan academic progress.

Features:
• Accurate UofT GPA calculations
• Complete special notations support
• Advanced analytics and reporting
• Course prerequisite tracking
• Degree progress monitoring
• Data visualization with charts
• Multiple export formats
• Auto-save and backup

Developed for UofT students by UofT students.

© 2024 - Licensed under MIT License
        \"\"\"

        messagebox.showinfo(\"About UofT Transcript Analyzer\", about_text)

    def check_updates(self):
        \"\"\"Check for application updates\"\"\"
        messagebox.showinfo(\"Check Updates\", \"You are running the latest version (v3.0).\\n\\nCheck GitHub for future updates.\")

    def load_sample_data(self):
        """Load sample data for demonstration"""
        sample_data = [
            {'term': 'Fall', 'year': 2023, 'course_code': 'AMS199H1', 'title': 'Razing the Roof and Tearing Down Monuments', 'weight': 0.5, 'mark': '80', 'grade': 'A-', 'notation': ''},
            {'term': 'Fall', 'year': 2023, 'course_code': 'MUN101H1', 'title': 'Global Innovation I', 'weight': 0.5, 'mark': '81', 'grade': 'A-', 'notation': ''},
            {'term': 'Fall', 'year': 2023, 'course_code': 'MUN195H1', 'title': 'Economics of Birth Death and Everything', 'weight': 0.5, 'mark': '86', 'grade': 'A', 'notation': ''},
            {'term': 'Fall', 'year': 2023, 'course_code': 'MUN198H1', 'title': 'Digital Technologies and Human Rights', 'weight': 0.5, 'mark': '82', 'grade': 'A-', 'notation': ''},
            {'term': 'Winter', 'year': 2024, 'course_code': 'MUN102H1', 'title': 'Global Innovation II', 'weight': 0.5, 'mark': '55', 'grade': 'D', 'notation': ''},
            {'term': 'Winter', 'year': 2024, 'course_code': 'MUN105Y1', 'title': 'Global Problem Solving', 'weight': 1.0, 'mark': '85', 'grade': 'A', 'notation': ''},
            {'term': 'Winter', 'year': 2024, 'course_code': 'MUN196H1', 'title': 'Global Politics of Surveillance', 'weight': 0.5, 'mark': '52', 'grade': 'D-', 'notation': ''},
            {'term': 'Winter', 'year': 2024, 'course_code': 'RLG107H1', 'title': 'Its the End of the World', 'weight': 0.5, 'mark': '77', 'grade': 'B+', 'notation': ''},
            {'term': 'Winter', 'year': 2024, 'course_code': 'SOC100H1', 'title': 'Intro to Soc-Soc Perspectives', 'weight': 0.5, 'mark': '', 'grade': '', 'notation': 'LWD'},
            {'term': 'Summer', 'year': 2024, 'course_code': 'ECO101H1', 'title': 'Principles of Microeconomics', 'weight': 0.5, 'mark': '20', 'grade': 'F', 'notation': ''},
            {'term': 'Summer', 'year': 2024, 'course_code': 'HIS103Y1', 'title': 'Strategy and Statecraft', 'weight': 1.0, 'mark': '74', 'grade': 'B', 'notation': ''},
            {'term': 'Fall', 'year': 2024, 'course_code': 'AMS310H1', 'title': 'US Democracy at a Crossroads', 'weight': 0.5, 'mark': '76', 'grade': 'B', 'notation': ''},
            {'term': 'Fall', 'year': 2024, 'course_code': 'ECO101H1', 'title': 'Principles of Microeconomics (Retake)', 'weight': 0.5, 'mark': '53', 'grade': 'D', 'notation': ''},
            {'term': 'Fall', 'year': 2024, 'course_code': 'POL218H1', 'title': 'State Society and Power', 'weight': 0.5, 'mark': '', 'grade': '', 'notation': 'CR'},
            {'term': 'Fall', 'year': 2024, 'course_code': 'STA220H1', 'title': 'Practice of Statistics I', 'weight': 0.5, 'mark': '50', 'grade': 'D-', 'notation': ''},
            {'term': 'Winter', 'year': 2025, 'course_code': 'CSC108H1', 'title': 'Intro to Computer Programming', 'weight': 0.5, 'mark': '19', 'grade': 'F', 'notation': ''},
            {'term': 'Winter', 'year': 2025, 'course_code': 'GGR274H1', 'title': 'Comp & Data Science - Social Sciences', 'weight': 0.5, 'mark': '70', 'grade': 'B-', 'notation': ''},
            {'term': 'Winter', 'year': 2025, 'course_code': 'MUN200H1', 'title': 'Understanding Global Controversies', 'weight': 0.5, 'mark': '75', 'grade': 'B', 'notation': ''},
            {'term': 'Winter', 'year': 2025, 'course_code': 'POL214H1', 'title': 'Canadian Government', 'weight': 0.5, 'mark': '66', 'grade': 'C', 'notation': ''},
            {'term': 'Summer', 'year': 2025, 'course_code': 'ECO102H1', 'title': 'Principles of Macroeconomics', 'weight': 0.5, 'mark': '51', 'grade': 'D-', 'notation': ''},
            {'term': 'Fall', 'year': 2025, 'course_code': 'GGR375H1', 'title': 'Introduction to Programming in GIS', 'weight': 0.5, 'mark': '', 'grade': '', 'notation': 'IPR'},
            {'term': 'Fall', 'year': 2025, 'course_code': 'POL208H1', 'title': 'Introduction to International Relations', 'weight': 0.5, 'mark': '', 'grade': '', 'notation': 'IPR'},
        ]
        
        self.transcript_data = sample_data
        self.update_displays()


class CourseDialog:
    def __init__(self, parent, title, all_grades, course_data=None, simulation_mode=False):
        self.result = None
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("500x400")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        self.all_grades = all_grades
        self.simulation_mode = simulation_mode
        
        # Initialize variables
        self.term_var = tk.StringVar(value=course_data.get('term', 'Fall') if course_data else 'Fall')
        self.year_var = tk.StringVar(value=str(course_data.get('year', 2025)) if course_data else '2025')
        self.course_code_var = tk.StringVar(value=course_data.get('course_code', '') if course_data else '')
        self.title_var = tk.StringVar(value=course_data.get('title', '') if course_data else '')
        self.weight_var = tk.StringVar(value=str(course_data.get('weight', 0.5)) if course_data else '0.5')
        self.mark_var = tk.StringVar(value=course_data.get('mark', '') if course_data else '')
        self.grade_var = tk.StringVar(value=course_data.get('grade', 'B') if course_data else 'B')
        self.notation_var = tk.StringVar(value=course_data.get('notation', '') if course_data else '')
        
        self.setup_dialog()
        
        # Wait for dialog to close
        self.dialog.wait_window()
    
    def setup_dialog(self):
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill='both', expand=True)
        
        # Course details
        row = 0
        
        # Term
        ttk.Label(main_frame, text="Term:").grid(row=row, column=0, sticky='w', pady=5)
        term_combo = ttk.Combobox(main_frame, textvariable=self.term_var, values=['Fall', 'Winter', 'Summer'], state='readonly')
        term_combo.grid(row=row, column=1, sticky='ew', padx=(10, 0), pady=5)
        
        # Year
        ttk.Label(main_frame, text="Year:").grid(row=row, column=2, sticky='w', padx=(20, 0), pady=5)
        year_entry = ttk.Entry(main_frame, textvariable=self.year_var, width=8)
        year_entry.grid(row=row, column=3, sticky='w', padx=(10, 0), pady=5)
        
        row += 1
        
        # Course Code
        ttk.Label(main_frame, text="Course Code:").grid(row=row, column=0, sticky='w', pady=5)
        code_entry = ttk.Entry(main_frame, textvariable=self.course_code_var)
        code_entry.grid(row=row, column=1, columnspan=3, sticky='ew', padx=(10, 0), pady=5)
        
        row += 1
        
        # Title
        ttk.Label(main_frame, text="Course Title:").grid(row=row, column=0, sticky='w', pady=5)
        title_entry = ttk.Entry(main_frame, textvariable=self.title_var)
        title_entry.grid(row=row, column=1, columnspan=3, sticky='ew', padx=(10, 0), pady=5)
        
        row += 1
        
        # Weight
        ttk.Label(main_frame, text="Weight (FCE):").grid(row=row, column=0, sticky='w', pady=5)
        weight_combo = ttk.Combobox(main_frame, textvariable=self.weight_var, 
                                  values=['0.5', '1.0'], state='readonly')
        weight_combo.grid(row=row, column=1, sticky='ew', padx=(10, 0), pady=5)
        
        # Mark (optional for simulation)
        ttk.Label(main_frame, text="Mark (%):").grid(row=row, column=2, sticky='w', padx=(20, 0), pady=5)
        mark_entry = ttk.Entry(main_frame, textvariable=self.mark_var, width=8)
        mark_entry.grid(row=row, column=3, sticky='w', padx=(10, 0), pady=5)
        
        row += 1
        
        # Grade selection
        ttk.Label(main_frame, text="Grade/Notation:").grid(row=row, column=0, sticky='w', pady=5)
        
        # Grade dropdown
        grade_frame = ttk.Frame(main_frame)
        grade_frame.grid(row=row, column=1, columnspan=3, sticky='ew', padx=(10, 0), pady=5)
        
        # Letter grades
        letter_grades = ['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'D-', 'F']
        grade_combo = ttk.Combobox(grade_frame, textvariable=self.grade_var, 
                                 values=letter_grades, state='readonly', width=10)
        grade_combo.pack(side='left')
        
        ttk.Label(grade_frame, text="OR").pack(side='left', padx=10)
        
        # Special notations
        special_notations = ['', 'CR', 'NCR', 'NC%', 'IPR', 'LWD', 'WDR', 'AEG', 'SDF', 'DNW', 'EXT', 'ADD', 'GWR', 'INC', 'NGA', 'XMP']
        notation_combo = ttk.Combobox(grade_frame, textvariable=self.notation_var, 
                                    values=special_notations, state='readonly', width=10)
        notation_combo.pack(side='left')
        
        row += 1
        
        # Info text
        if self.simulation_mode:
            info_text = "For simulation: Use expected grade or special notation (CR/NCR, etc.)"
        else:
            info_text = "Select either a letter grade OR a special notation, not both"
        
        info_label = ttk.Label(main_frame, text=info_text, font=('Arial', 9), foreground='gray')
        info_label.grid(row=row, column=0, columnspan=4, sticky='w', pady=10)
        
        row += 1
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, columnspan=4, pady=20)
        
        ttk.Button(button_frame, text="OK", command=self.ok_clicked).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.cancel_clicked).pack(side='left', padx=5)
        
        # Configure grid weights
        main_frame.columnconfigure(1, weight=1)
        main_frame.columnconfigure(3, weight=1)
        
        # Bind notation change to clear grade
        notation_combo.bind('<<ComboboxSelected>>', self.on_notation_change)
        grade_combo.bind('<<ComboboxSelected>>', self.on_grade_change)
    
    def on_notation_change(self, event):
        """Clear grade when notation is selected"""
        if self.notation_var.get():
            self.grade_var.set('')
    
    def on_grade_change(self, event):
        """Clear notation when grade is selected"""
        if self.grade_var.get():
            self.notation_var.set('')
    
    def ok_clicked(self):
        """Validate and save course data"""
        try:
            # Validate required fields
            if not self.course_code_var.get().strip():
                messagebox.showerror("Validation Error", "Course code is required.")
                return
            
            if not self.title_var.get().strip():
                messagebox.showerror("Validation Error", "Course title is required.")
                return
            
            # Validate year
            year = int(self.year_var.get())
            if year < 1900 or year > 2100:
                messagebox.showerror("Validation Error", "Please enter a valid year.")
                return
            
            # Validate weight
            weight = float(self.weight_var.get())
            if weight <= 0:
                messagebox.showerror("Validation Error", "Weight must be positive.")
                return
            
            # Validate grade/notation selection
            grade = self.grade_var.get()
            notation = self.notation_var.get()
            
            if not grade and not notation:
                messagebox.showerror("Validation Error", "Please select either a grade or notation.")
                return
            
            if grade and notation:
                messagebox.showerror("Validation Error", "Please select either grade OR notation, not both.")
                return
            
            # Create course data
            self.result = {
                'term': self.term_var.get(),
                'year': year,
                'course_code': self.course_code_var.get().strip(),
                'title': self.title_var.get().strip(),
                'weight': weight,
                'mark': self.mark_var.get().strip(),
                'grade': grade,
                'notation': notation
            }
            
            self.dialog.destroy()
            
        except ValueError as e:
            messagebox.showerror("Validation Error", f"Invalid input: {str(e)}")
    
    def cancel_clicked(self):
        """Cancel dialog"""
        self.dialog.destroy()


class CourseInfoDialog:
    \"\"\"Dialog for adding course information to the database\"\"\"
    def __init__(self, parent, course_code):
        self.result = None

        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f\"Add Course Information - {course_code}\")
        self.dialog.geometry(\"600x500\")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center the dialog
        self.dialog.geometry(\"+%d+%d\" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))

        self.course_code = course_code
        self.setup_dialog()

        # Wait for dialog to close
        self.dialog.wait_window()

    def setup_dialog(self):
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill='both', expand=True)

        # Course code (read-only)
        ttk.Label(main_frame, text=\"Course Code:\").grid(row=0, column=0, sticky='w', pady=5)
        ttk.Label(main_frame, text=self.course_code, font=('Arial', 10, 'bold')).grid(row=0, column=1, sticky='w', padx=10, pady=5)

        # Faculty
        ttk.Label(main_frame, text=\"Faculty:\").grid(row=1, column=0, sticky='w', pady=5)
        self.faculty_var = tk.StringVar(value=\"ARTSC\")
        faculty_combo = ttk.Combobox(main_frame, textvariable=self.faculty_var,
                                   values=[\"ARTSC\", \"ENGR\", \"MUSIC\", \"KINE\", \"UTM\", \"UTSC\"], width=20)
        faculty_combo.grid(row=1, column=1, sticky='ew', padx=10, pady=5)

        # Department
        ttk.Label(main_frame, text=\"Department:\").grid(row=2, column=0, sticky='w', pady=5)
        self.department_var = tk.StringVar()
        department_entry = ttk.Entry(main_frame, textvariable=self.department_var, width=30)
        department_entry.grid(row=2, column=1, sticky='ew', padx=10, pady=5)

        # Prerequisites
        ttk.Label(main_frame, text=\"Prerequisites:\").grid(row=3, column=0, sticky='nw', pady=5)
        self.prerequisites_var = tk.StringVar()
        prereq_entry = ttk.Entry(main_frame, textvariable=self.prerequisites_var, width=50)
        prereq_entry.grid(row=3, column=1, sticky='ew', padx=10, pady=5)
        ttk.Label(main_frame, text=\"(comma-separated course codes)\", font=('Arial', 8)).grid(row=4, column=1, sticky='w', padx=10)

        # Corequisites
        ttk.Label(main_frame, text=\"Corequisites:\").grid(row=5, column=0, sticky='nw', pady=5)
        self.corequisites_var = tk.StringVar()
        coreq_entry = ttk.Entry(main_frame, textvariable=self.corequisites_var, width=50)
        coreq_entry.grid(row=5, column=1, sticky='ew', padx=10, pady=5)

        # Exclusions
        ttk.Label(main_frame, text=\"Exclusions:\").grid(row=6, column=0, sticky='nw', pady=5)
        self.exclusions_var = tk.StringVar()
        exclusion_entry = ttk.Entry(main_frame, textvariable=self.exclusions_var, width=50)
        exclusion_entry.grid(row=6, column=1, sticky='ew', padx=10, pady=5)

        # Description
        ttk.Label(main_frame, text=\"Description:\").grid(row=7, column=0, sticky='nw', pady=5)
        self.description_text = tk.Text(main_frame, height=8, width=50)
        desc_scrollbar = ttk.Scrollbar(main_frame, orient='vertical', command=self.description_text.yview)
        self.description_text.configure(yscrollcommand=desc_scrollbar.set)

        self.description_text.grid(row=7, column=1, sticky='ew', padx=10, pady=5)
        desc_scrollbar.grid(row=7, column=2, sticky='ns', pady=5)

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=8, column=0, columnspan=3, pady=20)

        ttk.Button(button_frame, text=\"Save\", command=self.save_course_info).pack(side='left', padx=10)
        ttk.Button(button_frame, text=\"Cancel\", command=self.cancel_dialog).pack(side='left', padx=10)

        # Configure grid weights
        main_frame.columnconfigure(1, weight=1)

    def save_course_info(self):
        \"\"\"Save course information\"\"\"
        self.result = {
            'course_code': self.course_code,
            'faculty': self.faculty_var.get(),
            'department': self.department_var.get().strip(),
            'prerequisites': self.prerequisites_var.get().strip(),
            'corequisites': self.corequisites_var.get().strip(),
            'exclusions': self.exclusions_var.get().strip(),
            'description': self.description_text.get(1.0, tk.END).strip()
        }
        self.dialog.destroy()

    def cancel_dialog(self):
        \"\"\"Cancel dialog\"\"\"
        self.dialog.destroy()


def main():
    root = tk.Tk()
    app = UofTTranscriptAnalyzer(root)
    root.mainloop()


if __name__ == "__main__":
    main()
