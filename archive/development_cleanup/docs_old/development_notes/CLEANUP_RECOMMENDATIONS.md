# Codebase Cleanup Recommendations

## 📋 Files for Deletion

### Debug/Testing Scripts (Safe to Delete)
These scripts were created for debugging during Phase 2A development and are no longer needed:

- `scripts/debug_bulk.py` - Debug script for bulk operations testing
- `scripts/debug_mainwindow.py` - MainWindow initialization debugging
- `scripts/test_bulk_operations.py` - Bulk operations testing
- `scripts/test_final.py` - Final functionality test
- `scripts/test_qt_basic.py` - Basic PyQt6 functionality test
- `scripts/test_main_app.py` - Main application testing

**Reason**: These were temporary debugging scripts used during development. The application now works correctly and these scripts serve no ongoing purpose.

### Obsolete Batch Files (Consider Removing)
- `scripts/start.bat` - Windows batch file for old tkinter version
- `scripts/start_qt.bat` - Basic batch wrapper (superseded by Python scripts)

**Reason**: Python scripts provide better error handling and cross-platform compatibility.

### Legacy Files (Archive or Delete)
- `legacy/course_dashboard_original.py` - Original 173KB tkinter application
- `legacy/academic_cal/` - Old academic calendar implementation
- `legacy/transcript/` - Old transcript analyzer components

**Recommendation**: Archive these files in a separate repository or compressed backup before deletion.

## 📁 Files to Archive

### Move to `archive/` Directory
Create an `archive/` directory and move these items:

```
archive/
├── phase1_tkinter/
│   ├── course_dashboard_original.py
│   └── legacy_courses.db
├── academic_cal_v1/
│   └── [contents of legacy/academic_cal/]
└── transcript_analyzer_v1/
    └── [contents of legacy/transcript/]
```

## 🔧 Files to Keep

### Essential Scripts
- `scripts/start_qt.py` - Primary application launcher
- `scripts/start_qt_demo.py` - Demo mode for testing
- `scripts/test_theme.py` - Theme validation (useful for future development)
- `scripts/validate.py` - Application validation (useful for CI/CD)

### Core Application Files
- `src/main.py` - Core application logic
- `src/main_qt.py` - PyQt6 application entry point
- `src/gui_qt/` - Complete PyQt6 interface package

### Configuration Files
- `config/requirements.txt` - Core dependencies
- `config/requirements_qt.txt` - PyQt6 dependencies
- `.claude/settings.local.json` - Claude Code configuration

### Data Files
- `data/course_dashboard.db` - Current application database
- `courses.db` - Course search database (keep for now)

### Documentation
- All files in `docs/` directory should be kept

## 🗑️ Cleanup Commands

To implement these recommendations:

```bash
# Create archive directory
mkdir archive archive/phase1_tkinter archive/academic_cal_v1 archive/transcript_analyzer_v1

# Archive legacy files
mv legacy/course_dashboard_original.py archive/phase1_tkinter/
mv data/legacy_courses.db archive/phase1_tkinter/ 2>/dev/null || true
mv legacy/academic_cal/* archive/academic_cal_v1/
mv legacy/transcript/* archive/transcript_analyzer_v1/

# Remove empty legacy directories
rmdir legacy/academic_cal legacy/transcript legacy

# Delete debug/test scripts
rm scripts/debug_bulk.py
rm scripts/debug_mainwindow.py
rm scripts/test_bulk_operations.py
rm scripts/test_final.py
rm scripts/test_qt_basic.py
rm scripts/test_main_app.py

# Optionally remove batch files
rm scripts/start.bat
rm scripts/start_qt.bat

# Remove obsolete dependency versions
rm "=6.4.0" 2>/dev/null || true
rm legacy/transcript/1.20.0 2>/dev/null || true
rm legacy/transcript/3.0.9 2>/dev/null || true
rm legacy/transcript/3.6.0 2>/dev/null || true
```

## 📊 Space Savings

Estimated space savings after cleanup:
- **Debug scripts**: ~20KB
- **Legacy files**: ~200KB+ (archived, not deleted)
- **Obsolete files**: ~5KB

## ⚠️ Important Notes

1. **Backup First**: Create a full backup before running cleanup commands
2. **Test After Cleanup**: Run `python scripts/start_qt.py` to ensure application still works
3. **Git Commit**: Commit changes incrementally to track what was removed
4. **Documentation**: Update README.md to reflect new file structure

## 🎯 Post-Cleanup Structure

After cleanup, the project structure will be cleaner:

```
Course-Dashboard/
├── src/                    # Core application code
├── scripts/               # Essential launch/test scripts only
├── docs/                  # Documentation
├── config/                # Configuration files
├── data/                  # Application databases
├── archive/               # Archived legacy components
└── [project files]
```

This cleanup will make the codebase more maintainable and easier to navigate for future development.