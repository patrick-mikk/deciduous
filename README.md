# UofT Academic Transcript Analyzer v2.0
## Windows Desktop Application

### 📋 Overview
A comprehensive desktop application for University of Toronto students to analyze academic transcripts, calculate GPAs, and simulate future academic scenarios with full support for UofT's special notations system.

---

## 🚀 Quick Start

### Prerequisites
- **Windows 10/11** (or Windows 7+ with Python support)
- **Python 3.7 or higher** installed

### Installation Steps

1. **Download Python** (if not already installed):
   - Go to https://python.org/downloads/
   - Download Python 3.7+ for Windows
   - **IMPORTANT**: Check "Add Python to PATH" during installation

2. **Download Application Files**:
   - Save `uoft_transcript_analyzer.py` to a folder (e.g., `C:\UofT_Analyzer\`)
   - Save `run_analyzer.bat` to the same folder

3. **Launch the Application**:
   - Double-click `run_analyzer.bat` to start the application
   - OR open Command Prompt, navigate to the folder, and run: `python uoft_transcript_analyzer.py`

---

## 📊 Features

### ✅ Core Functionality
- **Accurate GPA Calculations** using official UofT grade scale
- **Complete Special Notations Support**: CR/NCR, LWD, IPR, AEG, SDF, and more
- **Sessional & Cumulative GPAs** with detailed breakdowns
- **Academic Standing** determination (Dean's List, Good Standing, Probation)

### 🎯 Advanced Simulation
- **Future Course Planning** with grade projections
- **Special Notation Simulation** (simulate taking courses CR/NCR)
- **Goal Calculator** - determine grades needed for target GPA
- **"What-If" Scenarios** for academic planning

### 📈 Analytics & Insights
- **Subject Performance Analysis** by department (ECO, CSC, MUN, etc.)
- **Grade Distribution** statistics
- **Sessional Trends** tracking
- **Personalized Recommendations** for improvement

### 💾 Data Management
- **CSV Import/Export** for transcript data
- **Session Save/Load** to preserve work
- **Data Validation** ensures accuracy
- **Sample Data** included for testing

---

## 🎓 UofT Grade Scale & Notations

### Letter Grades (Count Toward GPA)
```
A+, A  = 4.0    |    B+ = 3.3    |    C+ = 2.3    |    D+ = 1.3
A-     = 3.7    |    B  = 3.0    |    C  = 2.0    |    D  = 1.0
                |    B- = 2.7    |    C- = 1.7    |    D- = 0.7
                |                |                |    F  = 0.0
```

### Special Notations (Handled Correctly)
- **CR/NCR**: Credit/No Credit - Excluded from GPA
- **NC%**: No Credit - Counted as 0.0 in GPA
- **IPR**: In Progress - Excluded from calculations
- **LWD/WDR**: Late Withdrawal/Withdrawn - Excluded
- **AEG**: Aegrotat Standing - Credit granted
- **SDF**: Standing Deferred - Excluded
- **DNW**: Did Not Write - Excluded
- **EXT/ADD**: Extra/Additional Course - Excluded
- **GWR/INC**: Grade Withheld/Incomplete - Excluded
- **NGA**: No Grade Available - Excluded
- **XMP**: Exemption Granted - Excluded

---

## 🖥️ User Interface Guide

### Tab Navigation
1. **Overview**: Dashboard with key statistics and sessional GPAs
2. **Transcript**: View, edit, add, and manage all courses
3. **GPA Simulator**: Plan future courses and see projected results
4. **Analytics**: Detailed performance analysis and recommendations
5. **Data Management**: Import/export data and manage sessions

### Key Operations

#### Adding Courses
1. Go to **Transcript** tab
2. Click **"Add Course"**
3. Fill in course details:
   - Term/Year (Fall 2025, Winter 2024, etc.)
   - Course Code (e.g., ECO101H1)
   - Course Title
   - Weight (0.5 or 1.0 FCE)
   - Mark (if available)
   - Grade OR Special Notation (not both)

#### Simulation Planning
1. Go to **GPA Simulator** tab
2. Click **"Add Course"** to add future courses
3. Set expected grades or special notations
4. View projected GPA and changes in real-time
5. Use **Goal Calculator** to determine required grades

#### Importing Transcript Data
1. Go to **Data Management** tab
2. Click **"Import CSV Transcript"**
3. Select your CSV file with columns:
   ```
   Term, Year, Course_Code, Course_Title, Weight, Mark, Grade
   ```
4. Application will automatically handle special notations

---

## 📁 File Formats

### CSV Import Format
```csv
Term,Year,Course_Code,Course_Title,Weight,Mark,Grade
Fall,2023,ECO101H1,Principles of Microeconomics,0.5,75,B
Winter,2024,CSC108H1,Intro to Computer Programming,0.5,,CR
Fall,2024,MUN101H1,Global Innovation,0.5,,IPR
```

### Session Files
- Saved as JSON files with `.json` extension
- Contains both transcript and simulation data
- Can be shared between users or backed up

---

## 🎯 Use Cases & Examples

### Academic Planning
- **Scenario**: "I want to reach 3.5 GPA for grad school"
- **Solution**: Use Goal Calculator to see required grades in remaining courses

### Course Selection Strategy
- **Scenario**: "Should I take ECO102 CR/NCR?"
- **Solution**: Simulate both scenarios (letter grade vs. CR/NCR) to compare GPA impact

### Performance Analysis
- **Scenario**: "Which subjects are my strengths/weaknesses?"
- **Solution**: Check Analytics tab for subject-by-subject breakdown

### Retake Planning
- **Scenario**: "Will retaking ECO101 improve my GPA significantly?"
- **Solution**: Simulate different retake grades to see potential improvement

---

## 🔧 Troubleshooting

### Common Issues

**Application won't start:**
- Ensure Python 3.7+ is installed
- Check that Python is added to PATH
- Try running from Command Prompt: `python uoft_transcript_analyzer.py`

**Import CSV fails:**
- Check CSV format matches expected columns
- Ensure file is saved as UTF-8 encoding
- Verify no special characters in course codes

**GPA calculations seem wrong:**
- Verify special notations are correctly assigned
- Check that CR/NCR courses are properly marked
- Ensure weight values are correct (0.5 or 1.0)

### Getting Help
- Sample data is pre-loaded for testing
- Data Management tab contains reference information
- All calculations follow official UofT guidelines

---

## 🔒 Privacy & Security
- **Local Processing**: All data stays on your computer
- **No Internet Required**: Fully offline application
- **No Data Collection**: No personal information sent anywhere
- **Secure Storage**: Session files saved locally only

---

## 📱 System Requirements

### Minimum Requirements
- Windows 7 or later
- Python 3.7+
- 50 MB free disk space
- 512 MB RAM

### Recommended
- Windows 10/11
- Python 3.9+
- 100 MB free disk space
- 1 GB RAM

---

## 🆕 Version History

### v2.0 (Current)
- Full special notations support
- Advanced simulation capabilities
- Subject performance analysis
- Goal calculator
- Session save/load
- Improved data validation

### Features Added
- CR/NCR simulation
- LWD/IPR handling
- Multi-notation support
- Enhanced analytics
- Professional Windows interface

---

## 📞 Support

For technical issues:
1. Check troubleshooting section above
2. Verify Python installation
3. Ensure all files are in same folder
4. Try running with administrator privileges if needed

This application is designed specifically for University of Toronto students and follows all official UofT academic regulations and grade scale guidelines.

**Happy Academic Planning! 🎓**
