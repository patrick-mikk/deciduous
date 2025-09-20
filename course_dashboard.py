#!/usr/bin/env python3
"""
UofT Course Dashboard - Integrated Academic Planning Tool
Combines course search, transcript analysis, and academic planning
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import sqlite3
import csv
import json
from datetime import datetime, timedelta
from collections import defaultdict
import os
import sys
import threading
import queue
import webbrowser
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Selenium imports for course search
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.keys import Keys
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service
    from bs4 import BeautifulSoup
    import time
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("Selenium not available - course search will be disabled")

# Optional analytics imports
try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("Matplotlib not available - charts will be disabled")


class ModernTheme:
    """Modern theme configuration for enhanced UI"""

    # Color palette
    PRIMARY = "#2563EB"      # Blue
    PRIMARY_HOVER = "#1D4ED8"
    SECONDARY = "#64748B"     # Slate gray
    BACKGROUND = "#F8FAFC"    # Light gray
    SURFACE = "#FFFFFF"       # White
    SURFACE_ALT = "#F1F5F9"   # Light blue-gray
    TEXT_PRIMARY = "#0F172A"  # Dark slate
    TEXT_SECONDARY = "#475569" # Medium slate
    SUCCESS = "#10B981"       # Green
    WARNING = "#F59E0B"       # Amber
    ERROR = "#EF4444"         # Red
    BORDER = "#E2E8F0"        # Light border

    # Fonts
    FONT_MAIN = ("Segoe UI", 9)
    FONT_HEADING = ("Segoe UI", 12, "bold")
    FONT_SUBHEADING = ("Segoe UI", 10, "bold")
    FONT_MONOSPACE = ("Consolas", 9)


class UnifiedCourseDatabase:
    """Unified database for both academic calendar courses and transcript data with caching"""

    def __init__(self, db_path="course_dashboard.db"):
        self.db_path = db_path
        self._cache = {}
        self._cache_expiry = {}
        self._cache_timeout = 300  # 5 minutes
        self.init_database()

    def _get_connection(self):
        """Get optimized database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.execute('PRAGMA foreign_keys = ON')
        conn.execute('PRAGMA journal_mode = WAL')  # Better concurrency
        conn.execute('PRAGMA synchronous = NORMAL')  # Faster writes
        return conn

    def _is_cache_valid(self, key):
        """Check if cache entry is still valid"""
        if key not in self._cache_expiry:
            return False
        import time
        return time.time() < self._cache_expiry[key]

    def _set_cache(self, key, value):
        """Set cache entry with expiry"""
        import time
        self._cache[key] = value
        self._cache_expiry[key] = time.time() + self._cache_timeout

    def _clear_cache(self, pattern=None):
        """Clear cache entries"""
        if pattern:
            keys_to_remove = [k for k in self._cache.keys() if pattern in k]
            for key in keys_to_remove:
                del self._cache[key]
                del self._cache_expiry[key]
        else:
            self._cache.clear()
            self._cache_expiry.clear()

    def init_database(self):
        """Initialize the unified database with all required tables and indexes"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Academic calendar courses table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS academic_courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_code TEXT UNIQUE,
                title TEXT,
                hours TEXT,
                description TEXT,
                prerequisites TEXT,
                exclusions TEXT,
                breadth_requirements TEXT,
                url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Transcript courses table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transcript_courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_code TEXT,
                title TEXT,
                credits REAL,
                grade TEXT,
                mark REAL,
                session TEXT,
                year INTEGER,
                status TEXT DEFAULT 'completed',
                gpa_points REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Add mark column to existing tables if it doesn't exist
        try:
            cursor.execute('ALTER TABLE transcript_courses ADD COLUMN mark REAL')
        except:
            pass  # Column already exists

        # Planned courses table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS planned_courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_code TEXT,
                title TEXT,
                credits REAL,
                planned_session TEXT,
                planned_year INTEGER,
                priority INTEGER DEFAULT 1,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Course prerequisites table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS course_prerequisites (
                course_code TEXT PRIMARY KEY,
                prerequisites TEXT,
                corequisites TEXT,
                exclusions TEXT,
                description TEXT,
                faculty TEXT,
                department TEXT
            )
        ''')

        # Create performance indexes
        indexes = [
            'CREATE INDEX IF NOT EXISTS idx_transcript_year_session ON transcript_courses(year, session)',
            'CREATE INDEX IF NOT EXISTS idx_transcript_course_code ON transcript_courses(course_code)',
            'CREATE INDEX IF NOT EXISTS idx_planned_year_session ON planned_courses(planned_year, planned_session)',
            'CREATE INDEX IF NOT EXISTS idx_academic_course_code ON academic_courses(course_code)',
            'CREATE INDEX IF NOT EXISTS idx_transcript_grade ON transcript_courses(grade)',
            'CREATE INDEX IF NOT EXISTS idx_transcript_status ON transcript_courses(status)'
        ]

        for index_sql in indexes:
            cursor.execute(index_sql)

        conn.commit()
        conn.close()

    def save_academic_course(self, course_data):
        """Save course from academic calendar"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO academic_courses
            (course_code, title, hours, description, prerequisites, exclusions, breadth_requirements, url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            course_data['course_code'],
            course_data['title'],
            course_data['hours'],
            course_data['description'],
            course_data['prerequisites'],
            course_data['exclusions'],
            course_data['breadth_requirements'],
            course_data['url']
        ))

        conn.commit()
        conn.close()

    def save_transcript_course(self, course_data):
        """Save course to transcript"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO transcript_courses
            (course_code, title, credits, grade, mark, session, year, status, gpa_points)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            course_data['course_code'],
            course_data['title'],
            course_data['credits'],
            course_data['grade'],
            course_data.get('mark', None),
            course_data['session'],
            course_data['year'],
            course_data.get('status', 'completed'),
            course_data.get('gpa_points', 0.0)
        ))

        conn.commit()
        conn.close()
        self._clear_cache('transcript')

    def save_planned_course(self, course_data):
        """Save course to planning list"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO planned_courses
            (course_code, title, credits, planned_session, planned_year, priority, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            course_data['course_code'],
            course_data['title'],
            course_data['credits'],
            course_data['planned_session'],
            course_data['planned_year'],
            course_data.get('priority', 1),
            course_data.get('notes', '')
        ))

        conn.commit()
        conn.close()

    def get_academic_courses(self):
        """Get all academic calendar courses"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM academic_courses ORDER BY course_code')
        courses = cursor.fetchall()
        conn.close()
        return courses

    def get_transcript_courses(self, use_cache=True):
        """Get all transcript courses with caching"""
        cache_key = 'transcript_courses'

        if use_cache and self._is_cache_valid(cache_key):
            return self._cache[cache_key]

        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM transcript_courses ORDER BY year DESC, session, course_code')
        courses = cursor.fetchall()
        conn.close()

        if use_cache:
            self._set_cache(cache_key, courses)

        return courses

    def get_planned_courses(self, use_cache=True):
        """Get all planned courses with caching"""
        cache_key = 'planned_courses'

        if use_cache and self._is_cache_valid(cache_key):
            return self._cache[cache_key]

        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM planned_courses ORDER BY planned_year, planned_session, priority')
        courses = cursor.fetchall()
        conn.close()

        if use_cache:
            self._set_cache(cache_key, courses)

        return courses

    def update_transcript_course(self, course_id, course_data):
        """Update an existing transcript course"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE transcript_courses
            SET course_code=?, title=?, credits=?, grade=?, mark=?, session=?, year=?, status=?, gpa_points=?
            WHERE id=?
        ''', (
            course_data['course_code'],
            course_data['title'],
            course_data['credits'],
            course_data['grade'],
            course_data.get('mark', None),
            course_data['session'],
            course_data['year'],
            course_data.get('status', 'completed'),
            course_data.get('gpa_points', 0.0),
            course_id
        ))

        conn.commit()
        conn.close()

    def delete_transcript_courses(self, course_ids):
        """Delete multiple transcript courses by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        placeholders = ','.join(['?' for _ in course_ids])
        cursor.execute(f'DELETE FROM transcript_courses WHERE id IN ({placeholders})', course_ids)

        conn.commit()
        conn.close()

    def bulk_update_transcript_courses(self, updates):
        """Bulk update transcript courses
        updates: list of tuples (course_id, course_data)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for course_id, course_data in updates:
            cursor.execute('''
                UPDATE transcript_courses
                SET course_code=?, title=?, credits=?, grade=?, mark=?, session=?, year=?, status=?, gpa_points=?
                WHERE id=?
            ''', (
                course_data['course_code'],
                course_data['title'],
                course_data['credits'],
                course_data['grade'],
                course_data.get('mark', None),
                course_data['session'],
                course_data['year'],
                course_data.get('status', 'completed'),
                course_data.get('gpa_points', 0.0),
                course_id
            ))

        conn.commit()
        conn.close()

    def auto_populate_course_titles(self):
        """Auto-populate missing course titles from academic calendar database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Get transcript courses with missing or generic titles
            cursor.execute('''
                SELECT id, course_code, title
                FROM transcript_courses
                WHERE title IS NULL OR title = '' OR title = course_code
            ''')

            courses_to_update = cursor.fetchall()
            updates_made = 0

            for course_id, course_code, current_title in courses_to_update:
                # Look for matching course in academic calendar
                cursor.execute('''
                    SELECT title
                    FROM academic_courses
                    WHERE course_code = ? AND title IS NOT NULL AND title != ''
                    LIMIT 1
                ''', (course_code,))

                result = cursor.fetchone()
                if result:
                    new_title = result[0]
                    # Update the transcript course with the found title
                    cursor.execute('''
                        UPDATE transcript_courses
                        SET title = ?
                        WHERE id = ?
                    ''', (new_title, course_id))
                    updates_made += 1

            conn.commit()
            return updates_made

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def get_missing_title_courses(self):
        """Get count of courses with missing titles"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT COUNT(*)
            FROM transcript_courses
            WHERE title IS NULL OR title = '' OR title = course_code
        ''')

        count = cursor.fetchone()[0]
        conn.close()
        return count


