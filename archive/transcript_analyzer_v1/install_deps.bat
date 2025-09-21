@echo off
title UofT Transcript Analyzer - Install Dependencies
echo Installing Enhanced Features for UofT Transcript Analyzer v3.0
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH.
    echo Please install Python 3.7+ from https://python.org
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo Python found. Installing optional dependencies...
echo.

REM Install optional dependencies
echo Installing matplotlib for charts and graphs...
pip install matplotlib>=3.5.0 numpy>=1.20.0

echo.
echo Installing openpyxl for Excel export...
pip install openpyxl>=3.0.9

echo.
echo Installing reportlab for PDF export...
pip install reportlab>=3.6.0

echo.
echo Dependencies installation completed!
echo.
echo You can now enjoy all enhanced features:
echo - Data visualization with charts and graphs
echo - Export to Excel format (.xlsx)
echo - Export to PDF format (.pdf)
echo.
echo If any installation failed, you can still use the basic features.
echo The application will gracefully handle missing dependencies.
echo.
pause