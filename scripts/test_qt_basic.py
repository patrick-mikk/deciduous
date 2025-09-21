#!/usr/bin/env python3
"""
Basic PyQt6 test script to verify GUI functionality
"""
import sys
import os
from pathlib import Path

# Add src directory to path
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))
os.chdir(project_root)

def test_basic_qt():
    """Test basic PyQt6 functionality"""
    try:
        print("Testing basic PyQt6 functionality...")

        from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
        from PyQt6.QtCore import QTimer

        # Create application
        app = QApplication(sys.argv)
        print("QApplication created successfully")

        # Create simple window
        window = QWidget()
        window.setWindowTitle("PyQt6 Test")
        window.setGeometry(100, 100, 400, 200)

        # Add content
        layout = QVBoxLayout()
        label = QLabel("PyQt6 is working!\nThis is a test window.")
        layout.addWidget(label)
        window.setLayout(layout)

        # Show window
        window.show()
        print("Test window displayed")

        # Auto-close after 3 seconds
        def close_app():
            print("Auto-closing test window...")
            app.quit()

        timer = QTimer()
        timer.timeout.connect(close_app)
        timer.start(3000)  # 3 seconds

        # Run event loop
        print("Starting event loop...")
        return app.exec()

    except Exception as e:
        print(f"PyQt6 test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = test_basic_qt()
    print(f"Test completed with exit code: {exit_code}")
    sys.exit(exit_code)