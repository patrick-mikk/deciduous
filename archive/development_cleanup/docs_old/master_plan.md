# UofT Course Dashboard - Master Enhancement Plan

## Executive Summary

This master plan outlines the complete transformation of the UofT Course Dashboard from a basic transcript tracker into a comprehensive academic planning and degree management system. **Phase 1 (Academic Foundation) is now complete**, and **Phase 2 prioritizes GUI modernization** with PyQt6/PySide6 migration to create a modern, professional user experience. The plan leverages advanced interface design, intelligent course planning, and comprehensive academic integration to create a world-class tool for University of Toronto students.

### 🎯 **Updated Strategic Focus:**
1. **Immediate Priority**: Modern GUI with PyQt6/PySide6 (Phase 2)
2. **Foundation Complete**: Academic requirements engine and data management (Phase 1 ✅)
3. **Future Expansion**: Intelligent planning, analytics, and web platform (Phases 3-5)

## UofT Faculty of Arts & Science Requirements Framework

### 🎓 **Official Academic Requirements**
Based on the comprehensive UofT Academic Calendar and Faculty policies:

#### **Degree Completion Requirements**
- **Total Credits**: Exactly 20.0 credits for undergraduate degree
- **Faculty Credits**: At least 10.0 credits from Faculty of Arts & Science
- **Concentration Limit**: Maximum 15.0 credits with same 3-letter course designator
- **Minimum GPA**: 1.85 cumulative GPA for graduation
- **Academic Standing**: Continuous satisfactory progress monitoring

#### **Course Level Distribution**
- **Upper-Level Requirement**: At least 13.0 credits at 200-level or higher
- **Advanced Study**: At least 6.0 credits at 300-level or higher
- **Progressive Learning**: 100→200→300→400 level academic advancement

#### **Program Requirements**
**Specialist Programs (Deepest Study)**
- Credits: 10.0-14.0 credits (some interdisciplinary up to 16.0)
- Upper-Level: At least 4.0 credits at 300+ level
- Advanced: At least 1.0 credit at 400-level
- Limit: Maximum 2 Major/Specialist programs

**Major Programs (Comprehensive Study)**
- Credits: 6.0-8.0 credits
- Upper-Level: At least 2.0 credits at 300+ level
- Advanced: At least 0.5 credits at 400-level
- Flexibility: Can combine with other programs

**Minor Programs (Foundational Study)**
- Credits: Exactly 4.0 credits
- Upper-Level: At least 1.0 credit at 300+ level
- Complement: Designed to complement other programs

#### **Breadth Requirements (Liberal Education)**
- **Total**: 4.0 credits across diverse knowledge areas
- **Distribution Option 1**: 1.0 credit each in 4 of 5 categories
- **Distribution Option 2**: 1.0 credit in 3 categories + 0.5 credits in remaining 2

**Five Official Breadth Categories:**
1. **Creative and Cultural Representations** (Literature, Arts, Culture)
2. **Thought, Belief and Behaviour** (Psychology, Philosophy, Religion)
3. **Society and its Institutions** (Politics, Economics, Sociology)
4. **Living Things and their Environment** (Biology, Ecology, Environmental Science)
5. **The Physical and Mathematical Universes** (Physics, Chemistry, Mathematics, Computer Science)

## Current Status: Phase 2B Complete ✅

**Phase 1: Academic Foundation** has been successfully implemented with **accurate UofT Faculty of Arts & Science requirements**, providing:
- ✅ **20.0 Credit System**: Complete credit tracking and validation
- ✅ **Breadth Requirements**: 4.0 credits across 5 official categories (Creative/Cultural, Thought/Belief/Behaviour, Society/Institutions, Living Things/Environment, Physical/Mathematical)
- ✅ **Program Types**: Specialist (10.0-14.0 credits), Major (6.0-8.0 credits), Minor (4.0 credits)
- ✅ **Course Level Requirements**: 13.0+ at 200-level, 6.0+ at 300-level tracking
- ✅ **Academic Standing**: 1.85 GPA minimum with continuous monitoring
- ✅ **Concentration Limits**: No more than 15.0 credits with same 3-letter designator
- ✅ **Upper-Level Requirements**: 4.0+ at 300+ for Specialist, 2.0+ for Major, 1.0+ for Minor
- ✅ **Prerequisites & Exclusions**: Full course relationship management
- ✅ **Database migration system** with academic planning tables
- ✅ **Course search and transcript management** functionality
- ✅ **Bulk edit/delete operations** for transcript courses
- ✅ **Project reorganization** with proper directory structure

**Current Technical Status (Phase 2B Complete):**
- **Framework**: Modern PyQt6 GUI with professional styling ✅
- **Course Search**: Live filtering with Selenium-powered UofT Academic Calendar integration ✅
- **Transcript Management**: Advanced table with bulk operations and real-time filtering ✅
- **Database**: SQLite with accurate UofT academic requirements engine
- **Architecture**: Clean PyQt6 MVC with widget separation and signal/slot communication
- **Styling**: High-contrast accessibility theme with professional appearance

