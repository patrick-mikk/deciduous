# UofT Course Dashboard - Master Enhancement Plan

## Executive Summary

This master plan outlines the complete transformation of the UofT Course Dashboard from a basic transcript tracker into a comprehensive academic planning and degree management system. The plan leverages advanced web scraping, academic calendar integration, and intelligent course planning to create a world-class tool for University of Toronto students.

## Current Status: Phase 1 Complete ✅

**Phase 1: Academic Foundation** has been successfully implemented, providing:
- Database migration system with academic planning tables
- Requirements calculation engine for UofT degree compliance
- Program enrollment and management system
- Breadth requirements tracking (5 categories)
- Academic standing determination and graduation eligibility
- New Requirements tab with comprehensive progress visualization

## Phase 2: Intelligent Course Planning & Prerequisites (Weeks 5-8)

### 🎯 Objectives
Transform the system into an intelligent academic advisor that understands course dependencies, validates prerequisites, and provides smart course recommendations.

### 🗄️ Database Enhancements

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

### 🔧 Core Features Implementation

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

## Phase 4: Integration & Advanced Features (Weeks 13-16)

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

---

**Total Estimated Development Time**: 16 weeks
**Estimated Lines of Code**: 15,000+ lines
**Database Tables**: 20+ comprehensive tables
**API Integrations**: 5+ external systems
**Student Impact**: Transformational academic planning experience

*This master plan represents the complete vision for the UofT Course Dashboard evolution, building upon the solid Phase 1 foundation to create a world-class academic planning and management system.*