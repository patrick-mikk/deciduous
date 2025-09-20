# Quick Setup Guide - UofT Course Search Tool

## Prerequisites

Before running the application, ensure you have:

1. **Python 3.7 or higher** installed
   - Download from: https://www.python.org/downloads/
   - During installation, check "Add Python to PATH"

2. **Google Chrome browser** installed
   - Download from: https://www.google.com/chrome/
   - The application uses Chrome WebDriver (automatically managed)

## Installation Steps

### 1. Download the Application

Clone or download the repository to your local machine:
```bash
git clone <repository-url>
cd Course-Dashboard/academic_cal
```

Or download and extract the ZIP file to a folder of your choice.

### 2. Install Python Dependencies

Open Command Prompt or Terminal in the application folder and run:

```bash
pip install selenium webdriver-manager beautifulsoup4
```

**Note:** If you get permission errors, try:
```bash
pip install --user selenium webdriver-manager beautifulsoup4
```

### 3. Verify Installation

Test that all dependencies are properly installed:

```bash
python -c "import selenium, webdriver_manager, bs4; print('All dependencies installed successfully!')"
```

## Running the Application

### Method 1: Double-click (Windows)
- Navigate to the `academic_cal` folder
- Double-click `course_search.py`

### Method 2: Command Line
```bash
cd path/to/Course-Dashboard/academic_cal
python course_search.py
```

### Method 3: From IDE
- Open `course_search.py` in your preferred Python IDE
- Run the file

## First-Time Usage

1. **Launch the application** - The GUI window will open
2. **Test the search** - Try searching for "CSC148"
3. **Extract course details** - Select a course and click "Extract Course Details"
4. **Check the database** - Click "View All Saved Courses" to see stored data

## Expected Behavior

### Successful Launch
- GUI window opens with title "UofT Academic Calendar Course Search"
- Status bar shows "Ready"
- No error messages appear

### During Search
- Status changes to "Searching..."
- Chrome browser starts in background (you might see some console messages)
- Results appear in the list box
- Status updates with result count

### During Detail Extraction
- Status changes to "Extracting course details..."
- Course information appears in the text area
- Course is automatically saved to database
- Status confirms successful extraction

## Troubleshooting

### Common Issues and Solutions

#### "ModuleNotFoundError: No module named 'selenium'"
**Solution:** Install the missing dependencies:
```bash
pip install selenium webdriver-manager beautifulsoup4
```

#### "WebDriver executable not found"
**Solution:** This shouldn't happen with webdriver-manager, but if it does:
1. Ensure Chrome browser is installed
2. Check your internet connection (webdriver-manager downloads ChromeDriver)

#### GUI doesn't appear / "ModuleNotFoundError: No module named 'tkinter'"
**Solution:**
- **Windows:** Reinstall Python and ensure "tcl/tk and IDLE" is checked
- **Linux:** Install tkinter: `sudo apt-get install python3-tk`
- **Mac:** tkinter is usually included with Python

#### "Permission denied" errors
**Solution:**
1. Run command prompt as administrator (Windows)
2. Use `--user` flag: `pip install --user selenium webdriver-manager beautifulsoup4`

#### Search returns no results
**Solution:**
1. Check your internet connection
2. Try a different course code (e.g., "CSC108", "MAT137")
3. Verify the UofT website is accessible in your browser

#### Application freezes during search
**Solution:**
1. Wait 10-15 seconds (normal for first search)
2. Check your internet connection
3. Restart the application if it doesn't respond

## Performance Notes

- **First search** may take 10-15 seconds (Chrome WebDriver initialization)
- **Subsequent searches** typically take 3-5 seconds
- **Detail extraction** takes 2-3 seconds per course
- **Database operations** are near-instantaneous

## File Structure After Setup

```
academic_cal/
├── course_search.py          # Main application file
├── courses.db               # SQLite database (created automatically)
├── README.md                # User documentation
├── SETUP_GUIDE.md           # This file
├── TECHNICAL_DOCS.md        # Developer documentation
└── API_REFERENCE.md         # API documentation
```

## System Requirements

- **Operating System:** Windows 10/11, macOS 10.12+, or Linux
- **Python:** 3.7 or higher
- **RAM:** 512MB minimum (200MB for Chrome, 300MB for Python)
- **Storage:** 50MB for application + variable for database
- **Internet:** Required for web scraping

## Getting Help

If you encounter issues:

1. **Check this guide** for common solutions
2. **Review the error message** carefully
3. **Test with simple inputs** like "CSC108"
4. **Verify dependencies** are properly installed
5. **Check internet connectivity**

## Configuration Options

### Running in Visible Mode (for debugging)

To see the Chrome browser in action:
1. Open `course_search.py` in a text editor
2. Find the line: `chrome_options.add_argument("--headless")`
3. Add `#` at the beginning: `# chrome_options.add_argument("--headless")`
4. Save and run the application

### Changing Database Location

To use a different database file:
1. Open `course_search.py`
2. Find: `self.database = CourseDatabase()`
3. Change to: `self.database = CourseDatabase("path/to/your/database.db")`

## Next Steps

Once the application is running successfully:

1. **Explore different searches** - Try various course codes and keywords
2. **Build your course database** - Extract details for courses you're interested in
3. **Review saved courses** - Use "View All Saved Courses" to see your collection
4. **Read the full documentation** - Check `README.md` for detailed usage instructions

## Support

For additional help:
- Review the full `README.md` for detailed usage instructions
- Check `TECHNICAL_DOCS.md` for implementation details
- Consult `API_REFERENCE.md` for programming interface documentation

The application is designed to be user-friendly and should work out of the box with minimal setup. Happy course searching!