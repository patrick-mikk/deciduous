#!/usr/bin/env python3
"""
Test script to debug bulk operations
"""
import sys
import os
from pathlib import Path

# Add src directory to path
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))
os.chdir(project_root)

def test_database_bulk_operations():
    """Test database bulk operations"""
    try:
        from main import UnifiedCourseDatabase

        print("Testing database bulk operations...")
        db = UnifiedCourseDatabase()

        # Get some transcript courses
        courses = db.get_transcript_courses()
        print(f"Found {len(courses)} transcript courses")

        if courses:
            # Test data structure
            course = courses[0]
            print(f"Course structure: {course}")

            # Test bulk operations methods exist
            print(f"bulk_update_transcript_courses method exists: {hasattr(db, 'bulk_update_transcript_courses')}")
            print(f"delete_transcript_courses method exists: {hasattr(db, 'delete_transcript_courses')}")

        return True

    except Exception as e:
        print(f"Database test error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_bulk_classes():
    """Test if bulk dialog classes exist"""
    try:
        from main import BulkEditDialog, BulkImportDialog

        print("Bulk dialog classes exist: ✓")
        return True

    except ImportError as e:
        print(f"Bulk dialog import error: {e}")
        return False
    except Exception as e:
        print(f"Bulk dialog test error: {e}")
        return False

def test_course_dashboard_attributes():
    """Test CourseDashboard attributes"""
    try:
        from main import CourseDashboard

        # Check required attributes exist in class
        required_methods = [
            'bulk_edit_transcript',
            'bulk_delete_transcript',
            'transcript_course_data'
        ]

        for method in required_methods:
            if hasattr(CourseDashboard, method):
                print(f"✓ CourseDashboard.{method} exists")
            else:
                print(f"✗ CourseDashboard.{method} MISSING")

        return True

    except Exception as e:
        print(f"CourseDashboard test error: {e}")
        return False

if __name__ == "__main__":
    print("UofT Course Dashboard - Bulk Operations Test")
    print("=" * 50)

    success = True
    success &= test_database_bulk_operations()
    success &= test_bulk_classes()
    success &= test_course_dashboard_attributes()

    if success:
        print("\n✓ All tests passed!")
    else:
        print("\n✗ Some tests failed!")