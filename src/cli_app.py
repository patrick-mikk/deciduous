#!/usr/bin/env python3
"""
University of Toronto Course Dashboard - Command Line Interface
A simplified CLI tool for managing academic courses and transcript data
"""

import sys
import os
from pathlib import Path
import argparse
from typing import List, Dict, Optional
import json
import warnings

# Suppress warnings
warnings.filterwarnings("ignore")

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

from core import CourseDatabase, AcademicCalendarScraper


class CourseDashboardCLI:
    """Command-line interface for the UofT Course Dashboard"""

    def __init__(self):
        self.database = CourseDatabase()
        self.scraper = None  # Initialize on demand
        self.search_history = []  # Store recent searches
        self.session_stats = {
            'searches_performed': 0,
            'courses_viewed': 0,
            'courses_added': 0,
            'start_time': None
        }
        print("** University of Toronto Course Dashboard (CLI) **")
        print("=" * 50)

    def init_scraper(self):
        """Initialize the academic calendar scraper on demand"""
        if self.scraper is None:
            try:
                print("[*] Initializing academic calendar scraper...")

                # Temporarily suppress stderr to hide Chrome logs
                original_stderr = sys.stderr
                with open(os.devnull, 'w') as devnull:
                    sys.stderr = devnull
                    try:
                        self.scraper = AcademicCalendarScraper(debug=False, headless=True)
                    finally:
                        sys.stderr = original_stderr

                print("[✓] Scraper initialized successfully")
                return True
            except Exception as e:
                print(f"[!] Failed to initialize scraper: {e}")
                return False
        return True

    def search_courses(self, query: str, limit: int = 10):
        """Search for courses using the academic calendar"""
        if not self.init_scraper():
            return

        print(f"\n[*] Searching for courses: '{query}'")
        print("-" * 40)

        try:
            results = self.scraper.search_courses(query, limit)

            if not results:
                print("[!] No courses found")
                return

            print(f"[✓] Found {len(results)} course(s):")
            for i, course in enumerate(results, 1):
                print(f"\n{i}. {course.get('course_code', 'N/A')}")
                print(f"   Title: {course.get('title', 'N/A')}")
                print(f"   Credits: {course.get('credits', 'N/A')}")
                if course.get('description'):
                    desc = course['description'][:100] + "..." if len(course['description']) > 100 else course['description']
                    print(f"   Description: {desc}")

        except Exception as e:
            print(f"[!] Search failed: {e}")

    def get_course_details(self, course_code: str):
        """Get detailed information for a specific course"""
        if not self.init_scraper():
            return

        print(f"\n[*] Getting details for course: {course_code}")
        print("-" * 40)

        try:
            details = self.scraper.get_course_details(course_code)

            if not details:
                print("[!] Course details not found")
                return

            print("[✓] Course Details:")
            print(f"   Code: {details.get('course_code', 'N/A')}")
            print(f"   Title: {details.get('title', 'N/A')}")
            print(f"   Credits: {details.get('credits', 'N/A')}")
            print(f"   Department: {details.get('department', 'N/A')}")
            print(f"   Level: {details.get('level', 'N/A')}")

            if details.get('description'):
                print(f"   Description: {details['description']}")

            if details.get('hours'):
                print(f"   Hours: {details['hours']}")

            if details.get('prerequisites'):
                print(f"   Prerequisites: {details['prerequisites']}")

            if details.get('exclusions'):
                print(f"   Exclusions: {details['exclusions']}")

            if details.get('breadth_requirements'):
                print(f"   Breadth Requirements: {details['breadth_requirements']}")

            # Option to add to transcript
            while True:
                response = input("\n[?] Add this course to your transcript? (y/n): ").lower().strip()
                if response in ['y', 'yes']:
                    self.add_course_to_transcript(details)
                    break
                elif response in ['n', 'no']:
                    break
                else:
                    print("Please enter 'y' or 'n'")

        except Exception as e:
            print(f"[!] Failed to get course details: {e}")

    def add_course_to_transcript(self, course_data: Dict):
        """Add a course to the transcript with user input for grades/session"""
        print("\n[*] Adding course to transcript...")
        print("-" * 30)

        try:
            # Get grade
            valid_grades = ['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'D-', 'F', 'FZ', 'P', 'CR', 'NCR']
            while True:
                grade = input(f"Grade ({'/'.join(valid_grades[:5])}/.../none): ").upper().strip()
                if grade == '' or grade.upper() == 'NONE':
                    grade = ''
                    break
                elif grade in valid_grades:
                    break
                else:
                    print(f"Invalid grade. Valid options: {', '.join(valid_grades)}")

            # Get session
            valid_sessions = ['Fall', 'Winter', 'Summer']
            while True:
                session = input(f"Session ({'/'.join(valid_sessions)}): ").title().strip()
                if session in valid_sessions:
                    break
                else:
                    print(f"Invalid session. Valid options: {', '.join(valid_sessions)}")

            # Get year
            while True:
                year_input = input("Year (e.g., 2024): ").strip()
                try:
                    year = int(year_input)
                    if 2000 <= year <= 2030:
                        break
                    else:
                        print("Year must be between 2000 and 2030")
                except ValueError:
                    print("Please enter a valid year")

            # Prepare course data for database
            transcript_data = {
                'course_code': course_data.get('course_code', ''),
                'title': course_data.get('title', ''),
                'credits': course_data.get('credits', 0.5),
                'grade': grade,
                'semester': session,
                'year': year,
                'status': 'completed'
            }

            # Save to database
            result = self.database.save_course(transcript_data)
            if result:
                print(f"[✓] Successfully added {course_data.get('course_code')} to transcript")
            else:
                print("[!] Failed to add course to transcript")

        except Exception as e:
            print(f"[!] Error adding course to transcript: {e}")

    def view_transcript(self):
        """Display the current transcript"""
        print("\n📜 Your Academic Transcript")
        print("=" * 50)

        try:
            courses = self.database.get_transcript_courses()

            if not courses:
                print("📭 No courses in transcript")
                return

            # Calculate statistics
            total_credits = 0
            total_points = 0
            grade_credits = 0

            grade_points = {
                'A+': 4.0, 'A': 4.0, 'A-': 3.7,
                'B+': 3.3, 'B': 3.0, 'B-': 2.7,
                'C+': 2.3, 'C': 2.0, 'C-': 1.7,
                'D+': 1.3, 'D': 1.0, 'D-': 0.7,
                'F': 0.0, 'FZ': 0.0
            }

            # Display header
            print(f"{'Code':<12} {'Title':<40} {'Credits':<8} {'Grade':<6} {'Session':<8} {'Year':<6}")
            print("-" * 82)

            # Display courses
            for course in courses:
                if len(course) >= 8:
                    code = course[1] if len(course) > 1 else ''
                    title = course[2] if len(course) > 2 else ''
                    credits = course[3] if len(course) > 3 else 0
                    grade = course[4] if len(course) > 4 else ''
                    session = course[6] if len(course) > 6 else ''
                    year = course[7] if len(course) > 7 else ''

                    # Truncate title if too long
                    if len(title) > 37:
                        title = title[:37] + "..."

                    print(f"{code:<12} {title:<40} {credits:<8} {grade:<6} {session:<8} {year:<6}")

                    # Calculate GPA
                    if credits:
                        total_credits += float(credits)
                        if grade in grade_points:
                            total_points += grade_points[grade] * float(credits)
                            grade_credits += float(credits)

            # Display statistics
            print("-" * 82)
            current_gpa = total_points / grade_credits if grade_credits > 0 else 0.0
            print(f"📊 Statistics:")
            print(f"   Total Courses: {len(courses)}")
            print(f"   Total Credits: {total_credits:.1f}")
            print(f"   Current GPA: {current_gpa:.2f}")

        except Exception as e:
            print(f"[!] Error displaying transcript: {e}")

    def export_transcript(self, filename: str = None):
        """Export transcript to CSV file"""
        if filename is None:
            filename = f"transcript_{self.get_current_date()}.csv"

        print(f"\n💾 Exporting transcript to: {filename}")

        try:
            courses = self.database.get_transcript_courses()

            if not courses:
                print("[!] No courses to export")
                return

            import csv
            with open(filename, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)

                # Write header
                writer.writerow(['Course Code', 'Title', 'Credits', 'Grade', 'Mark', 'Session', 'Year', 'Status'])

                # Write courses
                for course in courses:
                    if len(course) >= 8:
                        writer.writerow([
                            course[1] if len(course) > 1 else '',  # course_code
                            course[2] if len(course) > 2 else '',  # title
                            course[3] if len(course) > 3 else '',  # credits
                            course[4] if len(course) > 4 else '',  # grade
                            course[5] if len(course) > 5 else '',  # mark
                            course[6] if len(course) > 6 else '',  # session
                            course[7] if len(course) > 7 else '',  # year
                            course[8] if len(course) > 8 else ''   # status
                        ])

            print(f"[✓] Successfully exported {len(courses)} courses to {filename}")

        except Exception as e:
            print(f"[!] Error exporting transcript: {e}")

    def get_current_date(self):
        """Get current date in YYYY-MM-DD format"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d")

    def interactive_mode(self):
        """Run the application in interactive mode"""
        from datetime import datetime
        self.session_stats['start_time'] = datetime.now()

        print("\n🎯 Interactive Mode - Welcome!")
        print("Type 'help' for available commands or 'quit' to exit\n")

        while True:
            try:
                # Display main menu
                self.show_main_menu()

                # Get user choice
                choice = input("\n📝 Enter your choice: ").strip().lower()

                if choice in ['quit', 'exit', 'q']:
                    print("\n👋 Thanks for using UofT Course Dashboard!")
                    break
                elif choice in ['help', 'h']:
                    self.show_help()
                elif choice == '1':
                    self.interactive_search()
                elif choice == '2':
                    self.interactive_course_details()
                elif choice == '3':
                    self.view_transcript()
                    self.pause_for_user()
                elif choice == '4':
                    self.interactive_export()
                elif choice == '5':
                    self.interactive_add_course()
                elif choice == '6':
                    self.show_statistics()
                elif choice == '7':
                    self.show_session_info()
                elif choice == '8':
                    self.show_search_history()
                else:
                    print("[!] Invalid choice. Please try again.")

            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n[!] Error: {e}")
                print("Please try again or type 'quit' to exit.")

    def show_main_menu(self):
        """Display the main menu options"""
        print("\n" + "=" * 60)
        print("** UNIVERSITY OF TORONTO COURSE DASHBOARD **")
        print("=" * 60)
        print("1.  Search Courses")
        print("2.  Get Course Details")
        print("3.  View Transcript")
        print("4.  Export Transcript")
        print("5.  Add Course to Transcript")
        print("6.  Academic Statistics")
        print("7.  Session Information")
        print("8.  Search History")
        print("?.  Help")
        print("q.  Quit")
        print("=" * 60)

    def show_help(self):
        """Display help information"""
        print("\n📋 HELP - Available Commands")
        print("-" * 50)
        print("1 or search    - Search for courses by code or keyword")
        print("2 or details   - Get detailed information about a course")
        print("3 or transcript - View your current academic transcript")
        print("4 or export    - Export transcript data to CSV file")
        print("5 or add       - Manually add a course to your transcript")
        print("6 or stats     - View academic statistics and GPA")
        print("7 or session   - View current session information")
        print("8 or history   - View search history")
        print("help or h      - Show this help message")
        print("quit or q      - Exit the application")
        print("-" * 50)
        print("💡 Tips:")
        print("  • Course codes should be in format: POL208H1")
        print("  • Use keywords like 'introduction' to find courses")
        print("  • Your transcript data is stored locally")
        self.pause_for_user()

    def interactive_search(self):
        """Interactive course search"""
        print("\n🔍 Course Search")
        print("-" * 30)

        query = input("Enter course code or keyword: ").strip()
        if not query:
            print("[!] Please enter a search term")
            return

        try:
            limit_input = input("Maximum results (default 10): ").strip()
            limit = int(limit_input) if limit_input else 10
            if limit <= 0 or limit > 50:
                limit = 10
        except ValueError:
            limit = 10

        # Track search in history
        if query not in self.search_history:
            self.search_history.append(query)
            if len(self.search_history) > 10:  # Keep last 10 searches
                self.search_history.pop(0)

        self.session_stats['searches_performed'] += 1
        self.search_courses(query, limit)

        # Option to get details on a specific course
        while True:
            choice = input("\n🔎 Enter course code for details (or press Enter to continue): ").strip()
            if not choice:
                break
            self.get_course_details(choice)

        self.pause_for_user()

    def interactive_course_details(self):
        """Interactive course details lookup"""
        print("\n📖 Course Details")
        print("-" * 30)

        course_code = input("Enter course code (e.g., POL208H1): ").strip().upper()
        if not course_code:
            print("[!] Please enter a course code")
            return

        self.session_stats['courses_viewed'] += 1
        self.get_course_details(course_code)
        self.pause_for_user()

    def interactive_export(self):
        """Interactive transcript export"""
        print("\n💾 Export Transcript")
        print("-" * 30)

        filename = input("Enter filename (press Enter for auto-generated): ").strip()
        if not filename:
            filename = None

        self.export_transcript(filename)
        self.pause_for_user()

    def interactive_add_course(self):
        """Interactive course addition to transcript"""
        print("\n[+] Add Course to Transcript")
        print("-" * 30)

        # Get course code
        course_code = input("Enter course code (e.g., POL208H1): ").strip().upper()
        if not course_code:
            print("[!] Please enter a course code")
            return

        # Get course title
        title = input("Enter course title: ").strip()
        if not title:
            print("[!] Please enter a course title")
            return

        # Get credits
        try:
            credits_input = input("Enter credits (0.5 or 1.0): ").strip()
            credits = float(credits_input)
            if credits not in [0.5, 1.0]:
                print("[!] Warning: Unusual credit value. Continuing anyway.")
        except ValueError:
            print("[!] Invalid credit value. Using 0.5 as default.")
            credits = 0.5

        # Create course data
        course_data = {
            'course_code': course_code,
            'title': title,
            'credits': credits
        }

        self.session_stats['courses_added'] += 1
        self.add_course_to_transcript(course_data)
        self.pause_for_user()

    def show_statistics(self):
        """Display detailed academic statistics"""
        print("\n📊 Academic Statistics")
        print("=" * 50)

        try:
            courses = self.database.get_transcript_courses()

            if not courses:
                print("📭 No courses in transcript yet")
                self.pause_for_user()
                return

            # Basic statistics
            total_credits = 0
            total_points = 0
            grade_credits = 0

            grade_points = {
                'A+': 4.0, 'A': 4.0, 'A-': 3.7,
                'B+': 3.3, 'B': 3.0, 'B-': 2.7,
                'C+': 2.3, 'C': 2.0, 'C-': 1.7,
                'D+': 1.3, 'D': 1.0, 'D-': 0.7,
                'F': 0.0, 'FZ': 0.0
            }

            # Count by department and level
            departments = {}
            levels = {'100': 0, '200': 0, '300': 0, '400': 0, 'Other': 0}
            grade_distribution = {}

            for course in courses:
                if len(course) >= 8:
                    code = course[1] if len(course) > 1 else ''
                    credits = course[3] if len(course) > 3 else 0
                    grade = course[4] if len(course) > 4 else ''

                    # Calculate totals
                    if credits:
                        total_credits += float(credits)
                        if grade in grade_points:
                            total_points += grade_points[grade] * float(credits)
                            grade_credits += float(credits)

                    # Department analysis
                    if code and len(code) >= 3:
                        dept = ''.join(filter(str.isalpha, code[:3]))
                        departments[dept] = departments.get(dept, 0) + 1

                        # Level analysis
                        level_digit = next((c for c in code if c.isdigit()), None)
                        if level_digit:
                            level_key = f"{level_digit}00" if level_digit in ['1','2','3','4'] else 'Other'
                            levels[level_key] += 1

                    # Grade distribution
                    if grade:
                        grade_distribution[grade] = grade_distribution.get(grade, 0) + 1

            # Display statistics
            current_gpa = total_points / grade_credits if grade_credits > 0 else 0.0

            print(f"📈 Overall Statistics:")
            print(f"   Total Courses: {len(courses)}")
            print(f"   Total Credits: {total_credits:.1f}")
            print(f"   Current GPA: {current_gpa:.2f}")
            print(f"   Credits toward degree: {total_credits:.1f}/20.0 ({(total_credits/20.0)*100:.1f}%)")

            print(f"\n🏛️  Department Breakdown:")
            for dept, count in sorted(departments.items()):
                print(f"   {dept}: {count} course(s)")

            print(f"\n📚 Course Level Distribution:")
            for level, count in levels.items():
                if count > 0:
                    print(f"   {level} level: {count} course(s)")

            print(f"\n🎯 Grade Distribution:")
            for grade, count in sorted(grade_distribution.items()):
                print(f"   {grade}: {count} course(s)")

        except Exception as e:
            print(f"[!] Error calculating statistics: {e}")

        self.pause_for_user()

    def show_session_info(self):
        """Display current session information and statistics"""
        print("\n🕒 Session Information")
        print("=" * 50)

        try:
            from datetime import datetime

            if self.session_stats['start_time']:
                elapsed = datetime.now() - self.session_stats['start_time']
                elapsed_str = str(elapsed).split('.')[0]  # Remove microseconds
                print(f"📅 Session started: {self.session_stats['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"[*]  Session duration: {elapsed_str}")
            else:
                print("📅 Session start time: Not recorded")

            print(f"\n📊 Session Activity:")
            print(f"   🔍 Searches performed: {self.session_stats['searches_performed']}")
            print(f"   📖 Courses viewed: {self.session_stats['courses_viewed']}")
            print(f"   [*] Courses added to transcript: {self.session_stats['courses_added']}")

            # Recent search terms
            if self.search_history:
                print(f"\n🔎 Recent searches ({len(self.search_history)}):")
                for i, search in enumerate(reversed(self.search_history[-5:]), 1):
                    print(f"   {i}. {search}")
            else:
                print(f"\n🔎 No searches performed this session")

            # Database stats
            courses = self.database.get_transcript_courses()
            print(f"\n💾 Database Status:")
            print(f"   Total courses in transcript: {len(courses) if courses else 0}")

        except Exception as e:
            print(f"[!] Error displaying session info: {e}")

        self.pause_for_user()

    def show_search_history(self):
        """Display search history with option to repeat searches"""
        print("\n🔎 Search History")
        print("=" * 50)

        if not self.search_history:
            print("📭 No searches performed yet")
            self.pause_for_user()
            return

        print("Recent search terms:")
        for i, search in enumerate(self.search_history, 1):
            print(f"   {i}. {search}")

        while True:
            choice = input(f"\n🔄 Enter number (1-{len(self.search_history)}) to repeat search, or press Enter to continue: ").strip()

            if not choice:
                break

            try:
                index = int(choice) - 1
                if 0 <= index < len(self.search_history):
                    repeat_query = self.search_history[index]
                    print(f"\n🔍 Repeating search for: '{repeat_query}'")

                    # Ask for limit
                    try:
                        limit_input = input("Maximum results (default 10): ").strip()
                        limit = int(limit_input) if limit_input else 10
                        if limit <= 0 or limit > 50:
                            limit = 10
                    except ValueError:
                        limit = 10

                    self.session_stats['searches_performed'] += 1
                    self.search_courses(repeat_query, limit)
                    break
                else:
                    print("[!] Invalid number. Please try again.")
            except ValueError:
                print("[!] Please enter a valid number.")

        self.pause_for_user()

    def pause_for_user(self):
        """Pause and wait for user to press Enter"""
        input("\n[pause]  Press Enter to continue...")

    def cleanup(self):
        """Clean up resources"""
        if self.scraper:
            self.scraper.close_driver()
            print("🧹 Cleaned up scraper resources")


def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(
        description="University of Toronto Course Dashboard CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli_app.py                                  # Launch interactive mode
  python cli_app.py interactive                      # Launch interactive mode
  python cli_app.py search POL208                    # Search for POL208 courses
  python cli_app.py details POL208H1                 # Get details for POL208H1
  python cli_app.py transcript                       # View your transcript
  python cli_app.py export transcript.csv            # Export transcript to CSV
        """
    )

    # Add interactive mode command
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Interactive mode command
    interactive_parser = subparsers.add_parser('interactive', help='Launch interactive mode')

    # Search command
    search_parser = subparsers.add_parser('search', help='Search for courses')
    search_parser.add_argument('query', help='Search query (course code or keyword)')
    search_parser.add_argument('--limit', type=int, default=10, help='Maximum number of results (default: 10)')

    # Details command
    details_parser = subparsers.add_parser('details', help='Get detailed course information')
    details_parser.add_argument('course_code', help='Course code (e.g., POL208H1)')

    # Transcript command
    transcript_parser = subparsers.add_parser('transcript', help='View your academic transcript')

    # Export command
    export_parser = subparsers.add_parser('export', help='Export transcript to CSV')
    export_parser.add_argument('filename', nargs='?', help='Output filename (optional)')

    args = parser.parse_args()

    # Initialize CLI application
    try:
        cli = CourseDashboardCLI()

        # If no command provided, launch interactive mode
        if not args.command:
            print("🚀 Launching interactive mode...")
            cli.interactive_mode()
        # Execute specific command
        elif args.command == 'interactive':
            cli.interactive_mode()
        elif args.command == 'search':
            cli.search_courses(args.query, args.limit)
        elif args.command == 'details':
            cli.get_course_details(args.course_code)
        elif args.command == 'transcript':
            cli.view_transcript()
        elif args.command == 'export':
            cli.export_transcript(args.filename)

    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n[!] Application error: {e}")
    finally:
        if 'cli' in locals():
            cli.cleanup()


if __name__ == "__main__":
    main()