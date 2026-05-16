@echo off
title Antigravity Setup and Runner

echo ========================================================
echo        🚀 Starting Antigravity Hackathon App 🚀
echo ========================================================
echo.

echo [1/3] Checking backend virtual environment...
cd backend
if not exist "venv\Scripts\activate.bat" (
    echo Creating virtual environment...
    python -m venv venv
)
call venv\Scripts\activate.bat

echo [2/3] Installing dependencies...
pip install -r requirements.txt >nul 2>&1

echo [3/3] Starting Backend Server...
echo The backend is running on http://127.0.0.1:8000
echo.

:: Open frontend in default browser
cd ../frontend
start index.html

:: Start Uvicorn
cd ../backend
uvicorn main:app --reload

pause