## Phase 2: PyQt6/PySide6 Migration (Weeks 5-8) 🎨

### 🎯 **NEXT MAJOR MILESTONE: Complete GUI Framework Migration**
Transform the current functional tkinter application into a modern, professional PyQt6/PySide6 application with enhanced user experience and advanced capabilities.

### 🚀 **Migration Approach: Systematic & Manageable**

#### **Why PyQt6/PySide6 Now:**
- **Professional Interface**: Modern, native look-and-feel across platforms
- **Enhanced Capabilities**: Advanced widgets, better data handling, rich styling
- **Performance**: Superior rendering, threading, and responsiveness
- **Future-Ready**: Active Qt 6 ecosystem, extensive documentation
- **Industry Standard**: Widely used in professional desktop applications

#### **Migration Strategy:**
1. **Complete Replacement**: Full migration from tkinter to PyQt6/PySide6
2. **Preserve Functionality**: Maintain all existing features during migration
3. **Incremental Development**: Build and test each component systematically
4. **Data Compatibility**: Ensure seamless database and data integration
5. **Enhanced UX**: Improve workflows and add new capabilities

### 📋 **Phase 2A: Foundation & Core Structure (Week 5)**

#### **Environment Setup & Planning**
- **Development Environment**: Configure PyQt6/PySide6 toolchain and dependencies
- **Project Structure**: Create new PyQt6 application structure alongside existing code
- **Architecture Design**: Plan MVC architecture for clean separation of concerns
- **Dependency Management**: Update requirements.txt with PyQt6/PySide6 dependencies

#### **Core Application Framework**
- **Main Application Window**: Create modern QMainWindow with menu bar and status bar
- **Tab System**: Implement QTabWidget with improved navigation and styling
- **Database Integration**: Ensure existing UnifiedCourseDatabase works with new GUI
- **Styling System**: Establish custom themes and styling framework

### 📋 **Phase 2B: Tab Migration & Core Features (Week 6)**

#### **Course Search Tab (Priority 1)**
- **Search Interface**: Modern QLineEdit with autocomplete and advanced filters
- **Results Display**: QTableWidget/QTreeWidget with sorting, filtering, and selection
- **Course Details**: Rich QTextEdit with formatted course information display
- **Action Buttons**: Styled QPushButtons with improved layouts and functionality

#### **Transcript Tab (Priority 2)**
- **Course Table**: Advanced QTableWidget with multi-selection, sorting, and filtering
- **Quick Add Form**: Streamlined course entry with QComboBox and validation
- **Bulk Operations**: Enhanced bulk edit/delete with modern dialogs
- **Summary Display**: Rich text summary with formatted statistics

### 📋 **Phase 2C: Enhanced Layout & Native PyQt6 Optimization (Week 7)**

#### **🎯 Strategic Redesign: From 6 Dispersed Tabs to 4 Centralized Hubs**

**New Tab Architecture:**

**1. Academic Overview Tab** 📊
- Main dashboard with status cards (GPA, Credits, Academic Standing)
- Degree progress visualization with native QProgressBar
- Recent activity timeline and quick actions
- Centralized course lookup and add functionality

**2. Course Management Tab** 🔍
- Unified Academic Calendar search with selenium integration
- Transcript management with advanced filtering
- Detailed course information panel
- Bulk operations (edit, delete, move to planning)
- Three-panel layout using QSplitter for optimal screen usage

**3. Degree Planning Tab** 🎓
- Integrated requirements tracking with QTreeWidget visualization
- Course planning workspace with drag-drop functionality
- Program enrollment and breadth requirements management
- Prerequisite validation and academic pathway planning

**4. Analytics & Reports Tab** 📈
- GPA trends and historical analysis using Qt Charts
- Credit distribution and completion metrics
- Progress visualization and milestone tracking
- Export functionality for transcripts and reports

#### **🎨 Native PyQt6 Styling Migration**
- **Remove Custom CSS**: Eliminate `styles.qss` dependency for maintenance simplicity
- **QPalette Integration**: Use native color scheme management for system consistency
- **Built-in Widget Properties**: Leverage Qt's professional appearance standards
- **Responsive Layouts**: Implement QSplitter and native layout managers for optimal UX
- **System Theme Compatibility**: Ensure app adapts to user's system preferences

#### **🏗️ Layout Optimization Strategy**
- **Compact Information Density**: Maximize useful information per screen area
- **Professional Grouping**: Use QGroupBox and QFrame for logical content organization
- **User-Resizable Panels**: Implement QSplitter throughout for customizable workspace
- **Native Controls**: Replace custom styling with Qt's built-in professional appearance

### 📋 **Phase 2D: Polish & Testing (Week 8)**

#### **Enhanced User Experience Implementation**
- **Keyboard Shortcuts**: Comprehensive navigation and action shortcuts (Ctrl+1-4, F5, Ctrl+F)
- **Drag & Drop**: Intuitive course planning with drag-and-drop between semesters
- **Context Menus**: Right-click menus for quick actions on courses and requirements
- **Tooltips**: Smart tooltips with course details and requirement explanations

