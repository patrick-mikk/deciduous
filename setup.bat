@echo off
title UofT Transcript Analyzer - Setup
color 0A
echo ================================================================
echo    UofT Academic Transcript Analyzer v2.0 - Windows Setup
echo ================================================================
echo.

echo Checking system requirements...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not found in PATH.
    echo.
    echo Please install Python 3.7+ from: https://python.org/downloads/
    echo.
    echo IMPORTANT: During installation, make sure to:
    echo  1. Check "Add Python to PATH"
    echo  2. Choose "Install for all users" (recommended)
    echo.
    echo After installing Python, run this setup again.
    echo.
    pause
    exit /b 1
) else (
    echo [OK] Python is installed
    python --version
)

echo.
echo Checking Python version...
python -c "import sys; exit(0 if sys.version_info >= (3,7) else 1)" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3.7+ is required.
    echo Please update your Python installation.
    pause
    exit /b 1
) else (
    echo [OK] Python version is compatible
)

echo.
echo Checking required files...

if not exist "uoft_transcript_analyzer.py" (
    echo [ERROR] uoft_transcript_analyzer.py not found in current directory.
    echo Please ensure all files are in the same folder.
    pause
    exit /b 1
) else (
    echo [OK] Main application file found
)

if not exist "run_analyzer.bat" (
    echo [WARNING] run_analyzer.bat not found. Creating launcher...
    echo @echo off > run_analyzer.bat
    echo title UofT Transcript Analyzer >> run_analyzer.bat
    echo python uoft_transcript_analyzer.py >> run_analyzer.bat
    echo pause >> run_analyzer.bat
) else (
    echo [OK] Launcher script found
)

echo.
echo Creating desktop shortcut...

REM Create a VBS script to create desktop shortcut
echo Set oWS = WScript.CreateObject("WScript.Shell") > create_shortcut.vbs
echo sLinkFile = oWS.SpecialFolders("Desktop") ^& "\UofT Transcript Analyzer.lnk" >> create_shortcut.vbs
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> create_shortcut.vbs
echo oLink.TargetPath = "%CD%\run_analyzer.bat" >> create_shortcut.vbs
echo oLink.WorkingDirectory = "%CD%" >> create_shortcut.vbs
echo oLink.Description = "UofT Academic Transcript Analyzer" >> create_shortcut.vbs
echo oLink.IconLocation = "shell32.dll,21" >> create_shortcut.vbs
echo oLink.Save >> create_shortcut.vbs

cscript //nologo create_shortcut.vbs >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Could not create desktop shortcut
) else (
    echo [OK] Desktop shortcut created
)

del create_shortcut.vbs >nul 2>&1

echo.
echo Testing application startup...
timeout /t 2 /nobreak >nul

REM Test if the application can import required modules
python -c "import tkinter; import csv; import json; import datetime; import collections; import os; print('[OK] All required modules available')" 2>nul
if errorlevel 1 (
    echo [ERROR] Some required Python modules are missing.
    echo This might indicate a problem with your Python installation.
    pause
    exit /b 1
)

echo.
echo ================================================================
echo                           SETUP COMPLETE!
echo ================================================================
echo.
echo Your UofT Transcript Analyzer is ready to use!
echo.
echo To start the application:
echo  1. Double-click "UofT Transcript Analyzer" on your desktop
echo  2. OR double-click "run_analyzer.bat" in this folder
echo  3. OR run: python uoft_transcript_analyzer.py
echo.
echo Features available:
echo  * Accurate UofT GPA calculations
echo  * Full special notations support (CR/NCR, LWD, IPR, etc.)
echo  * Future course simulation and planning
echo  * Academic performance analytics
echo  * CSV import/export
echo  * Session save/load
echo.
echo The application includes sample data for testing.
echo Check the README.md file for detailed usage instructions.
echo.
echo Press any key to launch the application now...
pause >nul

echo.
echo Starting UofT Transcript Analyzer...
python uoft_transcript_analyzer.py

echo.
echo Thanks for using UofT Transcript Analyzer!
pause
