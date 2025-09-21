#!/usr/bin/env python3
"""
Debug MainWindow initialization
"""
import sys
import os
from pathlib import Path

# Add src directory to path
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))
os.chdir(project_root)

def debug_mainwindow():
    """Debug MainWindow step by step"""
    try:
        print("Debugging MainWindow initialization...")

        from PyQt6.QtWidgets import QApplication
        print("1. PyQt6 imported")

        from main import UnifiedCourseDatabase
        print("2. Database imported")

        db = UnifiedCourseDatabase()
        print("3. Database created")

        app = QApplication([])  # Use empty sys.argv
        print("4. QApplication created")

        # Import MainWindow but don't create it yet
        from gui_qt.main_window import MainWindow
        print("5. MainWindow imported")

        # Try to create MainWindow
        print("6. Creating MainWindow...")
        window = MainWindow()
        print("7. MainWindow created successfully!")

        # Don't show or run - just test creation
        print("8. MainWindow initialization complete")
        app.quit()
        return 0

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = debug_mainwindow()
    print(f"Debug completed with exit code: {exit_code}")
    sys.exit(exit_code)