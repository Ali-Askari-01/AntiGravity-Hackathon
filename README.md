# 🚀 Antigravity

**Your Local Experts. Instantly.**

Antigravity is a next-generation AI-powered service booking platform built for Pakistan. It abstracts away the complexity of finding, negotiating, and scheduling local service professionals (Plumbers, Electricians, Cleaners, etc.) by utilizing a fully autonomous **Multi-Agent Pipeline** powered by the **Google Agent Development Kit (ADK)**.

---

## ✨ Features

- **🔐 Secure Authentication:** Email/password login with token-based auth and 24-hour session expiry.
- **🗣️ Multilingual NLP:** Talk in English, Urdu, or Roman Urdu ("Mere AC se pani tapak raha hai"). Our Intent Agent (Zuban) understands context and urgency.
- **🤖 Autonomous Multi-Agent Orchestration:** 8 specialized AI agents handle the entire booking lifecycle autonomously—from matching and dynamic pricing to dispute resolution.
- **📍 Real-time Tracking:** Live provider tracking with native Google Maps integration and WebSocket updates.
- **⚡ Dynamic Pricing & Scheduling:** Fair, transparent pricing using 7 data points (distance, urgency, peak hours) and intelligent conflict-free scheduling.
- ** Smart Intent Recognition:** AI-powered service detection from natural language prompts (e.g., "pani ki tanki leak" → Plumber, "bijli ka kaam" → Electrician).
- **📊 Provider Ranking:** 6-factor scoring algorithm considering distance, rating, availability, experience, urgency, and trust score.
- **🔔 Notifications:** Real-time notification system with unread badges and bulk mark-as-read.
- **📈 User Analytics:** Personalized dashboard showing booking stats, completion rates, and average ratings.
- ** Profile Management:** Dedicated profile screen with user stats and account management.

## 🏗️ Architecture

Antigravity uses a robust pipeline of specialized ADK `LlmAgent`s orchestrated by a Master Agent.

1. **Munsif (Orchestrator):** Manages the session state and delegates tasks sequentially.
2. **Zuban (Intent):** Extracts service type, location, urgency, and language from natural language input.
3. **Khoji (Matching):** Queries SQLite and applies a 6-factor algorithm to find the best provider.
4. **Jadwal (Scheduling):** Checks provider calendars, prevents double-booking, and suggests alternatives.
5. **Qeemat (Pricing):** Calculates transparent, dynamic pricing based on 7 components.
6. **Meezan/Hukum (Booking):** Executes the booking and generates receipts.
7. **Mayaar (Quality):** Manages post-service feedback loops.
8. **Insaf (Dispute):** Handles user complaints and automatically penalizes providers if necessary.

## ️ Tech Stack

- **Frontend:** HTML, CSS (Vanilla Custom UI), JavaScript, Google Maps JS API.
- **Backend:** Python, FastAPI, SQLite.
- **AI/LLM Engine:** Google Agent Development Kit (ADK), Gemini 2.0 Flash.
- **Database:** SQLite (Development), PostgreSQL (Production Ready).

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
The project comes with a pre-populated SQLite database (`antigravity.db`) containing mock service providers across Karachi areas (DHA, Gulshan, Clifton, Malir, Nazimabad, etc.) with precise coordinates and their schedules. To re-seed or wipe the database, run:
```bash
cd backend
python seed_providers.py
```

---

## 📋 API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Register new user (name, email, password) |
| POST | `/auth/login` | Login with email and password |
| GET | `/auth/me` | Get current user info (requires auth token) |
| POST | `/auth/logout` | Logout and invalidate token |

### Core Booking Flow
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/chat` | Send message to Zuban intent agent |
| POST | `/search` | Find providers by service type and location |
| POST | `/check_schedule` | Check provider availability |
| POST | `/pricing` | Calculate dynamic pricing |
| POST | `/book` | Create a new booking |
| POST | `/track` | Update booking status (EN_ROUTE/ARRIVED/COMPLETED) |
| POST | `/bookings/{id}/cancel` | Cancel a booking |

### User Data (Authenticated)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/bookings` | List user's bookings (user-scoped) |
| GET | `/analytics/stats` | Get user's booking analytics |
| GET | `/notifications` | Get user's notifications |
| POST | `/notifications/mark-all-read` | Mark all notifications as read |
| POST | `/notifications/{id}/read` | Mark single notification as read |

### Feedback & Disputes
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/feedback` | Submit service feedback |
| POST | `/dispute` | Raise a dispute |

### Utilities
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check with ADK status |
| GET | `/providers` | List all providers |
| GET | `/trace/{session_id}` | Get agent workplan trace |
| GET | `/booking/{id}` | Get single booking details |

---

## 🗺️ Supported Locations

Currently optimized for **Karachi, Pakistan** with providers in:
- Gulshan-e-Iqbal, DHA, Clifton, PECHS
- North Nazimabad, Federal B. Area, Johar
- Korangi, Saddar, Lyari, Orangi Town
- Malir, Landhi, Nazimabad

---

## 🔒 Security & Privacy

- **Token-Based Auth:** Bearer tokens with 24-hour expiry, stored securely in localStorage.
- **User-Scoped Data:** All bookings, notifications, and analytics are filtered by authenticated user.
- **XSS Protection:** Provider cards use event listeners instead of inline JavaScript.
- **Input Validation:** All API endpoints validate request schemas with Pydantic.
- **Rate Limiting:** 100 requests/minute per IP to prevent abuse.

---

## 📝 Recent Updates

### Major Improvements
- ✅ **Email/Password Authentication:** Replaced phone-based auth with email/password login and registration.
- ✅ **User-Scoped Endpoints:** Bookings, notifications, and analytics now return only authenticated user's data.
- ✅ **Auth Token Extraction:** Backend now properly reads `Authorization: Bearer <token>` header.
- ✅ **Profile Screen:** New dedicated profile page with user stats, avatar, and logout.
- ✅ **Bookings Screen:** Full bookings list view with refresh capability.
- ✅ **Cancel Booking:** New endpoint to cancel pending/confirmed bookings.
- ✅ **Bulk Mark Read:** `/notifications/mark-all-read` endpoint for clearing all notifications.
- ✅ **Peak Hour Pricing:** Booking flow now detects peak hours (9-11 AM, 5-8 PM) and applies dynamic pricing.
- ✅ **User-Booking Link:** Bookings are now associated with `user_id` for proper ownership tracking.
- ✅ **Loading States:** Auth forms, booking confirmation, and chat input now show loading indicators.
- ✅ **XSS Fix:** Provider selection uses safe event listeners instead of inline `onclick`.
- ✅ **Null Safety:** Feedback and dispute submission now validate booking existence.
- ✅ **Booking Status Default:** Model now defaults to `"pending"` status.
- ✅ **Chat Screen Cleanup:** Mock bubbles cleared on entry, welcome message shown dynamically.
- ✅ **Dispute Fix:** Fixed `create_session()` call that was passing unsupported `prefix` argument.

### Previous Updates
- ✅ Fixed intent recognition for plumbing/electrical services
- ✅ Added Malir area electricians to database
- ✅ Fixed booking flow and price breakdown parsing
- ✅ Improved location matching with Google Maps Geocoding API
- ✅ Enhanced fallback keyword matching for Roman Urdu inputs
- ✅ Added skill similarity matching for unknown service types
