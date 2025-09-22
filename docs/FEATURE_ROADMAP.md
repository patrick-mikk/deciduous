# Feature Development Roadmap

## Phase 1: Core CLI Functionality (✅ Completed)

### Essential Features
- ✅ Course search via UofT Academic Calendar
- ✅ Detailed course information retrieval
- ✅ Local transcript management with SQLite
- ✅ GPA calculation and academic statistics
- ✅ CSV export functionality
- ✅ Command-line interface with argparse

### Technical Foundation
- ✅ Selenium WebDriver automation
- ✅ Robust locator strategies with fallbacks
- ✅ SQLite database schema for transcript data
- ✅ Error handling and graceful degradation
- ✅ Comprehensive documentation

## Phase 2: Enhanced Academic Planning (Next Priority)

### Breadth Requirement Tracking
**Complexity**: Medium | **Timeline**: 2-3 weeks
```python
# Implementation approach
def analyze_breadth_requirements(transcript_courses):
    breadth_categories = {
        'Creative and Cultural Representations (1)': [],
        'Thought, Belief and Behaviour (2)': [],
        'Society and its Institutions (3)': [],
        'Living Things and Their Environment (4)': [],
        'The Physical and Mathematical Universes (5)': []
    }
    # Map courses to breadth categories
    # Calculate completion status
    return breadth_analysis
```

### Prerequisite Validation
**Complexity**: High | **Timeline**: 3-4 weeks
```python
# Features to implement
- Parse prerequisite strings from course data
- Build dependency graph of course requirements
- Check if student meets prerequisites for target courses
- Suggest prerequisite courses for degree goals
```

### Credit Tracking and Degree Progress
**Complexity**: Low | **Timeline**: 1 week
```python
# Implementation
def calculate_degree_progress(transcript):
    total_credits = sum(course.credits for course in transcript)
    remaining_credits = 20.0 - total_credits  # Standard degree requirement
    completion_percentage = (total_credits / 20.0) * 100
    return progress_summary
```

## Phase 3: Advanced Search and Filtering (Medium Priority)

### Department and Level Filtering
**Complexity**: Low | **Timeline**: 1-2 weeks
```bash
# New CLI commands
python cli_app.py search --department POL --level 200-299
python cli_app.py search --credits 1.0 --breadth "Society and its Institutions"
```

### Search Result Ranking
**Complexity**: Medium | **Timeline**: 2 weeks
- Relevance scoring based on query matching
- Popular course recommendations
- Prerequisites-based suggestions

## Phase 4: Analytics and Reporting (Lower Priority)

### GPA Trend Analysis
**Complexity**: Medium | **Timeline**: 2-3 weeks
```python
# Features
- Semester-by-semester GPA calculation
- Grade distribution analysis
- Course difficulty patterns by department
- Academic performance visualization (text-based charts)
```

### Progress Reports
**Complexity**: Low | **Timeline**: 1 week
```bash
# Generate comprehensive academic reports
python cli_app.py report --type degree_progress
python cli_app.py report --type gpa_trends
python cli_app.py report --type breadth_analysis
```

## Phase 5: Data Integration and Export (Future Scope)

### Enhanced Export Options
**Complexity**: Low | **Timeline**: 1 week
```python
# Multiple format support
- JSON export for programmatic access
- XML export for external systems
- PDF report generation (using reportlab)
```

### Import Functionality
**Complexity**: High | **Timeline**: 4-6 weeks
```python
# ACORN transcript import (if API available)
# Manual CSV import with validation
# Data verification against official records
```

## Implementation Strategy

### Development Priorities
1. **High Impact, Low Complexity**: Credit tracking, basic filtering
2. **High Impact, Medium Complexity**: Breadth requirement tracking
3. **High Impact, High Complexity**: Prerequisite validation system
4. **Medium Impact**: Advanced analytics and reporting

### Technical Considerations

#### Database Schema Extensions
```sql
-- New tables for enhanced functionality
CREATE TABLE breadth_mappings (
    course_code TEXT PRIMARY KEY,
    breadth_category INTEGER,
    updated_date TEXT
);

CREATE TABLE prerequisite_cache (
    course_code TEXT PRIMARY KEY,
    prerequisites TEXT,
    parsed_requirements TEXT,
    last_updated TEXT
);

CREATE TABLE user_goals (
    id INTEGER PRIMARY KEY,
    goal_type TEXT, -- 'major', 'minor', 'specialist'
    program_name TEXT,
    requirements TEXT,
    created_date TEXT
);
```

#### Performance Optimizations
- **Caching Strategy**: Store scraped course data locally to reduce web requests
- **Batch Processing**: Process multiple courses in single scraping sessions
- **Database Indexing**: Add indexes on frequently queried fields

#### Error Handling Improvements
- **Retry Logic**: Implement exponential backoff for failed web requests
- **Validation**: Enhanced input validation for course codes and data
- **Logging**: Comprehensive logging system for debugging and monitoring

## Risk Assessment

### Technical Risks
- **Website Changes**: UofT Academic Calendar structure modifications
- **Rate Limiting**: Potential blocking of automated requests
- **Data Accuracy**: Ensuring scraped data remains current and accurate

### Mitigation Strategies
- **Locator Monitoring**: Regular testing of selenium locators
- **Respectful Scraping**: Implement delays and request throttling
- **Data Validation**: Cross-reference with multiple sources when possible

## Success Metrics

### User Adoption
- Command usage frequency
- Feature utilization rates
- User feedback and feature requests

### Technical Performance
- Scraping success rates (>95% target)
- Database query performance (<100ms for common operations)
- Error rates (<5% for stable features)

### Academic Value
- Accuracy of GPA calculations (100% for supported grade types)
- Prerequisite validation accuracy (>90% for standard cases)
- Breadth requirement tracking completeness

## Future Extensions (Beyond CLI)

### Web Interface (Phase 6)
**Technology**: Flask/FastAPI + React
**Timeline**: 6-8 weeks
- Visual transcript display
- Interactive course planning
- Real-time GPA calculation
- Course recommendation interface

### Mobile Application (Phase 7)
**Technology**: React Native or Progressive Web App
**Timeline**: 8-12 weeks
- Mobile-optimized course search
- Offline transcript access
- Push notifications for important dates

### Integration APIs (Phase 8)
**Technology**: RESTful APIs with authentication
**Timeline**: 4-6 weeks
- Third-party application integration
- Calendar system synchronization
- Academic advisor dashboard access

## Conclusion

This roadmap provides a structured approach to evolving the CLI application into a comprehensive academic planning tool. The phased development ensures that core functionality remains stable while incrementally adding valuable features that enhance the student experience.

Each phase builds upon previous work, maintaining backwards compatibility while expanding capabilities. The focus on CLI-first development ensures the tool remains accessible and scriptable, while planned future phases can address different user interface preferences.

The feasible feature set balances technical complexity with user value, ensuring that development efforts produce meaningful improvements to student academic planning capabilities.