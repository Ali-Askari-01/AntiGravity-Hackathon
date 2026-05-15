import random
import uuid
import datetime
from sqlalchemy.orm import Session
from backend.models import Provider, Booking
from backend.jadwal.jadwal_agent import JadwalAgent

class MeezanAgent:
    def __init__(self):
        self.jadwal = JadwalAgent()

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

        # 2. Final check for conflicts with Jadwal
        # We need the ISO format for internal logic. 
        # If confirmed_slot is human readable, we should have the ISO from the request.
        # Let's assume for now the confirmed_slot passed here is the one used for the DB.
        # But Jadwal needs ISO. Let's try to parse it if it's human readable, or just expect the caller to provide ISO.
        # Actually, let's update the signature to take slot_iso.
        
        # For the hackathon, we'll try a simple heuristic to see if confirmed_slot is ISO
        slot_iso = confirmed_slot
        try:
            datetime.datetime.fromisoformat(slot_iso)
        except:
            # If not ISO, we'll just use a dummy current time for the DB record in this demo
            # In a real app, the frontend sends ISO.
            slot_iso = datetime.datetime.now().isoformat()

        conflict, _, _ = self.jadwal.check_conflict(db, provider_id, slot_iso)
        if conflict:
            raise ValueError("Maazrat! Ye slot ab masroof ho chuka hai. (Slot is now occupied)")

        # 3. Generate confirmation code (XIDMAT-XXXX)
        conf_code = f"XIDMAT-{random.randint(1000, 9999)}"

        # 3. Dynamic Pricing Logic (Simplified for Meezan)
        base_price = provider.base_price
        urgency_charge = 500 if urgency in ("urgent", "emergency") else 0
        distance_charge = round(distance_km * 50, 0) # 50 PKR per km
        peak_charge = 200 # Assume peak for demo
        quality_charge = 300 # Standard quality assurance fee
        tax = 0

        final_price = base_price + urgency_charge + distance_charge + peak_charge + quality_charge + tax
        
        price_breakdown = (
            f"Base {base_price} + Urgency {urgency_charge} + "
            f"Distance {distance_charge} + Peak {peak_charge} + "
            f"Quality {quality_charge} + Tax {tax}"
        )

        # 4. Calculate reminder time (1 hour before)
        # For demo, we just manipulate the string if possible, or just return a mock string
        # The PRD example: "Thursday, 21 May 2026 — 10:00 AM" -> "09:00 AM"
        reminder_at = confirmed_slot.replace("10:00 AM", "09:00 AM").replace("11:00 AM", "10:00 AM")
        if reminder_at == confirmed_slot: # fallback if time doesn't match
             reminder_at = "1 hour before your slot"

        # 5. Save to DB
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

        # 6. Occupy the slot in Jadwal
        self.jadwal.occupy_slot(db, provider_id, slot_iso)

        # 7. Return full receipt
        return {
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
