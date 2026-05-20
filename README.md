# XIDMAT.AI — AI-Powered Home Services Platform

> **Built for the Antigravity Hackathon** — A fully autonomous, multi-agent service booking platform for Pakistan, powered by the **Google Agent Development Kit (ADK)** and **Gemini 2.0 Flash**.

---

## Overview

XIDMAT.AI is a next-generation AI-powered platform that abstracts away the complexity of finding, negotiating, and scheduling local service professionals (Plumbers, Electricians, AC Technicians, Cleaners, etc.) in Pakistan. Users describe their problem in **English, Urdu, or Roman Urdu** — and our AI agents handle the entire booking lifecycle autonomously.

### Why Antigravity?

This project was built end-to-end using **Antigravity** as the development environment. Antigravity provided:
- **AI-assisted code generation** for all backend agents, API routes, and frontend components
- **Rapid prototyping** of the full multi-agent pipeline from intent extraction to dispute resolution
- **One-command deployment** to Railway with Docker/Nixpacks configuration
- **Automated APK builds** via GitHub Actions for the Capacitor-based mobile app
- **Full-stack debugging** with integrated terminal, file explorer, and AI pair programming

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     XIDMAT.AI Architecture                       │
─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐   │
│  │  Mobile App  │    │  Web Frontend │    │  Desktop Sidebar │   │
│  │  (Capacitor) │    │  (HTML/JS)    │    │                  │   │
│  └──────┬───────┘    └──────┬───────    └────────┬─────────┘   │
│         │                   │                      │             │
│         └───────────────────┼──────────────────────┘             │
│                             │                                    │
│                    ┌────────▼────────┐                           │
│                    │   FastAPI       │                           │
│                    │   Backend       │                           │
│                    │   (Python)      │                           │
│                    └────────┬────────┘                           │
│                             │                                    │
│              ┌──────────────┼──────────────┐                     │
│              │              │              │                     │
│     ┌────────▼────┐ ┌──────▼──────┐ ┌─────▼──────             │
│     │ Munsif      │ │ Google ADK  │ │ SQLite /   │             │
│     │ Orchestrator│ │ LlmAgents   │ │ PostgreSQL │             │
│     └─────────────┘ └─────────────┘ └────────────┘             │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              Agent Pipeline (Google ADK)                    │ │
│  │                                                            │ │
│  │  Munsif (Root) → Zuban ─→ Khoji → Jadwal ─→ Qeemat      │ │
│  │                       │                           │         │ │
│  │                       └──────────────→ Insaf ←────┘         │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Deployment Stack

| Layer | Technology | Hosting |
|-------|-----------|---------|
| **Backend API** | FastAPI + Google ADK + Python 3.12 | Railway (Docker) |
| **Mobile App** | Capacitor.js (WebView wrapper) | Android APK |
| **Web Frontend** | Vanilla HTML/CSS/JS (SPA pattern) | Served by FastAPI |
| **Database** | SQLite (dev) / PostgreSQL (prod) | Railway managed |
| **AI/LLM** | Google Gemini 2.0 Flash via ADK | Google Cloud |
| **Maps** | Google Maps JS API + Geocoding | Google Cloud |
| **CI/CD** | GitHub Actions (auto APK build) | GitHub |

---

## Agents Developed (Google ADK)

All agents are implemented as **Google ADK `LlmAgent`** instances with custom `FunctionTool` integrations. The pipeline is orchestrated by a root agent with sub-agent delegation.

### Agent 0: Munsif (Master Orchestrator)
- **Role:** Root ADK agent that coordinates all specialist agents
- **Model:** Gemini 2.0 Flash via `google.adk.agents.LlmAgent`
- **Sub-agents:** Zuban, Khoji, Jadwal, Qeemat, Insaf
- **Tools:** search_providers, check_availability, calculate_price, resolve_dispute
- **Responsibility:** Maintains session state, routes tasks sequentially, handles fallbacks

### Agent 1: Zuban (Multilingual Intent Extraction)
- **Role:** Parses user input in English, Urdu, or Roman Urdu
- **Output:** Structured intent JSON (service_type, location, urgency, language_detected)
- **Mapping:** 11 service categories (electrician, plumber, ac_technician, carpenter, painter, home_cleaner, mechanic, gas_technician, pest_control, tiler, welder)
- **Fallback:** Generates clarifying questions when confidence is low

