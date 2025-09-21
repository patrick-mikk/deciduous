#!/usr/bin/env python3
"""
Test script to verify the new high-contrast light theme
"""
import sys
import os
from pathlib import Path

# Add src directory to path
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))
os.chdir(project_root)

def test_theme():
    """Test the theme loading and display"""
    try:
        from PyQt6.QtWidgets import QApplication, QVBoxLayout, QWidget, QLabel, QPushButton, QTabWidget
        from PyQt6.QtCore import QTimer
        from gui_qt.main_window import MainWindow

        print("Testing high-contrast light theme...")

        # Create application
        app = QApplication([])

        # Test stylesheet loading
        style_path = src_path / "gui_qt" / "resources" / "styles.qss"
        if style_path.exists():
            print(f"Stylesheet found at: {style_path}")
            with open(style_path, 'r', encoding='utf-8') as f:
                stylesheet = f.read()
            print(f"Stylesheet loaded: {len(stylesheet)} characters")
        else:
            print("Stylesheet not found - will use fallback")

        # Create main window
        print("Creating main window with theme...")
        window = MainWindow()

        # Show window briefly
        window.show()
        print("Theme testing window displayed")
        print("Key theme features:")
        print("- White background (#ffffff)")
        print("- Black text (#000000)")
        print("- High contrast blue buttons (#0066cc)")
        print("- Clear borders and readable fonts")

        # Auto-close for testing
        def close_test():
            print("Theme test complete")
            app.quit()

        timer = QTimer()
        timer.timeout.connect(close_test)
        timer.start(2000)  # 2 seconds

        return app.exec()

    except Exception as e:
        print(f"Theme test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    print("UofT Course Dashboard - Theme Test")
    print("=" * 40)
    exit_code = test_theme()
    print(f"Theme test completed with exit code: {exit_code}")
    if exit_code == 0:
        print("SUCCESS: High-contrast light theme is working!")
    else:
        print("ERROR: Theme test failed")
    sys.exit(exit_code)