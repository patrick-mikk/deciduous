@echo off
title UofT Transcript Analyzer v3.0 - Enhanced Edition
echo.
echo ================================================
echo  UofT Academic Transcript Analyzer v3.0
echo  Enhanced Edition for Windows
echo ================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH.
    echo.
    echo Please install Python 3.7+ from https://python.org
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    echo After installing Python, run this script again.
    pause
    exit /b 1
)

echo Python found. Starting UofT Transcript Analyzer...
echo.

REM Check if enhanced dependencies are available
python -c "import matplotlib" >nul 2>&1
if errorlevel 1 (
    echo Note: Enhanced features not available.
    echo Run 'install_deps.bat' to install optional dependencies for:
    echo   - Charts and data visualization
    echo   - Excel and PDF export
    echo.
)

REM Run the application
python uoft_transcript_analyzer.py

REM Keep window open if there's an error
if errorlevel 1 (
    echo.
    echo ==============================================
    echo  An error occurred while running the app
    echo ==============================================
    echo.
    echo This might be due to:
    echo   1. Missing Python dependencies
    echo   2. Corrupted data files
    echo   3. Permission issues
    echo.
    echo Try running 'install_deps.bat' first.
    echo If the problem persists, check the error message above.
    echo.
    pause
)
