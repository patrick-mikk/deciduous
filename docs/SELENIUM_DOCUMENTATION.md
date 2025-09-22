# Selenium Web Scraping Documentation
## University of Toronto Academic Calendar Integration

This document provides comprehensive documentation of the selenium-based web scraping implementation for extracting course data from the University of Toronto Academic Calendar.

## 🎯 Overview

The scraping system targets the UofT Academic Calendar at `https://artsci.calendar.utoronto.ca` to extract detailed course information including:
- Course codes and titles
- Course descriptions
- Prerequisites and exclusions
- Credit values
- Breadth requirements
- Course hours (lecture/tutorial format)

## 🔍 Selenium Locator Strategy

### Base URLs
```python
BASE_URL = "https://artsci.calendar.utoronto.ca"
SEARCH_URL = "https://artsci.calendar.utoronto.ca/search-courses"
COURSE_URL_PATTERN = "https://artsci.calendar.utoronto.ca/course/{course_code_lower}"
```

### WebDriver Configuration
```python
def setup_driver(self):
    chrome_options = Options()

    # Performance optimizations
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins")
    chrome_options.add_argument("--disable-images")
    chrome_options.add_argument("--disable-javascript")  # Optional for faster loading

    # Optional headless mode
    if self.headless:
        chrome_options.add_argument("--headless")

    # Initialize driver with optimizations
    service = Service(ChromeDriverManager().install())
    self.driver = webdriver.Chrome(service=service, options=chrome_options)
    self.wait = WebDriverWait(self.driver, 10)
```

## 📋 Course Search Locators

### Search Form Elements

#### Course Search Form
```python
COURSE_SEARCH_FORM = (By.ID, "views-exposed-form-course-search-page-1")
```
**Purpose**: Main container for the course search interface
**Reliability**: High - Uses stable form ID
**Fallback**: None needed (essential element)

#### Course Keyword Input Field
```python
COURSE_KEYWORD_INPUT_STRATEGIES = [
    (By.ID, "edit-course-keyword"),                    # Primary
    (By.NAME, "course_keyword"),                       # Secondary
    (By.CSS_SELECTOR, "input[placeholder*='Course Code']"),  # Fallback
    (By.CSS_SELECTOR, "input[placeholder*='course']"),      # Fallback
    (By.CSS_SELECTOR, "input[type='text']")                 # Last resort
]
```
**Purpose**: Text input field for entering course codes or keywords
**Strategy**: Multiple fallback locators for robustness
**HTML Example**:
```html
<input id="edit-course-keyword" name="course_keyword"
       placeholder="Course Code" type="text" class="form-text">
```

#### Search Submit Button
```python
SEARCH_BUTTON_STRATEGIES = [
    (By.ID, "edit-submit-course-search"),             # Primary
    (By.CSS_SELECTOR, "input[value='Apply']"),        # Secondary
    (By.CSS_SELECTOR, "input[type='submit']"),        # Fallback
    (By.CSS_SELECTOR, ".form-submit")                 # Last resort
]
```
**Purpose**: Submit button to execute the search
**Strategy**: Multiple fallback strategies for different button implementations
**HTML Example**:
```html
<input id="edit-submit-course-search" type="submit"
       value="Apply" class="form-submit">
```

### Search Results Elements

#### Results Container
```python
SEARCH_RESULTS_CONTAINER = (By.CSS_SELECTOR, ".view-content")
```
**Purpose**: Main container holding all search results
**Reliability**: High - Standard Drupal Views structure
**HTML Structure**:
```html
<div class="view-content">
    <div class="views-row">...</div>
    <div class="views-row">...</div>
</div>
```

#### Individual Result Items
```python
COURSE_RESULT_ITEMS = [
    (By.CSS_SELECTOR, ".views-row"),                  # Primary
    (By.CSS_SELECTOR, ".course-result-item"),         # Fallback
    (By.CSS_SELECTOR, ".search-result")               # Last resort
]
```
**Purpose**: Individual course result containers
**Strategy**: Primary locator targets Drupal Views structure
**HTML Example**:
```html
<div class="views-row views-row-1 views-row-odd views-row-first">
    <h3 class="js-views-accordion-group-header">
        <div>POL208H1: Introduction to International Relations</div>
    </h3>
</div>
```

#### Course Title in Results
```python
COURSE_TITLE_IN_RESULT = [
    (By.CSS_SELECTOR, "h3.js-views-accordion-group-header div"),  # Primary
    (By.CSS_SELECTOR, "h3.js-views-accordion-group-header"),      # Fallback
    (By.CSS_SELECTOR, ".course-title"),                           # Fallback
    (By.CSS_SELECTOR, "h3")                                       # Last resort
]
```
**Purpose**: Extract course title from search result
**Strategy**: Targets accordion header structure used by UofT calendar
**Text Format**: "POL208H1: Introduction to International Relations"

