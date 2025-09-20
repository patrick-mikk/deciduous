# UofT Course Dashboard

A professional, compact dashboard application for searching and managing University of Toronto course information. Built with Python and featuring a modern dark theme interface, this tool scrapes course data from the UofT Academic Calendar website and provides powerful management features for academic planning.

## Features

### 🎛️ **Compact Dashboard Interface**
- **Multi-Column Layout**: Efficient three-panel design for maximum productivity
- **Real-time Preview**: Instant course details display on selection
- **Professional Menu System**: Comprehensive menu bar with organized functions

### 🔍 **Advanced Search Capabilities**
- **Quick Search**: Fast course lookup by code or keyword
- **Bulk Search**: Process multiple course codes simultaneously
- **Live Results**: Real-time result count and instant feedback
- **Smart Export**: Save search results to CSV format

### 📋 **Comprehensive Course Information**
- **Complete Details**: Extract all course information including:
  - Course title and code
  - Hours/credits
  - Prerequisites and corequisites
  - Exclusions
  - Breadth requirements
  - Multi-paragraph descriptions with links
- **Instant Preview**: Course details appear immediately on selection

### 💾 **Intelligent Database Management**
- **Auto-Save**: Automatically stores extracted course information
- **Quick Statistics**: Live database stats and course counts
- **Subject Analysis**: Breakdown of courses by department
- **Data Export**: Flexible export options for course data

### 🎨 **Modern User Experience**
- **Dark Theme**: Professional appearance with reduced eye strain
- **Responsive Design**: Optimized for different screen sizes
- **Intuitive Navigation**: Menu-driven interface with keyboard shortcuts
- **Status Awareness**: Clear feedback for all operations

### 🤖 **Robust Technology Stack**
- **Selenium WebDriver**: Reliable web scraping with JavaScript support
- **SQLite Database**: Fast, local data storage
- **Python/Tkinter**: Cross-platform desktop application
- **Multi-paragraph Parsing**: Handles complex course descriptions

## Requirements

### System Requirements
- Windows 10/11 (tested)
- Python 3.7 or higher
- Chrome browser (automatically managed by webdriver-manager)

### Python Dependencies
```
selenium>=4.35.0
webdriver-manager>=4.0.2
beautifulsoup4>=4.9.0
tkinter (usually included with Python)
sqlite3 (included with Python)
```

## Installation

1. **Clone or download the repository**
   ```bash
   git clone <repository-url>
   cd Course-Dashboard/academic_cal
   ```

2. **Install required packages**
   ```bash
   pip install selenium webdriver-manager beautifulsoup4
   ```

3. **Run the application**
   ```bash
   python course_search.py
   ```

## Usage

### Starting the Application
Run the main script:
```bash
python course_search.py
```

### Using the GUI

1. **Search for Courses**:
   - Enter a course code (e.g., "CSC148") or keyword in the search field
   - Press Enter or click the "Search" button
   - Results will appear in the list below

2. **Extract Course Details**:
   - Select a course from the search results
   - Click "Extract Course Details"
   - Full course information will be displayed and saved to the database

3. **View Saved Courses**:
   - Click "View All Saved Courses" to see previously extracted courses
   - A new window will open with a table of all saved courses

## Architecture

### Core Components

#### 1. CourseDatabase Class
Handles all database operations:
- Creates and manages SQLite database (`courses.db`)
- Saves course information with automatic duplicate handling
- Retrieves saved courses for viewing

#### 2. AcademicCalendarScraper Class
Manages web scraping functionality:
- **WebDriver Management**: Automatically downloads and configures ChromeDriver
- **Form Interaction**: Handles different search form variations on the website
- **Result Parsing**: Extracts course information from various page formats
- **Robust Error Handling**: Multiple fallback mechanisms for reliable scraping

#### 3. CourseSearchGUI Class
Provides the user interface:
- Search functionality with real-time feedback
- Course selection and detail extraction
- Database viewing capabilities
- Status updates and error handling

### Database Schema

