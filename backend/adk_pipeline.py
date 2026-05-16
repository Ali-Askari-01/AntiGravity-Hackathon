"""
Antigravity — Google ADK Multi-Agent Pipeline
=============================================
All 6 agents (Zuban, Khoji, Jadwal, Qeemat, Meezan, Insaf) are implemented
as proper Google ADK LlmAgents with registered tools.

Munsif acts as the SequentialAgent orchestrator.
"""
import os
import json
import asyncio
import datetime
import logging
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

# ── Google ADK imports ─────────────────────────────────────────────────────────
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools import FunctionTool
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk import types

# ── Shared in-memory ADK session service ──────────────────────────────────────
_session_service = InMemorySessionService()
APP_NAME = "antigravity"


# ══════════════════════════════════════════════════════════════════════════════
# TOOL DEFINITIONS — each tool wraps existing business logic
# ══════════════════════════════════════════════════════════════════════════════

def submit_intent(service_type: str, service_label: str, location: str, time_raw: str, time_normalized: str, urgency: str, language_detected: str) -> dict:
    """
    [Zuban Tool] Submit the extracted service intent fields.
    """
    return {
        "service_type": service_type,
        "service_label": service_label,
        "location": location,
        "time_raw": time_raw,
        "time_normalized": time_normalized,
        "urgency": urgency,
        "language_detected": language_detected
    }

def get_providers_from_db(service_type: str, location: str) -> dict:
    """
    [Khoji Tool] Query SQLite for all providers matching the service type.
    Returns their raw info (rating, experience, available) and calculated distance from the location.
    """
    from backend.database import SessionLocal
    from backend.models import Provider
    import math

    # Haversine distance
    def haversine(lat1, lng1, lat2, lng2):
        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)
        a = (math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2)
        return R * 2 * math.asin(math.sqrt(a))

    # Simulate Geocoding
    SECTOR_COORDS = {
        "g-13": (33.6938, 72.9797), "g13": (33.6938, 72.9797),
        "g-11": (33.6844, 73.0064), "g-10": (33.6892, 73.0189),
        "f-10": (33.7078, 73.0209), "f-6":  (33.7294, 73.0909),
        "f-7":  (33.7240, 73.0788), "f-8":  (33.7203, 73.0627),
        "i-8":  (33.6748, 73.0565), "i-9":  (33.6613, 73.0468),
        "dha":  (33.5651, 73.1651), "gulshan": (33.6844, 73.0950),
        "clifton": (24.8138, 67.0300),
    }
    user_lat, user_lng = SECTOR_COORDS.get(location.lower().strip(), (33.6844, 73.0479))

    db = SessionLocal()
    try:
        all_providers = db.query(Provider).all()
        matched = []
        for p in all_providers:
            if p.skills and service_type.lower() in [s.lower() for s in p.skills]:
                dist = round(haversine(user_lat, user_lng, p.lat, p.lng), 2)
                matched.append({
                    "provider_id": p.id, "name": p.name, "rating": p.rating,
                    "experience": p.experience, "available": p.is_available,
                    "base_price": p.base_price, "distance_km": dist
                })
        return {"matched_providers": matched, "user_location": {"lat": user_lat, "lng": user_lng}}
    finally:
        db.close()


def check_schedule(provider_id: int, requested_time: str) -> dict:
    """
    [Jadwal Tool] Check if a provider has a conflict at requested_time (ISO 8601).
    Returns boolean conflict flag and existing booked time range if conflict.
    """
    from backend.database import SessionLocal
    from backend.models import Schedule
    from datetime import datetime, timedelta
    
    db = SessionLocal()
    try:
        req_start = datetime.fromisoformat(requested_time)
        req_end = req_start + timedelta(hours=2) # default 2 hour session
        existing = db.query(Schedule).filter(Schedule.provider_id == provider_id, Schedule.status == 'occupied').all()
        for row in existing:
            booked_start = datetime.fromisoformat(row.slot_start)
            booked_end = datetime.fromisoformat(row.slot_end)
            if req_start < booked_end and req_end > booked_start:
                return {"conflict": True, "booked_start": row.slot_start, "booked_end": row.slot_end}
        return {"conflict": False}
    finally:
        db.close()

