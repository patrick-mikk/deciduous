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

### In Progress
- **Documentation**: Comprehensive user guides and API documentation
- **Testing**: Automated test suite development

---

## [3.0.0] - 2025-09-22

### Added
- **Interactive CLI Interface**: Complete migration to modern interactive terminal with arrow key navigation
  - **inquirer** library integration for arrow key navigation and menu selection `src/cli_app.py:16-21`
  - **rich** library for enhanced terminal output with colors, tables, and panels `src/cli_app.py:17-20`
  - Interactive main menu with emoji icons and visual feedback `src/cli_app.py:375-387`
  - Selectable search results with arrow navigation `src/cli_app.py:563-600`
  - Interactive course detail panels with rich formatting `src/cli_app.py:626-675`
- **Enhanced Course Display**: Modern table-based course information presentation
  - Rich table format for transcript view with colored columns `src/cli_app.py:413-419`
  - Course details displayed in formatted panels with proper spacing `src/cli_app.py:663-668`
  - Academic progress statistics with visual indicators `src/cli_app.py:464-474`
- **CSV Import Functionality**: Automated course data import from CSV files
  - Interactive CSV file selection with default path `src/cli_app.py:755`
  - Automatic course title generation for missing data `src/cli_app.py:787-788`
  - Progress indicators during import process `src/cli_app.py:769`
  - Import statistics with success/failure counts `src/cli_app.py:814-817`
- **UofT Grade Scale Integration**: Official University of Toronto grading system
  - Complete grade scale with proper GPA values (A+ through F) `src/cli_app.py:172-185`
  - Support for special grades (CR, NCR, P, LWD, WDR, IPR, INC) `src/cli_app.py:456-467`
  - Accurate GPA calculation excluding non-GPA grades `src/cli_app.py:488-498`

### Changed
- **User Interface**: Complete overhaul from text-based to interactive terminal
  - Replaced numbered menu selection with arrow key navigation
  - Enhanced visual feedback with colors and formatting
  - Modern terminal UI with consistent styling throughout
- **Data Parsing**: Fixed course data structure handling
  - Corrected database field mapping for proper course display `src/cli_app.py:466-471`
  - Added robust error handling for malformed course data `src/cli_app.py:477-479`
  - Improved type checking and validation throughout application
- **Grade System**: Updated to match official UofT undergraduate scale
  - A+/A: 4.0, A-: 3.7, B+: 3.3, B: 3.0, B-: 2.7, C+: 2.3, C: 2.0, C-: 1.7, D+: 1.3, D: 1.0, D-: 0.7, F: 0.0
  - Special grades properly handled without affecting GPA calculations

### Fixed
- **Data Display Errors**: Resolved "object of type 'float' has no len()" errors
  - Added type checking for course data before processing `src/cli_app.py:457`
  - Improved error handling with try-catch blocks throughout data parsing
  - Fixed course field index mapping to match database structure
- **WebDriver Cleanup**: Eliminated urllib3 connection warnings on application exit
  - Enhanced logging configuration to suppress connection warnings `src/core.py:38-45`
  - Improved WebDriver cleanup with silent error handling `src/core.py:511-522`
  - Added warning suppression during driver quit operations `src/cli_app.py:1114-1119`
- **Unicode Handling**: Maintained emoji support while fixing encoding issues
  - Proper terminal encoding configuration for Windows compatibility
  - Balanced emoji usage with ASCII fallbacks where needed

### Technical Improvements
- **Interactive Library Integration**: Professional CLI experience with modern libraries
- **Enhanced Error Handling**: Comprehensive exception handling with user-friendly messages
- **Data Validation**: Robust course data processing with type checking and fallbacks
- **Performance**: Optimized data parsing and display rendering
- **Code Quality**: Improved separation of concerns and method organization

---

## [2.3.0] - 2025-09-20

### Added
- **Phase 2D Implementation**: Complete polish and testing with enhanced UX and data interoperability
  - Comprehensive keyboard shortcuts (Ctrl+1-4 tabs, F5 refresh, Ctrl+F search) `src/gui_qt/main_window.py:547-565`
  - Smart tooltips and context menus throughout interface `src/gui_qt/widgets/academic_overview.py:298-308`
  - Unified data manager for cross-tab communication `src/gui_qt/utils/data_manager.py`
  - Undo/redo system with 50-action history and data validation pipeline
  - Comprehensive settings dialog with theme support `src/gui_qt/dialogs/settings_dialog.py`
- **Theme System**: Support for System Default, Light, Dark, and High Contrast modes
- **Data Interoperability**: Real-time synchronization across all tabs with signal/slot architecture
- **Performance Optimization**: Intelligent caching, lazy loading, and background processing

### Changed
- **Widget Constructors**: Updated all widgets to accept optional data_manager parameter
- **Main Window**: Enhanced with unified data coordination and theme switching capability
- **User Experience**: Seamless cross-tab navigation and context preservation

### Technical Improvements
- **Real-time Updates**: GPA and progress calculations update instantly across all views
- **Error Handling**: Enhanced validation with user-friendly feedback and graceful degradation
- **Settings Persistence**: User preferences saved with QSettings integration
- **Cross-Platform**: Native PyQt6 styling with system theme integration

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