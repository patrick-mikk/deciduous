"""
Enhanced Academic Calendar Scraper for UofT Course Dashboard
Improved selenium integration based on comprehensive analysis and reference documentation
"""

import time
import re
import logging
from typing import List, Dict, Optional
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    NoSuchElementException, TimeoutException,
    WebDriverException, ElementNotInteractableException
)

try:
    from webdriver_manager.chrome import ChromeDriverManager
    WEBDRIVER_MANAGER_AVAILABLE = True
except ImportError:
    WEBDRIVER_MANAGER_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UofTLocators:
    """Centralized locator definitions for UofT Academic Calendar based on reference documentation."""

    # Main navigation elements
    COURSE_SEARCH_LINK = (By.XPATH, "//a[@href='/search-courses']")

    # Search interface elements - Updated based on current structure
    COURSE_SEARCH_FORM = (By.CSS_SELECTOR, "form[action*='search']")

    # Search input fields - Multiple strategies
    COURSE_KEYWORD_INPUT_STRATEGIES = [
        (By.NAME, "course-keyword"),
        (By.NAME, "course_keyword"),
        (By.NAME, "keyword"),
        (By.ID, "edit-course-keyword"),
        (By.ID, "edit-keyword"),
        (By.CSS_SELECTOR, "input[name*='keyword']"),
        (By.CSS_SELECTOR, "input[placeholder*='course']"),
        (By.CSS_SELECTOR, "input[type='text']")
    ]

    # Search buttons
    SEARCH_BUTTON_STRATEGIES = [
        (By.CSS_SELECTOR, "input[type='submit']"),
        (By.CSS_SELECTOR, "button[type='submit']"),
        (By.XPATH, "//input[@value='Search' or @value='search']"),
        (By.XPATH, "//button[contains(text(), 'Search')]"),
        (By.CSS_SELECTOR, ".form-submit")
    ]

    # Search results - Based on current UofT structure
    SEARCH_RESULTS_CONTAINER = (By.CSS_SELECTOR, ".view-content, .search-results, .view-course-search")

    # Result items - Modern UofT structure uses views
    COURSE_RESULT_ITEMS = [
        (By.CSS_SELECTOR, ".views-row"),
        (By.CSS_SELECTOR, ".course-result-item"),
        (By.CSS_SELECTOR, ".search-result"),
        (By.CSS_SELECTOR, "[data-course-code]")
    ]

    # Course details in results
    COURSE_TITLE_IN_RESULT = [
        (By.CSS_SELECTOR, "h3.js-views-accordion-group-header"),
        (By.CSS_SELECTOR, ".course-title"),
        (By.CSS_SELECTOR, "h3 a"),
        (By.CSS_SELECTOR, ".views-field-title")
    ]

    # Course links
    COURSE_LINKS = (By.XPATH, "//a[contains(@href, '/course/')]")

