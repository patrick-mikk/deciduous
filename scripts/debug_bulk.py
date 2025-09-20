#!/usr/bin/env python3
"""
Debug script for bulk operations
"""
import sys
import os
from pathlib import Path

# Add src directory to path
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))
os.chdir(project_root)

def add_test_courses():
    """Add test courses to database"""
    from main import UnifiedCourseDatabase

    db = UnifiedCourseDatabase()

    # Add multiple test courses
    test_courses = [
        {'course_code': 'CSC108H1', 'title': 'Introduction to Computer Programming', 'credits': 0.5, 'grade': 'A', 'mark': 85.0, 'session': 'Fall', 'year': 2023, 'status': 'completed', 'gpa_points': 4.0},
        {'course_code': 'CSC148H1', 'title': 'Introduction to Computer Science', 'credits': 0.5, 'grade': 'B+', 'mark': 78.0, 'session': 'Winter', 'year': 2024, 'status': 'completed', 'gpa_points': 3.3},
        {'course_code': 'MAT137Y1', 'title': 'Calculus', 'credits': 1.0, 'grade': 'A-', 'mark': 82.5, 'session': 'Fall', 'year': 2023, 'status': 'completed', 'gpa_points': 3.7}
    ]

    for course in test_courses:
        db.save_transcript_course(course)
        print(f"Added: {course['course_code']}")

    courses = db.get_transcript_courses()
    print(f"Total courses now: {len(courses)}")

    return courses

def test_bulk_operations_manually():
    """Test bulk operations manually"""
    from main import UnifiedCourseDatabase

    db = UnifiedCourseDatabase()
    courses = db.get_transcript_courses()

    if len(courses) < 2:
        print("Adding test courses...")
        courses = add_test_courses()

    print(f"Testing with {len(courses)} courses")

    # Test bulk update
    print("\nTesting bulk update...")
    if len(courses) >= 2:
        course_ids = [courses[0][0], courses[1][0]]  # Get first two course IDs

        # Prepare update data
        updates = []
        for course_id in course_ids:
            course_data = {
                'course_code': f'UPDATED{course_id}',
                'title': 'Updated Title',
                'credits': 0.5,
                'grade': 'B',
                'mark': 75.0,
                'session': 'Summer',
                'year': 2024,
                'status': 'completed',
                'gpa_points': 3.0
            }
            updates.append((course_id, course_data))

        try:
            db.bulk_update_transcript_courses(updates)
            print("Bulk update successful!")
        except Exception as e:
            print(f"Bulk update failed: {e}")
            import traceback
            traceback.print_exc()

    # Test bulk delete
    print("\nTesting bulk delete...")
    courses = db.get_transcript_courses()
    if len(courses) >= 1:
        course_id = courses[-1][0]  # Get last course ID
        try:
            db.delete_transcript_courses([course_id])
            print("Bulk delete successful!")
        except Exception as e:
            print(f"Bulk delete failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    print("Bulk Operations Debug Script")
    print("=" * 40)

    try:
        test_bulk_operations_manually()
        print("\nDirect database operations completed.")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()