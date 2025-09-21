"""
PyQt6 GUI Package for UofT Course Dashboard
Modern interface implementation with enhanced user experience
"""

__version__ = "2.0.0"
__author__ = "UofT Course Dashboard Team"

# GUI Framework imports
try:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt, QTimer
    from PyQt6.QtGui import QIcon, QFont

    QT_AVAILABLE = True
    print("PyQt6 successfully imported")

except ImportError:
    QT_AVAILABLE = False
    print("PyQt6 not available - please install: pip install PyQt6>=6.4.0")

# Optional enhancements
try:
    import qdarkstyle
    DARK_THEME_AVAILABLE = True
except ImportError:
    DARK_THEME_AVAILABLE = False

try:
    import qtawesome as qta
    ICONS_AVAILABLE = True
except ImportError:
    ICONS_AVAILABLE = False

# Feature flags
FEATURES = {
    'qt6': QT_AVAILABLE,
    'dark_theme': DARK_THEME_AVAILABLE,
    'icons': ICONS_AVAILABLE
}

def check_requirements():
    """Check if all required dependencies are available"""
    missing = []

    if not QT_AVAILABLE:
        missing.append("PyQt6>=6.4.0")

    if missing:
        print(f"Missing dependencies: {', '.join(missing)}")
        print("Install with: pip install -r config/requirements_qt.txt")
        return False

    return True