from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timedelta
from backend.models import Schedule

class JadwalAgent:
    def __init__(self):
        self.session_length_hours = 2

    def check_conflict(self, db: Session, provider_id: int, requested_start: str) -> Tuple[bool, Optional[datetime], Optional[datetime]]:
        """
        Checks if the provider has an overlapping 'occupied' slot.
        """
        req_start = datetime.fromisoformat(requested_start)
        req_end = req_start + timedelta(hours=self.session_length_hours)

        existing = db.query(Schedule).filter(
            Schedule.provider_id == provider_id,
            Schedule.status == 'occupied'
        ).all()

        for row in existing:
            booked_start = datetime.fromisoformat(row.slot_start)
            booked_end = datetime.fromisoformat(row.slot_end)
            if req_start < booked_end and req_end > booked_start:
                return True, booked_start, booked_end
        
        return False, None, None

    def find_next_available_slots(self, db: Session, provider_id: int, after_datetime_iso: str, count: int = 3) -> List[str]:
        """
        Scenario B: Finds the next available slots if a conflict exists.
        """
        slots = []
        start_time = datetime.fromisoformat(after_datetime_iso)
        candidate = start_time + timedelta(hours=1)
        
        # Max lookahead: 24 hours from requested time (per PRD Scenario C)
        max_lookahead = start_time + timedelta(hours=24)
        
        while len(slots) < count and candidate < max_lookahead:
            conflict, _, _ = self.check_conflict(db, provider_id, candidate.isoformat())
            if not conflict:
                # Format for display: "Thursday, 21 May 2026 — 10:00 AM"
                slots.append(candidate.strftime("%A, %d %B %Y — %I:%M %p"))
            candidate += timedelta(hours=1) # check every hour
        
        return slots

    def validate_and_book(self, db: Session, provider_id: int, requested_start_iso: str) -> Dict[str, Any]:
        """
        Main entry point for Jadwal.
        """
        print(f"\n🗓️  Checking schedule for Provider {provider_id} on {requested_start_iso}...")
        
        conflict, b_start, b_end = self.check_conflict(db, provider_id, requested_start_iso)
        
        if conflict:
            print(f"⚠️  CONFLICT: Provider booked {b_start.strftime('%I:%M %p')}–{b_end.strftime('%I:%M %p')}")
            print(f"🔄  Finding next available slots...")
            
            next_slots = self.find_next_available_slots(db, provider_id, requested_start_iso)
            
            if not next_slots:
                # Scenario C: Waitlist
                print(f"📋  No slots within 24h. Adding to waitlist.")
                return {
                    "status": "waitlist",
                    "message": "Maazrat, provider fully booked hain. Humne aapko waitlist mein daal diya hai.",
                    "waitlist_enabled": True
                }
            
            print(f"✅  Available slots: {' | '.join(next_slots)}")
            return {
                "status": "conflict",
                "message": "Provider is waqt masroof hain. Kya aap ye slots pasand karenge?",
                "alternatives": next_slots
            }

        # Scenario A: Available
        # Note: We don't write 'occupied' here yet; Meezan does that upon final confirmation.
        # But for Jadwal's internal logic, we return success.
        print(f"✅  Slot available.")
        return {
            "status": "available",
            "message": "Waqt dastyab hai.",
            "requested_slot": requested_start_iso
        }

    def occupy_slot(self, db: Session, provider_id: int, slot_start_iso: str):
        """
        Called by Meezan to finalize the schedule.
        """
        start_dt = datetime.fromisoformat(slot_start_iso)
        end_dt = start_dt + timedelta(hours=self.session_length_hours)
        
        new_slot = Schedule(
            provider_id=provider_id,
            slot_start=start_dt.isoformat(),
            slot_end=end_dt.isoformat(),
            status="occupied"
        )
        db.add(new_slot)
        db.commit()
