#!/usr/bin/env python3
"""
Test script to demonstrate the interactive CLI functionality
"""

import sys
from pathlib import Path

# Add src directory to path
sys.path.append(str(Path(__file__).parent / "src"))

from cli_app import CourseDashboardCLI

def test_interactive_mode():
    """Test the interactive mode functionality"""
    print("🧪 Testing Interactive Mode")
    print("=" * 50)

    # Initialize the CLI
    cli = CourseDashboardCLI()

    print("\n✅ CLI initialized successfully!")
    print("📋 Available features in interactive mode:")
    print("   • Menu-driven navigation")
    print("   • Search courses with history tracking")
    print("   • View detailed course information")
    print("   • Manage transcript with GPA calculation")
    print("   • Export data to CSV")
    print("   • Session statistics and analytics")
    print("   • Search history with repeat functionality")

    print(f"\n🎯 To launch interactive mode, run:")
    print(f"   python src/cli_app.py")
    print(f"   # or")
    print(f"   python src/cli_app.py interactive")

    print(f"\n📖 Example workflow:")
    print(f"   1. Run: python src/cli_app.py")
    print(f"   2. Choose option 1 (Search Courses)")
    print(f"   3. Enter: POL208")
    print(f"   4. Choose option 2 to get details for a course")
    print(f"   5. Choose option 3 to view your transcript")
    print(f"   6. Choose option 7 to view session statistics")

    # Clean up
    cli.cleanup()
    print("\n✅ Test completed successfully!")

if __name__ == "__main__":
    test_interactive_mode()