@echo off
title Antigravity — Backend + Frontend
chcp 65001 >nul

echo ========================================================
echo        ^🚀 Starting Antigravity Hackathon App ^🚀
echo ========================================================
echo.

:: ── Make sure we run from the project root ──────────────────
cd /d "%~dp0"

:: ── Check that root-level venv exists ───────────────────────
if not exist "venv\Scripts\uvicorn.exe" (
    echo [ERROR] Root venv not found or uvicorn missing.
    echo Please run: python -m venv venv ^&^& venv\Scripts\pip install -r backend\requirements.txt
    pause
    exit /b 1
)

:: ── Open frontend in browser ─────────────────────────────────
echo [1/2] Opening frontend in browser...
start "" "%~dp0frontend\index.html"

:: ── Start backend with correct venv and module path ─────────
echo [2/2] Starting Backend on http://127.0.0.1:8000 ...
echo        (Use Ctrl+C to stop)
echo.
venv\Scripts\uvicorn.exe backend.main:app --reload --host 127.0.0.1 --port 8000

pause