#### **Data Interoperability & Cross-Tab Communication**
- **Unified Data Manager**: Central data coordination with real-time synchronization
- **Signal/Slot Enhancement**: Application-wide event system for seamless communication
- **Cross-Tab Workflows**: Course search → Planning, Overview → Management navigation
- **Undo/Redo System**: Comprehensive action history with rollback capability

#### **Performance Optimization & Settings**
- **Lazy Loading**: On-demand widget rendering and database query optimization
- **Background Processing**: Non-blocking operations with progress indicators
- **Settings Dialog**: Comprehensive preferences for themes, layout, and behavior
- **Layout Persistence**: Save/restore window positions and user customizations

#### **Quality Assurance & Testing**
- **Automated Testing**: Unit, integration, and end-to-end test suites
- **Performance Benchmarking**: Load time optimization and responsiveness metrics
- **Cross-Platform Validation**: Windows, macOS, and Linux compatibility testing
- **Accessibility Compliance**: Keyboard navigation and screen reader support

### 🎨 **New GUI Features & Enhancements**

#### **Modern Interface Components:**
- **Navigation**: Sidebar navigation with icons and modern tab system
- **Search Interface**: Advanced search with filters, autocomplete, and real-time results
- **Data Tables**: Sortable, filterable tables with multi-selection and context menus
- **Course Cards**: Visual course display cards with ratings, difficulty, and quick actions
- **Progress Visualization**: Interactive progress bars, pie charts, and timeline views
- **Dark/Light Theme**: User-selectable themes with system integration

#### **Enhanced User Experience:**
- **Responsive Design**: Adaptive layout for different screen sizes
- **Keyboard Shortcuts**: Comprehensive keyboard navigation and shortcuts
- **Drag & Drop**: Intuitive course planning with drag-and-drop functionality
- **Context Menus**: Right-click menus for quick actions
- **Tool Tips**: Helpful tooltips and guided user experience
- **Status Indicators**: Clear visual feedback for operations and data states

### 💻 **Technical Implementation Strategy**

#### **Development Approach for Claude Code + Human:**
1. **Incremental Migration**: Convert one component at a time for manageable changes
2. **Parallel Development**: Keep tkinter version functional during development
3. **Modular Architecture**: Design clean, maintainable code structure
4. **Thorough Testing**: Validate each component before proceeding
5. **Documentation**: Maintain clear documentation throughout migration

#### **PyQt6/PySide6 Architecture (New Structure):**
```python
# Main application architecture
src/
├── gui_qt/                    # New PyQt6 GUI package
│   ├── __init__.py
│   ├── main_window.py         # QMainWindow - main application
│   ├── widgets/               # Custom widget components
│   │   ├── course_search.py   # Course search interface
│   │   ├── transcript_table.py # Transcript management
│   │   ├── requirements_view.py # Requirements tracking
│   │   ├── planning_widget.py  # Course planning
│   │   └── gpa_dashboard.py    # GPA and analytics
│   ├── dialogs/               # Dialog windows
│   │   ├── course_dialog.py   # Course entry/edit
│   │   ├── bulk_edit.py       # Bulk operations
│   │   └── settings.py        # Application settings
│   ├── resources/             # UI resources
│   │   ├── styles.qss         # Stylesheets
│   │   ├── icons/             # Application icons
│   │   └── themes/            # Theme definitions
│   └── utils/                 # GUI utilities
│       ├── validators.py      # Input validation
│       ├── formatters.py      # Text formatting
│       └── charts.py          # Chart components
├── core/                      # Existing business logic (unchanged)
│   ├── database.py           # UnifiedCourseDatabase
│   ├── requirements.py       # RequirementsCalculator
│   └── scraper.py            # AcademicCalendarScraper
└── main_qt.py                # New PyQt6 entry point
```

#### **Migration Dependencies:**
```bash
# Core PyQt6 requirements
pip install PyQt6>=6.4.0
pip install PyQt6-tools>=6.4.0

# Enhanced features
pip install matplotlib>=3.6.0      # For charts and graphs
pip install pyqtgraph>=0.13.0     # Advanced plotting
pip install qdarkstyle>=3.1.0     # Professional dark theme
pip install qtawesome>=1.2.0      # Icon library

# Optional enhancements
pip install Pillow>=9.0.0          # Image processing
pip install requests>=2.28.0       # HTTP requests for themes
```

#### **Key PyQt6 Components to Implement:**
```python
# Core application classes
class MainWindow(QMainWindow):
    """Main application window with menu bar, status bar, and tab system"""

class CourseSearchWidget(QWidget):
    """Modern course search with QLineEdit, QTableWidget, and filters"""

class TranscriptTableWidget(QTableWidget):
    """Enhanced transcript table with sorting, filtering, bulk operations"""

class RequirementsWidget(QWidget):
    """Requirements tracking with QProgressBar and visual indicators"""

class PlanningWidget(QWidget):
    """Drag-and-drop planning with QListWidget and enhanced UX"""

class CourseDialog(QDialog):
    """Modern course entry dialog with tabbed interface"""
```