def find_next_slots(provider_id: int, after_time: str) -> dict:
    """
    [Jadwal Tool] Find the next 3 available slots for a provider after given time.
    """
    from backend.database import SessionLocal
    from backend.models import Schedule
    from datetime import datetime, timedelta
    db = SessionLocal()
    try:
        slots = []
        start_time = datetime.fromisoformat(after_time)
        candidate = start_time + timedelta(hours=1)
        max_lookahead = start_time + timedelta(hours=24)
        
        existing = db.query(Schedule).filter(Schedule.provider_id == provider_id, Schedule.status == 'occupied').all()
        
        while len(slots) < 3 and candidate < max_lookahead:
            req_end = candidate + timedelta(hours=2)
            conflict = False
            for row in existing:
                booked_start = datetime.fromisoformat(row.slot_start)
                booked_end = datetime.fromisoformat(row.slot_end)
                if candidate < booked_end and req_end > booked_start:
                    conflict = True
                    break
            if not conflict:
                slots.append(candidate.isoformat())
            candidate += timedelta(hours=1)
        return {"available_slots": slots, "count": len(slots)}
    finally:
        db.close()


def get_provider_pricing_details(provider_id: int) -> dict:
    """
    [Qeemat Tool] Fetch base rate and experience logic for Qeemat.
    """
    from backend.database import SessionLocal
    from backend.models import Provider
    db = SessionLocal()
    try:
        provider = db.query(Provider).filter(Provider.id == provider_id).first()
        if not provider:
            return {"error": f"Provider {provider_id} not found"}
        return {
            "base_rate": provider.base_price,
            "rating": provider.rating or 5.0,
            "experience_years": provider.experience or 1
        }
    finally:
        db.close()


def create_booking(session_id: str, provider_id: int, service_type: str,
                   location: str, distance_km: float,
                   urgency: str, confirmed_slot: str) -> dict:
    """
    [Meezan Tool] Insert a confirmed booking into SQLite.
    Returns: booking_id, confirmation_code, provider_name.
    """
    from backend.database import SessionLocal
    from backend.models import Provider, Booking, Schedule
    from datetime import datetime, timedelta
    import random
    
    db = SessionLocal()
    try:
        provider = db.query(Provider).filter(Provider.id == provider_id).first()
        if not provider:
            return {"error": "Provider not found"}
            
        code = f"XIDMAT-{random.randint(1000, 9999)}"
        booking = Booking(
            user_id="user_123",
            provider_id=provider_id,
            service_type=service_type,
            status="confirmed",
            location=location,
            distance_km=distance_km,
            urgency=urgency,
            scheduled_time=confirmed_slot,
            confirmation_code=code
        )
        db.add(booking)
        
        # also lock schedule
        start_dt = datetime.fromisoformat(confirmed_slot)
        end_dt = start_dt + timedelta(hours=2)
        schedule = Schedule(provider_id=provider_id, slot_start=start_dt.isoformat(), slot_end=end_dt.isoformat(), status="occupied")
        db.add(schedule)
        
        db.commit()
        db.refresh(booking)
        return {
            "booking_id": booking.id,
            "confirmation_code": code,
            "provider_name": provider.name
        }
    except Exception as e:
        db.rollback()
        return {"error": str(e)}
    finally:
        db.close()

def generate_reminder(provider_name: str, confirmed_slot: str) -> dict:
    """
    [Meezan Tool] Generate a reminder message scheduled 1 hour before the booking.
    """
    return {"reminder_at": f"1 hour before {confirmed_slot}", "status": "scheduled"}

