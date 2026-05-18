import random
import uuid
import datetime
import logging
from sqlalchemy.orm import Session
from backend.jadwal.jadwal_agent import JadwalAgent
from backend.qeemat.qeemat_agent import QeematAgent
from backend.insaf.insaf_agent import InsafAgent
from backend.models import Provider, Booking, Feedback

logger = logging.getLogger(__name__)

class MeezanAgent:
    def __init__(self):
        self.jadwal = JadwalAgent()
        self.qeemat = QeematAgent()
        self.insaf = InsafAgent()

    def create_booking(
        self, 
        db: Session, 
        session_id: str, 
        provider_id: int, 
        service_type: str, 
        location: str, 
        distance_km: float,
        urgency: str,
        confirmed_slot: str
    ) -> dict:
        # 1. Fetch provider details
        provider = db.query(Provider).filter(Provider.id == provider_id).first()
        if not provider:
            raise ValueError(f"Provider with ID {provider_id} not found.")

        # 2. Extract ISO time from confirmed_slot
        # Frontend sends format like "Today — 2026-05-18T20:27:50.557017" or "ASAP"
        slot_iso = None
        
        # Try to extract ISO datetime from the string
        if "—" in confirmed_slot or "-" in confirmed_slot:
            parts = confirmed_slot.split("—") if "—" in confirmed_slot else confirmed_slot.split("-")
            for part in parts:
                part = part.strip()
                # Check if this part looks like an ISO datetime
                if "T" in part and ":" in part:
                    try:
                        datetime.datetime.fromisoformat(part)
                        slot_iso = part
                        break
                    except:
                        continue
        
        # Fallback: try to parse the whole string
        if not slot_iso:
            try:
                datetime.datetime.fromisoformat(confirmed_slot)
                slot_iso = confirmed_slot
            except:
                pass
        
        # Final fallback to current time if parsing fails
        if not slot_iso:
            slot_iso = datetime.datetime.now().isoformat()
            logger.warning(f"Could not parse slot '{confirmed_slot}', using current time: {slot_iso}")

        # 3. Final check for conflicts with Jadwal
        conflict, _, _ = self.jadwal.check_conflict(db, provider_id, slot_iso)
        if conflict:
            # Try to find next available slot
            next_slots = self.jadwal.find_next_available_slots(db, provider_id, slot_iso)
            if next_slots:
                raise ValueError(f"Maazrat! Ye slot masroof hai. Available slots: {', '.join(next_slots[:2])}")
            else:
                raise ValueError("Maazrat! Ye slot ab masroof ho chuka hai. (Slot is now occupied)")

        # 4. Generate confirmation code (XIDMAT-XXXX)
        conf_code = f"XIDMAT-{random.randint(1000, 9999)}"

        # 5. Dynamic Pricing Logic (Using Qeemat Agent)
        try:
            appt_time = datetime.datetime.fromisoformat(slot_iso)
        except:
            appt_time = datetime.datetime.now()

        pricing = self.qeemat.calculate_price(
            base_rate=provider.base_price,
            urgency=urgency,
            distance_km=distance_km,
            appointment_time=appt_time,
            provider_rating=provider.rating or 5.0,
            experience_years=provider.experience or 1
        )
        
        final_price = pricing['final_price']
        price_breakdown = pricing['trace_log']

        # 6. Calculate reminder time (1 hour before)
        reminder_at = confirmed_slot.replace("10:00 AM", "09:00 AM").replace("11:00 AM", "10:00 AM")
        if reminder_at == confirmed_slot:
             reminder_at = "1 hour before your slot"

        # 7. Save to DB
        booking = Booking(
            session_id=session_id,
            provider_id=provider_id,
            service_type=service_type,
            price=final_price,
            confirmation_code=conf_code,
            confirmed_slot=confirmed_slot,
            price_breakdown=price_breakdown,
            reminder_at=reminder_at,
            status="CONFIRMED"
        )
        db.add(booking)
        db.commit()
        db.refresh(booking)

        # 8. Occupy the slot in Jadwal
        self.jadwal.occupy_slot(db, provider_id, slot_iso)

        # 9. Return full receipt
        return {
            "booking_id": booking.id,
            "confirmation_code": conf_code,
            "provider_name": provider.name,
            "provider_phone": provider.phone or "N/A",
            "provider_rating": provider.rating,
            "distance_km": round(distance_km, 2),
            "service": service_type.replace("_", " ").title(),
            "confirmed_slot": confirmed_slot,
            "final_price": int(final_price),
            "price_breakdown": price_breakdown,
            "location": location,
            "reminder_at": reminder_at,
            "status": "CONFIRMED"
        }

    def update_booking_status(self, db: Session, booking_id: int, new_status: str) -> dict:
        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking:
            raise ValueError("Booking not found")
        
        booking.status = new_status
        db.commit()
        return {"status": "updated", "new_status": new_status}

    def submit_feedback(self, db: Session, booking_id: int, rating: float, 
                        on_time: bool, quality: bool, cleanliness: bool, comment: str) -> dict:
        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking:
            raise ValueError("Booking not found")

        feedback = Feedback(
            booking_id=booking_id,
            provider_id=booking.provider_id,
            rating=rating,
            arrived_on_time=on_time,
            work_quality=quality,
            cleanliness=cleanliness,
            comment=comment
        )
        db.add(feedback)
        db.commit()

        # Trigger rating recalculation via InsafAgent's utility method
        self.insaf.update_provider_rating(db, booking.provider_id)
        
        booking.status = "COMPLETED"
        db.commit()

        return {"status": "feedback_received", "booking_id": booking_id}
    
    def raise_dispute(self, db: Session, booking_id: int, issue_type: str, description: str) -> dict:
        return self.insaf.handle_dispute(db, booking_id, issue_type, description)
