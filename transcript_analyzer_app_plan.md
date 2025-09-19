# Academic Transcript Analyzer App - Comprehensive Plan

## Overview
A web-based application that processes University of Toronto academic transcripts to calculate GPAs, analyze academic performance, and simulate future scenarios using the official UofT grading scale.

## Core Features

### 1. Data Input & Processing
- **CSV Upload**: Support for transcript CSV files with columns: Term, Year, College, Course_Code, Course_Title, Weight, Mark, Grade, Course_Average
- **Manual Entry**: Form-based interface for individual course entry
- **Data Validation**: 
  - Verify grade formats match UofT standards
  - Check weight values (0.5, 1.0, etc.)
  - Validate mark ranges (0-100)
  - Handle special notations (IPR, LWD, CR/NCR, etc.)

### 2. Grade Point Calculation System
```
Grade Scale Implementation:
A+, A = 4.0    |    B+ = 3.3    |    C+ = 2.3    |    D+ = 1.3
A- = 3.7       |    B = 3.0     |    C = 2.0     |    D = 1.0
               |    B- = 2.7    |    C- = 1.7    |    D- = 0.7
                                                  |    F = 0.0
```

**Special Handling**:
- CR/NCR courses: Excluded from GPA calculation
- IPR courses: Not included in current calculations
- LWD/WDR: No impact on GPA
- AEG, SDF: Course credit granted, grade points as recorded

### 3. GPA Calculations

#### Sessional GPA
- Calculate GPA for each term (Fall, Winter, Summer)
- Weight courses by credit value
- Formula: `Σ(Grade Points × Credits) / Σ(Credits)`

#### Cumulative GPA
- Overall GPA across all completed terms
- Include only courses with numeric grades
- Handle retaken courses (higher grade replaces lower)

#### Program-Specific Calculations
- Major GPA (courses within specific program)
- Last 20 courses GPA
- Final year GPA

### 4. Analytics Dashboard

#### Performance Visualization
- **GPA Trend Charts**: Line graphs showing sessional GPA over time
- **Grade Distribution**: Bar charts of grade frequencies
- **Credit Progress**: Visual progress toward degree requirements
- **Performance Heatmap**: Visual representation of grades by term/year

#### Statistical Analysis
- **Academic Standing**: Determine Dean's List, probation status
- **Grade Improvement**: Track progression over time
- **Course Difficulty Analysis**: Compare personal grades to course averages
- **Credit Completion Rate**: Percentage of attempted vs. completed credits

### 5. Simulation Tools

#### "What-If" GPA Calculator
- **Future Course Planning**: Input planned courses with expected grades
- **Grade Impact Simulator**: See how different grades affect cumulative GPA
- **Graduation GPA Projector**: Estimate final GPA based on remaining courses
- **Academic Goal Planner**: Calculate required grades to achieve target GPA

#### Scenario Modeling
- **Course Retake Advisor**: Calculate GPA improvement from retaking courses
- **Course Load Optimizer**: Suggest optimal course combinations
- **Summer School Impact**: Analyze benefits of additional courses

### 6. Academic Insights

#### Personalized Recommendations
- Identify weak subject areas
- Suggest courses to improve GPA
- Recommend optimal course timing
- Academic milestone tracking

#### Comparative Analysis
- Compare performance to course averages
- Benchmark against typical academic progression
- Identify exceptional performance areas

## Technical Architecture

### Frontend (React.js)
```
Components:
├── Dashboard/
│   ├── GPA_Summary.jsx
│   ├── Performance_Charts.jsx
│   └── Academic_Standing.jsx
├── DataInput/
│   ├── CSV_Uploader.jsx
│   ├── Course_Entry_Form.jsx
│   └── Data_Validator.jsx
├── Calculator/
│   ├── Sessional_GPA.jsx
│   ├── Cumulative_GPA.jsx
│   └── What_If_Calculator.jsx
├── Analytics/
│   ├── Trend_Analysis.jsx
│   ├── Grade_Distribution.jsx
│   └── Course_Performance.jsx
└── Simulator/
    ├── Future_Planning.jsx
    ├── Retake_Advisor.jsx
    └── Goal_Planner.jsx
```

### Backend Logic (JavaScript/Node.js)
```
Core Functions:
├── gradeToGPA(grade) → number
├── calculateSessionalGPA(courses) → number
├── calculateCumulativeGPA(allCourses) → number
├── handleSpecialNotations(course) → boolean
├── validateTranscriptData(data) → validation_result
├── generateAcademicInsights(transcript) → insights
└── simulateFutureGPA(current, planned) → projection
```

### Data Processing
```javascript
// Grade Point Mapping
const GRADE_POINTS = {
  'A+': 4.0, 'A': 4.0, 'A-': 3.7,
  'B+': 3.3, 'B': 3.0, 'B-': 2.7,
  'C+': 2.3, 'C': 2.0, 'C-': 1.7,
  'D+': 1.3, 'D': 1.0, 'D-': 0.7,
  'F': 0.0
};

// Special Notations (excluded from GPA)
const EXCLUDED_GRADES = ['CR', 'NCR', 'IPR', 'LWD', 'WDR', 'AEG', 'SDF'];
```

## User Interface Design

### Dashboard Layout
1. **Header**: Current GPA, academic standing, total credits
2. **Quick Stats**: Best/worst performing courses, grade trends
3. **Navigation Tabs**: Overview, Analytics, Simulator, Settings
4. **Visual Elements**: Charts, progress bars, achievement badges

### Key Screens
1. **Import Screen**: CSV upload with preview and validation
2. **Overview Dashboard**: High-level academic summary
3. **Detailed Analytics**: Deep-dive into performance metrics
4. **GPA Simulator**: Interactive planning tools
5. **Course Browser**: Searchable course history with filters

## Advanced Features

### Academic Planning Tools
- **Degree Audit**: Track progress toward graduation requirements
- **Course Sequencing**: Visualize prerequisite chains
- **Workload Balancing**: Optimize course difficulty distribution

### Export & Reporting
- **PDF Academic Summary**: Professional transcript analysis
- **Excel Export**: Detailed course data and calculations
- **Progress Reports**: Customizable academic reports

### Integration Capabilities
- **University Systems**: Connect with student information systems
- **Academic Calendars**: Import course requirements and prerequisites
- **Advisor Sharing**: Secure sharing with academic advisors

## Data Security & Privacy
- Local data processing (no server storage of personal information)
- Secure CSV parsing and validation
- Option for anonymous usage analytics
- GDPR-compliant data handling

## Validation & Testing
- Test with various UofT transcript formats
- Validate calculations against official university methods
- Edge case handling for complex academic situations
- User acceptance testing with current students

## Future Enhancements
- Multi-university support (different grading scales)
- Mobile application version
- Integration with course selection tools
- Peer comparison features (anonymized)
- Academic advisor collaboration tools

---

## Implementation Priority
1. **Phase 1**: Core GPA calculations and basic dashboard
2. **Phase 2**: Data visualization and analytics
3. **Phase 3**: Simulation and planning tools
4. **Phase 4**: Advanced features and integrations

This comprehensive plan creates a powerful tool for UofT students to understand, analyze, and plan their academic journey with precision and insight.
