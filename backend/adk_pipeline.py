"""
Antigravity — Agent Pipeline
Wraps the individual agent classes and provides async-compatible runners.
"""
import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from sqlalchemy.orm import Session

# Load .env from the backend directory
_backend_dir = Path(__file__).parent
load_dotenv(_backend_dir / ".env")

from backend.database import SessionLocal
from backend.models import Provider, Booking, Schedule
from backend.zuban.zuban_agent import ZubanAgent, IntentResponse
from backend.khoji.khoji_agent import KhojiAgent
from backend.jadwal.jadwal_agent import JadwalAgent
from backend.qeemat.qeemat_agent import QeematAgent
from backend.meezan.meezan_agent import MeezanAgent
from backend.insaf.insaf_agent import InsafAgent

load_dotenv()

logger = logging.getLogger(__name__)

# ── Instantiate agent classes ─────────────────────────────────────────────────
try:
    zuban_instance = ZubanAgent()
except EnvironmentError as e:
    logger.warning(f"ZubanAgent not initialized: {e}")
    zuban_instance = None

khoji_instance = KhojiAgent()
jadwal_instance = JadwalAgent()
qeemat_instance = QeematAgent()
meezan_instance = MeezanAgent()
insaf_instance = InsafAgent()


# ── Helper: get or create DB session ──────────────────────────────────────────
def _get_db() -> Session:
    return SessionLocal()


# ── Agent runners ─────────────────────────────────────────────────────────────

async def run_zuban(session_id: str, text: str) -> Dict[str, Any]:
    """Parse user intent via Zuban."""
    trace = [{"agent": "Zuban", "action": f"Parsing: {text}"}]
    try:
        if zuban_instance is None:
            raise EnvironmentError("GEMINI_API_KEY not configured")
        intent: IntentResponse = zuban_instance.parse_input(text)
        intent_dict = intent.model_dump()
        trace.append({
            "agent": "Zuban",
            "action": f"Extracted intent: {intent.service_label} in {intent.location}",
            "tool_name": "submit_intent",
            "tool_result": intent_dict,
        })
        return {
            "response": f"Samajh gaya! {intent.service_label} {intent.location} mein chahiye — urgency: {intent.urgency}",
            "intent": intent_dict,
            "trace": trace,
        }
    except Exception as e:
        logger.error(f"Zuban error: {e}", exc_info=True)
        trace.append({"agent": "Zuban", "action": f"Error: {e}", "error": str(e)})
        return {"response": "Maazrat, samajh nahi aaya. Dobara likhein.", "intent": {}, "trace": trace}


async def run_khoji(session_id: str, service_type: str, location: str, urgency: str) -> Dict[str, Any]:
    """Find and rank providers via Khoji."""
    trace = [{"agent": "Khoji", "action": f"Searching for {service_type} in {location}"}]
    db = _get_db()
    try:
        result = khoji_instance.find_providers(db, service_type, location, urgency)
        trace.append({
            "agent": "Khoji",
            "action": f"Found {result.get('total_found', 0)} providers",
            "tool_name": "get_providers_from_db",
            "tool_result": result,
        })
        return {
            "response": result.get("message", "Providers found"),
            "trace": trace,
            "top_providers": result.get("top_providers", []),
        }
    except Exception as e:
        logger.error(f"Khoji error: {e}", exc_info=True)
        trace.append({"agent": "Khoji", "action": f"Error: {e}", "error": str(e)})
        return {"response": "Provider search failed", "trace": trace, "top_providers": []}
    finally:
        db.close()


async def run_jadwal(session_id: str, provider_id: int, requested_start: str) -> Dict[str, Any]:
    """Check provider availability via Jadwal."""
    trace = [{"agent": "Jadwal", "action": f"Checking availability for provider {provider_id}"}]
    db = _get_db()
    try:
        conflict, booked_start, booked_end = jadwal_instance.check_conflict(db, provider_id, requested_start)
        trace.append({
            "agent": "Jadwal",
            "action": f"Conflict: {conflict}",
            "tool_name": "check_schedule",
            "tool_result": {"conflict": conflict, "booked_start": booked_start, "booked_end": booked_end},
        })
        if conflict:
            slots = jadwal_instance.find_next_available_slots(db, provider_id, requested_start)
            trace.append({
                "agent": "Jadwal",
                "action": f"Found {len(slots)} alternative slots",
                "tool_name": "find_next_slots",
                "tool_result": {"available_slots": slots},
            })
            return {
                "response": "Ye slot masroof hai. Yeh alternative slots hain:",
                "alternatives": slots,
                "trace": trace,
            }
        return {
            "response": "Waqt dastyab hai! Slot available hai.",
            "alternatives": [],
            "trace": trace,
        }
    except Exception as e:
        logger.error(f"Jadwal error: {e}", exc_info=True)
        trace.append({"agent": "Jadwal", "action": f"Error: {e}", "error": str(e)})
        return {"response": "Schedule check failed", "alternatives": [], "trace": trace}
    finally:
        db.close()


