#!/usr/bin/env python3
"""
PyQt6 Entry Point for UofT Course Dashboard
Modern GUI application with enhanced user experience
"""

import sys
import os
from pathlib import Path

# Add current directory to path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def check_dependencies():
    """Check if PyQt6 and other dependencies are available"""
    missing_deps = []

    try:
        from PyQt6.QtWidgets import QApplication
        print("PyQt6 available")
    except ImportError:
        missing_deps.append("PyQt6>=6.4.0")

    try:
        from gui_qt import check_requirements
        if not check_requirements():
            missing_deps.append("See gui_qt package requirements")
    except ImportError:
        missing_deps.append("gui_qt package initialization failed")

    if missing_deps:
        print("Missing dependencies:")
        for dep in missing_deps:
            print(f"  - {dep}")
        print("\nInstall with:")
        print("  pip install -r config/requirements_qt.txt")
        return False

    return True

def main():
    """Main application entry point"""
    print("UofT Course Dashboard - PyQt6 Edition")
    print("=" * 50)

    # Check dependencies
    if not check_dependencies():
        print("\nDependencies missing. Please install required packages.")
        sys.exit(1)

    # Import main window
    try:
        from gui_qt.main_window import main as run_qt_app
        print("GUI components loaded successfully")
        print("Starting PyQt6 application...")

        # Run the application
        run_qt_app()

    except ImportError as e:
        print(f"Failed to import GUI components: {e}")
        print("Make sure PyQt6 is installed: pip install PyQt6>=6.4.0")
        sys.exit(1)

    except Exception as e:
        print(f"Application error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()