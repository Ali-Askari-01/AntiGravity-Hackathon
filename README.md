# 🚀 Antigravity

**Your Local Experts. Instantly.**

Antigravity is a next-generation AI-powered service booking platform built for Pakistan. It abstracts away the complexity of finding, negotiating, and scheduling local service professionals (Plumbers, Electricians, Cleaners, etc.) by utilizing a fully autonomous **Multi-Agent Pipeline** powered by the **Google Agent Development Kit (ADK)**.

---

## ✨ Features

- **🗣️ Multilingual NLP:** Talk in English, Urdu, or Roman Urdu ("Mere AC se pani tapak raha hai"). Our Intent Agent (Zuban) understands context and urgency.
- **🤖 Autonomous Multi-Agent Orchestration:** 8 specialized AI agents handle the entire booking lifecycle autonomously—from matching and dynamic pricing to dispute resolution.
- **📍 Real-time Tracking:** Live provider tracking with native Google Maps integration.
- **⚡ Dynamic Pricing & Scheduling:** Fair, transparent pricing using 7 data points (distance, urgency, peak hours) and intelligent conflict-free scheduling.

## 🏗️ Architecture

Antigravity uses a robust pipeline of specialized ADK `LlmAgent`s orchestrated by a Master Agent.

1. **Munsif (Orchestrator):** Manages the session state and delegates tasks sequentially.
2. **Zuban (Intent):** Extracts service type, location, urgency, and language.
3. **Khoji (Matching):** Queries SQLite and applies a 6-factor algorithm to find the best provider.
4. **Jadwal (Scheduling):** Checks provider calendars, prevents double-booking, and suggests alternatives.
5. **Qeemat (Pricing):** Calculates transparent, dynamic pricing.
6. **Meezan/Hukum (Booking):** Executes the booking and generates receipts.
7. **Mayaar (Quality):** Manages post-service feedback loops.
8. **Insaf (Dispute):** Handles user complaints and automatically penalizes providers if necessary.

## 🛠️ Tech Stack

- **Frontend:** HTML, CSS (Vanilla Custom UI), JavaScript, Google Maps JS API.
- **Backend:** Python, FastAPI, SQLite.
- **AI/LLM Engine:** Google Agent Development Kit (ADK), routing through **OpenRouter** (`openrouter/google/gemini-2.5-flash`).

---

## 🚀 How to Run Locally (Windows)

We have provided a convenient batch script that automatically sets up the backend, installs dependencies, and serves the frontend.

### Prerequisites
- Python 3.9+
- An `.env` file in the `backend/` directory with the following keys:
  ```env
  GEMINI_API_KEY=your_key_here
  GOOGLE_MAPS_API_KEY=your_key_here
  OPENROUTER_API_KEY=your_key_here
  ```

### Quick Start
1. Clone the repository.
2. Double-click the `run_windows.bat` file in the root directory.
3. The script will automatically:
   - Create a virtual environment (`venv`).
   - Install Python dependencies from `backend/requirements.txt`.
   - Start the FastAPI backend on `http://127.0.0.1:8000`.
   - Open your default web browser to the frontend interface.

### Manual Start (Alternative)
**Terminal 1 (Backend):**
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

**Terminal 2 (Frontend):**
Open `frontend/index.html` in your browser or use a live server extension in VSCode.

---

## 💾 Database Seeding
The project comes with a pre-populated SQLite database (`antigravity.db`) containing mock service providers across Karachi areas (DHA, Gulshan, Clifton, etc.) with precise coordinates and their schedules. To re-seed or wipe the database, run:
```bash
cd backend
python seed_providers.py
```
