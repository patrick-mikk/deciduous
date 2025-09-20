# API Reference - UofT Course Search Tool

## Overview

This document provides a comprehensive reference for all classes, methods, and data structures in the UofT Course Search Tool.

## Table of Contents

- [CourseDatabase](#coursedatabase)
- [AcademicCalendarScraper](#academiccalendarscraper)
- [CourseSearchGUI](#coursesearchgui)
- [Data Structures](#data-structures)
- [Constants and Configuration](#constants-and-configuration)

---

## CourseDatabase

Handles all database operations for storing and retrieving course information.

### Constructor

```python
CourseDatabase(db_path="courses.db")
```

**Parameters:**
- `db_path` (str, optional): Path to SQLite database file. Defaults to "courses.db".

**Description:** Initializes database connection and creates tables if they don't exist.

### Methods

#### `init_database()`

```python
def init_database() -> None
```

**Description:** Creates the courses table with the required schema if it doesn't exist.

**SQL Schema:**
```sql
CREATE TABLE IF NOT EXISTS courses (
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
```

**Raises:** `sqlite3.Error` if database creation fails.

#### `save_course(course_data)`

```python
def save_course(course_data: dict) -> None
```

**Parameters:**
- `course_data` (dict): Dictionary containing course information

**Required Keys:**
- `course_code` (str): Unique course identifier (e.g., "CSC148H1")
- `title` (str): Full course title
- `hours` (str): Course hours/credits
- `description` (str): Course description
- `prerequisites` (str): Prerequisite requirements
- `exclusions` (str): Mutually exclusive courses
- `breadth_requirements` (str): Breadth requirement categories
- `url` (str): Direct link to course page

**Description:** Inserts or updates course information in the database.

**Behavior:** Uses `INSERT OR REPLACE` to handle duplicate course codes.

**Raises:** `sqlite3.Error` if database operation fails.

#### `get_all_courses()`

```python
def get_all_courses() -> List[Tuple]
```

**Returns:** List of tuples containing all course data, ordered by course_code.

**Tuple Structure:**
```python
(id, course_code, title, hours, description, prerequisites,
 exclusions, breadth_requirements, url, created_at)
```

**Description:** Retrieves all stored courses from the database.

---

## AcademicCalendarScraper

Handles web scraping operations using Selenium WebDriver.

### Constructor

```python
AcademicCalendarScraper()
```

**Description:** Initializes the scraper with Chrome WebDriver and sets up base URLs.

**Attributes:**
- `base_url` (str): "https://artsci.calendar.utoronto.ca"
- `search_url` (str): "{base_url}/search-courses"
- `driver` (WebDriver): Chrome WebDriver instance

### Methods

#### `setup_driver()`

```python
def setup_driver() -> None
```

**Description:** Configures and initializes Chrome WebDriver with optimal settings.

**Chrome Options:**
- `--headless`: Runs browser without GUI
- `--no-sandbox`: Bypasses OS security model
- `--disable-dev-shm-usage`: Prevents memory issues
- `--disable-gpu`: Disables GPU acceleration
- `--window-size=1920,1080`: Sets consistent viewport
- Custom User-Agent string

**Raises:** `Exception` if WebDriver setup fails.

#### `close_driver()`

```python
def close_driver() -> None
```

**Description:** Safely closes the WebDriver and releases resources.

#### `search_courses(course_code)`

```python
def search_courses(course_code: str) -> List[dict]
```

**Parameters:**
- `course_code` (str): Course code or keyword to search for

**Returns:** List of dictionaries containing search results.

**Result Dictionary Structure:**
```python
{
    'course_code': str,      # e.g., "CSC148H1"
    'title': str,            # e.g., "CSC148H1 - Introduction to Computer Science"
    'url': str,              # Direct link to course page
    'description': str       # Brief course description (truncated to 200 chars)
}
```

**Description:** Searches for courses on the UofT Academic Calendar website.

**Search Strategy:**
1. Navigates to search page
2. Tries multiple form field selectors
3. Submits search query
4. Parses results using multiple parsing strategies

**Raises:** `Exception` if search operation fails.

#### `extract_course_details(course_url)`

```python
def extract_course_details(course_url: str) -> dict
```

**Parameters:**
- `course_url` (str): Direct URL to course page

**Returns:** Dictionary containing detailed course information.

**Result Dictionary Structure:**
```python
{
    'title': str,                    # Full course title
    'hours': str,                    # Course hours/credits
    'description': str,              # Complete course description
    'prerequisites': str,            # Prerequisite requirements
    'exclusions': str,               # Mutually exclusive courses
    'breadth_requirements': str,     # Breadth requirement categories
    'url': str                       # Course page URL
}
```

**Description:** Extracts comprehensive course information from individual course pages.

**CSS Selectors Used:**
- Title: `#block-w3css-subtheme-page-title h1.page-title`
- Hours: `.field--name-field-hours .field__item p`
- Description: `#block-w3css-subtheme-content > article > div > div.w3-row.field.field--name-body.field--type-text-with-summary.field--label-hidden.w3-bar-item.field__item` (extracts all paragraphs, with fallback)
- Prerequisites: `.field--name-field-prerequisite .field__item`
- Exclusions: `.field--name-field-exclusion .field__item`
- Breadth: `.field--name-field-breadth-requirements .field__items`

**Raises:** `Exception` if detail extraction fails.

---

## CourseSearchGUI

Provides the graphical user interface for the application.

### Constructor

```python
CourseSearchGUI()
```

**Description:** Initializes the GUI application with all components.

**Window Properties:**
- Title: "UofT Academic Calendar Course Search"
- Size: 1000x700 pixels
- Resizable: Yes

**Components Initialized:**
- Search frame with input field and button
- Results listbox with scrollbar
- Course details text area
- Database management buttons
- Status bar

### Methods

#### `setup_gui()`

```python
def setup_gui() -> None
```

**Description:** Creates and arranges all GUI components using tkinter.

**Layout Structure:**
- Grid-based layout with responsive sizing
- Proper weight configuration for resizing
- Scrollbars for overflow content

#### `search_courses()`

```python
def search_courses() -> None
```

**Description:** Handles course search events from the GUI.

**Process Flow:**
1. Validates user input
2. Updates status to "Searching..."
3. Calls scraper with search terms
4. Populates results listbox
5. Updates status with result count
6. Handles and displays errors

**User Feedback:**
- Real-time status updates
- Progress indication
- Error message dialogs

#### `extract_selected_course()`

```python
def extract_selected_course() -> None
```

**Description:** Extracts details for the selected course from search results.

**Process Flow:**
1. Validates course selection
2. Updates status to "Extracting course details..."
3. Calls scraper for detailed information
4. Displays course details in text area
5. Saves course to database
6. Updates status confirmation

**Error Handling:**
- Selection validation
- Network error handling
- Database error handling

#### `display_course_details(course_details)`

```python
def display_course_details(course_details: dict) -> None
```

**Parameters:**
- `course_details` (dict): Dictionary containing course information

**Description:** Formats and displays course details in the text widget.

**Display Format:**
```
COURSE TITLE: {title}

COURSE CODE: {course_code}

HOURS: {hours}

DESCRIPTION:
{description}

PREREQUISITES:
{prerequisites}

EXCLUSIONS:
{exclusions}

BREADTH REQUIREMENTS:
{breadth_requirements}

URL: {url}
```

#### `view_saved_courses()`

```python
def view_saved_courses() -> None
```

**Description:** Opens a new window displaying all saved courses in a table format.

**Window Features:**
- Treeview widget with sortable columns
- Scrollbar for large datasets
- Columns: Course Code, Title, Hours, Created Date
- Close button

#### `run()`

```python
def run() -> None
```

**Description:** Starts the GUI application main loop.

**Cleanup:** Automatically closes scraper WebDriver when application exits.

---

## Data Structures

### Course Data Dictionary

Standard structure for course information throughout the application:

```python
course_data = {
    'course_code': str,          # Unique identifier (e.g., "CSC148H1")
    'title': str,                # Full course title
    'hours': str,                # Course hours/credits
    'description': str,          # Course description
    'prerequisites': str,        # Prerequisite requirements
    'exclusions': str,           # Mutually exclusive courses
    'breadth_requirements': str, # Breadth requirement categories
    'url': str                   # Direct link to course page
}
```

### Search Result Dictionary

Simplified structure for search results:

```python
search_result = {
    'course_code': str,      # Course identifier
    'title': str,            # Display title
    'url': str,              # Link to full course page
    'description': str       # Brief description (max 200 chars)
}
```

### Database Row Tuple

Structure returned by `get_all_courses()`:

```python
course_row = (
    id,                      # int: Primary key
    course_code,             # str: Course identifier
    title,                   # str: Course title
    hours,                   # str: Course hours
    description,             # str: Full description
    prerequisites,           # str: Prerequisites
    exclusions,              # str: Exclusions
    breadth_requirements,    # str: Breadth requirements
    url,                     # str: Course URL
    created_at               # str: Timestamp
)
```

---

## Constants and Configuration

### URL Constants

```python
BASE_URL = "https://artsci.calendar.utoronto.ca"
SEARCH_URL = f"{BASE_URL}/search-courses"
```

### Chrome WebDriver Options

```python
CHROME_OPTIONS = [
    "--headless",               # Run without GUI
    "--no-sandbox",             # Bypass OS security
    "--disable-dev-shm-usage",  # Prevent memory issues
    "--disable-gpu",            # Disable GPU acceleration
    "--window-size=1920,1080"   # Consistent viewport
]
```

### User Agent String

```python
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
```

### Timeout Settings

```python
IMPLICIT_WAIT = 10          # Seconds to wait for elements
PAGE_LOAD_TIMEOUT = 3       # Seconds to wait after form submission
```

### GUI Configuration

```python
WINDOW_SIZE = "1000x700"    # Main window dimensions
LISTBOX_HEIGHT = 8          # Results listbox height
DETAILS_HEIGHT = 15         # Course details text height
```

### Regular Expression Patterns

```python
COURSE_CODE_PATTERN = r'^([A-Z]{3}\d{3}[HY]\d)'  # Match course codes like CSC148H1
URL_COURSE_PATTERN = r'/course/([A-Z]{3}\d{3}[HY]\d)'  # Extract from URLs
```

---

## Error Handling

### Exception Types

The application handles several types of exceptions:

#### Selenium Exceptions
- `TimeoutException`: Element not found within timeout
- `NoSuchElementException`: Element not present on page
- `WebDriverException`: General WebDriver errors

#### Database Exceptions
- `sqlite3.Error`: Database operation errors
- `sqlite3.IntegrityError`: Constraint violations

#### GUI Exceptions
- `tk.TclError`: tkinter widget errors

### Error Response Patterns

```python
try:
    # Operation that might fail
    result = risky_operation()
except SpecificException as e:
    # Handle specific error type
    self.status_var.set("Specific error occurred")
    messagebox.showerror("Error", f"Operation failed: {e}")
except Exception as e:
    # Handle general errors
    self.status_var.set("Error occurred")
    messagebox.showerror("Error", f"Unexpected error: {e}")
```

---

## Usage Examples

### Basic Scraper Usage

```python
from course_search import AcademicCalendarScraper

# Initialize scraper
scraper = AcademicCalendarScraper()

try:
    # Search for courses
    results = scraper.search_courses("CSC148")
    print(f"Found {len(results)} courses")

    # Extract details for first result
    if results:
        details = scraper.extract_course_details(results[0]['url'])
        print(f"Course: {details['title']}")
        print(f"Prerequisites: {details['prerequisites']}")

finally:
    # Always clean up
    scraper.close_driver()
```

### Database Operations

```python
from course_search import CourseDatabase

# Initialize database
db = CourseDatabase()

# Save course data
course_data = {
    'course_code': 'CSC148H1',
    'title': 'Introduction to Computer Science',
    'hours': '36L/24P',
    'description': 'Abstract data types...',
    'prerequisites': 'CSC108H1',
    'exclusions': 'CSC111H1',
    'breadth_requirements': 'The Physical and Mathematical Universes (5)',
    'url': 'https://artsci.calendar.utoronto.ca/course/CSC148H1'
}

db.save_course(course_data)

# Retrieve all courses
courses = db.get_all_courses()
for course in courses:
    print(f"{course[1]}: {course[2]}")  # course_code: title
```

### GUI Application

```python
from course_search import CourseSearchGUI

# Create and run application
app = CourseSearchGUI()
app.run()  # Starts the GUI main loop
```

This API reference provides comprehensive documentation for all public interfaces in the UofT Course Search Tool.