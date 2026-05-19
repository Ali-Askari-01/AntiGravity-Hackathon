@echo off
title Antigravity — Backend + Frontend
chcp 65001 >nul

echo ========================================================
echo        ^🚀 Starting Antigravity Hackathon App ^🚀
echo ========================================================
echo.

:: ── Make sure we run from the project root ──────────────────
cd /d "%~dp0"

:: ── Check that backend venv exists ───────────────────────
if not exist "backend\venv\Scripts\uvicorn.exe" (
    echo [ERROR] Backend venv not found or uvicorn missing.
    echo Please run: cd backend ^&^& python -m venv venv ^&^& venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

:: ── Open frontend in browser ─────────────────────────────────
echo [1/2] Opening frontend in browser (will open in a few seconds)...
start "" cmd /c "timeout /t 3 >nul && start http://localhost:8000"

:: ── Start backend with correct venv and module path ─────────
echo [2/2] Starting Backend on http://localhost:8000 ...
echo        (Use Ctrl+C to stop)
echo.
backend\venv\Scripts\uvicorn.exe backend.main:app --reload --host 0.0.0.0 --port 8000

pause