The application creates a SQLite database (`courses.db`) with the following structure:

```sql
CREATE TABLE courses (
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
);
```

### Web Scraping Strategy

The scraper uses a multi-layered approach to handle the dynamic nature of the UofT website:

1. **Form Detection**: Tries multiple form field names (`course_keyword`, `course_title`)
2. **Result Parsing**: Handles different result formats:
   - Accordion-style results (primary format)
   - Legacy table formats (fallback)
   - Direct course links (fallback)
3. **Error Recovery**: Multiple retry mechanisms and fallback parsing strategies

## Configuration

### Chrome Options
The application runs Chrome in headless mode with the following options:
- `--headless`: Runs without GUI
- `--no-sandbox`: Improves compatibility
- `--disable-dev-shm-usage`: Prevents memory issues
- `--disable-gpu`: Disables GPU acceleration
- `--window-size=1920,1080`: Sets consistent window size

### Customization Options

You can modify these parameters in the `AcademicCalendarScraper` class:

```python
# In setup_driver() method
chrome_options.add_argument("--headless")  # Remove for visible browser
chrome_options.add_argument("--window-size=1920,1080")  # Adjust window size
```

## Troubleshooting

### Common Issues

1. **ChromeDriver Not Found**
   - The application automatically downloads ChromeDriver
   - Ensure you have Chrome browser installed
   - Check your internet connection

2. **Search Returns No Results**
   - Verify the course code is correct
   - Try using partial course codes (e.g., "CSC" instead of "CSC148")
   - Check if the UofT website is accessible

3. **Database Errors**
   - Ensure write permissions in the application directory
   - Delete `courses.db` to reset the database if corrupted

4. **GUI Issues**
   - Ensure tkinter is properly installed with Python
   - Try running with `python -m tkinter` to test tkinter installation

### Debug Mode

To enable debug mode and see browser actions:
1. Edit `course_search.py`
2. In the `setup_driver()` method, comment out the headless option:
   ```python
   # chrome_options.add_argument("--headless")
   ```
3. Run the application to see Chrome browser in action

## Example Usage

### Command Line Testing
```python
from course_search import AcademicCalendarScraper

# Initialize scraper
scraper = AcademicCalendarScraper()

# Search for courses
results = scraper.search_courses("CSC148")
print(f"Found {len(results)} courses")

# Extract details for first result
if results:
    details = scraper.extract_course_details(results[0]['url'])
    print(f"Course: {details['title']}")
    print(f"Prerequisites: {details['prerequisites']}")

# Clean up
scraper.close_driver()
```

### Database Query Example
```python
import sqlite3

# Connect to database
conn = sqlite3.connect('courses.db')
cursor = conn.cursor()

# Query courses
cursor.execute("SELECT course_code, title FROM courses WHERE course_code LIKE 'CSC%'")
courses = cursor.fetchall()

for code, title in courses:
    print(f"{code}: {title}")

conn.close()
```

## Performance Considerations

- **Search Speed**: Typical search takes 3-5 seconds
- **Detail Extraction**: Each course detail extraction takes 2-3 seconds
- **Database**: SQLite handles thousands of courses efficiently
- **Memory Usage**: Selenium uses ~100-200MB RAM during operation

## Limitations

1. **Rate Limiting**: Be respectful of UofT's servers; avoid rapid successive searches
2. **Website Changes**: The scraper may need updates if UofT changes their website structure
3. **Course Availability**: Only shows courses available in the current academic calendar
4. **Network Dependency**: Requires active internet connection

## Contributing

To contribute to this project:

1. Test the application with various course codes
2. Report bugs or suggest improvements
3. Ensure code follows the existing style and documentation standards
4. Add error handling for edge cases

## Version History

- **v1.0**: Initial release with basic requests-based scraping
- **v2.0**: Selenium integration for improved reliability and JavaScript support

## License

This project is for educational use. Please respect the University of Toronto's terms of service when using this tool.

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Verify your Python and Chrome installations
3. Test with a simple course code like "CSC108"