class EnhancedAcademicCalendarScraper:
    """Enhanced scraper with improved selenium integration and error handling."""

    def __init__(self, debug=False, headless=True):
        self.base_url = "https://artsci.calendar.utoronto.ca"
        self.search_url = f"{self.base_url}/search-courses"
        self.driver = None
        self.wait = None
        self.debug = debug
        self.headless = headless
        self.setup_driver()

    def setup_driver(self):
        """Set up Chrome WebDriver with optimized settings."""
        try:
            chrome_options = Options()

            if self.headless and not self.debug:
                chrome_options.add_argument("--headless")

            # Performance optimizations from reference documentation
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-plugins")
            chrome_options.add_argument("--window-size=1920,1080")

            # User agent for better compatibility
            chrome_options.add_argument(
                "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            )

            # Enable logging for debugging
            if self.debug:
                chrome_options.add_argument("--enable-logging")
                chrome_options.add_argument("--v=1")

            # Setup service
            if WEBDRIVER_MANAGER_AVAILABLE:
                service = Service(ChromeDriverManager().install())
            else:
                service = Service()  # Assumes chromedriver in PATH

            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.implicitly_wait(10)
            self.wait = WebDriverWait(self.driver, 20)

            logger.info("WebDriver setup successful")

        except Exception as e:
            logger.error(f"Failed to setup WebDriver: {e}")
            self.driver = None
            self.wait = None

    def close_driver(self):
        """Close the WebDriver safely."""
        try:
            if self.driver:
                self.driver.quit()
                logger.info("WebDriver closed successfully")
        except Exception as e:
            logger.error(f"Error closing WebDriver: {e}")

    def wait_for_page_load(self, timeout=15):
        """Wait for page to fully load."""
        try:
            self.wait.until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            time.sleep(1)  # Additional stabilization time
            return True
        except TimeoutException:
            logger.error("Page load timeout")
            return False

    def wait_for_search_results(self, timeout=15):
        """Wait for search results to load with multiple strategies."""
        try:
            # Try to wait for results container
            self.wait.until(
                EC.presence_of_element_located(UofTLocators.SEARCH_RESULTS_CONTAINER)
            )

            # Wait for actual content to appear
            time.sleep(2)

            # Verify we have actual results
            for result_strategy in UofTLocators.COURSE_RESULT_ITEMS:
                try:
                    results = self.driver.find_elements(*result_strategy)
                    if results:
                        logger.info(f"Found {len(results)} results using {result_strategy}")
                        return True
                except:
                    continue

            return False

        except TimeoutException:
            logger.error("Search results failed to load within timeout")
            return False

    def find_search_input(self):
        """Find search input using multiple strategies."""
        for strategy in UofTLocators.COURSE_KEYWORD_INPUT_STRATEGIES:
            try:
                element = self.driver.find_element(*strategy)
                if element.is_displayed() and element.is_enabled():
                    logger.info(f"Found search input using strategy: {strategy}")
                    return element
            except NoSuchElementException:
                if self.debug:
                    logger.debug(f"Strategy failed: {strategy}")
                continue

        return None

    def find_search_button(self):
        """Find search button using multiple strategies."""
        for strategy in UofTLocators.SEARCH_BUTTON_STRATEGIES:
            try:
                element = self.driver.find_element(*strategy)
                if element.is_displayed() and element.is_enabled():
                    logger.info(f"Found search button using strategy: {strategy}")
                    return element
            except NoSuchElementException:
                if self.debug:
                    logger.debug(f"Button strategy failed: {strategy}")
                continue

        return None

    def search_courses(self, course_code="", title="", department="", level="", credits="", limit=100):
        """Enhanced course search with improved error handling."""
        if not self.driver:
            logger.error("WebDriver not available")
            return []

        try:
            logger.info(f"Starting course search for: {course_code or title or department}")

            # Navigate to search page
            self.driver.get(self.search_url)
            if not self.wait_for_page_load():
                logger.error("Failed to load search page")
                return []

            # Debug: Print page title to verify we're on the right page
            if self.debug:
                logger.info(f"Page title: {self.driver.title}")
                logger.info(f"Current URL: {self.driver.current_url}")

            # Find search input
            search_input = self.find_search_input()
            if not search_input:
                # Debug: Print available inputs
                if self.debug:
                    inputs = self.driver.find_elements(By.TAG_NAME, "input")
                    logger.info("Available input elements:")
                    for i, inp in enumerate(inputs):
                        try:
                            name = inp.get_attribute("name") or "None"
                            id_attr = inp.get_attribute("id") or "None"
                            type_attr = inp.get_attribute("type") or "None"
                            placeholder = inp.get_attribute("placeholder") or "None"
                            logger.info(f"  Input {i}: name='{name}', id='{id_attr}', type='{type_attr}', placeholder='{placeholder}'")
                        except Exception:
                            pass

                raise Exception("Could not find search input field")

            # Determine search term
            search_term = course_code or title or department
            if not search_term:
                logger.warning("No search term provided")
                return []

            # Perform search
            logger.info(f"Searching for: {search_term}")
            search_input.clear()
            search_input.send_keys(search_term)

            # Try to submit via Enter key first
            try:
                search_input.send_keys(Keys.RETURN)
                logger.info("Submitted search via Enter key")
            except Exception:
                # Fallback to search button
                search_button = self.find_search_button()
                if search_button:
                    search_button.click()
                    logger.info("Submitted search via button click")
                else:
                    logger.error("Could not find search button")
                    return []

            # Wait for results
            if not self.wait_for_search_results():
                logger.warning("No search results found or results failed to load")

                # Debug: Check what's on the page
                if self.debug:
                    page_text = self.driver.find_element(By.TAG_NAME, "body").text[:500]
                    logger.info(f"Page content preview: {page_text}")

                return []

            # Parse results
            return self.parse_search_results(limit)

        except Exception as e:
            logger.error(f"Course search failed: {e}")
            if self.debug:
                logger.error(f"Exception details: {str(e)}")
            return []

    def parse_search_results(self, limit=100):
        """Parse search results with enhanced extraction."""
        results = []

        try:
            # Try different result item strategies
            result_elements = []
            for strategy in UofTLocators.COURSE_RESULT_ITEMS:
                try:
                    elements = self.driver.find_elements(*strategy)
                    if elements:
                        logger.info(f"Found {len(elements)} result elements using {strategy}")
                        result_elements = elements
                        break
                except Exception:
                    continue

            if not result_elements:
                logger.warning("No result elements found")
                return []

            logger.info(f"Processing {len(result_elements)} course results")

            for i, element in enumerate(result_elements[:limit]):
                try:
                    course_data = self.extract_course_from_element(element)
                    if course_data:
                        results.append(course_data)
                        if self.debug:
                            logger.info(f"Extracted course {i+1}: {course_data.get('course_code', 'Unknown')}")

                except Exception as e:
                    if self.debug:
                        logger.error(f"Failed to extract course {i+1}: {e}")
                    continue

            logger.info(f"Successfully extracted {len(results)} courses")
            return results

        except Exception as e:
            logger.error(f"Failed to parse search results: {e}")
            return []

    def extract_course_from_element(self, element):
        """Extract course information from a result element."""
        try:
            course_data = {
                'course_code': '',
                'title': '',
                'url': '',
                'description': '',
                'credits': 0.5,
                'prerequisites': '',
                'exclusions': '',
                'breadth_requirements': ''
            }

            # Extract course title and code
            title_element = None
            for strategy in UofTLocators.COURSE_TITLE_IN_RESULT:
                try:
                    title_element = element.find_element(*strategy)
                    break
                except NoSuchElementException:
                    continue

            if not title_element:
                # Fallback: try to get any text from the element
                text_content = element.text.strip()
                if text_content:
                    title_element = element
                else:
                    return None

            # Get text content
            if hasattr(title_element, 'text'):
                title_text = title_element.text.strip()
            else:
                title_text = str(title_element).strip()

            if not title_text:
                return None

            # Extract course code using improved regex
            course_code_patterns = [
                r'([A-Z]{3}\d{3}[HY]\d)',  # Standard format: CSC108H1
                r'([A-Z]{2,4}\d{3}[A-Z]\d)',  # Alternative formats
                r'([A-Z]{3}\d{3})',  # Just the base code
            ]

            extracted_code = ''
            for pattern in course_code_patterns:
                match = re.search(pattern, title_text)
                if match:
                    extracted_code = match.group(1)
                    break

            if not extracted_code:
                # Try to extract from the beginning of the text
                words = title_text.split()
                if words and re.match(r'[A-Z]{3}\d{3}', words[0]):
                    extracted_code = words[0]

            course_data['course_code'] = extracted_code
            course_data['title'] = title_text

            # Build course URL
            if extracted_code:
                course_data['url'] = f"{self.base_url}/course/{extracted_code.lower()}"

            # Extract description (text after course code and title)
            if ' - ' in title_text:
                parts = title_text.split(' - ', 1)
                if len(parts) > 1:
                    course_data['description'] = parts[1].strip()

            # Extract credits from course code
            if 'H1' in extracted_code or 'H5' in extracted_code:
                course_data['credits'] = 0.5
            elif 'Y1' in extracted_code or 'Y5' in extracted_code:
                course_data['credits'] = 1.0

            # Try to extract additional details if available
            try:
                # Look for prerequisite information in the element
                full_text = element.text if hasattr(element, 'text') else str(element)
                if 'prerequisite' in full_text.lower():
                    prereq_match = re.search(r'prerequisite[s]?:?\s*([^.]+)', full_text, re.IGNORECASE)
                    if prereq_match:
                        course_data['prerequisites'] = prereq_match.group(1).strip()
            except Exception:
                pass

            return course_data if extracted_code else None

        except Exception as e:
            if self.debug:
                logger.error(f"Failed to extract course from element: {e}")
            return None

    def get_course_details(self, course_code):
        """Get detailed course information from course page."""
        try:
            course_url = f"{self.base_url}/course/{course_code.lower()}"
            logger.info(f"Fetching details for {course_code} from {course_url}")

            self.driver.get(course_url)
            if not self.wait_for_page_load():
                return None

            # Extract detailed information
            course_details = {
                'course_code': course_code,
                'title': '',
                'description': '',
                'credits': 0.5,
                'prerequisites': '',
                'corequisites': '',
                'exclusions': '',
                'breadth_requirements': '',
                'hours': '',
                'department': ''
            }

            # Extract title
            try:
                title_element = self.driver.find_element(By.TAG_NAME, "h1")
                course_details['title'] = title_element.text.strip()
            except NoSuchElementException:
                pass

            # Extract description
            try:
                desc_selectors = [
                    ".course-description",
                    ".field-name-body",
                    ".course-content"
                ]
                for selector in desc_selectors:
                    try:
                        desc_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        course_details['description'] = desc_element.text.strip()
                        break
                    except NoSuchElementException:
                        continue
            except Exception:
                pass

            # Extract prerequisites, exclusions, etc.
            page_text = self.driver.find_element(By.TAG_NAME, "body").text

            # Prerequisites
            prereq_match = re.search(r'prerequisite[s]?:?\s*([^.]+)', page_text, re.IGNORECASE)
            if prereq_match:
                course_details['prerequisites'] = prereq_match.group(1).strip()

            # Exclusions
            excl_match = re.search(r'exclusion[s]?:?\s*([^.]+)', page_text, re.IGNORECASE)
            if excl_match:
                course_details['exclusions'] = excl_match.group(1).strip()

            # Breadth requirements
            breadth_match = re.search(r'breadth.{0,20}requirement[s]?:?\s*([^.]+)', page_text, re.IGNORECASE)
            if breadth_match:
                course_details['breadth_requirements'] = breadth_match.group(1).strip()

            return course_details

        except Exception as e:
            logger.error(f"Failed to get course details for {course_code}: {e}")
            return None

    def __del__(self):
        """Cleanup on object destruction."""
        self.close_driver()