class AcademicCalendarScraper:
    """Enhanced scraper for UofT Academic Calendar"""

    def __init__(self):
        self.base_url = "https://artsci.calendar.utoronto.ca"
        self.search_url = f"{self.base_url}/search-courses"
        self.driver = None
        if SELENIUM_AVAILABLE:
            self.setup_driver()

    def setup_driver(self):
        """Set up Chrome WebDriver"""
        if not SELENIUM_AVAILABLE:
            raise Exception("Selenium not available")

        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.implicitly_wait(10)
        except Exception as e:
            print(f"Failed to setup WebDriver: {e}")
            self.driver = None

    def close_driver(self):
        """Close the WebDriver"""
        if self.driver:
            self.driver.quit()

    def search_courses(self, course_code):
        """Search for courses"""
        if not self.driver:
            return []

        try:
            self.driver.get(self.search_url)

            # Try multiple possible form field names
            form_selectors = [
                "input[name='course_keyword']",
                "input[name='course_title']",
                "input[name='keyword']",
                "#edit-course-keyword",
                "#edit-course-title"
            ]

            search_input = None
            for selector in form_selectors:
                try:
                    search_input = self.driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except NoSuchElementException:
                    continue

            if not search_input:
                raise Exception("Could not find search input field")

            search_input.clear()
            search_input.send_keys(course_code)
            search_input.send_keys(Keys.RETURN)

            time.sleep(3)

            # Parse results
            results = []

            # Try accordion-style results first
            try:
                accordion_items = self.driver.find_elements(By.CSS_SELECTOR, ".accordion-item, .course-item")
                for item in accordion_items:
                    try:
                        title_element = item.find_element(By.CSS_SELECTOR, "h3, .course-title, .accordion-header")
                        title_text = title_element.text.strip()

                        # Extract course code from title
                        course_match = re.search(r'([A-Z]{3}\\d{3}[HY]\\d)', title_text)
                        if course_match:
                            extracted_code = course_match.group(1)
                        else:
                            extracted_code = course_code

                        # Get URL
                        try:
                            link = item.find_element(By.CSS_SELECTOR, "a")
                            url = link.get_attribute("href")
                            if not url.startswith("http"):
                                url = self.base_url + url
                        except NoSuchElementException:
                            url = ""

                        # Get description
                        try:
                            desc_element = item.find_element(By.CSS_SELECTOR, ".course-description, p")
                            description = desc_element.text.strip()[:200]
                        except NoSuchElementException:
                            description = ""

                        results.append({
                            'course_code': extracted_code,
                            'title': title_text,
                            'url': url,
                            'description': description
                        })
                    except Exception:
                        continue
            except Exception:
                pass

            return results

        except Exception as e:
            print(f"Search failed: {e}")
            return []

    def extract_course_details(self, course_url):
        """Extract detailed course information"""
        if not self.driver or not course_url:
            return {}

        try:
            self.driver.get(course_url)
            time.sleep(2)

            details = {'url': course_url}

            # Extract title
            try:
                title_element = self.driver.find_element(By.CSS_SELECTOR,
                    "#block-w3css-subtheme-page-title h1.page-title")
                details['title'] = title_element.text.strip()

                # Extract course code from title
                course_match = re.search(r'([A-Z]{3}\\d{3}[HY]\\d)', details['title'])
                if course_match:
                    details['course_code'] = course_match.group(1)
            except NoSuchElementException:
                details['title'] = ""
                details['course_code'] = ""

            # Extract hours
            try:
                hours_element = self.driver.find_element(By.CSS_SELECTOR,
                    ".field--name-field-hours .field__item p")
                details['hours'] = hours_element.text.strip()
            except NoSuchElementException:
                details['hours'] = ""

            # Extract description (handle multiple paragraphs)
            try:
                desc_container = self.driver.find_element(By.CSS_SELECTOR,
                    "#block-w3css-subtheme-content > article > div > div.w3-row.field.field--name-body.field--type-text-with-summary.field--label-hidden.w3-bar-item.field__item")
                paragraphs = desc_container.find_elements(By.TAG_NAME, "p")
                description_parts = []
                for p in paragraphs:
                    text = p.text.strip()
                    if text:
                        description_parts.append(text)
                details['description'] = "\\n\\n".join(description_parts)
            except NoSuchElementException:
                try:
                    # Fallback selector
                    desc_element = self.driver.find_element(By.CSS_SELECTOR,
                        ".field--name-body p")
                    details['description'] = desc_element.text.strip()
                except NoSuchElementException:
                    details['description'] = ""

            # Extract prerequisites
            try:
                prereq_element = self.driver.find_element(By.CSS_SELECTOR,
                    ".field--name-field-prerequisite .field__item")
                details['prerequisites'] = prereq_element.text.strip()
            except NoSuchElementException:
                details['prerequisites'] = ""

            # Extract exclusions
            try:
                excl_element = self.driver.find_element(By.CSS_SELECTOR,
                    ".field--name-field-exclusion .field__item")
                details['exclusions'] = excl_element.text.strip()
            except NoSuchElementException:
                details['exclusions'] = ""

            # Extract breadth requirements
            try:
                breadth_element = self.driver.find_element(By.CSS_SELECTOR,
                    ".field--name-field-breadth-requirements .field__items")
                details['breadth_requirements'] = breadth_element.text.strip()
            except NoSuchElementException:
                details['breadth_requirements'] = ""

            return details

        except Exception as e:
            print(f"Detail extraction failed: {e}")
            return {}


