# UofT Course Dashboard - System Architecture Documentation

## Table of Contents
1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Database Design](#database-design)
4. [Class Structure](#class-structure)
5. [UI Architecture](#ui-architecture)
6. [Data Flow](#data-flow)
7. [External Integrations](#external-integrations)
8. [Performance Considerations](#performance-considerations)
9. [Security & Privacy](#security--privacy)
10. [Testing Strategy](#testing-strategy)

## Overview

The UofT Course Dashboard is a comprehensive academic planning and degree management system built in Python using tkinter for the GUI and SQLite for data persistence. The system has evolved through multiple phases to become a sophisticated tool for University of Toronto students.

### Current Version
- **Phase 1**: Academic Foundation (COMPLETE)
- **Phase 2**: Intelligent Course Planning (PLANNED)
- **Phase 3**: Advanced Analytics (PLANNED)
- **Phase 4**: Integration & Advanced Features (PLANNED)

### Key Features
- Real-time course search and data extraction from UofT Academic Calendar
- Comprehensive transcript management with GPA calculation
- Academic requirements tracking and degree progress monitoring
- Program enrollment and breadth requirements validation
- Course planning and prerequisite management
- Advanced analytics and graduation timeline prediction

## System Architecture

### High-Level Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                    UofT Course Dashboard                    │
├─────────────────────────────────────────────────────────────┤
│  Presentation Layer (GUI - tkinter)                         │
│  ┌─────────────┬──────────────┬─────────────┬─────────────┐ │
│  │ Course      │ Transcript   │ Planning    │ Requirements│ │
│  │ Search Tab  │ Tab          │ Tab         │ Tab         │ │
│  └─────────────┴──────────────┴─────────────┴─────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  Business Logic Layer                                       │
│  ┌─────────────┬──────────────┬─────────────┬─────────────┐ │
│  │ Course      │ Requirements │ Academic    │ Course      │ │
│  │ Scraper     │ Calculator   │ Analytics   │ Recommender │ │
│  └─────────────┴──────────────┴─────────────┴─────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  Data Access Layer                                          │
│  ┌────────────────────────────────────────────────────────┐ │
│  │        UnifiedCourseDatabase                           │ │
│  │  ┌────────────┬──────────────┬─────────────────────────┤ │
│  │  │ Migration  │ CRUD         │ Query Optimization      │ │
│  │  │ Manager    │ Operations   │ & Caching               │ │
│  │  └────────────┴──────────────┴─────────────────────────┘ │
│  └────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  Data Storage Layer                                         │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              SQLite Database                           │ │
│  │  ┌─────────────┬──────────────┬────────────────────────┤ │
│  │  │ Course Data │ Academic     │ Student Progress       │ │
│  │  │ Tables      │ Programs     │ & Analytics            │ │
│  │  └─────────────┴──────────────┴────────────────────────┘ │
│  └────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  External Integrations                                      │
│  ┌────────────────────────────────────────────────────────┐ │
│  │    UofT Academic Calendar (Web Scraping)               │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Component Breakdown

#### 1. Presentation Layer (GUI)
- **Framework**: tkinter with ttk widgets for modern styling
- **Tabs**: Course Search, Transcript, Planning, GPA Dashboard, Requirements, Analytics
- **Components**: Treeviews, text widgets, forms, dialogs, progress indicators

#### 2. Business Logic Layer
- **Course Scraper**: Selenium-based web scraping of UofT Academic Calendar
- **Requirements Calculator**: Degree progress calculation and validation
- **Academic Analytics**: GPA trends, performance analysis, graduation prediction
- **Course Recommender**: AI-powered course suggestions (Phase 2)

#### 3. Data Access Layer
- **UnifiedCourseDatabase**: Centralized database management
- **Migration System**: Versioned schema updates
- **Caching**: Performance optimization for frequent queries
- **CRUD Operations**: Create, Read, Update, Delete operations

#### 4. Data Storage Layer
- **SQLite Database**: Local file-based storage
- **Schema Versioning**: Automatic migration system
- **Indexes**: Performance-optimized queries
- **Backup System**: Data protection and recovery

## Database Design

### Schema Overview
The database uses a normalized design with 12+ tables across different functional areas:

#### Core Tables (Phase 1)
```sql
-- Course Information
academic_courses          -- Course catalog data from Academic Calendar
course_prerequisites      -- Prerequisite relationships
course_breadth            -- Breadth requirement mappings

-- Student Data
transcript_courses        -- Completed courses with grades
planned_courses          -- Future course planning
student_programs         -- Program enrollment tracking

-- Academic Framework
programs                 -- Available academic programs
breadth_categories       -- UofT's 5 breadth requirements
degree_requirements      -- Graduation requirements
academic_standing        -- Historical academic standing

-- System
schema_version           -- Database migration tracking
```

### Database Relationships
```
Programs (1) ←→ (M) Student_Programs ←→ (1) Students
Programs (1) ←→ (M) Program_Requirements
Courses (1) ←→ (M) Course_Prerequisites
Courses (1) ←→ (M) Course_Breadth ←→ (M) Breadth_Categories
Students (1) ←→ (M) Transcript_Courses
Students (1) ←→ (M) Planned_Courses
Students (1) ←→ (M) Academic_Standing
```

### Key Design Decisions

1. **Normalized Structure**: Separate tables for different entity types
2. **Flexible Prerequisites**: Support for complex prerequisite logic
3. **Breadth Mapping**: Many-to-many relationship for course-category mapping
4. **Historical Tracking**: Academic standing and performance over time
5. **Migration System**: Schema versioning for safe updates

## Class Structure

### Core Classes

#### 1. UnifiedCourseDatabase
```python
class UnifiedCourseDatabase:
    """Central database management class"""

    # Core Methods
    - __init__(db_path)
    - init_database()
    - _apply_migrations()

    # CRUD Operations
    - save_academic_course()
    - save_transcript_course()
    - get_transcript_courses()
    - update_transcript_course()
    - delete_transcript_courses()

    # Phase 1: Academic Planning
    - save_program()
    - get_programs()
    - enroll_in_program()
    - get_enrolled_programs()
    - calculate_degree_progress()
    - calculate_breadth_progress()

    # Utility Methods
    - _get_connection()
    - _is_cache_valid()
    - _set_cache()
    - _clear_cache()
```

#### 2. CourseDashboard (Main GUI)
```python
class CourseDashboard:
    """Main application controller and GUI manager"""

    # Initialization
    - __init__(root)
    - setup_gui()
    - setup_search_tab()
    - setup_transcript_tab()
    - setup_planning_tab()
    - setup_gpa_dashboard_tab()
    - setup_requirements_tab()
    - setup_analytics_tab()

    # Search Functionality
    - search_courses()
    - extract_course_details()
    - view_course_details()

    # Transcript Management
    - add_to_transcript()
    - edit_transcript_course()
    - delete_transcript_courses()
    - import_transcript_csv()
    - export_transcript_csv()

    # Requirements Tab
    - populate_programs_combobox()
    - enroll_in_program()
    - update_requirements_display()
    - show_graduation_timeline()
    - suggest_breadth_courses()

    # Analytics & Display
    - update_gpa_display()
    - update_analytics_display()
    - generate_gpa_report()
```

#### 3. RequirementsCalculator
```python
class RequirementsCalculator:
    """Academic requirements calculation engine"""

    - __init__(database)
    - calculate_complete_progress()
    - _check_graduation_eligibility()
    - _generate_requirements_summary()
    - _suggest_next_steps()
    - get_academic_standing()
    - suggest_breadth_courses()
    - calculate_graduation_timeline()
```

#### 4. AcademicCalendarScraper
```python
class AcademicCalendarScraper:
    """Web scraping for UofT Academic Calendar"""

    - __init__(debug=False)
    - setup_driver()
    - search_courses(query)
    - extract_course_details(url)
    - get_detailed_info()
    - close_driver()
```

### Supporting Classes

#### 5. CourseDialog
```python
class CourseDialog:
    """Modal dialog for course entry/editing"""

    - __init__(parent, title, mode, course_data)
    - create_form()
    - calculate_gpa_points()
    - save_course()
    - apply_changes()
```

#### 6. CourseInfoWindow
```python
class CourseInfoWindow:
    """Detailed course information display"""

    - __init__(parent, course_data, database, scraper)
    - create_window()
    - display_course_info()
    - fetch_full_details()
    - add_to_transcript()
    - add_to_plan()
```

## UI Architecture

### Tab Structure
The application uses a tabbed interface with specialized functionality:

#### 1. Course Search Tab
- **Search Input**: Course code or keyword search
- **Results List**: Searchable course results
- **Course Details**: Preview pane with course information
- **Actions**: Add to transcript, add to plan, view details

#### 2. Transcript Tab
- **Quick Add Form**: Streamlined course entry
- **Course Tree**: Tabular display of completed courses
- **Filtering**: Search and filter capabilities
- **Summary Statistics**: GPA, credits, academic standing
- **Bulk Operations**: Import/export, bulk editing

#### 3. Planning Tab
- **Future Courses**: Planned course management
- **Priority System**: Course priority assignment
- **Session Planning**: Semester-by-semester organization
- **Move to Transcript**: Convert planned to completed

#### 4. GPA Dashboard Tab
- **Overall GPA**: Current cumulative GPA
- **Sessional Breakdown**: Semester-by-semester analysis
- **Academic Standing**: Current standing determination
- **Trend Analysis**: GPA progression over time

#### 5. Requirements Tab (Phase 1)
- **Program Enrollment**: Select and enroll in programs
- **Degree Progress**: Real-time requirement tracking
- **Breadth Requirements**: Category-by-category progress
- **Graduation Timeline**: Estimated completion date
- **Course Suggestions**: AI-powered recommendations

#### 6. Analytics Tab
- **Course Statistics**: Distribution and analysis
- **Performance Metrics**: Advanced GPA analytics
- **Trend Charts**: Visual progression analysis
- **Export Options**: Report generation

### Design Patterns

#### 1. Model-View-Controller (MVC)
- **Model**: UnifiedCourseDatabase + RequirementsCalculator
- **View**: tkinter GUI components
- **Controller**: CourseDashboard class

#### 2. Observer Pattern
- **Database Changes**: Automatic UI updates
- **Cache Invalidation**: Real-time data refresh
- **Progress Updates**: Live requirement calculation

#### 3. Factory Pattern
- **Dialog Creation**: CourseDialog factory methods
- **Window Management**: CourseInfoWindow instantiation

## Data Flow

### Course Search Flow
```
User Input → Search Query → Web Scraper → Course Data → Database → UI Update
     ↓
Course Selection → Detail Extraction → Full Course Info → Display/Action
```

### Transcript Management Flow
```
Course Entry → Validation → GPA Calculation → Database Save → UI Refresh
     ↓
Requirements Update → Progress Calculation → Analytics Update
```

### Requirements Calculation Flow
```
Transcript Data → Course Analysis → Level Classification → Credit Calculation
     ↓
Breadth Analysis → Program Requirements → Graduation Eligibility → Display
```

### Database Migration Flow
```
App Start → Version Check → Migration Queue → Schema Updates → Data Migration
     ↓
Validation → Index Creation → Cache Clear → App Ready
```

## External Integrations

### UofT Academic Calendar
- **URL**: `https://artsci.calendar.utoronto.ca`
- **Method**: Selenium WebDriver with Chrome
- **Rate Limiting**: Respectful scraping with delays
- **Error Handling**: Multiple fallback strategies
- **Data Extraction**: Course details, prerequisites, descriptions

### Web Scraping Strategy
1. **Form Detection**: Multiple form field identification
2. **Result Parsing**: Flexible HTML structure handling
3. **Error Recovery**: Retry mechanisms and fallbacks
4. **Cache Management**: Intelligent data caching
5. **Session Management**: Persistent browser sessions

## Performance Considerations

### Database Optimization
- **Indexing**: Strategic indexes on frequently queried columns
- **Query Optimization**: Efficient JOIN operations
- **Connection Pooling**: Reuse database connections
- **Cache Layer**: In-memory caching for frequent data

### Memory Management
- **Lazy Loading**: Load data only when needed
- **Cache Expiry**: Automatic cache invalidation
- **Resource Cleanup**: Proper WebDriver management
- **Garbage Collection**: Efficient object lifecycle

### UI Responsiveness
- **Threading**: Background operations for web scraping
- **Progress Indicators**: User feedback for long operations
- **Incremental Loading**: Paginated data display
- **Event Debouncing**: Optimized user input handling

## Security & Privacy

### Data Protection
- **Local Storage**: No cloud data transmission
- **Encryption**: Sensitive data protection (future)
- **Access Control**: User authentication (future web version)
- **Backup**: Automated local backup system

### Web Scraping Ethics
- **Terms Compliance**: Respect for UofT terms of service
- **Rate Limiting**: Prevent server overload
- **User Agent**: Transparent browser identification
- **Error Handling**: Graceful failure management

## Testing Strategy

### Unit Testing
- **Database Operations**: CRUD operation validation
- **Requirements Calculation**: Academic logic verification
- **GPA Calculations**: Mathematical accuracy testing
- **Data Validation**: Input sanitization testing

### Integration Testing
- **Database Migrations**: Schema update validation
- **Web Scraping**: External service interaction
- **UI Components**: Widget interaction testing
- **End-to-End**: Complete workflow validation

### Test Data
- **Synthetic Transcripts**: Varied academic scenarios
- **Edge Cases**: Boundary condition testing
- **Error Conditions**: Failure mode validation
- **Performance Testing**: Load and stress testing

### Automated Testing
```python
# Example test structure
class TestRequirementsCalculator:
    def test_gpa_calculation()
    def test_breadth_progress()
    def test_graduation_eligibility()
    def test_timeline_calculation()

class TestDatabaseOperations:
    def test_course_crud()
    def test_migration_system()
    def test_cache_management()
    def test_query_performance()
```

## File Organization

### Current Structure
```
Course-Dashboard/
├── course_dashboard.py          # Main application
├── course_dashboard.db          # SQLite database
├── README.md                   # Project overview
├── requirements.txt            # Python dependencies
├── master_plan.md             # Future development roadmap
├── ARCHITECTURE.md            # This document
│
├── academic_cal/              # Original course search module
├── transcript/                # Original transcript analyzer
├── docs/                     # Documentation (planned)
├── tests/                    # Test suite (planned)
└── assets/                   # Images and resources (planned)
```

### Planned Reorganization
```
Course-Dashboard/
├── src/                      # Source code
│   ├── main.py              # Application entry point
│   ├── gui/                 # User interface modules
│   ├── core/                # Business logic
│   ├── data/                # Database and models
│   └── utils/               # Utility functions
│
├── tests/                   # Test suite
├── docs/                    # Documentation
├── legacy/                  # Original modules
├── assets/                  # Resources
├── scripts/                 # Development scripts
└── config/                  # Configuration files
```

## Future Architecture (Phases 2-4)

### Phase 2: Intelligent Planning
- **Prerequisite Engine**: Complex dependency resolution
- **Course Recommender**: ML-powered suggestions
- **Conflict Detection**: Scheduling and prerequisite validation
- **Sequence Optimization**: Optimal course ordering

### Phase 3: Advanced Analytics
- **Predictive Modeling**: Performance and timeline prediction
- **Comparative Analysis**: Peer benchmarking
- **Risk Assessment**: Academic risk identification
- **Visualization Engine**: Advanced charts and graphs

### Phase 4: Integration & Web
- **Web Application**: Browser-based interface
- **API Layer**: RESTful service architecture
- **Multi-user Support**: Database multi-tenancy
- **External APIs**: University system integration

## Conclusion

The UofT Course Dashboard represents a sophisticated academic planning system with a well-architected foundation ready for future enhancements. The modular design, comprehensive database schema, and extensible class structure provide a solid platform for the advanced features planned in subsequent phases.

The system successfully balances functionality, performance, and maintainability while providing an intuitive user experience for University of Toronto students planning their academic journey.

---

**Document Version**: 1.0
**Last Updated**: September 2024
**Phase Status**: Phase 1 Complete
**Next Milestone**: Phase 2 Implementation