# University of Toronto Academic Calendar - Selenium & Python Implementation Guide

## Overview

This document provides comprehensive information about the University of Toronto Faculty of Arts & Science Academic Calendar system for building a Python transcript tracking and course planning application using **Selenium WebDriver** for web automation and data extraction.

## Table of Contents

1. [Setup & Dependencies](#setup--dependencies)
2. [Degree Requirements](#degree-requirements)
3. [Program Structure](#program-structure)
4. [Search Functionality](#search-functionality)
5. [Selenium Locators & Strategies](#selenium-locators--strategies)
6. [Python Implementation Examples](#python-implementation-examples)
7. [Data Structures](#data-structures)
8. [Selenium Best Practices](#selenium-best-practices)
9. [Error Handling & Debugging](#error-handling--debugging)
10. [Database Integration](#database-integration)

---

## Setup & Dependencies

### Required Python Packages

```bash
# Core dependencies
pip install selenium
pip install beautifulsoup4
pip install requests
pip install pandas
pip install sqlalchemy
pip install python-dotenv

# Optional for enhanced functionality
pip install lxml
pip install webdriver-manager  # Automatic driver management
pip install fake-useragent     # User agent rotation
pip install pytest            # For testing
```

### WebDriver Setup

```python
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from webdriver_manager.chrome import ChromeDriverManager
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UofTCalendarScraper:
    def __init__(self, headless=True):
        self.setup_driver(headless)
        self.base_url = "https://artsci.calendar.utoronto.ca"
        
    def setup_driver(self, headless=True):
        """Initialize Chrome WebDriver with optimized settings."""
        chrome_options = Options()
        
        if headless:
            chrome_options.add_argument("--headless")
        
        # Performance optimizations
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-images")
        chrome_options.add_argument("--disable-javascript")  # Remove if JS needed
        
        # Set user agent
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        # Use webdriver-manager for automatic driver management
        service = Service(ChromeDriverManager().install())
        
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.implicitly_wait(10)
        self.wait = WebDriverWait(self.driver, 20)
        
    def __del__(self):
        """Clean up driver on object destruction."""
        if hasattr(self, 'driver'):
            self.driver.quit()
```

### Environment Configuration

Create a `.env` file:
```env
# UofT Calendar Configuration
UOFT_BASE_URL=https://artsci.calendar.utoronto.ca
SCRAPING_DELAY=1.0
MAX_RETRIES=3
HEADLESS_MODE=True

# Database Configuration
DATABASE_URL=sqlite:///uoft_calendar.db
LOG_LEVEL=INFO

# Optional: If using a proxy or special configuration
USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36
```

---

## Degree Requirements

### Core Graduation Requirements (HBA/HBSc)

Students must complete **20.0 credits** total with the following specifications:

- **10.0 credits minimum** from Faculty of Arts & Science courses
- **13.0 credits minimum** at 200+ level (including 6.0 credits at 300+ level)
- **No more than 15.0 credits** with the same three-letter designator (e.g., "CSC", "MAT")
- **Cumulative GPA of 1.85 or higher** by graduation

### Breadth Requirements

Students must complete **4.0 FCEs (Full Course Equivalents)** in breadth categories, either:
- **Option 1**: 1.0 credit in each of 4 of the 5 categories
- **Option 2**: 1.0 credit in each of 3 categories + 0.5 credit in each of the other 2

#### The 5 Breadth Categories:
1. **Creative and Cultural Representations** - Arts, literature, languages, cultural studies
2. **Thought, Belief and Behaviour** - Philosophy, psychology, religion
3. **Society and its Institutions** - Politics, economics, sociology, law
4. **Living Things and their Environment** - Biology, environmental science
5. **The Physical and Mathematical Universes** - Physics, chemistry, mathematics, computer science

### Program Requirements

Students must enroll in **1-3 programs** (maximum 2 Majors/Specialists):

- **Specialist Program**: 10.0-14.0 credits (some up to 16.0), 4.0+ credits at 300+ level (1.0 at 400 level)
- **Major Program**: 6.0-8.0 credits, 2.0+ credits at 300+ level (0.5 at 400 level)  
- **Minor Program**: 4.0 credits, 1.0+ credit at 300+ level

---

## Program Structure

### Program Code Format

All programs follow a standardized coding system:

```
AS + TYPE + #### 
```

**Examples:**
- `ASSPE0608` - Actuarial Science Specialist
- `ASMAJ1689` - Computer Science Major
- `ASMIN1013` - Sociology Minor
- `ASFOC####` - Focus programs
- `ASCER####` - Certificate programs

### Code Components:
- **AS**: Arts & Science identifier
- **SPE/MAJ/MIN/FOC/CER**: Program type
- **4 digits**: Subject area identifier

### Program Types:

| Type | Code | Credits | Description |
|------|------|---------|-------------|
| Specialist | ASSPE | 10.0-14.0 | Deepest study in subject area |
| Major | ASMAJ | 6.0-8.0 | Comprehensive study |
| Minor | ASMIN | 4.0 | Fundamental study |
| Focus | ASFOC | Variable | Specialized cluster within Specialist/Major |
| Certificate | ASCER | 2.0-3.0 | Complementary themed courses |

### Degree Type Determination:

Programs determine if students receive **HBA (Honours Bachelor of Arts)** or **HBSc (Honours Bachelor of Science)**:

- **One Specialist**: Degree type depends on program area
- **Two Majors**: Choice if one Arts + one Science area
- **Major + Two Minors**: Majority area determines degree
- **12.0 different credits rule** applies to multiple program combinations

---

## Search Functionality

### Search Methods Available:

1. **Program and Certificate Search**
   - By keyword
   - By program type (Specialist, Major, Minor, Focus, Certificate)
   - By subject area
   - By program code

2. **Course Search**
   - By keyword (code, title, description)
   - By program area
   - By prerequisites
   - By breadth requirements

3. **Program Areas A-Z**
   - Alphabetical listing of all subject areas
   - Direct navigation to program sections

### Key URLs:
- Main Calendar: `https://artsci.calendar.utoronto.ca/`
- Program Search: `https://artsci.calendar.utoronto.ca/search-programs`
- Course Search: `https://artsci.calendar.utoronto.ca/search-courses`
- Program Areas: `https://artsci.calendar.utoronto.ca/listing-program-subject-areas`

---

## Selenium Locators & Strategies

### Page Navigation Locators

```python
class UofTLocators:
    """Centralized locator definitions for UofT Academic Calendar."""
    
    # Main navigation elements
    PROGRAM_SEARCH_LINK = (By.XPATH, "//a[@href='/search-programs']")
    COURSE_SEARCH_LINK = (By.XPATH, "//a[@href='/search-courses']")
    PROGRAM_AREAS_LINK = (By.XPATH, "//a[@href='/listing-program-subject-areas']")
    DEGREE_REQUIREMENTS_LINK = (By.XPATH, "//a[@href='/degree-requirements-hba-hbsc-bcom']")
    
    # Search interface elements
    PROGRAM_SEARCH_FORM = (By.ID, "program-search-form")
    COURSE_SEARCH_FORM = (By.ID, "course-search-form")
    
    # Search input fields
    PROGRAM_KEYWORD_INPUT = (By.NAME, "program-keyword")
    PROGRAM_TYPE_SELECT = (By.NAME, "program-type")
    SUBJECT_AREA_SELECT = (By.NAME, "subject-area")
    PROGRAM_CODE_INPUT = (By.NAME, "program-code")
    
    COURSE_KEYWORD_INPUT = (By.NAME, "course-keyword")
    COURSE_CODE_INPUT = (By.NAME, "course-code")
    PREREQUISITE_FILTER = (By.NAME, "prerequisites")
    BREADTH_REQUIREMENT_FILTER = (By.NAME, "breadth-requirement")
    
    # Search results
    SEARCH_RESULTS_CONTAINER = (By.CLASS_NAME, "search-results")
    PROGRAM_RESULTS_LIST = (By.CLASS_NAME, "program-results-list")
    COURSE_RESULTS_LIST = (By.CLASS_NAME, "course-results-list")
    
    # Result items
    PROGRAM_RESULT_ITEMS = (By.CLASS_NAME, "program-result-item")
    COURSE_RESULT_ITEMS = (By.CLASS_NAME, "course-result-item")
    
    # Program/course links
    PROGRAM_LINKS = (By.XPATH, "//a[contains(@href, '/program/')]")
    COURSE_LINKS = (By.XPATH, "//a[contains(@href, '/course/')]")
    
    # Subject area navigation
    SUBJECT_AREA_LINKS = (By.XPATH, "//a[contains(@href, '/section/')]")
    ALPHABETICAL_LINKS = (By.XPATH, "//a[@data-letter]")
```

### Dynamic Content Handling

```python
def wait_for_search_results(self, timeout=10):
    """Wait for search results to load."""
    try:
        self.wait.until(
            EC.presence_of_element_located(UofTLocators.SEARCH_RESULTS_CONTAINER)
        )
        # Additional wait for content to stabilize
        time.sleep(1)
        return True
    except Exception as e:
        logger.error(f"Search results failed to load: {e}")
        return False

def wait_for_page_load(self, timeout=10):
    """Wait for page to fully load."""
    try:
        self.wait.until(
            lambda driver: driver.execute_script("return document.readyState") == "complete"
        )
        return True
    except Exception as e:
        logger.error(f"Page load timeout: {e}")
        return False
```

### Program Data Extraction Locators

```python
class ProgramPageLocators:
    """Locators for program detail pages."""
    
    # Program header information
    PROGRAM_TITLE = (By.TAG_NAME, "h1")
    PROGRAM_CODE = (By.CLASS_NAME, "program-code")
    PROGRAM_TYPE = (By.CLASS_NAME, "program-type")
    DEGREE_TYPE = (By.CLASS_NAME, "degree-type")
    
    # Program details sections
    PROGRAM_DESCRIPTION = (By.CLASS_NAME, "program-description")
    ENROLMENT_REQUIREMENTS = (By.CLASS_NAME, "enrolment-requirements")
    COMPLETION_REQUIREMENTS = (By.CLASS_NAME, "completion-requirements")
    PROGRAM_NOTES = (By.CLASS_NAME, "program-notes")
    
    # Course requirements
    REQUIRED_COURSES_LIST = (By.CLASS_NAME, "required-courses-list")
    COURSE_LINKS_IN_PROGRAM = (By.XPATH, "//a[contains(@href, '/course/')]")
    
    # Year-based requirements
    FIRST_YEAR_REQUIREMENTS = (By.XPATH, "//h3[contains(text(), 'First Year')]/following-sibling::*")
    UPPER_YEAR_REQUIREMENTS = (By.XPATH, "//h3[contains(text(), 'Upper Years')]/following-sibling::*")
    
    # Credit information
    CREDIT_REQUIREMENTS = (By.XPATH, "//text()[contains(., 'credits')]")
    LEVEL_REQUIREMENTS = (By.XPATH, "//text()[contains(., '300+') or contains(., '400+')]")
```

### Course Data Extraction Locators

```python
class CoursePageLocators:
    """Locators for course detail pages."""
    
    # Course header
    COURSE_TITLE = (By.TAG_NAME, "h1")
    COURSE_CODE = (By.CLASS_NAME, "course-code")
    COURSE_DESCRIPTION = (By.CLASS_NAME, "course-description")
    
    # Course metadata
    COURSE_HOURS = (By.CLASS_NAME, "course-hours")
    COURSE_EXPERIENCE = (By.CLASS_NAME, "course-experience")
    BREADTH_REQUIREMENT = (By.CLASS_NAME, "breadth-requirement")
    
    # Requirements
    PREREQUISITES = (By.XPATH, "//strong[contains(text(), 'Prerequisite')]/following-sibling::text()")
    COREQUISITES = (By.XPATH, "//strong[contains(text(), 'Corequisite')]/following-sibling::text()")
    EXCLUSIONS = (By.XPATH, "//strong[contains(text(), 'Exclusion')]/following-sibling::text()")
    RECOMMENDED_PREP = (By.XPATH, "//strong[contains(text(), 'Recommended')]/following-sibling::text()")
    
    # Additional information
    PREVIOUS_COURSE_NUMBER = (By.CLASS_NAME, "previous-course-number")
    CR_NCR_ELIGIBILITY = (By.XPATH, "//text()[contains(., 'CR/NCR')]")
```

### Navigation and Search Strategies

```python
def navigate_to_program_search(self):
    """Navigate to the program search page."""
    try:
        self.driver.get(f"{self.base_url}/search-programs")
        self.wait_for_page_load()
        logger.info("Navigated to program search page")
        return True
    except Exception as e:
        logger.error(f"Failed to navigate to program search: {e}")
        return False

def navigate_to_course_search(self):
    """Navigate to the course search page."""
    try:
        self.driver.get(f"{self.base_url}/search-courses")
        self.wait_for_page_load()
        logger.info("Navigated to course search page")
        return True
    except Exception as e:
        logger.error(f"Failed to navigate to course search: {e}")
        return False

def perform_program_search(self, keyword="", program_type="", subject_area=""):
    """Perform a program search with given parameters."""
    try:
        # Navigate to search page
        if not self.navigate_to_program_search():
            return []
            
        # Fill search form
        if keyword:
            keyword_input = self.driver.find_element(*UofTLocators.PROGRAM_KEYWORD_INPUT)
            keyword_input.clear()
            keyword_input.send_keys(keyword)
            
        if program_type:
            type_select = Select(self.driver.find_element(*UofTLocators.PROGRAM_TYPE_SELECT))
            type_select.select_by_visible_text(program_type)
            
        if subject_area:
            area_select = Select(self.driver.find_element(*UofTLocators.SUBJECT_AREA_SELECT))
            area_select.select_by_visible_text(subject_area)
        
        # Submit search
        search_button = self.driver.find_element(By.XPATH, "//input[@type='submit' or @type='button']")
        search_button.click()
        
        # Wait for results
        if self.wait_for_search_results():
            return self.extract_program_search_results()
        else:
            return []
            
    except Exception as e:
        logger.error(f"Program search failed: {e}")
        return []
```

---

## Python Implementation Examples

### Complete Program Data Extraction

```python
import re
from bs4 import BeautifulSoup

def extract_all_programs(self):
    """Extract all programs from the UofT Academic Calendar."""
    programs = []
    
    try:
        # Navigate to program areas listing
        self.driver.get(f"{self.base_url}/listing-program-subject-areas")
        self.wait_for_page_load()
        
        # Get all subject area links
        subject_links = self.driver.find_elements(*UofTLocators.SUBJECT_AREA_LINKS)
        subject_urls = [link.get_attribute('href') for link in subject_links]
        
        logger.info(f"Found {len(subject_urls)} subject areas to process")
        
        for url in subject_urls:
            try:
                self.driver.get(url)
                self.wait_for_page_load()
                time.sleep(1.0)  # Respectful delay
                
                # Extract programs from this subject area
                area_programs = self.extract_programs_from_subject_page()
                programs.extend(area_programs)
                
                logger.info(f"Extracted {len(area_programs)} programs from {url}")
                
            except Exception as e:
                logger.error(f"Failed to process subject area {url}: {e}")
                continue
                
        return programs
        
    except Exception as e:
        logger.error(f"Failed to extract programs: {e}")
        return []

def extract_programs_from_subject_page(self):
    """Extract program information from a subject area page."""
    programs = []
    
    try:
        # Get page source and parse with BeautifulSoup for easier text processing
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        # Find program sections
        program_sections = soup.find_all(['h2', 'h3'], string=lambda text: 
            text and any(keyword in text.lower() for keyword in 
                        ['specialist', 'major', 'minor', 'certificate']))
        
        for section in program_sections:
            try:
                program = self.parse_program_section(section)
                if program:
                    programs.append(program)
            except Exception as e:
                logger.error(f"Failed to parse program section: {e}")
                continue
                
        return programs
        
    except Exception as e:
        logger.error(f"Failed to extract programs from subject page: {e}")
        return []

def parse_program_section(self, section_element):
    """Parse individual program information from HTML section."""
    try:
        program_data = {
            'title': '',
            'code': '',
            'type': '',
            'degree_type': '',
            'credits_required': 0.0,
            'description': '',
            'enrolment_requirements': [],
            'completion_requirements': [],
            'required_courses': []
        }
        
        # Extract title and type
        title_text = section_element.get_text(strip=True)
        program_data['title'] = title_text
        
        # Determine program type
        if 'specialist' in title_text.lower():
            program_data['type'] = 'Specialist'
        elif 'major' in title_text.lower():
            program_data['type'] = 'Major'
        elif 'minor' in title_text.lower():
            program_data['type'] = 'Minor'
        elif 'certificate' in title_text.lower():
            program_data['type'] = 'Certificate'
            
        # Look for program code in the section
        code_match = re.search(r'(AS[A-Z]{3}\d{4})', section_element.get_text())
        if code_match:
            program_data['code'] = code_match.group(1)
            
        # Extract subsequent content for requirements
        next_sibling = section_element.find_next_sibling()
        content_text = ""
        
        while next_sibling and next_sibling.name not in ['h1', 'h2', 'h3']:
            content_text += next_sibling.get_text() + "\n"
            next_sibling = next_sibling.find_next_sibling()
            
        # Parse requirements from content
        program_data['description'] = self.extract_description(content_text)
        program_data['enrolment_requirements'] = self.extract_enrolment_requirements(content_text)
        program_data['completion_requirements'] = self.extract_completion_requirements(content_text)
        program_data['required_courses'] = self.extract_course_codes(content_text)
        
        return program_data
        
    except Exception as e:
        logger.error(f"Failed to parse program section: {e}")
        return None
```

### Course Data Extraction

```python
def extract_course_details(self, course_code):
    """Extract detailed information for a specific course."""
    try:
        # Navigate to course page
        course_url = f"{self.base_url}/course/{course_code.lower()}"
        self.driver.get(course_url)
        self.wait_for_page_load()
        
        # Parse page with BeautifulSoup
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        course_data = {
            'code': course_code,
            'title': '',
            'description': '',
            'credits': 0.5,
            'level': 0,
            'prerequisites': [],
            'corequisites': [],
            'exclusions': [],
            'breadth_categories': [],
            'department': '',
            'hours': '',
            'session_offered': []
        }
        
        # Extract title
        title_element = soup.find('h1')
        if title_element:
            course_data['title'] = title_element.get_text(strip=True)
            
        # Extract description
        desc_element = soup.find('div', class_='course-description')
        if desc_element:
            course_data['description'] = desc_element.get_text(strip=True)
            
        # Extract credits (from course code - H1 = 0.5, Y1 = 1.0)
        if 'H1' in course_code:
            course_data['credits'] = 0.5
        elif 'Y1' in course_code:
            course_data['credits'] = 1.0
            
        # Extract level (first digit of course number)
        level_match = re.search(r'\d{3}', course_code)
        if level_match:
            course_data['level'] = int(level_match.group()[0]) * 100
            
        # Extract prerequisites
        prereq_text = self.find_requirement_text(soup, 'prerequisite')
        if prereq_text:
            course_data['prerequisites'] = self.parse_course_requirements(prereq_text)
            
        # Extract corequisites
        coreq_text = self.find_requirement_text(soup, 'corequisite')
        if coreq_text:
            course_data['corequisites'] = self.parse_course_requirements(coreq_text)
            
        # Extract exclusions
        exclusion_text = self.find_requirement_text(soup, 'exclusion')
        if exclusion_text:
            course_data['exclusions'] = self.parse_course_requirements(exclusion_text)
            
        # Extract breadth requirements
        breadth_text = self.find_requirement_text(soup, 'breadth')
        if breadth_text:
            course_data['breadth_categories'] = self.parse_breadth_requirements(breadth_text)
            
        return course_data
        
    except Exception as e:
        logger.error(f"Failed to extract course details for {course_code}: {e}")
        return None

def find_requirement_text(self, soup, requirement_type):
    """Find requirement text in course page."""
    try:
        # Look for bold text containing the requirement type
        bold_elements = soup.find_all(['strong', 'b'])
        
        for element in bold_elements:
            text = element.get_text().lower()
            if requirement_type in text:
                # Get following text
                next_element = element.next_sibling
                if next_element:
                    return next_element.strip() if isinstance(next_element, str) else next_element.get_text(strip=True)
                    
        return None
        
    except Exception as e:
        logger.error(f"Failed to find {requirement_type} text: {e}")
        return None

def parse_course_requirements(self, req_text):
    """Parse course requirement text to extract course codes."""
    try:
        # Pattern to match course codes like CSC108H1, MAT137Y1, etc.
        course_pattern = r'[A-Z]{3}\d{3}[HY]\d'
        courses = re.findall(course_pattern, req_text)
        return list(set(courses))  # Remove duplicates
        
    except Exception as e:
        logger.error(f"Failed to parse course requirements: {e}")
        return []
```

### Batch Processing with Error Handling

```python
def process_all_courses_with_retry(self, course_codes, max_retries=3):
    """Process multiple courses with retry logic."""
    results = []
    failed_courses = []
    
    for i, course_code in enumerate(course_codes):
        logger.info(f"Processing course {i+1}/{len(course_codes)}: {course_code}")
        
        retry_count = 0
        success = False
        
        while retry_count < max_retries and not success:
            try:
                course_data = self.extract_course_details(course_code)
                if course_data:
                    results.append(course_data)
                    success = True
                    logger.info(f"Successfully processed {course_code}")
                else:
                    raise Exception("No course data returned")
                    
            except Exception as e:
                retry_count += 1
                logger.warning(f"Attempt {retry_count} failed for {course_code}: {e}")
                
                if retry_count < max_retries:
                    # Progressive backoff
                    wait_time = 1.0 * (2 ** retry_count)
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed to process {course_code} after {max_retries} attempts")
                    failed_courses.append(course_code)
                    
        # Add delay between courses
        if success:
            time.sleep(1.0)
            
    logger.info(f"Processed {len(results)} courses successfully, {len(failed_courses)} failed")
    return results, failed_courses

def save_progress_checkpoint(self, data, checkpoint_file):
    """Save progress to allow resuming interrupted scraping."""
    try:
        import json
        with open(checkpoint_file, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Checkpoint saved to {checkpoint_file}")
    except Exception as e:
        logger.error(f"Failed to save checkpoint: {e}")

def load_progress_checkpoint(self, checkpoint_file):
    """Load previous progress to resume scraping."""
    try:
        import json
        with open(checkpoint_file, 'r') as f:
            data = json.load(f)
        logger.info(f"Checkpoint loaded from {checkpoint_file}")
        return data
    except FileNotFoundError:
        logger.info("No checkpoint file found, starting fresh")
        return None
    except Exception as e:
        logger.error(f"Failed to load checkpoint: {e}")
        return None
```
```

---

## Data Structures

### Program Data Model

```python
class Program:
    def __init__(self):
        self.code = ""           # e.g., "ASSPE0608"
        self.title = ""          # e.g., "Actuarial Science Specialist"
        self.type = ""           # "Specialist", "Major", "Minor"
        self.degree_type = ""    # "Arts program", "Science program"
        self.credits_required = 0.0  # Total credits needed
        self.credits_300_plus = 0.0  # 300+ level credits required
        self.credits_400_plus = 0.0  # 400+ level credits required
        self.enrolment_type = ""     # "Limited", "Open"
        self.description = ""
        self.enrolment_requirements = []
        self.completion_requirements = []
        self.required_courses = []
        self.elective_groups = []
        self.notes = []
        self.subject_area = ""
        self.department = ""
```

### Course Data Model

```python
class Course:
    def __init__(self):
        self.code = ""              # e.g., "CSC108H1"
        self.title = ""             # Course title
        self.description = ""       # Course description
        self.credits = 0.5          # Credit value (0.5 or 1.0)
        self.level = 0              # 100, 200, 300, 400
        self.prerequisites = []     # List of prerequisite courses/requirements
        self.corequisites = []      # Courses that must be taken concurrently
        self.exclusions = []        # Courses that cannot be taken with this one
        self.recommended_prep = []  # Recommended preparation
        self.breadth_categories = [] # Breadth requirement categories
        self.department = ""        # Department offering the course
        self.hours = ""            # Contact hours (e.g., "36L", "72L")
        self.experience_type = ""   # "University-Based Experience", etc.
        self.enrolment_controls = [] # Special enrolment restrictions
        self.cr_ncr_eligible = True  # Credit/No Credit eligibility
        self.session_offered = []   # F, S, Y (Fall, Spring, Year-long)
```

### Degree Requirements Model

```python
class DegreeRequirements:
    def __init__(self):
        self.total_credits = 20.0
        self.arts_science_credits = 10.0
        self.credits_200_plus = 13.0
        self.credits_300_plus = 6.0
        self.max_same_designator = 15.0
        self.min_gpa = 1.85
        self.breadth_requirements = {
            "total_credits": 4.0,
            "categories": [
                "Creative and Cultural Representations",
                "Thought, Belief and Behaviour", 
                "Society and its Institutions",
                "Living Things and their Environment",
                "The Physical and Mathematical Universes"
            ],
            "completion_options": [
                {"type": "4_of_5", "credits_per_category": 1.0},
                {"type": "3_plus_2", "major_categories": 3, "minor_categories": 2}
            ]
        }
        self.program_requirements = {
            "min_programs": 1,
            "max_programs": 3,
            "max_majors_specialists": 2,
            "distinct_credits_rule": 12.0  # For multiple program combinations
        }
```

### Student Progress Model

```python
class StudentProgress:
    def __init__(self):
        self.student_id = ""
        self.total_credits = 0.0
        self.credits_by_level = {100: 0.0, 200: 0.0, 300: 0.0, 400: 0.0}
        self.credits_by_designator = {}  # e.g., {"CSC": 3.0, "MAT": 2.5}
        self.current_gpa = 0.0
        self.breadth_progress = {
            "Creative and Cultural Representations": 0.0,
            "Thought, Belief and Behaviour": 0.0,
            "Society and its Institutions": 0.0,
            "Living Things and their Environment": 0.0,
            "The Physical and Mathematical Universes": 0.0
        }
        self.enrolled_programs = []      # List of Program objects
        self.completed_courses = []      # List of completed Course objects
        self.in_progress_courses = []    # Currently enrolled courses
        self.planned_courses = []        # Future planned courses
        self.degree_type = ""           # "HBA" or "HBSc"
        self.expected_graduation = ""    # Session (e.g., "2025 Fall")
```

---

## Selenium Best Practices

### Performance Optimization

```python
class OptimizedUofTScraper(UofTCalendarScraper):
    """Optimized version with performance enhancements."""
    
    def setup_driver(self, headless=True):
        """Setup Chrome with maximum performance optimizations."""
        chrome_options = Options()
        
        if headless:
            chrome_options.add_argument("--headless=new")  # Use new headless mode
        
        # Performance optimizations
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-images")  # Faster loading
        chrome_options.add_argument("--disable-javascript")  # Only if JS not needed
        chrome_options.add_argument("--disable-css")  # Minimal styling
        chrome_options.add_argument("--disable-fonts")
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-renderer-backgrounding")
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")
        
        # Memory optimizations
        chrome_options.add_argument("--memory-pressure-off")
        chrome_options.add_argument("--max_old_space_size=4096")
        
        # Set preferences to block unnecessary content
        prefs = {
            "profile.managed_default_content_settings.images": 2,  # Block images
            "profile.default_content_setting_values.notifications": 2,  # Block notifications
            "profile.managed_default_content_settings.media_stream": 2,  # Block media
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        # Set page load strategy
        chrome_options.add_argument("--page-load-strategy=eager")
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Set timeouts
        self.driver.set_page_load_timeout(30)
        self.driver.implicitly_wait(5)
        self.wait = WebDriverWait(self.driver, 15)

    def batch_extract_with_session_reuse(self, urls, batch_size=50):
        """Extract data in batches, reusing the same session."""
        all_results = []
        
        for i in range(0, len(urls), batch_size):
            batch = urls[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}, URLs {i+1}-{min(i+batch_size, len(urls))}")
            
            batch_results = []
            for url in batch:
                try:
                    result = self.extract_data_from_url(url)
                    if result:
                        batch_results.append(result)
                    time.sleep(0.5)  # Short delay between requests
                except Exception as e:
                    logger.error(f"Failed to process {url}: {e}")
                    
            all_results.extend(batch_results)
            
            # Save batch checkpoint
            self.save_progress_checkpoint(all_results, f"checkpoint_batch_{i//batch_size + 1}.json")
            
        return all_results
```

### Robust Error Handling and Recovery

```python
def robust_element_finder(self, locator, timeout=10, retry_count=3):
    """Find element with robust error handling and retries."""
    for attempt in range(retry_count):
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(locator)
            )
            return element
        except TimeoutException:
            if attempt < retry_count - 1:
                logger.warning(f"Element not found on attempt {attempt + 1}, retrying...")
                time.sleep(2)
                # Try refreshing the page
                self.driver.refresh()
                self.wait_for_page_load()
            else:
                logger.error(f"Element {locator} not found after {retry_count} attempts")
                return None
        except Exception as e:
            logger.error(f"Unexpected error finding element {locator}: {e}")
            return None

def handle_stale_element(self, func, *args, **kwargs):
    """Handle stale element reference exceptions."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except StaleElementReferenceException:
            if attempt < max_retries - 1:
                logger.warning(f"Stale element detected, retrying... (attempt {attempt + 1})")
                time.sleep(1)
                # Re-find the element if it's passed as an argument
                # This would need to be customized based on your specific use case
            else:
                logger.error("Stale element persists after retries")
                raise

def safe_click(self, element_locator, timeout=10):
    """Safely click an element with error handling."""
    try:
        element = self.wait.until(EC.element_to_be_clickable(element_locator))
        self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
        time.sleep(0.5)  # Allow scroll to complete
        element.click()
        return True
    except Exception as e:
        logger.error(f"Failed to click element {element_locator}: {e}")
        return False

def safe_get_text(self, element_locator, default=""):
    """Safely extract text from element."""
    try:
        element = self.driver.find_element(*element_locator)
        return element.text.strip()
    except NoSuchElementException:
        logger.debug(f"Element {element_locator} not found, returning default")
        return default
    except Exception as e:
        logger.error(f"Error extracting text from {element_locator}: {e}")
        return default
```

### Smart Waiting Strategies

```python
def wait_for_content_stability(self, locator, stable_time=2, timeout=30):
    """Wait for content to stabilize (useful for dynamic content)."""
    end_time = time.time() + timeout
    last_content = None
    stable_start = None
    
    while time.time() < end_time:
        try:
            element = self.driver.find_element(*locator)
            current_content = element.text
            
            if current_content == last_content:
                if stable_start is None:
                    stable_start = time.time()
                elif time.time() - stable_start >= stable_time:
                    logger.info("Content has stabilized")
                    return True
            else:
                stable_start = None
                last_content = current_content
                
            time.sleep(0.5)
            
        except NoSuchElementException:
            time.sleep(0.5)
            continue
            
    logger.warning("Content did not stabilize within timeout")
    return False

def wait_for_ajax_complete(self, timeout=30):
    """Wait for AJAX requests to complete."""
    try:
        WebDriverWait(self.driver, timeout).until(
            lambda driver: driver.execute_script("return jQuery.active == 0") if 
            driver.execute_script("return typeof jQuery !== 'undefined'") else True
        )
    except Exception:
        # Fallback: just wait a bit
        time.sleep(2)

def smart_page_load_wait(self, url, expected_element_locator=None):
    """Smart page loading with multiple wait conditions."""
    self.driver.get(url)
    
    # Wait for basic page load
    self.wait.until(lambda driver: driver.execute_script("return document.readyState") == "complete")
    
    # Wait for specific element if provided
    if expected_element_locator:
        try:
            self.wait.until(EC.presence_of_element_located(expected_element_locator))
        except TimeoutException:
            logger.warning(f"Expected element {expected_element_locator} not found")
    
    # Wait for potential AJAX
    self.wait_for_ajax_complete()
    
    # Final stabilization wait
    time.sleep(1)
```

### Data Validation and Cleaning

```python
def validate_program_data(self, program_data):
    """Validate extracted program data."""
    required_fields = ['title', 'code', 'type']
    
    for field in required_fields:
        if not program_data.get(field):
            logger.warning(f"Missing required field: {field} in program data")
            return False
    
    # Validate program code format
    code_pattern = r'^AS[A-Z]{3}\d{4}$'
    if not re.match(code_pattern, program_data.get('code', '')):
        logger.warning(f"Invalid program code format: {program_data.get('code')}")
        return False
    
    # Validate program type
    valid_types = ['Specialist', 'Major', 'Minor', 'Certificate', 'Focus']
    if program_data.get('type') not in valid_types:
        logger.warning(f"Invalid program type: {program_data.get('type')}")
        return False
    
    return True

def clean_course_code(self, course_code):
    """Clean and validate course code format."""
    if not course_code:
        return None
    
    # Remove extra whitespace and convert to uppercase
    cleaned = course_code.strip().upper()
    
    # Validate format (e.g., CSC108H1, MAT137Y1)
    pattern = r'^[A-Z]{3}\d{3}[HY]\d$'
    if re.match(pattern, cleaned):
        return cleaned
    else:
        logger.warning(f"Invalid course code format: {course_code}")
        return None

def parse_credit_value(self, text):
    """Parse credit value from text."""
    if not text:
        return 0.0
    
    # Look for patterns like "2.0 credits", "1.5 FCE", etc.
    patterns = [
        r'(\d+\.?\d*)\s*credits?',
        r'(\d+\.?\d*)\s*FCE',
        r'(\d+\.?\d*)\s*credit',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                continue
    
    return 0.0
```

### Session Management and Recovery

```python
class SessionManager:
    """Manage Selenium sessions with automatic recovery."""
    
    def __init__(self, scraper_class, max_session_duration=3600):
        self.scraper_class = scraper_class
        self.max_session_duration = max_session_duration
        self.session_start_time = None
        self.current_scraper = None
        
    def get_scraper(self):
        """Get current scraper or create new one if needed."""
        current_time = time.time()
        
        if (self.current_scraper is None or 
            self.session_start_time is None or
            current_time - self.session_start_time > self.max_session_duration):
            
            logger.info("Creating new scraper session")
            self._create_new_session()
            
        return self.current_scraper
    
    def _create_new_session(self):
        """Create a new scraper session."""
        if self.current_scraper:
            try:
                self.current_scraper.driver.quit()
            except Exception:
                pass
                
        self.current_scraper = self.scraper_class()
        self.session_start_time = time.time()
    
    def close(self):
        """Close current session."""
        if self.current_scraper:
            try:
                self.current_scraper.driver.quit()
            except Exception:
                pass
            self.current_scraper = None
            self.session_start_time = None

# Usage example
session_manager = SessionManager(UofTCalendarScraper)

def process_with_session_management(urls):
    """Process URLs with automatic session management."""
    results = []
    
    try:
        for url in urls:
            scraper = session_manager.get_scraper()
            result = scraper.extract_data_from_url(url)
            if result:
                results.append(result)
    finally:
        session_manager.close()
    
    return results
```

---

## Error Handling & Debugging

### Common Selenium Issues and Solutions

```python
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, StaleElementReferenceException,
    WebDriverException, ElementNotInteractableException
)

class SeleniumErrorHandler:
    """Centralized error handling for Selenium operations."""
    
    @staticmethod
    def handle_timeout_exception(e, context=""):
        """Handle timeout exceptions with context."""
        logger.error(f"Timeout exception in {context}: {e}")
        return {
            'error_type': 'timeout',
            'context': context,
            'message': str(e),
            'suggestion': 'Increase wait time or check element locator'
        }
    
    @staticmethod
    def handle_no_such_element(e, locator, context=""):
        """Handle missing element exceptions."""
        logger.error(f"Element not found: {locator} in {context}: {e}")
        return {
            'error_type': 'element_not_found',
            'locator': locator,
            'context': context,
            'suggestion': 'Check if page loaded correctly or locator is correct'
        }

def debug_page_state(driver, save_screenshot=True):
    """Debug current page state for troubleshooting."""
    debug_info = {
        'current_url': driver.current_url,
        'page_title': driver.title,
        'page_source_length': len(driver.page_source),
        'window_size': driver.get_window_size(),
        'ready_state': driver.execute_script("return document.readyState"),
        'timestamp': time.time()
    }
    
    if save_screenshot:
        screenshot_path = f"debug_screenshot_{int(time.time())}.png"
        driver.save_screenshot(screenshot_path)
        debug_info['screenshot'] = screenshot_path
    
    logger.info(f"Debug info: {debug_info}")
    return debug_info
```

### Debugging Tools and Utilities

```python
def inspect_element_properties(driver, locator):
    """Inspect element properties for debugging."""
    try:
        element = driver.find_element(*locator)
        properties = {
            'tag_name': element.tag_name,
            'text': element.text,
            'is_displayed': element.is_displayed(),
            'is_enabled': element.is_enabled(),
            'location': element.location,
            'size': element.size,
            'attributes': {}
        }
        
        # Get common attributes
        common_attrs = ['id', 'class', 'name', 'href', 'src', 'value']
        for attr in common_attrs:
            try:
                value = element.get_attribute(attr)
                if value:
                    properties['attributes'][attr] = value
            except Exception:
                pass
                
        return properties
    except Exception as e:
        logger.error(f"Failed to inspect element {locator}: {e}")
        return None

def setup_comprehensive_logging():
    """Setup comprehensive logging for scraping operations."""
    import os
    os.makedirs('logs', exist_ok=True)
    
    logger = logging.getLogger('uoft_scraper')
    logger.setLevel(logging.DEBUG)
    
    # File handler for detailed logs
    file_handler = logging.FileHandler(
        f'logs/scraper_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    )
    file_handler.setLevel(logging.DEBUG)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger
```
```

## Database Integration

### SQLAlchemy Models for Scraped Data

```python
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

Base = declarative_base()

class Program(Base):
    """Program model for scraped program data."""
    __tablename__ = 'programs'
    
    id = Column(Integer, primary_key=True)
    code = Column(String(10), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    type = Column(String(20), nullable=False)  # Specialist, Major, Minor
    degree_type = Column(String(20))  # Arts program, Science program
    credits_required = Column(Float)
    credits_300_plus = Column(Float)
    credits_400_plus = Column(Float)
    enrolment_type = Column(String(20))  # Limited, Open
    description = Column(Text)
    subject_area = Column(String(100))
    department = Column(String(100))
    scraped_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    requirements = relationship("ProgramRequirement", back_populates="program")
    courses = relationship("ProgramCourse", back_populates="program")

class Course(Base):
    """Course model for scraped course data."""
    __tablename__ = 'courses'
    
    id = Column(Integer, primary_key=True)
    code = Column(String(10), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    credits = Column(Float, nullable=False)
    level = Column(Integer, nullable=False, index=True)
    department = Column(String(100))
    hours = Column(String(50))
    session_offered = Column(String(10))  # F, S, Y
    breadth_categories = Column(Text)  # JSON string
    prerequisites = Column(Text)
    corequisites = Column(Text)
    exclusions = Column(Text)
    cr_ncr_eligible = Column(Boolean, default=True)
    scraped_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    program_courses = relationship("ProgramCourse", back_populates="course")

class ProgramRequirement(Base):
    """Program requirements extracted from scraping."""
    __tablename__ = 'program_requirements'
    
    id = Column(Integer, primary_key=True)
    program_id = Column(Integer, ForeignKey('programs.id'), nullable=False)
    requirement_type = Column(String(50), nullable=False)  # enrolment, completion
    requirement_text = Column(Text, nullable=False)
    year_level = Column(Integer)  # 1, 2, 3, 4 for year-specific requirements
    category = Column(String(100))  # For grouped requirements
    scraped_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    program = relationship("Program", back_populates="requirements")

class ProgramCourse(Base):
    """Many-to-many relationship between programs and courses."""
    __tablename__ = 'program_courses'
    
    id = Column(Integer, primary_key=True)
    program_id = Column(Integer, ForeignKey('programs.id'), nullable=False)
    course_id = Column(Integer, ForeignKey('courses.id'), nullable=False)
    requirement_type = Column(String(50))  # required, elective, optional
    year_level = Column(Integer)
    group_name = Column(String(100))  # For grouped electives
    is_optional = Column(Boolean, default=False)
    notes = Column(Text)
    
    # Relationships
    program = relationship("Program", back_populates="courses")
    course = relationship("Course", back_populates="program_courses")

class ScrapingLog(Base):
    """Log scraping operations for monitoring and debugging."""
    __tablename__ = 'scraping_logs'
    
    id = Column(Integer, primary_key=True)
    operation_type = Column(String(50), nullable=False)  # program_scrape, course_scrape
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    status = Column(String(20), nullable=False)  # running, completed, failed
    items_processed = Column(Integer, default=0)
    items_failed = Column(Integer, default=0)
    error_message = Column(Text)
    log_file_path = Column(String(255))
```

### Database Operations for Selenium Scraping

```python
class DatabaseManager:
    """Manage database operations for scraped data."""
    
    def __init__(self, database_url="sqlite:///uoft_calendar.db"):
        self.engine = create_engine(database_url, echo=False)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
    
    def save_program(self, program_data):
        """Save or update program data from scraping."""
        try:
            # Check if program exists
            existing = self.session.query(Program).filter_by(code=program_data['code']).first()
            
            if existing:
                # Update existing program
                for key, value in program_data.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                existing.last_updated = datetime.utcnow()
                program = existing
            else:
                # Create new program
                program = Program(**program_data)
                self.session.add(program)
            
            self.session.commit()
            logger.info(f"Saved program: {program_data['code']}")
            return program
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to save program {program_data.get('code')}: {e}")
            return None
    
    def save_course(self, course_data):
        """Save or update course data from scraping."""
        try:
            # Convert lists to JSON strings for storage
            if 'breadth_categories' in course_data and isinstance(course_data['breadth_categories'], list):
                course_data['breadth_categories'] = json.dumps(course_data['breadth_categories'])
            
            # Check if course exists
            existing = self.session.query(Course).filter_by(code=course_data['code']).first()
            
            if existing:
                # Update existing course
                for key, value in course_data.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                existing.last_updated = datetime.utcnow()
                course = existing
            else:
                # Create new course
                course = Course(**course_data)
                self.session.add(course)
            
            self.session.commit()
            logger.info(f"Saved course: {course_data['code']}")
            return course
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to save course {course_data.get('code')}: {e}")
            return None
    
    def bulk_save_programs(self, programs_data):
        """Bulk save multiple programs efficiently."""
        try:
            saved_count = 0
            for program_data in programs_data:
                if self.save_program(program_data):
                    saved_count += 1
            
            logger.info(f"Bulk saved {saved_count}/{len(programs_data)} programs")
            return saved_count
            
        except Exception as e:
            logger.error(f"Bulk save programs failed: {e}")
            return 0
    
    def log_scraping_operation(self, operation_type, status, **kwargs):
        """Log scraping operation for monitoring."""
        try:
            log_entry = ScrapingLog(
                operation_type=operation_type,
                status=status,
                start_time=kwargs.get('start_time', datetime.utcnow()),
                end_time=kwargs.get('end_time'),
                items_processed=kwargs.get('items_processed', 0),
                items_failed=kwargs.get('items_failed', 0),
                error_message=kwargs.get('error_message'),
                log_file_path=kwargs.get('log_file_path')
            )
            
            self.session.add(log_entry)
            self.session.commit()
            
        except Exception as e:
            logger.error(f"Failed to log scraping operation: {e}")
    
    def get_programs_by_type(self, program_type):
        """Get programs by type (Specialist, Major, Minor)."""
        return self.session.query(Program).filter_by(type=program_type).all()
    
    def get_courses_by_level(self, level):
        """Get courses by level (100, 200, 300, 400)."""
        return self.session.query(Course).filter_by(level=level).all()
    
    def search_programs(self, keyword):
        """Search programs by keyword in title or description."""
        return self.session.query(Program).filter(
            Program.title.contains(keyword) | 
            Program.description.contains(keyword)
        ).all()
    
    def close(self):
        """Close database session."""
        self.session.close()
```

### Integration with Selenium Scraper

```python
class UofTCalendarScraperWithDB(UofTCalendarScraper):
    """Extended scraper with database integration."""
    
    def __init__(self, database_url="sqlite:///uoft_calendar.db", headless=True):
        super().__init__(headless)
        self.db = DatabaseManager(database_url)
        
    def scrape_and_save_all_programs(self):
        """Scrape all programs and save to database."""
        start_time = datetime.utcnow()
        operation_id = None
        
        try:
            # Log operation start
            self.db.log_scraping_operation(
                operation_type="program_scrape",
                status="running",
                start_time=start_time
            )
            
            # Extract programs
            programs = self.extract_all_programs()
            
            # Save to database
            saved_count = self.db.bulk_save_programs(programs)
            
            # Log completion
            self.db.log_scraping_operation(
                operation_type="program_scrape",
                status="completed",
                start_time=start_time,
                end_time=datetime.utcnow(),
                items_processed=saved_count,
                items_failed=len(programs) - saved_count
            )
            
            logger.info(f"Completed program scraping: {saved_count} saved")
            return saved_count
            
        except Exception as e:
            # Log failure
            self.db.log_scraping_operation(
                operation_type="program_scrape",
                status="failed",
                start_time=start_time,
                end_time=datetime.utcnow(),
                error_message=str(e)
            )
            logger.error(f"Program scraping failed: {e}")
            return 0
    
    def scrape_and_save_courses_from_programs(self):
        """Extract course codes from programs and scrape course details."""
        # Get all programs from database
        programs = self.db.session.query(Program).all()
        all_course_codes = set()
        
        # Extract course codes from program requirements
        for program in programs:
            if program.description:
                course_codes = self.extract_course_codes(program.description)
                all_course_codes.update(course_codes)
        
        logger.info(f"Found {len(all_course_codes)} unique courses to scrape")
        
        # Scrape course details
        courses_data, failed_courses = self.process_all_courses_with_retry(list(all_course_codes))
        
        # Save to database
        saved_count = 0
        for course_data in courses_data:
            if self.db.save_course(course_data):
                saved_count += 1
        
        logger.info(f"Saved {saved_count} courses, {len(failed_courses)} failed")
        return saved_count, failed_courses
    
    def __del__(self):
        """Clean up database connection."""
        if hasattr(self, 'db'):
            self.db.close()
        super().__del__()
```

### Usage Example

```python
def main():
    """Main scraping workflow."""
    # Setup logging
    logger = setup_comprehensive_logging()
    
    # Initialize scraper with database
    scraper = UofTCalendarScraperWithDB(
        database_url="sqlite:///uoft_calendar.db",
        headless=True
    )
    
    try:
        # Scrape programs
        logger.info("Starting program scraping...")
        programs_saved = scraper.scrape_and_save_all_programs()
        
        # Scrape courses
        logger.info("Starting course scraping...")
        courses_saved, failed_courses = scraper.scrape_and_save_courses_from_programs()
        
        # Summary
        logger.info(f"Scraping completed: {programs_saved} programs, {courses_saved} courses")
        
        if failed_courses:
            logger.warning(f"Failed courses: {failed_courses}")
            
    except Exception as e:
        logger.error(f"Scraping workflow failed: {e}")
    finally:
        scraper.driver.quit()

if __name__ == "__main__":
    main()
```

---

## Additional Resources

### Important URLs to Monitor
- Academic Calendar Updates: `https://artsci.calendar.utoronto.ca/course-changes`
- Program Changes: `https://artsci.calendar.utoronto.ca/program-and-certificate-changes`
- Archived Calendars: `https://artsci.calendar.utoronto.ca/archived-calendars`

### Related Systems
- **ACORN**: Student information system (course enrollment, grades)
- **Degree Explorer**: Degree planning tool (requirement tracking)
- **Timetable Builder**: Course scheduling tool

### Selenium-Specific Considerations
- Use headless mode for production scraping
- Implement proper wait strategies for dynamic content
- Handle stale element references with retry logic
- Monitor memory usage for long-running scraping sessions
- Use session management to prevent resource leaks
- Implement comprehensive error handling and logging
- Regular checkpoints for resuming interrupted scraping
- Respect robots.txt and implement rate limiting

### Performance Tips
- Disable images and CSS for faster loading
- Use batch processing for large datasets
- Implement connection pooling for database operations
- Cache frequently accessed data
- Use appropriate database indexes for search operations
- Monitor and log performance metrics

---

*This document serves as a comprehensive Selenium and Python implementation guide for University of Toronto Academic Calendar data extraction and student transcript tracking functionality.*
