from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import contextlib

from backend.database import engine, get_db, SessionLocal
from backend import models
from backend.munsif.munsif_agent import MunsifAgent
from backend.khoji.khoji_agent import KhojiAgent
from backend.meezan.meezan_agent import MeezanAgent
from backend.jadwal.jadwal_agent import JadwalAgent

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    models.Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(title="Antigravity Agents API", lifespan=lifespan)

munsif_agent = MunsifAgent()
khoji_agent  = KhojiAgent()
meezan_agent = MeezanAgent()
jadwal_agent = JadwalAgent()

# ── Request schemas ────────────────────────────────────────────────────────────
class UserInput(BaseModel):
    session_id: Optional[str] = None
    text: str

class SearchRequest(BaseModel):
    service_type: str
    location: str
    urgency: Optional[str] = "normal"

class ScheduleRequest(BaseModel):
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

# ── Routes ─────────────────────────────────────────────────────────────────────
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
    if session_id not in munsif_agent.sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return munsif_agent.sessions[session_id]

@app.post("/search")
def search_providers(req: SearchRequest, db=Depends(get_db)):
    """
    Directly call Khoji to find and rank providers.
    Can be called standalone OR chained after /chat returns intent.
    """
    result = khoji_agent.find_providers(
        db=db,
        service_type=req.service_type,
        location=req.location,
        urgency=req.urgency,
    )
    return result

@app.post("/check_schedule")
def check_schedule(req: ScheduleRequest, db=Depends(get_db)):
    """
    Check if a slot is available with Jadwal.
    """
    result = jadwal_agent.validate_and_book(
        db=db,
        provider_id=req.provider_id,
        requested_start_iso=req.requested_start
    )
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
        return receipt
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