### 🎯 **Phase 2 Deliverables**
- ✅ Complete PyQt6/PySide6 migration
- ✅ Modern, professional interface design
- ✅ Enhanced user experience and workflows
- ✅ Improved performance and responsiveness
- ✅ Dark/light theme support
- ✅ Advanced data visualization
- ✅ Comprehensive testing and validation

---

## Phase 3: Intelligent Course Planning & Prerequisites (Weeks 9-12) 🧠

### 🎯 **Objectives**
Transform the system into an intelligent academic advisor that understands course dependencies, validates prerequisites, and provides smart course recommendations.

### 🗄️ **Database Enhancements**

**New Tables:**
```sql
-- Enhanced course prerequisites with structured data
CREATE TABLE course_prerequisites_structured (
    id INTEGER PRIMARY KEY,
    course_code TEXT NOT NULL,
    prerequisite_type TEXT, -- 'prerequisite', 'corequisite', 'recommended'
    requirement_group INTEGER, -- For AND/OR logic grouping
    requirement_text TEXT,
    parsed_courses TEXT, -- JSON array of course codes
    logic_operator TEXT, -- 'AND', 'OR'
    minimum_grade TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Course difficulty and enrollment data
CREATE TABLE course_metrics (
    id INTEGER PRIMARY KEY,
    course_code TEXT UNIQUE,
    average_grade REAL,
    difficulty_rating REAL, -- 1-5 scale
    workload_hours REAL,
    enrollment_limit INTEGER,
    historical_demand REAL, -- Ratio of applicants to spots
    professor_ratings REAL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Course scheduling and availability
CREATE TABLE course_offerings (
    id INTEGER PRIMARY KEY,
    course_code TEXT,
    session TEXT, -- 'Fall', 'Winter', 'Summer'
    year INTEGER,
    professor TEXT,
    lecture_times TEXT, -- JSON array
    tutorial_times TEXT, -- JSON array
    location TEXT,
    enrollment_current INTEGER,
    enrollment_max INTEGER,
    waitlist_count INTEGER,
    last_scraped TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Student course planning
CREATE TABLE planned_course_sequences (
    id INTEGER PRIMARY KEY,
    student_id TEXT DEFAULT 'default',
    sequence_name TEXT, -- e.g., "CS Major Path", "Math Minor"
    target_graduation TEXT,
    semester_plan TEXT, -- JSON structure of semester-by-semester plan
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 🔧 **Core Features Implementation**

#### 1. Advanced Prerequisites Engine
```python
class PrerequisiteChecker:
    def __init__(self, database):
        self.database = database
        self.course_graph = self._build_prerequisite_graph()

    def validate_course_eligibility(self, course_code, completed_courses):
        """Check if student can take a course based on prerequisites"""

    def get_missing_prerequisites(self, course_code, completed_courses):
        """Return list of missing prerequisites with details"""

    def find_prerequisite_path(self, target_course, completed_courses):
        """Find optimal sequence to reach target course"""

    def check_corequisite_conflicts(self, planned_courses):
        """Validate corequisite requirements for planned courses"""

    def suggest_prerequisite_courses(self, target_courses, completed_courses):
        """Recommend courses to unlock target courses"""
```

#### 2. Intelligent Course Recommender
```python
class CourseRecommender:
    def __init__(self, database, prerequisites_checker):
        self.database = database
        self.prereq_checker = prerequisites_checker

    def recommend_next_semester(self, student_id, target_credits=2.5):
        """AI-powered semester planning"""

    def suggest_breadth_courses(self, breadth_gaps, difficulty_preference):
        """Smart breadth course selection based on student profile"""

    def recommend_electives(self, program_requirements, interests, difficulty):
        """Personalized elective recommendations"""

    def balance_course_load(self, planned_courses):
        """Optimize course combinations for balanced workload"""

    def suggest_summer_courses(self, degree_progress):
        """Strategic summer course planning"""
```

#### 3. Course Sequencing & Timeline Planner
```python
class AcademicSequencer:
    def __init__(self, database, recommender):
        self.database = database
        self.recommender = recommender

    def generate_degree_sequence(self, programs, target_graduation):
        """Create semester-by-semester plan to graduation"""

    def optimize_course_order(self, required_courses, constraints):
        """Find optimal course ordering considering prerequisites"""

    def handle_course_conflicts(self, semester_plan):
        """Resolve scheduling and prerequisite conflicts"""

    def create_alternative_pathways(self, base_plan, risk_factors):
        """Generate backup plans for high-risk courses"""
