# UofT Course Dashboard - Developer Guide

## Table of Contents
1. [Quick Start](#quick-start)
2. [Development Environment Setup](#development-environment-setup)
3. [Project Structure](#project-structure)
4. [Development Workflow](#development-workflow)
5. [Database Development](#database-development)
6. [Testing Guide](#testing-guide)
7. [Debugging Tips](#debugging-tips)
8. [Contributing Guidelines](#contributing-guidelines)
9. [Common Issues & Solutions](#common-issues--solutions)

## Quick Start

### Prerequisites
- Python 3.7+
- Chrome browser
- Git (optional)

### Installation
```bash
# Clone or download the repository
git clone [repository-url]
cd Course-Dashboard

# Install dependencies
pip install -r requirements.txt

# Run the application
python course_dashboard.py
```

### First Run
1. The application will automatically create the database (`course_dashboard.db`)
2. Database migrations will run automatically
3. Sample data (programs, breadth categories) will be populated
4. The GUI will open with all tabs available

## Development Environment Setup

### Python Environment
```bash
# Create virtual environment (recommended)
python -m venv course_dashboard_env

# Activate virtual environment
# Windows:
course_dashboard_env\Scripts\activate
# Unix/macOS:
source course_dashboard_env/bin/activate

# Install dependencies
pip install -r requirements.txt

# Optional: Install development dependencies
pip install pytest pytest-cov black flake8
```

### IDE Configuration

#### VS Code
```json
// .vscode/settings.json
{
    "python.defaultInterpreterPath": "./course_dashboard_env/Scripts/python.exe",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black",
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests/"]
}
```

#### PyCharm
- Set Python interpreter to virtual environment
- Enable pytest as test runner
- Configure flake8 for linting
- Set up black for code formatting

### Chrome WebDriver
The application uses `webdriver-manager` to automatically manage ChromeDriver:
```python
# Automatic ChromeDriver management
from webdriver_manager.chrome import ChromeDriverManager
service = Service(ChromeDriverManager().install())
```

No manual ChromeDriver installation required!

## Project Structure

### Current Structure (Phase 1)
```
Course-Dashboard/
├── course_dashboard.py          # Main application (4000+ lines)
├── course_dashboard.db          # SQLite database
├── requirements.txt             # Python dependencies
├── README.md                   # User documentation
├── master_plan.md              # Development roadmap
├── ARCHITECTURE.md             # System architecture
├── DEVELOPER_GUIDE.md          # This document
│
├── academic_cal/               # Legacy: Original course search
│   ├── course_search.py
│   ├── README.md
│   └── requirements.txt
│
├── transcript/                 # Legacy: Original transcript analyzer
│   ├── uoft_transcript_analyzer.py
│   ├── README.md
│   └── requirements.txt
│
├── .git/                      # Git repository
├── __pycache__/               # Python cache
└── courses.db                 # Legacy database
```

### Planned Structure (Future Phases)
```
Course-Dashboard/
├── src/                       # Source code
│   ├── main.py               # Application entry point
│   ├── gui/                  # User interface
│   │   ├── __init__.py
│   │   ├── main_window.py
│   │   ├── tabs/
│   │   └── dialogs/
│   ├── core/                 # Business logic
│   │   ├── __init__.py
│   │   ├── requirements.py
│   │   ├── analytics.py
│   │   └── recommender.py
│   ├── data/                 # Database layer
│   │   ├── __init__.py
│   │   ├── database.py
│   │   ├── models.py
│   │   └── migrations/
│   ├── scraping/             # Web scraping
│   │   ├── __init__.py
│   │   ├── scraper.py
│   │   └── parsers.py
│   └── utils/                # Utilities
│       ├── __init__.py
│       ├── validators.py
│       └── helpers.py
│
├── tests/                    # Test suite
│   ├── __init__.py
│   ├── test_database.py
│   ├── test_requirements.py
│   ├── test_scraping.py
│   └── fixtures/
│
├── docs/                     # Documentation
│   ├── API.md
│   ├── DEPLOYMENT.md
│   └── images/
│
├── legacy/                   # Original modules
│   ├── academic_cal/
│   └── transcript/
│
├── scripts/                  # Development scripts
│   ├── setup_dev.py
│   ├── migrate_db.py
│   └── test_scraper.py
│
├── assets/                   # Resources
│   ├── icons/
│   └── docs/
│
└── config/                   # Configuration
    ├── settings.py
    └── database.ini
```

## Development Workflow

### Adding New Features

#### 1. Database Changes
```python
# 1. Create new migration in UnifiedCourseDatabase
def _migration_003_new_feature(self, cursor):
    """Migration 3: Add new feature tables"""
    cursor.execute('''
        CREATE TABLE new_feature_table (
            id INTEGER PRIMARY KEY,
            data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

# 2. Update migration list
migrations = [
    (1, "Initial database schema", self._migration_001_initial_schema),
    (2, "Phase 1: Academic planning foundation", self._migration_002_academic_planning),
    (3, "New feature implementation", self._migration_003_new_feature),  # Add here
]
```

#### 2. Business Logic
```python
# Add new methods to appropriate classes
class RequirementsCalculator:
    def new_feature_calculation(self, data):
        """New feature calculation logic"""
        # Implementation here
        pass
```

#### 3. GUI Components
```python
# Add new tab or update existing tab
def setup_new_feature_tab(self):
    """Setup new feature tab"""
    new_frame = ttk.Frame(self.notebook)
    self.notebook.add(new_frame, text="New Feature")
    # GUI implementation here
```

#### 4. Testing
```python
# Create tests for new feature
def test_new_feature():
    """Test new feature functionality"""
    # Test implementation
    assert expected_result == actual_result
```

### Code Standards

#### Python Style Guide
- Follow PEP 8 style guidelines
- Use `black` for code formatting
- Maximum line length: 88 characters
- Use type hints where appropriate

```python
# Good example
def calculate_gpa(courses: List[Dict[str, Any]]) -> float:
    """Calculate GPA from list of courses."""
    total_points = 0.0
    total_credits = 0.0

    for course in courses:
        if course['gpa_points'] > 0:
            total_points += course['gpa_points'] * course['credits']
            total_credits += course['credits']

    return total_points / total_credits if total_credits > 0 else 0.0
```

#### Database Conventions
- Use lowercase table names with underscores
- Include `created_at` timestamp for audit tables
- Use `INTEGER PRIMARY KEY` for IDs
- Add indexes for frequently queried columns

```sql
-- Good table design
CREATE TABLE student_courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT DEFAULT 'default',
    course_code TEXT NOT NULL,
    grade TEXT,
    credits REAL NOT NULL,
    session TEXT,
    year INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add appropriate indexes
CREATE INDEX idx_student_courses_student ON student_courses(student_id);
CREATE INDEX idx_student_courses_course ON student_courses(course_code);
```

#### GUI Conventions
- Use ttk widgets for modern appearance
- Group related controls with LabelFrame
- Implement proper grid weight configuration
- Add tooltips for complex features

```python
# Good GUI structure
def setup_feature_section(self, parent):
    """Setup feature section with proper layout"""
    # Container frame
    feature_frame = ttk.LabelFrame(parent, text="Feature Name", padding="10")
    feature_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

    # Controls
    ttk.Label(feature_frame, text="Input:").grid(row=0, column=0, sticky=tk.W)
    self.input_var = tk.StringVar()
    ttk.Entry(feature_frame, textvariable=self.input_var).grid(row=0, column=1, sticky=(tk.W, tk.E))

    # Configure weights
    feature_frame.columnconfigure(1, weight=1)
```

## Database Development

### Working with Migrations

#### Creating New Migrations
```python
def _migration_00X_description(self, cursor):
    """Migration X: Brief description of changes"""
    # 1. Create new tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS new_table (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            description TEXT
        )
    ''')

    # 2. Modify existing tables (if needed)
    try:
        cursor.execute('ALTER TABLE existing_table ADD COLUMN new_column TEXT')
    except sqlite3.OperationalError:
        pass  # Column already exists

    # 3. Create indexes
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_new_table_name ON new_table(name)
    ''')

    # 4. Populate initial data (if needed)
    cursor.execute('''
        INSERT OR IGNORE INTO new_table (name, description)
        VALUES ('default', 'Default entry')
    ''')
```

#### Testing Migrations
```python
# Test migration independently
def test_migration():
    import tempfile
    import os

    # Create temporary database
    db_fd, db_path = tempfile.mkstemp()
    try:
        os.close(db_fd)

        # Test migration
        db = UnifiedCourseDatabase(db_path)

        # Verify schema
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check table exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='new_table'
        """)
        assert cursor.fetchone() is not None

        conn.close()

    finally:
        os.unlink(db_path)
```

### Database Debugging

#### Inspect Database Schema
```python
def inspect_database():
    """Utility to inspect database structure"""
    db = UnifiedCourseDatabase()
    conn = db._get_connection()
    cursor = conn.cursor()

    # List all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()

    for table in tables:
        table_name = table[0]
        print(f"\nTable: {table_name}")

        # Get table schema
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()

        for col in columns:
            print(f"  {col[1]} {col[2]} {'NOT NULL' if col[3] else ''}")

    conn.close()
```

#### Query Performance Analysis
```python
def analyze_query_performance():
    """Analyze slow queries"""
    db = UnifiedCourseDatabase()
    conn = db._get_connection()

    # Enable query analysis
    conn.execute("PRAGMA query_only = ON")

    # Test query
    start_time = time.time()
    cursor = conn.cursor()
    cursor.execute("EXPLAIN QUERY PLAN SELECT * FROM transcript_courses WHERE student_id = ?", ('default',))
    plan = cursor.fetchall()
    end_time = time.time()

    print(f"Query time: {end_time - start_time:.4f}s")
    print("Query plan:")
    for step in plan:
        print(f"  {step}")

    conn.close()
```

## Testing Guide

### Unit Testing

#### Database Tests
```python
import pytest
import tempfile
import os
from course_dashboard import UnifiedCourseDatabase

class TestUnifiedCourseDatabase:
    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing"""
        db_fd, db_path = tempfile.mkstemp()
        os.close(db_fd)
        yield UnifiedCourseDatabase(db_path)
        os.unlink(db_path)

    def test_save_transcript_course(self, temp_db):
        """Test saving transcript course"""
        course_data = {
            'course_code': 'CSC108H1',
            'title': 'Introduction to Computer Programming',
            'credits': 0.5,
            'grade': 'A',
            'mark': 90,
            'session': 'Fall',
            'year': 2023,
            'gpa_points': 4.0
        }

        temp_db.save_transcript_course(course_data)
        courses = temp_db.get_transcript_courses()

        assert len(courses) == 1
        assert courses[0][1] == 'CSC108H1'  # course_code
        assert courses[0][4] == 'A'         # grade
```

#### Requirements Calculator Tests
```python
class TestRequirementsCalculator:
    @pytest.fixture
    def calculator_with_data(self):
        """Create calculator with sample data"""
        db = UnifiedCourseDatabase(':memory:')

        # Add sample transcript data
        sample_courses = [
            {'course_code': 'CSC108H1', 'credits': 0.5, 'grade': 'A', 'gpa_points': 4.0},
            {'course_code': 'MAT135H1', 'credits': 0.5, 'grade': 'B+', 'gpa_points': 3.3},
        ]

        for course in sample_courses:
            db.save_transcript_course(course)

        return RequirementsCalculator(db)

    def test_gpa_calculation(self, calculator_with_data):
        """Test GPA calculation accuracy"""
        progress = calculator_with_data.calculate_complete_progress()
        expected_gpa = (4.0 * 0.5 + 3.3 * 0.5) / (0.5 + 0.5)  # 3.65

        assert abs(progress['current_gpa'] - expected_gpa) < 0.01
```

### Integration Testing
```python
def test_full_workflow():
    """Test complete application workflow"""
    # 1. Create database
    db = UnifiedCourseDatabase(':memory:')

    # 2. Add courses
    course_data = {...}
    db.save_transcript_course(course_data)

    # 3. Calculate requirements
    calc = RequirementsCalculator(db)
    progress = calc.calculate_complete_progress()

    # 4. Verify results
    assert progress is not None
    assert 'current_gpa' in progress
    assert 'graduation_eligible' in progress
```

### Running Tests
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_database.py

# Run with coverage
pytest --cov=course_dashboard

# Run with verbose output
pytest -v

# Run specific test
pytest tests/test_database.py::TestUnifiedCourseDatabase::test_save_transcript_course
```

## Debugging Tips

### Common Debugging Scenarios

#### 1. Database Issues
```python
# Debug database connections
def debug_database():
    db = UnifiedCourseDatabase()
    try:
        conn = db._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM transcript_courses")
        count = cursor.fetchone()[0]
        print(f"Database accessible: {count} transcript courses")
        conn.close()
    except Exception as e:
        print(f"Database error: {e}")
```

#### 2. Web Scraping Issues
```python
# Debug scraper with visible browser
scraper = AcademicCalendarScraper(debug=True)  # Shows browser
try:
    results = scraper.search_courses("CSC108")
    print(f"Found {len(results)} courses")
except Exception as e:
    print(f"Scraping error: {e}")
finally:
    scraper.close_driver()
```

#### 3. GUI Issues
```python
# Debug tkinter widget values
def debug_gui_state(self):
    """Debug current GUI state"""
    print("=== GUI Debug Info ===")
    print(f"Search query: {self.search_var.get()}")
    print(f"Selected programs: {getattr(self, 'program_var', {}).get()}")
    print(f"Transcript courses: {len(self.transcript_tree.get_children())}")

    # Widget states
    try:
        print(f"Requirements calculator: {hasattr(self, 'requirements_calculator')}")
    except AttributeError:
        print("Requirements calculator not initialized")
```

### Logging Setup
```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('course_dashboard.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Use in code
def some_function():
    logger.debug("Starting function")
    try:
        # Function logic
        logger.info("Function completed successfully")
    except Exception as e:
        logger.error(f"Function failed: {e}")
        raise
```

### Performance Profiling
```python
import cProfile
import pstats

def profile_function():
    """Profile function performance"""
    pr = cProfile.Profile()
    pr.enable()

    # Code to profile
    db = UnifiedCourseDatabase()
    calc = RequirementsCalculator(db)
    progress = calc.calculate_complete_progress()

    pr.disable()

    # Print stats
    stats = pstats.Stats(pr)
    stats.sort_stats('cumulative')
    stats.print_stats(10)  # Top 10 functions
```

## Contributing Guidelines

### Getting Started
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-feature`
3. Make changes following code standards
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

### Pull Request Process
1. **Code Review**: All changes require review
2. **Testing**: Must include tests for new features
3. **Documentation**: Update relevant documentation
4. **Migration**: Include database migrations if needed

### Code Review Checklist
- [ ] Follows Python style guidelines (PEP 8)
- [ ] Includes appropriate tests
- [ ] Documentation updated
- [ ] No hardcoded values
- [ ] Proper error handling
- [ ] Performance considerations addressed
- [ ] Database migrations tested
- [ ] GUI components follow conventions

## Common Issues & Solutions

### Installation Issues

#### "Module not found" errors
```bash
# Ensure virtual environment is activated
# Windows:
course_dashboard_env\Scripts\activate
# Unix/macOS:
source course_dashboard_env/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

#### ChromeDriver issues
```python
# The app uses webdriver-manager for automatic ChromeDriver management
# If issues persist, try:

# 1. Clear webdriver cache
import shutil
shutil.rmtree(os.path.expanduser("~/.wdm"), ignore_errors=True)

# 2. Reinstall webdriver-manager
pip uninstall webdriver-manager
pip install webdriver-manager
```

### Runtime Issues

#### Database corruption
```python
# Backup and recreate database
import shutil
shutil.copy("course_dashboard.db", "course_dashboard_backup.db")

# Delete corrupted database (will be recreated)
os.remove("course_dashboard.db")

# Restart application - new database will be created
```

#### GUI not responding
```python
# Check for blocking operations in main thread
# Move long operations to background threads

import threading

def long_operation():
    # Long-running task
    pass

# Run in background
thread = threading.Thread(target=long_operation)
thread.daemon = True
thread.start()
```

#### Memory issues
```python
# Monitor memory usage
import psutil
import os

def check_memory():
    process = psutil.Process(os.getpid())
    memory_mb = process.memory_info().rss / 1024 / 1024
    print(f"Memory usage: {memory_mb:.1f} MB")
```

### Development Environment Issues

#### Virtual environment problems
```bash
# Recreate virtual environment
rm -rf course_dashboard_env
python -m venv course_dashboard_env
source course_dashboard_env/bin/activate  # Unix/macOS
# or
course_dashboard_env\Scripts\activate     # Windows
pip install -r requirements.txt
```

#### IDE configuration issues
```python
# VS Code Python interpreter issues
# 1. Ctrl+Shift+P -> "Python: Select Interpreter"
# 2. Choose virtual environment interpreter
# 3. Restart VS Code if needed
```

## Advanced Development Topics

### Performance Optimization

#### Database Query Optimization
```python
# Use indexes for frequent queries
CREATE INDEX idx_transcript_student_course ON transcript_courses(student_id, course_code);

# Use EXPLAIN QUERY PLAN to analyze queries
cursor.execute("EXPLAIN QUERY PLAN SELECT * FROM transcript_courses WHERE student_id = ?")

# Batch operations for better performance
cursor.executemany("INSERT INTO table VALUES (?, ?)", data_list)
```

#### Memory Optimization
```python
# Use generators for large datasets
def get_courses_generator():
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM transcript_courses")
    while True:
        row = cursor.fetchone()
        if row is None:
            break
        yield row

# Clear caches periodically
def clear_caches(self):
    self.database._clear_cache()
    gc.collect()
```

### Security Considerations

#### Input Validation
```python
def validate_course_code(course_code):
    """Validate course code format"""
    import re
    pattern = r'^[A-Z]{3}\d{3}[HY]\d$'
    if not re.match(pattern, course_code):
        raise ValueError(f"Invalid course code format: {course_code}")
    return course_code

def validate_grade(grade):
    """Validate grade value"""
    valid_grades = ['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'D-', 'F']
    if grade not in valid_grades:
        raise ValueError(f"Invalid grade: {grade}")
    return grade
```

#### Safe Database Operations
```python
# Always use parameterized queries
cursor.execute("SELECT * FROM courses WHERE code = ?", (course_code,))

# Never use string formatting for SQL
# BAD: cursor.execute(f"SELECT * FROM courses WHERE code = '{course_code}'")
# GOOD: cursor.execute("SELECT * FROM courses WHERE code = ?", (course_code,))
```

### Extensibility Patterns

#### Plugin Architecture (Future)
```python
class PluginInterface:
    """Interface for dashboard plugins"""

    def get_name(self) -> str:
        raise NotImplementedError

    def get_version(self) -> str:
        raise NotImplementedError

    def initialize(self, dashboard) -> None:
        raise NotImplementedError

    def get_menu_items(self) -> List[Dict]:
        raise NotImplementedError

class ExamplePlugin(PluginInterface):
    def get_name(self):
        return "Example Plugin"

    def initialize(self, dashboard):
        # Plugin initialization
        pass
```

#### Event System (Future)
```python
class EventManager:
    """Event-driven architecture for loose coupling"""

    def __init__(self):
        self._listeners = {}

    def subscribe(self, event_type, callback):
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(callback)

    def publish(self, event_type, data):
        if event_type in self._listeners:
            for callback in self._listeners[event_type]:
                callback(data)

# Usage
events = EventManager()
events.subscribe('course_added', update_gpa_display)
events.publish('course_added', course_data)
```

---

This developer guide provides comprehensive information for working with the UofT Course Dashboard codebase. For additional help, refer to the ARCHITECTURE.md document or create an issue in the project repository.

**Document Version**: 1.0
**Last Updated**: September 2024
**Maintainer**: Development Team