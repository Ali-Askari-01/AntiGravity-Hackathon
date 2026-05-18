"""
Antigravity FastAPI — All agent calls go through the Google ADK pipeline.
"""
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
import contextlib
import datetime
import logging
import uuid

from backend.database import engine, get_db, SessionLocal
from backend import models
from backend.munsif.munsif_agent import MunsifAgent        # session/workplan manager
from backend.meezan.meezan_agent import MeezanAgent        # fallback for feedback/dispute

from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

# ── ADK pipeline (loaded lazily to avoid import errors if ADK not installed) ───
_adk_available = False
try:
    from backend import adk_pipeline as adk
    _adk_available = True
    logger.info("✅ Google ADK pipeline loaded successfully")
except Exception as _adk_err:
    logger.warning(f"⚠️  ADK not available: {_adk_err}")


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    models.Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(title="Antigravity Agents API — Powered by Google ADK", lifespan=lifespan)

origins = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "success", "message": "Antigravity Backend is running!"}

# Always-on orchestrator (manages sessions, workplan)
munsif = MunsifAgent()


# ── Request schemas ─────────────────────────────────────────────────────────────
class UserInput(BaseModel):
    session_id: Optional[str] = None
    text: str

class SearchRequest(BaseModel):
    session_id: Optional[str] = None
    service_type: str
    location: str
    urgency: Optional[str] = "normal"

class ScheduleRequest(BaseModel):
    session_id: Optional[str] = None
    provider_id: int
    requested_start: str

class BookingRequest(BaseModel):
    session_id: str
    provider_id: int
    service_type: str
    location: str
    distance_km: float
    urgency: str
    confirmed_slot: str

class FeedbackRequest(BaseModel):
    booking_id: int
    rating: float
    on_time: bool
    quality: bool
    cleanliness: bool
    comment: Optional[str] = ""

class DisputeRequest(BaseModel):
    booking_id: int
    issue_type: str
    description: str

class TrackRequest(BaseModel):
    booking_id: int
    status: str

class PricingRequest(BaseModel):
    provider_id: int
    urgency: Optional[str] = "normal"
    distance_km: Optional[float] = 1.0
    is_peak: Optional[bool] = False


# ── Helper: push ADK trace into our SQLite workplan ────────────────────────────
def _push_trace(session_id: str, trace: list):
    for step in trace:
        munsif.add_workplan_step(
            session_id,
            step.get("agent", "Agent"),
            step.get("action", "")
        )


# ══════════════════════════════════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/trace/{session_id}")
def get_trace(session_id: str):
    """GET /trace/{session_id} — Stream agent workplan as PRD-spec step list."""
    session = munsif.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    steps = []
    for i, step in enumerate(session.get("workplan", [])):
        steps.append({
            "step_number": i + 1,
            "agent": step.get("agent", "System"),
            "stage": "error" if step.get("error") else "action",
            "message": step.get("action", ""),
            "timestamp": datetime.datetime.utcnow().isoformat()
        })
    return {"steps": steps, "session_id": session_id}