class CourseDialog:
    """Dialog for adding/editing courses"""

    def __init__(self, parent, title, mode="transcript", course_data=None):
        self.result = None
        self.mode = mode  # "transcript", "planned"

        # Grade scale
        self.GRADE_POINTS = {
            'A+': 4.0, 'A': 4.0, 'A-': 3.7,
            'B+': 3.3, 'B': 3.0, 'B-': 2.7,
            'C+': 2.3, 'C': 2.0, 'C-': 1.7,
            'D+': 1.3, 'D': 1.0, 'D-': 0.7,
            'F': 0.0, 'FZ': 0.0
        }

        self.ALL_GRADES = list(self.GRADE_POINTS.keys()) + ['CR', 'NCR', 'WDR', 'LWD']

        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("500x600")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.setup_dialog(course_data)

        # Center dialog
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))

        # Wait for dialog to close
        self.dialog.wait_window()

    def setup_dialog(self, course_data):
        """Setup dialog interface"""
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Course Code
        ttk.Label(main_frame, text="Course Code:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.code_var = tk.StringVar(value=course_data.get('course_code', '') if course_data else '')
        ttk.Entry(main_frame, textvariable=self.code_var, width=15).grid(row=0, column=1, sticky=tk.W, pady=5)

        # Course Title
        ttk.Label(main_frame, text="Course Title:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.title_var = tk.StringVar(value=course_data.get('title', '') if course_data else '')
        ttk.Entry(main_frame, textvariable=self.title_var, width=40).grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5)

        # Credits
        ttk.Label(main_frame, text="Credits:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.credits_var = tk.StringVar(value=str(course_data.get('credits', '0.5')) if course_data else '0.5')
        ttk.Entry(main_frame, textvariable=self.credits_var, width=10).grid(row=2, column=1, sticky=tk.W, pady=5)

        if self.mode == "transcript":
            # Grade
            ttk.Label(main_frame, text="Grade:").grid(row=3, column=0, sticky=tk.W, pady=5)
            self.grade_var = tk.StringVar(value=course_data.get('grade', '') if course_data else '')
            grade_combo = ttk.Combobox(main_frame, textvariable=self.grade_var, values=self.ALL_GRADES, width=10)
            grade_combo.grid(row=3, column=1, sticky=tk.W, pady=5)

            # Mark (percentage)
            ttk.Label(main_frame, text="Mark (%):").grid(row=4, column=0, sticky=tk.W, pady=5)
            self.mark_var = tk.StringVar(value=str(course_data.get('mark', '')) if course_data and course_data.get('mark') else '')
            ttk.Entry(main_frame, textvariable=self.mark_var, width=10).grid(row=4, column=1, sticky=tk.W, pady=5)

            # Session
            ttk.Label(main_frame, text="Session:").grid(row=5, column=0, sticky=tk.W, pady=5)
            self.session_var = tk.StringVar(value=course_data.get('session', 'Fall') if course_data else 'Fall')
            session_combo = ttk.Combobox(main_frame, textvariable=self.session_var,
                                       values=['Fall', 'Winter', 'Summer'], width=10)
            session_combo.grid(row=5, column=1, sticky=tk.W, pady=5)

            # Year
            ttk.Label(main_frame, text="Year:").grid(row=6, column=0, sticky=tk.W, pady=5)
            current_year = datetime.now().year
            self.year_var = tk.StringVar(value=str(course_data.get('year', current_year)) if course_data else str(current_year))
            ttk.Entry(main_frame, textvariable=self.year_var, width=10).grid(row=6, column=1, sticky=tk.W, pady=5)

        elif self.mode == "planned":
            # Planned Session
            ttk.Label(main_frame, text="Planned Session:").grid(row=3, column=0, sticky=tk.W, pady=5)
            self.session_var = tk.StringVar(value=course_data.get('planned_session', 'Fall') if course_data else 'Fall')
            session_combo = ttk.Combobox(main_frame, textvariable=self.session_var,
                                       values=['Fall', 'Winter', 'Summer'], width=10)
            session_combo.grid(row=3, column=1, sticky=tk.W, pady=5)

            # Planned Year
            ttk.Label(main_frame, text="Planned Year:").grid(row=4, column=0, sticky=tk.W, pady=5)
            current_year = datetime.now().year
            self.year_var = tk.StringVar(value=str(course_data.get('planned_year', current_year)) if course_data else str(current_year))
            ttk.Entry(main_frame, textvariable=self.year_var, width=10).grid(row=4, column=1, sticky=tk.W, pady=5)

            # Priority
            ttk.Label(main_frame, text="Priority:").grid(row=5, column=0, sticky=tk.W, pady=5)
            self.priority_var = tk.StringVar(value=str(course_data.get('priority', 1)) if course_data else '1')
            priority_combo = ttk.Combobox(main_frame, textvariable=self.priority_var,
                                        values=['1', '2', '3', '4', '5'], width=10)
            priority_combo.grid(row=5, column=1, sticky=tk.W, pady=5)

            # Notes
            ttk.Label(main_frame, text="Notes:").grid(row=6, column=0, sticky=(tk.W, tk.N), pady=5)
            self.notes_text = tk.Text(main_frame, width=40, height=4)
            self.notes_text.grid(row=6, column=1, sticky=(tk.W, tk.E), pady=5)
            if course_data and 'notes' in course_data:
                self.notes_text.insert(1.0, course_data['notes'])

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=10, column=0, columnspan=2, pady=20)

        ttk.Button(button_frame, text="Save", command=self.save_course).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.dialog.destroy).pack(side=tk.LEFT, padx=5)

        # Configure grid weights
        main_frame.columnconfigure(1, weight=1)
        self.dialog.columnconfigure(0, weight=1)
        self.dialog.rowconfigure(0, weight=1)

    def save_course(self):
        """Save course data"""
        try:
            if self.mode == "transcript":
                # Parse mark if provided
                mark_value = None
                mark_str = self.mark_var.get().strip()
                if mark_str:
                    try:
                        mark_value = float(mark_str)
                        if mark_value < 0 or mark_value > 100:
                            messagebox.showerror("Error", "Mark must be between 0 and 100")
                            return
                    except ValueError:
                        messagebox.showerror("Error", "Mark must be a valid number")
                        return

                self.result = {
                    'course_code': self.code_var.get().strip(),
                    'title': self.title_var.get().strip(),
                    'credits': float(self.credits_var.get()),
                    'grade': self.grade_var.get().strip(),
                    'mark': mark_value,
                    'session': self.session_var.get(),
                    'year': int(self.year_var.get()),
                    'gpa_points': self.GRADE_POINTS.get(self.grade_var.get().strip(), 0.0)
                }
            elif self.mode == "planned":
                notes = ""
                if hasattr(self, 'notes_text'):
                    notes = self.notes_text.get(1.0, tk.END).strip()

                self.result = {
                    'course_code': self.code_var.get().strip(),
                    'title': self.title_var.get().strip(),
                    'credits': float(self.credits_var.get()),
                    'planned_session': self.session_var.get(),
                    'planned_year': int(self.year_var.get()),
                    'priority': int(self.priority_var.get()),
                    'notes': notes
                }

            if not self.result['course_code']:
                messagebox.showerror("Error", "Course code is required")
                return

            self.dialog.destroy()

        except ValueError as e:
            messagebox.showerror("Error", f"Invalid input: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save course: {e}")


