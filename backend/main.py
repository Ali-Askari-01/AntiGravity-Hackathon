from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
import contextlib
import datetime

from backend.database import engine, get_db, SessionLocal
from backend import models
from backend.munsif.munsif_agent import MunsifAgent
from backend.khoji.khoji_agent import KhojiAgent
from backend.meezan.meezan_agent import MeezanAgent
from backend.jadwal.jadwal_agent import JadwalAgent
from backend.qeemat.qeemat_agent import QeematAgent

from fastapi.middleware.cors import CORSMiddleware

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    models.Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(title="Antigravity Agents API", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For hackathon demo, allow all
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

munsif_agent  = MunsifAgent()
khoji_agent   = KhojiAgent()
meezan_agent  = MeezanAgent()
jadwal_agent  = JadwalAgent()
qeemat_agent  = QeematAgent()

# ── Request schemas ────────────────────────────────────────────────────────────
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
    requested_start: str # ISO format

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

# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/trace/{session_id}")
def get_trace(session_id: str):
    """
    GET /trace/{session_id} — Stream agent reasoning steps for a session.
    Returns workplan steps in the PRD-specified format.
    """
    session = munsif_agent.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    steps = []
    for i, step in enumerate(session.get("workplan", [])):
        steps.append({
            "step_number": i + 1,
            "agent": step.get("agent", "System"),
            "stage": step.get("result") and "result" or (step.get("error") and "error" or "action"),
            "message": step.get("action", ""),
            "timestamp": datetime.datetime.utcnow().isoformat()
        })
    return {"steps": steps, "session_id": session_id}

@app.post("/analyze")
def analyze(user_input: UserInput):
    """
    POST /analyze — PRD alias for /chat. Parses intent via Zuban.
    Returns intent JSON as specified in the PRD API spec.
    """
    session_id = user_input.session_id
    if not session_id:
        session_id = munsif_agent.create_session()
    response = munsif_agent.process_input(session_id, user_input.text)
    response["session_id"] = session_id
    # Extract flat intent fields for PRD compliance
    intent = response.get("intent", {})
    return {
        "session_id": session_id,
        "service_type": intent.get("service_type", ""),
        "service_label": intent.get("service_label", ""),
        "location": intent.get("location", ""),
        "time_normalized": intent.get("time_normalized", ""),
        "urgency": intent.get("urgency", "normal"),
        "language_detected": intent.get("language", "en"),
        "message": response.get("message", ""),
        "intent": intent,
        "next_step": response.get("next_step", ""),
        "session_state": response.get("session_state", {})
    }

@app.post("/match")
def match_providers(req: SearchRequest, db=Depends(get_db)):
    """
    POST /match — PRD alias for /search. Matches providers via Khoji.
    Returns providers list with id, name, distance_km, rating, available, score.
    """
    if req.session_id:
        munsif_agent.add_workplan_step(req.session_id, "Khoji", f"Matching providers for {req.service_type} in {req.location}")

    result = khoji_agent.find_providers(
        db=db,
        service_type=req.service_type,
        location=req.location,
        urgency=req.urgency,
    )

    if req.session_id:
        for line in result.get("trace", []):
            munsif_agent.add_workplan_step(req.session_id, "Khoji", line)

    providers = [
        {
            "id": p.get("provider_id", p.get("id")),
            "name": p.get("name"),
            "distance_km": p.get("distance_km"),
            "rating": p.get("rating"),
            "available": p.get("available", True),
            "score": p.get("score", 0)
        }
        for p in result.get("top_providers", [])
    ]
    return {"providers": providers}

@app.post("/pricing")
def get_pricing(req: PricingRequest, db=Depends(get_db)):
    """
    POST /pricing — Standalone Qeemat agent endpoint.
    Returns final_price and breakdown as per PRD spec.
    """
    provider = db.query(models.Provider).filter(models.Provider.id == req.provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    now = datetime.datetime.now()
    # If is_peak flag supplied, mock hour accordingly
    appt_time = now.replace(hour=9) if req.is_peak else now.replace(hour=14)

    pricing = qeemat_agent.calculate_price(
        base_rate=provider.base_price,
        urgency=req.urgency,
        distance_km=req.distance_km,
        appointment_time=appt_time,
        provider_rating=provider.rating or 5.0,
        experience_years=provider.experience or 1
    )
    return {
        "final_price": pricing["final_price"],
        "breakdown": pricing["breakdown"]
    }

@app.post("/track")
def track_booking(req: TrackRequest, db=Depends(get_db)):
    """
    POST /track — Update booking status.
    Returns booking_id, status, updated_at.
    """
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
@app.post("/chat")
def chat(user_input: UserInput):
    session_id = user_input.session_id
    if not session_id:
        session_id = munsif_agent.create_session()

    response = munsif_agent.process_input(session_id, user_input.text)
    response["session_id"] = session_id
    return response

@app.get("/session/{session_id}")
def get_session(session_id: str):
    session = munsif_agent.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

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

@app.post("/search")
def search_providers(req: SearchRequest, db=Depends(get_db)):
    """
    Directly call Khoji to find and rank providers.
    Can be called standalone OR chained after /chat returns intent.
    """
    if req.session_id:
        munsif_agent.add_workplan_step(req.session_id, "Khoji", f"Searching for providers for {req.service_type}...")

    result = khoji_agent.find_providers(
        db=db,
        service_type=req.service_type,
        location=req.location,
        urgency=req.urgency,
    )

    if req.session_id:
        for line in result.get("trace", []):
            munsif_agent.add_workplan_step(req.session_id, "Khoji", line)
        munsif_agent.add_workplan_step(req.session_id, "Khoji", f"Found {len(result.get('top_providers', []))} top matches.")

    return result

@app.post("/check_schedule")
def check_schedule(req: ScheduleRequest, db=Depends(get_db)):
    """
    Check if a slot is available with Jadwal.
    """
    if req.session_id:
        munsif_agent.add_workplan_step(req.session_id, "Jadwal", f"Checking availability for Provider ID {req.provider_id}")

    result = jadwal_agent.validate_and_book(
        db=db,
        provider_id=req.provider_id,
        requested_start_iso=req.requested_start
    )

    if req.session_id:
        for line in result.get("trace", []):
            munsif_agent.add_workplan_step(req.session_id, "Jadwal", line)
        status = "Available" if result.get("status") == "available" else "Unavailable/Conflict"
        munsif_agent.add_workplan_step(req.session_id, "Jadwal", f"Final Status: {status}")

    return result

@app.get("/providers")
def list_providers(db=Depends(get_db)):
    """Debug endpoint — list all seeded providers."""
    providers = db.query(models.Provider).all()
    return [
        {
            "id": p.id, "name": p.name, "skills": p.skills,
            "location": p.location, "rating": p.rating,
            "experience": p.experience, "available": p.is_available,
        }
        for p in providers
    ]

@app.post("/book")
def create_booking(req: BookingRequest, db=Depends(get_db)):
    """
    Finalize booking with Meezan.
    """
    munsif_agent.add_workplan_step(req.session_id, "Qeemat", "Calculating final price & breakdown...")
    munsif_agent.add_workplan_step(req.session_id, "Hukum", "Generating confirmation code & receipt...")
    
    try:
        receipt = meezan_agent.create_booking(
            db=db,
            session_id=req.session_id,
            provider_id=req.provider_id,
            service_type=req.service_type,
            location=req.location,
            distance_km=req.distance_km,
            urgency=req.urgency,
            confirmed_slot=req.confirmed_slot
        )
        
        munsif_agent.add_workplan_step(req.session_id, "Meezan", f"Booking confirmed! Code: {receipt['confirmation_code']}")
        return receipt
    except ValueError as e:
        munsif_agent.add_workplan_step(req.session_id, "Meezan", "Booking failed", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/feedback")
def submit_feedback(req: FeedbackRequest, db=Depends(get_db)):
    try:
        result = meezan_agent.submit_feedback(
            db=db,
            booking_id=req.booking_id,
            rating=req.rating,
            on_time=req.on_time,
            quality=req.quality,
            cleanliness=req.cleanliness,
            comment=req.comment
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/dispute")
def raise_dispute(req: DisputeRequest, db=Depends(get_db)):
    try:
        result = meezan_agent.raise_dispute(
            db=db,
            booking_id=req.booking_id,
            issue_type=req.issue_type,
            description=req.description
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