@app.post("/chat")
async def chat(user_input: UserInput, db: Session = Depends(get_db)):
    """
    POST /chat — Orchestrates Zuban via ADK.
    """
    session_id = user_input.session_id or munsif.create_session()
    munsif.add_workplan_step(session_id, "System", "Session started. Routing to Zuban...")

    if not _adk_available:
        raise HTTPException(status_code=500, detail="ADK not available. Please install it.")

    try:
        result = await adk.run_zuban(session_id, user_input.text)
        _push_trace(session_id, result.get("trace", []))
        
        intent = {}
        # The intent is now in the tool_result of the 'submit_intent' tool call
        for step in result.get("trace", []):
            if step.get("tool_name") == "submit_intent" and "tool_result" in step:
                intent = step.get("tool_result", {})
        
        if not intent:
            logger.error("Zuban did not return a valid intent.")
            munsif.add_workplan_step(session_id, "System", "Error: Zuban failed to understand the request.", error=True)
            # Fallback to Meezan for clarification
            fallback_result = await adk.run_meezan(session_id, 0, "clarification", "", 0, "low", "", 0)
            _push_trace(session_id, fallback_result.get("trace", []))
            return {
                "message": fallback_result.get("response", "Sorry, I am having trouble understanding. Could you please rephrase?"),
                "intent": {},
                "next_step": "chat",
                "session_id": session_id,
                "session_state": munsif.get_session(session_id)
            }

        munsif.add_workplan_step(session_id, "System", f"Routing to Khoji for {intent.get('service_label', '')} search in {intent.get('location', '')}")
        
        # update context
        db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
        if db_session:
            db_session.context = {"intent": intent}
            db.commit()
        
        return {
            "message": result.get("response", ""),
            "intent": intent,
            "next_step": "khoji_search",
            "session_id": session_id,
            "session_state": munsif.get_session(session_id)
        }
    except Exception as e:
        logger.error(f"ADK Zuban failed: {e}", exc_info=True)
        munsif.add_workplan_step(session_id, "System", f"Error during chat processing: {e}", error=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze")
async def analyze(user_input: UserInput, db: Session = Depends(get_db)):
    """POST /analyze — PRD alias. Returns flat intent JSON."""
    return await chat(user_input, db)


@app.post("/search")
async def search_providers_endpoint(req: SearchRequest, db: Session = Depends(get_db)):
    """POST /search — Khoji via ADK finds and ranks providers."""
    if not _adk_available:
        raise HTTPException(status_code=500, detail="ADK not available.")

    session_id = req.session_id or str(uuid.uuid4())
    if req.session_id:
        munsif.add_workplan_step(session_id, "System", f"Routing to Khoji for {req.service_type} in {req.location}")

    try:
        adk_result = await adk.run_khoji(session_id, req.service_type, req.location, req.urgency)
        if req.session_id:
            _push_trace(req.session_id, adk_result.get("trace", []))
            
        # The ADK pipeline now returns a structured list of providers.
        # We extract it from the tool call results in the trace.
        providers_list = []
        for step in adk_result.get("trace", []):
            if step.get("tool_name") == "get_providers_from_db" and "tool_result" in step:
                providers_list = step.get("tool_result", {}).get("matched_providers", [])
                break # Found the providers, no need to look further

        # The new Khoji agent should provide a rationale in its final response.
        # We can add a fallback just in case.
        for p in providers_list:
            if "rationale" not in p:
                p["rationale"] = "Recommended based on a combination of distance, rating, and experience."
        
        return {
            "status": "success",
            "message": adk_result.get("response", "Here are the top providers I found for you."),
            "session_id": session_id,
            "top_providers": providers_list[:5] # Return top 5 as per new logic
        }
    except Exception as e:
        logger.warning(f"ADK Khoji error: {e}", exc_info=True)
        if req.session_id:
            munsif.add_workplan_step(req.session_id, "System", f"Khoji search failed: {e}", error=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/match")
async def match_providers(req: SearchRequest, db: Session = Depends(get_db)):
    """POST /match — PRD alias for /search."""
    return await search_providers_endpoint(req, db)


@app.post("/check_schedule")
async def check_schedule(req: ScheduleRequest, db: Session = Depends(get_db)):
    """POST /check_schedule — Jadwal via ADK checks availability."""
    if not _adk_available:
        raise HTTPException(status_code=500, detail="ADK not available.")

    session_id = req.session_id or str(uuid.uuid4())
    if req.session_id:
        munsif.add_workplan_step(session_id, "System", f"Routing to Jadwal for Provider {req.provider_id}")

    try:
        adk_result = await adk.run_jadwal(session_id, req.provider_id, req.requested_start)
        if req.session_id:
            _push_trace(req.session_id, adk_result.get("trace", []))
            
        # extract schedule details from tool calls in trace for frontend
        status = "available"
        alts = []
        for step in adk_result.get("trace", []):
            if step.get("tool_name") == "check_schedule" and "tool_result" in step:
                if step["tool_result"].get("conflict"):
                    status = "conflict"
            if step.get("tool_name") == "find_next_slots" and "tool_result" in step:
                alts = step.get("tool_result", {}).get("available_slots", [])
        
        return {
            "status": status,
            "message": adk_result.get("response", ""),
            "alternatives": alts,
            "session_id": session_id,
            "trace": [s.get("action") for s in adk_result.get("trace", [])]
        }
    except Exception as e:
        logger.warning(f"ADK Jadwal error: {e}", exc_info=True)
        if req.session_id:
            munsif.add_workplan_step(req.session_id, "System", f"Jadwal check failed: {e}", error=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/schedule")
async def schedule_alias(req: ScheduleRequest, db: Session = Depends(get_db)):
    """POST /schedule — PRD alias for /check_schedule."""
    return await check_schedule(req, db)


@app.post("/pricing")
async def get_pricing(req: PricingRequest, db: Session = Depends(get_db)):
    """POST /pricing — Qeemat via ADK calculates the 7-component price."""
    if not _adk_available:
        raise HTTPException(status_code=500, detail="ADK not available.")

    session_id = f"price_{req.provider_id}_{datetime.datetime.now().timestamp()}"
<<<<<<< Updated upstream
    adk_result = adk.run_qeemat(session_id, req.provider_id, req.urgency, req.distance_km, req.is_peak)

    # Parse final_price from the Qeemat tool result in the trace
    final_price = 0.0
    breakdown = {}
    for step in adk_result.get("trace", []):
        if step.get("tool_name") == "get_provider_pricing_details":
            tool_result = step.get("tool_result", {})
            if isinstance(tool_result, dict) and "base_rate" in tool_result:
                base = tool_result.get("base_rate", 0.0)
                rating = tool_result.get("rating", 5.0)
                exp = tool_result.get("experience_years", 1)
                urgency_surcharge = 500.0 if req.urgency == "urgent" else 0.0
                distance_fee = req.distance_km * 50.0
                peak_fee = 300.0 if req.is_peak else 0.0
                quality_premium = 200.0 if rating >= 4.5 else 0.0
                experience_factor = exp * 100.0
                final_price = round(base + urgency_surcharge + distance_fee + peak_fee + quality_premium + experience_factor, 2)
                breakdown = {
                    "base_rate": base,
                    "urgency_surcharge": urgency_surcharge,
                    "distance_fee": distance_fee,
                    "peak_hour_fee": peak_fee,
                    "quality_premium": quality_premium,
                    "experience_factor": experience_factor,
                    "total": final_price,
                }

    return {
        "final_price": final_price,
        "breakdown": breakdown,
        "message": adk_result.get("response", ""),
        "trace": [s.get("action") for s in adk_result.get("trace", [])]
    }
=======
    
    try:
        adk_result = await adk.run_qeemat(session_id, req.provider_id, req.urgency, req.distance_km, req.is_peak)
        
        # Extract final price and breakdown from the new agent's structured output
        final_price = 0
        breakdown = {}
        for step in adk_result.get("trace", []):
            if step.get("tool_name") == "calculate_price" and "tool_result" in step:
                tool_res = step["tool_result"]
                final_price = tool_res.get("final_price", 0)
                breakdown = tool_res.get("breakdown", {})
                break
        
        return {
            "final_price": final_price,
            "breakdown": breakdown, 
            "message": adk_result.get("response", ""),
            "trace": [s.get("action") for s in adk_result.get("trace", [])]
        }
    except Exception as e:
        logger.error(f"ADK Qeemat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
>>>>>>> Stashed changes


@app.post("/book")
async def create_booking(req: BookingRequest, db: Session = Depends(get_db)):
    """POST /book — Qeemat + Meezan via ADK: price then book."""
    if not _adk_available:
        raise HTTPException(status_code=500, detail="ADK not available.")

    session_id = req.session_id
    munsif.add_workplan_step(session_id, "System", "Routing to Qeemat for pricing...")

    try:
        # 1. Get Price from Qeemat
        qeemat_result = await adk.run_qeemat(
            session_id, req.provider_id, req.urgency, req.distance_km, False # is_peak=False for now
        )
        _push_trace(session_id, qeemat_result.get("trace", []))
        
        price = 0
        price_breakdown = {}
        for step in qeemat_result.get("trace", []):
            if step.get("tool_name") == "calculate_price" and "tool_result" in step:
                price = step["tool_result"].get("final_price", 0)
                price_breakdown = step["tool_result"].get("breakdown", {})
                break
        
        if price == 0:
            raise ValueError("Qeemat failed to calculate a valid price.")

        munsif.add_workplan_step(session_id, "System", f"Routing to Meezan for booking execution with price {price}...")
        
        # 2. Execute Booking with Meezan
        meezan_result = await adk.run_meezan(
            session_id, req.provider_id, req.service_type,
            req.location, req.distance_km, req.urgency, req.confirmed_slot,
            price=price
        )
        _push_trace(session_id, meezan_result.get("trace", []))
        
        # 3. Extract confirmation details from Meezan's tool call
        booking_id = None
        confirmation_code = None
        for step in meezan_result.get("trace", []):
            if step.get("tool_name") == "create_booking" and "tool_result" in step:
                booking_id = step["tool_result"].get("booking_id")
                confirmation_code = step["tool_result"].get("confirmation_code")
                break
        
        if not booking_id or not confirmation_code:
            raise ValueError("Meezan failed to return a valid booking confirmation.")
                
        # 4. Fetch provider details for the final response
        p = db.query(models.Provider).filter(models.Provider.id == req.provider_id).first()
        
        return {
            "booking_id": booking_id,
            "confirmation_code": confirmation_code,
            "message": meezan_result.get("response", "Booking confirmed!"),
            "final_price": price,
            "price_breakdown": price_breakdown,
            "provider_name": p.name if p else "Provider",
            "provider_rating": p.rating if p else 5.0,
            "distance_km": req.distance_km,
            "confirmed_slot": req.confirmed_slot,
            "location": req.location
        }
    except Exception as e:
        logger.warning(f"ADK Booking flow error: {e}", exc_info=True)
        munsif.add_workplan_step(session_id, "System", f"Booking failed: {e}", error=True)
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/track")
def track_booking(req: TrackRequest, db=Depends(get_db)):
    """POST /track — Update booking status (EN_ROUTE / ARRIVED / COMPLETED)."""
    booking = db.query(models.Booking).filter(models.Booking.id == req.booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    booking.status = req.status
    db.commit()
    return {
        "booking_id": req.booking_id,
        "status": req.status,
        "updated_at": datetime.datetime.utcnow().isoformat()
    }


@app.post("/feedback")
def submit_feedback(req: FeedbackRequest, db=Depends(get_db)):
    """POST /feedback — Submit rating and update provider score."""
    try:
        b = db.query(models.Booking).filter(models.Booking.id == req.booking_id).first()
        if not b: raise HTTPException(status_code=404, detail="Booking not found")
        
        # 1. Create Feedback record
        feedback = models.Feedback(
            booking_id=req.booking_id,
            provider_id=b.provider_id,
            rating=req.rating,
            arrived_on_time=req.on_time,
            work_quality=req.quality,
            cleanliness=req.cleanliness,
            comment=req.comment
        )
        db.add(feedback)
        
        p = db.query(models.Provider).filter(models.Provider.id == b.provider_id).first()
        if p:
            # 2. Weighted rolling average
            current_rating = p.rating or 5.0
            review_count = p.review_count or 0
            p.rating = round((current_rating * review_count + req.rating) / (review_count + 1), 2)
            p.review_count = review_count + 1
            
        b.status = "completed"
        db.commit()
        return {"status": "success", "message": "Shukriya! Feedback mil gaya."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/dispute")
async def raise_dispute(req: DisputeRequest, db: Session = Depends(get_db)):
    """POST /dispute — Insaf via ADK resolves dispute."""
    if not _adk_available:
        raise HTTPException(status_code=500, detail="ADK not available.")
    
    try:
        # A dispute needs its own session for tracking purposes
        munsif_session = munsif.create_session(prefix="dispute_")
        munsif.add_workplan_step(munsif_session, "System", f"Routing to Insaf for dispute on Booking {req.booking_id}")

        insaf_result = await adk.run_insaf(
            munsif_session, req.booking_id, req.issue_type, req.description
        )
        _push_trace(munsif_session, insaf_result.get("trace", []))

        # Extract resolution details from the trace
        resolution_status = "pending"
        for step in insaf_result.get("trace", []):
            if step.get("tool_name") == "create_refund" and "tool_result" in step:
                if step["tool_result"].get("status") == "success":
                    resolution_status = "refund_processed"
                    break
            elif step.get("tool_name") == "escalate_to_manager" and "tool_result" in step:
                 if step["tool_result"].get("status") == "success":
                    resolution_status = "escalated"
                    break

        return {
            "booking_id": req.booking_id,
            "status": resolution_status,
            "message": insaf_result.get("response", "Your dispute is being processed."),
            "session_id": munsif_session
        }
    except Exception as e:
        logger.error(f"ADK Insaf error: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))


# ── Read-only utility endpoints ─────────────────────────────────────────────────
@app.get("/bookings")
def list_bookings(db=Depends(get_db)):
    bookings = db.query(models.Booking).order_by(models.Booking.id.desc()).all()
    return bookings

@app.get("/booking/{booking_id}")
def get_booking(booking_id: int, db=Depends(get_db)):
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking

@app.get("/session/{session_id}")
def get_session(session_id: str):
    session = munsif.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@app.get("/providers")
def list_providers(db=Depends(get_db)):
    providers = db.query(models.Provider).all()
    return [
        {"id": p.id, "name": p.name, "skills": p.skills, "location": p.location,
         "rating": p.rating, "experience": p.experience, "available": p.is_available}
        for p in providers
    ]

@app.get("/health")
def health():
    return {"status": "ok", "adk_available": _adk_available,
            "timestamp": datetime.datetime.utcnow().isoformat()}