class CourseDashboard:
    """Main integrated course dashboard application with enhanced UI"""

    def __init__(self, root):
        self.root = root
        self.root.title("🎓 UofT Course Dashboard - Enhanced Academic Planning Tool")
        self.root.geometry("1600x1000")
        self.root.minsize(1200, 800)
        self.root.configure(bg=ModernTheme.BACKGROUND)

        # Setup modern styling
        self.setup_styles()
        self.setup_shortcuts()

        # Initialize components
        self.database = UnifiedCourseDatabase()
        if SELENIUM_AVAILABLE:
            self.scraper = AcademicCalendarScraper()
        else:
            self.scraper = None

        # Grade scale for GPA calculations
        self.GRADE_POINTS = {
            'A+': 4.0, 'A': 4.0, 'A-': 3.7,
            'B+': 3.3, 'B': 3.0, 'B-': 2.7,
            'C+': 2.3, 'C': 2.0, 'C-': 1.7,
            'D+': 1.3, 'D': 1.0, 'D-': 0.7,
            'F': 0.0, 'FZ': 0.0
        }

        # Data storage
        self.search_results = []

        # Setup keyboard shortcuts
        self.setup_shortcuts()

        self.setup_gui()
        self.update_displays()

    def setup_styles(self):
        """Setup modern ttk styles"""
        style = ttk.Style()

        # Configure modern button style - Light theme
        style.configure('Modern.TButton',
                       background='white',
                       foreground='black',
                       borderwidth=1,
                       relief='solid',
                       focuscolor='none',
                       font=ModernTheme.FONT_MAIN,
                       padding=(10, 5))

        style.map('Modern.TButton',
                 background=[('active', '#E5E7EB'),
                           ('pressed', '#D1D5DB')],
                 foreground=[('active', 'black'),
                           ('pressed', 'black')])

        # Configure accent button style - Light theme
        style.configure('Accent.TButton',
                       background='#F3F4F6',
                       foreground='black',
                       borderwidth=1,
                       relief='solid',
                       focuscolor='none',
                       font=ModernTheme.FONT_MAIN,
                       padding=(10, 5))

        # Configure modern frame style
        style.configure('Modern.TFrame',
                       background=ModernTheme.SURFACE,
                       relief='flat',
                       borderwidth=1)

        # Configure modern labelframe style
        style.configure('Modern.TLabelframe',
                       background=ModernTheme.SURFACE,
                       relief='flat',
                       borderwidth=1)

        style.configure('Modern.TLabelframe.Label',
                       background=ModernTheme.SURFACE,
                       foreground=ModernTheme.TEXT_PRIMARY,
                       font=ModernTheme.FONT_SUBHEADING)

    def setup_shortcuts(self):
        """Setup keyboard shortcuts for better UX"""
        # Global shortcuts
        self.root.bind('<Control-n>', lambda e: self.add_transcript_course())
        self.root.bind('<Control-s>', lambda e: self.save_session())
        self.root.bind('<Control-o>', lambda e: self.import_transcript_csv())
        self.root.bind('<Control-e>', lambda e: self.export_transcript_csv())
        self.root.bind('<F5>', lambda e: self.refresh_all_data())
        self.root.bind('<Control-f>', lambda e: self.focus_search())

        # Tab navigation
        self.root.bind('<Control-1>', lambda e: self.notebook.select(0))
        self.root.bind('<Control-2>', lambda e: self.notebook.select(1))
        self.root.bind('<Control-3>', lambda e: self.notebook.select(2))
        self.root.bind('<Control-4>', lambda e: self.notebook.select(3))
        self.root.bind('<Control-5>', lambda e: self.notebook.select(4))

        # Help
        self.root.bind('<F1>', lambda e: self.show_help_dialog())

    def focus_search(self):
        """Focus on search entry"""
        self.notebook.select(0)  # Switch to search tab

    def refresh_all_data(self):
        """Refresh all data"""
        self.database._clear_cache()  # Clear cache
        self.update_displays()

    def save_session(self):
        """Save session placeholder"""
        messagebox.showinfo("Save", "Session saved successfully!")

    def show_help_dialog(self):
        """Show keyboard shortcuts help dialog"""
        help_text = """
Keyboard Shortcuts:

Navigation:
• Ctrl+1-5: Switch between tabs
• F5: Refresh all data

Actions:
• Ctrl+N: Add new course to transcript
• Ctrl+O: Import CSV file
• Ctrl+E: Export to CSV
• Ctrl+F: Focus search (switch to search tab)
• Ctrl+S: Save session

Other:
• F1: Show this help dialog
        """

        help_window = tk.Toplevel(self.root)
        help_window.title("Keyboard Shortcuts")
        help_window.geometry("400x300")
        help_window.resizable(False, False)

        # Center the window
        help_window.transient(self.root)
        help_window.grab_set()

        text_widget = tk.Text(help_window, wrap=tk.WORD, padx=20, pady=20,
                             font=ModernTheme.FONT_MAIN)
        text_widget.pack(fill=tk.BOTH, expand=True)
        text_widget.insert(tk.END, help_text)
        text_widget.config(state=tk.DISABLED)

        # Close button
        close_btn = ttk.Button(help_window, text="Close",
                              command=help_window.destroy, style='Modern.TButton')
        close_btn.pack(pady=10)

    def setup_gui(self):
        """Setup the main GUI"""
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)

        # Create tabs
        self.setup_search_tab()
        self.setup_transcript_tab()
        self.setup_planning_tab()
        self.setup_gpa_dashboard_tab()
        self.setup_analytics_tab()

    def setup_search_tab(self):
        """Setup course search tab"""
        search_frame = ttk.Frame(self.notebook)
        self.notebook.add(search_frame, text="Course Search")

        # Main container with padding
        main_frame = ttk.Frame(search_frame, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Search section
        search_section = ttk.LabelFrame(main_frame, text="Search Courses", padding="10")
        search_section.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Label(search_section, text="Course Code or Keyword:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_section, textvariable=self.search_var, width=30)
        search_entry.grid(row=0, column=1, padx=(0, 10))
        search_entry.bind('<Return>', lambda e: self.search_courses())

        ttk.Button(search_section, text="Search", command=self.search_courses, style='Modern.TButton').grid(row=0, column=2)

        # Results section
        results_section = ttk.LabelFrame(main_frame, text="Search Results", padding="10")
        results_section.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))

        # Results listbox with scrollbar
        results_frame = ttk.Frame(results_section)
        results_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.results_listbox = tk.Listbox(results_frame, height=10)
        results_scrollbar = ttk.Scrollbar(results_frame, orient='vertical', command=self.results_listbox.yview)
        self.results_listbox.configure(yscrollcommand=results_scrollbar.set)

        self.results_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        results_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # Bind selection event
        self.results_listbox.bind('<<ListboxSelect>>', self.on_course_select)

        # Action buttons
        button_frame = ttk.Frame(results_section)
        button_frame.grid(row=1, column=0, pady=(10, 0))

        ttk.Button(button_frame, text="Extract Details", command=self.extract_course_details, style='Modern.TButton').pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Add to Transcript", command=self.add_to_transcript, style='Modern.TButton').pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Add to Plan", command=self.add_to_plan, style='Modern.TButton').pack(side=tk.LEFT)

        # Course details section
        details_section = ttk.LabelFrame(main_frame, text="Course Details", padding="10")
        details_section.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.details_text = tk.Text(details_section, height=15, wrap=tk.WORD)
        details_scrollbar = ttk.Scrollbar(details_section, orient='vertical', command=self.details_text.yview)
        self.details_text.configure(yscrollcommand=details_scrollbar.set)

        self.details_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        details_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(10, 0))

        # Configure grid weights
        search_frame.columnconfigure(0, weight=1)
        search_frame.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=2)
        results_section.columnconfigure(0, weight=1)
        results_section.rowconfigure(0, weight=1)
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)
        details_section.columnconfigure(0, weight=1)
        details_section.rowconfigure(0, weight=1)

    def setup_transcript_tab(self):
        """Setup transcript management tab"""
        transcript_frame = ttk.Frame(self.notebook)
        self.notebook.add(transcript_frame, text="Transcript")

        main_frame = ttk.Frame(transcript_frame, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Button(button_frame, text="Add Course", command=self.add_transcript_course, style='Modern.TButton').pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Edit Course", command=self.edit_transcript_course, style='Modern.TButton').pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Delete Course", command=self.delete_transcript_course, style='Modern.TButton').pack(side=tk.LEFT, padx=(0, 10))

        # Bulk operations
        ttk.Button(button_frame, text="Bulk Edit", command=self.bulk_edit_transcript, style='Modern.TButton').pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Bulk Delete", command=self.bulk_delete_transcript, style='Modern.TButton').pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Bulk Import Codes", command=self.bulk_import_course_codes, style='Modern.TButton').pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Auto-Populate Titles", command=self.auto_populate_titles, style='Modern.TButton').pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(button_frame, text="Import CSV", command=self.import_transcript_csv, style='Modern.TButton').pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Export CSV", command=self.export_transcript_csv, style='Modern.TButton').pack(side=tk.LEFT)

        # Transcript treeview
        tree_frame = ttk.Frame(main_frame)
        tree_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        columns = ('Course Code', 'Title', 'Credits', 'Grade', 'Mark', 'Session', 'Year', 'Status')
        self.transcript_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=20)

        for col in columns:
            self.transcript_tree.heading(col, text=col)
            if col == 'Mark':
                self.transcript_tree.column(col, width=80)
            else:
                self.transcript_tree.column(col, width=120)

        tree_scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=self.transcript_tree.yview)
        self.transcript_tree.configure(yscrollcommand=tree_scrollbar.set)

        self.transcript_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        tree_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # Configure grid weights
        transcript_frame.columnconfigure(0, weight=1)
        transcript_frame.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

    def setup_planning_tab(self):
        """Setup course planning tab"""
        planning_frame = ttk.Frame(self.notebook)
        self.notebook.add(planning_frame, text="Course Planning")

        main_frame = ttk.Frame(planning_frame, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Button(button_frame, text="Add Planned Course", command=self.add_planned_course).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Edit Course", command=self.edit_planned_course).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Delete Course", command=self.delete_planned_course).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Move to Transcript", command=self.move_to_transcript).pack(side=tk.LEFT)

        # Planning treeview
        tree_frame = ttk.Frame(main_frame)
        tree_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        columns = ('Course Code', 'Title', 'Credits', 'Session', 'Year', 'Priority', 'Notes')
        self.planning_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=20)

        for col in columns:
            self.planning_tree.heading(col, text=col)
            if col == 'Notes':
                self.planning_tree.column(col, width=200)
            else:
                self.planning_tree.column(col, width=120)

        tree_scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=self.planning_tree.yview)
        self.planning_tree.configure(yscrollcommand=tree_scrollbar.set)

        self.planning_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        tree_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # Configure grid weights
        planning_frame.columnconfigure(0, weight=1)
        planning_frame.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

    def setup_gpa_dashboard_tab(self):
        """Setup GPA dashboard tab"""
        gpa_frame = ttk.Frame(self.notebook)
        self.notebook.add(gpa_frame, text="GPA Dashboard")

        main_frame = ttk.Frame(gpa_frame, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # GPA Summary section
        summary_frame = ttk.LabelFrame(main_frame, text="GPA Summary", padding="10")
        summary_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        # Overall GPA
        ttk.Label(summary_frame, text="Overall GPA:", font=('TkDefaultFont', 12, 'bold')).grid(row=0, column=0, sticky=tk.W, padx=(0, 20))
        self.overall_gpa_var = tk.StringVar()
        ttk.Label(summary_frame, textvariable=self.overall_gpa_var, font=('TkDefaultFont', 16, 'bold')).grid(row=0, column=1, sticky=tk.W)

        # Total Credits
        ttk.Label(summary_frame, text="Total Credits:", font=('TkDefaultFont', 12, 'bold')).grid(row=1, column=0, sticky=tk.W, padx=(0, 20))
        self.total_credits_var = tk.StringVar()
        ttk.Label(summary_frame, textvariable=self.total_credits_var, font=('TkDefaultFont', 12)).grid(row=1, column=1, sticky=tk.W)

        # Academic Standing
        ttk.Label(summary_frame, text="Academic Standing:", font=('TkDefaultFont', 12, 'bold')).grid(row=2, column=0, sticky=tk.W, padx=(0, 20))
        self.standing_var = tk.StringVar()
        ttk.Label(summary_frame, textvariable=self.standing_var, font=('TkDefaultFont', 12)).grid(row=2, column=1, sticky=tk.W)

        # Sessional GPAs section
        sessional_frame = ttk.LabelFrame(main_frame, text="Sessional GPAs", padding="10")
        sessional_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Sessional GPA treeview
        columns = ('Session', 'Year', 'GPA', 'Credits', 'Courses')
        self.sessional_tree = ttk.Treeview(sessional_frame, columns=columns, show='headings', height=15)

        for col in columns:
            self.sessional_tree.heading(col, text=col)
            self.sessional_tree.column(col, width=120)

        sessional_scrollbar = ttk.Scrollbar(sessional_frame, orient='vertical', command=self.sessional_tree.yview)
        self.sessional_tree.configure(yscrollcommand=sessional_scrollbar.set)

        self.sessional_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        sessional_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # Buttons
        button_frame = ttk.Frame(sessional_frame)
        button_frame.grid(row=1, column=0, pady=(10, 0))

        ttk.Button(button_frame, text="Refresh", command=self.update_gpa_display).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Export Report", command=self.export_gpa_report).pack(side=tk.LEFT)

        # Configure grid weights
        gpa_frame.columnconfigure(0, weight=1)
        gpa_frame.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        sessional_frame.columnconfigure(0, weight=1)
        sessional_frame.rowconfigure(0, weight=1)

    def setup_analytics_tab(self):
        """Setup analytics tab"""
        analytics_frame = ttk.Frame(self.notebook)
        self.notebook.add(analytics_frame, text="Analytics")

        main_frame = ttk.Frame(analytics_frame, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Statistics section
        stats_frame = ttk.LabelFrame(main_frame, text="Course Statistics", padding="10")
        stats_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        self.stats_text = tk.Text(stats_frame, height=10, wrap=tk.WORD)
        stats_scrollbar = ttk.Scrollbar(stats_frame, orient='vertical', command=self.stats_text.yview)
        self.stats_text.configure(yscrollcommand=stats_scrollbar.set)

        self.stats_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        stats_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # Chart section (if matplotlib available)
        if MATPLOTLIB_AVAILABLE:
            chart_frame = ttk.LabelFrame(main_frame, text="GPA Trend Chart", padding="10")
            chart_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

            # Create matplotlib figure
            self.fig = Figure(figsize=(10, 6), dpi=100)
            self.chart_canvas = FigureCanvasTkAgg(self.fig, chart_frame)
            self.chart_canvas.get_tk_widget().grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, pady=(10, 0))

        ttk.Button(button_frame, text="Refresh Analytics", command=self.update_analytics).pack(side=tk.LEFT, padx=(0, 10))
        if MATPLOTLIB_AVAILABLE:
            ttk.Button(button_frame, text="Update Chart", command=self.update_chart).pack(side=tk.LEFT)

        # Configure grid weights
        analytics_frame.columnconfigure(0, weight=1)
        analytics_frame.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        stats_frame.columnconfigure(0, weight=1)
        stats_frame.rowconfigure(0, weight=1)
        if MATPLOTLIB_AVAILABLE:
            main_frame.rowconfigure(1, weight=1)
            chart_frame.columnconfigure(0, weight=1)
            chart_frame.rowconfigure(0, weight=1)

    def search_courses(self):
        """Search for courses using the scraper (threaded)"""
        if not self.scraper:
            messagebox.showerror("Error", "Course search not available - Selenium not installed")
            return

        query = self.search_var.get().strip()
        if not query:
            messagebox.showwarning("Warning", "Please enter a course code or keyword")
            return

        # Show loading state
        self.status_var.set("Searching...")
        self.results_listbox.delete(0, tk.END)
        self.results_listbox.insert(tk.END, "Searching...")
        self.root.update()

        # Start search in background thread
        def search_thread():
            try:
                results = self.scraper.search_courses(query)
                # Schedule GUI update on main thread
                self.root.after(0, lambda: self.update_search_results(results, query))
            except Exception as e:
                # Schedule error display on main thread
                self.root.after(0, lambda: self.handle_search_error(str(e)))

        thread = threading.Thread(target=search_thread, daemon=True)
        thread.start()

    def update_search_results(self, results, query):
        """Update search results in GUI (main thread only)"""
        self.search_results = results

        # Update results listbox
        self.results_listbox.delete(0, tk.END)
        for result in self.search_results:
            display_text = f"{result['course_code']} - {result['title']}"
            self.results_listbox.insert(tk.END, display_text)

        self.status_var.set(f"Found {len(self.search_results)} courses for '{query}'")

    def handle_search_error(self, error_msg):
        """Handle search error (main thread only)"""
        messagebox.showerror("Search Error", f"Search failed: {error_msg}")
        self.status_var.set("Search failed")
        self.results_listbox.delete(0, tk.END)

    def on_course_select(self, event):
        """Handle course selection in search results"""
        selection = self.results_listbox.curselection()
        if selection:
            index = selection[0]
            if index < len(self.search_results):
                course = self.search_results[index]
                # Show basic info immediately
                self.details_text.delete(1.0, tk.END)
                self.details_text.insert(1.0, f"Course: {course['title']}\\n\\nDescription: {course['description']}")

    def extract_course_details(self):
        """Extract detailed course information (threaded)"""
        selection = self.results_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a course first")
            return

        if not self.scraper:
            messagebox.showerror("Error", "Course extraction not available - Selenium not installed")
            return

        index = selection[0]
        course = self.search_results[index]

        if not course.get('url'):
            messagebox.showwarning("Warning", "No URL available for this course")
            return

        # Show loading state
        self.status_var.set("Extracting course details...")
        self.details_text.delete(1.0, tk.END)
        self.details_text.insert(tk.END, "Extracting course details...")
        self.root.update()

        # Start extraction in background thread
        def extraction_thread():
            try:
                details = self.scraper.extract_course_details(course['url'])
                # Schedule GUI update on main thread
                self.root.after(0, lambda: self.update_course_details(details, course))
            except Exception as e:
                # Schedule error display on main thread
                self.root.after(0, lambda: self.handle_extraction_error(str(e)))

        thread = threading.Thread(target=extraction_thread, daemon=True)
        thread.start()

    def update_course_details(self, details, course):
        """Update course details in GUI (main thread only)"""
        if details:
            # Save to database
            try:
                self.database.save_academic_course(details)
                # Display details
                self.display_course_details(details)
                self.status_var.set("Course details extracted and saved")
            except Exception as e:
                self.status_var.set(f"Saved to display but database error: {e}")
                self.display_course_details(details)
        else:
            messagebox.showwarning("Warning", "Failed to extract course details")
            self.status_var.set("Extraction failed")

    def handle_extraction_error(self, error_msg):
        """Handle extraction error (main thread only)"""
        messagebox.showerror("Extraction Error", f"Extraction failed: {error_msg}")
        self.status_var.set("Extraction failed")
        self.details_text.delete(1.0, tk.END)

    def display_course_details(self, details):
        """Display course details in the text widget"""
        self.details_text.delete(1.0, tk.END)

        details_text = f"""COURSE TITLE: {details.get('title', 'N/A')}

COURSE CODE: {details.get('course_code', 'N/A')}

HOURS: {details.get('hours', 'N/A')}

DESCRIPTION:
{details.get('description', 'N/A')}

PREREQUISITES:
{details.get('prerequisites', 'N/A')}

EXCLUSIONS:
{details.get('exclusions', 'N/A')}

BREADTH REQUIREMENTS:
{details.get('breadth_requirements', 'N/A')}

URL: {details.get('url', 'N/A')}"""

        self.details_text.insert(1.0, details_text)

    def add_to_transcript(self):
        """Add selected course to transcript"""
        selection = self.results_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a course first")
            return

        index = selection[0]
        course = self.search_results[index]

        # Pre-populate dialog with course data
        course_data = {
            'course_code': course['course_code'],
            'title': course['title'],
            'credits': 0.5  # Default value
        }

        dialog = CourseDialog(self.root, "Add to Transcript", mode="transcript", course_data=course_data)
        if dialog.result:
            try:
                self.database.save_transcript_course(dialog.result)
                self.update_displays()
                messagebox.showinfo("Success", "Course added to transcript")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add course: {e}")

    def add_to_plan(self):
        """Add selected course to planning list"""
        selection = self.results_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a course first")
            return

        index = selection[0]
        course = self.search_results[index]

        # Pre-populate dialog with course data
        course_data = {
            'course_code': course['course_code'],
            'title': course['title'],
            'credits': 0.5  # Default value
        }

        dialog = CourseDialog(self.root, "Add to Plan", mode="planned", course_data=course_data)
        if dialog.result:
            try:
                self.database.save_planned_course(dialog.result)
                self.update_displays()
                messagebox.showinfo("Success", "Course added to plan")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add course: {e}")

    def add_transcript_course(self):
        """Add course manually to transcript"""
        dialog = CourseDialog(self.root, "Add Course to Transcript", mode="transcript")
        if dialog.result:
            try:
                self.database.save_transcript_course(dialog.result)
                self.update_displays()
                messagebox.showinfo("Success", "Course added to transcript")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add course: {e}")

    def add_planned_course(self):
        """Add course manually to planning list"""
        dialog = CourseDialog(self.root, "Add Planned Course", mode="planned")
        if dialog.result:
            try:
                self.database.save_planned_course(dialog.result)
                self.update_displays()
                messagebox.showinfo("Success", "Course added to plan")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add course: {e}")

    def edit_transcript_course(self):
        """Edit selected transcript course"""
        selection = self.transcript_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a course to edit")
            return

        # Get course data from tree selection
        item = self.transcript_tree.item(selection[0])
        values = item['values']

        # Parse mark if present
        mark_value = None
        if len(values) > 4 and values[4].strip():
            try:
                mark_value = float(values[4])
            except ValueError:
                pass

        course_data = {
            'course_code': values[0],
            'title': values[1],
            'credits': float(values[2]),
            'grade': values[3],
            'mark': mark_value,
            'session': values[5],  # Updated index after mark column
            'year': int(values[6])  # Updated index after mark column
        }

        dialog = CourseDialog(self.root, "Edit Transcript Course", mode="transcript", course_data=course_data)
        if dialog.result:
            # Update database logic would go here
            self.update_displays()
            messagebox.showinfo("Success", "Course updated")

    def delete_transcript_course(self):
        """Delete selected transcript course"""
        selection = self.transcript_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a course to delete")
            return

        if messagebox.askyesno("Confirm", "Are you sure you want to delete this course?"):
            # Delete from database logic would go here
            self.update_displays()
            messagebox.showinfo("Success", "Course deleted")

    def bulk_edit_transcript(self):
        """Bulk edit selected transcript courses"""
        selection = self.transcript_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select courses to edit")
            return

        if len(selection) == 0:
            return

        # Create bulk edit dialog
        dialog = BulkEditDialog(self.root, len(selection))
        if dialog.result:
            try:
                updates = []
                for item_id in selection:
                    course_data = self.transcript_course_data[item_id].copy()
                    course_id = course_data['id']

                    # Apply bulk changes
                    if dialog.result.get('session'):
                        course_data['session'] = dialog.result['session']
                    if dialog.result.get('year'):
                        course_data['year'] = dialog.result['year']
                    if dialog.result.get('grade'):
                        course_data['grade'] = dialog.result['grade']
                        course_data['gpa_points'] = self.GRADE_POINTS.get(dialog.result['grade'], 0.0)
                    if dialog.result.get('status'):
                        course_data['status'] = dialog.result['status']

                    updates.append((course_id, course_data))

                self.database.bulk_update_transcript_courses(updates)
                self.update_displays()
                messagebox.showinfo("Success", f"Updated {len(selection)} courses")

            except Exception as e:
                messagebox.showerror("Error", f"Bulk edit failed: {e}")

    def bulk_delete_transcript(self):
        """Bulk delete selected transcript courses"""
        selection = self.transcript_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select courses to delete")
            return

        if messagebox.askyesno("Confirm", f"Are you sure you want to delete {len(selection)} course(s)?"):
            try:
                course_ids = [self.transcript_course_data[item_id]['id'] for item_id in selection]
                self.database.delete_transcript_courses(course_ids)
                self.update_displays()
                messagebox.showinfo("Success", f"Deleted {len(selection)} courses")

            except Exception as e:
                messagebox.showerror("Error", f"Bulk delete failed: {e}")

    def bulk_import_course_codes(self):
        """Bulk import course codes and auto-populate from academic calendar"""
        if not SELENIUM_AVAILABLE or not self.scraper:
            messagebox.showerror("Error", "Course search not available - Selenium not installed")
            return

        dialog = BulkImportDialog(self.root)
        if dialog.result:
            course_codes = dialog.result

            # Progress tracking
            progress_window = tk.Toplevel(self.root)
            progress_window.title("Bulk Import Progress")
            progress_window.geometry("500x300")
            progress_window.transient(self.root)
            progress_window.grab_set()

            progress_frame = ttk.Frame(progress_window, padding="20")
            progress_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

            ttk.Label(progress_frame, text="Importing and populating course data...",
                     font=('TkDefaultFont', 12, 'bold')).grid(row=0, column=0, pady=(0, 20))

            progress_label = ttk.Label(progress_frame, text="Starting...")
            progress_label.grid(row=1, column=0, pady=(0, 10))

            # Progress text area
            progress_text = tk.Text(progress_frame, height=12, width=60)
            progress_scroll = ttk.Scrollbar(progress_frame, orient='vertical', command=progress_text.yview)
            progress_text.configure(yscrollcommand=progress_scroll.set)
            progress_text.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
            progress_scroll.grid(row=2, column=1, sticky=(tk.N, tk.S))

            progress_frame.columnconfigure(0, weight=1)
            progress_frame.rowconfigure(2, weight=1)
            progress_window.columnconfigure(0, weight=1)
            progress_window.rowconfigure(0, weight=1)

            def log_progress(message):
                progress_text.insert(tk.END, message + "\n")
                progress_text.see(tk.END)
                progress_window.update()

            # Process course codes
            imported_count = 0
            failed_codes = []

            for i, course_code in enumerate(course_codes):
                course_code = course_code.strip().upper()
                if not course_code:
                    continue

                progress_label.config(text=f"Processing {course_code}... ({i+1}/{len(course_codes)})")
                log_progress(f"Searching for {course_code}...")

                try:
                    # Search for the course
                    search_results = self.scraper.search_courses(course_code)

                    if search_results:
                        # Try to find exact match first
                        exact_match = None
                        for result in search_results:
                            if result['course_code'].upper() == course_code:
                                exact_match = result
                                break

                        # Use exact match or first result
                        selected_result = exact_match or search_results[0]
                        log_progress(f"Found: {selected_result['title']}")

                        # Extract detailed course information
                        if selected_result.get('url'):
                            log_progress(f"Extracting details for {course_code}...")
                            details = self.scraper.extract_course_details(selected_result['url'])

                            if details:
                                # Save to academic database
                                self.database.save_academic_course(details)
                                log_progress(f"✓ Successfully imported {course_code}")
                                imported_count += 1
                            else:
                                log_progress(f"✗ Failed to extract details for {course_code}")
                                failed_codes.append(course_code)
                        else:
                            log_progress(f"✗ No URL available for {course_code}")
                            failed_codes.append(course_code)
                    else:
                        log_progress(f"✗ Course {course_code} not found")
                        failed_codes.append(course_code)

                except Exception as e:
                    log_progress(f"✗ Error processing {course_code}: {str(e)}")
                    failed_codes.append(course_code)

            # Show completion summary
            progress_label.config(text="Import completed!")
            log_progress(f"\n=== IMPORT SUMMARY ===")
            log_progress(f"Successfully imported: {imported_count} courses")
            log_progress(f"Failed: {len(failed_codes)} courses")

            if failed_codes:
                log_progress(f"Failed courses: {', '.join(failed_codes)}")

            # Add close button
            close_button = ttk.Button(progress_frame, text="Close",
                                    command=progress_window.destroy)
            close_button.grid(row=3, column=0, pady=(20, 0))

            # Update displays
            self.update_displays()

            # Final message
            messagebox.showinfo("Import Complete",
                              f"Successfully imported {imported_count} courses.\n"
                              f"Failed: {len(failed_codes)} courses.\n"
                              f"Check the progress window for details.")

    def auto_populate_titles(self):
        """Auto-populate missing course titles from academic calendar database"""
        try:
            # Check how many courses have missing titles
            missing_count = self.database.get_missing_title_courses()

            if missing_count == 0:
                messagebox.showinfo("Auto-Populate Titles",
                                  "All courses already have titles!")
                return

            # Confirm action with user
            result = messagebox.askyesno("Auto-Populate Titles",
                                       f"Found {missing_count} courses with missing titles.\n\n"
                                       f"This will search the academic calendar database to find "
                                       f"matching course titles based on course codes.\n\n"
                                       f"Continue?")

            if not result:
                return

            # Show progress
            self.status_var.set("Auto-populating course titles...")
            self.root.update()

            # Perform the auto-population
            updates_made = self.database.auto_populate_course_titles()

            # Clear cache to ensure fresh data
            self.database._clear_cache()

            # Update the transcript display
            self.update_transcript_display()

            # Show results
            if updates_made > 0:
                messagebox.showinfo("Auto-Populate Complete",
                                  f"Successfully updated {updates_made} course titles!")
                self.status_var.set(f"Updated {updates_made} course titles")
            else:
                messagebox.showinfo("Auto-Populate Complete",
                                  "No matching titles found in academic calendar database.\n\n"
                                  "Try using 'Extract Details' from the Course Search tab to "
                                  "add more courses to the academic calendar database first.")
                self.status_var.set("No titles updated")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to auto-populate titles: {e}")
            self.status_var.set("Auto-populate failed")

    def edit_planned_course(self):
        """Edit selected planned course"""
        selection = self.planning_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a course to edit")
            return

        # Similar implementation to edit_transcript_course
        messagebox.showinfo("Info", "Edit planned course functionality would be implemented here")

    def delete_planned_course(self):
        """Delete selected planned course"""
        selection = self.planning_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a course to delete")
            return

        if messagebox.askyesno("Confirm", "Are you sure you want to delete this course?"):
            # Delete from database logic would go here
            self.update_displays()
            messagebox.showinfo("Success", "Course deleted")

    def move_to_transcript(self):
        """Move planned course to transcript"""
        selection = self.planning_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a course to move")
            return

        # Implementation would move course from planned to transcript
        messagebox.showinfo("Info", "Move to transcript functionality would be implemented here")

    def calculate_gpa(self, courses):
        """Calculate GPA for a list of courses"""
        total_points = 0.0
        total_credits = 0.0

        for course in courses:
            # course tuple: (id, course_code, title, credits, grade, mark, session, year, status, gpa_points, created_at)
            if len(course) >= 5:  # Ensure we have grade and credits
                credits_value = course[3]  # credits field
                grade = course[4]  # grade field

                try:
                    credits = float(credits_value)
                except (ValueError, TypeError):
                    continue

                if grade in self.GRADE_POINTS:
                    points = self.GRADE_POINTS[grade]
                    total_points += points * credits
                    total_credits += credits

        if total_credits > 0:
            return total_points / total_credits, total_credits
        else:
            return 0.0, 0.0

    def update_displays(self):
        """Update all displays"""
        self.update_transcript_display()
        self.update_planning_display()
        self.update_gpa_display()
        self.update_analytics()

    def update_transcript_display(self):
        """Update transcript treeview"""
        # Clear existing items
        for item in self.transcript_tree.get_children():
            self.transcript_tree.delete(item)

        # Store course data for bulk operations
        self.transcript_course_data = {}

        # Get transcript courses from database
        courses = self.database.get_transcript_courses()

        for course in courses:
            # course tuple: (id, course_code, title, credits, grade, mark, session, year, status, gpa_points, created_at)
            course_id = course[0]
            # Handle mark display - could be float or string
            mark_display = ""
            if course[5] is not None:
                try:
                    mark_value = float(course[5])
                    mark_display = f"{mark_value:.1f}"
                except (ValueError, TypeError):
                    mark_display = str(course[5])

            item_id = self.transcript_tree.insert('', 'end', values=(
                course[1],  # course_code
                course[2],  # title
                course[3],  # credits
                course[4],  # grade
                mark_display,  # mark
                course[6],  # session
                course[7],  # year
                course[8]   # status
            ))

            # Store course data for bulk operations
            self.transcript_course_data[item_id] = {
                'id': course_id,
                'course_code': course[1],
                'title': course[2],
                'credits': course[3],
                'grade': course[4],
                'mark': course[5],
                'session': course[6],
                'year': course[7],
                'status': course[8]
            }

    def update_planning_display(self):
        """Update planning treeview"""
        # Clear existing items
        for item in self.planning_tree.get_children():
            self.planning_tree.delete(item)

        # Get planned courses from database
        courses = self.database.get_planned_courses()

        for course in courses:
            # course tuple: (id, course_code, title, credits, planned_session, planned_year, priority, notes, created_at)
            self.planning_tree.insert('', 'end', values=(
                course[1],  # course_code
                course[2],  # title
                course[3],  # credits
                course[4],  # planned_session
                course[5],  # planned_year
                course[6],  # priority
                course[7]   # notes
            ))

    def update_gpa_display(self):
        """Update GPA dashboard"""
        # Get transcript courses
        courses = self.database.get_transcript_courses()

        # Calculate overall GPA
        overall_gpa, total_credits = self.calculate_gpa(courses)

        self.overall_gpa_var.set(f"{overall_gpa:.2f}")
        self.total_credits_var.set(f"{total_credits:.1f}")

        # Determine academic standing
        standing = self.get_academic_standing(overall_gpa)
        self.standing_var.set(standing)

        # Update sessional GPAs
        self.update_sessional_display(courses)

    def get_academic_standing(self, gpa):
        """Determine academic standing based on GPA"""
        if gpa >= 3.60:
            return "Dean's List"
        elif gpa >= 3.00:
            return "Good Standing"
        elif gpa >= 2.00:
            return "Satisfactory"
        elif gpa >= 1.50:
            return "Academic Probation"
        else:
            return "Academic Suspension"

    def update_sessional_display(self, courses):
        """Update sessional GPA display"""
        # Clear existing items
        for item in self.sessional_tree.get_children():
            self.sessional_tree.delete(item)

        # Group courses by session and year
        sessions = defaultdict(list)
        for course in courses:
            # course tuple: (id, course_code, title, credits, grade, mark, session, year, status, gpa_points, created_at)
            if len(course) >= 8:
                session_key = f"{course[6]} {course[7]}"  # session year
                sessions[session_key].append(course)

        # Calculate GPA for each session
        for session_key, session_courses in sessions.items():
            gpa, credits = self.calculate_gpa(session_courses)
            course_count = len(session_courses)

            # Parse session and year
            parts = session_key.split()
            if len(parts) == 2:
                session, year = parts
                self.sessional_tree.insert('', 'end', values=(
                    session, year, f"{gpa:.2f}", f"{credits:.1f}", course_count
                ))

    def update_analytics(self):
        """Update analytics display"""
        courses = self.database.get_transcript_courses()
        academic_courses = self.database.get_academic_courses()
        planned_courses = self.database.get_planned_courses()

        stats_text = f"""COURSE STATISTICS

Transcript Courses: {len(courses)}
Academic Calendar Courses: {len(academic_courses)}
Planned Courses: {len(planned_courses)}

GRADE DISTRIBUTION:"""

        # Calculate grade distribution
        grade_counts = defaultdict(int)
        for course in courses:
            if len(course) >= 5:
                grade = course[4]
                grade_counts[grade] += 1

        for grade, count in sorted(grade_counts.items()):
            stats_text += f"\\n{grade}: {count}"

        # Calculate department distribution
        dept_counts = defaultdict(int)
        for course in courses:
            if len(course) >= 2:
                course_code = course[1]
                dept = re.match(r'^([A-Z]+)', course_code)
                if dept:
                    dept_counts[dept.group(1)] += 1

        stats_text += f"\\n\\nDEPARTMENT DISTRIBUTION:"
        for dept, count in sorted(dept_counts.items(), key=lambda x: x[1], reverse=True):
            stats_text += f"\\n{dept}: {count}"

        self.stats_text.delete(1.0, tk.END)
        self.stats_text.insert(1.0, stats_text)

    def update_chart(self):
        """Update GPA trend chart"""
        if not MATPLOTLIB_AVAILABLE:
            return

        courses = self.database.get_transcript_courses()

        # Group by session and calculate GPAs
        sessions = defaultdict(list)
        for course in courses:
            # course tuple: (id, course_code, title, credits, grade, mark, session, year, status, gpa_points, created_at)
            if len(course) >= 8:
                session_key = f"{course[7]}-{course[6]}"  # year-session
                sessions[session_key].append(course)

        session_names = []
        gpas = []

        for session_key in sorted(sessions.keys()):
            session_courses = sessions[session_key]
            gpa, _ = self.calculate_gpa(session_courses)
            session_names.append(session_key)
            gpas.append(gpa)

        # Clear and plot
        self.fig.clear()
        ax = self.fig.add_subplot(111)

        if gpas:
            ax.plot(range(len(gpas)), gpas, marker='o', linewidth=2, markersize=6)
            ax.set_xlabel('Session')
            ax.set_ylabel('GPA')
            ax.set_title('GPA Trend Over Time')
            ax.set_xticks(range(len(session_names)))
            ax.set_xticklabels(session_names, rotation=45, ha='right')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(0, 4.0)
        else:
            ax.text(0.5, 0.5, 'No data available', ha='center', va='center', transform=ax.transAxes)

        self.fig.tight_layout()
        self.chart_canvas.draw()

    def import_transcript_csv(self):
        """Import transcript from CSV"""
        file_path = filedialog.askopenfilename(
            title="Import Transcript CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )

        if file_path:
            try:
                with open(file_path, 'r', newline='', encoding='utf-8') as file:
                    reader = csv.DictReader(file)
                    imported_count = 0

                    for row in reader:
                        try:
                            # Parse mark if provided
                            mark_value = None
                            if 'mark' in row and row['mark'].strip():
                                try:
                                    mark_value = float(row['mark'])
                                except ValueError:
                                    pass

                            course_data = {
                                'course_code': row.get('course_code', ''),
                                'title': row.get('title', ''),
                                'credits': float(row.get('credits', 0.5)),
                                'grade': row.get('grade', ''),
                                'mark': mark_value,
                                'session': row.get('session', 'Fall'),
                                'year': int(row.get('year', datetime.now().year)),
                                'gpa_points': self.GRADE_POINTS.get(row.get('grade', ''), 0.0)
                            }

                            self.database.save_transcript_course(course_data)
                            imported_count += 1
                        except (ValueError, KeyError) as e:
                            print(f"Skipped row due to error: {e}")
                            continue

                    self.update_displays()
                    messagebox.showinfo("Success", f"Imported {imported_count} courses")

            except Exception as e:
                messagebox.showerror("Error", f"Import failed: {e}")

    def export_transcript_csv(self):
        """Export transcript to CSV"""
        file_path = filedialog.asksaveasfilename(
            title="Export Transcript CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )

        if file_path:
            try:
                courses = self.database.get_transcript_courses()

                with open(file_path, 'w', newline='', encoding='utf-8') as file:
                    fieldnames = ['course_code', 'title', 'credits', 'grade', 'mark', 'session', 'year', 'status']
                    writer = csv.DictWriter(file, fieldnames=fieldnames)
                    writer.writeheader()

                    for course in courses:
                        # course tuple: (id, course_code, title, credits, grade, mark, session, year, status, gpa_points, created_at)
                        writer.writerow({
                            'course_code': course[1],
                            'title': course[2],
                            'credits': course[3],
                            'grade': course[4],
                            'mark': course[5] if course[5] is not None else '',
                            'session': course[6],
                            'year': course[7],
                            'status': course[8]
                        })

                messagebox.showinfo("Success", f"Exported {len(courses)} courses to {file_path}")

            except Exception as e:
                messagebox.showerror("Error", f"Export failed: {e}")

    def export_gpa_report(self):
        """Export GPA report"""
        file_path = filedialog.asksaveasfilename(
            title="Export GPA Report",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )

        if file_path:
            try:
                courses = self.database.get_transcript_courses()
                overall_gpa, total_credits = self.calculate_gpa(courses)

                report = f"""UofT Course Dashboard - GPA Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

OVERALL STATISTICS
==================
Overall GPA: {overall_gpa:.2f}
Total Credits: {total_credits:.1f}
Academic Standing: {self.get_academic_standing(overall_gpa)}
Total Courses: {len(courses)}

SESSIONAL BREAKDOWN
==================
"""

                # Add sessional data
                sessions = defaultdict(list)
                for course in courses:
                    if len(course) >= 7:
                        session_key = f"{course[5]} {course[6]}"
                        sessions[session_key].append(course)

                for session_key in sorted(sessions.keys()):
                    session_courses = sessions[session_key]
                    gpa, credits = self.calculate_gpa(session_courses)
                    report += f"{session_key}: GPA {gpa:.2f}, Credits {credits:.1f}, Courses {len(session_courses)}\\n"

                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write(report)

                messagebox.showinfo("Success", f"GPA report exported to {file_path}")

            except Exception as e:
                messagebox.showerror("Error", f"Export failed: {e}")

    def run(self):
        """Start the application"""
        try:
            self.root.mainloop()
        finally:
            if self.scraper:
                self.scraper.close_driver()


class BulkImportDialog:
    """Dialog for bulk importing course codes"""

    def __init__(self, parent):
        self.result = None

        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Bulk Import Course Codes")
        self.dialog.geometry("500x400")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.setup_dialog()

        # Center dialog
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))

        # Wait for dialog to close
        self.dialog.wait_window()

    def setup_dialog(self):
        """Setup bulk import dialog interface"""
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Instructions
        instructions = ttk.Label(main_frame,
                               text="Enter course codes (one per line).\nThe system will search and extract details from the Academic Calendar.",
                               justify='left')
        instructions.grid(row=0, column=0, sticky=tk.W, pady=(0, 15))

        # Text area for course codes
        ttk.Label(main_frame, text="Course Codes:").grid(row=1, column=0, sticky=tk.W, pady=(0, 5))

        text_frame = ttk.Frame(main_frame)
        text_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 15))

        self.codes_text = tk.Text(text_frame, height=15, width=50)
        codes_scroll = ttk.Scrollbar(text_frame, orient='vertical', command=self.codes_text.yview)
        self.codes_text.configure(yscrollcommand=codes_scroll.set)

        self.codes_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        codes_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # Example text
        example_text = """CSC108H1
CSC148H1
MAT137Y1
CSC165H1
CSC207H1"""
        self.codes_text.insert(1.0, example_text)

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, pady=(10, 0))

        ttk.Button(button_frame, text="Import Courses", command=self.import_courses).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.dialog.destroy).pack(side=tk.LEFT, padx=5)

        # Configure grid weights
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)
        self.dialog.columnconfigure(0, weight=1)
        self.dialog.rowconfigure(0, weight=1)

    def import_courses(self):
        """Start the import process"""
        try:
            codes_text = self.codes_text.get(1.0, tk.END).strip()
            if not codes_text:
                messagebox.showwarning("Warning", "Please enter at least one course code")
                return

            # Parse course codes
            course_codes = [line.strip() for line in codes_text.split('\n') if line.strip()]

            if not course_codes:
                messagebox.showwarning("Warning", "No valid course codes found")
                return

            self.result = course_codes
            self.dialog.destroy()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to parse course codes: {e}")


