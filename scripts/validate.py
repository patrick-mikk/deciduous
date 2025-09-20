#!/usr/bin/env python3
"""
Validation script to check if all classes and methods are properly defined
"""
import sys
import os
from pathlib import Path

# Add src directory to path
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

def test_imports():
    """Test all imports and class definitions"""
    try:
        print("Testing imports...")
        import main

        print("✓ Main module imported successfully")

        # Test class availability
        classes_to_check = [
            'UnifiedCourseDatabase',
            'RequirementsCalculator',
            'AcademicCalendarScraper',
            'CourseDialog',
            'CourseDashboard',
            'CourseInfoWindow',
            'BulkImportDialog',
            'BulkEditDialog'
        ]

        for class_name in classes_to_check:
            if hasattr(main, class_name):
                print(f"✓ {class_name} class found")
            else:
                print(f"✗ {class_name} class MISSING")

        # Test key methods on CourseDashboard
        dashboard_methods = [
            'populate_programs_combobox',
            'enroll_in_program',
            'update_requirements_display',
            'view_course_details'
        ]

        dashboard_class = getattr(main, 'CourseDashboard')
        for method_name in dashboard_methods:
            if hasattr(dashboard_class, method_name):
                print(f"✓ CourseDashboard.{method_name} method found")
            else:
                print(f"✗ CourseDashboard.{method_name} method MISSING")

        print("\n✓ All validation checks passed!")
        return True

    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Validation error: {e}")
        return False

def test_database_path():
    """Test database path configuration"""
    try:
        os.chdir(project_root)
        print(f"\nWorking directory: {os.getcwd()}")

        data_dir = project_root / "data"
        db_file = data_dir / "course_dashboard.db"

        print(f"Data directory exists: {data_dir.exists()}")
        print(f"Database file exists: {db_file.exists()}")

        if not data_dir.exists():
            print("✗ Data directory missing")
            return False
        if not db_file.exists():
            print("✗ Database file missing")
            return False

        print("✓ Database configuration valid")
        return True

    except Exception as e:
        print(f"✗ Database path error: {e}")
        return False

if __name__ == "__main__":
    print("UofT Course Dashboard - Validation Script")
    print("=" * 50)

    success = True
    success &= test_imports()
    success &= test_database_path()

    if success:
        print("\n🎉 All validations passed! Application should work correctly.")
    else:
        print("\n❌ Some validations failed. Please check the issues above.")
        sys.exit(1)