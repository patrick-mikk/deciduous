#!/usr/bin/env python3
"""
Academic Calendar Course Search Tool
Searches for course information from the UofT Academic Calendar website
"""

import requests
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
import time


class CourseDatabase:
    """Handles database operations for course information"""

    def __init__(self, db_path="courses.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize the database with courses table"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_code TEXT UNIQUE,
                title TEXT,
                hours TEXT,
                description TEXT,
                prerequisites TEXT,
                exclusions TEXT,
                breadth_requirements TEXT,
                url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def save_course(self, course_data):
        """Save course information to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO courses
            (course_code, title, hours, description, prerequisites, exclusions, breadth_requirements, url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            course_data['course_code'],
            course_data['title'],
            course_data['hours'],
            course_data['description'],
            course_data['prerequisites'],
            course_data['exclusions'],
            course_data['breadth_requirements'],
            course_data['url']
        ))
        conn.commit()
        conn.close()

    def get_all_courses(self):
        """Retrieve all courses from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM courses ORDER BY course_code')
        courses = cursor.fetchall()
        conn.close()
        return courses


class AcademicCalendarScraper:
    """Handles web scraping from UofT Academic Calendar"""

    def __init__(self):
        self.base_url = "https://artsci.calendar.utoronto.ca"
        self.search_url = f"{self.base_url}/search-courses"
        self.session = requests.Session()
        # Add headers to mimic a real browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def search_courses(self, course_code):
        """Search for courses using the provided course code"""
        try:
            # First, get the search page to retrieve any necessary form tokens
            search_page = self.session.get(self.search_url)
            search_soup = BeautifulSoup(search_page.content, 'html.parser')

            # Find the form and prepare the search data
            form_data = {
                'course_title': course_code.strip(),
                'op': 'Apply'
            }

            # Look for any hidden form fields (like CSRF tokens)
            form = search_soup.find('form')
            if form:
                hidden_inputs = form.find_all('input', type='hidden')
                for hidden in hidden_inputs:
                    if hidden.get('name') and hidden.get('value'):
                        form_data[hidden.get('name')] = hidden.get('value')

            # Submit the search
            response = self.session.post(self.search_url, data=form_data)
            soup = BeautifulSoup(response.content, 'html.parser')

            # Parse search results
            results = []
            view_content = soup.find('div', class_='view-content')

            if view_content:
                # Find all course result entries
                course_links = view_content.find_all('h3')

                for link_container in course_links:
                    link = link_container.find('a')
                    title_element = link.find('h6') if link else None

                    if link and title_element:
                        course_title = title_element.get_text(strip=True)
                        course_url = urljoin(self.base_url, link.get('href'))

                        # Extract course code from title
                        course_code_match = re.match(r'^([A-Z]{3}\d{3}[HY]\d)', course_title)
                        course_code = course_code_match.group(1) if course_code_match else course_title.split(':')[0]

                        # Get the description from the following div
                        description = ""
                        next_div = link_container.find_next_sibling('div', class_='w3-row views-row')
                        if next_div:
                            desc_div = next_div.find('div', class_='field-content')
                            if desc_div:
                                description = desc_div.get_text(strip=True)

                        results.append({
                            'course_code': course_code,
                            'title': course_title,
                            'url': course_url,
                            'description': description
                        })

            return results

        except requests.RequestException as e:
            raise Exception(f"Error searching courses: {e}")

    def extract_course_details(self, course_url):
        """Extract detailed course information from the course page"""
        try:
            response = self.session.get(course_url)
            soup = BeautifulSoup(response.content, 'html.parser')

            course_details = {}

            # Extract course title
            title_element = soup.select_one('#block-w3css-subtheme-page-title h1.page-title')
            course_details['title'] = title_element.get_text(strip=True) if title_element else ""

            # Extract hours
            hours_element = soup.select_one('.field--name-field-hours .field__item p')
            course_details['hours'] = hours_element.get_text(strip=True) if hours_element else ""

            # Extract description
            desc_element = soup.select_one('.field--name-body.field--type-text-with-summary')
            course_details['description'] = desc_element.get_text(strip=True) if desc_element else ""

            # Extract prerequisites
            prereq_element = soup.select_one('.field--name-field-prerequisite .field__item')
            course_details['prerequisites'] = prereq_element.get_text(strip=True) if prereq_element else ""

            # Extract exclusions
            exclusion_element = soup.select_one('.field--name-field-exclusion .field__item')
            course_details['exclusions'] = exclusion_element.get_text(strip=True) if exclusion_element else ""

            # Extract breadth requirements
            breadth_element = soup.select_one('.field--name-field-breadth-requirements .field__items')
            course_details['breadth_requirements'] = breadth_element.get_text(strip=True) if breadth_element else ""

            course_details['url'] = course_url

            return course_details

        except requests.RequestException as e:
            raise Exception(f"Error extracting course details: {e}")


class CourseSearchGUI:
    """Main GUI application for course search"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("UofT Academic Calendar Course Search")
        self.root.geometry("1000x700")

        self.scraper = AcademicCalendarScraper()
        self.database = CourseDatabase()
        self.search_results = []

        self.setup_gui()

    def setup_gui(self):
        """Set up the GUI components"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        # Search section
        search_frame = ttk.LabelFrame(main_frame, text="Course Search", padding="10")
        search_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        search_frame.columnconfigure(1, weight=1)

        ttk.Label(search_frame, text="Course Code:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.course_entry = ttk.Entry(search_frame, width=20)
        self.course_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        self.course_entry.bind('<Return>', lambda e: self.search_courses())

        self.search_button = ttk.Button(search_frame, text="Search", command=self.search_courses)
        self.search_button.grid(row=0, column=2, padx=(10, 0))

        # Results section
        results_frame = ttk.LabelFrame(main_frame, text="Search Results", padding="10")
        results_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)

        # Results listbox with scrollbar
        listbox_frame = ttk.Frame(results_frame)
        listbox_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        listbox_frame.columnconfigure(0, weight=1)
        listbox_frame.rowconfigure(0, weight=1)

        self.results_listbox = tk.Listbox(listbox_frame, height=8)
        self.results_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        scrollbar = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=self.results_listbox.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.results_listbox.config(yscrollcommand=scrollbar.set)

        # Select button
        ttk.Button(results_frame, text="Extract Course Details",
                  command=self.extract_selected_course).grid(row=1, column=0, pady=(10, 0))

        # Course details section
        details_frame = ttk.LabelFrame(main_frame, text="Course Details", padding="10")
        details_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        details_frame.columnconfigure(0, weight=1)
        details_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=2)

        self.details_text = scrolledtext.ScrolledText(details_frame, height=15, wrap=tk.WORD)
        self.details_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Database section
        db_frame = ttk.LabelFrame(main_frame, text="Database", padding="10")
        db_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Button(db_frame, text="View All Saved Courses",
                  command=self.view_saved_courses).grid(row=0, column=0, padx=(0, 10))

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))

    def search_courses(self):
        """Handle course search"""
        course_code = self.course_entry.get().strip()
        if not course_code:
            messagebox.showwarning("Warning", "Please enter a course code")
            return

        self.status_var.set("Searching...")
        self.root.update()

        try:
            self.search_results = self.scraper.search_courses(course_code)

            # Clear and populate results listbox
            self.results_listbox.delete(0, tk.END)
            for result in self.search_results:
                self.results_listbox.insert(tk.END, result['title'])

            if self.search_results:
                self.status_var.set(f"Found {len(self.search_results)} results")
            else:
                self.status_var.set("No results found")
                messagebox.showinfo("No Results", "No courses found for the given search term")

        except Exception as e:
            self.status_var.set("Error occurred")
            messagebox.showerror("Error", f"Search failed: {e}")

    def extract_selected_course(self):
        """Extract details for the selected course"""
        selection = self.results_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a course from the results")
            return

        selected_result = self.search_results[selection[0]]

        self.status_var.set("Extracting course details...")
        self.root.update()

        try:
            course_details = self.scraper.extract_course_details(selected_result['url'])

            # Extract course code from title
            course_code_match = re.match(r'^([A-Z]{3}\d{3}[HY]\d)', course_details['title'])
            course_code = course_code_match.group(1) if course_code_match else course_details['title'].split(':')[0]

            course_details['course_code'] = course_code

            # Display course details
            self.display_course_details(course_details)

            # Save to database
            self.database.save_course(course_details)

            self.status_var.set("Course details extracted and saved")

        except Exception as e:
            self.status_var.set("Error occurred")
            messagebox.showerror("Error", f"Failed to extract course details: {e}")

    def display_course_details(self, course_details):
        """Display course details in the text widget"""
        self.details_text.delete(1.0, tk.END)

        details_text = f"""
COURSE TITLE: {course_details.get('title', 'N/A')}

COURSE CODE: {course_details.get('course_code', 'N/A')}

HOURS: {course_details.get('hours', 'N/A')}

DESCRIPTION:
{course_details.get('description', 'N/A')}

PREREQUISITES:
{course_details.get('prerequisites', 'N/A')}

EXCLUSIONS:
{course_details.get('exclusions', 'N/A')}

BREADTH REQUIREMENTS:
{course_details.get('breadth_requirements', 'N/A')}

URL: {course_details.get('url', 'N/A')}
        """.strip()

        self.details_text.insert(1.0, details_text)

    def view_saved_courses(self):
        """Open a window to view all saved courses"""
        courses_window = tk.Toplevel(self.root)
        courses_window.title("Saved Courses")
        courses_window.geometry("800x600")

        # Create treeview for courses
        frame = ttk.Frame(courses_window, padding="10")
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        courses_window.columnconfigure(0, weight=1)
        courses_window.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        columns = ('Course Code', 'Title', 'Hours', 'Created')
        tree = ttk.Treeview(frame, columns=columns, show='headings', height=20)

        # Define column headings
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=150)

        # Add scrollbar
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)

        tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # Populate tree with saved courses
        courses = self.database.get_all_courses()
        for course in courses:
            tree.insert('', tk.END, values=(course[1], course[2], course[3], course[9]))

        # Add close button
        ttk.Button(frame, text="Close", command=courses_window.destroy).grid(row=1, column=0, pady=(10, 0))

    def run(self):
        """Start the GUI application"""
        self.root.mainloop()


def main():
    """Main function to start the application"""
    app = CourseSearchGUI()
    app.run()


if __name__ == "__main__":
    main()