#!/usr/bin/env python3
"""
Demo startup script for PyQt6 UofT Course Dashboard
Shows the application briefly for demonstration purposes
"""
import os
import sys
from pathlib import Path

def main():
    """Launch the PyQt6 UofT Course Dashboard application with auto-close"""
    # Get the project root directory
    project_root = Path(__file__).parent.parent

    # Add src directory to Python path
    src_path = project_root / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

    # Change to project root for relative paths to work correctly
    os.chdir(project_root)

    # Import and run the PyQt6 application
    try:
        print("Starting UofT Course Dashboard - PyQt6 Edition (Demo Mode)...")
        print(f"Working directory: {os.getcwd()}")

        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import QTimer
        from gui_qt.main_window import MainWindow

        # Create application
        app = QApplication(sys.argv)

        # Create main window
        window = MainWindow()
        window.show()

        print("Application window displayed successfully!")
        print("Demo mode: Application will auto-close in 5 seconds...")

        # Auto-close for demo
        def close_demo():
            print("Demo complete - closing application...")
            app.quit()

        timer = QTimer()
        timer.timeout.connect(close_demo)
        timer.start(5000)  # 5 seconds

        # Run the application
        exit_code = app.exec()
        print(f"Application closed with exit code: {exit_code}")
        return exit_code

    except ImportError as e:
        print(f"Import error: {e}")
        print("\nMake sure PyQt6 is installed:")
        print("  pip install -r config/requirements_qt.txt")
        return 1
    except Exception as e:
        print(f"Error starting application: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = main()
    print(f"\nDemo completed with exit code: {exit_code}")
    sys.exit(exit_code)