#### Course Links
```python
COURSE_LINKS = (By.XPATH, "//a[contains(@href, '/course/')]")
```
**Purpose**: Links to individual course detail pages
**Reliability**: High - URL pattern is consistent
**URL Format**: `/course/pol208h1`

## 📖 Course Detail Page Locators

### Page Structure
Course detail pages follow this URL pattern:
```
https://artsci.calendar.utoronto.ca/course/{course_code_lower}
```
Example: `https://artsci.calendar.utoronto.ca/course/pol208h1`

### Course Information Elements

#### Course Title
```python
COURSE_PAGE_TITLE = (By.CSS_SELECTOR, "#block-w3css-subtheme-page-title > h1")
```
**Purpose**: Main course title on detail page
**Reliability**: High - Uses page title block structure
**HTML Example**:
```html
<div id="block-w3css-subtheme-page-title">
    <h1>POL208H1: Introduction to International Relations</h1>
</div>
```
**Text Format**: "POL208H1: Introduction to International Relations"

#### Course Hours
```python
COURSE_PAGE_HOURS = (By.CSS_SELECTOR, "#block-w3css-subtheme-content > article > div > div.w3-row.field.field--name-field-hours.field--type-text.field--label-inline.clearfix > div > p")
```
**Purpose**: Extract course hours (lecture/tutorial format)
**Reliability**: Medium - Complex CSS path, but stable field structure
**HTML Example**:
```html
<div class="w3-row field field--name-field-hours field--type-text field--label-inline clearfix">
    <div class="field__label">Hours:</div>
    <div class="field__item"><p>24L/12T</p></div>
</div>
```
**Text Format**: "24L/12T" (24 Lecture hours, 12 Tutorial hours)

#### Course Description
```python
COURSE_PAGE_DESCRIPTION = (By.CSS_SELECTOR, "#block-w3css-subtheme-content > article > div > div.w3-row.field.field--name-body.field--type-text-with-summary.field--label-hidden.w3-bar-item.field__item")
```
**Purpose**: Main course description paragraph
**Reliability**: Medium - Long CSS path but unique structure
**HTML Example**:
```html
<div class="w3-row field field--name-body field--type-text-with-summary field--label-hidden w3-bar-item field__item">
    <p>This introductory course examines some key themes and issues in global politics...</p>
</div>
```

#### Prerequisites
```python
COURSE_PAGE_PREREQUISITES = (By.CSS_SELECTOR, "#block-w3css-subtheme-content > article > div > div.w3-row.field.field--name-field-prerequisite.field--type-text-long.field--label-inline.clearfix > div")
```
**Purpose**: Course prerequisite requirements
**Reliability**: Medium - Field-based structure is stable
**HTML Example**:
```html
<div class="w3-row field field--name-field-prerequisite field--type-text-long field--label-inline clearfix">
    <div class="field__label">Prerequisite:</div>
    <div class="field__item">4.0 credits, or 1.0 credit in POL/ JPA/ JPF/ JPI/ JPR/ JPS/ JRA courses</div>
</div>
```

#### Exclusions
```python
COURSE_PAGE_EXCLUSIONS = (By.CSS_SELECTOR, "#block-w3css-subtheme-content > article > div > div.w3-row.field.field--name-field-exclusion.field--type-text-long.field--label-inline.clearfix > div")
```
**Purpose**: Courses that cannot be taken with this course
**Reliability**: Medium - Field-based structure
**HTML Example**:
```html
<div class="w3-row field field--name-field-exclusion field--type-text-long field--label-inline clearfix">
    <div class="field__label">Exclusion:</div>
    <div class="field__item">POL208Y1/ POL208Y5/ POL209H5/ POLB80H3/ POLB81H3</div>
</div>
```

#### Breadth Requirements
```python
COURSE_PAGE_BREADTH = (By.CSS_SELECTOR, "#block-w3css-subtheme-content > article > div > div.w3-row.field.field--name-field-breadth-requirements.field--type-list-string.field--label-inline.clearfix > div")
```
**Purpose**: Breadth requirement category
**Reliability**: Medium - Field structure is consistent
**HTML Example**:
```html
<div class="w3-row field field--name-field-breadth-requirements field--type-list-string field--label-inline clearfix">
    <div class="field__label">Breadth Requirements:</div>
    <div class="field__item">Society and its Institutions (3)</div>
</div>
```

#### Corequisites
```python
COURSE_PAGE_COREQUISITES = (By.CSS_SELECTOR, ".field--name-field-corequisite .field__item")
```
**Purpose**: Courses that must be taken simultaneously
**Reliability**: Medium - Less common field, simpler selector
**HTML Example**:
```html
<div class="field field--name-field-corequisite">
    <div class="field__item">Must be taken with POL200Y1</div>
</div>
```

## 🔧 Implementation Strategies

