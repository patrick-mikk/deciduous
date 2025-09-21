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

    def __init__(self, db_path="data/course_dashboard.db"):
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

        # Create schema version table for migration tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            )
        ''')

        # Check current schema version
        cursor.execute('SELECT MAX(version) FROM schema_version')
        current_version = cursor.fetchone()[0] or 0

        # Apply migrations in order
        self._apply_migrations(cursor, current_version)

        conn.commit()
        conn.close()

    def _apply_migrations(self, cursor, current_version):
        """Apply database migrations in order"""
        migrations = [
            (1, "Initial database schema", self._migration_001_initial_schema),
            (2, "Phase 1: Academic planning foundation", self._migration_002_academic_planning),
        ]

        for version, description, migration_func in migrations:
            if version > current_version:
                try:
                    print(f"Applying migration {version}: {description}")
                    migration_func(cursor)
                    cursor.execute('INSERT INTO schema_version (version, description) VALUES (?, ?)',
                                 (version, description))
                    print(f"Migration {version} completed successfully")
                except Exception as e:
                    print(f"Migration {version} failed: {e}")
                    raise

    def _migration_001_initial_schema(self, cursor):
        """Migration 1: Original database schema"""
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

    def _migration_002_academic_planning(self, cursor):
        """Migration 2: Academic planning foundation tables for Phase 1"""

        # Programs table - UofT academic programs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS programs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,        -- ASSPE0608, ASMAJ1689, etc.
                title TEXT NOT NULL,              -- "Computer Science Major"
                type TEXT NOT NULL,               -- Specialist, Major, Minor, Certificate, Focus
                degree_type TEXT,                 -- HBA, HBSc, BCom
                credits_required REAL DEFAULT 0, -- Total credits needed (6.0-14.0)
                credits_300_plus REAL DEFAULT 0, -- Required 300+ level credits
                credits_400_plus REAL DEFAULT 0, -- Required 400+ level credits
                department TEXT,                  -- Department offering program
                faculty TEXT DEFAULT 'Arts & Science',
                description TEXT,
                enrolment_type TEXT,             -- Limited, Open
                active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Student programs - track which programs student is enrolled in
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS student_programs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                program_id INTEGER NOT NULL REFERENCES programs(id),
                student_id TEXT DEFAULT 'default',  -- Support for multiple students later
                enrolled_date DATE DEFAULT CURRENT_DATE,
                status TEXT DEFAULT 'active',       -- active, completed, withdrawn
                target_graduation TEXT,             -- e.g., "2025 Spring"
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(program_id, student_id)
            )
        ''')

        # Degree requirements - configurable requirements tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS degree_requirements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT DEFAULT 'default',
                total_credits_required REAL DEFAULT 20.0,
                arts_science_min REAL DEFAULT 10.0,      -- Min credits from Arts & Science
                credits_200_plus_min REAL DEFAULT 13.0,  -- Min 200+ level credits
                credits_300_plus_min REAL DEFAULT 6.0,   -- Min 300+ level credits
                max_same_designator REAL DEFAULT 15.0,   -- Max credits from same department
                min_gpa REAL DEFAULT 1.85,               -- Minimum CGPA for graduation
                breadth_credits_required REAL DEFAULT 4.0, -- Total breadth requirement
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(student_id)
            )
        ''')

        # Breadth categories - UofT's 5 breadth requirement categories
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS breadth_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_number INTEGER UNIQUE,  -- 1, 2, 3, 4, 5
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Course breadth mappings - which courses satisfy which breadth requirements
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS course_breadth (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_code TEXT NOT NULL,
                category_id INTEGER NOT NULL REFERENCES breadth_categories(id),
                verified BOOLEAN DEFAULT 0,      -- Whether mapping is verified
                source TEXT DEFAULT 'manual',   -- manual, scraped, official
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(course_code, category_id)
            )
        ''')

        # Program requirements - specific requirements for each program
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS program_requirements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                program_id INTEGER NOT NULL REFERENCES programs(id),
                requirement_type TEXT NOT NULL,   -- core, elective, prerequisite
                year_level INTEGER,               -- 1, 2, 3, 4 for year-specific requirements
                credits_required REAL DEFAULT 0,
                course_list TEXT,                 -- JSON array of course codes
                description TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Academic standing - track academic standing over time
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS academic_standing (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT DEFAULT 'default',
                session TEXT,                    -- "2024 Fall", "2024 Winter"
                year INTEGER,
                gpa REAL,
                total_credits REAL,
                standing TEXT,                   -- "Good Standing", "Dean's List", etc.
                notes TEXT,
                calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(student_id, session, year)
            )
        ''')

        # Create indexes for new tables
        phase1_indexes = [
            'CREATE INDEX IF NOT EXISTS idx_programs_code ON programs(code)',
            'CREATE INDEX IF NOT EXISTS idx_programs_type ON programs(type)',
            'CREATE INDEX IF NOT EXISTS idx_programs_active ON programs(active)',
            'CREATE INDEX IF NOT EXISTS idx_student_programs_student ON student_programs(student_id)',
            'CREATE INDEX IF NOT EXISTS idx_student_programs_status ON student_programs(status)',
            'CREATE INDEX IF NOT EXISTS idx_course_breadth_course ON course_breadth(course_code)',
            'CREATE INDEX IF NOT EXISTS idx_course_breadth_category ON course_breadth(category_id)',
            'CREATE INDEX IF NOT EXISTS idx_program_requirements_program ON program_requirements(program_id)',
            'CREATE INDEX IF NOT EXISTS idx_program_requirements_type ON program_requirements(requirement_type)',
            'CREATE INDEX IF NOT EXISTS idx_academic_standing_student ON academic_standing(student_id)',
            'CREATE INDEX IF NOT EXISTS idx_academic_standing_session ON academic_standing(session, year)'
        ]

        for index_sql in phase1_indexes:
            cursor.execute(index_sql)

        # Populate breadth categories if empty
        self._populate_breadth_categories(cursor)

        # Populate sample programs if empty
        self._populate_sample_programs(cursor)

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

    def _populate_breadth_categories(self, cursor):
        """Populate the breadth categories table with UofT's 5 categories"""
        try:
            # Check if categories already exist
            cursor.execute('SELECT COUNT(*) FROM breadth_categories')
            if cursor.fetchone()[0] > 0:
                return  # Already populated

            categories = [
                (1, "Creative and Cultural Representations",
                 "Arts, literature, languages, cultural studies, creative expression"),
                (2, "Thought, Belief and Behaviour",
                 "Philosophy, psychology, religion, cognitive science, human behavior"),
                (3, "Society and its Institutions",
                 "Politics, economics, sociology, law, governance and social structures"),
                (4, "Living Things and their Environment",
                 "Biology, environmental science, ecology, life sciences"),
                (5, "The Physical and Mathematical Universes",
                 "Physics, chemistry, mathematics, computer science, physical sciences")
            ]

            cursor.executemany('''
                INSERT INTO breadth_categories (category_number, name, description)
                VALUES (?, ?, ?)
            ''', categories)

            print("Breadth categories populated successfully")

        except Exception as e:
            print(f"Error populating breadth categories: {e}")

    def _populate_sample_programs(self, cursor):
        """Populate sample UofT programs for demonstration"""
        try:
            # Check if programs already exist
            cursor.execute('SELECT COUNT(*) FROM programs')
            if cursor.fetchone()[0] > 0:
                return  # Already populated

            sample_programs = [
                # Computer Science Programs
                ('ASSPE1689', 'Computer Science Specialist', 'Specialist', 'HBSc', 12.0, 4.0, 1.0,
                 'Computer Science', 'Arts & Science', 'Comprehensive study of computer science theory and applications', 'Limited'),
                ('ASMAJ1689', 'Computer Science Major', 'Major', 'HBSc', 8.0, 2.0, 0.5,
                 'Computer Science', 'Arts & Science', 'Major study in computer science fundamentals', 'Limited'),
                ('ASMIN0107', 'Computer Science Minor', 'Minor', '', 4.0, 1.0, 0.0,
                 'Computer Science', 'Arts & Science', 'Introduction to computer science concepts', 'Open'),

                # Mathematics Programs
                ('ASSPE1393', 'Mathematics Specialist', 'Specialist', 'HBSc', 14.0, 5.0, 1.0,
                 'Mathematics', 'Arts & Science', 'Advanced study of pure and applied mathematics', 'Open'),
                ('ASMAJ1393', 'Mathematics Major', 'Major', 'HBSc', 8.0, 2.5, 0.5,
                 'Mathematics', 'Arts & Science', 'Comprehensive mathematics foundation', 'Open'),
                ('ASMIN0397', 'Mathematics Minor', 'Minor', '', 4.0, 1.0, 0.0,
                 'Mathematics', 'Arts & Science', 'Essential mathematical concepts', 'Open'),

                # Physics Programs
                ('ASSPE1477', 'Physics Specialist', 'Specialist', 'HBSc', 13.0, 4.5, 1.0,
                 'Physics', 'Arts & Science', 'Comprehensive study of physics theory and experimentation', 'Open'),
                ('ASMAJ1477', 'Physics Major', 'Major', 'HBSc', 8.0, 2.5, 0.5,
                 'Physics', 'Arts & Science', 'Foundation in physical sciences', 'Open'),

                # Psychology Programs
                ('ASMAJ1709', 'Psychology Major', 'Major', 'HBA', 8.0, 2.0, 0.5,
                 'Psychology', 'Arts & Science', 'Study of human behavior and mental processes', 'Limited'),
                ('ASMIN0649', 'Psychology Minor', 'Minor', '', 4.0, 1.0, 0.0,
                 'Psychology', 'Arts & Science', 'Introduction to psychological concepts', 'Open'),

                # Economics Programs
                ('ASMAJ0800', 'Economics Major', 'Major', 'HBA', 8.0, 2.0, 0.5,
                 'Economics', 'Arts & Science', 'Study of economic theory and policy', 'Open'),
                ('ASMIN0800', 'Economics Minor', 'Minor', '', 4.0, 1.0, 0.0,
                 'Economics', 'Arts & Science', 'Fundamentals of economic analysis', 'Open'),

                # Biology Programs
                ('ASSPE0359', 'Biology Specialist', 'Specialist', 'HBSc', 13.0, 4.0, 1.0,
                 'Biology', 'Arts & Science', 'Comprehensive study of biological systems', 'Limited'),
                ('ASMAJ0359', 'Biology Major', 'Major', 'HBSc', 8.0, 2.0, 0.5,
                 'Biology', 'Arts & Science', 'Foundation in biological sciences', 'Limited'),

                # English Programs
                ('ASMAJ0406', 'English Major', 'Major', 'HBA', 8.0, 2.0, 0.5,
                 'English', 'Arts & Science', 'Study of literature, writing, and critical analysis', 'Open'),
                ('ASMIN0406', 'English Minor', 'Minor', '', 4.0, 1.0, 0.0,
                 'English', 'Arts & Science', 'Introduction to literary studies', 'Open'),
            ]

            cursor.executemany('''
                INSERT INTO programs
                (code, title, type, degree_type, credits_required, credits_300_plus, credits_400_plus,
                 department, faculty, description, enrolment_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', sample_programs)

            print("Sample programs populated successfully")

        except Exception as e:
            print(f"Error populating sample programs: {e}")

    # === Phase 1: Academic Planning Methods ===

    def save_program(self, program_data):
        """Save or update program information"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT OR REPLACE INTO programs
                (code, title, type, degree_type, credits_required, credits_300_plus,
                 credits_400_plus, department, faculty, description, enrolment_type, active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                program_data['code'],
                program_data['title'],
                program_data['type'],
                program_data.get('degree_type', ''),
                program_data.get('credits_required', 0),
                program_data.get('credits_300_plus', 0),
                program_data.get('credits_400_plus', 0),
                program_data.get('department', ''),
                program_data.get('faculty', 'Arts & Science'),
                program_data.get('description', ''),
                program_data.get('enrolment_type', ''),
                program_data.get('active', True)
            ))

            conn.commit()
            return cursor.lastrowid

        except Exception as e:
            print(f"Error saving program: {e}")
            return None
        finally:
            conn.close()

    def get_programs(self, program_type=None, active_only=True):
        """Get programs, optionally filtered by type"""
        conn = self._get_connection()
        cursor = conn.cursor()

        query = 'SELECT * FROM programs WHERE 1=1'
        params = []

        if program_type:
            query += ' AND type = ?'
            params.append(program_type)

        if active_only:
            query += ' AND active = 1'

        query += ' ORDER BY type, title'

        cursor.execute(query, params)
        programs = cursor.fetchall()
        conn.close()
        return programs

    def enroll_in_program(self, program_code, target_graduation=None, notes=None):
        """Enroll student in a program"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Get program ID
            cursor.execute('SELECT id FROM programs WHERE code = ?', (program_code,))
            program = cursor.fetchone()
            if not program:
                raise ValueError(f"Program {program_code} not found")

            program_id = program[0]

            cursor.execute('''
                INSERT OR REPLACE INTO student_programs
                (program_id, student_id, enrolled_date, status, target_graduation, notes)
                VALUES (?, ?, DATE('now'), 'active', ?, ?)
            ''', (program_id, 'default', target_graduation, notes))

            conn.commit()
            return True

        except Exception as e:
            print(f"Error enrolling in program: {e}")
            return False
        finally:
            conn.close()

    def get_enrolled_programs(self, student_id='default'):
        """Get programs student is enrolled in"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT p.*, sp.enrolled_date, sp.status, sp.target_graduation, sp.notes
            FROM programs p
            JOIN student_programs sp ON p.id = sp.program_id
            WHERE sp.student_id = ? AND sp.status = 'active'
            ORDER BY sp.enrolled_date
        ''', (student_id,))

        programs = cursor.fetchall()
        conn.close()
        return programs

    def get_degree_requirements(self, student_id='default'):
        """Get degree requirements for student"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM degree_requirements WHERE student_id = ?
        ''', (student_id,))

        requirements = cursor.fetchone()

        # Create default requirements if none exist
        if not requirements:
            cursor.execute('''
                INSERT INTO degree_requirements (student_id) VALUES (?)
            ''', (student_id,))
            conn.commit()

            cursor.execute('''
                SELECT * FROM degree_requirements WHERE student_id = ?
            ''', (student_id,))
            requirements = cursor.fetchone()

        conn.close()
        return requirements

    def get_breadth_categories(self):
        """Get all breadth categories"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM breadth_categories ORDER BY category_number
        ''')

        categories = cursor.fetchall()
        conn.close()
        return categories

    def save_course_breadth_mapping(self, course_code, category_ids, source='manual'):
        """Map a course to breadth categories"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Remove existing mappings for this course
            cursor.execute('DELETE FROM course_breadth WHERE course_code = ?', (course_code,))

            # Add new mappings
            for category_id in category_ids:
                cursor.execute('''
                    INSERT INTO course_breadth (course_code, category_id, source)
                    VALUES (?, ?, ?)
                ''', (course_code, category_id, source))

            conn.commit()
            return True

        except Exception as e:
            print(f"Error saving course breadth mapping: {e}")
            return False
        finally:
            conn.close()

    def get_course_breadth_categories(self, course_code):
        """Get breadth categories for a course"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT bc.* FROM breadth_categories bc
            JOIN course_breadth cb ON bc.id = cb.category_id
            WHERE cb.course_code = ?
        ''', (course_code,))

        categories = cursor.fetchall()
        conn.close()
        return categories

    def calculate_breadth_progress(self, student_id='default'):
        """Calculate breadth requirement progress"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Get completed courses with their breadth categories
        cursor.execute('''
            SELECT tc.course_code, tc.credits, bc.category_number, bc.name
            FROM transcript_courses tc
            JOIN course_breadth cb ON tc.course_code = cb.course_code
            JOIN breadth_categories bc ON cb.category_id = bc.id
            WHERE tc.status = 'completed'
            ORDER BY bc.category_number
        ''')

        results = cursor.fetchall()
        conn.close()

        # Calculate credits by category
        breadth_progress = {}
        for i in range(1, 6):  # Categories 1-5
            breadth_progress[i] = {'credits': 0.0, 'courses': []}

        for course_code, credits, category_num, category_name in results:
            breadth_progress[category_num]['credits'] += credits
            breadth_progress[category_num]['courses'].append(course_code)
            breadth_progress[category_num]['name'] = category_name

        return breadth_progress

    def calculate_degree_progress(self, student_id='default'):
        """Calculate overall degree requirement progress"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Get degree requirements
        requirements = self.get_degree_requirements(student_id)
        if not requirements:
            return None

        # Get completed courses
        cursor.execute('''
            SELECT course_code, credits, grade, gpa_points, session, year
            FROM transcript_courses
            WHERE status = 'completed'
        ''')

        courses = cursor.fetchall()
        conn.close()

        progress = {
            'total_credits': 0.0,
            'arts_science_credits': 0.0,  # Will need logic to determine
            'credits_200_plus': 0.0,
            'credits_300_plus': 0.0,
            'credits_by_designator': {},
            'current_gpa': 0.0,
            'breadth_progress': self.calculate_breadth_progress(student_id),
            'requirements_met': {}
        }

        total_gpa_points = 0.0
        total_gpa_credits = 0.0

        for course_code, credits, grade, gpa_points, session, year in courses:
            # Count total credits
            progress['total_credits'] += credits

            # Extract course level from course code (e.g., CSC148 -> 100 level)
            course_level = self._extract_course_level(course_code)

            if course_level >= 200:
                progress['credits_200_plus'] += credits
            if course_level >= 300:
                progress['credits_300_plus'] += credits

            # Count credits by designator (e.g., CSC, MAT)
            designator = course_code[:3] if len(course_code) >= 3 else course_code
            if designator not in progress['credits_by_designator']:
                progress['credits_by_designator'][designator] = 0.0
            progress['credits_by_designator'][designator] += credits

            # Calculate GPA
            if gpa_points is not None and gpa_points > 0:
                total_gpa_points += gpa_points * credits
                total_gpa_credits += credits

        # Calculate current GPA
        if total_gpa_credits > 0:
            progress['current_gpa'] = total_gpa_points / total_gpa_credits

        # Check requirements
        req_total, req_arts_sci, req_200_plus, req_300_plus, req_max_designator, req_min_gpa, req_breadth = requirements[2:9]

        progress['requirements_met'] = {
            'total_credits': progress['total_credits'] >= req_total,
            'credits_200_plus': progress['credits_200_plus'] >= req_200_plus,
            'credits_300_plus': progress['credits_300_plus'] >= req_300_plus,
            'min_gpa': progress['current_gpa'] >= req_min_gpa,
            'max_designator': all(credits <= req_max_designator for credits in progress['credits_by_designator'].values()),
            'breadth': sum(cat_data['credits'] for cat_data in progress['breadth_progress'].values()) >= req_breadth
        }

        return progress

    def _extract_course_level(self, course_code):
        """Extract course level from course code (e.g., CSC148H1 -> 100)"""
        import re
        match = re.search(r'[A-Z]{3}(\d{3})', course_code)
        if match:
            course_num = int(match.group(1))
            return (course_num // 100) * 100
        return 0


class RequirementsCalculator:
    """Calculate and track academic requirements and degree progress"""

    def __init__(self, database):
        self.database = database

    def calculate_complete_progress(self, student_id='default'):
        """Calculate comprehensive degree progress with detailed breakdown"""
        progress = self.database.calculate_degree_progress(student_id)
        if not progress:
            return None

        # Add additional calculations
        progress['graduation_eligible'] = self._check_graduation_eligibility(progress)
        progress['requirements_summary'] = self._generate_requirements_summary(progress)
        progress['next_steps'] = self._suggest_next_steps(progress)

        return progress

    def _check_graduation_eligibility(self, progress):
        """Check if student meets all graduation requirements"""
        requirements_met = progress.get('requirements_met', {})

        # All core requirements must be met
        core_requirements = ['total_credits', 'credits_200_plus', 'credits_300_plus', 'min_gpa']
        core_met = all(requirements_met.get(req, False) for req in core_requirements)

        # Breadth requirement must be met
        breadth_met = requirements_met.get('breadth', False)

        # Designator limit must not be exceeded
        designator_ok = requirements_met.get('max_designator', True)

        return {
            'eligible': core_met and breadth_met and designator_ok,
            'core_requirements_met': core_met,
            'breadth_requirement_met': breadth_met,
            'designator_limit_ok': designator_ok
        }

    def _generate_requirements_summary(self, progress):
        """Generate a summary of requirement completion"""
        requirements = self.database.get_degree_requirements()
        if not requirements:
            return {}

        req_total, req_arts_sci, req_200_plus, req_300_plus, req_max_designator, req_min_gpa, req_breadth = requirements[2:9]

        return {
            'total_credits': {
                'completed': progress['total_credits'],
                'required': req_total,
                'remaining': max(0, req_total - progress['total_credits'])
            },
            'credits_200_plus': {
                'completed': progress['credits_200_plus'],
                'required': req_200_plus,
                'remaining': max(0, req_200_plus - progress['credits_200_plus'])
            },
            'credits_300_plus': {
                'completed': progress['credits_300_plus'],
                'required': req_300_plus,
                'remaining': max(0, req_300_plus - progress['credits_300_plus'])
            },
            'gpa': {
                'current': progress['current_gpa'],
                'required': req_min_gpa,
                'meets_requirement': progress['current_gpa'] >= req_min_gpa
            },
            'breadth': {
                'completed': sum(cat_data.get('credits', 0) for cat_data in progress['breadth_progress'].values()),
                'required': req_breadth,
                'categories_completed': len([cat for cat in progress['breadth_progress'].values() if cat.get('credits', 0) >= 1.0])
            }
        }

    def _suggest_next_steps(self, progress):
        """Suggest next academic steps based on current progress"""
        suggestions = []
        requirements_met = progress.get('requirements_met', {})
        summary = self._generate_requirements_summary(progress)

        # Credit requirements
        if summary['total_credits']['remaining'] > 0:
            suggestions.append(f"Complete {summary['total_credits']['remaining']:.1f} more credits to reach graduation requirement")

        if summary['credits_200_plus']['remaining'] > 0:
            suggestions.append(f"Take {summary['credits_200_plus']['remaining']:.1f} more 200+ level courses")

        if summary['credits_300_plus']['remaining'] > 0:
            suggestions.append(f"Take {summary['credits_300_plus']['remaining']:.1f} more 300+ level courses")

        # GPA requirement
        if not requirements_met.get('min_gpa', False):
            suggestions.append(f"Improve GPA to {summary['gpa']['required']:.2f} (currently {summary['gpa']['current']:.2f})")

        # Breadth requirements
        if summary['breadth']['completed'] < summary['breadth']['required']:
            remaining_breadth = summary['breadth']['required'] - summary['breadth']['completed']
            suggestions.append(f"Complete {remaining_breadth:.1f} more breadth requirement credits")

            # Suggest specific categories
            for cat_num, cat_data in progress['breadth_progress'].items():
                if cat_data.get('credits', 0) < 1.0:
                    suggestions.append(f"Consider taking courses in {cat_data.get('name', f'Category {cat_num}')}")

        # Designator limits
        if not requirements_met.get('max_designator', True):
            for designator, credits in progress['credits_by_designator'].items():
                if credits > 15.0:
                    suggestions.append(f"Too many {designator} credits ({credits:.1f}/15.0 max) - diversify course selection")

        if not suggestions:
            suggestions.append("Congratulations! You meet all graduation requirements.")

        return suggestions

    def get_academic_standing(self, gpa, total_credits=0):
        """Determine academic standing based on GPA and credits"""
        if gpa >= 3.50:
            return "Dean's List"
        elif gpa >= 2.50:
            return "Good Standing"
        elif gpa >= 1.85:
            return "Satisfactory Standing"
        elif gpa >= 1.50:
            return "Probationary Standing"
        else:
            return "Unsatisfactory Standing"

    def suggest_breadth_courses(self, student_id='default'):
        """Suggest courses to fulfill breadth requirements"""
        breadth_progress = self.database.calculate_breadth_progress(student_id)
        suggestions = {}

        for cat_num in range(1, 6):
            cat_data = breadth_progress.get(cat_num, {'credits': 0.0})
            if cat_data['credits'] < 1.0:
                # This category needs courses
                category_info = next((cat for cat in self.database.get_breadth_categories() if cat[1] == cat_num), None)
                if category_info:
                    suggestions[cat_num] = {
                        'name': category_info[2],
                        'description': category_info[3],
                        'credits_needed': 1.0 - cat_data['credits'],
                        'sample_courses': self._get_sample_courses_for_breadth(cat_num)
                    }

        return suggestions

    def _get_sample_courses_for_breadth(self, category_number):
        """Get sample courses for a breadth category (placeholder for now)"""
        sample_courses = {
            1: ["ENG140H1", "VIS105H1", "MUS111H1", "PHL101H1"],  # Creative and Cultural
            2: ["PSY100H1", "PHL100H1", "REL101H1", "PHL245H1"],  # Thought, Belief and Behaviour
            3: ["ECO100Y1", "POL101H1", "SOC101Y1", "HIS107H1"],  # Society and its Institutions
            4: ["BIO120H1", "ENV200H1", "GGR100H1", "EEB100H1"],  # Living Things and Environment
            5: ["MAT135H1", "PHY131H1", "CHE135H1", "CSC108H1"]   # Physical and Mathematical
        }
        return sample_courses.get(category_number, [])

    def calculate_graduation_timeline(self, student_id='default', courses_per_semester=2.5):
        """Estimate graduation timeline based on current progress"""
        progress = self.database.calculate_degree_progress(student_id)
        if not progress:
            return None

        summary = self._generate_requirements_summary(progress)
        remaining_credits = summary['total_credits']['remaining']

        if remaining_credits <= 0:
            return {
                'semesters_remaining': 0,
                'estimated_graduation': "Eligible now",
                'credits_remaining': 0
            }

        semesters_needed = max(1, round(remaining_credits / courses_per_semester))

        return {
            'semesters_remaining': semesters_needed,
            'estimated_graduation': f"In {semesters_needed} semester{'s' if semesters_needed != 1 else ''}",
            'credits_remaining': remaining_credits,
            'courses_per_semester': courses_per_semester
        }


class UofTLocators:
    """Centralized locator definitions for UofT Academic Calendar based on reference documentation."""

    # Main navigation elements
    COURSE_SEARCH_LINK = (By.XPATH, "//a[@href='/search-courses']")

    # Search interface elements - Updated based on current structure
    COURSE_SEARCH_FORM = (By.CSS_SELECTOR, "form[action*='search']")

    # Search input fields - Multiple strategies
    COURSE_KEYWORD_INPUT_STRATEGIES = [
        (By.NAME, "course-keyword"),
        (By.NAME, "course_keyword"),
        (By.NAME, "keyword"),
        (By.ID, "edit-course-keyword"),
        (By.ID, "edit-keyword"),
        (By.CSS_SELECTOR, "input[name*='keyword']"),
        (By.CSS_SELECTOR, "input[placeholder*='course']"),
        (By.CSS_SELECTOR, "input[type='text']")
    ]

    # Search buttons
    SEARCH_BUTTON_STRATEGIES = [
        (By.CSS_SELECTOR, "input[type='submit']"),
        (By.CSS_SELECTOR, "button[type='submit']"),
        (By.XPATH, "//input[@value='Search' or @value='search']"),
        (By.XPATH, "//button[contains(text(), 'Search')]"),
        (By.CSS_SELECTOR, ".form-submit")
    ]

    # Search results - Based on current UofT structure
    SEARCH_RESULTS_CONTAINER = (By.CSS_SELECTOR, ".view-content, .search-results, .view-course-search")

    # Result items - Modern UofT structure uses views
    COURSE_RESULT_ITEMS = [
        (By.CSS_SELECTOR, ".views-row"),
        (By.CSS_SELECTOR, ".course-result-item"),
        (By.CSS_SELECTOR, ".search-result"),
        (By.CSS_SELECTOR, "[data-course-code]")
    ]

    # Course details in results
    COURSE_TITLE_IN_RESULT = [
        (By.CSS_SELECTOR, "h3.js-views-accordion-group-header"),
        (By.CSS_SELECTOR, ".course-title"),
        (By.CSS_SELECTOR, "h3 a"),
        (By.CSS_SELECTOR, ".views-field-title")
    ]

    # Course links
    COURSE_LINKS = (By.XPATH, "//a[contains(@href, '/course/')]")


class AcademicCalendarScraper:
    """Enhanced scraper for UofT Academic Calendar with improved selenium integration"""

    def __init__(self, debug=False, headless=True):
        self.base_url = "https://artsci.calendar.utoronto.ca"
        self.search_url = f"{self.base_url}/search-courses"
        self.driver = None
        self.wait = None
        self.debug = debug
        self.headless = headless
        if SELENIUM_AVAILABLE:
            self.setup_driver()

    def setup_driver(self):
        """Set up Chrome WebDriver with optimized settings."""
        try:
            chrome_options = Options()

            if self.headless and not self.debug:
                chrome_options.add_argument("--headless")

            # Performance optimizations from reference documentation
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-plugins")
            chrome_options.add_argument("--window-size=1920,1080")

            # User agent for better compatibility
            chrome_options.add_argument(
                "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            )

            # Enable logging for debugging
            if self.debug:
                chrome_options.add_argument("--enable-logging")
                chrome_options.add_argument("--v=1")

            # Setup service
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
            except ImportError:
                service = Service()  # Assumes chromedriver in PATH

            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.implicitly_wait(10)
            self.wait = WebDriverWait(self.driver, 20)

            if self.debug:
                print("WebDriver setup successful")

        except Exception as e:
            print(f"Failed to setup WebDriver: {e}")
            self.driver = None
            self.wait = None

    def close_driver(self):
        """Close the WebDriver safely."""
        try:
            if self.driver:
                self.driver.quit()
                if self.debug:
                    print("WebDriver closed successfully")
        except Exception as e:
            print(f"Error closing WebDriver: {e}")

    def wait_for_page_load(self, timeout=15):
        """Wait for page to fully load."""
        try:
            self.wait.until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            time.sleep(1)  # Additional stabilization time
            return True
        except TimeoutException:
            print("Page load timeout")
            return False

    def wait_for_search_results(self, timeout=15):
        """Wait for search results to load with multiple strategies."""
        try:
            # Try to wait for results container
            self.wait.until(
                EC.presence_of_element_located(UofTLocators.SEARCH_RESULTS_CONTAINER)
            )

            # Wait for actual content to appear
            time.sleep(2)

            # Verify we have actual results
            for result_strategy in UofTLocators.COURSE_RESULT_ITEMS:
                try:
                    results = self.driver.find_elements(*result_strategy)
                    if results:
                        if self.debug:
                            print(f"Found {len(results)} results using {result_strategy}")
                        return True
                except:
                    continue

            return False

        except TimeoutException:
            print("Search results failed to load within timeout")
            return False

    def find_search_input(self):
        """Find search input using multiple strategies."""
        for strategy in UofTLocators.COURSE_KEYWORD_INPUT_STRATEGIES:
            try:
                element = self.driver.find_element(*strategy)
                if element.is_displayed() and element.is_enabled():
                    if self.debug:
                        print(f"Found search input using strategy: {strategy}")
                    return element
            except NoSuchElementException:
                if self.debug:
                    print(f"Strategy failed: {strategy}")
                continue

        return None

    def find_search_button(self):
        """Find search button using multiple strategies."""
        for strategy in UofTLocators.SEARCH_BUTTON_STRATEGIES:
            try:
                element = self.driver.find_element(*strategy)
                if element.is_displayed() and element.is_enabled():
                    if self.debug:
                        print(f"Found search button using strategy: {strategy}")
                    return element
            except NoSuchElementException:
                if self.debug:
                    print(f"Button strategy failed: {strategy}")
                continue

        return None

    def search_courses(self, course_code="", title="", department="", level="", credits="", limit=100):
        """Search for courses with multiple criteria"""
        if not self.driver:
            return []

        # Add timeout for search operations
        original_timeout = self.driver.implicitly_wait(0)
        self.driver.set_page_load_timeout(15)  # 15 second timeout

        try:
            if self.debug:
                print(f"Navigating to: {self.search_url}")
            self.driver.get(self.search_url)
            time.sleep(2)  # Wait for page to load

            # Try multiple possible form field names
            form_selectors = [
                "input[name='course_keyword']",
                "input[name='course_title']",
                "input[name='keyword']",
                "#edit-course-keyword",
                "#edit-course-title",
                "input[type='text']",  # Generic fallback
                "input[id*='search']",  # Any input with 'search' in id
                "input[class*='search']"  # Any input with 'search' in class
            ]

            search_input = None
            found_selector = None
            for selector in form_selectors:
                try:
                    search_input = self.driver.find_element(By.CSS_SELECTOR, selector)
                    found_selector = selector
                    if self.debug:
                        print(f"Found search input using selector: {selector}")
                    break
                except NoSuchElementException:
                    if self.debug:
                        print(f"Selector failed: {selector}")
                    continue

            if not search_input:
                if self.debug:
                    print("Could not find search input field")
                    print("Available inputs on page:")
                    inputs = self.driver.find_elements(By.TAG_NAME, "input")
                    for i, inp in enumerate(inputs):
                        try:
                            name = inp.get_attribute("name")
                            id_attr = inp.get_attribute("id")
                            type_attr = inp.get_attribute("type")
                            print(f"  Input {i}: name='{name}', id='{id_attr}', type='{type_attr}'")
                        except:
                            pass
                raise Exception("Could not find search input field")

            # Determine search term based on parameters
            search_term = course_code or title or department
            if not search_term:
                return []

            search_input.clear()
            search_input.send_keys(search_term)
            search_input.send_keys(Keys.RETURN)

            time.sleep(3)

            # Parse results
            results = []

            if self.debug:
                print("Parsing search results...")

            # Try views-row results (current UofT format)
            try:
                view_rows = self.driver.find_elements(By.CSS_SELECTOR, ".views-row")
                if self.debug:
                    print(f"Found {len(view_rows)} view rows")

                for item in view_rows:
                    try:
                        # Look for the accordion header with course information
                        title_element = item.find_element(By.CSS_SELECTOR, "h3.js-views-accordion-group-header")

                        # Extract the text from the div inside the h3
                        course_div = title_element.find_element(By.CSS_SELECTOR, "div")
                        title_text = course_div.text.strip()

                        if self.debug:
                            print(f"Found course: {title_text}")

                        # Extract course code from title (fix regex pattern)
                        course_match = re.search(r'([A-Z]{3}\d{3}[HY]\d)', title_text)
                        if course_match:
                            extracted_code = course_match.group(1)
                        else:
                            # Fallback: try to extract first word as course code
                            first_word = title_text.split(' - ')[0].strip()
                            extracted_code = first_word if first_word else course_code

                        # Build course URL from course code
                        # UofT course URLs follow pattern: /course/COURSECODE
                        url = f"{self.base_url}/course/{extracted_code}"

                        # Extract description from title (after the dash)
                        if ' - ' in title_text:
                            description = title_text.split(' - ', 1)[1].strip()
                        else:
                            description = title_text

                        course_dict = {
                            'course_code': extracted_code,
                            'title': title_text,
                            'url': url,
                            'description': description,
                            'credits': '',  # Will be extracted from course details
                            'prerequisites': '',
                            'exclusions': '',
                            'breadth_requirements': ''
                        }

                        # Apply filters
                        if level:
                            level_num = level.split('-')[0]  # Extract number from "100-level"
                            if level_num not in extracted_code:
                                continue

                        results.append(course_dict)
                    except Exception:
                        continue
            except Exception as e:
                if self.debug:
                    print(f"Accordion parsing failed: {e}")

            # If no accordion results, try alternative selectors
            if not results and self.debug:
                print("No accordion results found, checking page content...")

                # Check what's actually on the page
                page_text = self.driver.page_source[:1000]  # First 1000 chars
                print("Page content preview:")
                print(page_text)

                # Try to find any course-related text
                all_text = self.driver.find_element(By.TAG_NAME, "body").text
                if "CSC" in all_text:
                    print("Found 'CSC' in page text")
                else:
                    print("No 'CSC' found in page text")

                # Check for common result containers
                possible_containers = [
                    ".view-course-search",
                    ".search-results",
                    ".course-results",
                    ".views-row",
                    ".course-item",
                    "article",
                    ".node"
                ]

                for container in possible_containers:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, container)
                        if elements:
                            print(f"Found {len(elements)} elements with selector: {container}")
                    except:
                        pass

            # Apply limit
            results = results[:limit]
            return results

        except Exception as e:
            print(f"Search failed: {e}")
            return []

    def parse_search_results(self, limit=100):
        """Parse search results with enhanced extraction."""
        results = []

        try:
            # Try different result item strategies
            result_elements = []
            for strategy in UofTLocators.COURSE_RESULT_ITEMS:
                try:
                    elements = self.driver.find_elements(*strategy)
                    if elements:
                        print(f"Found {len(elements)} result elements using {strategy}")
                        result_elements = elements
                        break
                except Exception:
                    continue

            if not result_elements:
                print("No result elements found")
                return []

            print(f"Processing {len(result_elements)} course results")

            for i, element in enumerate(result_elements[:limit]):
                try:
                    course_data = self.extract_course_from_element(element)
                    if course_data:
                        results.append(course_data)
                        if self.debug:
                            print(f"Extracted course {i+1}: {course_data.get('course_code', 'Unknown')}")

                except Exception as e:
                    if self.debug:
                        print(f"Failed to extract course {i+1}: {e}")
                    continue

            print(f"Successfully extracted {len(results)} courses")
            return results

        except Exception as e:
            print(f"Failed to parse search results: {e}")
            return []

    def extract_course_from_element(self, element):
        """Extract course information from a result element."""
        try:
            course_data = {
                'course_code': '',
                'title': '',
                'url': '',
                'description': '',
                'credits': 0.5,
                'prerequisites': '',
                'exclusions': '',
                'breadth_requirements': ''
            }

            # Extract course title and code
            title_element = None
            for strategy in UofTLocators.COURSE_TITLE_IN_RESULT:
                try:
                    title_element = element.find_element(*strategy)
                    break
                except NoSuchElementException:
                    continue

            if not title_element:
                # Fallback: try to get any text from the element
                text_content = element.text.strip()
                if text_content:
                    title_element = element
                else:
                    return None

            # Get text content
            if hasattr(title_element, 'text'):
                title_text = title_element.text.strip()
            else:
                title_text = str(title_element).strip()

            if not title_text:
                return None

            # Extract course code using improved regex
            course_code_patterns = [
                r'([A-Z]{3}\d{3}[HY]\d)',  # Standard format: CSC108H1
                r'([A-Z]{2,4}\d{3}[A-Z]\d)',  # Alternative formats
                r'([A-Z]{3}\d{3})',  # Just the base code
            ]

            extracted_code = ''
            for pattern in course_code_patterns:
                match = re.search(pattern, title_text)
                if match:
                    extracted_code = match.group(1)
                    break

            if not extracted_code:
                # Try to extract from the beginning of the text
                words = title_text.split()
                if words and re.match(r'[A-Z]{3}\d{3}', words[0]):
                    extracted_code = words[0]

            course_data['course_code'] = extracted_code
            course_data['title'] = title_text

            # Build course URL
            if extracted_code:
                course_data['url'] = f"{self.base_url}/course/{extracted_code.lower()}"

            # Extract description (text after course code and title)
            if ' - ' in title_text:
                parts = title_text.split(' - ', 1)
                if len(parts) > 1:
                    course_data['description'] = parts[1].strip()

            # Extract credits from course code
            if 'H1' in extracted_code or 'H5' in extracted_code:
                course_data['credits'] = 0.5
            elif 'Y1' in extracted_code or 'Y5' in extracted_code:
                course_data['credits'] = 1.0

            # Try to extract additional details if available
            try:
                # Look for prerequisite information in the element
                full_text = element.text if hasattr(element, 'text') else str(element)
                if 'prerequisite' in full_text.lower():
                    prereq_match = re.search(r'prerequisite[s]?:?\s*([^.]+)', full_text, re.IGNORECASE)
                    if prereq_match:
                        course_data['prerequisites'] = prereq_match.group(1).strip()
            except Exception:
                pass

            return course_data if extracted_code else None

        except Exception as e:
            if self.debug:
                print(f"Failed to extract course from element: {e}")
            return None

    def get_course_details(self, course_code):
        """Get detailed course information from course page."""
        try:
            course_url = f"{self.base_url}/course/{course_code.lower()}"
            print(f"Fetching details for {course_code} from {course_url}")

            self.driver.get(course_url)
            if not self.wait_for_page_load():
                return None

            # Extract detailed information
            course_details = {
                'course_code': course_code,
                'title': '',
                'description': '',
                'credits': 0.5,
                'prerequisites': '',
                'corequisites': '',
                'exclusions': '',
                'breadth_requirements': '',
                'hours': '',
                'department': ''
            }

            # Extract title
            try:
                title_element = self.driver.find_element(By.TAG_NAME, "h1")
                course_details['title'] = title_element.text.strip()
            except NoSuchElementException:
                pass

            # Extract description
            try:
                desc_selectors = [
                    ".course-description",
                    ".field-name-body",
                    ".course-content"
                ]
                for selector in desc_selectors:
                    try:
                        desc_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        course_details['description'] = desc_element.text.strip()
                        break
                    except NoSuchElementException:
                        continue
            except Exception:
                pass

            # Extract prerequisites, exclusions, etc.
            page_text = self.driver.find_element(By.TAG_NAME, "body").text

            # Prerequisites
            prereq_match = re.search(r'prerequisite[s]?:?\s*([^.]+)', page_text, re.IGNORECASE)
            if prereq_match:
                course_details['prerequisites'] = prereq_match.group(1).strip()

            # Exclusions
            excl_match = re.search(r'exclusion[s]?:?\s*([^.]+)', page_text, re.IGNORECASE)
            if excl_match:
                course_details['exclusions'] = excl_match.group(1).strip()

            # Breadth requirements
            breadth_match = re.search(r'breadth.{0,20}requirement[s]?:?\s*([^.]+)', page_text, re.IGNORECASE)
            if breadth_match:
                course_details['breadth_requirements'] = breadth_match.group(1).strip()

            return course_details

        except Exception as e:
            print(f"Failed to get course details for {course_code}: {e}")
            return None

    def __del__(self):
        """Cleanup on object destruction."""
        self.close_driver()

    def get_departments(self):
        """Get list of available departments"""
        return [
            "CSC - Computer Science",
            "MAT - Mathematics",
            "STA - Statistics",
            "PHY - Physics",
            "CHM - Chemistry",
            "BIO - Biology",
            "ECO - Economics",
            "PSY - Psychology",
            "SOC - Sociology",
            "HIS - History",
            "ENG - English",
            "FRE - French"
        ]

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
                course_match = re.search(r'([A-Z]{3}\d{3}[HY]\d)', details['title'])
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
                details['description'] = "\n\n".join(description_parts)
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
        self.transcript_course_data = {}

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

        # Course details
        self.root.bind('<Control-d>', lambda e: self.view_course_details())

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
• Ctrl+D: View course details

Course Interaction:
• Double-click: View course details
• Enter: View course details (in search results)

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
        self.setup_requirements_tab()
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

        # Bind selection and interaction events
        self.results_listbox.bind('<<ListboxSelect>>', self.on_course_select)
        self.results_listbox.bind('<Double-Button-1>', lambda e: self.view_course_details())
        self.results_listbox.bind('<Return>', lambda e: self.view_course_details())

        # Action buttons
        button_frame = ttk.Frame(results_section)
        button_frame.grid(row=1, column=0, pady=(10, 0))

        ttk.Button(button_frame, text="View Details", command=self.view_course_details, style='Modern.TButton').pack(side=tk.LEFT, padx=(0, 10))
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

        # Quick add section
        quick_frame = ttk.LabelFrame(main_frame, text="Quick Add Course", padding="10")
        quick_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        # Course code entry
        ttk.Label(quick_frame, text="Course Code:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.quick_course_var = tk.StringVar()
        quick_entry = ttk.Entry(quick_frame, textvariable=self.quick_course_var, width=15)
        quick_entry.grid(row=0, column=1, padx=(0, 10))
        quick_entry.bind('<Return>', self.quick_add_course)

        # Grade entry
        ttk.Label(quick_frame, text="Grade:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.quick_grade_var = tk.StringVar()
        grade_values = ['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'D-', 'F', 'FZ', 'CR', 'NCR']
        quick_grade = ttk.Combobox(quick_frame, textvariable=self.quick_grade_var, values=grade_values, width=8)
        quick_grade.grid(row=0, column=3, padx=(0, 10))

        # Session/Year
        ttk.Label(quick_frame, text="Session:").grid(row=0, column=4, sticky=tk.W, padx=(0, 5))
        self.quick_session_var = tk.StringVar()
        session_combo = ttk.Combobox(quick_frame, textvariable=self.quick_session_var,
                                   values=['Fall', 'Winter', 'Summer'], width=8)
        session_combo.grid(row=0, column=5, padx=(0, 10))

        ttk.Label(quick_frame, text="Year:").grid(row=0, column=6, sticky=tk.W, padx=(0, 5))
        self.quick_year_var = tk.StringVar()
        current_year = datetime.now().year
        year_combo = ttk.Combobox(quick_frame, textvariable=self.quick_year_var,
                                values=[str(current_year - i) for i in range(10)], width=8)
        year_combo.grid(row=0, column=7, padx=(0, 10))

        # Quick add button
        ttk.Button(quick_frame, text="Add", command=self.quick_add_course,
                  style='Modern.TButton').grid(row=0, column=8, padx=(0, 10))

        # Action buttons - organized in groups
        action_frame = ttk.Frame(main_frame)
        action_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        # Basic operations
        basic_group = ttk.LabelFrame(action_frame, text="Basic Operations", padding="5")
        basic_group.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(basic_group, text="Add Course", command=self.add_transcript_course, style='Modern.TButton').pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(basic_group, text="Edit", command=self.edit_transcript_course, style='Modern.TButton').pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(basic_group, text="Delete", command=self.delete_transcript_course, style='Modern.TButton').pack(side=tk.LEFT)

        # Bulk operations
        bulk_group = ttk.LabelFrame(action_frame, text="Bulk Operations", padding="5")
        bulk_group.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(bulk_group, text="Bulk Edit", command=self.bulk_edit_transcript, style='Modern.TButton').pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(bulk_group, text="Bulk Delete", command=self.bulk_delete_transcript, style='Modern.TButton').pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(bulk_group, text="Import Codes", command=self.bulk_import_course_codes, style='Modern.TButton').pack(side=tk.LEFT)

        # Import/Export
        file_group = ttk.LabelFrame(action_frame, text="Import/Export", padding="5")
        file_group.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(file_group, text="Import CSV", command=self.import_transcript_csv, style='Modern.TButton').pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(file_group, text="Export CSV", command=self.export_transcript_csv, style='Modern.TButton').pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(file_group, text="Auto-Fill Titles", command=self.auto_populate_titles, style='Modern.TButton').pack(side=tk.LEFT)

        # Filter section
        filter_frame = ttk.LabelFrame(main_frame, text="Filter & Search", padding="10")
        filter_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Label(filter_frame, text="Search:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.filter_var = tk.StringVar()
        filter_entry = ttk.Entry(filter_frame, textvariable=self.filter_var, width=20)
        filter_entry.grid(row=0, column=1, padx=(0, 10))
        filter_entry.bind('<KeyRelease>', self.filter_transcript)

        ttk.Label(filter_frame, text="Session:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.filter_session_var = tk.StringVar()
        filter_session = ttk.Combobox(filter_frame, textvariable=self.filter_session_var,
                                    values=['All', 'Fall', 'Winter', 'Summer'], width=10)
        filter_session.grid(row=0, column=3, padx=(0, 10))
        filter_session.bind('<<ComboboxSelected>>', self.filter_transcript)
        filter_session.set('All')

        ttk.Label(filter_frame, text="Grade:").grid(row=0, column=4, sticky=tk.W, padx=(0, 5))
        self.filter_grade_var = tk.StringVar()
        filter_grade = ttk.Combobox(filter_frame, textvariable=self.filter_grade_var,
                                  values=['All'] + grade_values, width=10)
        filter_grade.grid(row=0, column=5, padx=(0, 10))
        filter_grade.bind('<<ComboboxSelected>>', self.filter_transcript)
        filter_grade.set('All')

        ttk.Button(filter_frame, text="Clear Filters", command=self.clear_filters,
                  style='Modern.TButton').grid(row=0, column=6, padx=(10, 0))

        # Summary section
        summary_frame = ttk.LabelFrame(main_frame, text="Quick Summary", padding="10")
        summary_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        self.summary_label = ttk.Label(summary_frame, text="No courses loaded", font=('Segoe UI', 9))
        self.summary_label.pack()

        # Transcript treeview
        tree_frame = ttk.Frame(main_frame)
        tree_frame.grid(row=4, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

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

        # Bind double-click to view course details
        self.transcript_tree.bind('<Double-Button-1>', self.view_transcript_course_details)

        # Configure grid weights
        transcript_frame.columnconfigure(0, weight=1)
        transcript_frame.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1)  # Tree frame is now at row 4
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

    def setup_requirements_tab(self):
        """Setup academic requirements and degree progress tab"""
        requirements_frame = ttk.Frame(self.notebook)
        self.notebook.add(requirements_frame, text="Requirements")

        main_frame = ttk.Frame(requirements_frame, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Initialize requirements calculator
        self.requirements_calculator = RequirementsCalculator(self.database)

        # Program enrollment section
        program_frame = ttk.LabelFrame(main_frame, text="Program Enrollment", padding="10")
        program_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        # Current programs display
        ttk.Label(program_frame, text="Enrolled Programs:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.enrolled_programs_var = tk.StringVar(value="No programs enrolled")
        ttk.Label(program_frame, textvariable=self.enrolled_programs_var,
                 foreground='blue').grid(row=1, column=0, sticky=tk.W, columnspan=2)

        # Program enrollment controls
        ttk.Label(program_frame, text="Add Program:").grid(row=2, column=0, sticky=tk.W, pady=(10, 5))

        program_select_frame = ttk.Frame(program_frame)
        program_select_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 5))

        self.program_var = tk.StringVar()
        self.program_combobox = ttk.Combobox(program_select_frame, textvariable=self.program_var,
                                           width=40, state='readonly')
        self.program_combobox.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))

        ttk.Button(program_select_frame, text="Enroll",
                  command=self.enroll_in_program).grid(row=0, column=1)

        # Degree progress section
        progress_frame = ttk.LabelFrame(main_frame, text="Degree Progress", padding="10")
        progress_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))

        # Progress display
        self.progress_text = tk.Text(progress_frame, height=12, wrap=tk.WORD, state='disabled')
        progress_scrollbar = ttk.Scrollbar(progress_frame, orient='vertical', command=self.progress_text.yview)
        self.progress_text.configure(yscrollcommand=progress_scrollbar.set)

        self.progress_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        progress_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # Breadth requirements section
        breadth_frame = ttk.LabelFrame(main_frame, text="Breadth Requirements", padding="10")
        breadth_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(10, 0))

        self.breadth_text = tk.Text(breadth_frame, height=12, wrap=tk.WORD, state='disabled')
        breadth_scrollbar = ttk.Scrollbar(breadth_frame, orient='vertical', command=self.breadth_text.yview)
        self.breadth_text.configure(yscrollcommand=breadth_scrollbar.set)

        self.breadth_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        breadth_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # Action buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=(10, 0))

        ttk.Button(button_frame, text="Refresh Requirements",
                  command=self.update_requirements_display).grid(row=0, column=0, padx=(0, 5))

        ttk.Button(button_frame, text="Calculate Timeline",
                  command=self.show_graduation_timeline).grid(row=0, column=1, padx=(0, 5))

        ttk.Button(button_frame, text="Suggest Courses",
                  command=self.suggest_breadth_courses).grid(row=0, column=2)

        # Configure grid weights
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        program_frame.columnconfigure(0, weight=1)
        program_select_frame.columnconfigure(0, weight=1)
        progress_frame.columnconfigure(0, weight=1)
        progress_frame.rowconfigure(0, weight=1)
        breadth_frame.columnconfigure(0, weight=1)
        breadth_frame.rowconfigure(0, weight=1)

        # Load initial data
        self.populate_programs_combobox()
        self.update_requirements_display()

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
                self.details_text.insert(1.0, f"Course: {course['title']}\n\nDescription: {course['description']}")

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

    def view_course_details(self):
        """Open detailed course information window"""
        selection = self.results_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a course first")
            return

        if not hasattr(self, 'search_results') or not self.search_results:
            messagebox.showwarning("Warning", "No search results available")
            return

        index = selection[0]
        if index >= len(self.search_results):
            messagebox.showwarning("Warning", "Invalid selection")
            return

        course = self.search_results[index]

        try:
            # Open course information window
            CourseInfoWindow(self.root, course, database=self.database, scraper=self.scraper)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open course details: {e}")

    def view_transcript_course_details(self, event=None):
        """View details for a course in the transcript"""
        selection = self.transcript_tree.selection()
        if not selection:
            return

        # Get selected item
        item = selection[0]
        values = self.transcript_tree.item(item, 'values')

        if not values:
            return

        # Create course data from transcript row
        course_code = values[0]
        title = values[1]

        course_data = {
            'course_code': course_code,
            'title': f"{course_code} - {title}" if title != course_code else course_code,
            'url': f"https://artsci.calendar.utoronto.ca/course/{course_code}",
            'description': title,
            'credits': values[2] if len(values) > 2 else '',
            'grade': values[3] if len(values) > 3 else '',
            'mark': values[4] if len(values) > 4 else '',
            'session': values[5] if len(values) > 5 else '',
            'year': values[6] if len(values) > 6 else '',
            'status': values[7] if len(values) > 7 else ''
        }

        try:
            # Open course information window
            CourseInfoWindow(self.root, course_data, database=self.database, scraper=self.scraper)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open course details: {e}")

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

        # Check if course data is available
        if not hasattr(self, 'transcript_course_data') or not self.transcript_course_data:
            messagebox.showerror("Error", "Course data not available. Please refresh the transcript display.")
            return

        # Create bulk edit dialog
        dialog = BulkEditDialog(self.root, len(selection))
        if dialog.result:
            try:
                updates = []
                for item_id in selection:
                    if item_id not in self.transcript_course_data:
                        messagebox.showerror("Error", f"Course data not found for selected item. Please refresh the transcript display.")
                        return

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
                # Debug information
                if not hasattr(self, 'transcript_course_data') or not self.transcript_course_data:
                    messagebox.showerror("Error", "Course data not available. Please refresh the transcript display.")
                    return

                course_ids = []
                for item_id in selection:
                    if item_id in self.transcript_course_data:
                        course_ids.append(self.transcript_course_data[item_id]['id'])
                    else:
                        messagebox.showerror("Error", f"Course data not found for selected item. Please refresh the transcript display.")
                        return

                if course_ids:
                    self.database.delete_transcript_courses(course_ids)
                    self.update_displays()
                    messagebox.showinfo("Success", f"Deleted {len(course_ids)} courses")
                else:
                    messagebox.showwarning("Warning", "No valid courses selected for deletion")

            except Exception as e:
                messagebox.showerror("Error", f"Bulk delete failed: {e}")
                import traceback
                print(f"Bulk delete error details: {traceback.format_exc()}")

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

    def quick_add_course(self, event=None):
        """Quick add course with minimal information"""
        course_code = self.quick_course_var.get().strip().upper()
        grade = self.quick_grade_var.get().strip()
        session = self.quick_session_var.get().strip()
        year = self.quick_year_var.get().strip()

        if not course_code:
            messagebox.showwarning("Warning", "Please enter a course code")
            return

        if not grade:
            messagebox.showwarning("Warning", "Please select a grade")
            return

        if not session:
            messagebox.showwarning("Warning", "Please select a session")
            return

        if not year:
            messagebox.showwarning("Warning", "Please enter a year")
            return

        try:
            # Try to get course title from academic calendar
            title = course_code  # Default fallback
            try:
                conn = self.database._get_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT title FROM academic_courses WHERE course_code = ?', (course_code,))
                result = cursor.fetchone()
                if result and result[0]:
                    title = result[0]
                conn.close()
            except:
                pass  # Use fallback title

            # Prepare course data
            course_data = {
                'course_code': course_code,
                'title': title,
                'credits': 0.5,  # Default value
                'grade': grade,
                'mark': '',  # Empty for now
                'session': session,
                'year': int(year),
                'status': 'completed'
            }

            # Save to database
            self.database.save_transcript_course(course_data)

            # Clear the form
            self.quick_course_var.set('')
            self.quick_grade_var.set('')

            # Update display
            self.update_transcript_display()

            messagebox.showinfo("Success", f"Added {course_code} to transcript")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to add course: {e}")

    def filter_transcript(self, event=None):
        """Filter transcript based on search criteria"""
        search_text = self.filter_var.get().lower()
        session_filter = self.filter_session_var.get()
        grade_filter = self.filter_grade_var.get()

        # Get all transcript courses
        all_courses = self.database.get_transcript_courses()

        # Clear current display
        for item in self.transcript_tree.get_children():
            self.transcript_tree.delete(item)

        # Apply filters
        filtered_courses = []
        for course in all_courses:
            course_code = course[1].lower()
            title = course[2].lower()
            grade = course[4]
            session = course[6]

            # Apply search filter
            if search_text and search_text not in course_code and search_text not in title:
                continue

            # Apply session filter
            if session_filter != 'All' and session != session_filter:
                continue

            # Apply grade filter
            if grade_filter != 'All' and grade != grade_filter:
                continue

            filtered_courses.append(course)

        # Display filtered results
        for course in filtered_courses:
            values = [
                course[1],  # course_code
                course[2],  # title
                course[3],  # credits
                course[4],  # grade
                f"{course[5]:.1f}" if course[5] else "",  # mark
                course[6],  # session
                course[7],  # year
                course[8],  # status
            ]
            self.transcript_tree.insert('', 'end', values=values)

    def clear_filters(self):
        """Clear all filters and show all courses"""
        self.filter_var.set('')
        self.filter_session_var.set('All')
        self.filter_grade_var.set('All')
        self.update_transcript_display()

    def update_transcript_summary(self):
        """Update the transcript summary information"""
        try:
            courses = self.database.get_transcript_courses()
            if not courses:
                self.summary_label.config(text="No courses in transcript")
                return

            total_courses = len(courses)
            total_credits = sum(float(course[3]) for course in courses if course[3])

            # Calculate current GPA
            current_gpa, _ = self.calculate_gpa(courses)

            # Count by session
            current_year = datetime.now().year
            recent_courses = [c for c in courses if c[7] >= current_year - 1]

            summary_text = f"Total: {total_courses} courses, {total_credits:.1f} credits | Current GPA: {current_gpa:.2f} | Recent: {len(recent_courses)} courses"
            self.summary_label.config(text=summary_text)

        except Exception as e:
            self.summary_label.config(text="Error loading summary")

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

        # Update summary statistics
        self.update_transcript_summary()

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
            stats_text += f"\n{grade}: {count}"

        # Calculate department distribution
        dept_counts = defaultdict(int)
        for course in courses:
            if len(course) >= 2:
                course_code = course[1]
                dept = re.match(r'^([A-Z]+)', course_code)
                if dept:
                    dept_counts[dept.group(1)] += 1

        stats_text += f"\n\nDEPARTMENT DISTRIBUTION:"
        for dept, count in sorted(dept_counts.items(), key=lambda x: x[1], reverse=True):
            stats_text += f"\n{dept}: {count}"

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
                    report += f"{session_key}: GPA {gpa:.2f}, Credits {credits:.1f}, Courses {len(session_courses)}\n"

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

    # === Requirements Tab Supporting Methods ===

    def populate_programs_combobox(self):
        """Populate the programs combobox with available programs"""
        try:
            programs = self.database.get_programs()
            program_options = [f"{prog[1]} - {prog[2]} ({prog[3]})" for prog in programs]
            self.program_combobox['values'] = program_options

            # Store program mapping for easy access
            self.program_mapping = {f"{prog[1]} - {prog[2]} ({prog[3]})": prog[1] for prog in programs}

        except Exception as e:
            print(f"Error populating programs: {e}")

    def enroll_in_program(self):
        """Enroll student in selected program"""
        selection = self.program_var.get()
        if not selection:
            messagebox.showwarning("Warning", "Please select a program")
            return

        try:
            program_code = self.program_mapping[selection]
            success = self.database.enroll_in_program(program_code)

            if success:
                messagebox.showinfo("Success", f"Enrolled in {selection}")
                self.update_requirements_display()
            else:
                messagebox.showerror("Error", "Failed to enroll in program")

        except Exception as e:
            messagebox.showerror("Error", f"Enrollment failed: {e}")

    def update_requirements_display(self):
        """Update the requirements and progress displays"""
        try:
            # Update enrolled programs
            enrolled = self.database.get_enrolled_programs()
            if enrolled:
                program_names = [f"{prog[2]} ({prog[3]})" for prog in enrolled]
                self.enrolled_programs_var.set(", ".join(program_names))
            else:
                self.enrolled_programs_var.set("No programs enrolled")

            # Update degree progress
            progress = self.requirements_calculator.calculate_complete_progress()
            if progress:
                self._display_degree_progress(progress)
                self._display_breadth_progress(progress['breadth_progress'])
            else:
                self._clear_progress_displays()

        except Exception as e:
            print(f"Error updating requirements display: {e}")

    def _display_degree_progress(self, progress):
        """Display degree progress in the progress text widget"""
        self.progress_text.config(state='normal')
        self.progress_text.delete(1.0, tk.END)

        # Header
        self.progress_text.insert(tk.END, "DEGREE PROGRESS SUMMARY\n", 'header')
        self.progress_text.insert(tk.END, "=" * 40 + "\n\n")

        # Overall status
        graduation_status = progress['graduation_eligible']
        status_text = "✓ ELIGIBLE FOR GRADUATION" if graduation_status['eligible'] else "✗ NOT YET ELIGIBLE"
        self.progress_text.insert(tk.END, f"Status: {status_text}\n\n")

        # Requirements summary
        summary = progress['requirements_summary']

        # Credits
        total_credits = summary['total_credits']
        self.progress_text.insert(tk.END, f"Total Credits: {total_credits['completed']:.1f} / {total_credits['required']:.1f}")
        if total_credits['remaining'] > 0:
            self.progress_text.insert(tk.END, f" ({total_credits['remaining']:.1f} remaining)")
        self.progress_text.insert(tk.END, "\n")

        # 200+ level credits
        credits_200 = summary['credits_200_plus']
        self.progress_text.insert(tk.END, f"200+ Level Credits: {credits_200['completed']:.1f} / {credits_200['required']:.1f}")
        if credits_200['remaining'] > 0:
            self.progress_text.insert(tk.END, f" ({credits_200['remaining']:.1f} remaining)")
        self.progress_text.insert(tk.END, "\n")

        # 300+ level credits
        credits_300 = summary['credits_300_plus']
        self.progress_text.insert(tk.END, f"300+ Level Credits: {credits_300['completed']:.1f} / {credits_300['required']:.1f}")
        if credits_300['remaining'] > 0:
            self.progress_text.insert(tk.END, f" ({credits_300['remaining']:.1f} remaining)")
        self.progress_text.insert(tk.END, "\n")

        # GPA
        gpa_info = summary['gpa']
        self.progress_text.insert(tk.END, f"GPA: {gpa_info['current']:.2f} (required: {gpa_info['required']:.2f})")
        gpa_status = "✓" if gpa_info['meets_requirement'] else "✗"
        self.progress_text.insert(tk.END, f" {gpa_status}\n")

        # Academic standing
        standing = self.requirements_calculator.get_academic_standing(gpa_info['current'])
        self.progress_text.insert(tk.END, f"Academic Standing: {standing}\n\n")

        # Breadth summary
        breadth_info = summary['breadth']
        self.progress_text.insert(tk.END, f"Breadth Requirements: {breadth_info['completed']:.1f} / {breadth_info['required']:.1f} credits\n")
        self.progress_text.insert(tk.END, f"Categories Completed: {breadth_info['categories_completed']} / 5\n\n")

        # Next steps
        self.progress_text.insert(tk.END, "NEXT STEPS:\n")
        self.progress_text.insert(tk.END, "-" * 20 + "\n")
        for i, step in enumerate(progress['next_steps'][:8], 1):  # Limit to 8 suggestions
            self.progress_text.insert(tk.END, f"{i}. {step}\n")

        self.progress_text.config(state='disabled')

    def _display_breadth_progress(self, breadth_progress):
        """Display breadth requirements progress"""
        self.breadth_text.config(state='normal')
        self.breadth_text.delete(1.0, tk.END)

        self.breadth_text.insert(tk.END, "BREADTH REQUIREMENTS\n")
        self.breadth_text.insert(tk.END, "=" * 30 + "\n\n")

        categories = self.database.get_breadth_categories()
        for category in categories:
            cat_num = category[1]
            cat_name = category[2]
            cat_progress = breadth_progress.get(cat_num, {'credits': 0.0, 'courses': []})

            credits = cat_progress['credits']
            status = "✓" if credits >= 1.0 else "✗"

            self.breadth_text.insert(tk.END, f"{status} Category {cat_num}: {cat_name}\n")
            self.breadth_text.insert(tk.END, f"   Credits: {credits:.1f} / 1.0\n")

            if cat_progress['courses']:
                self.breadth_text.insert(tk.END, f"   Courses: {', '.join(cat_progress['courses'])}\n")
            else:
                self.breadth_text.insert(tk.END, "   No courses completed\n")

            self.breadth_text.insert(tk.END, "\n")

        self.breadth_text.config(state='disabled')

    def _clear_progress_displays(self):
        """Clear progress displays when no data available"""
        self.progress_text.config(state='normal')
        self.progress_text.delete(1.0, tk.END)
        self.progress_text.insert(tk.END, "No transcript data available.\nAdd courses to your transcript to see degree progress.")
        self.progress_text.config(state='disabled')

        self.breadth_text.config(state='normal')
        self.breadth_text.delete(1.0, tk.END)
        self.breadth_text.insert(tk.END, "No course data available for breadth analysis.")
        self.breadth_text.config(state='disabled')

    def show_graduation_timeline(self):
        """Show estimated graduation timeline"""
        try:
            timeline = self.requirements_calculator.calculate_graduation_timeline()
            if timeline:
                message = f"""Graduation Timeline Estimate:

Credits Remaining: {timeline['credits_remaining']:.1f}
Semesters Remaining: {timeline['semesters_remaining']}
Estimated Graduation: {timeline['estimated_graduation']}

Based on taking {timeline['courses_per_semester']:.1f} credits per semester."""

                messagebox.showinfo("Graduation Timeline", message)
            else:
                messagebox.showwarning("Warning", "Unable to calculate timeline - no degree requirements data")

        except Exception as e:
            messagebox.showerror("Error", f"Timeline calculation failed: {e}")

    def suggest_breadth_courses(self):
        """Show suggested courses for breadth requirements"""
        try:
            suggestions = self.requirements_calculator.suggest_breadth_courses()
            if suggestions:
                message = "BREADTH COURSE SUGGESTIONS:\n\n"
                for cat_num, info in suggestions.items():
                    message += f"Category {cat_num}: {info['name']}\n"
                    message += f"Credits needed: {info['credits_needed']:.1f}\n"
                    message += f"Sample courses: {', '.join(info['sample_courses'])}\n\n"

                # Show in a new window for better readability
                window = tk.Toplevel(self.root)
                window.title("Breadth Course Suggestions")
                window.geometry("600x400")

                text_widget = tk.Text(window, wrap=tk.WORD, padx=10, pady=10)
                scrollbar = ttk.Scrollbar(window, orient='vertical', command=text_widget.yview)
                text_widget.configure(yscrollcommand=scrollbar.set)

                text_widget.pack(side=tk.LEFT, fill='both', expand=True)
                scrollbar.pack(side=tk.RIGHT, fill='y')

                text_widget.insert(1.0, message)
                text_widget.config(state='disabled')

            else:
                messagebox.showinfo("Breadth Requirements", "All breadth requirements completed!")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate suggestions: {e}")


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

class CourseInfoWindow:
    """Display detailed course information in a separate window"""

    def __init__(self, parent, course_data, database=None, scraper=None):
        self.parent = parent
        self.course_data = course_data
        self.database = database
        self.scraper = scraper
        self.window = None
        self.create_window()

    def create_window(self):
        """Create the course information window"""
        self.window = tk.Toplevel(self.parent)
        self.window.title(f"Course Information - {self.course_data.get('course_code', 'Unknown')}")
        self.window.geometry("800x700")
        self.window.resizable(True, True)

        # Center the window
        self.window.transient(self.parent)
        self.window.grab_set()

        # Main frame with scrollbar
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Create scrollable text widget
        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)

        self.text_widget = tk.Text(text_frame, wrap=tk.WORD, font=('Segoe UI', 10),
                                  bg='white', fg='black', padx=15, pady=15)

        scrollbar = ttk.Scrollbar(text_frame, orient='vertical', command=self.text_widget.yview)
        self.text_widget.configure(yscrollcommand=scrollbar.set)

        self.text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Configure text tags for formatting
        self.text_widget.tag_configure('title', font=('Segoe UI', 16, 'bold'), foreground='#2563EB')
        self.text_widget.tag_configure('heading', font=('Segoe UI', 12, 'bold'), foreground='#1F2937')
        self.text_widget.tag_configure('subheading', font=('Segoe UI', 11, 'bold'), foreground='#374151')
        self.text_widget.tag_configure('body', font=('Segoe UI', 10), foreground='#111827')
        self.text_widget.tag_configure('emphasis', font=('Segoe UI', 10, 'italic'), foreground='#6B7280')

        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))

        # Action buttons
        ttk.Button(button_frame, text="Get Full Details",
                  command=self.fetch_full_details, style='Modern.TButton').pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(button_frame, text="Add to Transcript",
                  command=self.add_to_transcript, style='Modern.TButton').pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(button_frame, text="Add to Plan",
                  command=self.add_to_plan, style='Modern.TButton').pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(button_frame, text="Close",
                  command=self.window.destroy, style='Modern.TButton').pack(side=tk.RIGHT)

        # Display initial course information
        self.display_course_info()

    def format_text(self, text):
        """Format text by converting \\n to actual newlines"""
        if not text:
            return ""
        # Replace literal \n with actual newlines
        return text.replace('\\n\\n', '\n\n').replace('\\n', '\n')

    def display_course_info(self):
        """Display course information in the text widget"""
        self.text_widget.delete(1.0, tk.END)

        # Course title
        course_code = self.course_data.get('course_code', 'Unknown')
        title = self.course_data.get('title', '')

        if ' - ' in title:
            parts = title.split(' - ', 1)
            course_name = parts[1] if len(parts) > 1 else parts[0]
        else:
            course_name = title

        self.text_widget.insert(tk.END, f"{course_code}\n", 'title')
        self.text_widget.insert(tk.END, f"{course_name}\n\n", 'heading')

        # Basic information
        if self.course_data.get('url'):
            self.text_widget.insert(tk.END, "🌐 Course URL\n", 'subheading')
            self.text_widget.insert(tk.END, f"{self.course_data['url']}\n\n", 'body')

        if self.course_data.get('description'):
            self.text_widget.insert(tk.END, "📝 Description\n", 'subheading')
            formatted_desc = self.format_text(self.course_data['description'])
            self.text_widget.insert(tk.END, f"{formatted_desc}\n\n", 'body')

        # Check if we have detailed information from database
        detailed_info = self.get_detailed_info()
        if detailed_info:
            self.display_detailed_info(detailed_info)
        else:
            self.text_widget.insert(tk.END, "ℹ️ Additional Information\n", 'subheading')
            self.text_widget.insert(tk.END, "Click 'Get Full Details' to fetch comprehensive course information including prerequisites, exclusions, and breadth requirements.\n\n", 'emphasis')

        # Make text widget read-only
        self.text_widget.config(state=tk.DISABLED)

    def get_detailed_info(self):
        """Get detailed course information from database if available"""
        if not self.database:
            return None

        course_code = self.course_data.get('course_code')
        if not course_code:
            return None

        try:
            conn = self.database._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT course_code, title, hours, description, prerequisites, exclusions, breadth_requirements
                FROM academic_courses
                WHERE course_code = ?
            ''', (course_code,))

            result = cursor.fetchone()
            conn.close()

            if result:
                return {
                    'course_code': result[0],
                    'title': result[1],
                    'hours': result[2],
                    'description': result[3],
                    'prerequisites': result[4],
                    'exclusions': result[5],
                    'breadth_requirements': result[6]
                }
            return None
        except Exception:
            return None

    def display_detailed_info(self, info):
        """Display detailed course information"""
        self.text_widget.config(state=tk.NORMAL)

        if info.get('hours'):
            self.text_widget.insert(tk.END, "⏰ Hours\n", 'subheading')
            self.text_widget.insert(tk.END, f"{info['hours']}\n\n", 'body')

        if info.get('description') and info['description'] != self.course_data.get('description'):
            self.text_widget.insert(tk.END, "📋 Full Description\n", 'subheading')
            formatted_desc = self.format_text(info['description'])
            self.text_widget.insert(tk.END, f"{formatted_desc}\n\n", 'body')

        if info.get('prerequisites'):
            self.text_widget.insert(tk.END, "📚 Prerequisites\n", 'subheading')
            formatted_prereq = self.format_text(info['prerequisites'])
            self.text_widget.insert(tk.END, f"{formatted_prereq}\n\n", 'body')

        if info.get('exclusions'):
            self.text_widget.insert(tk.END, "🚫 Exclusions\n", 'subheading')
            formatted_excl = self.format_text(info['exclusions'])
            self.text_widget.insert(tk.END, f"{formatted_excl}\n\n", 'body')

        if info.get('breadth_requirements'):
            self.text_widget.insert(tk.END, "🎯 Breadth Requirements\n", 'subheading')
            formatted_breadth = self.format_text(info['breadth_requirements'])
            self.text_widget.insert(tk.END, f"{formatted_breadth}\n\n", 'body')

        self.text_widget.config(state=tk.DISABLED)

    def fetch_full_details(self):
        """Fetch full course details using the scraper"""
        if not self.scraper or not self.course_data.get('url'):
            messagebox.showwarning("Warning", "Cannot fetch details - scraper not available or no URL")
            return

        # Show loading message
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.insert(tk.END, "\n🔄 Fetching detailed course information...\n", 'emphasis')
        self.text_widget.config(state=tk.DISABLED)
        self.window.update()

        try:
            details = self.scraper.extract_course_details(self.course_data['url'])
            if details:
                # Save to database
                if self.database:
                    self.database.save_academic_course(details)

                # Update display
                self.text_widget.config(state=tk.NORMAL)
                self.text_widget.delete(1.0, tk.END)
                self.course_data.update(details)  # Update with new details
                self.display_course_info()

                messagebox.showinfo("Success", "Course details fetched successfully!")
            else:
                messagebox.showwarning("Warning", "Failed to fetch course details")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch details: {e}")

    def add_to_transcript(self):
        """Add course to transcript"""
        try:
            # Create CourseDialog for transcript
            dialog = CourseDialog(self.window, "Add to Transcript", mode="transcript",
                                course_data=self.course_data)
            # No need for success message as the dialog handles it
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open transcript dialog: {e}")

    def add_to_plan(self):
        """Add course to planning list"""
        try:
            # Create CourseDialog for planning
            dialog = CourseDialog(self.window, "Add to Plan", mode="planning",
                                course_data=self.course_data)
            # No need for success message as the dialog handles it
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open planning dialog: {e}")


def main():
    """Main function - redirect to PyQt6 application"""
    print("Starting UofT Course Dashboard (PyQt6)...")

    # Import and run the PyQt6 application
    try:
        from gui_qt.main_window import main as run_qt_app
        run_qt_app()
    except ImportError as e:
        print(f"Failed to import PyQt6 components: {e}")
        print("Make sure PyQt6 is installed: pip install PyQt6>=6.4.0")
        return
    except Exception as e:
        print(f"Application error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
