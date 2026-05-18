"""
Antigravity FastAPI — All agent calls go through the Google ADK pipeline.
"""
import inspect
import json
import logging
from pydantic import BaseModel, Field
from typing import Any, Callable, Dict, List, Optional, Tuple

from backend.database import get_db
from backend import models
from backend.khoji.khoji_agent import get_providers_from_db
from backend.jadwal.jadwal_agent import check_schedule, find_next_slots
from backend.meezan.meezan_agent import create_booking
from backend.qeemat.qeemat_agent import calculate_price
from backend.insaf.insaf_agent import get_booking_details, create_refund, escalate_to_manager
from backend.zuban.zuban_agent import submit_intent

# We can use any LLM that supports function calling.
# For this project, we'll use Google's Gemini Pro.
try:
    import google.generativeai as genai
    from google.generativeai.types import GenerationConfig, Tool
except ImportError:
    raise ImportError("Google ADK requires google-generativeai. Please `pip install google-generativeai`")

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
# Tool and Agent Definition
# ------------------------------------------------------------------------------
def tool(func: Callable) -> Callable:
    """
    Decorator to mark a function as a tool that can be used by an agent.
    """
    func.is_tool = True
    return func

class AgentRunner:
    """
    A simple class to define an agent with a persona and a set of tools.
    """
    def __init__(self, persona: str, tools: List[Callable]):
        self.persona = persona
        self.tools = tools
        self.tool_map = {t.__name__: t for t in tools}
        self.tool_schemas = [Tool.from_function(t) for t in tools]

    def get_system_prompt(self) -> str:
        """
        Generates a system prompt that includes the agent's persona and a
        description of its tools.
        """
        return f"{self.persona}\n\nYou have access to the following tools. Use them to answer the user's request."

# ------------------------------------------------------------------------------
# Agent Execution
# ------------------------------------------------------------------------------
async def run_agent(
    agent: AgentRunner,
    prompt: str,
    session_id: str,
    generation_config: Optional[GenerationConfig] = None,
) -> Dict[str, Any]:
    """
    Runs an agent with a given prompt and returns the final response and a
    trace of the execution.
    """
