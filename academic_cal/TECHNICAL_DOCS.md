# Technical Documentation - UofT Course Search Tool

## Overview

This document provides detailed technical information about the implementation, architecture, and maintenance of the UofT Academic Calendar Course Search Tool.

## System Architecture

### High-Level Design

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   GUI Layer     │    │  Scraping Layer │    │  Data Layer     │
│ (CourseSearchGUI)│───►│(AcademicCalendar│───►│(CourseDatabase) │
│                 │    │    Scraper)     │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
    ┌────▼────┐            ┌─────▼─────┐          ┌─────▼─────┐
    │ tkinter │            │ Selenium  │          │  SQLite   │
    │   GUI   │            │ WebDriver │          │ Database  │
    └─────────┘            └───────────┘          └───────────┘
```

### Component Interaction Flow

1. **User Input** → GUI captures search terms
2. **Search Request** → GUI calls scraper with search terms
3. **Web Scraping** → Scraper uses Selenium to interact with UofT website
4. **Data Parsing** → BeautifulSoup parses HTML results
5. **Data Storage** → Results saved to SQLite database
6. **Display** → GUI shows results to user

## Detailed Component Analysis

### 1. CourseDatabase Class

**Purpose**: Manages all database operations and data persistence.

**Key Methods**:
- `__init__(db_path="courses.db")`: Initializes database connection
- `init_database()`: Creates database schema if not exists
- `save_course(course_data)`: Inserts or updates course information
- `get_all_courses()`: Retrieves all stored courses

**Database Schema**:
```sql
courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_code TEXT UNIQUE,           -- e.g., "CSC148H1"
    title TEXT,                        -- e.g., "Introduction to Computer Science"
    hours TEXT,                        -- e.g., "36L/24P"
    description TEXT,                  -- Full course description
    prerequisites TEXT,                -- Prerequisite courses
    exclusions TEXT,                   -- Mutually exclusive courses
    breadth_requirements TEXT,         -- Breadth requirement categories
    url TEXT,                         -- Direct link to course page
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

**Error Handling**:
- Uses `INSERT OR REPLACE` to handle duplicate course codes
- Automatic database creation on first run
- Graceful handling of connection failures

### 2. AcademicCalendarScraper Class

**Purpose**: Handles all web scraping operations using Selenium WebDriver.

#### WebDriver Configuration

**Chrome Options**:
```python
chrome_options = Options()
chrome_options.add_argument("--headless")              # No GUI
chrome_options.add_argument("--no-sandbox")            # Bypass OS security
chrome_options.add_argument("--disable-dev-shm-usage") # Overcome limited resource
chrome_options.add_argument("--disable-gpu")           # Disable GPU acceleration
chrome_options.add_argument("--window-size=1920,1080") # Consistent viewport
```

**Driver Management**:
- Uses `webdriver-manager` for automatic ChromeDriver installation
- Implements proper cleanup with `__del__()` method
- 10-second implicit wait timeout

#### Search Strategy

The scraper implements a multi-step search strategy:

1. **Navigation**: Load the search page
2. **Form Detection**: Try multiple form field selectors:
   ```python
   # Primary: General keyword search
   search_input = driver.find_element(By.NAME, "course_keyword")

   # Fallback: Specific course title search
   search_input = driver.find_element(By.NAME, "course_title")

   # Last resort: Any text input
   search_input = driver.find_element(By.CSS_SELECTOR, "input[type='text']")
   ```

3. **Form Submission**: Multiple button selector strategies:
   ```python
   # Preferred submit button
   submit_button = driver.find_element(By.CSS_SELECTOR, "input[data-drupal-selector='edit-submit-course-search']")

   # Fallback submit button
   submit_button = driver.find_element(By.CSS_SELECTOR, "input[value='Apply']")
   ```

#### Result Parsing Strategy

The scraper uses a hierarchical parsing approach to handle different page formats:

**Primary Parser - Accordion Format**:
```python
accordion_headers = soup.find_all('h3', class_='js-views-accordion-group-header')
for header in accordion_headers:
    title_div = header.find('div')
    course_title = title_div.get_text(strip=True)
    # Extract course code using regex
    course_code_match = re.match(r'^([A-Z]{3}\d{3}[HY]\d)', course_title)
```

**Fallback Parser - Row Format**:
```python
course_rows = soup.find_all('div', class_='w3-row views-row')
for row in course_rows:
    course_link = row.find('a')
    if course_link and '/course/' in course_link.get('href', ''):
        # Process course link
```

**Legacy Parser**:
```python
view_content = soup.find('div', class_='view-content')
course_links = view_content.find_all('h3')
# Process legacy format
```

#### Course Detail Extraction

**Process**:
1. Navigate to individual course page
2. Wait for page load
3. Parse structured data using CSS selectors:
   ```python
   selectors = {
       'title': '#block-w3css-subtheme-page-title h1.page-title',
       'hours': '.field--name-field-hours .field__item p',
       'description': '.field--name-body.field--type-text-with-summary',
       'prerequisites': '.field--name-field-prerequisite .field__item',
       'exclusions': '.field--name-field-exclusion .field__item',
       'breadth_requirements': '.field--name-field-breadth-requirements .field__items'
   }
   ```

### 3. CourseSearchGUI Class

**Purpose**: Provides the user interface and coordinates interactions between components.

#### GUI Layout Structure

