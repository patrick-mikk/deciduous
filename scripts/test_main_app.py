#!/usr/bin/env python3
"""
Test script for main PyQt6 application debugging
"""
import sys
import os
from pathlib import Path

# Add src directory to path
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))
os.chdir(project_root)

def test_main_app():
    """Test main application startup step by step"""
    try:
        print("Step 1: Testing imports...")
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import QTimer
        print("OK - PyQt6 imports successful")

        print("Step 2: Testing database...")
        from main import UnifiedCourseDatabase
        db = UnifiedCourseDatabase()
        courses = db.get_transcript_courses()
        print(f"OK - Database connection successful - {len(courses)} courses")

        print("Step 3: Testing MainWindow import...")
        from gui_qt.main_window import MainWindow
        print("OK - MainWindow import successful")

        print("Step 4: Creating QApplication...")
        app = QApplication(sys.argv)
        print("OK - QApplication created")

        print("Step 5: Creating MainWindow...")
        window = MainWindow()
        print("OK - MainWindow created")

        print("Step 6: Showing window...")
        window.show()
        print("OK - Window displayed")

        # Auto-close after 3 seconds for testing
        def close_app():
            print("Auto-closing main application...")
            app.quit()

        timer = QTimer()
        timer.timeout.connect(close_app)
        timer.start(3000)  # 3 seconds

        print("Step 7: Starting event loop...")
        result = app.exec()
        print(f"OK - Application completed with code: {result}")
        return result

    except Exception as e:
        print(f"ERROR at step: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    print("Testing UofT Course Dashboard - PyQt6 Main Application")
    print("=" * 60)
    exit_code = test_main_app()
    print(f"\nTest completed with exit code: {exit_code}")
    sys.exit(exit_code)