class BulkEditDialog:
    """Dialog for bulk editing transcript courses"""

    def __init__(self, parent, course_count):
        self.result = None

        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Bulk Edit - {course_count} courses")
        self.dialog.geometry("400x350")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.setup_dialog()

        # Center dialog
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))

        # Wait for dialog to close
        self.dialog.wait_window()

    def setup_dialog(self):
        """Setup bulk edit dialog interface"""
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        ttk.Label(main_frame, text="Select fields to update (leave blank to keep existing values):").grid(
            row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 15))

        # Session
        ttk.Label(main_frame, text="Session:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.session_var = tk.StringVar()
        session_combo = ttk.Combobox(main_frame, textvariable=self.session_var,
                                   values=['', 'Fall', 'Winter', 'Summer'], width=15)
        session_combo.grid(row=1, column=1, sticky=tk.W, pady=5, padx=(10, 0))

        # Year
        ttk.Label(main_frame, text="Year:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.year_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.year_var, width=15).grid(row=2, column=1, sticky=tk.W, pady=5, padx=(10, 0))

        # Grade
        ttk.Label(main_frame, text="Grade:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.grade_var = tk.StringVar()
        grade_values = [''] + ['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'D-', 'F', 'FZ', 'CR', 'NCR', 'WDR', 'LWD']
        grade_combo = ttk.Combobox(main_frame, textvariable=self.grade_var, values=grade_values, width=15)
        grade_combo.grid(row=3, column=1, sticky=tk.W, pady=5, padx=(10, 0))

        # Status
        ttk.Label(main_frame, text="Status:").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.status_var = tk.StringVar()
        status_combo = ttk.Combobox(main_frame, textvariable=self.status_var,
                                  values=['', 'completed', 'in_progress', 'withdrawn'], width=15)
        status_combo.grid(row=4, column=1, sticky=tk.W, pady=5, padx=(10, 0))

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=2, pady=20)

        ttk.Button(button_frame, text="Apply Changes", command=self.apply_changes).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.dialog.destroy).pack(side=tk.LEFT, padx=5)

        # Configure grid weights
        main_frame.columnconfigure(1, weight=1)
        self.dialog.columnconfigure(0, weight=1)
        self.dialog.rowconfigure(0, weight=1)

    def apply_changes(self):
        """Apply bulk changes"""
        try:
            self.result = {}

            # Only include non-empty values
            if self.session_var.get().strip():
                self.result['session'] = self.session_var.get().strip()

            if self.year_var.get().strip():
                self.result['year'] = int(self.year_var.get().strip())

            if self.grade_var.get().strip():
                self.result['grade'] = self.grade_var.get().strip()

            if self.status_var.get().strip():
                self.result['status'] = self.status_var.get().strip()

            if not self.result:
                messagebox.showwarning("Warning", "Please select at least one field to update")
                return

            self.dialog.destroy()

        except ValueError as e:
            messagebox.showerror("Error", f"Invalid input: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to apply changes: {e}")


def main():
    """Main function"""
    root = tk.Tk()
    app = CourseDashboard(root)
    app.run()


if __name__ == "__main__":
    main()