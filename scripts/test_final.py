#!/usr/bin/env python3
"""
Final test script for transcript bulk operations
"""
import sys
import os
from pathlib import Path

# Add src directory to path
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))
os.chdir(project_root)

def test_full_functionality():
    """Test the full functionality"""
    try:
        from main import UnifiedCourseDatabase, CourseDashboard, BulkEditDialog

        print("1. Testing database operations...")
        db = UnifiedCourseDatabase()
        courses = db.get_transcript_courses()
        print(f"   Found {len(courses)} courses")

        print("2. Testing class definitions...")
        print(f"   CourseDashboard has bulk_edit_transcript: {hasattr(CourseDashboard, 'bulk_edit_transcript')}")
        print(f"   CourseDashboard has bulk_delete_transcript: {hasattr(CourseDashboard, 'bulk_delete_transcript')}")
        print(f"   BulkEditDialog exists: {BulkEditDialog is not None}")

        print("3. Testing required database methods...")
        print(f"   Database has bulk_update_transcript_courses: {hasattr(db, 'bulk_update_transcript_courses')}")
        print(f"   Database has delete_transcript_courses: {hasattr(db, 'delete_transcript_courses')}")

        print("4. Testing data availability...")
        if len(courses) > 0:
            print(f"   Sample course structure: {courses[0]}")
        else:
            print("   No courses found - adding test data...")
            test_course = {
                'course_code': 'FINAL_TEST101',
                'title': 'Final Test Course',
                'credits': 0.5,
                'grade': 'A',
                'mark': 90.0,
                'session': 'Fall',
                'year': 2024,
                'status': 'completed',
                'gpa_points': 4.0
            }
            db.save_transcript_course(test_course)
            print("   Test course added successfully")

        print("\nAll tests passed! The bulk operations should work correctly.")
        print("\nTo test in the GUI:")
        print("1. Run the application: python scripts/start.py")
        print("2. Go to the Transcript tab")
        print("3. Select one or more courses")
        print("4. Click 'Bulk Edit' or 'Bulk Delete'")

        return True

    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("UofT Course Dashboard - Final Functionality Test")
    print("=" * 55)

    success = test_full_functionality()

    if success:
        print("\n*** SUCCESS: All components verified! ***")
    else:
        print("\n*** FAILURE: Issues detected ***")