```

### 🎨 Enhanced User Interface

#### New Planning Tab Features:
- **Interactive Course Graph**: Visual prerequisite dependency tree
- **Drag-and-Drop Semester Planner**: Visual course scheduling interface
- **Course Difficulty Indicators**: Color-coded difficulty and workload metrics
- **Prerequisite Validation**: Real-time checking with clear error messages
- **What-If Scenarios**: Test different course combinations
- **Timeline Visualization**: Gantt chart style graduation timeline

#### Course Search Enhancements:
- **Advanced Filters**: By prerequisites, difficulty, professor, session
- **Prerequisite Tree View**: See course dependencies at a glance
- **Course Comparison**: Side-by-side analysis of options
- **Availability Tracking**: Real-time enrollment and waitlist data

## Phase 3: Advanced Analytics & Automation (Weeks 9-12)

### 🎯 Objectives
Create a sophisticated analytics engine with automated data collection, predictive modeling, and comprehensive academic insights.

### 🤖 Advanced Web Scraping System

#### Enhanced Academic Calendar Integration:
```python
class AdvancedCalendarScraper:
    def __init__(self):
        self.session_manager = SessionManager()
        self.cache_manager = CacheManager()

    def bulk_extract_program_requirements(self, program_codes):
        """Mass extraction of detailed program requirements"""

    def scrape_course_availability(self, session_year):
        """Real-time course offering and enrollment data"""

    def extract_grade_distributions(self, course_codes):
        """Historical grade data (if available)"""

    def monitor_course_changes(self):
        """Track changes in course offerings and requirements"""

    def scrape_professor_information(self, course_offerings):
        """Faculty data and teaching assignments"""
```

#### Intelligent Data Processing:
```python
class CourseDataProcessor:
    def parse_complex_prerequisites(self, requirement_text):
        """NLP-powered prerequisite parsing"""

    def extract_program_requirements(self, program_page_content):
        """Structured extraction of program requirements"""

    def analyze_course_descriptions(self, descriptions):
        """Content analysis for course difficulty and topics"""

    def standardize_course_data(self, raw_data):
        """Clean and normalize scraped data"""
```

### 📊 Comprehensive Analytics Engine

#### Academic Performance Analytics:
```python
class PerformanceAnalyzer:
    def analyze_gpa_trends(self, transcript_data):
        """Semester-by-semester GPA analysis with predictions"""

    def predict_course_performance(self, student_profile, target_course):
        """ML-based grade prediction"""

    def identify_academic_patterns(self, student_data):
        """Find strengths, weaknesses, and optimal strategies"""

    def benchmark_against_peers(self, student_metrics):
        """Compare performance to similar academic profiles"""
```

#### Degree Progress Analytics:
```python
class ProgressAnalytics:
    def calculate_graduation_probability(self, current_progress, risk_factors):
        """Statistical graduation likelihood analysis"""

    def optimize_graduation_timeline(self, constraints, preferences):
        """Multi-objective optimization for graduation planning"""

    def analyze_requirement_efficiency(self, course_history):
        """Identify most efficient paths to requirements"""

    def predict_course_demand(self, historical_data):
        """Forecast course availability and competition"""
```

### 📈 Advanced Visualization System

#### Interactive Dashboard Components:
- **GPA Trend Analysis**: Interactive charts with semester breakdowns
- **Requirement Progress Wheels**: Circular progress indicators
- **Course Network Graph**: Interactive prerequisite visualization
- **Academic Timeline**: Gantt chart with milestone tracking
- **Performance Heatmaps**: Subject area strength analysis
- **Graduation Countdown**: Real-time progress to degree completion

#### Data Export & Reporting:
- **PDF Academic Reports**: Professional progress summaries
- **Excel Audit Sheets**: Detailed requirement tracking
- **Calendar Integration**: Course schedule export to Google/Outlook
- **Transcript Formatting**: Official transcript-style outputs
- **Planning Worksheets**: Printable semester planning guides

### 🔮 Predictive Features

#### Machine Learning Integration:
```python
class AcademicPredictor:
    def __init__(self):
        self.models = self._load_prediction_models()

    def predict_semester_gpa(self, planned_courses, student_history):
        """Predict likely GPA for planned course load"""

    def recommend_optimal_course_load(self, student_profile):
        """ML-recommended number of courses per semester"""

    def predict_course_difficulty(self, course_code, student_background):
        """Personalized difficulty prediction"""

    def identify_at_risk_semesters(self, degree_plan):
        """Flag potentially problematic semester combinations"""
```

---

## Phase 4: Advanced Analytics & Machine Learning (Weeks 13-16) 📊

### 🎯 Objectives
Complete the transformation with advanced integrations, multi-campus support, and cutting-edge features.

### 🌐 Multi-Campus Integration

#### Extended University Support:
- **UTM (Mississauga) Integration**: Course offerings and requirements
- **UTSC (Scarborough) Integration**: Campus-specific programs
- **Cross-Campus Course Recognition**: Transfer credit handling
- **Faculty-Specific Requirements**: Engineering, Medicine, Law variations

#### Advanced Program Support:
```python
class ExtendedProgramManager:
    def handle_professional_programs(self, program_type):
        """Support for Medicine, Law, Engineering programs"""

    def manage_double_degrees(self, primary_program, secondary_program):
        """Complex dual degree planning"""

    def track_certificate_programs(self, certificate_requirements):
        """Professional certificate integration"""

    def handle_exchange_programs(self, exchange_data):
        """International exchange credit planning"""