### Agent 2: Khoji (AI Provider Matching)
- **Role:** Finds and ranks providers using a 6-factor scoring algorithm
- **Factors:** Distance (Haversine), rating, experience, availability, urgency match, trust score
- **Tool:** `search_providers` — queries SQLite provider database with geocoding
- **Output:** Ranked provider list with AI-generated rationale for each recommendation

### Agent 3: Jadwal (Scheduling Intelligence)
- **Role:** Checks provider calendar for conflicts and suggests alternatives
- **Features:** Double-booking prevention, buffer time enforcement, next-available-slot finder
- **Tool:** `check_availability` — validates time slots against existing bookings

### Agent 4: Qeemat (Dynamic Pricing Engine)
- **Role:** Calculates transparent pricing using 7 components
- **Components:** Base rate, urgency premium, distance charge, peak hour factor, quality premium, experience bonus, demand surge
- **Tool:** `calculate_price` — returns structured breakdown with AI rationale

### Agent 5: Meezan (Booking Execution)
- **Role:** Creates confirmed bookings, generates unique confirmation codes, writes to database
- **Features:** Price integration from Qeemat, session linking, notification triggers

### Agent 6: Mayaar (Quality Assurance)
- **Role:** Post-service feedback loop — collects ratings, updates provider scores
- **Features:** Weighted rolling average, multi-criteria feedback (on-time, quality, cleanliness)

### Agent 7: Insaf (Dispute Resolution)
- **Role:** Handles user complaints with AI-powered analysis
- **Dispute Types:** No-show, overcharge, poor quality, property damage
- **Actions:** Refund processing, provider penalties, escalation to management

### Agent 8: Bonus (Provider Optimization)
- **Role:** Provider-side workload balancing and demand forecasting
- **Features:** Time slot optimization, capacity management, demand prediction

---

## APIs Used

### Real APIs
| API | Purpose | Provider |
|-----|---------|----------|
| **Google ADK** | Multi-agent orchestration framework | Google |
| **Gemini 2.0 Flash** | LLM inference for all agents | Google Cloud |
| **Google Maps JS API** | Live tracking, geocoding, route rendering | Google Cloud |
| **Google Geocoding API** | Convert area names to lat/lng coordinates | Google Cloud |
| **Railway** | Cloud hosting with PostgreSQL & Docker | Railway.app |

### Mock/Simulated APIs
| API | Purpose | Notes |
|-----|---------|-------|
| **WebSocket Tracking** | Real-time provider location updates | Simulated movement on map |
| **UI Avatars** | Provider profile images | `ui-avatars.com` |
| **Phosphor Icons** | UI icon library | `unpkg.com/@phosphor-icons` |

---

## Integrations Implemented

### 1. Google ADK Multi-Agent Pipeline
- Full `LlmAgent` hierarchy with root agent (`Munsif`) and 5 sub-agents
- `FunctionTool` wrappers for database operations (search, schedule, price, dispute)
- Session management with workplan trace logging
- Async-compatible agent runners in `adk_pipeline.py`

### 2. Capacitor.js Mobile App
- WebView-based Android app wrapping the web frontend
- GPS location permissions (`ACCESS_FINE_LOCATION`, `ACCESS_COARSE_LOCATION`)
- Native bridge for geolocation via `navigator.geolocation`
- GitHub Actions CI/CD for automated APK builds

### 3. Railway Cloud Deployment
- Docker-based deployment with `python:3.12-slim` base image
- Nixpacks fallback configuration
- Environment variable management (`.env` for API keys)
- Health check endpoint (`/health`) with ADK availability status

### 4. SQLite + SQLAlchemy ORM
- 8 database models: User, Session, Provider, Booking, Schedule, Feedback, Dispute, Notification
- Auto-seeding of 20+ mock providers across Karachi neighborhoods
- User-scoped data isolation (bookings, notifications, analytics)

### 5. Token-Based Authentication
- Bearer token auth with 24-hour expiry
- Password hashing via SHA-256
- User registration, login, logout, and profile management
- Protected endpoints with `Depends(get_current_user)`

### 6. Real-Time WebSocket Tracking
- WebSocket endpoint (`/ws/tracking/{booking_id}`) for live provider location
- Google Maps integration with animated provider movement
- Route line rendering between user and provider

### 7. Rate Limiting Middleware
- 100 requests/minute per IP address
- Sliding window implementation
- Returns `429 Too Many Requests` on limit exceeded

