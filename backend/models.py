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
    skills = Column(JSON)  # e.g., ["plumbing", "electrical"]
    location = Column(String) # For simple distance calculation later
    rating = Column(Float, default=5.0)
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
    status = Column(String) # pending, confirmed, en-route, completed