```

### 🔗 External System Integration

#### University System Connections:
```python
class SystemIntegrator:
    def sync_with_acorn(self, student_credentials):
        """Direct ACORN integration (if API available)"""

    def integrate_with_degree_explorer(self, degree_data):
        """Degree Explorer data synchronization"""

    def connect_to_timetable_builder(self, course_selections):
        """Automated timetable generation"""

    def sync_with_library_systems(self, course_codes):
        """Course reading list integration"""
```

#### Third-Party Enhancements:
- **Rate My Professor Integration**: Professor ratings and reviews
- **Course Evaluation Data**: Historical course feedback
- **Reddit/Discord Integration**: Student community insights
- **LinkedIn Learning**: Skill development recommendations
- **Graduate School Planning**: Post-graduation pathway analysis

### 🚀 Advanced Features

#### AI-Powered Academic Advisor:
```python
class AIAcademicAdvisor:
    def __init__(self):
        self.nlp_processor = NLPProcessor()
        self.knowledge_base = AcademicKnowledgeBase()

    def answer_academic_questions(self, question):
        """Natural language academic advising"""

    def provide_career_guidance(self, student_profile, career_interests):
        """AI-powered career path recommendations"""

    def suggest_research_opportunities(self, academic_interests):
        """Research opportunity matching"""

    def plan_graduate_school_preparation(self, target_programs):
        """Graduate school preparation planning"""
```

#### Smart Notifications & Alerts:
- **Course Opening Alerts**: Real-time notifications for waitlisted courses
- **Deadline Reminders**: Academic milestone and application deadlines
- **Prerequisite Warnings**: Alerts for potential scheduling conflicts
- **GPA Risk Alerts**: Early warning for academic standing issues
- **Graduation Timeline Updates**: Progress milestone notifications

## Technical Architecture & Implementation

### 🏗️ System Architecture

#### Modular Design:
```
course_dashboard/
├── core/
│   ├── database/
│   │   ├── migration_manager.py
│   │   ├── models.py
│   │   └── query_optimizer.py
│   ├── scraping/
│   │   ├── advanced_scraper.py
│   │   ├── session_manager.py
│   │   └── data_processor.py
│   └── analytics/
│       ├── requirements_engine.py
│       ├── performance_analyzer.py
│       └── predictor.py
├── planning/
│   ├── prerequisite_checker.py
│   ├── course_recommender.py
│   ├── sequence_planner.py
│   └── timeline_optimizer.py
├── ui/
│   ├── advanced_dashboard.py
│   ├── planning_interface.py
│   ├── analytics_dashboard.py
│   └── visualization_engine.py
├── integration/
│   ├── external_apis.py
│   ├── data_sync.py
│   └── export_manager.py
└── ml/
    ├── prediction_models.py
    ├── recommendation_engine.py
    └── pattern_analyzer.py
```

#### Technology Stack:
- **Backend**: Python 3.9+, SQLite/PostgreSQL, SQLAlchemy
- **Web Scraping**: Selenium, BeautifulSoup, Requests-HTML
- **Data Processing**: Pandas, NumPy, NLTK
- **Machine Learning**: Scikit-learn, TensorFlow (optional)
- **Visualization**: Matplotlib, Plotly, Seaborn
- **GUI**: tkinter (current), web interface (future)
- **Caching**: Redis (optional), file-based caching
- **Testing**: pytest, selenium testing framework

### 🗄️ Enhanced Database Schema

#### Complete Table Structure:
```sql
-- Core academic data (existing + enhanced)
academic_courses (enhanced with difficulty metrics)
transcript_courses (existing)
planned_courses (existing)
course_prerequisites (existing)

-- Phase 1: Academic foundation (completed)
programs (completed)
student_programs (completed)
degree_requirements (completed)
breadth_categories (completed)
course_breadth (completed)
program_requirements (completed)
academic_standing (completed)

-- Phase 2: Course planning
course_prerequisites_structured
course_metrics
course_offerings
planned_course_sequences

-- Phase 3: Advanced analytics
course_evaluations
professor_data
enrollment_history
grade_distributions
student_performance_metrics