async def run_qeemat(session_id: str, provider_id: int, urgency: str, distance_km: float, is_peak: bool) -> Dict[str, Any]:
    """Calculate price via Qeemat."""
    trace = [{"agent": "Qeemat", "action": f"Calculating price for provider {provider_id}"}]
    db = _get_db()
    try:
        provider = db.query(Provider).filter(Provider.id == provider_id).first()
        if not provider:
            raise ValueError(f"Provider {provider_id} not found")

        appt_time = datetime.now()
        pricing = qeemat_instance.calculate_price(
            base_rate=provider.base_price or 0,
            urgency=urgency,
            distance_km=distance_km,
            appointment_time=appt_time,
            provider_rating=provider.rating or 5.0,
            experience_years=provider.experience or 1,
        )

        trace.append({
            "agent": "Qeemat",
            "action": f"Final price: PKR {pricing['final_price']}",
            "tool_name": "calculate_price",
            "tool_result": {
                "final_price": pricing["final_price"],
                "breakdown": pricing["breakdown"],
            },
        })
        return {
            "response": pricing.get("trace_log", f"Price: PKR {pricing['final_price']}"),
            "trace": trace,
        }
    except Exception as e:
        logger.error(f"Qeemat error: {e}", exc_info=True)
        trace.append({"agent": "Qeemat", "action": f"Error: {e}", "error": str(e)})
        return {"response": "Pricing failed", "trace": trace}
    finally:
        db.close()


async def run_meezan(
    session_id: str, provider_id: int, service_type: str, location: str,
    distance_km: float, urgency: str, confirmed_slot: str, price: float = 0
) -> Dict[str, Any]:
    """Create booking via Meezan."""
    trace = [{"agent": "Meezan", "action": "Creating booking..."}]
    db = _get_db()
    try:
        result = meezan_instance.create_booking(
            db=db,
            session_id=session_id,
            provider_id=provider_id,
            service_type=service_type,
            location=location,
            distance_km=distance_km,
            urgency=urgency,
            confirmed_slot=confirmed_slot,
        )
        trace.append({
            "agent": "Meezan",
            "action": f"Booking confirmed: {result['confirmation_code']}",
            "tool_name": "create_booking",
            "tool_result": result,
        })
        return {
            "response": result.get("confirmation_code", "Booking confirmed"),
            "trace": trace,
        }
    except Exception as e:
        logger.error(f"Meezan error: {e}", exc_info=True)
        trace.append({"agent": "Meezan", "action": f"Error: {e}", "error": str(e)})
        # Re-raise the exception so the caller can handle it properly
        raise
    finally:
        db.close()


async def run_insaf(session_id: str, booking_id: int, issue_type: str, description: str) -> Dict[str, Any]:
    """Resolve dispute via Insaf."""
    trace = [{"agent": "Insaf", "action": f"Processing dispute for booking {booking_id}"}]
    db = _get_db()
    try:
        result = insaf_instance.handle_dispute(db, booking_id, issue_type, description)
        trace.append({
            "agent": "Insaf",
            "action": f"Dispute resolved: {result.get('resolution', 'pending')}",
            "tool_name": "apply_dispute_resolution",
            "tool_result": result,
        })
        return {
            "response": result.get("message", "Dispute processed"),
            "trace": trace,
        }
    except Exception as e:
        logger.error(f"Insaf error: {e}", exc_info=True)
        trace.append({"agent": "Insaf", "action": f"Error: {e}", "error": str(e)})
        return {"response": f"Dispute failed: {e}", "trace": trace}
    finally:
        db.close()
