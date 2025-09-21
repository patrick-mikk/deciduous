#!/usr/bin/env python3
"""
Academic Calendar Course Search Tool
Searches for course information from the UofT Academic Calendar website
"""

import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# Simple theme - using default system colors


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
        self.driver = None
        self.setup_driver()

    def setup_driver(self):
        """Setup Chrome WebDriver with appropriate options"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in background
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.implicitly_wait(10)
        except Exception as e:
            raise Exception(f"Failed to setup Chrome driver: {e}")

    def close_driver(self):
        """Close the WebDriver"""
        if self.driver:
            self.driver.quit()
            self.driver = None

    def __del__(self):
        """Cleanup driver when object is destroyed"""
        self.close_driver()

    def search_courses(self, course_code):
        """Search for courses using the provided course code"""
        try:
            if not self.driver:
                self.setup_driver()

            # Navigate to the search page
            self.driver.get(self.search_url)

            # Wait for the page to load
            wait = WebDriverWait(self.driver, 10)

            # Find and fill the search form
            # Try different form fields that might exist
            search_input = None
            submit_button = None

            try:
                # First try course_keyword field (seems to be for general search)
                search_input = wait.until(
                    EC.presence_of_element_located((By.NAME, "course_keyword"))
                )
                search_input.clear()
                search_input.send_keys(course_code.strip())

                # Find and click the submit button for this form
                submit_button = self.driver.find_element(By.CSS_SELECTOR, "input[data-drupal-selector='edit-submit-course-search']")
                submit_button.click()

            except (TimeoutException, NoSuchElementException):
                try:
                    # Alternative: try course_title field
                    search_input = self.driver.find_element(By.NAME, "course_title")
                    search_input.clear()
                    search_input.send_keys(course_code.strip())

                    # Find the corresponding submit button
                    submit_button = self.driver.find_element(By.CSS_SELECTOR, "input[value='Apply']")
                    submit_button.click()

                except NoSuchElementException:
                    # Last resort: try any text input and submit button
                    try:
                        search_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='text']")
                        search_input.clear()
                        search_input.send_keys(course_code.strip())

                        submit_button = self.driver.find_element(By.CSS_SELECTOR, "input[type='submit']")
                        submit_button.click()
                    except NoSuchElementException:
                        raise Exception("Could not find search form elements")

            # Wait for results to load
            time.sleep(3)  # Give some time for the page to update

            # Parse the results using BeautifulSoup
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')

            # Parse search results
            results = []

            # Look for course results in accordion format
            accordion_headers = soup.find_all('h3', class_='js-views-accordion-group-header')

            for header in accordion_headers:
                # Get the course title from the div inside the h3
                title_div = header.find('div')
                if title_div:
                    course_title = title_div.get_text(strip=True)

                    # Extract course code from the title
                    course_code_match = re.match(r'^([A-Z]{3}\d{3}[HY]\d)', course_title)
                    if course_code_match:
                        course_code = course_code_match.group(1)
                        course_url = f"{self.base_url}/course/{course_code}"

                        # Get the description from the corresponding accordion content
                        description = ""
                        next_div = header.find_next_sibling('div', class_='ui-accordion-content')
                        if next_div:
                            desc_div = next_div.find('div', class_='field-content')
                            if desc_div:
                                description = desc_div.get_text(strip=True)

                        results.append({
                            'course_code': course_code,
                            'title': course_title,
                            'url': course_url,
                            'description': description[:200] + "..." if len(description) > 200 else description
                        })

            # Fallback: Look for course results in other formats
            if not results:
                course_rows = soup.find_all('div', class_='w3-row views-row')

                for row in course_rows:
                    # Look for course title with link
                    course_link = row.find('a')
                    if course_link and '/course/' in course_link.get('href', ''):
                        # Extract course title and URL
                        course_title = course_link.get_text(strip=True)
                        course_url = urljoin(self.base_url, course_link.get('href'))

                        # Extract course code from the title or URL
                        course_code_match = re.match(r'^([A-Z]{3}\d{3}[HY]\d)', course_title)
                        if course_code_match:
                            course_code = course_code_match.group(1)
                        else:
                            # Try extracting from URL
                            url_match = re.search(r'/course/([A-Z]{3}\d{3}[HY]\d)', course_url)
                            course_code = url_match.group(1) if url_match else course_title.split(':')[0]

                        # Get description from the field-content div
                        description = ""
                        desc_div = row.find('div', class_='field-content')
                        if desc_div:
                            # Get the text content, removing HTML tags
                            description = desc_div.get_text(strip=True)

                        results.append({
                            'course_code': course_code,
                            'title': course_title,
                            'url': course_url,
                            'description': description[:200] + "..." if len(description) > 200 else description
                        })

            # Another fallback: Look for the old format as well
            if not results:
                view_content = soup.find('div', class_='view-content')
                if view_content:
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

        except Exception as e:
            raise Exception(f"Error searching courses: {e}")

    def extract_course_details(self, course_url):
        """Extract detailed course information from the course page"""
        try:
            if not self.driver:
                self.setup_driver()

            # Navigate to the course details page
            self.driver.get(course_url)

            # Wait for the page to load
            wait = WebDriverWait(self.driver, 10)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

            # Parse the page with BeautifulSoup
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')

            course_details = {}

            # Extract course title
            title_element = soup.select_one('#block-w3css-subtheme-page-title h1.page-title')
            course_details['title'] = title_element.get_text(strip=True) if title_element else ""

            # Extract hours
            hours_element = soup.select_one('.field--name-field-hours .field__item p')
            course_details['hours'] = hours_element.get_text(strip=True) if hours_element else ""

            # Extract description - target the entire div container to get all paragraphs and links
            desc_element = soup.select_one('#block-w3css-subtheme-content > article > div > div.w3-row.field.field--name-body.field--type-text-with-summary.field--label-hidden.w3-bar-item.field__item')
            if not desc_element:
                # Fallback to previous selector
                desc_element = soup.select_one('.field--name-body.field--type-text-with-summary')

            if desc_element:
                # Get all text content including from multiple paragraphs and links
                # Look specifically for paragraph elements first
                paragraphs = desc_element.find_all('p')
                if paragraphs and len(paragraphs) > 0:
                    # Join paragraphs with double newline for better readability
                    # Also preserve any links within paragraphs
                    paragraph_texts = []
                    for p in paragraphs:
                        text = p.get_text(strip=True)
                        if text:  # Only add non-empty paragraphs
                            paragraph_texts.append(text)

                    if paragraph_texts:
                        course_details['description'] = '\n\n'.join(paragraph_texts)
                    else:
                        # Fallback to getting all text if paragraphs are empty
                        course_details['description'] = desc_element.get_text(strip=True)
                else:
                    # No paragraph tags found, get all text content
                    course_details['description'] = desc_element.get_text(strip=True)
            else:
                course_details['description'] = ""

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

        except Exception as e:
            raise Exception(f"Error extracting course details: {e}")


class CourseSearchGUI:
    """Main GUI application for course search"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("UofT Course Search")
        self.root.geometry("800x700")

        self.scraper = AcademicCalendarScraper()
        self.database = CourseDatabase()
        self.search_results = []

        self.setup_menu()
        self.setup_gui()

    def setup_menu(self):
        """Setup the application menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Export Search Results...", command=self.export_results)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="All Saved Courses", command=self.view_saved_courses)
        view_menu.add_command(label="Course Statistics", command=self.view_course_statistics)
        view_menu.add_separator()
        view_menu.add_command(label="Refresh Results", command=self.refresh_results)

        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Bulk Search...", command=self.bulk_search)
        tools_menu.add_command(label="Clear Database", command=self.clear_database)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)


    def setup_gui(self):
        """Set up the GUI with simple vertical layout"""
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
        self.course_entry = ttk.Entry(search_frame, width=30)
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

        # Extract button
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

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))

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


    def export_results(self):
        """Export current search results to CSV"""
        if not self.search_results:
            messagebox.showwarning("Warning", "No search results to export")
            return

        from tkinter import filedialog
        import csv

        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )

        if filename:
            try:
                with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(['Course Code', 'Title', 'Description', 'URL'])

                    for result in self.search_results:
                        writer.writerow([
                            result['course_code'],
                            result['title'],
                            result['description'],
                            result['url']
                        ])

                messagebox.showinfo("Success", f"Results exported to {filename}")
                self.status_var.set(f"Exported {len(self.search_results)} results to {filename}")

            except Exception as e:
                messagebox.showerror("Error", f"Failed to export results: {e}")

    def view_course_statistics(self):
        """Show course statistics window"""
        stats_window = tk.Toplevel(self.root)
        stats_window.title("Course Statistics")
        stats_window.geometry("600x400")

        main_frame = ttk.Frame(stats_window, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        stats_window.columnconfigure(0, weight=1)
        stats_window.rowconfigure(0, weight=1)

        # Header
        ttk.Label(main_frame, text="Course Database Statistics").grid(row=0, column=0, sticky=tk.W, pady=(0, 20))

        # Get statistics
        courses = self.database.get_all_courses()
        total_courses = len(courses)

        # Analyze by subject
        subjects = {}
        for course in courses:
            subject = course[1][:3] if course[1] else "Unknown"  # First 3 chars of course code
            subjects[subject] = subjects.get(subject, 0) + 1

        # Display stats
        stats_text = scrolledtext.ScrolledText(main_frame, height=15, width=60)
        stats_text.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        stats_content = f"""DATABASE STATISTICS