def fetch_booking_details(booking_id: int) -> dict:
    """
    [Insaf Tool] Fetch booking details for a dispute.
    """
    from backend.database import SessionLocal
    from backend.models import Booking, Provider
    db = SessionLocal()
    try:
        b = db.query(Booking).filter(Booking.id == booking_id).first()
        if not b: return {"error": "Booking not found"}
        p = db.query(Provider).filter(Provider.id == b.provider_id).first()
        return {
            "booking_status": b.status,
            "service_type": b.service_type,
            "provider_name": p.name if p else "Unknown",
            "provider_rating": p.rating if p else 5.0
        }
    finally:
        db.close()

def apply_dispute_resolution(booking_id: int, action: str, penalty_amount: float = 0.0, new_rating: float = None) -> dict:
    """
    [Insaf Tool] Apply the resolution to the database.
    """
    from backend.database import SessionLocal
    from backend.models import Booking, Provider
    db = SessionLocal()
    try:
        b = db.query(Booking).filter(Booking.id == booking_id).first()
        if not b: return {"error": "Booking not found"}
        b.status = f"disputed_resolved_{action}"
        if new_rating and b.provider_id:
            p = db.query(Provider).filter(Provider.id == b.provider_id).first()
            if p: p.rating = new_rating
        db.commit()
        return {"status": "success", "action_applied": action}
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════════════
# ADK AGENT DEFINITIONS
# ══════════════════════════════════════════════════════════════════════════════

_MODEL = "gemini-2.0-flash"

zuban_agent = LlmAgent(
    name="Zuban",
    model=_MODEL,
    description="Multilingual intent analyst. Parses Roman Urdu, Urdu, and English service requests.",
    instruction="""You are Zuban, the Intent Analyst for Antigravity — Pakistan's AI service booking platform.

Your ONLY job: parse the user's text to extract service intent and call the `submit_intent` tool with what you find.

Steps:
1. Extract service_type, service_label, location, time_raw, time_normalized, urgency, and language_detected from the user's message.
2. Call submit_intent(...) with these fields.
3. Output a concise Urdu/English summary like: "Samajh gaya! Plumber G-13 mein kal subah chahiye — urgency: normal"

Never respond without calling submit_intent first.""",
    tools=[FunctionTool(func=submit_intent)],
    output_key="zuban_output"
)

khoji_agent = LlmAgent(
    name="Khoji",
    model=_MODEL,
    description="Provider matcher. Searches SQLite and applies 6-factor ranking.",
    instruction="""You are Khoji, the Provider Matcher for Antigravity.

Your job: Find and rank the best service providers for the user's request.

Steps:
1. Call get_providers_from_db(service_type, location) using values from the context.
2. The tool returns a list of matched providers with distance, rating, experience, and availability.
3. Score each provider using this formula: 
   score = (0.35 * distance_score) + (0.30 * trust_score) + (0.20 * availability) + (0.10 * experience) + (0.05 * urgency_bonus)
   where distance_score = max(0, 1 - (distance_km / 10)), trust_score = ((rating - 1)/4)*0.6 + (experience/10)*0.4.
4. Report the top 3 providers: name, score, distance, rating, and your rationale.
5. Recommend the best match.

Never invent provider data. Only use get_providers_from_db results.""",
    tools=[
        FunctionTool(func=get_providers_from_db),
    ],
    output_key="khoji_output"
)

jadwal_agent = LlmAgent(
    name="Jadwal",
    model=_MODEL,
    description="Scheduling agent. Detects conflicts and finds next available slots.",
    instruction="""You are Jadwal, the Scheduling Intelligence for Antigravity.

Your job: Verify the selected provider's availability.

Steps:
1. Call check_schedule(provider_id, requested_time)
2. If the tool returns conflict=False, confirm the slot with a message like: "Waqt dastyab hai."
3. If the tool returns conflict=True, call find_next_slots(provider_id, requested_time) and present the 3 alternatives.
4. Ask the user if they want to proceed with the alternatives.

Always base your answer on tool results only.""",
    tools=[
        FunctionTool(func=check_schedule),
        FunctionTool(func=find_next_slots),
    ],
    output_key="jadwal_output"
)