-- Phase 4: Integration
external_system_sync
notification_preferences
career_planning_data
research_opportunities
```

### ⚡ Performance Optimization

#### Caching Strategy:
- **Course Data**: 24-hour cache for course information
- **Prerequisites**: Static cache with weekly updates
- **Analytics**: On-demand calculation with result caching
- **Web Scraping**: Intelligent rate limiting and retry logic

#### Query Optimization:
- **Database Indexing**: Comprehensive index strategy
- **Connection Pooling**: Efficient database connections
- **Lazy Loading**: Load data only when needed
- **Batch Operations**: Bulk database operations

## User Experience Design

### 🎨 Modern Interface Design

#### Design Principles:
- **Clean & Intuitive**: Minimal cognitive load
- **Responsive**: Adapts to different screen sizes
- **Accessible**: WCAG compliance for all users
- **Fast**: Sub-second response times
- **Visual**: Rich data visualization

#### Navigation Structure:
```
Main Dashboard
├── Course Search (enhanced with filters)
├── My Transcript (existing + analytics)
├── Course Planning (new advanced planner)
├── Requirements (Phase 1 complete)
├── Analytics (comprehensive insights)
├── Timeline (graduation planning)
└── Settings (preferences and sync)
```

### 🎯 User Workflows

#### Primary Use Cases:
1. **New Student Setup**: Program selection and initial planning
2. **Semester Planning**: Course selection and scheduling
3. **Progress Tracking**: Continuous requirement monitoring
4. **Course Discovery**: Finding optimal courses for goals
5. **Graduation Planning**: Timeline and requirement validation
6. **What-If Analysis**: Testing different academic scenarios

## Quality Assurance & Testing

### 🧪 Testing Strategy

#### Test Coverage:
- **Unit Tests**: 90%+ coverage for core functionality
- **Integration Tests**: Database and scraping components
- **UI Tests**: Automated GUI testing with selenium
- **Performance Tests**: Load testing and optimization
- **User Acceptance Tests**: Real student feedback

#### Test Data:
- **Synthetic Transcripts**: Various academic scenarios
- **Edge Cases**: Complex prerequisite chains
- **Error Conditions**: Network failures, data corruption
- **Load Testing**: Concurrent user simulation

### 🔒 Security & Privacy

#### Data Protection:
- **Local Storage**: No cloud data transmission by default
- **Encryption**: Sensitive data encryption at rest
- **Access Control**: User authentication (future web version)
- **Privacy**: No personal data collection
- **Backup**: Automated local backup system

## Deployment & Maintenance

### 📦 Distribution Strategy

#### Release Versions:
- **v2.0**: Phase 1 complete (current)
- **v2.5**: Phase 2 planning features
- **v3.0**: Phase 3 analytics and automation
- **v4.0**: Phase 4 advanced integration

#### Deployment Options:
- **Standalone Desktop**: Current tkinter application
- **Web Application**: Future browser-based version
- **Mobile App**: React Native or Flutter version
- **API Service**: Backend API for third-party integration

### 🔄 Maintenance Plan

#### Regular Updates:
- **Weekly**: Course offering updates
- **Monthly**: Academic calendar synchronization
- **Quarterly**: Feature enhancements and bug fixes
- **Annually**: Major version releases

#### Monitoring:
- **Error Tracking**: Comprehensive error logging
- **Performance Metrics**: Response time monitoring
- **User Analytics**: Feature usage analysis
- **Feedback Collection**: User satisfaction tracking

## Success Metrics & ROI

### 📊 Key Performance Indicators

#### Technical Metrics:
- **Data Accuracy**: 99%+ correct course information
- **Response Time**: <1 second for most operations
- **Uptime**: 99.9% availability
- **User Satisfaction**: 4.5+ stars average rating

#### Academic Impact:
- **Graduation Rate Improvement**: Track student success
- **Course Planning Efficiency**: Time saved in advising
- **Requirement Compliance**: Reduced degree audit errors
- **Student Satisfaction**: Academic planning confidence

### 💰 Value Proposition

#### For Students:
- **Time Savings**: 10+ hours per semester in planning
- **Better Decisions**: Data-driven course selection
- **Reduced Risk**: Prerequisite and scheduling conflict prevention
- **Academic Success**: Optimized graduation pathways

#### For Institutions:
- **Reduced Advising Load**: Self-service academic planning
- **Improved Graduation Rates**: Better student planning
- **Data Insights**: Academic program analytics
- **Student Satisfaction**: Enhanced academic experience

## Risk Assessment & Mitigation

### ⚠️ Technical Risks

#### Web Scraping Risks:
- **Website Changes**: Regular scraper updates required
- **Rate Limiting**: Implement respectful scraping practices
- **Legal Compliance**: Ensure terms of service compliance
- **Data Quality**: Validation and error checking

#### Mitigation Strategies:
- **Modular Design**: Easy component updates
- **Fallback Systems**: Manual data entry options
- **Version Control**: Rollback capabilities
- **User Feedback**: Community-driven error reporting

### 📋 Academic Risks

#### Data Accuracy:
- **Outdated Information**: Regular synchronization required
- **Complex Requirements**: Edge case handling
- **Policy Changes**: Academic regulation updates

#### Mitigation:
- **Multiple Sources**: Cross-validation of data
- **User Verification**: Student confirmation of critical decisions
- **Disclaimer System**: Clear limitation statements
- **Professional Backup**: Encourage official academic advising

## Future Vision & Roadmap

### 🔮 Long-term Goals (Years 2-3)

#### Advanced AI Integration:
- **Natural Language Interface**: Chat-based academic advising
- **Personalized Learning**: Adaptive course recommendations
- **Career Prediction**: ML-powered career outcome forecasting
- **Research Matching**: AI-driven research opportunity discovery

#### Ecosystem Expansion:
- **Multi-University Support**: Canadian university network
- **International Programs**: Study abroad integration
- **Professional Development**: Continuing education planning
- **Alumni Network**: Career mentorship connections

### 🌟 Innovation Opportunities

#### Emerging Technologies:
- **Blockchain Credentials**: Secure academic record management
- **VR/AR Visualization**: Immersive course planning experience
- **IoT Integration**: Smart campus data integration
- **Voice Interface**: Hands-free academic planning

#### Collaborative Features:
- **Peer Planning**: Collaborative course selection
- **Study Group Formation**: Automatic study partner matching
- **Academic Social Network**: Course review and discussion platform
- **Mentorship Platform**: Senior student guidance system

## Conclusion

This master plan transforms the UofT Course Dashboard from a simple transcript tracker into a comprehensive academic planning ecosystem. By implementing this plan across four phases, we create a tool that not only tracks academic progress but actively guides students toward successful graduation while providing unprecedented insights into their academic journey.

The system will serve as a model for academic planning tools, demonstrating how intelligent automation, comprehensive data integration, and user-centric design can revolutionize the student academic experience. With its modular architecture and extensible design, the platform will continue to evolve and adapt to changing academic landscapes while maintaining its core mission of empowering students to make informed academic decisions.

## Phase 5: Web Platform & Cloud Integration (Weeks 17-20) 🌐

### 🎯 **Objectives**
Transform the desktop application into a modern web platform with cloud integration, multi-user support, and advanced collaboration features.

### 🚀 **Web Platform Migration**

#### **Technology Stack:**
- **Frontend**: React/Vue.js with modern UI framework
- **Backend**: FastAPI/Django REST framework
- **Database**: PostgreSQL with cloud hosting
- **Authentication**: JWT-based auth with university SSO
- **Deployment**: Docker containers with cloud hosting (AWS/Azure)

#### **Key Features:**
- **Multi-User Support**: Individual student accounts with data isolation
- **Cloud Sync**: Cross-device synchronization
- **Collaboration**: Shared planning sessions and course discussions
- **Real-Time Updates**: Live data synchronization across users
- **API Access**: RESTful API for third-party integrations

---

## Updated Development Timeline 📅

### **Phase Status Overview:**

| Phase | Duration | Status | Focus Area |
|-------|----------|--------|------------|
| **Phase 1** | ✅ **Complete** | Weeks 1-4 | **Academic Foundation** |
| **Phase 2** | 🎯 **Current Priority** | Weeks 5-8 | **GUI Modernization (PyQt6/PySide6)** |
| **Phase 3** | 📋 **Planned** | Weeks 9-12 | **Intelligent Course Planning** |
| **Phase 4** | 📋 **Planned** | Weeks 13-16 | **Advanced Analytics & ML** |
| **Phase 5** | 🔮 **Future** | Weeks 17-20 | **Web Platform & Cloud** |

### **Phase 2 Ready to Begin: PyQt6/PySide6 Migration**

#### **Current Status: Migration Planning Complete**
- ✅ **Phase 1**: All academic foundation features implemented and tested
- ✅ **Architecture**: Well-documented, organized codebase ready for migration
- ✅ **Planning**: Detailed migration strategy and technical approach defined
- 🎯 **Next**: Begin PyQt6/PySide6 development environment setup

#### **Immediate Actions for Phase 2A (Week 5):**
1. **Environment Setup**: Install PyQt6/PySide6 and configure development tools
2. **Project Structure**: Create new gui_qt/ directory and organize components
3. **Main Window**: Implement basic QMainWindow with tab system
4. **Database Integration**: Ensure existing UnifiedCourseDatabase works with PyQt6
5. **Basic Styling**: Establish initial theme and styling framework

#### **Migration Priority Order:**
1. **Main Application Window** - Core QMainWindow structure
2. **Course Search Tab** - Most complex tab with search, results, and details
3. **Transcript Tab** - Data-heavy tab with table operations
4. **Requirements Tab** - Visual progress and calculations
5. **Planning/GPA Tabs** - Enhanced features and visualizations
6. **Dialogs & Polish** - Course dialogs, bulk operations, themes

### **Success Metrics:**

- ✅ **Phase 1**: Functional academic foundation with comprehensive features
- 🎯 **Phase 2**: Modern, professional GUI with enhanced user experience
- 📊 **Phase 3**: Intelligent course recommendations and prerequisite validation
- 🤖 **Phase 4**: Predictive analytics and machine learning insights
- 🌐 **Phase 5**: Full web platform with cloud integration and collaboration

---

**Updated Estimated Development Time**: 20 weeks
**Current Progress**: Phase 1 Complete (25% of total roadmap)
**Next Milestone**: Modern PyQt6/PySide6 Interface (Phase 2)
**Estimated Lines of Code**: 20,000+ lines
**Database Tables**: 25+ comprehensive tables
**Student Impact**: Revolutionary academic planning experience

*This updated master plan prioritizes frontend modernization to create an exceptional user experience before expanding into advanced backend features. The PyQt6/PySide6 migration will provide a solid foundation for all future enhancements while delivering immediate visual and usability improvements.*