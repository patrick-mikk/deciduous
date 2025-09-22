# University of Toronto Course Dashboard

A command-line tool for University of Toronto students to search courses, manage academic transcripts, and plan their degree requirements using real-time data from the UofT Academic Calendar.

## 🎯 Project Goals

### Primary Objectives
- **Real-time Course Data**: Access up-to-date course information directly from the UofT Academic Calendar
- **Academic Planning**: Help students track their academic progress and plan future course selections
- **Transcript Management**: Maintain a personal academic record with GPA calculations
- **Degree Planning**: Assist with breadth requirement tracking and prerequisite validation
- **Data Export**: Enable easy sharing and backup of academic records

### Target Audience
- **University of Toronto Students**: Current students in Arts & Science and other faculties
- **Academic Advisors**: Staff helping students with course planning and degree requirements
- **Prospective Students**: Those researching UofT course offerings and requirements

## 🏗️ Technical Architecture

### Core Components

#### 1. Interactive Command-Line Interface (`src/cli_app.py`)
- **Purpose**: Modern interactive terminal interface with arrow key navigation
- **Framework**: Python argparse + inquirer for interactive menus + rich for enhanced output
- **Features**: Interactive course search, visual course details, rich transcript tables, CSV import/export
- **UI Libraries**: inquirer (arrow navigation), rich (colored tables, panels, progress bars)

#### 2. Database Layer (`src/core.py`)
- **Purpose**: SQLite-based storage for transcript data and course information
- **Schema**: Courses table with fields for code, title, credits, grades, sessions
- **Functionality**: CRUD operations, GPA calculations, data validation

#### 3. Web Scraping Engine (`src/core.py`)
- **Purpose**: Extract course data from UofT Academic Calendar
- **Technology**: Selenium WebDriver with Chrome automation
- **Target**: https://artsci.calendar.utoronto.ca/
- **Data Extracted**: Course codes, titles, descriptions, prerequisites, exclusions, breadth requirements

#### 4. Documentation System
- **Selenium Documentation**: Comprehensive locator strategies and HTML structure analysis
- **API Documentation**: Method signatures and usage examples
- **User Guide**: Command-line usage and workflow examples

### Data Flow
```
User Input → CLI Parser → Database/Scraper → Data Processing → Formatted Output
```

## 🚀 Features

### Currently Implemented

#### ✅ Interactive Course Search
- **Access**: Main menu → "🔍 Search Courses" or `python cli_app.py search <query>`
- **Features**:
  - Arrow key navigation through search results
  - Rich table display with colored columns
  - Selectable result limit (5, 10, 15, 20)
  - Direct access to course details from results
- **Example**: Search for "POL208" and navigate with arrow keys

#### ✅ Enhanced Course Information Display
- **Access**: Main menu → "📖 Get Course Details" or `python cli_app.py details <course_code>`
- **Features**:
  - Rich formatted panels with course information
  - Prerequisites, exclusions, and breadth requirements displayed clearly
  - Interactive option to add course directly to transcript
  - Professional layout with color-coded sections

#### ✅ Modern Transcript Management
- **Access**: Main menu → "📜 View Transcript" or `python cli_app.py transcript`
- **Features**:
  - Rich table format with sortable columns (Code, Title, Credits, Grade, Session, Year)
  - Real-time GPA calculation using official UofT grading scale
  - Academic progress panel with credit tracking (X/20.0 credits)
  - Proper handling of special grades (CR, NCR, P, LWD, WDR, IPR, INC)
  - Visual statistics with colored progress indicators

#### ✅ CSV Import/Export System
- **Import**: Main menu → "📥 Import from CSV"
  - Interactive file selection with default path (docs/my_courses.csv)
  - Automatic course title generation for missing data
  - Progress indicators and import statistics
  - Error handling for malformed data
- **Export**: Main menu → "💾 Export Transcript" or `python cli_app.py export [filename]`
  - CSV format with all transcript data
  - Proper field mapping and data validation

#### ✅ Interactive Terminal Interface
- **Launch**: `python cli_app.py interactive` or just `python cli_app.py`
- **Navigation**: Use arrow keys to navigate menus, Enter to select
- **Features**:
  - Emoji-enhanced menu options
  - Rich welcome banner and status displays
  - Interactive prompts for all user input
  - Graceful error handling with user-friendly messages

### Planned Features (Feasible for CLI Implementation)

#### 🔄 Degree Planning Tools
- **Breadth Requirement Tracking**: Analyze transcript against UofT breadth categories
- **Credit Calculations**: Track progress toward degree completion (120+ credits)
- **Prerequisite Validation**: Check if student meets requirements for target courses
- **Program Requirements**: Support for specialist/major/minor program tracking

#### 🔄 Enhanced Search and Filtering
- **Department Filtering**: Search within specific departments (e.g., all POL courses)
- **Level Filtering**: Filter by course level (100, 200, 300, 400)
- **Credit Filtering**: Find courses by credit value (0.5 vs 1.0)
- **Breadth Filtering**: Search courses by breadth requirement category

#### 🔄 Academic Analytics
- **GPA Trends**: Calculate GPA by semester/year
- **Course Load Analysis**: Track credits per semester
- **Grade Distribution**: Analyze grade patterns by department/level
- **Progress Reports**: Generate degree completion summaries

#### ✅ Import/Export Enhancements (COMPLETED)
- **CSV Import**: Interactive import from CSV files with data validation
- **CSV Export**: Full transcript export with proper formatting
- **Future**: ACORN Integration, Multiple Export Formats (JSON, XML)
- **Backup/Restore**: Complete database backup and restoration
- **Data Validation**: Verify transcript accuracy against official records

