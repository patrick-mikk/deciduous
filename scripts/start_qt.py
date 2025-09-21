#!/usr/bin/env python3
"""
Startup script for PyQt6 UofT Course Dashboard
Handles path configuration and launches the PyQt6 application
"""
import os
import sys
from pathlib import Path

def main():
    """Launch the PyQt6 UofT Course Dashboard application"""
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
        print("Starting UofT Course Dashboard - PyQt6 Edition...")
        print(f"Working directory: {os.getcwd()}")

        from main_qt import main as run_qt_app
        run_qt_app()

    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("\nMake sure PyQt6 is installed:")
        print("  pip install -r config/requirements_qt.txt")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()