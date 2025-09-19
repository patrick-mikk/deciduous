# UofT Academic Calendar Course Search Tool

A Python application that searches and extracts course information from the University of Toronto Academic Calendar website.

## Features

- **Course Search**: Search for courses by course code on the UofT Academic Calendar
- **Results Display**: View search results with course titles and descriptions
- **Detailed Extraction**: Extract comprehensive course information including:
  - Course title and code
  - Credit hours
  - Course description
  - Prerequisites
  - Exclusions
  - Breadth requirements
- **Database Storage**: Save course information to a local SQLite database
- **Clean Dashboard**: User-friendly GUI for browsing and managing course data

## Installation

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python course_search.py
```

## Usage

### Step 1: Search for a Course
1. Enter a course code (e.g., "POL208", "GGR273") in the search field
2. Click the "Search" button or press Enter
3. The application will search the Academic Calendar and display results

### Step 2: Review Search Results
- Search results will appear in the results list box
- Each result shows the full course title
- Select a course from the list to extract detailed information

### Step 3: Extract Course Details
1. Select a course from the search results
2. Click "Extract Course Details"
3. The application will:
   - Navigate to the course page
   - Extract all course information
   - Display the details in the dashboard
   - Save the course to the database

### Step 4: View Course Information
The extracted course information includes:
- **Course Title**: Full course name
- **Course Code**: Official course code
- **Hours**: Credit hours (e.g., "24L/24P")
- **Description**: Detailed course description
- **Prerequisites**: Required prerequisite courses
- **Exclusions**: Courses that cannot be taken with this course
- **Breadth Requirements**: University breadth requirement categories

### Step 5: Database Management
- All extracted courses are automatically saved to a local SQLite database
- Click "View All Saved Courses" to see previously extracted courses
- The database persists between application sessions

## Technical Details

### Components

1. **AcademicCalendarScraper**: Handles web scraping from the UofT Academic Calendar
2. **CourseDatabase**: Manages SQLite database operations
3. **CourseSearchGUI**: Provides the tkinter-based user interface

### Web Scraping Elements

The application uses the following CSS selectors based on the Academic Calendar website structure:

- **Search Input**: `#edit-course-title`
- **Search Submit**: `#edit-submit-search-courses-block`
- **Results**: `.view-content h3 a h6`
- **Course Title**: `#block-w3css-subtheme-page-title h1`
- **Hours**: `.field--name-field-hours .field__item p`
- **Description**: `.field--name-body.field--type-text-with-summary`
- **Prerequisites**: `.field--name-field-prerequisite .field__item`
- **Exclusions**: `.field--name-field-exclusion .field__item`
- **Breadth Requirements**: `.field--name-field-breadth-requirements .field__items`

### Database Schema

The SQLite database contains a `courses` table with the following columns:
- `id`: Primary key
- `course_code`: Course code (unique)
- `title`: Full course title
- `hours`: Credit hours
- `description`: Course description
- `prerequisites`: Prerequisites text
- `exclusions`: Exclusions text
- `breadth_requirements`: Breadth requirements
- `url`: Source URL
- `created_at`: Timestamp

## Files

- `course_search.py`: Main application script
- `requirements.txt`: Python dependencies
- `courses.db`: SQLite database (created automatically)
- `academic_cal/`: Directory containing reference files
  - `info.md`: Element selectors and website structure information
  - `2025-26 Academic Calendar _ Academic Calendar.html`: Reference HTML file

## Error Handling

The application includes comprehensive error handling for:
- Network connectivity issues
- Invalid course codes
- Missing course information
- Database operations
- Website structure changes

## Notes

- The application respects the website's structure and includes appropriate delays
- All course data is stored locally and not transmitted elsewhere
- The GUI is built with tkinter for cross-platform compatibility
- The scraper uses session management for efficient web requests