```
Main Window (1000x700)
├── Search Frame
│   ├── Label: "Course Code:"
│   ├── Entry: course_entry
│   └── Button: search_button
├── Results Frame
│   ├── Listbox: results_listbox (with scrollbar)
│   └── Button: "Extract Course Details"
├── Details Frame
│   └── ScrolledText: details_text
├── Database Frame
│   └── Button: "View All Saved Courses"
└── Status Bar
    └── Label: status_var
```

#### Event Handling

**Search Event Flow**:
1. User input validation
2. Status update to "Searching..."
3. Scraper invocation
4. Result processing and display
5. Status update with result count
6. Error handling with user feedback

**Detail Extraction Flow**:
1. Selection validation
2. Status update to "Extracting..."
3. Detail scraper invocation
4. Database storage
5. GUI display update
6. Status confirmation

## Error Handling Strategy

### Selenium Errors

**TimeoutException**:
```python
try:
    element = wait.until(EC.presence_of_element_located((By.NAME, "course_keyword")))
except TimeoutException:
    # Fallback to alternative selectors
```

**NoSuchElementException**:
```python
try:
    search_input = driver.find_element(By.NAME, "course_title")
except NoSuchElementException:
    # Try alternative field names
```

### Database Errors

**Connection Handling**:
```python
try:
    conn = sqlite3.connect(self.db_path)
    # Database operations
finally:
    conn.close()  # Always close connection
```

### GUI Error Display

```python
try:
    # Operation that might fail
    result = some_operation()
except Exception as e:
    self.status_var.set("Error occurred")
    messagebox.showerror("Error", f"Operation failed: {e}")
```

## Performance Optimization

### WebDriver Optimization

1. **Connection Reuse**: Single WebDriver instance per scraper
2. **Implicit Waits**: 10-second timeout for element location
3. **Headless Mode**: Reduced resource consumption
4. **Window Size**: Consistent 1920x1080 for reliable rendering

### Database Optimization

1. **Indexing**: Primary key on `id`, unique constraint on `course_code`
2. **Connection Management**: Open/close connections per operation
3. **Batch Operations**: Single transaction for multiple inserts

### GUI Responsiveness

1. **Status Updates**: Real-time feedback during operations
2. **Error Handling**: Non-blocking error dialogs
3. **Progressive Loading**: Results displayed as found

## Testing Strategy

### Unit Testing Structure

```python
def test_database_operations():
    """Test database creation, insertion, and retrieval"""

def test_scraper_initialization():
    """Test WebDriver setup and configuration"""

def test_search_functionality():
    """Test course search with various inputs"""

def test_detail_extraction():
    """Test individual course detail scraping"""

def test_gui_components():
    """Test GUI initialization and event handling"""
```

### Integration Testing

1. **End-to-End Search**: Complete search → extract → save workflow
2. **Error Recovery**: Network failures, malformed pages
3. **Data Consistency**: Database integrity after operations

## Maintenance Guidelines

### Regular Updates Required

1. **CSS Selectors**: UofT website changes may require selector updates
2. **Form Fields**: New form structures need handling code
3. **Chrome Version**: WebDriver compatibility with Chrome updates

### Monitoring Points

1. **Search Success Rate**: Track failed searches
2. **Parsing Accuracy**: Verify extracted data quality
3. **Performance Metrics**: Search and extraction times

### Version Control Strategy

```
academic_cal/
├── course_search.py          # Main application
├── README.md                 # User documentation
├── TECHNICAL_DOCS.md         # This file
├── CHANGELOG.md              # Version history
└── tests/
    ├── test_database.py
    ├── test_scraper.py
    └── test_gui.py
```

## Deployment Considerations

### System Requirements

- **Python**: 3.7+ (tested on 3.13)
- **RAM**: 500MB minimum (200MB for Chrome, 300MB for Python)
- **Storage**: 50MB for application + variable for database
- **Network**: Stable internet connection required

### Security Considerations

1. **User Agent**: Mimics real browser to avoid blocking
2. **Rate Limiting**: Reasonable delays between requests
3. **Data Privacy**: Only public course information is scraped
4. **Local Storage**: All data stored locally, no external transmission

### Scalability Limits

1. **Database Size**: SQLite handles thousands of courses efficiently
2. **Concurrent Users**: Single-user desktop application
3. **Search Volume**: Respectful of UofT server resources

## Future Enhancement Opportunities

### Potential Features

1. **Batch Search**: Multiple course codes at once
2. **Export Functionality**: CSV/Excel export of saved courses
3. **Advanced Filters**: Search by prerequisites, breadth requirements
4. **Course Comparison**: Side-by-side course comparison
5. **Update Notifications**: Alert when course information changes

### Technical Improvements

1. **Caching Layer**: Redis for frequently accessed courses
2. **API Integration**: Direct UofT API if available
3. **Async Operations**: Non-blocking scraping operations
4. **Configuration File**: User-customizable settings
5. **Logging System**: Detailed operation logging

## Troubleshooting Guide

### Development Environment Setup

```bash
# Virtual environment setup
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install selenium webdriver-manager beautifulsoup4

# Run application
python course_search.py
```

### Common Development Issues

1. **Import Errors**: Ensure all dependencies are installed
2. **WebDriver Issues**: Update Chrome browser
3. **GUI Problems**: Verify tkinter installation
4. **Database Locks**: Ensure proper connection closing

This technical documentation should be updated whenever significant changes are made to the codebase.