---

## Tech Stack

| Category | Technology |
|----------|-----------|
| **Frontend** | HTML5, CSS3 (Custom Glass UI), Vanilla JavaScript, Google Maps JS API |
| **Backend** | Python 3.12, FastAPI, Uvicorn, Pydantic |
| **AI/ML** | Google ADK, Gemini 2.0 Flash, google-genai |
| **Database** | SQLite (dev), PostgreSQL (prod), SQLAlchemy ORM |
| **Mobile** | Capacitor.js v8, Android (Java/Kotlin bridge) |
| **DevOps** | Docker, Railway, GitHub Actions, Nixpacks |
| **Icons/UI** | Phosphor Icons, Google Fonts (Inter, Outfit) |

---

## How to Run Locally

### Prerequisites
- Python 3.9+
- Node.js 22+
- `.env` file in `backend/` with API keys:
  ```env
  GEMINI_API_KEY=your_gemini_key
  GOOGLE_MAPS_API_KEY=your_maps_key
  OPENROUTER_API_KEY=your_openrouter_key
  OPENROUTER_MODEL=google/gemini-2.0-flash-001
  ```

### Quick Start (Windows)
```bash
# Double-click run_windows.bat
# Or run manually:
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Then open `frontend/index.html` in your browser.

### Mobile App Build
```bash
npm install
npx cap sync android
# Open in Android Studio or use GitHub Actions for automated APK build
```

---

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Register new user |
| POST | `/auth/login` | Login with phone and password |
| GET | `/auth/me` | Get current user info |
| POST | `/auth/logout` | Logout and invalidate token |

### Core Booking Flow
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/chat` | Send message to Zuban intent agent |
| POST | `/search` | Find providers via Khoji |
| POST | `/check_schedule` | Check availability via Jadwal |
| POST | `/pricing` | Calculate price via Qeemat |
| POST | `/book` | Create booking via Meezan |
| POST | `/track` | Update booking status |

### User Data (Authenticated)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/bookings` | List user's bookings |
| GET | `/analytics/stats` | User booking analytics |
| GET | `/notifications` | User notifications |
| POST | `/notifications/mark-all-read` | Mark all as read |

### Feedback & Disputes
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/feedback` | Submit service feedback |
| POST | `/dispute` | Raise dispute via Insaf |

### Utilities
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check with ADK status |
| GET | `/providers` | List all providers |
| GET | `/trace/{session_id}` | Get agent workplan trace |
| WS | `/ws/tracking/{booking_id}` | Real-time tracking WebSocket |

---

## Supported Locations

Optimized for **Karachi, Pakistan** with providers across:
- Gulshan-e-Iqbal, DHA, Clifton, PECHS
- North Nazimabad, Federal B. Area, Johar
- Korangi, Saddar, Lyari, Orangi Town
- Malir, Landhi, Nazimabad

---

## Project Structure

```
antigravity-hackathon/
├── backend/
│   ├── main.py              # FastAPI app, all routes, auth, WebSocket
│   ├── adk_agents.py        # Google ADK LlmAgent definitions
│   ├── adk_pipeline.py      # Async agent runners
│   ├── database.py          # SQLAlchemy engine & session
│   ├── models.py            # 8 database models
│   ├── seed_providers.py    # Mock provider data seeder
│   ├── requirements.txt     # Python dependencies
│   ├── munsif/              # Orchestrator agent
│   ├── zuban/               # Intent extraction agent
│   ├── khoji/               # Provider matching agent
│   ├── jadwal/              # Scheduling agent
│   ├── qeemat/              # Pricing agent
│   ├── meezan/              # Booking execution agent
│   ├── insaf/               # Dispute resolution agent
│   ├── mayaar/              # Quality assurance agent
│   └── bonus/               # Provider optimization agent
├── frontend/
│   ├── index.html           # Main HTML (all screens)
│   ├── app.js               # SPA router, API calls, UI logic
│   └── styles.css           # Custom glass-morphism UI
├── android/                  # Capacitor Android project
├── .github/workflows/        # GitHub Actions APK build
├── Dockerfile                # Railway Docker deployment
├── nixpacks.toml             # Railway Nixpacks fallback
├── railway.toml              # Railway deployment config
├── capacitor.config.json     # Capacitor mobile config
└── run_windows.bat           # Windows quick-start script
```

---

## License

Built for the **Antigravity Hackathon 2026**.
