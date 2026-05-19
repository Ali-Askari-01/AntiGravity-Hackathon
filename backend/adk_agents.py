import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / ".env")

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from backend.database import SessionLocal
from backend.models import Provider, Booking, Feedback, Dispute, Schedule
from backend.khoji.khoji_agent import KhojiAgent, haversine, geocode_location
from backend.jadwal.jadwal_agent import JadwalAgent
from backend.qeemat.qeemat_agent import QeematAgent
from backend.insaf.insaf_agent import InsafAgent

logger = logging.getLogger(__name__)

khoji = KhojiAgent()
jadwal = JadwalAgent()
qeemat = QeematAgent()
insaf = InsafAgent()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")


def _get_llm_model():
    if GEMINI_API_KEY:
        return "gemini-2.0-flash"
    return "gemini-2.0-flash"


def search_providers(service_type: str, location: str, urgency: str = "normal") -> str:
    db = SessionLocal()
    try:
        result = khoji.find_providers(db, service_type, location, urgency)
        return json.dumps({
            "status": result["status"],
            "user_location": result["user_location"],
            "top_providers": result["top_providers"],
            "message": result["message"],
            "ai_rationale": True
        }, default=str)
    except Exception as e:
        logger.error(f"search_providers error: {e}")
        return json.dumps({"status": "error", "message": str(e)})
    finally:
        db.close()


def check_availability(provider_id: int, requested_time: str) -> str:
    db = SessionLocal()
    try:
        result = jadwal.validate_and_book(db, provider_id, requested_time)
        return json.dumps(result)
    except Exception as e:
        logger.error(f"check_availability error: {e}")
        return json.dumps({"status": "error", "message": str(e)})
    finally:
        db.close()


def calculate_price(base_rate: float, urgency: str, distance_km: float,
                    provider_rating: float, experience_years: int,
                    provider_name: str = "Provider") -> str:
    try:
        pricing = qeemat.calculate_price(
            base_rate=base_rate,
            urgency=urgency,
            distance_km=distance_km,
            appointment_time=datetime.now(),
            provider_rating=provider_rating,
            experience_years=experience_years,
            provider_name=provider_name
        )
        return json.dumps({
            "final_price": pricing["final_price"],
            "breakdown": pricing["breakdown"],
            "ai_rationale": pricing["trace_log"],
            "is_peak": pricing["is_peak"]
        })
    except Exception as e:
        logger.error(f"calculate_price error: {e}")
        return json.dumps({"status": "error", "message": str(e)})


def resolve_dispute(booking_id: int, issue_type: str, description: str) -> str:
    db = SessionLocal()
    try:
        result = insaf.handle_dispute(db, booking_id, issue_type, description)
        return json.dumps(result, default=str)
    except Exception as e:
        logger.error(f"resolve_dispute error: {e}")
        return json.dumps({"status": "error", "message": str(e)})
    finally:
        db.close()


search_providers_tool = FunctionTool(func=search_providers)
check_availability_tool = FunctionTool(func=check_availability)
calculate_price_tool = FunctionTool(func=calculate_price)
resolve_dispute_tool = FunctionTool(func=resolve_dispute)

LLM_MODEL = _get_llm_model()

zuban_agent = LlmAgent(
    name="Zuban",
    model=LLM_MODEL,
    instruction="""You are Zuban, a multilingual intent extraction agent for XIDMAT.AI, a Pakistani service booking app.
Your job is to understand what the user needs from their natural language input — whether in English, Urdu, or Roman Urdu.

Extract the following and respond with ONLY valid JSON (no markdown, no explanation):
- service_type: one of [electrician, plumber, ac_technician, carpenter, painter, home_cleaner, mechanic, gas_technician, pest_control, tiler, welder]
- service_label: human-readable name (e.g., "Electrician", "Plumber")
- location: the neighborhood or area mentioned (e.g., "DHA", "Gulshan-e-Iqbal")
- time_raw: the time expression as said by user (e.g., "abhi", "kal subah", "tomorrow 3pm")
- time_normalized: ISO datetime estimate
- urgency: "urgent", "normal", or "flexible"
- language_detected: "english", "urdu", or "roman_urdu"

MAPPING RULES:
- bijli, wiring, switch, socket, fan, circuit, power, solar, inverter, UPS, DC wiring → electrician
- pani, tanki, leak, pipe, tap, nala, drain, toilet, bathroom, washroom, motor, sewer → plumber
- AC, air conditioner, thanda, fridge, refrigerator, cooling → ac_technician
- daraza, almari, furniture, wood, door, shelf, cabinet → carpenter
- paint, rang, color, whitewash → painter
- safai, cleaning, clean, deep clean → home_cleaner
- car, engine, mechanic, vehicle → mechanic
- gas, geyser, cylinder, stove, burner → gas_technician
- pest, cockroach, rat, spray, insects → pest_control
- tiles, flooring, marble → tiler
- welding, iron, gate → welder
""",
    description="Zuban: Multilingual intent extraction agent that understands English, Urdu, and Roman Urdu service requests",
    tools=[],
    output_key="intent",
)

