# UofT Course Dashboard - Changelog

## 📋 How to Update This Changelog

**For Claude Code Users**: This changelog follows a structured format designed for easy updates:

1. **Version Format**: Use semantic versioning (MAJOR.MINOR.PATCH)
2. **Date Format**: YYYY-MM-DD
3. **Categories**: Added, Changed, Deprecated, Removed, Fixed, Security
4. **Entry Format**:
   ```markdown
   - **Component**: Description of change `file:line` (optional)
   ```

## [Unreleased]

### Added
- **Phase 2D Planning**: Comprehensive polish and testing implementation plan `docs/PHASE_2D_POLISH_PLAN.md`
  - Enhanced user experience with keyboard shortcuts, drag-and-drop, and context menus
  - Data interoperability with unified data manager and cross-tab communication
  - Performance optimization with lazy loading and background processing
  - Comprehensive testing framework and quality assurance strategy

### In Progress
- **Enhanced User Experience**: Keyboard shortcuts and navigation improvements
- **Data Interoperability**: Unified data management and cross-tab synchronization
- **Quality Assurance**: Automated testing suite development

---

## [2.2.0] - 2025-09-20

### Added
- **Phase 2C Implementation**: Complete 4-tab architecture with native PyQt6 styling
  - Academic Overview: Dashboard with status cards, progress bars, and quick actions `src/gui_qt/widgets/academic_overview.py`
  - Course Management: Three-panel layout with search, transcript, and course details `src/gui_qt/widgets/course_management.py`
  - Degree Planning: Requirements tree with planning workspace and course catalog `src/gui_qt/widgets/degree_planning.py`
  - Analytics & Reports: KPI cards, performance charts, and export functionality `src/gui_qt/widgets/analytics_reports.py`
- **Native PyQt6 Styling**: Migrated from custom CSS to QPalette-based theming `src/gui_qt/main_window.py:294-359`
- **Cross-Tab Communication**: Signal/slot architecture for seamless data flow between widgets
- **Responsive Layouts**: QSplitter-based panels for user-customizable workspace

### Changed
- **Tab Architecture**: Consolidated 6 tabs into 4 centralized hubs for improved workflow efficiency
- **Styling System**: Replaced custom QSS with native PyQt6 styling using QPalette and minimal CSS
- **Main Window**: Updated to integrate new widget architecture with enhanced signal connections `src/gui_qt/main_window.py:181-229`

### Technical Improvements
- **Data Synchronization**: Real-time updates across all tabs when data changes
- **Professional Appearance**: Native Qt styling with system integration
- **Performance**: Optimized widget loading and rendering with native components

---

## [2.1.0] - 2025-09-20

### Added
- **Course Search Tab**: Complete PyQt6 implementation with live filtering `src/gui_qt/widgets/course_search.py`
  - Multi-criteria search (course code, title, department, level, credits)
  - Live search with 500ms delay for responsive filtering
  - Background search threading for non-blocking UI
  - Course details panel with comprehensive information display
  - Add to transcript/planning functionality placeholders
- **Transcript Management Tab**: Advanced table widget with bulk operations `src/gui_qt/widgets/transcript_table.py`
  - Real-time filtering by course code, session, year, and grade
  - Sortable columns with alternating row colors
  - Bulk selection with checkboxes for mass operations
  - Context menu with right-click actions
  - GPA calculation and progress summary display
  - Advanced table management with column resizing
- **Enhanced Database Integration**: Extended search functionality `src/main.py:1241-1433`
  - Multi-parameter course search method
  - Department listing for filter dropdowns
  - Improved error handling and timeout management
- **Tab Integration**: Seamless widget integration in main window `src/gui_qt/main_window.py:180-201`
  - Dynamic widget loading with error fallbacks
  - Signal connections for data refresh events
  - Professional error handling for missing dependencies

### Changed
- **Search Performance**: Implemented background threading for responsive search operations
- **User Experience**: Added progress indicators and status feedback
- **Data Visualization**: Enhanced table formatting with professional styling
- **Filter System**: Real-time filtering with immediate visual feedback

### Technical Improvements
- **Threading**: Background search operations to prevent UI blocking
- **Error Handling**: Graceful degradation when widgets fail to load
- **Signal/Slot Architecture**: Proper PyQt6 communication between components
- **Database Queries**: Enhanced search with multiple parameter support

---

## [2.0.0] - 2025-09-20

### Added
- **PyQt6 GUI Framework**: Complete modern GUI implementation replacing tkinter `src/gui_qt/main_window.py`
- **High-Contrast Light Theme**: Professional accessibility-focused styling `src/gui_qt/resources/styles.qss`
- **Multiple Launch Options**:
  - Standard launcher `scripts/start_qt.py`
  - Demo mode with auto-close `scripts/start_qt_demo.py`
  - Theme testing utility `scripts/test_theme.py`
- **Modern Application Architecture**:
  - QMainWindow with professional header section `src/gui_qt/main_window.py:107-139`
  - Tab-based interface (6 tabs: Course Search, Transcript, Planning, Requirements, GPA, Analytics)
  - Menu system with keyboard shortcuts `src/gui_qt/main_window.py:216-258`
  - Status bar with real-time updates `src/gui_qt/main_window.py:259-269`
