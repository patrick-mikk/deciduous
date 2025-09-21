"""
Core Components for UofT Course Dashboard
Contains database, scraper, and calculation logic without GUI dependencies
"""

import sqlite3
import os
import re
import time
import logging
from typing import List, Dict, Optional

# Selenium imports (optional)
SELENIUM_AVAILABLE = False
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.keys import Keys
    from selenium.common.exceptions import (
        NoSuchElementException, TimeoutException,
        WebDriverException, ElementNotInteractableException
    )
    SELENIUM_AVAILABLE = True
except ImportError:
    print("Selenium not installed - course search functionality will be limited")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CourseDatabase:
    """Database handler for course and transcript data"""

    def __init__(self, db_path="courses.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize the database with proper schema"""
        if not os.path.exists(self.db_path):
            print(f"Creating new database: {self.db_path}")

        conn = sqlite3.connect(self.db_path)
        try:
            self.migrate_database(conn)
        finally:
            conn.close()

    def migrate_database(self, conn):
        """Run database migrations"""
        cursor = conn.cursor()

        # Check if migrations table exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS migrations (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            )
        ''')

        # Define migrations
        migrations = [
            (1, "Initial schema", self._migration_001_initial_schema),
            (2, "Add breadth categories", self._migration_002_breadth_categories),
            (3, "Add program management", self._migration_003_program_management),
            (4, "Enhanced course details", self._migration_004_enhanced_details),
        ]

        # Get applied migrations
        cursor.execute("SELECT version FROM migrations")
        applied = {row[0] for row in cursor.fetchall()}

        # Apply pending migrations
        for version, description, migration_func in migrations:
            if version not in applied:
                try:
                    print(f"Applying migration {version}: {description}")
                    migration_func(cursor)
                    cursor.execute("INSERT INTO migrations (version, description) VALUES (?, ?)",
                                 (version, description))
                    print(f"Migration {version} completed successfully")
                except Exception as e:
                    print(f"Migration {version} failed: {e}")
                    raise

    def _migration_001_initial_schema(self, cursor):
        """Migration 1: Original database schema"""
        cursor.executescript('''
            CREATE TABLE IF NOT EXISTS courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_code TEXT UNIQUE NOT NULL,
                title TEXT,
                credits REAL DEFAULT 0.5,
                grade TEXT,
                semester TEXT,
                year INTEGER,
                gpa_points REAL,
                status TEXT DEFAULT 'completed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS planned_courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_code TEXT NOT NULL,
                title TEXT,
                credits REAL DEFAULT 0.5,
                planned_semester TEXT,
                planned_year INTEGER,
                priority INTEGER DEFAULT 1,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS course_details (
                course_code TEXT PRIMARY KEY,
                title TEXT,
                description TEXT,
                prerequisites TEXT,
                exclusions TEXT,
                breadth_requirements TEXT,
                department TEXT,
                level INTEGER,
                credits REAL,
                url TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')

    def _migration_002_breadth_categories(self, cursor):
        """Migration 2: Add breadth requirement categories"""
        cursor.executescript('''
            CREATE TABLE IF NOT EXISTS breadth_categories (
                id INTEGER PRIMARY KEY,
                category_number INTEGER UNIQUE,
                title TEXT NOT NULL,
                description TEXT,
                required_courses INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS course_breadth_mapping (
                course_code TEXT,
                breadth_category INTEGER,
                PRIMARY KEY (course_code, breadth_category),
                FOREIGN KEY (breadth_category) REFERENCES breadth_categories(category_number)
            );
        ''')

    def _migration_003_program_management(self, cursor):
        """Migration 3: Add program and degree management"""
        cursor.executescript('''
            CREATE TABLE IF NOT EXISTS programs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                program_code TEXT UNIQUE NOT NULL,
                program_name TEXT NOT NULL,
                program_type TEXT NOT NULL,
                faculty TEXT,
                total_credits REAL DEFAULT 20.0,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS student_enrollments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                program_id INTEGER,
                enrollment_date DATE,
                expected_graduation DATE,
                status TEXT DEFAULT 'active',
                FOREIGN KEY (program_id) REFERENCES programs(id)
            );

            CREATE TABLE IF NOT EXISTS program_requirements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                program_id INTEGER,
                requirement_type TEXT NOT NULL,
                requirement_description TEXT,
                required_credits REAL,
                required_courses INTEGER,
                course_list TEXT,
                FOREIGN KEY (program_id) REFERENCES programs(id)
            );
        ''')

    def _migration_004_enhanced_details(self, cursor):
        """Migration 4: Enhanced course details and analytics"""
        # Add columns only if they don't exist
        columns_to_add = [
            ("courses", "corequisites", "TEXT DEFAULT ''"),
            ("courses", "hours", "TEXT DEFAULT ''"),
            ("courses", "distribution_requirement", "TEXT DEFAULT ''"),
            ("courses", "last_offered", "TEXT DEFAULT ''"),
            ("course_details", "corequisites", "TEXT DEFAULT ''"),
            ("course_details", "hours", "TEXT DEFAULT ''"),
        ]

        for table, column, definition in columns_to_add:
            try:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
            except Exception:
                # Column already exists, skip
                pass

    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)

    def save_course(self, course_data):
        """Save course to transcript"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO courses
                (course_code, title, credits, grade, semester, year, gpa_points, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                course_data.get('course_code', ''),
                course_data.get('title', ''),
                course_data.get('credits', 0.5),
                course_data.get('grade', ''),
                course_data.get('semester', ''),
                course_data.get('year', ''),
                course_data.get('gpa_points', 0.0),
                course_data.get('status', 'completed')
            ))
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            print(f"Error saving course: {e}")
            return None
        finally:
            conn.close()

    def get_transcript_courses(self):
        """Get all courses from transcript"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT course_code, title, credits, grade, semester, year, gpa_points, status
                FROM courses ORDER BY year DESC, semester, course_code
            ''')
            return cursor.fetchall()
        finally:
            conn.close()

    def delete_course(self, course_code):
        """Delete course from transcript"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM courses WHERE course_code = ?', (course_code,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error deleting course: {e}")
            return False
        finally:
            conn.close()

    def save_course_details(self, course_details):
        """Save detailed course information"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO course_details
                (course_code, title, description, prerequisites, exclusions,
                 breadth_requirements, department, level, credits, url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                course_details.get('course_code', ''),
                course_details.get('title', ''),
                course_details.get('description', ''),
                course_details.get('prerequisites', ''),
                course_details.get('exclusions', ''),
                course_details.get('breadth_requirements', ''),
                course_details.get('department', ''),
                course_details.get('level', 0),
                course_details.get('credits', 0.5),
                course_details.get('url', '')
            ))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error saving course details: {e}")
            return False
        finally:
            conn.close()


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

    def search_courses(self, course_code="", title="", department="", level="", credits="", limit=100):
        """Enhanced course search with improved error handling."""
        if not self.driver:
            print("WebDriver not available")
            return []

        try:
            print(f"Starting course search for: {course_code or title or department}")

            # Navigate to search page
            self.driver.get(self.search_url)
            if not self.wait_for_page_load():
                print("Failed to load search page")
                return []

            # Find and use search input
            search_input = self.find_search_input()
            if not search_input:
                raise Exception("Could not find search input field")

            # Determine search term
            search_term = course_code or title or department
            if not search_term:
                print("No search term provided")
                return []

            # Perform search
            search_input.clear()
            search_input.send_keys(search_term)
            search_input.send_keys(Keys.RETURN)

            # Wait for results and parse
            if not self.wait_for_search_results():
                return []

            return self.parse_search_results(limit)

        except Exception as e:
            print(f"Course search failed: {e}")
            return []

    def wait_for_page_load(self, timeout=15):
        """Wait for page to fully load."""
        try:
            self.wait.until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            time.sleep(1)
            return True
        except TimeoutException:
            print("Page load timeout")
            return False

    def wait_for_search_results(self, timeout=15):
        """Wait for search results to load with multiple strategies."""
        try:
            self.wait.until(
                EC.presence_of_element_located(UofTLocators.SEARCH_RESULTS_CONTAINER)
            )
            time.sleep(2)
            return True
        except TimeoutException:
            print("Search results failed to load within timeout")
            return False

    def find_search_input(self):
        """Find search input using multiple strategies."""
        for strategy in UofTLocators.COURSE_KEYWORD_INPUT_STRATEGIES:
            try:
                element = self.driver.find_element(*strategy)
                if element.is_displayed() and element.is_enabled():
                    return element
            except NoSuchElementException:
                continue
        return None

    def parse_search_results(self, limit=100):
        """Parse search results with enhanced extraction."""
        results = []
        try:
            # Find result elements using multiple strategies
            result_elements = []
            for strategy in UofTLocators.COURSE_RESULT_ITEMS:
                try:
                    elements = self.driver.find_elements(*strategy)
                    if elements:
                        result_elements = elements
                        break
                except Exception:
                    continue

            if not result_elements:
                return []

            # Extract course data from each element
            for element in result_elements[:limit]:
                try:
                    course_data = self.extract_course_from_element(element)
                    if course_data:
                        results.append(course_data)
                except Exception:
                    continue

            return results

        except Exception as e:
            print(f"Failed to parse search results: {e}")
            return []

    def extract_course_from_element(self, element):
        """Extract course information from a result element."""
        try:
            # Get text content
            title_text = element.text.strip()
            if not title_text:
                return None

            # Extract course code using regex
            course_code_match = re.search(r'([A-Z]{3}\d{3}[HY]\d)', title_text)
            if not course_code_match:
                return None

            extracted_code = course_code_match.group(1)

            # Build course data
            course_data = {
                'course_code': extracted_code,
                'title': title_text,
                'url': f"{self.base_url}/course/{extracted_code.lower()}",
                'description': '',
                'credits': 0.5 if 'H' in extracted_code else 1.0,
                'prerequisites': '',
                'exclusions': '',
                'breadth_requirements': ''
            }

            # Extract description if available
            if ' - ' in title_text:
                parts = title_text.split(' - ', 1)
                if len(parts) > 1:
                    course_data['description'] = parts[1].strip()

            return course_data

        except Exception:
            return None

    def __del__(self):
        """Cleanup on object destruction."""
        self.close_driver()


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