qeemat_agent = LlmAgent(
    name="Qeemat",
    model=_MODEL,
    description="Dynamic pricing agent. Applies 7-component pricing formula.",
    instruction="""You are Qeemat, the Pricing Agent for Antigravity.

Your job: Calculate the total service cost fairly and transparently.

Steps:
1. Call get_provider_pricing_details(provider_id)
2. Calculate the price breakdown: 
   - base_rate (from tool)
   - urgency surcharge (if urgent add 500)
   - distance fee (distance_km * 50)
   - peak hour (if is_peak add 300)
   - quality premium (if rating >= 4.5 add 200)
   - experience factor (experience_years * 100)
3. Sum these up to get the final price.
4. State the final price clearly: "Final price: PKR X,XXX" and explain the breakdown.

Never estimate prices without the tool.""",
    tools=[FunctionTool(func=get_provider_pricing_details)],
    output_key="qeemat_output"
)

meezan_agent = LlmAgent(
    name="Meezan",
    model=_MODEL,
    description="Booking executor. Creates DB record and generates confirmation code.",
    instruction="""You are Meezan, the Booking Executor for Antigravity.

Your job: Finalize the booking and generate the confirmation.

Steps:
1. Call create_booking(session_id, provider_id, service_type, location, distance_km, urgency, confirmed_slot)
2. Call generate_reminder(provider_name, confirmed_slot)
3. Present the full receipt: confirmation code, provider name, slot, and reminder.

Always call create_booking first. Never confirm a booking without the tool result.""",
    tools=[
        FunctionTool(func=create_booking),
        FunctionTool(func=generate_reminder),
    ],
    output_key="meezan_output"
)

insaf_agent = LlmAgent(
    name="Insaf",
    model=_MODEL,
    description="Dispute resolution agent. Classifies issues and applies provider penalties.",
    instruction="""You are Insaf, the Dispute Resolution agent for Antigravity.

Your job: Handle service complaints fairly and transparently.

Steps:
1. Call fetch_booking_details(booking_id) to get context.
2. Based on the issue_type and description, determine a resolution (e.g., refund, provider warning).
3. Call apply_dispute_resolution(booking_id, action, penalty_amount, new_rating) to apply it.
4. Explain the classification and resolution in empathetic Urdu/English.

Never make up resolutions without applying them via the tool.""",
    tools=[
        FunctionTool(func=fetch_booking_details),
        FunctionTool(func=apply_dispute_resolution)
    ],
    output_key="insaf_output"
)


# ══════════════════════════════════════════════════════════════════════════════
# RUNNER HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _collect_trace(events: list) -> List[dict]:
    """Convert ADK event stream into workplan step dicts."""
    steps = []
    for event in events:
        author = getattr(event, 'author', 'Agent')
        content = getattr(event, 'content', None)
        if not content:
            continue
        parts = getattr(content, 'parts', []) or []
        for part in parts:
            if hasattr(part, 'text') and part.text:
                steps.append({"agent": author, "action": part.text})
            elif hasattr(part, 'function_call') and part.function_call:
                fn = part.function_call
                args_str = json.dumps(dict(fn.args)) if fn.args else "{}"
                steps.append({"agent": author, "action": f"[Tool] {fn.name}({args_str})", "tool_name": fn.name, "tool_args": dict(fn.args) if fn.args else {}})
            elif hasattr(part, 'function_response') and part.function_response:
                fr = part.function_response
                resp_str = str(fr.response)
                # Attempt to parse resp_str as JSON if it's a dict-like string, or if fr.response is a dict
                tool_res = fr.response
                if hasattr(tool_res, "items"):
                    tool_res = dict(tool_res)
                steps.append({"agent": author, "action": f"[Result] {fr.name} → {resp_str}", "tool_name": fr.name, "tool_result": tool_res})
    return steps


def _get_final_text(events: list) -> str:
    """Extract the last agent text response from events."""
    for event in reversed(events):
        if hasattr(event, 'is_final_response') and event.is_final_response():
            content = getattr(event, 'content', None)
            if content and getattr(content, 'parts', None):
                for part in content.parts:
                    if hasattr(part, 'text') and part.text:
                        return part.text
    return ""


