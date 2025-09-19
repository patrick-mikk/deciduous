import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import csv
import json
from datetime import datetime
from collections import defaultdict
import os

class UofTTranscriptAnalyzer:
    def __init__(self, root):
        self.root = root
        self.root.title("UofT Academic Transcript Analyzer v2.0")
        self.root.geometry("1200x800")
        self.root.configure(bg='#f0f0f0')
        
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
        
        self.setup_gui()
        self.load_sample_data()
        
    def setup_gui(self):
        # Create main notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create tabs
        self.setup_overview_tab()
        self.setup_transcript_tab()
        self.setup_simulation_tab()
        self.setup_analytics_tab()
        self.setup_data_tab()
        
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
        
        ttk.Button(controls_frame, text="Add Course", command=self.add_course_dialog).pack(side='left', padx=5)
        ttk.Button(controls_frame, text="Edit Course", command=self.edit_course).pack(side='left', padx=5)
        ttk.Button(controls_frame, text="Delete Course", command=self.delete_course).pack(side='left', padx=5)
        ttk.Button(controls_frame, text="Import CSV", command=self.import_csv).pack(side='left', padx=5)
        ttk.Button(controls_frame, text="Export CSV", command=self.export_csv).pack(side='left', padx=5)
        
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
                    break
            
            self.update_displays()
    
    def add_simulation_course(self):
        """Add a course to simulation"""
        dialog = CourseDialog(self.root, "Add Simulation Course", self.ALL_GRADES, simulation_mode=True)
        if dialog.result:
            self.simulation_courses.append(dialog.result)
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
                break
        
        self.update_simulation_display()
    
    def clear_simulation(self):
        """Clear all simulation courses"""
        if messagebox.askyesno("Confirm Clear", "Clear all simulation courses?"):
            self.simulation_courses = []
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
                    self.update_displays()
                    messagebox.showinfo("Success", "Session loaded successfully.")
                    
            except Exception as e:
                messagebox.showerror("Load Error", f"Error loading session: {str(e)}")
    
    def clear_all_data(self):
        """Clear all data"""
        if messagebox.askyesno("Confirm Clear", "This will delete all transcript and simulation data. Continue?"):
            self.transcript_data = []
            self.simulation_courses = []
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


def main():
    root = tk.Tk()
    app = UofTTranscriptAnalyzer(root)
    root.mainloop()


if __name__ == "__main__":
    main()
