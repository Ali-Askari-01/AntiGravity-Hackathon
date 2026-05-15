from sqlalchemy.orm import Session
from typing import Dict, Any, List
from datetime import datetime, timedelta

# In a real app we'd import the Booking model, but for mocking conflict we can use a stub
# from backend.models import Booking

class JadwalAgent:
    def __init__(self):
        self.travel_buffer_minutes = 30

    def check_schedule(self, db: Session, provider_id: int, requested_time: datetime) -> Dict[str, Any]:
        """
        Checks for time conflicts and handles buffers/waitlists.
        For hackathon demo, we will mock the conflict logic.
        """
        # Mock logic: Assume provider is booked if requested_time hour is 14 (2 PM)
        is_conflict = (requested_time.hour == 14)
        
        if is_conflict:
            # Generate 2 alternative slots
            alt_slot_1 = requested_time + timedelta(hours=2)
            alt_slot_2 = requested_time + timedelta(hours=4)
            
            return {
                "status": "conflict",
                "message": "Provider is waqt masroof hain (Provider is busy at this time).",
                "alternatives": [
                    alt_slot_1.isoformat(),
                    alt_slot_2.isoformat()
                ],
                "waitlist_option": True
            }

        # No conflict scenario
        return {
            "status": "available",
            "message": "Waqt dastyab hai (Time is available).",
            "booked_slot": requested_time.isoformat(),
            "buffer_added": f"{self.travel_buffer_minutes} mins"
        }
