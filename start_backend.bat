@echo off
cd /d "C:\Users\SIKANDAR\Desktop\antigravity hackathon"
venv\Scripts\python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
