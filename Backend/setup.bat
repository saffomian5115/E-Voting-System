@echo off
echo ============================================
echo   E-Voting System — Module 1 Setup Script
echo ============================================

cd /d "%~dp0"

echo.
echo [1/3] Virtual environment bana raha hoon...
python -m venv venv
if errorlevel 1 (
    echo [ERROR] Python nahi mila. Python 3.10+ install karein.
    pause
    exit /b 1
)

echo.
echo [2/3] Dependencies install kar raha hoon...
call venv\Scripts\activate
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] pip install fail hua.
    pause
    exit /b 1
)

echo.
echo [3/3] BWAPI test kar raha hoon...
python test_bwapi.py

echo.
echo ============================================
echo   Setup complete! Ab chalao:
echo   call venv\Scripts\activate
echo   python app.py
echo ============================================
pause