async def _run_agent_async(agent: LlmAgent, adk_session_id: str, message_text: str) -> dict:
    """Run a single ADK agent and return trace + final response text."""
    runner = Runner(agent=agent, app_name=APP_NAME, session_service=_session_service)
    message = types.Content(role="user", parts=[types.Part(text=message_text)])
    events = []
    async for event in runner.run_async(
        user_id="antigravity_user",
        session_id=adk_session_id,
        new_message=message
    ):
        events.append(event)
    return {
        "trace": _collect_trace(events),
        "response": _get_final_text(events)
    }


def _run_agent(agent: LlmAgent, adk_session_id: str, message_text: str) -> dict:
    """Synchronous wrapper for _run_agent_async."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _run_agent_async(agent, adk_session_id, message_text))
                return future.result(timeout=30)
        else:
            return loop.run_until_complete(_run_agent_async(agent, adk_session_id, message_text))
    except Exception as e:
        logger.error(f"ADK agent run failed: {e}")
        return {"trace": [{"agent": agent.name, "action": f"Error: {str(e)}"}], "response": ""}


def ensure_adk_session(adk_session_id: str):
    """Create an ADK session if it doesn't exist yet."""
    try:
        _session_service.get_session(
            app_name=APP_NAME, user_id="antigravity_user", session_id=adk_session_id
        )
    except Exception:
        _session_service.create_session(
            app_name=APP_NAME, user_id="antigravity_user", session_id=adk_session_id
        )


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC API — called from main.py
# ══════════════════════════════════════════════════════════════════════════════

def run_zuban(session_id: str, user_text: str) -> dict:
    """Run Zuban agent to parse intent."""
    ensure_adk_session(session_id)
    return _run_agent(zuban_agent, session_id, f"Parse this service request: {user_text}")


def run_khoji(session_id: str, service_type: str, location: str, urgency: str = "normal") -> dict:
    """Run Khoji agent to find and rank providers."""
    ensure_adk_session(session_id)
    msg = (f"Find providers: service_type='{service_type}', "
           f"location='{location}', urgency='{urgency}'")
    return _run_agent(khoji_agent, session_id, msg)


def run_jadwal(session_id: str, provider_id: int, requested_time: str) -> dict:
    """Run Jadwal agent to check schedule."""
    ensure_adk_session(session_id)
    msg = f"Check schedule: provider_id={provider_id}, requested_time='{requested_time}'"
    return _run_agent(jadwal_agent, session_id, msg)


def run_qeemat(session_id: str, provider_id: int, urgency: str,
               distance_km: float, is_peak: bool = False) -> dict:
    """Run Qeemat agent to calculate price."""
    ensure_adk_session(session_id)
    msg = (f"Calculate price: provider_id={provider_id}, urgency='{urgency}', "
           f"distance_km={distance_km}, is_peak={is_peak}")
    return _run_agent(qeemat_agent, session_id, msg)


def run_meezan(session_id: str, provider_id: int, service_type: str,
               location: str, distance_km: float, urgency: str, confirmed_slot: str) -> dict:
    """Run Meezan agent to execute booking."""
    ensure_adk_session(session_id)
    msg = (f"Create booking: session_id='{session_id}', provider_id={provider_id}, "
           f"service_type='{service_type}', location='{location}', "
           f"distance_km={distance_km}, urgency='{urgency}', confirmed_slot='{confirmed_slot}'")
    return _run_agent(meezan_agent, session_id, msg)


def run_insaf(session_id: str, booking_id: int, issue_type: str, description: str) -> dict:
    """Run Insaf agent to resolve dispute."""
    ensure_adk_session(session_id)
    msg = (f"Handle dispute: booking_id={booking_id}, "
           f"issue_type='{issue_type}', description='{description}'")
    return _run_agent(insaf_agent, session_id, msg)