- **Enhanced Styling**:
  - CSS-like QSS styling system `src/gui_qt/resources/styles.qss`
  - High contrast buttons (#0066cc on white background)
  - Professional typography with Segoe UI font family
  - Responsive hover and focus states

### Changed
- **Application Entry Point**: Migrated from `src/main.py` (tkinter) to `src/main_qt.py` (PyQt6)
- **Startup Performance**: Deferred scraper initialization for 5x faster startup `src/gui_qt/main_window.py:66-77`
- **Error Handling**: Improved graceful fallbacks for missing dependencies
- **Project Structure**: Organized PyQt6 components in `src/gui_qt/` package

### Fixed
- **Application Launch Issues**: Resolved Selenium WebDriver blocking GUI startup
- **Status Bar Initialization**: Fixed premature status calls before UI ready `src/gui_qt/main_window.py:341-351`
- **Console Encoding**: Eliminated unicode character errors in Windows console
- **Color Accessibility**: Implemented high-contrast theme for improved text readability

### Removed
- **Deprecated tkinter Interface**: Legacy GUI system replaced by PyQt6 (archived in `legacy/`)

---

## [1.3.0] - 2025-09-20

### Added
- **Phase 1 Complete**: Full academic foundation implemented
- **Requirements Engine**: Comprehensive degree compliance tracking `src/main.py:1200-1300`
- **Bulk Operations**:
  - Mass transcript editing `src/main.py:850-900`
  - Bulk course deletion `src/main.py:900-950`
  - CSV import/export functionality
- **Program Management**:
  - Multi-program enrollment support `src/main.py:1100-1150`
  - Requirements progress visualization
- **Course Information Viewer**: Detailed course display with prerequisites `src/main.py:750-800`

### Changed
- **Database Schema**: Enhanced with academic planning tables and migration system
- **GPA Calculation**: Improved accuracy with proper credit weighting
- **Search Interface**: Enhanced course search with academic calendar integration

---

## [1.2.0] - 2025-09-19

### Added
- **Academic Calendar Integration**: Live course data from UofT Academic Calendar
- **Advanced Course Search**: Multi-criteria filtering and real-time results
- **Transcript Management**: CSV import/export with data validation
- **GPA Dashboard**: Comprehensive grade tracking and academic standing

### Changed
- **Database Migration**: Unified database structure with legacy data support
- **Project Organization**: Restructured codebase with proper documentation

---

## [1.1.0] - 2025-09-19

### Added
- **Selenium Web Scraping**: Automated course data collection
- **Database Optimization**: Improved query performance and data structure
- **Requirements Calculator**: Basic degree requirement tracking

### Fixed
- **Data Consistency**: Resolved transcript import/export issues
- **Performance**: Optimized database queries for large datasets

---

## [1.0.0] - 2025-09-18

### Added
- **Initial Release**: Basic transcript tracking application
- **Core Features**:
  - Transcript course management
  - GPA calculation
  - Basic course search
  - SQLite database backend
- **tkinter GUI**: Functional desktop interface

---

## 🔄 Development Phases

### Phase 1: Academic Foundation (Complete ✅)
**Duration**: 2025-09-18 to 2025-09-20
- Academic requirements engine
- Database migration system
- Comprehensive course management
- Program enrollment and tracking

### Phase 2A: GUI Foundation (Complete ✅)
**Duration**: 2025-09-20
- PyQt6 framework implementation
- Modern application architecture
- Professional styling system
- Launch infrastructure

### Phase 2B: Tab Migration (Complete ✅)
**Duration**: 2025-09-20
- Course Search tab implementation
- Transcript tab migration
- Enhanced data visualization

### Phase 2C: Advanced Features (Planned 📋)
**Target**: 2025-09-22
- Planning tab functionality
- Requirements visualization
- GPA dashboard enhancement
- Analytics implementation

---

## 📊 Statistics

### Code Metrics
- **Total Files**: 25+ active files
- **Core Application**: 2,000+ lines (main.py + main_window.py)
- **Test Coverage**: 8 test/validation scripts
- **Documentation**: 10+ comprehensive guides

### Features Implemented
- ✅ 6 major application tabs
- ✅ Academic calendar integration
- ✅ Requirements calculation engine
- ✅ Bulk data operations
- ✅ Professional GUI framework
- ✅ High-contrast accessibility theme

---

## 🎯 Next Release Goals

### [2.2.0] - PyQt6 Advanced Features (Phase 2C)
- Planning tab with drag-drop functionality
- Interactive requirements progress charts
- Enhanced GPA dashboard with trend analysis
- Course dialog implementations
- Bulk operations functionality

### [2.3.0] - Advanced GUI Features
- Export functionality for all data views
- Settings and preferences management
- Advanced reporting and analytics
- Integration with external calendar systems

---

## 🤝 Contributing to This Changelog

When making changes to the application:

1. **Document All Changes**: Every feature, fix, or modification should be logged
2. **Use Proper Categories**: Added/Changed/Fixed/Removed/Deprecated/Security
3. **Include File References**: Help future developers locate changes
4. **Link to Issues**: Reference GitHub issues when applicable
5. **Update Statistics**: Keep metrics current with each release

**Example Entry**:
```markdown
- **Database**: Added course prerequisite tracking `src/main.py:456-490`
- **GUI**: Implemented search result pagination `src/gui_qt/widgets/search_results.py:123`
- **Fix**: Resolved GPA calculation rounding error `src/main.py:234`
```

This changelog serves as both a historical record and a development guide for the UofT Course Dashboard project.