# UofT Course Dashboard - Integrated Academic Planning Tool

A comprehensive Python application that combines course search, transcript analysis, and academic planning for University of Toronto students. This integrated tool merges the functionality of the Academic Calendar Course Search with advanced transcript analysis and GPA calculation features.

## Features

### 🔍 **Course Search & Discovery**
- **Real-time Search**: Search UofT Academic Calendar using Selenium-powered web scraping
- **Detailed Extraction**: Extract comprehensive course information including prerequisites, exclusions, and descriptions
- **Direct Integration**: Add courses directly from search results to transcript or planning list
- **Comprehensive Database**: Automatically saves extracted course data for future reference

### 📊 **GPA Dashboard & Analytics**
- **Real-time GPA Calculation**: Automatic calculation using UofT 4.0 scale
- **Sessional Analysis**: Track GPA trends by session and year
- **Academic Standing**: Automatic determination of academic standing (Dean's List, Good Standing, etc.)
- **Visual Analytics**: GPA trend charts and statistical analysis (requires matplotlib)
- **Grade Distribution**: Detailed breakdown by grade and department

### 📋 **Transcript Management**
- **Complete Transcript Tracking**: Manage all completed courses with grades
- **Import/Export**: CSV import/export functionality for data portability
- **Flexible Grading**: Support for letter grades and special notations (CR, NCR, WDR, etc.)
- **Session Organization**: Organize courses by Fall/Winter/Summer sessions

### 📅 **Course Planning**
- **Future Course Planning**: Plan courses for upcoming sessions
- **Priority System**: Set priorities for planned courses
- **Notes & Annotations**: Add personal notes to planned courses
- **Move to Transcript**: Easily convert planned courses to completed courses

### 📈 **Advanced Analytics**
- **Department Analysis**: Course distribution by department
- **Credit Tracking**: Monitor total credits and progress
- **Trend Visualization**: GPA trends over time with interactive charts
- **Statistical Reports**: Comprehensive academic performance reports

## Installation

### Prerequisites
- Python 3.7 or higher
- Chrome browser (for course search functionality)

### Required Dependencies
```bash
pip install selenium webdriver-manager beautifulsoup4
```

### Optional Dependencies (for enhanced features)
```bash
pip install matplotlib numpy  # For charts and analytics
pip install openpyxl          # For Excel export
pip install reportlab         # For PDF reports
```

### Setup
1. Clone or download the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run the integrated application: `python course_dashboard.py`

## Usage

### Starting the Application
```bash
python course_dashboard.py
```

### Tab Overview

#### 1. Course Search Tab
- **Search**: Enter course codes (e.g., "CSC148") or keywords
- **Extract Details**: Get comprehensive course information from Academic Calendar
- **Add to Transcript**: Directly add searched courses to your transcript
- **Add to Plan**: Add courses to your planning list for future sessions

#### 2. Transcript Tab
- **Manage Courses**: Add, edit, delete completed courses
- **Import/Export**: CSV functionality for data management
- **Grade Tracking**: Full support for UofT grading system

#### 3. Course Planning Tab
- **Plan Ahead**: Add courses you plan to take in future sessions
- **Set Priorities**: Organize courses by importance
- **Add Notes**: Personal annotations for each planned course
- **Move to Transcript**: Convert planned courses to completed once taken

#### 4. GPA Dashboard Tab
- **Live GPA**: Real-time overall GPA calculation
- **Sessional GPAs**: Track performance by session
- **Academic Standing**: Automatic standing determination
- **Export Reports**: Generate comprehensive GPA reports

#### 5. Analytics Tab
- **Statistics**: Course and grade distribution analysis
- **Trend Charts**: Visual GPA progression (requires matplotlib)
- **Department Breakdown**: Analysis by subject area

## Database Structure

The application uses SQLite with four main tables:

### Academic Courses
Stores course information from the Academic Calendar:
- Course code, title, hours, description
- Prerequisites, exclusions, breadth requirements
- Direct URL to course page

### Transcript Courses
Tracks completed courses:
- Course code, title, credits, grade
- Session, year, status, GPA points

### Planned Courses
Manages future course planning:
- Course code, title, credits
- Planned session/year, priority, notes

### Course Prerequisites
Stores prerequisite and course relationship data

## Grade Scale

Uses the official UofT 4.0 GPA scale:
- A+, A: 4.0
- A-: 3.7
- B+: 3.3
- B: 3.0
- B-: 2.7
- C+: 2.3
- C: 2.0
- C-: 1.7
- D+: 1.3
- D: 1.0
- D-: 0.7
- F, FZ: 0.0

Special notations (CR, NCR, WDR, LWD, etc.) are supported but excluded from GPA calculations.

## Architecture

### Key Components

#### UnifiedCourseDatabase
- Centralizes all course data management
- Handles academic calendar and transcript data
- Provides unified interface for data operations

#### AcademicCalendarScraper
- Selenium-powered web scraping of UofT Academic Calendar
- Robust form interaction and result parsing
- Handles dynamic website elements and multiple page formats

#### CourseDialog
- Flexible dialog system for adding/editing courses
- Supports both transcript and planning modes
- Validates input and calculates GPA points

#### CourseDashboard
- Main application controller
- Manages all GUI components and user interactions
- Coordinates between search, transcript, and planning features

## Data Import/Export

### CSV Import Format
```csv
course_code,title,credits,grade,session,year,status
CSC148H1,Introduction to Computer Science,0.5,A,Fall,2023,completed
```

### Export Formats
- **CSV**: Course data with all fields
- **Text Reports**: Formatted GPA and academic reports
- **Excel**: Enhanced spreadsheet format (if openpyxl installed)

## Configuration

### Browser Settings
Course search uses Chrome in headless mode. To see browser actions:
1. Edit `course_dashboard.py`
2. Comment out `chrome_options.add_argument("--headless")`
3. Restart application

### Database Location
Default database file: `course_dashboard.db`
Change by modifying the `UnifiedCourseDatabase` initialization.

## Performance

- **Search Speed**: 3-5 seconds per course search
- **Detail Extraction**: 2-3 seconds per course
- **Database Operations**: Near-instantaneous for normal dataset sizes
- **Memory Usage**: ~150-300MB during active scraping

## Files

- `course_dashboard.py`: Main integrated application
- `academic_cal/course_search.py`: Original course search tool
- `transcript/uoft_transcript_analyzer.py`: Original transcript analyzer
- `requirements.txt`: Python dependencies
- `course_dashboard.db`: Unified SQLite database (created automatically)

## Troubleshooting

### Common Issues

1. **Course Search Not Working**
   - Ensure Chrome browser is installed
   - Check internet connection
   - Verify Selenium and webdriver-manager are installed

2. **Import/Export Errors**
   - Check file permissions
   - Verify CSV format matches expected structure
   - Ensure file is not open in another application

3. **Charts Not Displaying**
   - Install matplotlib: `pip install matplotlib numpy`
   - Restart application after installation

4. **Database Errors**
   - Ensure write permissions in application directory
   - Delete `course_dashboard.db` to reset database if corrupted

### Debug Mode
Set `chrome_options.add_argument("--headless")` to see browser actions during course search.

## Future Enhancements

- **Degree Requirements Tracking**: Monitor progress toward degree completion
- **Course Recommendation System**: Suggest courses based on prerequisites and interests
- **Schedule Planning**: Visual timetable planning for course scheduling
- **Multi-Campus Support**: Extended support for UTM and UTSC courses
- **API Integration**: Direct integration with UofT systems where available

## Contributing

To contribute to this project:
1. Test with various course codes and academic scenarios
2. Report bugs or suggest improvements
3. Follow existing code style and documentation standards
4. Add comprehensive error handling for edge cases

## License

This project is for educational use. Please respect the University of Toronto's terms of service when using this tool.

## Support

For issues or questions:
1. Check the troubleshooting section
2. Verify Python and Chrome installations
3. Test with simple course codes like "CSC108" or "MAT137"
4. Ensure all dependencies are properly installed

---

**Note**: This tool is designed to assist with academic planning and should be used in conjunction with official university resources and academic advisors.