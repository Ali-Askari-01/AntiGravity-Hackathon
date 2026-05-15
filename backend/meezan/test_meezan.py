import sys
import os
import uuid
sys.stdout.reconfigure(encoding='utf-8')
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.database import SessionLocal
from backend.meezan.meezan_agent import MeezanAgent
from backend.models import Provider

def run_tests():
    agent = MeezanAgent()
    db = SessionLocal()

    try:
        # 1. Fetch a provider to test with
        provider = db.query(Provider).filter(Provider.name == "Ali AC Services").first()
        if not provider:
            print("❌ Ali AC Services not found in DB. Run seed first.")
            return

        session_id = str(uuid.uuid4())
        service_type = "ac_technician"
        location = "G-13"
        distance_km = 2.1
        urgency = "normal"
        confirmed_slot = "Thursday, 21 May 2026 — 10:00 AM"

        print(f"\n{'='*55}")
        print(f"Test 1: Booking with {provider.name}")
        
        receipt = agent.create_booking(
            db=db,
            session_id=session_id,
            provider_id=provider.id,
            service_type=service_type,
            location=location,
            distance_km=distance_km,
            urgency=urgency,
            confirmed_slot=confirmed_slot
        )

        print("\n✅ BOOKING SUCCESSFUL!")
        import json
        print(json.dumps(receipt, indent=2))

        # Verify persistence
        from backend.models import Booking
        saved = db.query(Booking).filter(Booking.confirmation_code == receipt["confirmation_code"]).first()
        if saved:
            print(f"\n✅ VERIFIED: Booking {saved.confirmation_code} found in database.")
        else:
            print(f"\n❌ ERROR: Booking not found in database.")

    except Exception as e:
        print(f"❌ TEST FAILED: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_tests()