#### 🔄 Course Recommendation System
- **Prerequisite Suggestions**: Recommend prerequisite courses for target goals
- **Breadth Completion**: Suggest courses to complete remaining breadth requirements
- **Schedule Optimization**: Help plan course sequences across multiple semesters

### Advanced Features (Potential Future Scope)

#### 📋 Web Interface
- **Technology**: Flask/Django web application
- **Purpose**: More accessible interface for non-technical users
- **Features**: Visual transcript display, interactive course planning

#### 📋 Mobile Application
- **Technology**: React Native or Flutter
- **Purpose**: On-the-go access to course information
- **Features**: Course lookup, schedule planning, grade tracking

#### 📋 Integration APIs
- **ACORN Integration**: Direct connection to official UofT systems (if available)
- **Calendar Sync**: Export course schedules to Google Calendar/Outlook
- **Notification System**: Alerts for registration periods, deadline reminders

## 🛠️ Installation and Setup

### Prerequisites
- Python 3.8 or higher
- Chrome browser (for selenium automation)
- Internet connection (for course data retrieval)

### Installation Steps
1. **Clone Repository**:
   ```bash
   git clone <repository-url>
   cd Course-Dashboard
   ```

2. **Install Dependencies**:
   ```bash
   pip install selenium webdriver-manager
   ```

3. **Initialize Database**:
   ```bash
   python -c "from src.core import CourseDatabase; CourseDatabase()"
   ```

### Dependencies
- `selenium`: Web automation for course data scraping
- `webdriver-manager`: Automatic Chrome WebDriver management
- `sqlite3`: Built-in database management
- `argparse`: Built-in command-line parsing
- `csv`: Built-in CSV export functionality

## 📖 Usage Examples

### Interactive Mode (Recommended)
```bash
# Launch interactive menu-driven interface
python src/cli_app.py

# Or explicitly launch interactive mode
python src/cli_app.py interactive
```

**Interactive Features:**
- 🎯 Menu-driven navigation with numbered options
- 🔍 Course search with history tracking
- 📖 Detailed course information lookup
- 📜 Transcript management and GPA calculation
- 💾 Data export with custom filenames
- 📊 Advanced academic statistics
- 🕒 Session information and activity tracking
- 🔎 Search history with repeat functionality

### Command-Line Mode
```bash
# Search for courses
python src/cli_app.py search "introduction to"

# Get detailed information
python src/cli_app.py details POL208H1

# View your transcript
python src/cli_app.py transcript

# Export data
python src/cli_app.py export my_transcript.csv
```

### Advanced Usage
```bash
# Search with result limit
python src/cli_app.py search CSC --limit 20

# Export with custom filename
python src/cli_app.py export "fall_2024_transcript.csv"
```

## 🔧 Technical Implementation Details

### Selenium Locator Strategy
- **Robust Element Finding**: Multiple fallback strategies for each page element
- **Error Handling**: Graceful degradation when elements are not found
- **Performance Optimization**: Disabled images and JavaScript for faster scraping
- **Documentation**: Comprehensive locator documentation in `docs/SELENIUM_DOCUMENTATION.md`

### Database Schema
```sql
CREATE TABLE courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_code TEXT NOT NULL,
    title TEXT,
    credits REAL,
    grade TEXT,
    mark REAL,
    semester TEXT,
    year INTEGER,
    status TEXT DEFAULT 'planned'
);
```

### Grade Point Calculations
- **4.0 Scale**: Standard UofT GPA calculation
- **Supported Grades**: A+, A, A-, B+, B, B-, C+, C, C-, D+, D, D-, F, FZ
- **Pass/Fail Support**: P, CR, NCR grades (excluded from GPA)

## 🎓 Academic Calendar Integration

### Supported Data Fields
- **Course Information**: Code, title, description, credit value
- **Academic Requirements**: Prerequisites, exclusions, corequisites
- **Scheduling**: Course hours (lecture/tutorial format)
- **Degree Planning**: Breadth requirement categories
- **Department Data**: Derived from course codes

### Data Accuracy
- **Real-time**: Data pulled directly from official UofT Academic Calendar
- **Validation**: Cross-reference with official course codes and formats
- **Error Handling**: Graceful handling of missing or changed course information

## 🔒 Privacy and Data Security

### Local Data Storage
- **SQLite Database**: All transcript data stored locally
- **No Cloud Storage**: Personal academic information never transmitted to external servers
- **User Control**: Complete ownership and control of academic data

### Web Scraping Ethics
- **Respectful Automation**: Reasonable delays between requests to avoid server overload
- **Public Data Only**: Only accessing publicly available course information
- **Terms Compliance**: Respecting UofT website terms of service

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Make changes with appropriate tests
4. Submit a pull request

### Code Standards
- **Python Style**: PEP 8 compliance
- **Documentation**: Comprehensive docstrings and comments
- **Error Handling**: Robust exception handling
- **Testing**: Unit tests for core functionality

## 📄 License

This project is for educational use by University of Toronto students and is not officially affiliated with the University of Toronto.

## 🆘 Support

### Common Issues
- **Chrome Driver Issues**: Automatic driver management via webdriver-manager
- **Network Connectivity**: Requires stable internet for course data retrieval
- **Course Not Found**: Verify course code format (e.g., POL208H1, not pol208h1)

### Getting Help
- Check documentation in `docs/` directory
- Review example usage in this README
- Ensure all dependencies are properly installed

---

*Last Updated: September 2024*
*Version: 2.0.0 (CLI Implementation)*