═══════════════════

Total Courses: {total_courses}

COURSES BY SUBJECT:
"""
        for subject, count in sorted(subjects.items()):
            stats_content += f"{subject}: {count} courses\n"

        stats_text.insert(1.0, stats_content)
        stats_text.config(state=tk.DISABLED)

        # Close button
        ttk.Button(main_frame, text="Close", command=stats_window.destroy).grid(row=2, column=0, pady=(20, 0))

    def bulk_search(self):
        """Open bulk search dialog"""
        bulk_window = tk.Toplevel(self.root)
        bulk_window.title("Bulk Course Search")
        bulk_window.geometry("500x400")

        main_frame = ttk.Frame(bulk_window, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        bulk_window.columnconfigure(0, weight=1)
        bulk_window.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)

        # Header
        ttk.Label(main_frame, text="Bulk Course Search").grid(row=0, column=0, sticky=tk.W, pady=(0, 15))

        # Instructions
        ttk.Label(main_frame, text="Enter course codes (one per line):").grid(row=1, column=0, sticky=tk.W, pady=(0, 5))

        # Text area for course codes
        codes_text = scrolledtext.ScrolledText(main_frame,
                                             height=10,
                                             width=40)
        codes_text.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 15))
        codes_text.insert(1.0, "CSC108\nCSC148\nMAT137\nCSC165\nCSC207")

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, sticky=(tk.W, tk.E))

        def run_bulk_search():
            course_codes = codes_text.get(1.0, tk.END).strip().split('\n')
            course_codes = [code.strip() for code in course_codes if code.strip()]

            if not course_codes:
                messagebox.showwarning("Warning", "Please enter at least one course code")
                return

            # Close dialog and run searches
            bulk_window.destroy()

            progress_window = tk.Toplevel(self.root)
            progress_window.title("Bulk Search Progress")
            progress_window.geometry("400x200")

            progress_frame = ttk.Frame(progress_window, padding="20")
            progress_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

            ttk.Label(progress_frame, text="Bulk Search in Progress...").grid(row=0, column=0, pady=(0, 20))

            progress_label = ttk.Label(progress_frame, text="Starting...")
            progress_label.grid(row=1, column=0, pady=(0, 20))

            # Simulate bulk search (you can implement actual logic here)
            total_found = 0
            for i, code in enumerate(course_codes):
                progress_label.config(text=f"Searching {code}... ({i+1}/{len(course_codes)})")
                progress_window.update()

                try:
                    results = self.scraper.search_courses(code)
                    total_found += len(results)
                    # Optionally extract details for each result
                except:
                    pass  # Continue with next course

            progress_window.destroy()
            messagebox.showinfo("Bulk Search Complete",
                              f"Searched {len(course_codes)} course codes\nFound {total_found} total results")

        ttk.Button(button_frame, text="Start Bulk Search",
                  command=run_bulk_search).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Cancel",
                  command=bulk_window.destroy).pack(side=tk.LEFT)

    def clear_database(self):
        """Clear the course database"""
        result = messagebox.askyesno("Confirm Clear Database",
                                   "Are you sure you want to clear all saved courses?\nThis action cannot be undone.")
        if result:
            try:
                import os
                os.remove(self.database.db_path)
                self.database.init_database()
                self.update_stats()
                messagebox.showinfo("Success", "Database cleared successfully")
                self.status_var.set("Database cleared")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to clear database: {e}")

    def refresh_results(self):
        """Refresh the current search results"""
        if hasattr(self, 'search_results') and self.search_results:
            course_code = self.course_entry.get().strip()
            if course_code:
                self.search_courses()
            else:
                messagebox.showinfo("Info", "No previous search to refresh")

    def show_about(self):
        """Show about dialog"""
        about_window = tk.Toplevel(self.root)
        about_window.title("About UofT Course Search")
        about_window.geometry("500x400")

        main_frame = ttk.Frame(about_window, padding="30")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        about_window.columnconfigure(0, weight=1)
        about_window.rowconfigure(0, weight=1)

        # Header
        ttk.Label(main_frame, text="UofT Course Search Tool").grid(row=0, column=0, pady=(0, 20))

        # About text
        about_text = """A course search and management tool for the University of Toronto Academic Calendar.

Features:
• Search courses by code or keyword
• Extract detailed course information
• Save courses to local database
• Export search results
• Bulk search functionality

Built with Python, Tkinter, Selenium, and SQLite.

Version 2.0 - Simple Edition
"""

        text_widget = scrolledtext.ScrolledText(main_frame,
                                              height=12,
                                              width=50,
                                              wrap=tk.WORD)
        text_widget.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        text_widget.insert(1.0, about_text)
        text_widget.config(state=tk.DISABLED)

        # Close button
        ttk.Button(main_frame, text="Close",
                  command=about_window.destroy).grid(row=2, column=0, pady=(20, 0))

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
        try:
            self.root.mainloop()
        finally:
            # Cleanup the scraper's driver when the GUI is closed
            if hasattr(self.scraper, 'close_driver'):
                self.scraper.close_driver()


def main():
    """Main function to start the application"""
    app = CourseSearchGUI()
    app.run()


if __name__ == "__main__":
    main()