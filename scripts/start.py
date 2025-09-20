#!/usr/bin/env python3
"""
Startup script for UofT Course Dashboard
Handles path configuration and launches the main application
"""
import os
import sys
from pathlib import Path

def main():
    """Launch the UofT Course Dashboard application"""
    # Get the project root directory
    project_root = Path(__file__).parent.parent

    # Add src directory to Python path
    src_path = project_root / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

    # Change to project root for relative paths to work correctly
    os.chdir(project_root)

    # Import and run the main application
    try:
        from main import main as run_app
        print("Starting UofT Course Dashboard...")
        print(f"Working directory: {os.getcwd()}")
        run_app()
    except ImportError as e:
        print(f"Error importing main application: {e}")
        print("Make sure you're running from the project root directory")
        sys.exit(1)
    except Exception as e:
        print(f"Error starting application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()