khoji_agent = LlmAgent(
    name="Khoji",
    model=LLM_MODEL,
    instruction="""You are Khoji, an AI-powered provider matching agent for XIDMAT.AI in Karachi.
When the user needs a service provider, use the search_providers tool to find the best matches.
After getting results, explain in roman Urdu+English mix why each provider is recommended based on their
distance, rating, experience, and availability. Be specific about rankings.""",
    description="Khoji: AI provider matching agent that ranks providers using 6-factor scoring",
    tools=[search_providers_tool],
    output_key="providers",
)

jadwal_agent = LlmAgent(
    name="Jadwal",
    model=LLM_MODEL,
    instruction="""You are Jadwal, the scheduling agent for XIDMAT.AI. Your job is to check provider availability.
Use the check_availability tool to verify if a provider is free at the requested time.
If there's a conflict, suggest alternative time slots. Respond in roman Urdu+English mix.""",
    description="Jadwal: Scheduling agent that checks availability and finds conflict-free slots",
    tools=[check_availability_tool],
    output_key="schedule",
)

qeemat_agent = LlmAgent(
    name="Qeemat",
    model=LLM_MODEL,
    instruction="""You are Qeemat, the dynamic pricing agent for XIDMAT.AI. 
Use the calculate_price tool to compute the final price based on 7 pricing components.
After getting the price breakdown, explain the pricing in roman Urdu+English mix — which factors
increased or decreased the price, and why. Be transparent about surcharges.""",
    description="Qeemat: AI pricing agent that calculates transparent dynamic pricing with 7 components",
    tools=[calculate_price_tool],
    output_key="pricing",
)

insaf_agent = LlmAgent(
    name="Insaf",
    model=LLM_MODEL,
    instruction="""You are Insaf, the AI dispute resolution agent for XIDMAT.AI.
When a user raises a dispute, use the resolve_dispute tool to get AI-powered resolution recommendations.
Explain the resolution in roman Urdu+English mix — what action was taken, any refund amount, and the
provider penalty. Be fair and empathetic.""",
    description="Insaf: AI dispute resolution agent that fairly resolves booking issues",
    tools=[resolve_dispute_tool],
    output_key="dispute",
)

root_agent = LlmAgent(
    name="Munsif",
    model=LLM_MODEL,
    instruction="""You are Munsif, the master orchestrator agent for XIDMAT.AI — a Pakistani AI-powered service booking platform.

Your role is to understand the user's request and coordinate the appropriate specialist agents:
- Zuban: Extracts intent from natural language (English/Urdu/Roman Urdu)
- Khoji: Finds and ranks the best providers using AI-powered 6-factor scoring
- Jadwal: Checks provider availability and suggests alternative slots
- Qeemat: Calculates transparent dynamic pricing with 7 components
- Insaf: Resolves disputes fairly with AI-powered analysis

Guide the conversation naturally. When a user asks for a service:
1. Let Zuban understand what they need
2. Use Khoji to find the best providers
3. Use Jadwal to check availability
4. Use Qeemat for pricing
5. Bring it all together for a seamless booking experience

Always respond in roman Urdu+English mix. Be helpful, specific, and efficient.""",
    description="Munsif: Master orchestrator that coordinates all XIDMAT.AI agents for seamless service booking",
    sub_agents=[zuban_agent, khoji_agent, jadwal_agent, qeemat_agent, insaf_agent],
    tools=[search_providers_tool, check_availability_tool, calculate_price_tool, resolve_dispute_tool],
)

logger.info(f"ADK Agents initialized with model={LLM_MODEL}: Munsif (root) → Zuban, Khoji, Jadwal, Qeemat, Insaf")