<<<<<<< Updated upstream
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
                   urgency: str, confirmed_slot: str, price: float = None) -> dict:
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

        # Calculate price inline so it's never None
        base = provider.base_price or 0.0
        urgency_surcharge = 500.0 if urgency == "urgent" else 0.0
        distance_fee = distance_km * 50.0
        quality_premium = 200.0 if (provider.rating or 0) >= 4.5 else 0.0
        experience_factor = (provider.experience or 0) * 100.0
        calculated_price = round(base + urgency_surcharge + distance_fee + quality_premium + experience_factor, 2)
        price_breakdown = (
            f"Base: PKR {base} | Urgency: PKR {urgency_surcharge} | "
            f"Distance: PKR {distance_fee} | Quality: PKR {quality_premium} | "
            f"Experience: PKR {experience_factor} | Total: PKR {calculated_price}"
        )

        code = f"XIDMAT-{random.randint(1000, 9999)}"
        booking = Booking(
            session_id=session_id,
            provider_id=provider_id,
            service_type=service_type,
            status="confirmed",
            confirmed_slot=confirmed_slot,
            confirmation_code=code,
            price=calculated_price,
            price_breakdown=price_breakdown,
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

def apply_dispute_resolution(booking_id: int, action: str, penalty_amount: float = 0.0, new_rating: float = None, issue_type: str = None, description: str = None, resolution_text: str = None) -> dict:
    """
    [Insaf Tool] Apply the resolution to the database.
    """
    from backend.database import SessionLocal
    from backend.models import Booking, Provider, Dispute
    
    db = SessionLocal()
    try:
        b = db.query(Booking).filter(Booking.id == booking_id).first()
        if not b: return {"error": "Booking not found"}
        
        b.status = f"disputed_resolved_{action}"
        if new_rating and b.provider_id:
            p = db.query(Provider).filter(Provider.id == b.provider_id).first()
            if p: p.rating = new_rating
            
        # Log Dispute in DB
        dispute = Dispute(
            booking_id=booking_id,
            issue_type=issue_type or "unknown",
            description=description or "",
            resolution=resolution_text or action,
            status="RESOLVED"
        )
        db.add(dispute)
        
        db.commit()
        return {"status": "success", "action_applied": action}
    except Exception as e:
        db.rollback()
        return {"error": str(e)}
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════════════
# ADK AGENT DEFINITIONS
# ══════════════════════════════════════════════════════════════════════════════

_MODEL = "openrouter/google/gemini-2.0-flash-001"

# Optional: Ensure litellm (if ADK uses it under the hood) knows about the key
os.environ["OPENROUTER_API_KEY"] = os.getenv("OPENROUTER_API_KEY", "")

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
1. Call create_booking(session_id, provider_id, service_type, location, distance_km, urgency, confirmed_slot, price)
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
3. Call apply_dispute_resolution(booking_id, action, penalty_amount, new_rating, issue_type, description, resolution_text) to apply it. Pass the original issue_type and description, and set resolution_text to your explanation of the resolution.
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
    message = SimpleNamespace(role="user", parts=[SimpleNamespace(text=message_text)])
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


async def _ensure_adk_session_async(adk_session_id: str):
    """Async implementation to ensure ADK session."""
    try:
        await _session_service.get_session(
            app_name=APP_NAME, user_id="antigravity_user", session_id=adk_session_id
        )
    except Exception:
        await _session_service.create_session(
            app_name=APP_NAME, user_id="antigravity_user", session_id=adk_session_id
        )

def ensure_adk_session(adk_session_id: str):
    """Create an ADK session if it doesn't exist yet."""
    try:
=======
    if not genai.model:
>>>>>>> Stashed changes
        try:
            # Attempt to configure with API key from environment
            from dotenv import load_dotenv
            import os
            load_dotenv()
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("Gemini API key not configured. Set GOOGLE_API_KEY.")
            genai.configure(api_key=api_key)
        except Exception as e:
             raise ValueError(f"Gemini API key not configured. Set GOOGLE_API_KEY. Details: {e}")


    model = genai.GenerativeModel(
        model_name="gemini-1.5-pro-latest",
        system_instruction=agent.get_system_prompt(),
        generation_config=generation_config,
        tools=agent.tool_schemas,
    )
    
    chat = model.start_chat()
    response = await chat.send_message_async(prompt)
    response_message = response.candidates[0].content

    trace = []
    # Maximum number of tool calls to prevent infinite loops
    max_tool_calls = 10
    tool_call_count = 0

    while response_message.parts and response_message.parts[0].function_call and tool_call_count < max_tool_calls:
        tool_call_count += 1
        function_call = response_message.parts[0].function_call
        tool_name = function_call.name
        tool_args = {key: value for key, value in function_call.args.items()}
        
        trace.append({
            "agent": agent.__class__.__name__,
            "action": f"Calling tool `{tool_name}` with args: {tool_args}",
            "tool_name": tool_name,
            "tool_args": tool_args,
        })

        if tool_name not in agent.tool_map:
            trace.append({"error": f"Tool `{tool_name}` not found."})
            break

        tool_func = agent.tool_map[tool_name]
        try:
            # This is a simplified way to handle DB sessions for tools.
            # A more robust solution would use a dependency injection system.
            db_session_needed = "db" in inspect.signature(tool_func).parameters
            
            tool_result = None
            db = None
            try:
                if db_session_needed:
                    db = next(get_db())
                    tool_result = tool_func(db=db, **tool_args)
                else:
                    tool_result = tool_func(**tool_args)

                if inspect.isawaitable(tool_result):
                    tool_result = await tool_result
            finally:
                if db:
                    db.close()


            tool_result_str = json.dumps(tool_result, default=str) # Use default=str for non-serializable objects like datetime
            trace.append({
                "action": f"[Result] `{tool_name}`: {tool_result_str}",
                "tool_result": tool_result,
            })

            response = await chat.send_message_async(
                 [genai.types.Part(
                    function_response=genai.types.FunctionResponse(name=tool_name, response=tool_result)
                )]
            )
            response_message = response.candidates[0].content

        except Exception as e:
            error_message = f"Error calling `{tool_name}`: {e}"
            trace.append({"error": error_message})
            logger.error(f"ADK Tool Error: {e}", exc_info=True)
            # We can optionally send the error back to the model
            response = await chat.send_message_async(
                 [genai.types.Part(
                    function_response=genai.types.FunctionResponse(name=tool_name, response={"error": str(e)})
                )]
            )
            response_message = response.candidates[0].content
    
    if tool_call_count >= max_tool_calls:
        trace.append({"error": "Max tool calls reached. Exiting loop."})


    final_response = response_message.parts[0].text if response_message.parts and hasattr(response_message.parts[0], 'text') else ""
    trace.append({"agent": agent.__class__.__name__, "action": f"Final response: {final_response}"})
    
    return {"response": final_response, "trace": trace}


# ------------------------------------------------------------------------------
# Agent Definitions
# ------------------------------------------------------------------------------
zuban_agent = AgentRunner(
    persona="You are Zuban, a friendly AI assistant for a services marketplace. Your job is to understand the user's request and translate it into a structured `intent` using the `submit_intent` tool. The user might speak in Urdu, English, or a mix. Be conversational and helpful.",
    tools=[submit_intent],
)

khoji_agent = AgentRunner(
    persona="You are Khoji, a service provider search and matching expert. Your goal is to find the best 3-5 providers for a user's request. Use the `get_providers_from_db` tool to search the database. Then, use your reasoning to rank them based on location, rating, and urgency. Explain your choices clearly.",
    tools=[get_providers_from_db],
)

jadwal_agent = AgentRunner(
    persona="You are Jadwal, a scheduling assistant. Your job is to check if a provider is available at a requested time using the `check_schedule` tool. If they are not available, use the `find_next_slots` tool to suggest 3-5 alternative times.",
    tools=[check_schedule, find_next_slots],
)

qeemat_agent = AgentRunner(
    persona="You are Qeemat, a pricing specialist. Your task is to calculate the final price for a service using the `calculate_price` tool. The price has 7 components: base fee, distance fee, urgency surcharge, peak time fee, service complexity charge, provider tier bonus, and platform fee. Explain the breakdown clearly.",
    tools=[calculate_price],
)

meezan_agent = AgentRunner(
    persona="You are Meezan, the booking confirmation agent. Your role is to finalize a booking using the `create_booking` tool. You will be given all the details. Confirm the booking and provide the user with a confirmation code.",
    tools=[create_booking],
)

insaf_agent = AgentRunner(
    persona="You are Insaf, a dispute resolution officer. Your goal is to resolve customer complaints fairly. Use the `get_booking_details` tool to understand the case. You can then either `create_refund` or `escalate_to_manager`. Explain your decision.",
    tools=[get_booking_details, create_refund, escalate_to_manager],
)

# ------------------------------------------------------------------------------
# Agent Runners
# ------------------------------------------------------------------------------
async def run_zuban(session_id: str, text: str) -> Dict[str, Any]:
    return await run_agent(zuban_agent, text, session_id)

async def run_khoji(session_id: str, service_type: str, location: str, urgency: str) -> Dict[str, Any]:
    prompt = f"Find the best providers for '{service_type}' in '{location}'. The urgency is {urgency}."
    return await run_agent(khoji_agent, prompt, session_id)

async def run_jadwal(session_id: str, provider_id: int, requested_start: str) -> Dict[str, Any]:
    prompt = f"Check if provider {provider_id} is available around {requested_start}."
    return await run_agent(jadwal_agent, prompt, session_id)

async def run_qeemat(session_id: str, provider_id: int, urgency: str, distance_km: float, is_peak: bool) -> Dict[str, Any]:
    prompt = f"Calculate the price for provider {provider_id} with urgency {urgency}, distance {distance_km}km, and peak time status {is_peak}."
    return await run_agent(qeemat_agent, prompt, session_id)

async def run_meezan(session_id: str, provider_id: int, service_type: str, location: str, distance_km: float, urgency: str, confirmed_slot: str, price: float) -> Dict[str, Any]:
    prompt = f"Book provider {provider_id} for '{service_type}' at '{location}' ({distance_km}km away) for {confirmed_slot}. The confirmed price is PKR {price}. Urgency: {urgency}."
    return await run_agent(meezan_agent, prompt, session_id)

async def run_insaf(session_id: str, booking_id: int, issue_type: str, description: str) -> Dict[str, Any]:
    prompt = f"Resolve dispute for booking {booking_id}. Issue: '{issue_type}'. Description: '{description}'."
    return await run_agent(insaf_agent, prompt, session_id)
