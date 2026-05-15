from sqlalchemy import Column, Integer, String, Float, Boolean, JSON
from backend.database import Base

class Session(Base):
    __tablename__ = "sessions"
    
    id = Column(String, primary_key=True, index=True)
    status = Column(String, default="active")
    workplan = Column(JSON, default=[])
    context = Column(JSON, default={})

class Provider(Base):
    __tablename__ = "providers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    phone = Column(String)          # e.g., "0312-4567890"
    skills = Column(JSON)          # e.g., ["plumber", "ac_technician"]
    location = Column(String)      # Human-readable area name
    lat = Column(Float, default=0.0)
    lng = Column(Float, default=0.0)
    rating = Column(Float, default=5.0)
    experience = Column(Integer, default=1)  # years of experience
    base_price = Column(Float)
    workload = Column(Integer, default=0)
    is_available = Column(Boolean, default=True)

class Booking(Base):
    __tablename__ = "bookings"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    provider_id = Column(Integer, index=True)
    service_type = Column(String)
    price = Column(Float)
    confirmation_code = Column(String, unique=True) # e.g., XIDMAT-2847
    confirmed_slot = Column(String)                 # e.g., "Thursday, 21 May 2026 — 10:00 AM"
    price_breakdown = Column(String)                # Detailed string
    reminder_at = Column(String)                    # e.g., "Thursday, 21 May 2026 — 09:00 AM"
    status = Column(String) # pending, confirmed, en-route, completed

class Schedule(Base):
    __tablename__ = "schedules"
    
    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, index=True)
    slot_start = Column(String) # ISO format
    slot_end = Column(String)   # ISO format
    status = Column(String)     # occupied, available
