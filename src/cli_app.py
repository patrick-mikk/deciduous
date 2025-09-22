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

# Interactive CLI libraries
import inquirer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt, Confirm

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
        self.console = Console()  # Rich console for enhanced output
        self.session_stats = {
            'searches_performed': 0,
            'courses_viewed': 0,
            'courses_added': 0,
            'start_time': None
        }

        # Display welcome banner
        self.show_welcome_banner()

    def show_welcome_banner(self):
        """Display a rich welcome banner"""
        title = Text("University of Toronto Course Dashboard", style="bold blue")
        subtitle = Text("Interactive CLI Tool for Academic Course Management", style="italic cyan")

        panel = Panel.fit(
            f"{title}\n{subtitle}",
            border_style="blue",
            padding=(1, 2)
        )

        self.console.print()
        self.console.print(panel)
        self.console.print()

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
        """Add a course to the transcript with interactive prompts"""
        self.console.print("\n[bold blue]📝 Adding Course to Transcript[/bold blue]")

        try:
            # Get grade with interactive selection - UofT Grade Scale
            grade_choices = [
                'A+', 'A', 'A-',           # Excellent (4.0, 4.0, 3.7)
                'B+', 'B', 'B-',           # Good (3.3, 3.0, 2.7)
                'C+', 'C', 'C-',           # Adequate (2.3, 2.0, 1.7)
                'D+', 'D', 'D-',           # Marginal (1.3, 1.0, 0.7)
                'F',                       # Inadequate (0.0)
                'CR',                      # Credit (Pass, no GPA impact)
                'NCR',                     # No Credit (Fail, no GPA impact)
                'P',                       # Pass (no GPA impact)
                'LWD',                     # Late Withdrawal
                'WDR',                     # Withdrawal
                'IPR',                     # In Progress
                'INC',                     # Incomplete
                'No Grade (TBD)'           # To be determined
            ]

            grade_question = [
                inquirer.List(
                    'grade',
                    message="Select grade",
                    choices=grade_choices,
                    default='A'
                )
            ]

            grade_answer = inquirer.prompt(grade_question)
            if not grade_answer:
                return

            grade = '' if grade_answer['grade'] == 'No Grade (TBD)' else grade_answer['grade']

            # Get session
            session_question = [
                inquirer.List(
                    'session',
                    message="Select session",
                    choices=['Fall', 'Winter', 'Summer'],
                    default='Fall'
                )
            ]

            session_answer = inquirer.prompt(session_question)
            if not session_answer:
                return

            session = session_answer['session']

            # Get year
            current_year = 2024
            year_choices = [str(year) for year in range(current_year-2, current_year+3)]

            year_question = [
                inquirer.List(
                    'year',
                    message="Select year",
                    choices=year_choices,
                    default=str(current_year)
                )
            ]

            year_answer = inquirer.prompt(year_question)
            if not year_answer:
                return

            year = int(year_answer['year'])

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
                self.console.print(f"[bold green]✓ Successfully added {course_data.get('course_code')} to transcript[/bold green]")
                self.session_stats['courses_added'] += 1
            else:
                self.console.print("[bold red]✗ Failed to add course to transcript[/bold red]")

        except Exception as e:
            self.console.print(f"[bold red]Error adding course to transcript:[/bold red] {e}")

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

            # University of Toronto Undergraduate Grade Scale
            grade_points = {
                'A+': 4.0, 'A': 4.0, 'A-': 3.7,
                'B+': 3.3, 'B': 3.0, 'B-': 2.7,
                'C+': 2.3, 'C': 2.0, 'C-': 1.7,
                'D+': 1.3, 'D': 1.0, 'D-': 0.7,
                'F': 0.0, 'FZ': 0.0,
                # Additional UofT grades
                'CR': 0.0,  # Credit (no GPA impact)
                'NCR': 0.0, # No Credit (no GPA impact)
                'P': 0.0,   # Pass (no GPA impact)
                'LWD': 0.0, # Late Withdrawal (no GPA impact)
                'WDR': 0.0, # Withdrawal (no GPA impact)
                'IPR': 0.0, # In Progress (no GPA impact)
                'INC': 0.0  # Incomplete (no GPA impact)
            }

            # Display header
            print(f"{'Code':<12} {'Title':<40} {'Credits':<8} {'Grade':<6} {'Session':<8} {'Year':<6}")
            print("-" * 82)

            # Display courses
            for course in courses:
                try:
                    if isinstance(course, (list, tuple)) and len(course) >= 6:
                        code = course[0] if len(course) > 0 else ''
                        title = course[1] if len(course) > 1 else ''
                        credits = course[2] if len(course) > 2 else 0
                        grade = course[3] if len(course) > 3 else ''
                        session = course[4] if len(course) > 4 else ''
                        year = course[5] if len(course) > 5 else ''

                        # Handle None values
                        grade = grade if grade is not None else ''

                        # Truncate title if too long
                        if len(title) > 37:
                            title = title[:37] + "..."

                        print(f"{code:<12} {title:<40} {credits:<8} {grade:<6} {session:<8} {year:<6}")

                        # Calculate GPA - special grades don't count toward GPA
                        non_gpa_grades = {'CR', 'NCR', 'P', 'LWD', 'WDR', 'IPR', 'INC'}

                        if credits:
                            # Always count credits toward total (except NCR, LWD, WDR)
                            if grade not in {'NCR', 'LWD', 'WDR'}:
                                total_credits += float(credits)

                            # Only count toward GPA if it's a letter grade
                            if grade and grade in grade_points and grade not in non_gpa_grades:
                                total_points += grade_points[grade] * float(credits)
                                grade_credits += float(credits)
                except (TypeError, IndexError, ValueError):
                    print(f"Skipping invalid course data: {course}")
                    continue

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
                    try:
                        if isinstance(course, (list, tuple)) and len(course) >= 6:
                            writer.writerow([
                                course[0] if len(course) > 0 else '',  # course_code
                                course[1] if len(course) > 1 else '',  # title
                                course[2] if len(course) > 2 else '',  # credits
                                course[3] if len(course) > 3 else '',  # grade
                                course[6] if len(course) > 6 else '',  # mark
                                course[4] if len(course) > 4 else '',  # session
                                course[5] if len(course) > 5 else '',  # year
                                course[7] if len(course) > 7 else ''   # status
                            ])
                    except (TypeError, IndexError, ValueError):
                        continue

            print(f"[✓] Successfully exported {len(courses)} courses to {filename}")

        except Exception as e:
            print(f"[!] Error exporting transcript: {e}")

    def get_current_date(self):
        """Get current date in YYYY-MM-DD format"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d")

    def interactive_mode(self):
        """Run the application in interactive mode with arrow key navigation"""
        from datetime import datetime
        self.session_stats['start_time'] = datetime.now()

        self.console.print("[bold green]Welcome to Interactive Mode![/bold green]")
        self.console.print("Use [blue]arrow keys[/blue] to navigate and [yellow]Enter[/yellow] to select\n")

        while True:
            try:
                # Main menu options
                choices = [
                    "🔍 Search Courses",
                    "📖 Get Course Details",
                    "📜 View Transcript",
                    "💾 Export Transcript",
                    "📥 Import from CSV",
                    "➕ Add Course to Transcript",
                    "📊 Academic Statistics",
                    "🕒 Session Information",
                    "🔎 Search History",
                    "❓ Help",
                    "🚪 Exit"
                ]

                # Create interactive menu
                question = [
                    inquirer.List(
                        'action',
                        message="Select an action",
                        choices=choices,
                        carousel=True  # Allow wrapping around
                    )
                ]

                answer = inquirer.prompt(question)
                if not answer:  # User pressed Ctrl+C
                    break

                selected = answer['action']

                # Handle menu selection
                if "Search Courses" in selected:
                    self.interactive_search()
                elif "Get Course Details" in selected:
                    self.interactive_course_details()
                elif "View Transcript" in selected:
                    self.interactive_transcript_view()
                elif "Export Transcript" in selected:
                    self.interactive_export()
                elif "Import from CSV" in selected:
                    self.interactive_import_csv()
                elif "Add Course" in selected:
                    self.interactive_add_course()
                elif "Academic Statistics" in selected:
                    self.show_statistics()
                elif "Session Information" in selected:
                    self.show_session_info()
                elif "Search History" in selected:
                    self.show_search_history()
                elif "Help" in selected:
                    self.show_help()
                elif "Exit" in selected:
                    self.console.print("\n[bold green]Thanks for using UofT Course Dashboard![/bold green]")
                    break

            except KeyboardInterrupt:
                self.console.print("\n\n[bold yellow]Goodbye![/bold yellow]")
                break
            except Exception as e:
                self.console.print(f"\n[bold red]Error:[/bold red] {e}")
                self.console.print("Please try again.")

    def interactive_transcript_view(self):
        """Interactive transcript viewer with rich formatting and navigation"""
        try:
            courses = self.database.get_transcript_courses()

            if not courses:
                self.console.print("[yellow]No courses in transcript[/yellow]")
                return

            # Create a rich table for the transcript
            table = Table(title="Academic Transcript", show_header=True, header_style="bold magenta")
            table.add_column("Code", style="cyan", no_wrap=True)
            table.add_column("Title", style="white")
            table.add_column("Credits", justify="center", style="green")
            table.add_column("Grade", justify="center", style="yellow")
            table.add_column("Session", justify="center", style="blue")
            table.add_column("Year", justify="center", style="blue")

            # Calculate statistics
            total_credits = 0
            total_points = 0
            grade_credits = 0

            # University of Toronto Undergraduate Grade Scale
            grade_points = {
                'A+': 4.0, 'A': 4.0, 'A-': 3.7,
                'B+': 3.3, 'B': 3.0, 'B-': 2.7,
                'C+': 2.3, 'C': 2.0, 'C-': 1.7,
                'D+': 1.3, 'D': 1.0, 'D-': 0.7,
                'F': 0.0, 'FZ': 0.0,
                # Additional UofT grades
                'CR': 0.0,  # Credit (no GPA impact)
                'NCR': 0.0, # No Credit (no GPA impact)
                'P': 0.0,   # Pass (no GPA impact)
                'LWD': 0.0, # Late Withdrawal (no GPA impact)
                'WDR': 0.0, # Withdrawal (no GPA impact)
                'IPR': 0.0, # In Progress (no GPA impact)
                'INC': 0.0  # Incomplete (no GPA impact)
            }

            # Add courses to table
            for course in courses:
                try:
                    if isinstance(course, (list, tuple)) and len(course) >= 6:
                        # Database returns: (course_code, title, credits, grade, session, year, mark, status)
                        code = course[0] if len(course) > 0 else ''
                        title = course[1] if len(course) > 1 else ''
                        credits = course[2] if len(course) > 2 else 0
                        grade = course[3] if len(course) > 3 else ''
                        session = course[4] if len(course) > 4 else ''
                        year = course[5] if len(course) > 5 else ''

                        # Handle None values
                        grade = grade if grade is not None else ''

                        # Truncate title if too long
                        if len(title) > 35:
                            title = title[:32] + "..."

                        table.add_row(code, title, str(credits), grade, session, str(year))

                        # Calculate GPA - special grades don't count toward GPA
                        non_gpa_grades = {'CR', 'NCR', 'P', 'LWD', 'WDR', 'IPR', 'INC'}

                        if credits:
                            # Always count credits toward total (except NCR, LWD, WDR)
                            if grade not in {'NCR', 'LWD', 'WDR'}:
                                total_credits += float(credits)

                            # Only count toward GPA if it's a letter grade
                            if grade and grade in grade_points and grade not in non_gpa_grades:
                                total_points += grade_points[grade] * float(credits)
                                grade_credits += float(credits)

                except (TypeError, IndexError, ValueError) as e:
                    self.console.print(f"[yellow]Skipping invalid course data: {course}[/yellow]")
                    continue

            # Display the table
            self.console.print()
            self.console.print(table)

            # Display statistics
            current_gpa = total_points / grade_credits if grade_credits > 0 else 0.0

            stats_text = f"""