### Robust Element Finding
```python
def find_element_with_strategies(self, strategies):
    """Try multiple locator strategies until one succeeds"""
    for strategy in strategies:
        try:
            element = self.wait.until(EC.presence_of_element_located(strategy))
            return element
        except TimeoutException:
            continue
    raise NoSuchElementException("No strategy succeeded")
```

### Error Handling and Retries
```python
def extract_course_from_element(self, course_element):
    """Extract course data with fallback handling"""
    course_data = {}

    try:
        # Try multiple strategies for course title
        title_element = None
        for strategy in self.COURSE_TITLE_IN_RESULT:
            try:
                title_element = course_element.find_element(*strategy)
                break
            except NoSuchElementException:
                continue

        if title_element:
            title_text = title_element.text.strip()
            # Parse "POL208H1: Introduction to International Relations"
            if ':' in title_text:
                course_code, title = title_text.split(':', 1)
                course_data['course_code'] = course_code.strip()
                course_data['title'] = title.strip()
            else:
                course_data['course_code'] = title_text
                course_data['title'] = title_text

    except Exception as e:
        if self.debug:
            print(f"Error extracting course title: {e}")

    return course_data
```

### Page Navigation and Timing
```python
def get_course_details(self, course_code):
    """Navigate to course page and extract details"""
    try:
        # Navigate to course page
        course_url = f"{self.base_url}/course/{course_code.lower()}"
        self.driver.get(course_url)

        # Wait for page load
        self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        # Extract all course details
        course_details = self._extract_all_course_fields(course_code)

        return course_details

    except Exception as e:
        if self.debug:
            print(f"Failed to get course details for {course_code}: {e}")
        return None
```

## 🚧 Known Issues and Limitations

### 1. Dynamic Content Loading
**Issue**: Some course details may load asynchronously
**Solution**: Use explicit waits for specific elements
```python
self.wait.until(EC.presence_of_element_located(locator))
```

### 2. Rate Limiting
**Issue**: Too many requests may trigger rate limiting
**Solution**: Add delays between requests
```python
import time
time.sleep(1)  # 1 second delay between requests
```

### 3. Selenium WebDriver Management
**Issue**: WebDriver instances can accumulate and consume resources
**Solution**: Proper cleanup in `__del__` method
```python
def __del__(self):
    self.close_driver()

def close_driver(self):
    if self.driver:
        self.driver.quit()
        self.driver = None
```

### 4. Field Availability Variations
**Issue**: Not all courses have all fields (prerequisites, exclusions, etc.)
**Solution**: Graceful handling of missing elements
```python
try:
    prereq_element = self.driver.find_element(*COURSE_PAGE_PREREQUISITES)
    course_details['prerequisites'] = prereq_element.text.strip()
except NoSuchElementException:
    course_details['prerequisites'] = ''
```

## 📊 Data Extraction Results

### Successfully Extracted Fields
Based on testing with POL208H1:

| Field | Status | Example Value |
|-------|--------|---------------|
| Course Code | ✅ Reliable | "POL208H1" |
| Title | ✅ Reliable | "Introduction to International Relations" |
| Description | ✅ Reliable | "This introductory course examines..." |
| Hours | ✅ Reliable | "24L/12T" |
| Prerequisites | ✅ Reliable | "4.0 credits, or 1.0 credit in POL/..." |
| Exclusions | ✅ Reliable | "POL208Y1/ POL208Y5/ POL209H5/..." |
| Breadth Requirements | ✅ Reliable | "Society and its Institutions (3)" |
| Corequisites | ⚠️ Variable | Often empty |
| Department | ✅ Derived | "POL" (from course code) |
| Level | ✅ Derived | 2 (from course code) |
| Credits | ✅ Derived | 0.5 (H courses) / 1.0 (Y courses) |

### Data Quality Verification
All extracted data matches the source HTML content exactly, with proper handling of:
- HTML entity decoding
- Whitespace normalization
- Empty field handling
- Multi-line text preservation

## 🔄 Maintenance and Updates

### Monitoring Locator Health
Regular testing should verify:
1. Search functionality works
2. Course detail extraction succeeds
3. All expected fields are captured
4. No new required fields are missed

### Updating Locators
When locators break:
1. Inspect the current HTML structure
2. Update the primary locator
3. Add new fallback strategies if needed
4. Test with multiple course examples
5. Update this documentation

### Testing Strategy
```python
def test_locators():
    """Test all locators with known course codes"""
    test_courses = ['POL208H1', 'MAT137Y1', 'CSC108H1']

    for course_code in test_courses:
        details = scraper.get_course_details(course_code)
        assert details is not None
        assert details['course_code'] == course_code
        assert len(details['title']) > 0
        assert len(details['description']) > 0
```

This documentation ensures the selenium-based scraping system remains maintainable and reliable for extracting course data from the University of Toronto Academic Calendar.