[bold]Statistics:[/bold]
• Total Courses: [cyan]{len(courses)}[/cyan]
• Total Credits: [green]{total_credits:.1f}[/green]
• Current GPA: [yellow]{current_gpa:.2f}[/yellow]
• Progress: [blue]{total_credits:.1f}/20.0[/blue] credits ([magenta]{(total_credits/20.0)*100:.1f}%[/magenta])
            """

            stats_panel = Panel(stats_text.strip(), title="Academic Progress", border_style="green")
            self.console.print()
            self.console.print(stats_panel)

        except Exception as e:
            self.console.print(f"[bold red]Error displaying transcript:[/bold red] {e}")

        self.pause_for_user()

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
        """Interactive course search with selectable results"""
        self.console.print("\n[bold blue]🔍 Course Search[/bold blue]")

        # Get search query
        query = Prompt.ask("Enter course code or keyword")
        if not query:
            self.console.print("[yellow]No search term entered[/yellow]")
            return

        # Get search limit
        limit_choices = ["5", "10", "15", "20"]
        limit_question = [
            inquirer.List(
                'limit',
                message="Maximum number of results",
                choices=limit_choices,
                default="10"
            )
        ]

        limit_answer = inquirer.prompt(limit_question)
        limit = int(limit_answer['limit']) if limit_answer else 10

        # Track search in history
        if query not in self.search_history:
            self.search_history.append(query)
            if len(self.search_history) > 10:
                self.search_history.pop(0)

        self.session_stats['searches_performed'] += 1

        # Perform search
        if not self.init_scraper():
            return

        try:
            with self.console.status(f"[bold green]Searching for '{query}'...", spinner="dots"):
                results = self.scraper.search_courses(query, limit)

            if not results:
                self.console.print("[yellow]No courses found[/yellow]")
                return

            # Display results in a table
            table = Table(title=f"Search Results for '{query}'", show_header=True, header_style="bold magenta")
            table.add_column("Code", style="cyan", no_wrap=True)
            table.add_column("Title", style="white")
            table.add_column("Credits", justify="center", style="green")

            course_choices = []
            for i, course in enumerate(results):
                code = course.get('course_code', 'N/A')
                title = course.get('title', 'N/A')
                credits = course.get('credits', 'N/A')

                # Truncate title for display
                display_title = title[:50] + "..." if len(title) > 50 else title
                table.add_row(code, display_title, str(credits))

                # Prepare for selection menu
                choice_text = f"{code} - {title[:60]}{'...' if len(title) > 60 else ''}"
                course_choices.append(choice_text)

            self.console.print()
            self.console.print(table)

            if not course_choices:
                return

            # Add navigation options
            course_choices.extend(["[View All Details]", "[Return to Main Menu]"])

            # Interactive selection
            course_question = [
                inquirer.List(
                    'course',
                    message="Select a course for details",
                    choices=course_choices,
                    carousel=True
                )
            ]

            course_answer = inquirer.prompt(course_question)
            if not course_answer:
                return

            selected = course_answer['course']

            if "[Return to Main Menu]" in selected:
                return
            elif "[View All Details]" in selected:
                # Show details for all courses
                for course in results:
                    self.display_course_details(course)
                    if not Confirm.ask("Continue to next course?"):
                        break
            else:
                # Extract course code and get details
                course_code = selected.split(" - ")[0]
                self.get_course_details(course_code)

        except Exception as e:
            self.console.print(f"[bold red]Search failed:[/bold red] {e}")

        self.pause_for_user()

    def display_course_details(self, course_data):
        """Display course details in a rich formatted panel"""
        if not course_data:
            self.console.print("[yellow]No course details available[/yellow]")
            return

        # Build content text
        content_lines = []
        content_lines.append(f"[bold cyan]Code:[/bold cyan] {course_data.get('course_code', 'N/A')}")
        content_lines.append(f"[bold cyan]Title:[/bold cyan] {course_data.get('title', 'N/A')}")
        content_lines.append(f"[bold cyan]Credits:[/bold cyan] {course_data.get('credits', 'N/A')}")

        if course_data.get('department'):
            content_lines.append(f"[bold cyan]Department:[/bold cyan] {course_data.get('department')}")

        if course_data.get('level'):
            content_lines.append(f"[bold cyan]Level:[/bold cyan] {course_data.get('level')}")

        if course_data.get('hours'):
            content_lines.append(f"[bold cyan]Hours:[/bold cyan] {course_data.get('hours')}")

        if course_data.get('prerequisites'):
            content_lines.append(f"[bold cyan]Prerequisites:[/bold cyan] {course_data.get('prerequisites')}")

        if course_data.get('exclusions'):
            content_lines.append(f"[bold cyan]Exclusions:[/bold cyan] {course_data.get('exclusions')}")

        if course_data.get('breadth_requirements'):
            content_lines.append(f"[bold cyan]Breadth Requirements:[/bold cyan] {course_data.get('breadth_requirements')}")

        if course_data.get('description'):
            content_lines.append(f"\n[bold cyan]Description:[/bold cyan]")
            content_lines.append(f"{course_data.get('description')}")

        content = "\n".join(content_lines)

        # Create a panel with the course details
        panel = Panel(
            content,
            title=f"Course Details: {course_data.get('course_code', 'Unknown')}",
            border_style="green",
            padding=(1, 2)
        )

        self.console.print()
        self.console.print(panel)

        # Ask if user wants to add to transcript
        if Confirm.ask("\nAdd this course to your transcript?"):
            self.add_course_to_transcript(course_data)

    def interactive_course_details(self):
        """Interactive course details lookup"""
        self.console.print("\n[bold blue]📖 Course Details[/bold blue]")

        course_code = Prompt.ask("Enter course code (e.g., POL208H1)").strip().upper()
        if not course_code:
            self.console.print("[yellow]No course code entered[/yellow]")
            return

        self.session_stats['courses_viewed'] += 1

        if not self.init_scraper():
            return

        try:
            with self.console.status(f"[bold green]Getting details for {course_code}...", spinner="dots"):
                details = self.scraper.get_course_details(course_code)

            if not details:
                self.console.print(f"[yellow]Course details not found for {course_code}[/yellow]")
                return

            self.display_course_details(details)

        except Exception as e:
            self.console.print(f"[bold red]Failed to get course details:[/bold red] {e}")

        self.pause_for_user()

    def interactive_import_csv(self):
        """Import courses from a CSV file"""
        self.console.print("\n[bold blue]📥 Import Courses from CSV[/bold blue]")

        # Get CSV file path
        csv_path = Prompt.ask("Enter path to CSV file", default="docs/my_courses.csv")

        if not os.path.exists(csv_path):
            self.console.print(f"[bold red]File not found: {csv_path}[/bold red]")
            return

        try:
            import csv
            courses_imported = 0
            courses_skipped = 0

            with open(csv_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)

                with self.console.status("[bold green]Importing courses...", spinner="dots"):
                    for row in reader:
                        try:
                            # Extract data from CSV
                            course_code = row.get('course_code', '').strip()
                            title = row.get('title', '').strip()
                            credits = float(row.get('credits', 0.5))
                            grade = row.get('grade', '').strip()
                            session = row.get('session', '').strip()
                            year = int(row.get('year', 2024))
                            status = row.get('status', 'completed').strip()

                            # Skip if course code is empty
                            if not course_code:
                                courses_skipped += 1
                                continue

                            # If title is empty, create a default one
                            if not title:
                                title = f"{course_code}: Course Title"

                            # Prepare course data for database
                            transcript_data = {
                                'course_code': course_code,
                                'title': title,
                                'credits': credits,
                                'grade': grade,
                                'semester': session,
                                'year': year,
                                'status': status
                            }

                            # Save to database
                            result = self.database.save_course(transcript_data)
                            if result:
                                courses_imported += 1
                            else:
                                courses_skipped += 1

                        except (ValueError, KeyError) as e:
                            self.console.print(f"[yellow]Skipping invalid row: {row} - Error: {e}[/yellow]")
                            courses_skipped += 1
                            continue

            # Display results
            self.console.print(f"\n[bold green]✓ Import completed![/bold green]")
            self.console.print(f"• [green]{courses_imported}[/green] courses imported")
            if courses_skipped > 0:
                self.console.print(f"• [yellow]{courses_skipped}[/yellow] courses skipped")

        except Exception as e:
            self.console.print(f"[bold red]Import failed:[/bold red] {e}")

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

            # University of Toronto Undergraduate Grade Scale
            grade_points = {
                'A+': 4.0, 'A': 4.0, 'A-': 3.7,
                'B+': 3.3, 'B': 3.0, 'B-': 2.7,
                'C+': 2.3, 'C': 2.0, 'C-': 1.7,
                'D+': 1.3, 'D': 1.0, 'D-': 0.7,
                'F': 0.0, 'FZ': 0.0,
                # Additional UofT grades
                'CR': 0.0,  # Credit (no GPA impact)
                'NCR': 0.0, # No Credit (no GPA impact)
                'P': 0.0,   # Pass (no GPA impact)
                'LWD': 0.0, # Late Withdrawal (no GPA impact)
                'WDR': 0.0, # Withdrawal (no GPA impact)
                'IPR': 0.0, # In Progress (no GPA impact)
                'INC': 0.0  # Incomplete (no GPA impact)
            }

            # Count by department and level
            departments = {}
            levels = {'100': 0, '200': 0, '300': 0, '400': 0, 'Other': 0}
            grade_distribution = {}

            for course in courses:
                try:
                    if isinstance(course, (list, tuple)) and len(course) >= 6:
                        code = course[0] if len(course) > 0 else ''
                        credits = course[2] if len(course) > 2 else 0
                        grade = course[3] if len(course) > 3 else ''

                        # Handle None values
                        grade = grade if grade is not None else ''

                        # Calculate totals - special grades don't count toward GPA
                        non_gpa_grades = {'CR', 'NCR', 'P', 'LWD', 'WDR', 'IPR', 'INC'}

                        if credits:
                            # Always count credits toward total (except NCR, LWD, WDR)
                            if grade not in {'NCR', 'LWD', 'WDR'}:
                                total_credits += float(credits)

                            # Only count toward GPA if it's a letter grade
                            if grade and grade in grade_points and grade not in non_gpa_grades:
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
                except (TypeError, IndexError, ValueError):
                    continue

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
            try:
                self.scraper.close_driver()
                self.console.print("[green]✓ Cleaned up scraper resources[/green]")
            except Exception:
                # Silently ignore cleanup errors
                pass


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